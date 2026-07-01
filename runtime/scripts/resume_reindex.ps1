# Продолжить re-index с последнего checkpoint (запускать из runtime/)
Set-Location (Resolve-Path $PSScriptRoot\..).Path
$env:PYTHONPATH = "."
$env:PYTHONUNBUFFERED = "1"
$env:TMKI_PDF_MAX_PAGES = "300"
python scripts/reindex_regulations_local.py --checkpoint-every 200
