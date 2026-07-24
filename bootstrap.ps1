<#
.SYNOPSIS
  Onboard a repository that consumes copilot-workflow-base (Windows / PowerShell).

.DESCRIPTION
  Idempotent and safe to re-run. It:
    1. initializes/updates the .github/shared submodule (and nested ones),
    2. sets `git config submodule.recurse true`,
    3. (optional -CopySkills) copies shared skills into .github/skills/ as a fallback
       for VS Code builds that lack the `chat.agentSkillsLocations` setting.

  Run from anywhere; it locates the consuming repo root itself:
    pwsh .github/shared/bootstrap.ps1 [-CopySkills]

  Rollback: the copy fallback writes only into .github/skills/shared-* ; delete those
  folders to undo. Everything else is standard git submodule state.
#>
[CmdletBinding()]
param(
  [switch]$CopySkills
)

$ErrorActionPreference = 'Stop'

# This script lives at <repo>/.github/shared/bootstrap.ps1 → repo root is two levels up.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path

try {
  $RepoRoot = (git -C $RepoRoot rev-parse --show-toplevel 2>$null)
} catch {
  Write-Warning "bootstrap.ps1: '$RepoRoot' is not inside a git repository - nothing to do."
  exit 0
}
if (-not $RepoRoot) {
  Write-Warning "bootstrap.ps1: could not resolve a git repository root - nothing to do."
  exit 0
}

Write-Host "==> copilot-workflow-base bootstrap"
Write-Host "    repo: $RepoRoot"

if (Test-Path (Join-Path $RepoRoot '.gitmodules')) {
  Write-Host "==> syncing submodules"
  git -C $RepoRoot submodule sync --recursive
  git -C $RepoRoot submodule update --init --recursive
} else {
  Write-Host "    no .gitmodules found - skipping submodule update"
}

Write-Host "==> setting submodule.recurse = true"
git -C $RepoRoot config submodule.recurse true

$Copied = 0
if ($CopySkills) {
  $SharedSkills = Join-Path $RepoRoot '.github/shared/skills'
  $DestSkills   = Join-Path $RepoRoot '.github/skills'
  if (Test-Path $SharedSkills) {
    Write-Host "==> copying shared skills (fallback for VS Code without chat.agentSkillsLocations)"
    New-Item -ItemType Directory -Force -Path $DestSkills | Out-Null
    Get-ChildItem -Path $SharedSkills -Directory | ForEach-Object {
      $dest = Join-Path $DestSkills ("shared-" + $_.Name)
      if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
      Copy-Item -Recurse -Force $_.FullName $dest
      Write-Host ("    -> .github/skills/shared-" + $_.Name)
      $Copied++
    }
  } else {
    Write-Host "    no shared skills directory at $SharedSkills - skipping copy"
  }
}

Write-Host ""
Write-Host "==> done."
Write-Host "    submodules initialized/updated, submodule.recurse enabled."
if ($CopySkills) {
  Write-Host "    shared skills copied: $Copied (remove .github/skills/shared-* to undo)."
} else {
  Write-Host "    skills are loaded from the submodule via chat.agentSkillsLocations"
  Write-Host "    (re-run with -CopySkills only on older VS Code builds)."
}
