#!/usr/bin/env php
<?php
/**
 * Checkmk WordPress core version inventory.
 *
 * This plug-in intentionally never includes or executes WordPress application
 * code. It reads the installed core version from wp-includes/version.php and
 * queries the public WordPress version-check API for the latest release.
 */

const DEFAULT_BASE_DIR = '/var/www/sites.d';
const DEFAULT_SEARCH_STRING = 'deploy/current';
const MAX_SCAN_ENTRIES = 100000;
const API_TIMEOUT_SECONDS = 10;

function config_path(): string
{
    $configDir = getenv('MK_CONFDIR');
    if ($configDir === false || trim($configDir) === '') {
        $configDir = '/etc/check_mk';
    }
    return rtrim($configDir, '/') . '/wp_instances.cfg';
}

function load_config(): array
{
    $config = [
        'BASEDIR' => DEFAULT_BASE_DIR,
        'SEARCH_STRING' => DEFAULT_SEARCH_STRING,
    ];

    $path = config_path();
    if (!is_readable($path)) {
        return $config;
    }

    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        return $config;
    }

    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
            continue;
        }
        [$key, $value] = explode('=', $line, 2);
        $key = trim($key);
        $value = trim($value);
        if (strlen($value) >= 2) {
            $first = $value[0];
            $last = $value[strlen($value) - 1];
            if (($first === '"' && $last === '"') || ($first === "'" && $last === "'")) {
                $value = substr($value, 1, -1);
            }
        }
        if ($key === 'BASEDIR') {
            $config['BASEDIR'] = $value;
        } elseif ($key === 'SEARCH_STRING' || $key === 'SEACH_STRING') {
            // Accept the historical misspelling for existing baked agents.
            $config['SEARCH_STRING'] = $value;
        }
    }

    return $config;
}

function find_wordpress_roots(string $baseDir, string $searchString): array
{
    $realBase = realpath($baseDir);
    if ($realBase === false || !is_dir($realBase) || !is_readable($realBase)) {
        throw new RuntimeException("Base directory is not readable: {$baseDir}");
    }

    $queue = [$realBase];
    $visited = [];
    $roots = [];
    $entries = 0;

    while ($queue !== []) {
        $directory = array_pop($queue);
        $realDirectory = realpath($directory);
        if ($realDirectory === false || isset($visited[$realDirectory])) {
            continue;
        }
        $visited[$realDirectory] = true;

        $children = @scandir($realDirectory);
        if ($children === false) {
            continue;
        }

        foreach ($children as $child) {
            if ($child === '.' || $child === '..') {
                continue;
            }
            $entries++;
            if ($entries > MAX_SCAN_ENTRIES) {
                throw new RuntimeException('Directory scan exceeded the safety limit');
            }

            $path = $realDirectory . DIRECTORY_SEPARATOR . $child;
            if (is_dir($path)) {
                $queue[] = $path;
                continue;
            }
            if ($child !== 'wp-load.php' || !is_file($path)) {
                continue;
            }
            if ($searchString !== '' && !str_contains($path, $searchString)) {
                continue;
            }
            $root = dirname($path);
            $realRoot = realpath($root);
            if ($realRoot !== false) {
                $roots[$realRoot] = true;
            }
        }
    }

    $result = array_keys($roots);
    sort($result, SORT_NATURAL | SORT_FLAG_CASE);
    return $result;
}

function read_installed_version(string $wordpressRoot): string
{
    $versionFile = $wordpressRoot . '/wp-includes/version.php';
    if (!is_readable($versionFile)) {
        throw new RuntimeException('wp-includes/version.php is not readable');
    }

    $content = file_get_contents($versionFile);
    if ($content === false) {
        throw new RuntimeException('Unable to read wp-includes/version.php');
    }

    if (!preg_match('/\$wp_version\s*=\s*[\'\"]([^\'\"]+)[\'\"]\s*;/', $content, $matches)) {
        throw new RuntimeException('Unable to determine the installed WordPress version');
    }
    return trim($matches[1]);
}

