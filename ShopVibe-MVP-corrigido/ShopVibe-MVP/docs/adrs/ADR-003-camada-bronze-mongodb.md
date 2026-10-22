# ADR-003 — Camada bronze (eventos brutos) em MongoDB

- **Status**: Aceito, com ressalva de licença (ver ADR-006)
- **Data**: 21/10/2026
- **Autoria**: \[nome da dupla\]
- **Requisito**: RF02 (obrigatório); durabilidade

## Contexto

Além de transportar os eventos, a ShopVibe precisa guardá-los como chegaram para poder reprocessar: por exemplo, quando uma regra antifraude mudar, quando for preciso auditar um chargeback ou quando houver um erro no processamento. O Kafka guarda apenas 7 dias, então é necessária uma camada bruta (bronze) própria.

## Decisão

Um worker Python consome o tópico e grava o **envelope CDC completo, sem transformação**, na coleção `raw_events` do **MongoDB** (camada bronze), junto com tópico, partição, offset e horário de recebimento. O identificador do evento (`topico:partição:offset`) tem índice único, de modo que o mesmo evento nunca é gravado duas vezes. O offset do Kafka só é confirmado depois da gravação.

## Alternativas consideradas

- **PostgreSQL com JSONB:** menos componentes e licença open source; porém mistura a carga de histórico com a do banco transacional, a menos que se crie uma instância separada.

- **Arquivos JSON/Parquet em armazenamento de objetos:** é o padrão de data lake e barato, porém mais trabalhoso de consultar e de tornar idempotente no prazo do MVP.

- **Apenas Kafka com retenção longa:** simples, mas custo de disco alto e consulta limitada.

- **Redis:** guarda em memória e não serve como histórico definitivo.

## Consequências positivas

- O documento JSON guarda o evento como veio, sem esquema fixo, e é fácil de consultar.

- A gravação é idempotente: se o worker reiniciar, o reprocessamento não duplica eventos.

- Separa o histórico bruto (bronze) das métricas rápidas, que podem ser reconstruídas a partir dele.

## Consequências negativas e limitações

- O MongoDB Community usa a licença SSPL, que é gratuita mas **não é aprovada pela OSI** (source-available). O tratamento está no ADR-006.

- MongoDB, Redis e offsets do Kafka não participam de uma transação única; uma falha entre a gravação e a confirmação do offset causa reprocessamento, que a idempotência absorve.

- É mais um sistema para operar e fazer backup.

## Evolução

Criar camadas silver e gold para análise e, se necessário, migrar o bronze para um formato aberto em armazenamento de objetos.

## Validação

No vídeo: consultar `db.raw_events` no `mongosh` e ver o evento do pedido recém-criado.
