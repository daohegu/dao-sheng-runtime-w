#Requires -Version 5.1
<#
DaoSheng Installation Layer - single entry point (Deployment/Installation Layer, L4).

Contract: docs/deployment/INSTALLATION_CONTRACT.md (persistent task state;
re-read it first after any context-compaction recovery).

Entries:
  .\dao-sheng.ps1 install   check env, fill missing runtime, prepare standard
                            directories, verify install (the ONLY writable entry
                            for the installation layer; NEVER writes any inventory
                            item -- identity/faculties stay design-layer owned)
  .\dao-sheng.ps1 status    show current install/runtime state (read-only)
  .\dao-sheng.ps1 doctor    read-only health check: [OK]/[FAIL] per check,
                            final line "Result: PASS" or "Result: FAIL"
  .\dao-sheng.ps1 init-role      design-layer initialization entry: create
                                 identity.json + faculties.json for a FRESH
                                 instance only (refuses when either carrier
                                 already exists; never overwrites)
  .\dao-sheng.ps1 configure-role design-layer modification entry: edit an
                                 existing identity.json field-by-field (faculties
                                 / continuity / memory untouched)
  .\dao-sheng.ps1 migrate-data   explicit one-time relocation of legacy
                                 personal data found INSIDE the repository
                                 (instances/ config/ log/) into the external
                                 data home (refuses when any target already
                                 exists; never overwrites; SHA256-verified)

Optional: -InstanceRoot <path>  (default: <data home>\instances\default;
          relative paths resolve against the data home; a resolved root
          inside the repository worktree is refused)

Data home (ALL mutable personal runtime data, OUTSIDE the Git worktree):
  default : %LOCALAPPDATA%\DaoSheng  (fallback %USERPROFILE%\AppData\Local\DaoSheng)
  override: DAO_SHENG_DATA_HOME (resolved identically by run_dao_sheng.py)
  layout  : <data home>\instances\default\  identity.json / faculties.json /
            continuity.jsonl / memory/ / capabilities/
            <data home>\config\  install-state.json (and model/host config)
            <data home>\log\
  A data home or -InstanceRoot resolving INSIDE the repository is refused
  fail-loud by every entry. Plain source upgrades (git pull) then have no
  personal-data path in the worktree to overwrite.

Frozen-DaoSheng-Core rule (contract section 0): this file plus the machine-
local directories (.venv/ in the repository; personal runtime data under the
external data home) are the ENTIRE installation system. No Python module is
added to dao_sheng/. The Core (dao_sheng/, tests/) is never modified by this
entry point.

Note: this file is intentionally ASCII-only (PowerShell 5.1 reads BOM-less
.ps1 files as ANSI; non-ASCII characters would be mangled).
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("install", "status", "doctor", "init-role", "configure-role", "migrate-data")]
    [string]$Command = "",

    [string]$InstanceRoot = "",

    # Role-entry values (init-role / configure-role only; install never
    # reads them). PowerShell's native binder binds only the first bare
    # token after a named array parameter, but the CLI contract here is
    # space-separated multi-value lists (e.g. -BehavioralHabits a b). Role
    # values are therefore collected raw here (probe-verified: declared
    # parameters such as -InstanceRoot still bind normally and never land
    # in $RoleArgs) and parsed manually by Parse-RoleArgs below.
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RoleArgs = @()
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
# $script:DataHome / $script:ResolvedInstanceRoot / $script:StateFile are
# computed by the central guard near the end of this file (before any entry
# runs), NOT here: they depend on environment resolution and the
# inside-repository refusal.

$script:docChecks = 0
$script:docFailed = 0

function Write-Usage {
    Write-Host "Usage: .\dao-sheng.ps1 <install|status|doctor|init-role|configure-role|migrate-data> [-InstanceRoot <path>]"
    Write-Host "  install        : check env, fill missing runtime, verify install (never writes any inventory item)"
    Write-Host "  init-role      : create identity.json + faculties.json on a FRESH instance (refuses if either exists)"
    Write-Host "  configure-role : edit an existing identity.json field-by-field (faculties/continuity/memory untouched)"
    Write-Host "  migrate-data   : move legacy in-repo personal data (instances/ config/ log/) to the data home (never overwrites)"
    Write-Host "data home        : %LOCALAPPDATA%\DaoSheng (override: DAO_SHENG_DATA_HOME); -InstanceRoot defaults to <data home>\instances\default"
}

function Fail-Step([string]$Object, [string]$Expected, [string]$Current, [string]$Fix) {
    Write-Host "[FAIL] $Object"
    Write-Host "       expected : $Expected"
    Write-Host "       current  : $Current"
    Write-Host "       fix      : $Fix"
    exit 1
}

function Resolve-DataHome {
    # Single source of truth for the personal-data root. Mirrors
    # run_dao_sheng.py resolve_data_home() exactly: DAO_SHENG_DATA_HOME
    # override (trimmed; '~' expanded via USERPROFILE; relative resolved
    # against the current directory), else %LOCALAPPDATA%\DaoSheng with a
    # %USERPROFILE%\AppData\Local\DaoSheng fallback. GetFullPath matches
    # Python normalization (no symlink resolution) AND expands 8.3 short
    # names of existing components to long names; run_dao_sheng.py
    # _expand_short_names() mirrors this via GetLongPathNameW (runner
    # TEMP is C:\Users\RUNNER~1\... while PowerShell reports
    # C:\Users\runneradmin\...). MEASURED CAVEAT (PS 5.1): for the shape
    # "existing 8.3 short component + missing leaf" GetFullPath's output
    # text is call-order dependent within one process (calling the child
    # path first -> long form; a parent GetFullPath call first -> short
    # form), so raw text parity is only guaranteed for fully existing
    # paths. The inside-repo decision is kept safe-identical across both
    # runtimes for every shape by Test-PathInsideRepo's walk-up
    # canonicalization (Get-CanonicalPathForComparison, see below).
    $raw = $env:DAO_SHENG_DATA_HOME
    if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $value = $raw.Trim()
        if ($value.StartsWith("~")) {
            $profile = $env:USERPROFILE
            if ([string]::IsNullOrWhiteSpace($profile)) {
                Fail-Step "DAO_SHENG_DATA_HOME" "an absolute path, or a '~'-prefixed path resolvable via USERPROFILE" "USERPROFILE unavailable for '~' expansion" "Set DAO_SHENG_DATA_HOME to an absolute path outside the repository; nothing was written"
            }
            $value = $profile + $value.Substring(1)
        }
        if (-not [System.IO.Path]::IsPathRooted($value)) {
            $value = Join-Path (Get-Location).Path $value
        }
        return [System.IO.Path]::GetFullPath($value)
    }
    $base = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($base)) {
        $profile = $env:USERPROFILE
        if ([string]::IsNullOrWhiteSpace($profile)) {
            Fail-Step "data home" "LOCALAPPDATA (or USERPROFILE) available for the default data home" "neither is available" "Set DAO_SHENG_DATA_HOME to an absolute path outside the repository; nothing was written"
        }
        $base = Join-Path $profile "AppData\Local"
    }
    return [System.IO.Path]::GetFullPath((Join-Path $base "DaoSheng"))
}

