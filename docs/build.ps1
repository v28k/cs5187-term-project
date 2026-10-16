# Builds all study guides, the meeting slides (PDF + PPTX) and speaker notes.
# Requires: python with matplotlib, pandoc, a LaTeX with pdflatex and beamer.
# Usage (from anywhere):  powershell -File docs/build.ps1
$ErrorActionPreference = "Stop"
$docs = $PSScriptRoot

function Invoke-Pandoc([string]$dir, [string[]]$pandocArgs) {
    Push-Location $dir
    try {
        & pandoc @pandocArgs
        if ($LASTEXITCODE -ne 0) { throw "pandoc failed: $($pandocArgs -join ' ')" }
    } finally { Pop-Location }
}

Push-Location (Join-Path $docs "figs")
try {
    & python make_figs.py
    if ($LASTEXITCODE -ne 0) { throw "make_figs.py failed" }
} finally { Pop-Location }

$learn = Join-Path $docs "learn"
foreach ($name in "00_whole_project", "01_project_so_far", "02_future_plan") {
    Invoke-Pandoc $learn @("$name.md", "-o", "$name.pdf", "--pdf-engine=pdflatex", "--resource-path=.")
}

$meeting = Join-Path $docs "meeting"
Invoke-Pandoc $meeting @("slides.md", "-t", "beamer", "-o", "slides.pdf", "--pdf-engine=pdflatex", "--resource-path=.")
Invoke-Pandoc $meeting @("slides.md", "-o", "slides.pptx", "--resource-path=.")
Invoke-Pandoc $meeting @("speaker_notes.md", "-o", "speaker_notes.pdf", "--pdf-engine=pdflatex")

$pack = Join-Path (Split-Path $docs -Parent) "progressmeet1"
New-Item -ItemType Directory -Force -Path $pack | Out-Null
Copy-Item (Join-Path $meeting "slides.pdf") (Join-Path $pack "slides.pdf") -Force
Copy-Item (Join-Path $meeting "slides.pptx") (Join-Path $pack "slides.pptx") -Force
Copy-Item (Join-Path $meeting "speaker_notes.pdf") (Join-Path $pack "speaker_notes.pdf") -Force
Copy-Item (Join-Path $learn "00_whole_project.pdf") (Join-Path $pack "whole_project.pdf") -Force
Copy-Item (Join-Path $learn "01_project_so_far.pdf") (Join-Path $pack "current_progress.pdf") -Force
Copy-Item (Join-Path $learn "02_future_plan.pdf") (Join-Path $pack "future_plan.pdf") -Force

Write-Host "Built:"
Get-ChildItem $learn, $meeting, $pack -Include *.pdf, *.pptx -Recurse | ForEach-Object { Write-Host "  $($_.FullName)" }
