<#
.SYNOPSIS
  Implanta a versão já posta na pasta de produção: constrói as imagens dessa
  versão, sobe os contêineres e confere a saúde; se algo falhar, volta à
  versão anterior.

.DESCRIPTION
  Chamado pelo workflow "Deploy" (.github/workflows/deploy.yml), no runner da
  máquina de produção, depois que o workflow já pôs o código na versão nova.
  Pode ser rodado à mão na pasta de produção:

    pwsh scripts/ops/deploy.ps1 -PreviousSha <commit em produção antes>

  Cada versão vira imagens marcadas com o commit (app:<commit>,
  frontend:<commit>); a versão saudável também recebe a marca "current", que
  é a que o Compose usa sem APP_TAG. Voltar atrás é subir com APP_TAG no
  commit anterior: a imagem dele continua na máquina, nada é reconstruído.
  Ficam as últimas -KeepVersions versões; as mais antigas e o cache de build
  com mais de uma semana são apagados.

  O nome do projeto, as imagens e os contêineres vêm do docker-compose.yml, e
  os perfis opcionais (túnel, MinIO), de COMPOSE_PROFILES no .env.

  Volta manual a uma versão guardada:

    $env:APP_TAG = "<commit>"; docker compose up -d --no-build
#>
param(
    [string]$PreviousSha = "",
    [string]$HealthUrl = "http://localhost:3000/api/health",
    [int]$HealthTimeoutSeconds = 600,
    [int]$KeepVersions = 3
)

$ErrorActionPreference = "Stop"
$builtServices = @("backend", "frontend")

function Invoke-Docker([string[]]$arguments) {
    & docker @arguments
    if ($LASTEXITCODE -ne 0) { throw "docker $($arguments -join ' ') terminou com código $LASTEXITCODE" }
}

function Get-ComposeConfig {
    $json = & docker compose config --format json
    if ($LASTEXITCODE -ne 0) { throw "docker compose config falhou" }
    return $json | ConvertFrom-Json
}

function Get-ImageRepository([object]$config, [string]$service) {
    return ($config.services.$service.image -split ":")[0]
}

function Get-RunningTag {
    # Versão em execução: a marca da imagem do backend (vazia numa instalação nova).
    $id = (& docker compose ps -q backend 2>$null)
    if (-not $id) { return "" }
    $image = (& docker inspect -f "{{.Config.Image}}" $id 2>$null)
    if ($image -notmatch ":") { return "" }
    return ($image -split ":")[-1]
}

function Test-Healthy {
    # O backend precisa ficar "healthy" (o /health dele consulta o banco e o
    # Redis) e a interface precisa entregar /api/health, o caminho público.
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $id = (& docker compose ps -q backend 2>$null)
        $state = if ($id) { & docker inspect -f "{{.State.Health.Status}}" $id 2>$null }
        if ($state -eq "healthy") {
            try {
                $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 10
                if ($response.StatusCode -eq 200) { return $true }
            } catch { }
        }
        Start-Sleep -Seconds 5
    }
    return $false
}

function Remove-OldVersions([string[]]$repositories, [string[]]$keep) {
    # Mantém "current", as versões em uso e as -KeepVersions mais recentes.
    foreach ($repository in $repositories) {
        $tags = & docker image ls $repository --format "{{.Tag}}" |
            Where-Object { $_ -and $_ -ne "<none>" -and $_ -ne "current" -and $keep -notcontains $_ }
        $old = $tags | Select-Object -Skip ([Math]::Max(0, $KeepVersions - 1))
        foreach ($tag in $old) {
            & docker image rm "${repository}:${tag}" *> $null
            if ($LASTEXITCODE -eq 0) { Write-Host "Versão antiga removida: ${repository}:${tag}" }
        }
    }
    & docker image prune -f *> $null
    & docker builder prune -f --filter "until=168h" *> $null
}

$config = Get-ComposeConfig
$project = $config.name
$repositories = $builtServices | ForEach-Object { Get-ImageRepository $config $_ } | Select-Object -Unique
$version = (& git rev-parse --short=12 HEAD).Trim()
$previousTag = Get-RunningTag

$profiles = (Get-Content .env -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*COMPOSE_PROFILES\s*=' }) -replace '^\s*COMPOSE_PROFILES\s*=\s*', ''
$hasTunnelToken = Get-Content .env -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*CLOUDFLARE_TUNNEL_TOKEN\s*=\s*\S' }
if ($hasTunnelToken -and ($profiles -notmatch 'internet')) {
    Write-Host "::warning::CLOUDFLARE_TUNNEL_TOKEN está no .env, mas COMPOSE_PROFILES não inclui 'internet': o túnel não sobe."
}

Write-Host "Implantando $version (projeto $project; em execução: $(if ($previousTag) { $previousTag } else { 'nenhuma' }); perfis: $(if ($profiles) { $profiles } else { 'nenhum' }))"

$env:APP_TAG = $version
try {
    Invoke-Docker (@("compose", "build") + $builtServices)
    Invoke-Docker @("compose", "up", "-d", "--no-build")
    if (-not (Test-Healthy)) { throw "a versão $version não ficou saudável em $HealthTimeoutSeconds s" }
    foreach ($repository in $repositories) { Invoke-Docker @("tag", "${repository}:${version}", "${repository}:current") }
    Write-Host "Versão $version no ar e saudável."
    Remove-OldVersions $repositories @($version, $previousTag)
}
catch {
    Write-Host "::error::Falha na implantação: $($_.Exception.Message)"
    $canRollBack = $previousTag -and ($repositories | ForEach-Object {
        & docker image inspect "${_}:${previousTag}" *> $null; $LASTEXITCODE -eq 0 }) -notcontains $false
    if (-not $canRollBack) {
        Write-Host "::error::Sem imagens da versão anterior para voltar; é preciso olhar a máquina."
        exit 1
    }
    Write-Host "Voltando à versão $previousTag."
    if ($PreviousSha) { & git checkout --force --detach $PreviousSha }
    $env:APP_TAG = $previousTag
    Invoke-Docker @("compose", "up", "-d", "--no-build")
    if (Test-Healthy) {
        Write-Host "::warning::A versão anterior ($previousTag) voltou ao ar."
    } else {
        Write-Host "::error::A versão anterior também não ficou saudável; é preciso olhar a máquina."
    }
    exit 1
}
