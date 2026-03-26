param(
  [string]$ProjectName = "Product Launch ES",
  [string]$Requirement = "Simular la reaccion social a un lanzamiento de producto en espanol."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
  python -m alvear.cli init --name $ProjectName --requirement $Requirement
  Write-Host ""
  Write-Host "Crea el proyecto, copia el project_id y ejecuta despues:"
  Write-Host "python -m alvear.cli ingest --project-id <PROJECT_ID> ..\seeds\product_launch_es\launch_brief.md ..\seeds\product_launch_es\landing_copy.md ..\seeds\product_launch_es\faq.md ..\seeds\product_launch_es\sample_reactions.md"
  Write-Host "python -m alvear.cli build-graph --project-id <PROJECT_ID>"
  Write-Host "python -m alvear.cli prepare --project-id <PROJECT_ID> --max-entities 24"
}
finally {
  Pop-Location
}
