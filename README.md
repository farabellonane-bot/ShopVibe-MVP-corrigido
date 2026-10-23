# ShopVibe — Ingestão de dados em tempo real (MVP)

Projeto didático para demonstrar o caminho **PostgreSQL → Debezium/Kafka Connect → Kafka → Worker Python → MongoDB/Redis → FastAPI**.

O caso de uso é a ShopVibe, um e-commerce fictício que perde vendas por não enxergar a loja em tempo real. O foco obrigatório é a **captura e ingestão dos pedidos**: cada pedido novo chega ao Kafka em segundos (RF01) e os eventos brutos ficam guardados na **camada bronze** (RF02). Veja o desenho em [`docs/desenho-solucao.png`](docs/desenho-solucao.png) e as decisões em [`docs/adrs/`](docs/adrs/).

> Este é um MVP local de demonstração. Um único broker Kafka com fator de replicação 1 não oferece alta disponibilidade contra perda do broker. Não use as senhas deste ambiente em produção.

## Requisitos

- Docker Desktop com Docker Compose funcionando
- Aproximadamente 5 GB de espaço livre para baixar as imagens
- Navegador para acessar a API

## 1. Subir a infraestrutura

Abra o terminal (PowerShell no Windows, ou Bash) na pasta que contém `docker-compose.yml` e execute. Os comandos abaixo funcionam nos dois, exceto onde houver indicação:

```bash
docker compose up -d --build
docker compose ps
```

A primeira inicialização pode levar alguns minutos. Confira os logs se algum serviço não ficar saudável:

```bash
docker compose logs --tail=100 postgres
docker compose logs --tail=100 kafka
docker compose logs --tail=100 connect
docker compose logs --tail=100 connector-init
docker compose logs --tail=100 worker
```

O serviço `connector-init` registra o conector PostgreSQL no Kafka Connect. Para conferir o status:

- `http://localhost:8083/connectors`
- `http://localhost:8083/connectors/shopvibe-postgres-connector/status`

O tópico esperado é `shopvibe.public.orders`.

## 2. Criar pedidos de demonstração

Em outro terminal:

```bash
docker compose --profile demo up -d simulator
docker compose logs -f simulator
```

O simulador cria um pedido a cada dois segundos. Para parar apenas o simulador:

```bash
docker compose stop simulator
```

Também é possível inserir um pedido manualmente, em uma linha só (sem entrar no `psql`):

```powershell
docker exec shopvibe-postgres psql -U shopvibe -d shopvibe -c "INSERT INTO orders (customer_id, total, status) VALUES (999, 42.90, 'created');"
```

> Se preferir o modo interativo (`docker exec -it shopvibe-postgres psql -U shopvibe -d shopvibe`), lembre-se de que o prompt `shopvibe=#` é do PostgreSQL: comandos do Docker só funcionam depois de sair com `\q`.

## 3. Demonstrar a API

Abra:

- Swagger interativo: http://localhost:8000/docs
- Saúde dos serviços: http://localhost:8000/health
- Vendas de hoje: http://localhost:8000/vendas/hoje
- Pedido (troque `1` por um ID existente): http://localhost:8000/pedidos/1
- Alertas: http://localhost:8000/alertas/fraude
- Eventos brutos: http://localhost:8000/eventos/brutos

O processamento pode levar alguns segundos na primeira execução enquanto o conector e o worker iniciam.

## 4. Comandos de diagnóstico

