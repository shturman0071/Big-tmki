param(
  [ValidateSet('auto','ollama','stub')]
  [string]$Llm = 'auto',
  [switch]$SkipDocker,
  [switch]$SkipQa,
  [switch]$SkipDocs,
  [switch]$SkipRead
)

$runtime = Resolve-Path (Join-Path $PSScriptRoot '..')
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $runtime

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  TMKI leadership demo (trial)' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

Write-Host '[1/4] Preflight...' -ForegroundColor Yellow
python scripts/pipeline_status.py
python scripts/check_runtime_health.py
if ($LASTEXITCODE -ne 0) { Write-Host 'Health check: warnings (continue)' -ForegroundColor DarkYellow }

$resolvedLlm = 'stub'
if ($Llm -eq 'auto') {
  $r = python scripts/check_ollama.py --resolve 2>$null
  if ($LASTEXITCODE -eq 0 -and $r) { $resolvedLlm = $r.Trim() }
} else {
  $resolvedLlm = $Llm
}
$env:TMKI_LLM_PROVIDER = $resolvedLlm
if ($resolvedLlm -eq 'ollama') {
  if (-not $env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434' }
  if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = 'qwen2.5:7b' }
  Write-Host ("  LLM: ollama ({0})" -f $env:OLLAMA_MODEL) -ForegroundColor Green
} else {
  Write-Host ("  LLM: {0}" -f $resolvedLlm) -ForegroundColor DarkYellow
}

if (-not $SkipDocker) {
  python scripts/check_docker.py --require 2>$null
  if ($LASTEXITCODE -eq 0) {
    $env:DATABASE_URL = 'postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki'
    $env:TMKI_INDEX_BACKEND = 'pgvector'
  }
}

if (-not $SkipQa) {
  Write-Host ''
  Write-Host '[2/4] Q&A over regulations...' -ForegroundColor Yellow
  $questions = @(
    'marksheider survey site',
    'crane rosthehnadzor',
    'OPO hazardous production facility'
  )
  $backendArgs = @('--variant','v2','--hybrid','--llm',$resolvedLlm)
  if ($env:DATABASE_URL) { $backendArgs += @('--backend','pgvector') }

  foreach ($q in $questions) {
    Write-Host ''
    Write-Host ("  Q: {0}" -f $q) -ForegroundColor White
    python scripts/run_mvp_regulations.py $q @backendArgs
    if ($LASTEXITCODE -ne 0) {
      Write-Host '  (error - check Ollama and pgvector)' -ForegroundColor Red
    }
  }
}

if (-not $SkipDocs) {
  Write-Host ''
  Write-Host '[3/4] Document from template...' -ForegroundColor Yellow
  python scripts/run_document_author_demo.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipRead) {
  Write-Host ''
  Write-Host '[4/4] Read multiple file formats...' -ForegroundColor Yellow
  python scripts/demo_read_formats.py --matrix
  Write-Host ''
  python scripts/demo_read_formats.py --samples
}

Write-Host ''
Write-Host '========================================' -ForegroundColor Green
Write-Host '  Demo completed' -ForegroundColor Green
Write-Host '  Documents: artifacts\\leadership-demo\\documents\\' -ForegroundColor Green
Write-Host ("  Repeat Q&A: python scripts/run_mvp_regulations.py ""your question"" --llm {0} --hybrid --backend pgvector" -f $resolvedLlm) -ForegroundColor Green
Write-Host '========================================' -ForegroundColor Green
