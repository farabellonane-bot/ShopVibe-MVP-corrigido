# ShopVibe MVP - sobe o ambiente completo e confirma que o pipeline esta funcionando.
#
# Uso (PowerShell, na pasta do projeto):
#   .\start.ps1                  sobe tudo (mantem os dados existentes)
#   .\start.ps1 -Limpo           apaga containers e VOLUMES antes (recomeca do zero)
#   .\start.ps1 -SemSimulador    sobe tudo, mas deixa o simulador parado (ex.: para gravar a demo)
#
# Se a execucao de scripts estiver bloqueada:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

param(
    [switch]$Limpo,
    [switch]$SemSimulador
)

# "Continue" de proposito: o docker compose escreve progresso no stderr e o PowerShell 5.1
# trataria isso como erro. O sucesso e verificado por $LASTEXITCODE.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Falhar($msg) {
    Write-Host ""
    Write-Host "ERRO: $msg" -ForegroundColor Red
    Write-Host "Dica: docker compose logs --tail=100 <servico>   (connector-init, connect, kafka, worker...)" -ForegroundColor Yellow
    exit 1
}

# 0. Docker Desktop precisa estar aberto
docker info *> $null
if ($LASTEXITCODE -ne 0) { Falhar "Docker nao esta respondendo. Abra o Docker Desktop e tente de novo." }

# 1. Limpeza
if ($Limpo) {
    Write-Host "== Removendo containers e volumes (dados serao apagados) ==" -ForegroundColor Yellow
    docker compose --profile demo down -v --remove-orphans
}

# 2. Container 'simulator' antigo (de versoes com profile) pode estar apontando para uma
#    rede que ja nao existe ("network ... not found"). Remove para o compose recriar.
$velho = docker ps -aq --filter "name=^shopvibe-simulator$"
if ($velho) { docker rm -f shopvibe-simulator *> $null }

# 3. Subir
Write-Host "== Subindo servicos ==" -ForegroundColor Cyan
docker compose up -d --build --remove-orphans
if ($LASTEXITCODE -ne 0) { Falhar "docker compose up falhou." }

# 4. Conector Debezium RUNNING
Write-Host "== Aguardando conector Debezium ficar RUNNING ==" -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $st = Invoke-RestMethod "http://localhost:8083/connectors/shopvibe-postgres-connector/status" -TimeoutSec 5
        if ($st.connector.state -eq "RUNNING" -and $st.tasks.Count -gt 0 -and $st.tasks[0].state -eq "RUNNING") { $ok = $true; break }
        if ($st.tasks.Count -gt 0 -and $st.tasks[0].state -eq "FAILED") { Falhar "Task do conector em FAILED: $($st.tasks[0].trace)" }
    } catch { }
    Start-Sleep 3
}
if (-not $ok) { Falhar "Conector nao ficou RUNNING em 3 minutos." }
Write-Host "Conector RUNNING." -ForegroundColor Green

# 5. Topico existe
$topicos = docker exec shopvibe-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
if (-not ($topicos -contains "shopvibe.public.orders")) { Falhar "Topico shopvibe.public.orders nao existe." }
Write-Host "Topico shopvibe.public.orders existe." -ForegroundColor Green

# 6. Simulador
if ($SemSimulador) {
    docker compose stop simulator *> $null
    Write-Host "Simulador parado (-SemSimulador). Para ligar: docker compose start simulator" -ForegroundColor Yellow
} else {
    # 7. Teste ponta a ponta: pedidos do simulador precisam chegar ate o MongoDB
    Write-Host "== Verificando fluxo ponta a ponta (Postgres -> Kafka -> Worker -> Mongo) ==" -ForegroundColor Cyan
    $fluxo = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep 3
        $n = (docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.countDocuments({})' | Out-String).Trim()
        if ($n -match "^\d+$" -and [int]$n -gt 0) { $fluxo = $true; break }
    }
    if (-not $fluxo) { Falhar "Nenhum evento chegou ao MongoDB em 60s. Veja: docker compose logs --tail=50 worker" }
    Write-Host "Eventos chegando ao MongoDB (raw_events = $n)." -ForegroundColor Green
}

Write-Host ""
docker compose ps
Write-Host ""
Write-Host "Pipeline no ar." -ForegroundColor Green
Write-Host "  API:      http://localhost:8000/docs"
Write-Host "  Vendas:   http://localhost:8000/vendas/hoje"
Write-Host "  Alertas:  http://localhost:8000/alertas/fraude"
Write-Host "  Conector: http://localhost:8083/connectors/shopvibe-postgres-connector/status"
