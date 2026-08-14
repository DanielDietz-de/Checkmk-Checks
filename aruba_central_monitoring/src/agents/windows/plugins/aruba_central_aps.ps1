#requires -Version 5.1
<#
.SYNOPSIS
    Checkmk agent plug-in for Aruba Central access points.
.DESCRIPTION
    Executes `cencli show aps -v --json`, detects whether JSON and diagnostic
    lines were written to stdout or stderr, normalizes the selected fields, and
    emits one collector section plus one piggyback section per access point.

    The Checkmk Windows agent must execute this plug-in asynchronously because
    a full Aruba Central query typically takes around 30 seconds. See the
    bundled check_mk.user.yml example.
#>

[CmdletBinding()]
param(
    [string]$ConfigFile = $(
        if ($env:MK_CONFDIR) { Join-Path $env:MK_CONFDIR 'aruba_central_aps.json' }
        else { 'C:\ProgramData\checkmk\agent\config\aruba_central_aps.json' }
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SectionHeader = '<<<aruba_central_aps:sep(0)>>>'
$PiggybackEnd = '<<<<>>>>'

function Get-DefaultConfig {
    $programData = if ($env:ProgramData) { $env:ProgramData } else { 'C:\ProgramData' }
    return [ordered]@{
        CencliPath             = 'cencli.exe'
        CencliPrefixArguments  = ''
        CencliSuffixArguments  = ''
        TimeoutSeconds         = 60
        LastGoodCacheFile      = Join-Path $programData 'checkmk\agent\cache\aruba_central_aps.last_good.json'
        MaxStaleSeconds        = 1800
        EmitPiggyback          = $true
    }
}

function Read-Configuration {
    param([string]$Path)

    $config = Get-DefaultConfig
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $config
    }

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $loaded = $raw | ConvertFrom-Json
    foreach ($property in $loaded.PSObject.Properties) {
        if ($config.Contains($property.Name)) {
            $config[$property.Name] = $property.Value
        }
    }

    $config.TimeoutSeconds = [Math]::Max(1, [int]$config.TimeoutSeconds)
    $config.MaxStaleSeconds = [Math]::Max(0, [int]$config.MaxStaleSeconds)
    $config.EmitPiggyback = [bool]$config.EmitPiggyback
    return $config
}

function Protect-Message {
    param([AllowEmptyString()][string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $value = $Text -replace '[\r\n\t]+', ' '
    $value = $value -replace '(?i)(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+', '$1=<redacted>'
    if ($value.Length -gt 800) { $value = $value.Substring(0, 800) + '...' }
    return $value.Trim()
}

function Find-JsonObject {
    param([AllowEmptyString()][string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    for ($start = 0; $start -lt $Text.Length; $start++) {
        if ($Text[$start] -ne '{') { continue }
        $depth = 0
        $inString = $false
        $escaped = $false
        for ($index = $start; $index -lt $Text.Length; $index++) {
            $character = $Text[$index]
            if ($inString) {
                if ($escaped) { $escaped = $false; continue }
                if ($character -eq '\') { $escaped = $true; continue }
                if ($character -eq '"') { $inString = $false }
                continue
            }
            if ($character -eq '"') { $inString = $true; continue }
            if ($character -eq '{') { $depth++ }
            elseif ($character -eq '}') {
                $depth--
                if ($depth -eq 0) {
                    $candidate = $Text.Substring($start, $index - $start + 1)
                    try {
                        $object = $candidate | ConvertFrom-Json
                        return [pscustomobject]@{ Object = $object; Text = $candidate }
                    }
                    catch { break }
                }
            }
        }
    }
    return $null
}

function Invoke-Cencli {
    param([System.Collections.IDictionary]$Config)

    $arguments = @()
    if (-not [string]::IsNullOrWhiteSpace([string]$Config.CencliPrefixArguments)) {
        $arguments += [string]$Config.CencliPrefixArguments
    }
    $arguments += 'show aps -v --json'
    if (-not [string]::IsNullOrWhiteSpace([string]$Config.CencliSuffixArguments)) {
        $arguments += [string]$Config.CencliSuffixArguments
    }

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = [string]$Config.CencliPath
    $startInfo.Arguments = ($arguments -join ' ')
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $startedAt = [DateTimeOffset]::UtcNow
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) { throw 'Unable to start cencli' }

    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit([int]$Config.TimeoutSeconds * 1000)) {
        try { $process.Kill() } catch { }
        throw "cencli timed out after $($Config.TimeoutSeconds) seconds"
    }
    $stdout = $stdoutTask.Result
    $stderr = $stderrTask.Result
    $stopwatch.Stop()

    $stdoutJson = Find-JsonObject -Text $stdout
    $stderrJson = Find-JsonObject -Text $stderr
    $jsonResult = $null
    $jsonStream = 'none'
    if ($null -ne $stdoutJson) { $jsonResult = $stdoutJson; $jsonStream = 'stdout' }
    elseif ($null -ne $stderrJson) { $jsonResult = $stderrJson; $jsonStream = 'stderr' }
    else {
        $combinedJson = Find-JsonObject -Text ($stdout + "`n" + $stderr)
        if ($null -ne $combinedJson) { $jsonResult = $combinedJson; $jsonStream = 'combined' }
    }

    if ($process.ExitCode -ne 0) {
        throw "cencli exited with code $($process.ExitCode): $(Protect-Message ($stderr + ' ' + $stdout))"
    }
    if ($null -eq $jsonResult) {
        throw "cencli returned no parseable JSON; stdout=$(Protect-Message $stdout); stderr=$(Protect-Message $stderr)"
    }

    return [pscustomobject]@{
        Object          = $jsonResult.Object
        Stdout          = $stdout
        Stderr          = $stderr
        JsonStream      = $jsonStream
        DurationSeconds = [Math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        GeneratedAt     = $startedAt.ToString('o')
    }
}

function Get-ObjectProperty {
    param($Object, [string]$Name, $Default = $null)
    if ($null -eq $Object) { return $Default }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) { return $Default }
    return $property.Value
}

function Convert-ToNumber {
    param($Value)
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    $normalized = ([string]$Value).Trim() -replace '%$', ''
    $number = 0.0
    if ([double]::TryParse($normalized, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$number)) {
        return $number
    }
    return $null
}

function Convert-ToMegabytes {
    param($Value)
    if ($null -eq $Value) { return $null }
    $match = [regex]::Match(([string]$Value).Trim(), '^(?<n>[0-9]+(?:\.[0-9]+)?)\s*(?<u>KB|MB|GB|TB)?$', 'IgnoreCase')
    if (-not $match.Success) { return $null }
    $number = [double]::Parse($match.Groups['n'].Value, [Globalization.CultureInfo]::InvariantCulture)
    switch ($match.Groups['u'].Value.ToUpperInvariant()) {
        'KB' { return [Math]::Round($number / 1024, 2) }
        'GB' { return [Math]::Round($number * 1024, 2) }
        'TB' { return [Math]::Round($number * 1048576, 2) }
        default { return [Math]::Round($number, 2) }
    }
}

function Convert-UptimeSeconds {
    param($Value)
    $total = 0L
    $found = $false
    foreach ($match in [regex]::Matches(([string]$Value).ToLowerInvariant(), '(\d+)\s*([wdhms])')) {
        $found = $true
        $factor = switch ($match.Groups[2].Value) {
            'w' { 604800 }
            'd' { 86400 }
            'h' { 3600 }
            'm' { 60 }
            default { 1 }
        }
        $total += [long]$match.Groups[1].Value * $factor
    }
    if ($found) { return $total }
    return $null
}

function Convert-ToHostName {
    param([string]$Name, [string]$Mac, [string]$Serial)

    $compactMac = ($Mac -replace '[^A-Fa-f0-9]', '').ToUpperInvariant()
    $compactName = ($Name -replace '[^A-Fa-f0-9]', '').ToUpperInvariant()
    $nameIsMac = -not [string]::IsNullOrWhiteSpace($Name) -and $compactName -eq $compactMac
    $candidate = if ([string]::IsNullOrWhiteSpace($Name) -or $nameIsMac) {
        if (-not [string]::IsNullOrWhiteSpace($Serial)) { "AP_$Serial" }
        elseif ($compactMac) { "AP_$compactMac" }
        else { 'AP_unknown' }
    }
    else { $Name }
    $safe = ($candidate -replace '[^A-Za-z0-9_.-]+', '_').Trim('_')
    if ($safe) { return $safe }
    return 'AP_unknown'
}

function Assert-UniqueHostNames {
    param($AccessPoints)

    # PowerShell hashtables compare string keys case-insensitively by default,
    # matching the conservative collision semantics used by the synchronizer.
    $seen = @{}
    foreach ($ap in @($AccessPoints)) {
        $hostName = [string](Get-ObjectProperty $ap 'host_name' '')
        if ([string]::IsNullOrWhiteSpace($hostName)) {
            throw 'Aruba AP produced an empty piggyback host name'
        }
        $serial = [string](Get-ObjectProperty $ap 'serial' '')
        $mac = [string](Get-ObjectProperty $ap 'mac' '')
        $identity = "serial=$serial mac=$mac"
        if ($seen.ContainsKey($hostName)) {
            throw "Duplicate Aruba AP piggyback host name '$hostName' for identities '$($seen[$hostName])' and '$identity'; refusing to emit ambiguous piggyback data"
        }
        $seen[$hostName] = $identity
    }
}

function Convert-Radio {
    param($Radio, [int]$Index)
    return [ordered]@{
        index         = [int](Get-ObjectProperty $Radio 'index' $Index)
        radio_name    = [string](Get-ObjectProperty $Radio 'radio_name' "Radio $Index")
        radio_type    = [string](Get-ObjectProperty $Radio 'radio_type' '')
        band          = Get-ObjectProperty $Radio 'band' $null
        channel       = [string](Get-ObjectProperty $Radio 'channel' '')
        status        = [string](Get-ObjectProperty $Radio 'status' 'Unknown')
        tx_power      = Convert-ToNumber (Get-ObjectProperty $Radio 'tx_power' $null)
        utilization   = Convert-ToNumber (Get-ObjectProperty $Radio 'utilization' $null)
        spatial_stream = [string](Get-ObjectProperty $Radio 'spatial_stream' '')
        macaddr       = [string](Get-ObjectProperty $Radio 'macaddr' '')
    }
}

function Convert-AccessPoint {
    param([string]$Key, $Raw)

    $mac = [string](Get-ObjectProperty $Raw 'mac' $Key)
    $serial = [string](Get-ObjectProperty $Raw 'serial' '')
    $name = [string](Get-ObjectProperty $Raw 'name' (Get-ObjectProperty $Raw 'ap_name' ''))
    $radios = @()
    $rawRadios = Get-ObjectProperty $Raw 'radios' @()
    $index = 0
    foreach ($radio in @($rawRadios)) {
        if ($null -ne $radio) { $radios += Convert-Radio -Radio $radio -Index $index }
        $index++
    }

    $uptime = [string](Get-ObjectProperty $Raw 'uptime' '')
    return [ordered]@{
        host_name      = Convert-ToHostName -Name $name -Mac $mac -Serial $serial
        name           = $name
        status         = [string](Get-ObjectProperty $Raw 'status' 'Unknown')
        type           = [string](Get-ObjectProperty $Raw 'type' 'ap')
        model          = [string](Get-ObjectProperty $Raw 'model' '')
        clients        = [int](Get-ObjectProperty $Raw 'client1' (Get-ObjectProperty $Raw 'clients' 0))
        ip             = [string](Get-ObjectProperty $Raw 'ip' '')
        mac            = $mac
        serial         = $serial
        group          = [string](Get-ObjectProperty $Raw 'group' 'Unassigned')
        site           = [string](Get-ObjectProperty $Raw 'site' 'Unassigned')
        uptime         = $uptime
        uptime_seconds = Convert-UptimeSeconds $uptime
        cpu_percent    = Convert-ToNumber (Get-ObjectProperty $Raw 'cpu_%' (Get-ObjectProperty $Raw 'cpu_percent' $null))
        mem_total_mb   = Convert-ToMegabytes (Get-ObjectProperty $Raw 'mem_total' $null)
        mem_free_mb    = Convert-ToMegabytes (Get-ObjectProperty $Raw 'mem_free' $null)
        version        = [string](Get-ObjectProperty $Raw 'version' '')
        ssid_count     = Get-ObjectProperty $Raw 'ssid_count' $null
        sleep_status   = [bool](Get-ObjectProperty $Raw 'sleep_status' $false)
        radios         = $radios
    }
}

function Get-AccessPoints {
    param($Root)
    $result = @()
    foreach ($property in $Root.PSObject.Properties) {
        if ($null -eq $property.Value) { continue }
        $deviceType = [string](Get-ObjectProperty $property.Value 'type' 'ap')
        if ($deviceType -ne 'ap') { continue }
        $result += Convert-AccessPoint -Key $property.Name -Raw $property.Value
    }
    return @($result)
}

function Find-DiagnosticMatch {
    param([string]$Stdout, [string]$Stderr, [string]$Pattern)

    $stdoutMatch = [regex]::Match($Stdout, $Pattern, 'IgnoreCase')
    $stderrMatch = [regex]::Match($Stderr, $Pattern, 'IgnoreCase')
    if ($stdoutMatch.Success -and $stderrMatch.Success) {
        return [pscustomobject]@{ Match = $stdoutMatch; Stream = 'both' }
    }
    if ($stdoutMatch.Success) {
        return [pscustomobject]@{ Match = $stdoutMatch; Stream = 'stdout' }
    }
    if ($stderrMatch.Success) {
        return [pscustomobject]@{ Match = $stderrMatch; Stream = 'stderr' }
    }
    return [pscustomobject]@{ Match = [regex]::Match('', $Pattern); Stream = 'none' }
}

function Get-Diagnostics {
    param([string]$Stdout, [string]$Stderr, $AccessPoints)
    $countResult = Find-DiagnosticMatch -Stdout $Stdout -Stderr $Stderr -Pattern 'Counts:\s*ap:\s*(\d+)\s*\((\d+)\s*:\s*(\d+)\)\s*,\s*clients:\s*(\d+)'
    $rateResult = Find-DiagnosticMatch -Stdout $Stdout -Stderr $Stderr -Pattern 'API\s+Rate\s+Limit:\s*(\d+)\s+of\s+(\d+)\s+remaining'
    $countMatch = $countResult.Match
    $rateMatch = $rateResult.Match

    $apTotal = @($AccessPoints).Count
    $apUp = @($AccessPoints | Where-Object { $_.status -eq 'Up' }).Count
    $apDown = $apTotal - $apUp
    $clients = ($AccessPoints | Measure-Object -Property clients -Sum).Sum
    if ($null -eq $clients) { $clients = 0 }
    if ($countMatch.Success) {
        $apTotal = [int]$countMatch.Groups[1].Value
        $apUp = [int]$countMatch.Groups[2].Value
        $apDown = [int]$countMatch.Groups[3].Value
        $clients = [int]$countMatch.Groups[4].Value
    }
    else {
        $countResult.Stream = 'derived'
    }

    return [ordered]@{
        ap_total           = $apTotal
        ap_up              = $apUp
        ap_down            = $apDown
        clients_total      = [int]$clients
        api_rate_remaining = if ($rateMatch.Success) { [int]$rateMatch.Groups[1].Value } else { $null }
        api_rate_limit     = if ($rateMatch.Success) { [int]$rateMatch.Groups[2].Value } else { $null }
        counts_stream      = $countResult.Stream
        rate_limit_stream  = $rateResult.Stream
    }
}

function Write-AtomicJson {
    param([string]$Path, $Value)
    $directory = Split-Path -Parent $Path
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $temporary = "$Path.tmp.$PID"
    $Value | ConvertTo-Json -Depth 20 -Compress | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Read-LastGood {
    param([string]$Path, [int]$MaxAgeSeconds)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try {
        $cache = (Get-Content -LiteralPath $Path -Raw -Encoding UTF8) | ConvertFrom-Json
        $savedAt = [DateTimeOffset]::Parse([string]$cache.saved_at)
        $age = [Math]::Max(0, [int]([DateTimeOffset]::UtcNow - $savedAt).TotalSeconds)
        if ($age -gt $MaxAgeSeconds) { return $null }
        return [pscustomobject]@{ Cache = $cache; Age = $age }
    }
    catch { return $null }
}

function Write-SectionJson {
    param($Value)
    Write-Output $SectionHeader
    Write-Output ($Value | ConvertTo-Json -Depth 20 -Compress)
}

function Write-MonitoringOutput {
    param($Collector, $AccessPoints, [bool]$EmitPiggyback)
    Write-SectionJson ([ordered]@{ schema = 1; kind = 'collector'; collector = $Collector })
    if (-not $EmitPiggyback) { return }
    foreach ($ap in @($AccessPoints | Sort-Object host_name)) {
        Write-Output "<<<<$($ap.host_name)>>>>"
        Write-SectionJson ([ordered]@{ schema = 1; kind = 'ap'; ap = $ap; collector = [ordered]@{ generated_at = $Collector.generated_at; stale = $Collector.stale; last_success_age_seconds = $Collector.last_success_age_seconds } })
        Write-Output $PiggybackEnd
    }
}

$config = Get-DefaultConfig
try {
    $config = Read-Configuration -Path $ConfigFile
    $execution = Invoke-Cencli -Config $config
    $accessPoints = Get-AccessPoints -Root $execution.Object
    Assert-UniqueHostNames -AccessPoints $accessPoints
    $diagnostics = Get-Diagnostics -Stdout $execution.Stdout -Stderr $execution.Stderr -AccessPoints $accessPoints
    $collector = [ordered]@{
        status                   = 'OK'
        message                  = "Counts: ap: $($diagnostics.ap_total) ($($diagnostics.ap_up):$($diagnostics.ap_down)), clients: $($diagnostics.clients_total)"
        generated_at             = $execution.GeneratedAt
        stale                    = $false
        last_success_age_seconds = 0
        refresh_duration_seconds = $execution.DurationSeconds
        json_stream              = $execution.JsonStream
        counts_stream            = $diagnostics.counts_stream
        rate_limit_stream        = $diagnostics.rate_limit_stream
        ap_total                 = $diagnostics.ap_total
        ap_up                    = $diagnostics.ap_up
        ap_down                  = $diagnostics.ap_down
        clients_total            = $diagnostics.clients_total
        api_rate_remaining       = $diagnostics.api_rate_remaining
        api_rate_limit           = $diagnostics.api_rate_limit
    }
    Write-AtomicJson -Path ([string]$config.LastGoodCacheFile) -Value ([ordered]@{ saved_at = [DateTimeOffset]::UtcNow.ToString('o'); access_points = $accessPoints; collector = $collector })
    Write-MonitoringOutput -Collector $collector -AccessPoints $accessPoints -EmitPiggyback ([bool]$config.EmitPiggyback)
}
catch {
    $message = Protect-Message $_.Exception.Message
    $lastGood = Read-LastGood -Path ([string]$config.LastGoodCacheFile) -MaxAgeSeconds ([int]$config.MaxStaleSeconds)
    if ($null -ne $lastGood) {
        $cachedCollector = $lastGood.Cache.collector
        $collector = [ordered]@{
            status                   = 'ERROR'
            message                  = "$message; using last-known-good AP data"
            generated_at             = [DateTimeOffset]::UtcNow.ToString('o')
            stale                    = $true
            last_success_age_seconds = $lastGood.Age
            refresh_duration_seconds = $null
            json_stream              = 'none'
            counts_stream            = 'none'
            rate_limit_stream        = 'none'
            ap_total                 = [int](Get-ObjectProperty $cachedCollector 'ap_total' 0)
            ap_up                    = [int](Get-ObjectProperty $cachedCollector 'ap_up' 0)
            ap_down                  = [int](Get-ObjectProperty $cachedCollector 'ap_down' 0)
            clients_total            = [int](Get-ObjectProperty $cachedCollector 'clients_total' 0)
            api_rate_remaining       = Get-ObjectProperty $cachedCollector 'api_rate_remaining' $null
            api_rate_limit           = Get-ObjectProperty $cachedCollector 'api_rate_limit' $null
        }
        Write-MonitoringOutput -Collector $collector -AccessPoints @($lastGood.Cache.access_points) -EmitPiggyback ([bool]$config.EmitPiggyback)
    }
    else {
        $collector = [ordered]@{
            status                   = 'ERROR'
            message                  = $message
            generated_at             = [DateTimeOffset]::UtcNow.ToString('o')
            stale                    = $true
            last_success_age_seconds = $null
            refresh_duration_seconds = $null
            json_stream              = 'none'
            counts_stream            = 'none'
            rate_limit_stream        = 'none'
            ap_total                 = 0
            ap_up                    = 0
            ap_down                  = 0
            clients_total            = 0
            api_rate_remaining       = $null
            api_rate_limit           = $null
        }
        Write-MonitoringOutput -Collector $collector -AccessPoints @() -EmitPiggyback $false
    }
}