function Test-PathExistsForComparison {
    param([string]$Path)
    # Tri-state existence probe for the walk-up canonicalization below.
    #   $true  -> the path exists;
    #   $false -> DEFINITIVELY missing (Win32 ERROR_FILE_NOT_FOUND /
    #             ERROR_PATH_NOT_FOUND, surfaced by .NET as
    #             FileNotFoundException / DirectoryNotFoundException);
    #   throw  -> every other failure: access denied
    #             (UnauthorizedAccessException), unexpected IO error,
    #             unavailable drive or unreachable UNC share root
    #             (IOException, e.g. ERROR_BAD_NETPATH). Such a failure
    #             is NOT "missing" and must never be walked up past.
    # MEASURED on PS 5.1 / Windows 11 26100 (2026-10-15): missing leaf ->
    # FileNotFoundException; missing intermediate -> DirectoryNotFound-
    # Exception; nonexistent drive letter (Z:\ and Z:\Missing) ->
    # DirectoryNotFoundException (definitively missing -- but the walk-up
    # must NOT keep such an input verbatim: reaching an unverified ROOT is
    # fail-loud, see Get-CanonicalPathForComparison); unreachable host UNC
    # (full path AND the share root itself) and a missing share on a
    # reachable host (\\127.0.0.1\share...) -> IOException "network path
    # was not found"; bare server name (\\server) -> ArgumentException;
    # traversal-blocked path -> UnauthorizedAccessException.
    # Test-Path returns $false for ALL of these -- exactly the conflation
    # this probe replaces.
    # Injectable seam (tests only): a session/script-scoped
    # $DaoShengPathExistsProbe scriptblock replaces the real probe so
    # tests can drive the PRODUCTION walk-up helper with each failure
    # classification without machine-specific ACL setups. Production
    # never sets this variable.
    if ($DaoShengPathExistsProbe) { return & $DaoShengPathExistsProbe $Path }
    try {
        [void][System.IO.File]::GetAttributes($Path)
        return $true
    } catch [System.IO.FileNotFoundException] { return $false }
    catch [System.IO.DirectoryNotFoundException] { return $false }
    catch {
        $inner = $_.Exception
        while ($inner.InnerException) { $inner = $inner.InnerException }
        throw [System.InvalidOperationException]::new(
            ("existence probe failed for '" + $Path + "' (" + $inner.GetType().Name + ": " + $inner.Message + "); " +
             "access denied / IO error / unavailable drive or UNC root is not 'missing' and was not treated as such"),
            $_.Exception)
    }
}

function Get-CanonicalPathForComparison {
    param([string]$Path)
    # Canonical text for containment comparison: walk up to the longest
    # existing prefix, expand it via GetFullPath (8.3 components -> long
    # names), then re-append the missing tail verbatim. Mirrors
    # run_dao_sheng.py _expand_short_names(). Plain GetFullPath alone is
    # NOT reliable for containment: measured on PS 5.1, its output for
    # "existing short component + missing leaf" depends on prior calls in
    # the same process (child-first -> long form; parent-first -> short
    # form), so a short-form component could slip through a raw-text
    # comparison. Canonicalizing BOTH sides through this walk-up expands
    # every EXISTING component regardless of call order, keeping the
    # inside-repo decision identical to the Python side.
    # The walk-up steps ONLY over components Test-PathExistsForComparison
    # reports as DEFINITIVELY missing. An access-denied, IO-error or
    # unexpected failure throws out of the probe and aborts
    # canonicalization fail-loud: such a path is never treated as "does
    # not exist" and never walked up past. If the walk-up reaches a ROOT
    # (no parent) and the root itself is reported missing, the root is
    # unavailable -- a nonexistent drive root or a missing / unreachable
    # UNC share root -- which is NOT a normal missing component: fail loud
    # instead of returning the input verbatim (mirrors run_dao_sheng.py
    # _expand_short_names()). Normal new-directory paths on an EXISTING
    # drive terminate at a verified-existing component (at worst the drive
    # root itself) and are unaffected.
    $full = [System.IO.Path]::GetFullPath($Path)
    $tail = [System.Collections.Generic.List[string]]::new()
    $current = $full
    while (-not (Test-PathExistsForComparison $current)) {
        $parent = [System.IO.Path]::GetDirectoryName($current)
        if (-not $parent -or $parent -eq $current) {
            throw [System.InvalidOperationException]::new(
                ("root of '" + $full + "' ('" + $current + "') could not be " +
                 "verified as existing; unavailable drive root or missing / " +
                 "unreachable UNC share root is not a normal missing " +
                 "component and was not canonicalized verbatim"))
        }
        $tail.Add([System.IO.Path]::GetFileName($current))
        $current = $parent
    }
    $canonical = [System.IO.Path]::GetFullPath($current)
    for ($i = $tail.Count - 1; $i -ge 0; $i--) {
        $canonical = [System.IO.Path]::Combine($canonical, $tail[$i])
    }
    return $canonical
}

function Test-PathInsideRepo([string]$Path) {
    # True when $Path resolves to the repository worktree itself or a path
    # inside it (full normalization; case-insensitive comparison as on
    # Windows; mirrors run_dao_sheng.py _is_inside_repo()). BOTH sides go
    # through Get-CanonicalPathForComparison, so every EXISTING 8.3 short
    # component is expanded to its long name regardless of GetFullPath's
    # measured call-order dependence, and a short-form worktree vs a
    # long-form inside-repo path (or vice versa) is still detected.
    # TrimEnd + DirectorySeparatorChar builds a single-separator boundary:
    # when the repo root is a drive root the canonical text already ends
    # with one separator, and appending another would make direct children
    # of a drive-root repo miss the prefix (mirrors Python
    # root.rstrip(os.sep) + os.sep). Different drive letters can never be
    # prefixes of each other, so cross-drive paths are never misjudged.
    $full = (Get-CanonicalPathForComparison $Path).TrimEnd('\')
    $repo = (Get-CanonicalPathForComparison $RepoRoot).TrimEnd('\')
    if ($full -eq $repo) { return $true }
    return $full.StartsWith($repo + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
}

function Resolve-InstanceRoot([string]$Value) {
    # Instance roots resolve against the DATA HOME, never the repository:
    # empty -> <data home>\instances\default; absolute -> as given;
    # relative -> relative to the data home. A resolved path inside the
    # repository worktree is refused by the central guard below.
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return [System.IO.Path]::GetFullPath((Join-Path $script:DataHome "instances\default"))
    }
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $script:DataHome $Value))
}

function Find-LegacyRepoData {
    # Legacy personal-data carriers that older versions placed INSIDE the
    # repository (instances/ config/ log/). DETECTION ONLY -- this function
    # never moves, deletes, or modifies anything. Returns full file paths.
    $found = @()
    foreach ($rel in @("instances", "config", "log")) {
        $dir = Join-Path $RepoRoot $rel
        if (Test-Path $dir -PathType Container) {
            foreach ($file in @(Get-ChildItem -Path $dir -Recurse -File -Force)) {
                $found += $file.FullName
            }
        }
    }
    return $found
}

function Get-PythonVersion([string]$Exe) {
    $out = & $Exe -B -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    if ($null -eq $out) { return "" }
    return (($out -join " ") -replace "\s+", "").Trim()
}

function Find-Python {
    # venv preferred, then PATH: python, py. Returns hashtable or $null.
    if (Test-Path $VenvPython) {
        $v = Get-PythonVersion $VenvPython
        if ($v) { return @{ Exe = $VenvPython; Version = $v; Source = "venv" } }
    }
    foreach ($name in @("python", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -eq $cmd) { continue }
        $v = Get-PythonVersion $cmd.Source
        if ($v) { return @{ Exe = $cmd.Source; Version = $v; Source = "system ($name)" } }
    }
    return $null
}

function Test-PythonVersionOk([string]$Version, [string]$MinMajor, [string]$MinMinor) {
    # Explicit MINIMUM-version comparison (contract 2.1, long-term rule):
    # major > min -> ok; major == min -> minor >= min minor -> ok; below -> fail.
    # Never an equality pin: no "must be exactly some version" check exists
    # anywhere in this file (contract 2.1 prohibitions).
    if ($Version -notmatch "^(\d+)\.(\d+)") { return $false }
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -gt [int]$MinMajor) { return $true }
    return ($major -eq [int]$MinMajor) -and ($minor -ge [int]$MinMinor)
}

