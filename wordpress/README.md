# Wordpress Instance Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0p1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p8-blue)
<!-- compatibility-badges:end -->

Monitors the installed WordPress core version of every WordPress installation found on a Linux host.

The agent plug-in is intentionally read-only and does **not** include `wp-load.php`, connect to the WordPress database, or execute WordPress core, plug-in, theme, must-use plug-in, or drop-in code. It reads the installed version statically from `wp-includes/version.php` and queries the official WordPress version-check API over verified HTTPS.

## How it works

1. The bakery deploys `wp_instances.php` and a `wp_instances.cfg` file containing `BASEDIR` and `SEARCH_STRING`.
2. The PHP agent performs a bounded directory scan under `BASEDIR`, follows each real directory only once, and selects `wp-load.php` files whose path contains `SEARCH_STRING`.
3. For every installation, it reads `$wp_version` from `wp-includes/version.php` as text. No WordPress PHP file is executed.
4. The installed version is compared with the latest version returned by `https://api.wordpress.org/core/version-check/1.7/`.
5. One JSON record per installation is emitted under the `<<<wordpress_instances:sep(0)>>>` section.
6. Checkmk discovers one `Wordpress Core <instance>` service per installation.

The core-status logic is:

- `0`: installed version is current — OK
- `1`: patch update available — WARN
- `2`: major or minor update available — CRIT
- `3`: version or API status could not be determined — UNKNOWN

## Package contents

| Path | Purpose |
| --- | --- |
| `src/agents/plugins/wp_instances.php` | Read-only Linux agent plug-in that locates WordPress installations and emits JSON. |
| `src/wordpress/agent_based/bakery.py` | Bakery hook that deploys the agent plug-in and configuration. |
| `src/wordpress/agent_based/wp_instances.py` | Section parser and Checkmk check plug-in. |
| `src/wordpress/rulesets/bakery.py` | Agent Bakery rule *Wordpress Monitoring (Linux)*. |

## Installation

1. Install the MKP on the Checkmk site.
2. Ensure PHP is installed on the monitored Linux host.
3. Deploy the plug-in with the Agent Bakery rule, or copy `wp_instances.php` into the agent plug-in directory and create `${MK_CONFDIR}/wp_instances.cfg`.
4. Run service discovery.

The PHP cURL extension is preferred. When it is unavailable, the plug-in uses PHP stream wrappers with peer and hostname verification enabled. The plug-in requires outbound HTTPS access to `api.wordpress.org` to determine whether an update is available.

## Configuration

WATO rule: *Setup > Agents > Agent rules > Wordpress Monitoring (Linux)*.

| Parameter | Default | Meaning |
| --- | --- | --- |
| `deployment` | `cached` | Run synchronously, asynchronously at the selected interval, or do not deploy. |
| `base_dir` | `/var/www/sites.d` | Root directory below which WordPress installations are searched. |
| `search_string` | `deploy/current` | Optional substring that must occur in the discovered `wp-load.php` path. Use an empty value to accept every installation below the base directory. |

The agent accepts the historical misspelled key `SEACH_STRING` for existing manually created configuration files, but newly baked configurations use `SEARCH_STRING`.

## Security properties

- Does not execute WordPress application code.
- Does not read `wp-config.php` or database credentials.
- Does not invoke `locate`, a shell, or commands built from configured paths.
- Limits the directory scan to 100,000 entries.
- Uses a 10-second API timeout and verifies TLS certificates.
- Reports API or parsing failures as UNKNOWN instead of silently reporting OK.
