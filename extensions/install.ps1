<#
.SYNOPSIS
  Install the VS Code extensions vendored in this folder (Windows / PowerShell).

.DESCRIPTION
  Every subfolder holding a package.json that declares publisher, name, version and
  engines.vscode is treated as an extension. Drop a new folder in and it is picked up
  automatically - this script never needs editing.

  Each extension is linked into the VS Code extensions folder with a directory junction,
  so `git pull` updates it in place with no reinstall. Junctions need neither admin
  rights nor Developer Mode; -Copy falls back to a plain copy for filesystems that
  refuse links (re-run after every pull in that case).

    pwsh extensions/install.ps1                  # all extensions
    pwsh extensions/install.ps1 md-flashcards    # one, by folder name
    pwsh extensions/install.ps1 -List            # show what would be installed
    pwsh extensions/install.ps1 -Uninstall       # remove them again

  Rollback: -Uninstall, or delete the target folders printed at the end.
#>
[CmdletBinding()]
param(
  [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
  [string[]]$Name,
  [switch]$Insiders,
  [switch]$Copy,
  [switch]$Uninstall,
  [switch]$List
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExtRoot = if ($Insiders) { Join-Path $HOME '.vscode-insiders\extensions' } else { Join-Path $HOME '.vscode\extensions' }

function Get-VendoredExtensions {
  param([string]$Root)

  Get-ChildItem -Path $Root -Directory | ForEach-Object {
    $manifestPath = Join-Path $_.FullName 'package.json'
    if (-not (Test-Path $manifestPath)) { return }

    try {
      $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    } catch {
      Write-Warning "skipping $($_.Name): unreadable package.json - $($_.Exception.Message)"
      return
    }
    if (-not ($manifest.publisher -and $manifest.name -and $manifest.version -and $manifest.engines.vscode)) {
      Write-Warning "skipping $($_.Name): package.json needs publisher, name, version and engines.vscode"
      return
    }

    [pscustomobject]@{
      Folder  = $_.Name
      Source  = $_.FullName
      Id      = "$($manifest.publisher).$($manifest.name)"
      Version = $manifest.version
      Target  = Join-Path $ExtRoot "$($manifest.publisher).$($manifest.name)-$($manifest.version)"
    }
  }
}

# Junctions must go through Directory.Delete; Remove-Item -Recurse can follow the link
# and wipe the source folder.
function Remove-Install {
  param([string]$ExtRoot, [string]$Id)

  Get-ChildItem -Path $ExtRoot -Filter "$Id-*" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.LinkType) { [System.IO.Directory]::Delete($_.FullName) } else { Remove-Item -Recurse -Force $_.FullName }
    Write-Host "    removed $($_.Name)"
  }
}

$extensions = @(Get-VendoredExtensions -Root $Root)
if ($Name) {
  $unknown = $Name | Where-Object { $_ -notin $extensions.Folder }
  if ($unknown) { throw "no such extension: $($unknown -join ', ') (available: $($extensions.Folder -join ', '))" }
  $extensions = $extensions | Where-Object { $_.Folder -in $Name }
}

if ($extensions.Count -eq 0) {
  Write-Host "no extensions found under $Root"
  exit 0
}

if ($List) {
  $extensions | Select-Object Folder, Id, Version, @{ n = 'Installed'; e = { Test-Path $_.Target } } | Format-Table -AutoSize
  exit 0
}

# Not an error: the repo is often cloned on machines without VS Code (servers, CI).
if (-not (Test-Path $ExtRoot)) {
  Write-Warning "VS Code extensions folder not found ($ExtRoot) - skipping extension install."
  exit 0
}

foreach ($ext in $extensions) {
  Write-Host "==> $($ext.Folder) ($($ext.Id) $($ext.Version))"
  Remove-Install -ExtRoot $ExtRoot -Id $ext.Id
  if ($Uninstall) { continue }

  $copied = $Copy
  if (-not $copied) {
    try {
      New-Item -ItemType Junction -Path $ext.Target -Target $ext.Source -ErrorAction Stop | Out-Null
      Write-Host "    linked  -> $($ext.Target)"
    } catch {
      Write-Warning "junction failed ($($_.Exception.Message)); falling back to a copy"
      $copied = $true
    }
  }
  if ($copied) {
    New-Item -ItemType Directory -Force -Path $ext.Target | Out-Null
    Copy-Item -Recurse -Force (Join-Path $ext.Source '*') $ext.Target
    Write-Host "    copied  -> $($ext.Target)   (re-run after every git pull)"
  }
}

Write-Host ""
if ($Uninstall) {
  Write-Host "==> uninstalled. Run 'Developer: Reload Window' in VS Code."
} else {
  Write-Host "==> done. Run 'Developer: Reload Window' in VS Code."
}