function Compare-VersionTuple([string]$Left, [string]$Right) {
    # Element-wise numeric compare of "major.minor" tuples (major dominates).
    $l = $Left -split "\."; $r = $Right -split "\."
    $n = [Math]::Max($l.Count, $r.Count)
    for ($i = 0; $i -lt $n; $i++) {
        $a = 0; if ($i -lt $l.Count) { $a = [int]$l[$i] }
        $b = 0; if ($i -lt $r.Count) { $b = [int]$r[$i] }
        if ($a -ne $b) { if ($a -gt $b) { return 1 } else { return -1 } }
    }
    return 0
}

function Get-PythonMinVersion {
    # MIN_SUPPORTED_PYTHON is DERIVED AT RUNTIME from the project's own formal
    # declaration: pyproject.toml [project] requires-python (contract 2.1).
    # The minimum version number is deliberately NOT written into this script.
    $py = Join-Path $RepoRoot "pyproject.toml"
    if (-not (Test-Path $py)) { return $null }
    $text = Get-Content -Path $py -Raw
    if ($text -notmatch "(?im)^[ \t]*requires-python[ \t]*=[ \t]*""(?<min>[^""]+)""") { return $null }
    if ($Matches['min'] -notmatch "(?im)^>=[ \t]*(\d+)\.(\d+)") { return $null }
    return "$($Matches[1]).$($Matches[2])"
}

function Test-ZeroExternalDeps {
    # M01 toolchain decision: V1 is stdlib-only. "Installing project
    # dependencies" therefore means VERIFYING pyproject declares none.
    $py = Join-Path $RepoRoot "pyproject.toml"
    if (-not (Test-Path $py)) { return $false }
    $text = Get-Content -Path $py -Raw
    return -not ($text -match "(?m)^\s*dependencies\s*=")
}

function Test-DaoShengImport([string]$Exe) {
    # -B: write no bytecode (keeps doctor strictly read-only).
    $prev = (Get-Location).Path
    Set-Location $RepoRoot
    try {
        $out = & $Exe -B -c "import dao_sheng, dao_sheng.composition; print('dao-sheng-import-ok')" 2>&1 | Out-String
    } finally {
        Set-Location $prev
    }
    return ($out -match "dao-sheng-import-ok")
}

function Get-InstanceState([string]$Root) {
    # 5-item persistent file inventory, positions per
    # dao_sheng/layout.py IndividualFiles.layout(root). Read-only.
    $items = [ordered]@{
        "identity"     = @{ Path = Join-Path $Root "identity.json";  Dir = $false }
        "faculties"    = @{ Path = Join-Path $Root "faculties.json"; Dir = $false }
        "continuity"   = @{ Path = Join-Path $Root "continuity.jsonl"; Dir = $false }
        "memory"       = @{ Path = Join-Path $Root "memory"; Dir = $true }
        "capabilities" = @{ Path = Join-Path $Root "capabilities"; Dir = $true }
    }
    $result = [ordered]@{}
    foreach ($name in $items.Keys) {
        $item = $items[$name]
        if ($item.Dir) { $result[$name] = (Test-Path $item.Path -PathType Container) }
        else { $result[$name] = (Test-Path $item.Path) }
    }
    return $result
}

function Write-InventoryLines([string]$Root, $State, [string]$Style) {
    $display = @{
        "identity" = "identity.json"; "faculties" = "faculties.json";
        "continuity" = "continuity.jsonl"; "memory" = "memory/"; "capabilities" = "capabilities/"
    }
    $notes = @{
        "identity"     = "initial: design-layer initialization required (compose fail-louds by design)"
        "faculties"    = "initial: design-layer initialization required (compose fail-louds by design)"
        "continuity"   = "initial: empty log (Core semantics)"
        "memory"       = "initial: Core self-creates on first use"
        "capabilities" = "initial: Core self-creates on first use"
    }
    foreach ($name in $State.Keys) {
        if ($State[$name]) {
            if ($Style -eq "install") {
                Write-Host "[OK] $Root\$($display[$name]) : kept (existing content preserved, untouched)"
            } else {
                Write-Host "  [present] $($display[$name])"
            }
        } else {
            if ($Style -eq "install") {
                Write-Host "[OK] $Root\$($display[$name]) : absent ($($notes[$name]))"
            } else {
                Write-Host "  [absent]  $($display[$name]) - $($notes[$name])"
            }
        }
    }
}

function Invoke-Install {
    $instanceRoot = $script:ResolvedInstanceRoot
    Write-Host "DaoSheng install"
    Write-Host "contract : docs/deployment/INSTALLATION_CONTRACT.md"
    Write-Host "repo     : $RepoRoot"
    Write-Host "data home: $script:DataHome"
    Write-Host "instance : $instanceRoot"
    Write-Host ""

    # 0. Legacy personal data inside the repository blocks install: the
    #    upgrade-safety rule is "no personal data in the Git worktree".
    $legacy = Find-LegacyRepoData
    if ($legacy.Count -gt 0) {
        $sample = (($legacy | Select-Object -First 3) -join ", ")
        Fail-Step "legacy personal data in repository" "no files under instances/ config/ log/ inside the repository worktree" ("found $($legacy.Count) file(s), e.g.: $sample") "Run: .\dao-sheng.ps1 migrate-data first (explicit, verified, never-overwriting relocation to the data home); install refuses while legacy data sits in the repository"
    }

    # 1. OS (Windows; PS 5.1 is Windows-only, PS7 elsewhere -> $IsWindows)
    if (($PSVersionTable.PSVersion.Major -ge 6) -and -not $IsWindows) {
        Fail-Step "Operating system" "Windows" "PowerShell $($PSVersionTable.PSVersion.Major) on non-Windows" "This is the Windows entry point; other platforms run the Core directly without this layer"
    }
    Write-Host "[OK] Operating system: Windows"

    # 2. Python discovery
    $py = Find-Python
    if ($null -eq $py) {
        Fail-Step "Python" "python discoverable (.venv preferred, then PATH python/py)" "not found" "Install a system Python >= MIN_SUPPORTED_PYTHON (python.org; see pyproject.toml requires-python) and re-run: .\dao-sheng.ps1 install"
    }
    Write-Host "[OK] Python $($py.Version) [$($py.Source)] $($py.Exe)"

    # 3. Version >= MIN_SUPPORTED_PYTHON (contract 2.1 long-term rule: the
    #    minimum is derived AT RUNTIME from pyproject.toml requires-python;
    #    explicit minimum comparison, never a fixed-version equality check)
    $minPy = Get-PythonMinVersion
    if ($null -eq $minPy) {
        Fail-Step "MIN_SUPPORTED_PYTHON" "parseable 'requires-python = '>=[N].N'' in pyproject.toml (contract 2.1)" "not found or not parseable" "Declare [project] requires-python in pyproject.toml (M01 toolchain decision), then re-run: .\dao-sheng.ps1 install"
    }
    $minParts = $minPy -split "\."
    if (-not (Test-PythonVersionOk $py.Version $minParts[0] $minParts[1])) {
        Fail-Step "Python version" ">= $minPy (MIN_SUPPORTED_PYTHON, pyproject.toml requires-python)" $py.Version "Install Python $minPy+ (python.org) and re-run: .\dao-sheng.ps1 install"
    }
    Write-Host "[OK] Python version >= $minPy (MIN_SUPPORTED_PYTHON from pyproject.toml)"

    # 4. .venv (create only if absent; existing kept as-is; never deleted)
    if (Test-Path $VenvPython) {
        Write-Host "[OK] .venv present (kept as-is)"
    } else {
        Write-Host "[..] creating .venv from $($py.Exe) ..."
        & $py.Exe -m venv (Join-Path $RepoRoot ".venv")
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
            Fail-Step ".venv creation" ".venv\Scripts\python.exe exists after 'python -m venv'" "creation failed (exit $LASTEXITCODE)" "Re-run: .\dao-sheng.ps1 install; if it persists, check the system Python installation"
        }
        Write-Host "[OK] .venv created"
    }
    $py = Find-Python

    # 5. Dependencies: M01 zero external deps -> verify, not pip-install
    if (-not (Test-ZeroExternalDeps)) {
        Fail-Step "pyproject.toml [project] dependencies" "no 'dependencies' key (M01: zero external dependencies)" "declared" "External deps conflict with the M01 toolchain decision; resolve via the RECONSTRUCTION.md decision flow first"
    }
    Write-Host "[OK] Dependencies: zero external dependencies verified (M01; nothing to pip-install)"

    # 6. Standard directories UNDER THE DATA HOME (create-only; -Force is
    #    idempotent; never delete/rebuild). Nothing is created in the repo.
    foreach ($dir in @("config", "log")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $script:DataHome $dir) | Out-Null
    }
    New-Item -ItemType Directory -Force -Path $instanceRoot | Out-Null
    Write-Host "[OK] Directories ready (data home): config/  log/  instance root ($instanceRoot)"

    # 7. Detect-then-keep: 5-item inventory (dao_sheng/layout.py).
    #    install NEVER writes any inventory item; the Core owns them.
    $state = Get-InstanceState $instanceRoot
    Write-InventoryLines $instanceRoot $state "install"

    # 8. Verify: Core imports via the venv python from the repo root
    if (-not (Test-DaoShengImport $py.Exe)) {
        Fail-Step "DaoSheng import" "import dao_sheng and dao_sheng.composition succeed" "import failed" "Run .\dao-sheng.ps1 install from the repository root; if it persists, run: python -m unittest discover -s tests"
    }
    Write-Host "[OK] DaoSheng import verified (venv python, repo root)"

    # 9. Install-layer metadata (install's OWN state file; Core never reads it)
    $meta = [ordered]@{
        "installed_at"   = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
        "python"         = $py.Exe
        "python_version" = $py.Version
        "instance_root"  = $instanceRoot
        "contract"       = "docs/deployment/INSTALLATION_CONTRACT.md"
    }
    # UTF-8 without BOM: the repo path may contain non-ASCII characters
    # (-Encoding ascii would corrupt them to '?').
    $json = $meta | ConvertTo-Json
    [System.IO.File]::WriteAllText($script:StateFile, $json, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[OK] install-state.json written: $script:StateFile"

    Write-Host ""
    Write-Host "install complete: OK (re-runnable: re-running keeps all existing instance content)"
    exit 0
}

