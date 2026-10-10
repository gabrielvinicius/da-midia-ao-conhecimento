<#
.SYNOPSIS
  Implanta a versão já posta na pasta de produção: reconstrói as imagens, sobe
  os contêineres e confere a saúde; se algo falhar, volta às imagens anteriores.

.DESCRIPTION
  Chamado pelo workflow "Deploy" (.github/workflows/deploy.yml), no runner da
  máquina de produção, depois que o workflow já pôs o código na versão nova.
  Pode ser rodado à mão na pasta de produção:

    pwsh scripts/ops/deploy.ps1 -PreviousSha <commit em produção antes>

  O nome do projeto do Compose é fixo (video-summarizer) para que a pasta de
  produção reaproveite os contêineres e os volumes existentes.
#>
param(
    [string]$PreviousSha = "",
    [string]$Project = "video-summarizer",
    [string]$HealthUrl = "http://localhost:3000/api/health",
    [int]$HealthTimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"
$images = @("app", "frontend")
$compose = @("compose", "-p", $Project)

# O túnel da Cloudflare é opcional: só entra com o token no .env. Sem ele, o
# contêiner cloudflared subiria sem credencial e ficaria reiniciando, e a
# plataforma continua acessível na rede local (porta 3000).
$tunnelToken = Get-Content .env -ErrorAction SilentlyContinue |
    Where-Object { $_ -match '^\s*CLOUDFLARE_TUNNEL_TOKEN\s*=\s*\S' }
if ($tunnelToken) {
    $compose += @("--profile", "internet")
    Write-Host "Túnel da Cloudflare ligado (CLOUDFLARE_TUNNEL_TOKEN definido)."
} else {
    Write-Host "Sem túnel da Cloudflare: acesso pela rede local, porta 3000."
}

function Invoke-Docker([string[]]$arguments) {
    & docker @arguments
    if ($LASTEXITCODE -ne 0) { throw "docker $($arguments -join ' ') terminou com código $LASTEXITCODE" }
}

function Test-Healthy {
    # O backend precisa ficar "healthy" (o /health dele consulta o banco e o
    # Redis) e a interface precisa entregar /api/health, o caminho público.
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $state = (& docker inspect -f "{{.State.Health.Status}}" backend 2>$null)
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

function Save-PreviousImages {
    foreach ($name in $images) {
        & docker image inspect "${name}:latest" *> $null
        if ($LASTEXITCODE -eq 0) { Invoke-Docker @("tag", "${name}:latest", "${name}:previous") }
    }
}

function Restore-PreviousImages {
    foreach ($name in $images) {
        & docker image inspect "${name}:previous" *> $null
        if ($LASTEXITCODE -eq 0) { Invoke-Docker @("tag", "${name}:previous", "${name}:latest") }
    }
}

$sha = (& git rev-parse --short HEAD).Trim()
Write-Host "Implantando $sha (projeto $Project)"

Save-PreviousImages
try {
    Invoke-Docker ($compose + @("build", "backend", "frontend"))
    Invoke-Docker ($compose + @("up", "-d", "--no-build"))
    if (-not (Test-Healthy)) { throw "a versão $sha não ficou saudável em $HealthTimeoutSeconds s" }
    Write-Host "Versão $sha no ar e saudável."
}
catch {
    Write-Host "::error::Falha na implantação: $($_.Exception.Message). Voltando à versão anterior."
    Restore-PreviousImages
    if ($PreviousSha) { & git checkout --force --detach $PreviousSha }
    Invoke-Docker ($compose + @("up", "-d", "--no-build"))
    if (Test-Healthy) {
        Write-Host "::warning::A versão anterior ($PreviousSha) voltou ao ar."
    } else {
        Write-Host "::error::A versão anterior também não ficou saudável; é preciso olhar a máquina."
    }
    exit 1
}