```bash
docker compose ps
docker compose logs -f connect
docker compose logs -f worker
docker exec shopvibe-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

Para ver as mensagens do tópico (escreva em **uma linha só**; no PowerShell o `\` de fim de linha não funciona):

```powershell
docker exec -it shopvibe-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic shopvibe.public.orders --from-beginning
```

Sem `--from-beginning`, o consumidor mostra apenas eventos novos, o que é melhor para ver um pedido recém-criado chegando em tempo real.

Para conferir a camada bronze (eventos brutos no MongoDB):

```powershell
docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.countDocuments({})'
docker exec shopvibe-mongo mongosh shopvibe --quiet --eval 'db.raw_events.find().sort({$natural:-1}).limit(1).pretty()'
```

## 5. Encerrar

```bash
docker compose down
```

Para apagar também os dados persistidos (**irreversível**; não use antes de entregar ou gravar a demonstração):

```bash
docker compose down -v
```

## Arquitetura e correções importantes

1. **CDC real:** Debezium lê o WAL lógico do PostgreSQL; não há polling de tabela nem publicação manual no produtor.
2. **Eventos brutos (camada bronze):** a coleção `raw_events` do MongoDB guarda o envelope CDC e metadados de tópico/partição/offset. O identificador de evento impede gravar o mesmo offset duas vezes.
3. **Idempotência:** o worker grava o evento bruto e a visão atual do pedido com upsert e usa uma chave de evento Redis antes de incrementar os contadores. O commit do offset Kafka só ocorre depois do processamento.
4. **Métricas:** Redis mantém contagem e soma de eventos de criação do dia. O snapshot inicial serve para popular a visão dos pedidos, sem incrementar as métricas.
5. **Janela de fraude:** Sorted Set do Redis mantém os timestamps de pedidos por cliente e remove itens anteriores a 120 segundos.
6. **API:** FastAPI expõe vendas do dia, pedido por ID, alertas, health check e uma rota auxiliar para demonstrar eventos brutos.
7. **Limitação de garantia:** MongoDB, Redis e offsets Kafka não participam de uma transação distribuída. A idempotência reduz duplicações em reinícios, mas uma falha entre escrita no MongoDB e marcação da chave Redis ainda exige reconciliação para garantias fortes. Para produção, considerar inbox/outbox transacional, processamento idempotente com estado durável e testes de recuperação.
8. **Escala:** um broker Kafka e fator de replicação 1 são suficientes para laboratório, não para tolerância à perda de nó. Para produção seriam necessários múltiplos brokers, replicação, monitoramento, autenticação, segredos e políticas de retenção adequadas.
9. **Regra de fraude:** a demonstração gera alerta quando o cliente supera cinco pedidos dentro de 120 segundos. Para não disparar alertas repetidos por eventos duplicados, o alerta é identificado pelo cliente e pelo pedido que cruzou o limite.

## Requisitos cobertos

**Obrigatórios do trabalho**

- RF01: capturar cada pedido novo por CDC e disponibilizá-lo em um tópico do Kafka em poucos segundos.
- RF02: armazenar os eventos brutos para reprocessamento (camada bronze, coleção `raw_events`).

**Diferenciais implementados** (além do obrigatório)

- Contagem e soma de pedidos do dia no Redis.
- Consulta de métricas e pedidos pela API REST (FastAPI).
- Alerta de fraude para cliente com mais de cinco pedidos em 120 segundos.

## Não confundir demonstração com produção

O ambiente valida o fluxo funcional e facilita uma apresentação reproduzível. A meta de 300 mil pedidos/dia e disponibilidade sem perda precisa de teste de carga, monitoramento e configuração de alta disponibilidade; não é comprovada apenas por iniciar os contêineres.

## Documentação da entrega

- [`docs/adrs/`](docs/adrs/): seis registros de decisão (Kafka, CDC com Debezium, camada bronze, Redis e FastAPI, durabilidade e escalabilidade, custo e licenças).
- [`docs/desenho-solucao.png`](docs/desenho-solucao.png) e [`.pdf`](docs/desenho-solucao.pdf): desenho da solução, com o que foi implementado e o que fica como evolução.
- [`docs/roteiro-demonstracao.md`](docs/roteiro-demonstracao.md): roteiro do vídeo de até 5 minutos.
- [`docs/comandos.md`](docs/comandos.md): lista dos comandos usados para reproduzir a demonstração.

## Licenças

O código deste repositório usa a licença MIT (arquivo `LICENSE`). Kafka, Kafka Connect, Debezium, PostgreSQL, Python e FastAPI têm licenças open source. O MongoDB Community (SSPL) e o Redis 7.4 (RSALv2/SSPLv1) são gratuitos, mas **não são open source segundo a OSI**; essa ressalva e o plano de saída estão no [ADR-006](docs/adrs/ADR-006-custo-e-licencas.md).
