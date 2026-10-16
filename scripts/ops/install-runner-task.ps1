<#
.SYNOPSIS
  (Re)cria a tarefa agendada que mantém o runner do GitHub (rótulo
  "producao") rodando na máquina de produção.

.DESCRIPTION
  O Docker Desktop só funciona com o usuário conectado ao Windows, então o
  runner também roda na sessão dele (como serviço do Windows, ele subiria sem
  Docker). A tarefa anterior tinha só o gatilho de logon e "reiniciar se
  falhar", que o Agendador aplica quando a tarefa não consegue iniciar, e não
  quando o processo termina depois: em 10/10/2026, a janela do runner foi
  fechada e ele ficou parado três dias, com implantações na fila.

  Agora:
    - o Docker Desktop é aberto antes do runner, se não estiver rodando;
    - o runner roda num laço (se o processo terminar, volta em 30 s);
    - além do logon, um gatilho repete a cada 5 minutos: se a tarefa não
      estiver em execução, ela é iniciada de novo (uma instância por vez).

  Uso (PowerShell do próprio usuário, na pasta do projeto):
    pwsh scripts/ops/install-runner-task.ps1 [-RunnerDir C:\actions-runner]
#>
param(
    [string]$RunnerDir = "C:\actions-runner",
    [string]$TaskName = "GitHub Actions Runner (producao)"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path (Join-Path $RunnerDir "run.cmd"))) { throw "run.cmd não encontrado em $RunnerDir" }

# Antes de cada início do runner, o Docker Desktop: ele não estava configurado
# para abrir no logon, e depois de uma queda de energia (15/10/2026) a máquina
# voltou com o runner no ar e o sistema fora até alguém abrir o Docker.
$docker = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
$ensureDocker = "if (-not (Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue)) { Start-Process '$docker' }"
$loop = "Set-Location '$RunnerDir'; while (`$true) { $ensureDocker; & .\run.cmd *>> '$RunnerDir\runner.log'; Start-Sleep -Seconds 30 }"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $RunnerDir `
    -Argument "-NoProfile -WindowStyle Hidden -Command `"$loop`""

$user = "$env:USERDOMAIN\$env:USERNAME"
$atLogon = New-ScheduledTaskTrigger -AtLogOn -User $user
$watchdog = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 5)

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($atLogon, $watchdog) `
    -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Tarefa '$TaskName' registrada (logon + verificação a cada 5 min) e iniciada."