function fetch_url(string $url): string
{
    if (function_exists('curl_init')) {
        $handle = curl_init($url);
        if ($handle === false) {
            throw new RuntimeException('Unable to initialize cURL');
        }
        curl_setopt_array($handle, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS => 3,
            CURLOPT_CONNECTTIMEOUT => API_TIMEOUT_SECONDS,
            CURLOPT_TIMEOUT => API_TIMEOUT_SECONDS,
            CURLOPT_USERAGENT => 'checkmk-wordpress-inventory/1.0',
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
        ]);
        $body = curl_exec($handle);
        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        $error = curl_error($handle);
        curl_close($handle);
        if ($body === false) {
            throw new RuntimeException('WordPress version API request failed: ' . $error);
        }
        if ($status < 200 || $status >= 300) {
            throw new RuntimeException("WordPress version API returned HTTP {$status}");
        }
        return (string) $body;
    }

    $context = stream_context_create([
        'http' => [
            'timeout' => API_TIMEOUT_SECONDS,
            'follow_location' => 1,
            'max_redirects' => 3,
            'user_agent' => 'checkmk-wordpress-inventory/1.0',
            'ignore_errors' => false,
        ],
        'ssl' => [
            'verify_peer' => true,
            'verify_peer_name' => true,
        ],
    ]);
    $body = @file_get_contents($url, false, $context);
    if ($body === false) {
        throw new RuntimeException('WordPress version API request failed');
    }
    return $body;
}

function latest_core_version(string $installedVersion, array &$cache): string
{
    if (isset($cache[$installedVersion])) {
        return $cache[$installedVersion];
    }

    $query = http_build_query([
        'version' => $installedVersion,
        'php' => PHP_VERSION,
        'locale' => 'en_US',
    ]);
    $body = fetch_url('https://api.wordpress.org/core/version-check/1.7/?' . $query);
    $payload = json_decode($body, true, 32, JSON_THROW_ON_ERROR);
    $offers = $payload['offers'] ?? null;
    if (!is_array($offers) || $offers === []) {
        throw new RuntimeException('WordPress version API returned no offers');
    }

    foreach ($offers as $offer) {
        if (is_array($offer) && isset($offer['current']) && is_string($offer['current'])) {
            $cache[$installedVersion] = trim($offer['current']);
            return $cache[$installedVersion];
        }
    }
    throw new RuntimeException('WordPress version API returned no current version');
}

function core_status(string $installedVersion, string $latestVersion): int
{
    if (version_compare($installedVersion, $latestVersion, '>=')) {
        return 0;
    }

    $installed = array_pad(explode('.', $installedVersion), 3, '0');
    $latest = array_pad(explode('.', $latestVersion), 3, '0');
    if ($installed[0] !== $latest[0] || $installed[1] !== $latest[1]) {
        return 2;
    }
    return 1;
}

function instance_name(string $root, string $baseDir, array &$seen): string
{
    $realBase = realpath($baseDir);
    $name = basename($root);
    if ($realBase !== false && str_starts_with($root, $realBase . DIRECTORY_SEPARATOR)) {
        $relative = substr($root, strlen($realBase) + 1);
        if ($relative !== false && $relative !== '') {
            $name = $relative;
        }
    }
    $name = str_replace(DIRECTORY_SEPARATOR, '/', $name);
    $candidate = $name;
    $index = 2;
    while (isset($seen[$candidate])) {
        $candidate = $name . ' ' . $index;
        $index++;
    }
    $seen[$candidate] = true;
    return $candidate;
}

function build_instance(string $root, string $baseDir, array &$latestCache, array &$seenNames): array
{
    $name = instance_name($root, $baseDir, $seenNames);
    try {
        $installed = read_installed_version($root);
        $latest = latest_core_version($installed, $latestCache);
        return [
            'name' => $name,
            'path' => $root,
            'core_status' => core_status($installed, $latest),
            'core_version' => $installed,
            'core_new_version' => $latest,
        ];
    } catch (Throwable $error) {
        return [
            'name' => $name,
            'path' => $root,
            'core_status' => 3,
            'core_version' => '',
            'core_new_version' => '',
            'error' => $error->getMessage(),
        ];
    }
}

$config = load_config();
$instances = [];
try {
    $roots = find_wordpress_roots($config['BASEDIR'], $config['SEARCH_STRING']);
    $latestCache = [];
    $seenNames = [];
    foreach ($roots as $root) {
        $instances[] = build_instance($root, $config['BASEDIR'], $latestCache, $seenNames);
    }
    $payload = ['instances' => $instances];
} catch (Throwable $error) {
    $payload = [
        'instances' => [],
        'error' => $error->getMessage(),
    ];
}

echo "<<<wordpress_instances:sep(0)>>>", PHP_EOL;
echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), PHP_EOL;