function Invoke-Status {
    $instanceRoot = $script:ResolvedInstanceRoot
    Write-Host "DaoSheng status (read-only)"
    Write-Host ""
    Write-Host "repo          : $RepoRoot"
    Write-Host "data home     : $script:DataHome"
    $py = Find-Python
    if ($py) {
        Write-Host "python        : $($py.Version) [$($py.Source)] $($py.Exe)"
    } else {
        Write-Host "python        : not found (run: .\dao-sheng.ps1 install)"
    }
    $minPy = Get-PythonMinVersion
    if ($minPy) {
        Write-Host "min python    : >= $minPy (MIN_SUPPORTED_PYTHON, pyproject.toml requires-python)"
    } else {
        Write-Host "min python    : not declared (pyproject.toml requires-python missing or not parseable)"
    }
    if (Test-Path $VenvPython) { Write-Host ".venv         : present" } else { Write-Host ".venv         : absent (run: .\dao-sheng.ps1 install)" }
    $dataConfig = Join-Path $script:DataHome "config"
    $dataLog = Join-Path $script:DataHome "log"
    if (Test-Path $dataConfig -PathType Container) { Write-Host "config/       : present ($dataConfig)" } else { Write-Host "config/       : absent ($dataConfig; run: .\dao-sheng.ps1 install)" }
    if (Test-Path $dataLog -PathType Container) { Write-Host "log/          : present ($dataLog)" } else { Write-Host "log/          : absent ($dataLog; run: .\dao-sheng.ps1 install)" }
    if (Test-Path $instanceRoot -PathType Container) { Write-Host "instance root : present ($instanceRoot)" } else { Write-Host "instance root : absent ($instanceRoot; run: .\dao-sheng.ps1 install)" }
    $legacy = Find-LegacyRepoData
    if ($legacy.Count -gt 0) {
        Write-Host "legacy repo   : DETECTED ($($legacy.Count) file(s) under instances/ config/ log/) - run: .\dao-sheng.ps1 migrate-data"
    } else {
        Write-Host "legacy repo   : none"
    }

    Write-Host ""
    Write-Host "instance inventory (5 items, dao_sheng/layout.py):"
    $state = Get-InstanceState $instanceRoot
    Write-InventoryLines $instanceRoot $state "status"

    Write-Host ""
    if (Test-Path $script:StateFile) {
        Write-Host "config\install-state.json (data home):"
        Get-Content $script:StateFile | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "config\install-state.json: absent (install not yet run)"
    }
    Write-Host ""
    Write-Host "test entry    : PYTHONIOENCODING=utf-8 python -m unittest discover -s tests"
}

