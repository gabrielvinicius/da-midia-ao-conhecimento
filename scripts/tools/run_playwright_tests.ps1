# Script PowerShell para facilitar a execução dos testes Playwright

Write-Host "Executando testes Playwright para o frontend do video-summarizer" -ForegroundColor Green
Write-Host "Selecione uma opção:" -ForegroundColor Yellow
Write-Host "1) Executar todos os testes"
Write-Host "2) Executar testes em modo headed" 
Write-Host "3) Executar testes em modo debug"
Write-Host "4) Executar testes com interface UI"
Write-Host "5) Executar um teste específico"
Write-Host "0) Sair"

$option = Read-Host "Opção"

switch ($option) {
  "1" {
    Write-Host "Executando todos os testes..." -ForegroundColor Cyan
    Set-Location frontend
    npx playwright test
  }
  "2" {
    Write-Host "Executando testes em modo headed..." -ForegroundColor Cyan
    Set-Location frontend
    npx playwright test --headed
  }
  "3" {
    Write-Host "Executando testes em modo debug..." -ForegroundColor Cyan
    Set-Location frontend
    npx playwright test --debug
  }
  "4" {
    Write-Host "Executando testes com interface UI..." -ForegroundColor Cyan
    Set-Location frontend
    npx playwright test --ui
  }
  "5" {
    $testPath = Read-Host "Caminho do teste específico (ex: tests/e2e/auth/login.spec.ts)"
    Write-Host "Executando teste específico: $testPath" -ForegroundColor Cyan
    Set-Location frontend
    npx playwright test $testPath
  }
  "0" {
    Write-Host "Saindo..." -ForegroundColor Green
    exit 0
  }
  default {
    Write-Host "Opção inválida" -ForegroundColor Red
  }
}