function Invoke-Doctor {
    $instanceRoot = $script:ResolvedInstanceRoot
    Write-Host "DaoSheng doctor (read-only)"
    Write-Host "repo     : $RepoRoot"
    Write-Host "data home: $script:DataHome"
    Write-Host "instance : $instanceRoot"
    Write-Host ""

    function Add-Check([string]$Name, [bool]$Ok, [string]$Expected, [string]$Current, [string]$Fix) {
        $script:docChecks++
        if ($Ok) {
            Write-Host "[OK]   $Name"
        } else {
            $script:docFailed++
            Write-Host "[FAIL] $Name"
            Write-Host "       expected : $Expected"
            Write-Host "       current  : $Current"
            if ($Fix) { Write-Host "       fix      : $Fix" }
        }
    }

    # 1. Python
    $py = Find-Python
    if ($py) {
        Add-Check "Python" $true "python discoverable (.venv preferred, then PATH python/py)" $py.Exe ""
    } else {
        Add-Check "Python" $false "python discoverable (.venv preferred, then PATH python/py)" "not found" "Run: .\dao-sheng.ps1 install (needs a system Python >= MIN_SUPPORTED_PYTHON on PATH)"
    }

    # 2. Python version (MIN_SUPPORTED_PYTHON derived at runtime, contract 2.1)
    $minPy = Get-PythonMinVersion
    if ($py) {
        if ($null -ne $minPy) {
            $minParts = $minPy -split "\."
            if (Test-PythonVersionOk $py.Version $minParts[0] $minParts[1]) {
                Add-Check "Python version" $true ">= $minPy (MIN_SUPPORTED_PYTHON, pyproject.toml requires-python)" $py.Version ""
            } else {
                Add-Check "Python version" $false ">= $minPy (MIN_SUPPORTED_PYTHON, pyproject.toml requires-python)" $py.Version "Install Python $minPy+ and re-run: .\dao-sheng.ps1 install"
            }
        } else {
            Add-Check "Python version" $false "parseable requires-python in pyproject.toml (MIN_SUPPORTED_PYTHON)" "not found or not parseable" "Declare [project] requires-python in pyproject.toml (M01 toolchain decision)"
        }
    } else {
        Add-Check "Python version" $false ">= MIN_SUPPORTED_PYTHON (pyproject.toml requires-python)" "unreachable (python not found)" "Install a current Python (python.org) and re-run: .\dao-sheng.ps1 install"
    }

    # 3. Project structure
    $structure = @(
        "dao_sheng\__init__.py", "dao_sheng\composition.py", "dao_sheng\layout.py",
        "pyproject.toml", "tests\__init__.py", "dao-sheng.ps1",
        "docs\deployment\INSTALLATION_CONTRACT.md"
    )
    $missing = @()
    foreach ($rel in $structure) { if (-not (Test-Path (Join-Path $RepoRoot $rel))) { $missing += $rel } }
    if ($missing.Count -eq 0) {
        Add-Check "Project structure" $true "dao_sheng/ + pyproject.toml + tests/ + dao-sheng.ps1 + contract all present" "all present" ""
    } else {
        Add-Check "Project structure" $false "all required files present" ("missing: " + ($missing -join ", ")) "Restore the missing files from the repository"
    }

    # 4. DaoSheng import
    if ($py) {
        if (Test-DaoShengImport $py.Exe) {
            Add-Check "DaoSheng import" $true "import dao_sheng and dao_sheng.composition succeed" "ok" ""
        } else {
            Add-Check "DaoSheng import" $false "import dao_sheng and dao_sheng.composition succeed (run from repo root, no bytecode written)" "import failed" "Run: .\dao-sheng.ps1 install; if it persists, run: python -m unittest discover -s tests"
        }
    } else {
        Add-Check "DaoSheng import" $false "import dao_sheng and dao_sheng.composition succeed" "unreachable (python not found)" "Run: .\dao-sheng.ps1 install"
    }

    # 5. Dependencies
    if (Test-ZeroExternalDeps) {
        Add-Check "Dependencies" $true "zero external dependencies (M01; pyproject declares none)" "zero external dependencies" ""
    } else {
        Add-Check "Dependencies" $false "zero external dependencies (M01; pyproject declares none)" "pyproject.toml declares a 'dependencies' key" "Resolve via the RECONSTRUCTION.md decision flow (M01 toolchain decision)"
    }

    # 6. Config directory (data home)
    $dataConfig = Join-Path $script:DataHome "config"
    if (Test-Path $dataConfig -PathType Container) {
        Add-Check "Config directory" $true "config/ exists in the data home: $dataConfig" "present" ""
    } else {
        Add-Check "Config directory" $false "config/ exists in the data home: $dataConfig" "absent" "Run: .\dao-sheng.ps1 install"
    }

    # 7. Data directory (instance root, under the data home)
    if (Test-Path $instanceRoot -PathType Container) {
        Add-Check "Data directory" $true "instance root exists: $instanceRoot" "present" ""
    } else {
        Add-Check "Data directory" $false "instance root exists: $instanceRoot" "absent" "Run: .\dao-sheng.ps1 install"
    }

    # 8. Log directory (data home)
    $dataLog = Join-Path $script:DataHome "log"
    if (Test-Path $dataLog -PathType Container) {
        Add-Check "Log directory" $true "log/ exists in the data home: $dataLog" "present" ""
    } else {
        Add-Check "Log directory" $false "log/ exists in the data home: $dataLog" "absent" "Run: .\dao-sheng.ps1 install"
    }

    # 9. Test entry point
    $testDir = Join-Path $RepoRoot "tests"
    $testFiles = @()
    if (Test-Path $testDir -PathType Container) {
        $testFiles = @(Get-ChildItem -Path $testDir -Filter "test_*.py" -File)
    }
    if ($testFiles.Count -ge 1) {
        Add-Check "Test entry point" $true "tests/ with >= 1 test_*.py (suite: python -m unittest discover -s tests)" "$($testFiles.Count) test modules" ""
    } else {
        Add-Check "Test entry point" $false "tests/ with >= 1 test_*.py" "none found" "Restore tests/ from the repository"
    }

    # 10. No personal data inside the repository worktree (upgrade-safety
    #     guard: a plain source upgrade must never have a personal-data
    #     path in the worktree to overwrite).
    $legacy = Find-LegacyRepoData
    if ($legacy.Count -eq 0) {
        Add-Check "No personal data in repository" $true "instances/ config/ log/ hold no files inside the repository worktree" "none found" ""
    } else {
        Add-Check "No personal data in repository" $false "no personal-data files inside the repository worktree" ("found $($legacy.Count) file(s) under instances/ config/ log/") "Run: .\dao-sheng.ps1 migrate-data (explicit, verified, never-overwriting relocation to the data home)"
    }

    Write-Host ""
    Write-Host "checked $script:docChecks items"
    if ($script:docFailed -eq 0) {
        Write-Host "Result: PASS"
        exit 0
    } else {
        Write-Host "Result: FAIL"
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Design-layer role entries (init-role / configure-role).
#
# These are the ONLY entries in this file that write identity.json /
# faculties.json, and only as explicit design-layer initialization or
# modification requested by the user. install never reaches this code.
# Schema authority stays in the Core: every carrier written here is
# validated and canonicalized by dao_sheng.identity.parse_identity and
# generated from dao_sheng.faculties.FACULTY_ROOTS via a Python
# subprocess -- this script hard-codes no schema and no faculty roots.
# ---------------------------------------------------------------------------

$script:RoleScalarFields = @("name", "self_appellation", "voice", "visual_image")
$script:RoleListFields = @("behavioral_habits", "past_experiences", "continuous_memory")
function Parse-RoleArgs {
    # Manually parse the raw $RoleArgs token stream (see param block note).
    # Returns @{ scalars = field -> trimmed string; lists = field ->
    # normalized string[]; clears = lowercased field tokens }. Malformed
    # input fails the step before anything is written.
    $flagFor = @{
        name              = "name"
        selfappellation   = "self_appellation"
        voice             = "voice"
        visualimage       = "visual_image"
        behavioralhabits  = "behavioral_habits"
        pastexperiences   = "past_experiences"
        continuousmemory  = "continuous_memory"
        clear             = "clear"
    }
    $scalars = @{}
    $lists = @{}
    $clears = @()
    $tokens = @($RoleArgs)
    $i = 0
    while ($i -lt $tokens.Count) {
        $tok = [string]$tokens[$i]
        if (-not $tok.StartsWith("-")) {
            Fail-Step "role arguments" "a parameter token such as -Name / -Voice / -BehavioralHabits" ("unexpected bare value: '" + $tok + "'") "Nothing was written"
        }
        $key = $flagFor[$tok.Substring(1).ToLowerInvariant()]
        if ($null -eq $key) {
            Fail-Step "role arguments" "one of: -Name, -SelfAppellation, -Voice, -VisualImage, -BehavioralHabits, -PastExperiences, -ContinuousMemory, -Clear" ("unknown parameter token: '" + $tok + "'") "Nothing was written"
        }
        if ($key -eq "clear") {
            if ($clears.Count -gt 0) {
                Fail-Step "role arguments" "each parameter specified once" "-Clear specified twice" "Remove one of the two; nothing was written"
            }
            $j = $i + 1
            while ($j -lt $tokens.Count -and -not ([string]$tokens[$j]).StartsWith("-")) {
                $clears += ([string]$tokens[$j]).Trim().ToLowerInvariant()
                $j++
            }
            $i = $j
            continue
        }
        if ($scalars.ContainsKey($key) -or $lists.ContainsKey($key)) {
            Fail-Step "role arguments" "each field specified once" ($tok + " specified twice") "Remove one of the two; nothing was written"
        }
        if ($script:RoleListFields -contains $key) {
            $vals = @()
            $j = $i + 1
            while ($j -lt $tokens.Count -and -not ([string]$tokens[$j]).StartsWith("-")) {
                $vals += [string]$tokens[$j]
                $j++
            }
            $lists[$key] = @(Normalize-ListParam $vals)
            $i = $j
        } else {
            if ($i + 1 -ge $tokens.Count -or ([string]$tokens[$i + 1]).StartsWith("-")) {
                Fail-Step "role arguments" ($tok + " followed by a value") ($tok + " has no value") ("Provide a value after " + $tok + "; nothing was written")
            }
            $scalars[$key] = ([string]$tokens[$i + 1]).Trim()
            $i += 2
        }
    }
    return @{ scalars = $scalars; lists = $lists; clears = $clears }
}

function Test-RoleParamBound {
    # True when the user passed any role token (parameter mode); otherwise
    # the role entries run interactive mode.
    return (@($RoleArgs).Count -gt 0)
}

function Split-ListField([string]$Line) {
    # Interactive list input: one line, comma separated; empty items dropped.
    $out = @()
    foreach ($part in ($Line -split ",")) {
        $t = $part.Trim()
        if ($t -ne "") { $out += $t }
    }
    return $out
}

function Normalize-ListParam([string[]]$Values) {
    # Parameter-mode list values: trim each item, drop empty items.
    $out = @()
    foreach ($v in @($Values)) {
        $t = [string]$v
        if ($null -eq $t) { continue }
        $t = $t.Trim()
        if ($t -ne "") { $out += $t }
    }
    return $out
}

function Write-JsonUtf8NoBom([string]$Path, [string]$Text) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Remove-RoleTmp([string]$Path) {
    if (Test-Path $Path) { Remove-Item -Force -Path $Path }
}

function Invoke-RoleValidate([hashtable]$Py, [string]$Mode, [string]$IdentityPath, [string]$FacultiesPath) {
    # Run the Core's own validators over a carrier file (Python subprocess).
    #   check  : validate an existing carrier, write nothing
    #   update : validate + canonicalize identity in place
    #   init   : validate + canonicalize identity, then write faculties
    #            straight from FACULTY_ROOTS (single source; never hard-coded here)
    # argv[1] = repo root so 'import dao_sheng' resolves regardless of cwd.
    # Python code uses single quotes only (safe inside a PS double-quoted string).
    $codeCheck  = "import sys; sys.path.insert(0, sys.argv[1]); from dao_sheng.identity import parse_identity; parse_identity(open(sys.argv[2], encoding='utf-8').read())"
    $codeUpdate = "import sys, json; sys.path.insert(0, sys.argv[1]); from dao_sheng.identity import parse_identity; i = parse_identity(open(sys.argv[2], encoding='utf-8').read()); d = {'name': i.name, 'self_appellation': i.self_appellation, 'voice': i.voice, 'visual_image': i.visual_image, 'behavioral_habits': list(i.behavioral_habits), 'past_experiences': list(i.past_experiences), 'continuous_memory': list(i.continuous_memory)}; open(sys.argv[2], 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False))"
    $codeInit   = $codeUpdate + "; from dao_sheng.faculties import FACULTY_ROOTS; open(sys.argv[3], 'w', encoding='utf-8').write(json.dumps(list(FACULTY_ROOTS), ensure_ascii=False))"
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($Mode -eq "init") {
            $out = & $Py.Exe -B -c $codeInit $RepoRoot $IdentityPath $FacultiesPath 2>&1
        } elseif ($Mode -eq "update") {
            $out = & $Py.Exe -B -c $codeUpdate $RepoRoot $IdentityPath 2>&1
        } else {
            $out = & $Py.Exe -B -c $codeCheck $RepoRoot $IdentityPath 2>&1
        }
        $exit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEAP
    }
    if ($exit -ne 0) {
        foreach ($line in @($out)) {
            $t = ([string]$line).Trim()
            if ($t -ne "") { Write-Host "       python: $t" }
        }
        return $false
    }
    return $true
}

function Invoke-InitRole {
    $script:RoleParsed = Parse-RoleArgs
    $instanceRoot = $script:ResolvedInstanceRoot
    $identityPath = Join-Path $instanceRoot "identity.json"
    $facultiesPath = Join-Path $instanceRoot "faculties.json"

    # Design-layer initialization is for a FRESH instance only: if either
    # carrier already exists, refuse -- never overwrite an existing identity.
    if ((Test-Path $identityPath) -or (Test-Path $facultiesPath)) {
        $existing = @()
        if (Test-Path $identityPath) { $existing += "identity.json" }
        if (Test-Path $facultiesPath) { $existing += "faculties.json" }
        Fail-Step "init-role" "fresh instance: neither identity.json nor faculties.json exists" ("already present: " + ($existing -join ", ")) "init-role initializes a FRESH instance only and never overwrites; to edit an existing identity run: .\dao-sheng.ps1 configure-role"
    }

    $py = Find-Python
    if ($null -eq $py) {
        Fail-Step "Python" "python discoverable (.venv preferred, then PATH python/py)" "not found" "Run .\dao-sheng.ps1 install first (role entries validate every carrier through the Core's Python modules)"
    }

    if (-not (Test-Path $instanceRoot)) {
        New-Item -ItemType Directory -Force -Path $instanceRoot | Out-Null
    }

    $name = ""
    $selfAppellation = ""
    $voice = ""
    $visualImage = ""
    $behavioralHabits = @()
    $pastExperiences = @()
    $continuousMemory = @()

    if (Test-RoleParamBound) {
        if ($script:RoleParsed.scalars.ContainsKey("name")) { $name = $script:RoleParsed.scalars["name"] }
        if ($script:RoleParsed.scalars.ContainsKey("self_appellation")) { $selfAppellation = $script:RoleParsed.scalars["self_appellation"] }
        if ($script:RoleParsed.scalars.ContainsKey("voice")) { $voice = $script:RoleParsed.scalars["voice"] }
        if ($script:RoleParsed.scalars.ContainsKey("visual_image")) { $visualImage = $script:RoleParsed.scalars["visual_image"] }
        if ($script:RoleParsed.lists.ContainsKey("behavioral_habits")) { $behavioralHabits = @($script:RoleParsed.lists["behavioral_habits"]) }
        if ($script:RoleParsed.lists.ContainsKey("past_experiences")) { $pastExperiences = @($script:RoleParsed.lists["past_experiences"]) }
        if ($script:RoleParsed.lists.ContainsKey("continuous_memory")) { $continuousMemory = @($script:RoleParsed.lists["continuous_memory"]) }
    } else {
        Write-Host "init-role interactive mode: enter values (empty line = empty value; list fields: one line, comma separated)"
        $name = (Read-Host "Name (required)").Trim()
        $selfAppellation = (Read-Host "Self appellation").Trim()
        $voice = (Read-Host "Voice").Trim()
        $visualImage = (Read-Host "Visual image").Trim()
        $behavioralHabits = @(Split-ListField (Read-Host "Behavioral habits"))
        $pastExperiences = @(Split-ListField (Read-Host "Past experiences"))
        $continuousMemory = @(Split-ListField (Read-Host "Continuous memory"))
    }

    if ($name -eq "") {
        Fail-Step "init-role name" "a non-empty name (required identity field)" "empty" "Re-run with -Name <name> or provide a non-empty name interactively; nothing was written"
    }

    # No persona is ever generated by default: unbound fields stay empty.
    $doc = [ordered]@{
        name              = $name
        self_appellation  = $selfAppellation
        voice             = $voice
        visual_image      = $visualImage
        behavioral_habits = @($behavioralHabits)
        past_experiences  = @($pastExperiences)
        continuous_memory = @($continuousMemory)
    }

    $idTmp = Join-Path $instanceRoot "identity.json.new.tmp"
    $facTmp = Join-Path $instanceRoot "faculties.json.new.tmp"
    Write-JsonUtf8NoBom $idTmp ($doc | ConvertTo-Json -Depth 5)

    if (-not (Invoke-RoleValidate $py "init" $idTmp $facTmp)) {
        Remove-RoleTmp $idTmp
        Remove-RoleTmp $facTmp
        Fail-Step "init-role validation" "generated identity passes dao_sheng.identity.parse_identity (strict 7-key schema); faculties generated from FACULTY_ROOTS" "Core validation rejected the generated carriers" "Correct the input values and re-run: .\dao-sheng.ps1 init-role (no partial state was left behind)"
    }

    # Race re-check: refuse to overwrite carriers that appeared meanwhile.
    if ((Test-Path $identityPath) -or (Test-Path $facultiesPath)) {
        Remove-RoleTmp $idTmp
        Remove-RoleTmp $facTmp
        Fail-Step "init-role" "identity.json / faculties.json still absent at write time" "a carrier appeared during this run" "Re-run: .\dao-sheng.ps1 init-role (nothing was overwritten)"
    }

    Move-Item -Force $idTmp $identityPath
    Move-Item -Force $facTmp $facultiesPath
    Write-Host "[OK] identity.json + faculties.json created (design-layer initialization)"
    Write-Host "     instance root : $instanceRoot"
    Write-Host "     to edit fields later: .\dao-sheng.ps1 configure-role"
    exit 0
}

function Invoke-ConfigureRole {
    $script:RoleParsed = Parse-RoleArgs
    $instanceRoot = $script:ResolvedInstanceRoot
    $identityPath = Join-Path $instanceRoot "identity.json"

    if (-not (Test-Path $identityPath)) {
        Fail-Step "configure-role" "existing identity.json (design layer already initialized)" "identity.json not found" "Initialize the role first: .\dao-sheng.ps1 init-role"
    }

    $py = Find-Python
    if ($null -eq $py) {
        Fail-Step "Python" "python discoverable (.venv preferred, then PATH python/py)" "not found" "Run .\dao-sheng.ps1 install first (role entries validate every carrier through the Core's Python modules)"
    }

    # Validate the existing carrier read-only: an invalid carrier is refused
    # untouched -- configure-role never repairs or damages it.
    if (-not (Invoke-RoleValidate $py "check" $identityPath "")) {
        Fail-Step "configure-role" "existing identity.json passes dao_sheng.identity.parse_identity (strict 7-key schema)" "existing identity.json is invalid" "configure-role refuses to touch an invalid carrier; repair or remove identity.json manually, then run: .\dao-sheng.ps1 init-role"
    }

    $cur = ConvertFrom-Json ([System.IO.File]::ReadAllText($identityPath, [System.Text.Encoding]::UTF8))

    $new = @{}
    foreach ($f in $script:RoleScalarFields) { $new[$f] = [string]$cur.$f }
    foreach ($f in $script:RoleListFields) {
        $v = $cur.$f
        if ($null -eq $v) { $new[$f] = @() } else { $new[$f] = @($v) }
    }

    # -Clear token validation: name is a required field and can never be
    # cleared; unknown tokens are rejected; a field cannot be both set and cleared.
    $clears = @()
    foreach ($t in $script:RoleParsed.clears) {
        if ($t -eq "name") {
            Fail-Step "configure-role -Clear" "one of: self_appellation, voice, visual_image, behavioral_habits, past_experiences, continuous_memory" "name is a required identity field and cannot be cleared" "Remove 'name' from -Clear; nothing was written"
        }
        if (-not ($script:RoleScalarFields -contains $t) -and -not ($script:RoleListFields -contains $t)) {
            Fail-Step "configure-role -Clear" "a known identity field token (self_appellation, voice, visual_image, behavioral_habits, past_experiences, continuous_memory)" ("unknown token: '" + $t + "'") "Nothing was written"
        }
        if ($script:RoleParsed.scalars.ContainsKey($t) -or $script:RoleParsed.lists.ContainsKey($t)) {
            Fail-Step "configure-role" "each field specified once" ("field '" + $t + "' appears both as its parameter and in -Clear") "Remove one of the two; nothing was written"
        }
        $clears += $t
    }

    if (Test-RoleParamBound) {
        # Parameter mode: bound fields replace their values; unbound fields keep current values.
        foreach ($f in ($script:RoleScalarFields + $script:RoleListFields)) {
            if ($script:RoleParsed.scalars.ContainsKey($f)) { $new[$f] = $script:RoleParsed.scalars[$f] }
            elseif ($script:RoleParsed.lists.ContainsKey($f)) { $new[$f] = @($script:RoleParsed.lists[$f]) }
        }
        foreach ($t in $clears) {
            if ($script:RoleListFields -contains $t) { $new[$t] = @() } else { $new[$t] = "" }
        }
    } else {
        Write-Host "configure-role interactive mode: empty input keeps the current value; '-' clears an optional field; list fields: one line, comma separated"
        Write-Host "Current identity:"
        foreach ($f in ($script:RoleScalarFields + $script:RoleListFields)) {
            if ($script:RoleListFields -contains $f) { Write-Host ("  {0,-18}: {1}" -f $f, ($new[$f] -join ", ")) }
            else { Write-Host ("  {0,-18}: {1}" -f $f, $new[$f]) }
        }
        foreach ($f in ($script:RoleScalarFields + $script:RoleListFields)) {
            $isList = $script:RoleListFields -contains $f
            if ($isList) { $curText = $new[$f] -join ", " } else { $curText = $new[$f] }
            $line = (Read-Host ("{0} [current: {1}]" -f $f, $curText)).Trim()
            if ($f -eq "name") {
                # name is required: empty input or '-' keep the current value.
                if ($line -ne "" -and $line -ne "-") { $new["name"] = $line }
            } elseif ($line -eq "-") {
                if ($isList) { $new[$f] = @() } else { $new[$f] = "" }
            } elseif ($line -ne "") {
                if ($isList) { $new[$f] = @(Split-ListField $line) } else { $new[$f] = $line }
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($new["name"])) {
        Fail-Step "configure-role name" "a non-empty name (required identity field)" "empty" "Provide a non-empty -Name or keep the current name interactively; nothing was written"
    }

    $doc = [ordered]@{
        name              = $new["name"]
        self_appellation  = $new["self_appellation"]
        voice             = $new["voice"]
        visual_image      = $new["visual_image"]
        behavioral_habits = @($new["behavioral_habits"])
        past_experiences  = @($new["past_experiences"])
        continuous_memory = @($new["continuous_memory"])
    }

    $idTmp = Join-Path $instanceRoot "identity.json.new.tmp"
    Write-JsonUtf8NoBom $idTmp ($doc | ConvertTo-Json -Depth 5)

    if (-not (Invoke-RoleValidate $py "update" $idTmp "")) {
        Remove-RoleTmp $idTmp
        Fail-Step "configure-role validation" "updated identity passes dao_sheng.identity.parse_identity (strict 7-key schema)" "Core validation rejected the updated carrier" "Correct the values and re-run: .\dao-sheng.ps1 configure-role (the original identity.json was left untouched)"
    }

    Move-Item -Force $idTmp $identityPath
    Write-Host "[OK] identity.json updated"
    Write-Host "     faculties.json / continuity / memory were NOT touched"
    Write-Host "     the next composition will load the new identity"
    exit 0
}

function Invoke-MigrateData {
    # Explicit one-time relocation of legacy personal data that older
    # versions placed INSIDE the repository (instances/ config/ log/) into
    # the external data home. Two phases:
    #   1. refuse phase: if ANY migration target already exists, stop
    #      BEFORE copying anything -- migrate-data never overwrites.
    #   2. copy phase: copy + SHA256 verify, then delete the source file.
    #      A hash mismatch removes the partial copy and keeps the source.
    # Empty source directories are left in place (harmless, untracked).
    # Nothing here reads or understands the data -- files move byte-for-byte.
    $legacy = Find-LegacyRepoData
    Write-Host "DaoSheng migrate-data"
    Write-Host "repo      : $RepoRoot"
    Write-Host "data home : $script:DataHome"
    Write-Host ""
    if ($legacy.Count -eq 0) {
        Write-Host "[OK] no legacy personal data found under instances/ config/ log/ in the repository - nothing to migrate"
        exit 0
    }
    Write-Host "found $($legacy.Count) legacy file(s) inside the repository:"

    $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
    $plan = @()
    foreach ($src in $legacy) {
        $srcFull = [System.IO.Path]::GetFullPath($src)
        $rel = $srcFull.Substring($repoFull.Length).TrimStart('\')
        $dst = Join-Path $script:DataHome $rel
        $plan += @{ Src = $srcFull; Dst = $dst; Rel = $rel }
        Write-Host "  $rel  ->  $dst"
    }
    Write-Host ""

    # Phase 1: refuse if any target already exists (nothing copied yet).
    $collisions = @()
    foreach ($item in $plan) {
        if (Test-Path $item.Dst) { $collisions += $item.Rel }
    }
    if ($collisions.Count -gt 0) {
        Fail-Step "migrate-data" "no existing file at any migration target under the data home" ("target(s) already present: " + ($collisions -join ", ")) "migrate-data never overwrites existing data; compare the files yourself and resolve the collision manually, then re-run; nothing was copied"
    }

    # Phase 2: copy + verify + delete source. NOT atomic across files: a
    # failure mid-run leaves already-migrated files in the data home and
    # un-migrated sources untouched in the repository -- no source file is
    # ever deleted before its copy is verified, and no blank instance is
    # started. Re-running migrate-data after fixing the blocking condition
    # moves the rest.
    $migrated = 0
    foreach ($item in $plan) {
        $dstDir = Split-Path -Parent $item.Dst
        if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
        $srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.Src).Hash
        try {
            Copy-Item -LiteralPath $item.Src -Destination $item.Dst
        } catch {
            if ((Test-Path -LiteralPath $item.Dst -PathType Leaf) -and
                ((Get-FileHash -Algorithm SHA256 -LiteralPath $item.Dst).Hash -ne $srcHash)) {
                Remove-Item -Force -LiteralPath $item.Dst
            }
            Fail-Step "migrate-data copy" "each legacy file copies into the data home without error" ("copy failed for: " + $item.Rel + " -- " + $_.Exception.Message) "the source file was kept in place; already-migrated files stay in the data home; resolve the blocking condition and re-run migrate-data to move the remaining files"
        }
        $dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.Dst).Hash
        if ($srcHash -ne $dstHash) {
            Remove-Item -Force -LiteralPath $item.Dst
            Fail-Step "migrate-data verification" "SHA256 of the copy equals SHA256 of the source" ("hash mismatch for: " + $item.Rel) "the partial copy was removed and the original file was kept in place; investigate the file and re-run; already-migrated files stay in the data home"
        }
        Remove-Item -Force -LiteralPath $item.Src
        $migrated++
        Write-Host "[OK] moved $($item.Rel) -> $($item.Dst) (SHA256 verified)"
    }

    # install-state.json fix-up: when the recorded instance_root still
    # points inside the repository, rewrite that ONE key to the same
    # relative position under the data home. Nothing else is touched.
    if (Test-Path $script:StateFile) {
        $stateDoc = $null
        try {
            $stateDoc = ConvertFrom-Json ([System.IO.File]::ReadAllText($script:StateFile, [System.Text.Encoding]::UTF8))
        } catch {
            Write-Host "[WARN] install-state.json could not be parsed; left untouched"
        }
        if ($null -ne $stateDoc -and $stateDoc.PSObject.Properties.Name -contains "instance_root") {
            $recorded = [string]$stateDoc.instance_root
            $recFull = $null
            if ($recorded -ne "") {
                # Probe failure (access denied / IO error / unavailable
                # drive / unreachable UNC root) aborts fail-loud BEFORE
                # anything is rewritten: install-state.json stays intact.
                try {
                    if (Test-PathInsideRepo $recorded) {
                        $recFull = (Get-CanonicalPathForComparison $recorded).TrimEnd('\')
                    }
                } catch {
                    Fail-Step "migrate-data install-state fix-up" "install-state instance_root to be classifiable" ("existence probe failed: " + $_.Exception.Message) "install-state.json was left untouched; resolve the path/access error and re-run"
                }
            }
            if ($null -ne $recFull) {
                # Same canonical text the containment decision used, so the
                # Substring below extracts the right relative position even
                # when $recorded mixes short/long forms or has a missing leaf.
                $relRoot = $recFull.Substring($repoFull.Length).TrimStart('\')
                $newRoot = [System.IO.Path]::GetFullPath((Join-Path $script:DataHome $relRoot))
                $stateDoc.instance_root = $newRoot
                Write-JsonUtf8NoBom $script:StateFile ($stateDoc | ConvertTo-Json)
                Write-Host "[OK] install-state.json instance_root updated: $recorded -> $newRoot"
            }
        }
    }

    Write-Host ""
    Write-Host "migrate-data complete: $migrated file(s) moved to the data home (sources removed; empty legacy directories left in place)"
    exit 0
}

# Test seam (DAO_SHENG_PS_LIB_ONLY=1): define the functions and stop
# BEFORE the usage check, the central guard and the command dispatch, so
# tests can dot-source this file, override $DaoShengPathExistsProbe, and
# call the production helpers (Test-PathExistsForComparison /
# Get-CanonicalPathForComparison / Test-PathInsideRepo) directly.
# Production entries never set this variable; only the exact value "1"
# is honored, and this mode reads/writes nothing.
if ($env:DAO_SHENG_PS_LIB_ONLY -eq "1") { return }

if ([string]::IsNullOrWhiteSpace($Command)) {
    Write-Usage
    exit 1
}
# install / status / doctor / migrate-data take no role tokens (old
# strictness preserved).
if ($Command -ne "init-role" -and $Command -ne "configure-role" -and @($RoleArgs).Count -gt 0) {
    Fail-Step "entry arguments" "no extra arguments for install / status / doctor / migrate-data" ("unexpected tokens: " + (@($RoleArgs) -join " ")) "Nothing was written"
}

# ---------------------------------------------------------------------------
# Central path resolution + upgrade-safety guard (runs for EVERY entry,
# before any read or write). Personal runtime data must live OUTSIDE the
# Git worktree: a data home or instance root that resolves inside the
# repository is refused fail-loud here. This is what makes a plain source
# upgrade (git pull) structurally unable to touch personal data.
# ---------------------------------------------------------------------------
$script:DataHome = Resolve-DataHome
# A probe failure (access denied / IO error / unavailable drive /
# unreachable UNC root) is NOT "outside the repo" and NOT "missing": it
# aborts the guard fail-loud via Fail-Step, same exit path as a refusal.
try { $dataHomeInsideRepo = Test-PathInsideRepo $script:DataHome } catch {
    Fail-Step "data home" "a personal-data root OUTSIDE the repository worktree ($RepoRoot)" ("existence probe failed: " + $_.Exception.Message) "Resolve the path/access error first (access denied / IO error / unavailable drive / unreachable UNC root is NOT treated as 'missing'); nothing was written"
}
if ($dataHomeInsideRepo) {
    Fail-Step "data home" "a personal-data root OUTSIDE the repository worktree ($RepoRoot)" $script:DataHome "Point DAO_SHENG_DATA_HOME to a directory outside the repository (or unset it for the default) and re-run; nothing was written"
}
$script:ResolvedInstanceRoot = Resolve-InstanceRoot $InstanceRoot
try { $instanceRootInsideRepo = Test-PathInsideRepo $script:ResolvedInstanceRoot } catch {
    Fail-Step "instance root" "an instance root OUTSIDE the repository worktree ($RepoRoot)" ("existence probe failed: " + $_.Exception.Message) "Resolve the path/access error first (access denied / IO error / unavailable drive / unreachable UNC root is NOT treated as 'missing'); nothing was written"
}
if ($instanceRootInsideRepo) {
    Fail-Step "instance root" "an instance root OUTSIDE the repository worktree ($RepoRoot)" $script:ResolvedInstanceRoot "-InstanceRoot must resolve outside the repository (relative paths resolve against the data home); nothing was written"
}
$script:StateFile = Join-Path $script:DataHome "config\install-state.json"

switch ($Command) {
    "install" { Invoke-Install }
    "status"  { Invoke-Status }
    "doctor"  { Invoke-Doctor }
    "migrate-data" { Invoke-MigrateData }
    "init-role" { Invoke-InitRole }
    "configure-role" { Invoke-ConfigureRole }
}
