# ADR-006 — Custo: ferramentas open source e licenças

- **Status**: Aceito, com duas ressalvas declaradas
- **Data**: 21/10/2026
- **Autoria**: \[nome da dupla\]
- **Requisito**: Custo (usar apenas ferramentas open source)

## Contexto

O critério de custo pede apenas ferramentas open source. Este registro lista a licença de cada ferramenta do MVP e declara onde há ressalva, em vez de assumir que "gratuito" significa "open source".

## Licenças das ferramentas

|                                     |                              |                    |                                     |
|-------------------------------------|------------------------------|--------------------|-------------------------------------|
| **Ferramenta**                      | **Uso**                      | **Licença**        | **Open source (OSI)?**              |
| Apache Kafka (inclui Kafka Connect) | Streaming de eventos         | Apache 2.0         | Sim                                 |
| Debezium                            | CDC do PostgreSQL            | Apache 2.0         | Sim                                 |
| PostgreSQL 16                       | Banco de origem              | Licença PostgreSQL | Sim                                 |
| Python e FastAPI                    | Worker e API                 | PSF e MIT          | Sim                                 |
| Docker Engine e Compose             | Execução dos contêineres     | Apache 2.0         | Sim                                 |
| MongoDB 7 Community                 | Camada bronze                | SSPL v1            | Não: gratuito, mas source-available |
| Redis 7.4                           | Métricas e janela antifraude | RSALv2 ou SSPLv1   | Não: gratuito, mas source-available |

## Decisão

O MVP não tem custo de licença. As duas ferramentas que não são open source segundo a OSI foram mantidas de forma consciente e têm saída definida:

- **Redis (diferencial, não obrigatório):** não faz parte do caminho obrigatório (RF01 e RF02: origem, Kafka e camada bronze). Se a licença for um impedimento, ele pode ser retirado sem afetar esses requisitos, e as métricas e o alerta passam a ser calculados a partir do bronze. Como evolução, usar uma alternativa de licença aberta.

- **MongoDB (bronze):** aceito no laboratório porque é gratuito e guarda o JSON do evento sem esquema; a ShopVibe o usaria apenas internamente, sem oferecê-lo como serviço a terceiros, que é o caso restringido pela SSPL. Em produção, a alternativa open source é guardar o bronze em **PostgreSQL (JSONB)** ou em arquivos em formato aberto (Parquet) em armazenamento de objetos.

## Alternativas consideradas

- **Serviços gerenciados pagos:** menos operação, mas custo recorrente e dependência do fornecedor.

- **Trocar agora toda a pilha por equivalentes OSI:** eliminaria a ressalva, mas aumentaria o esforço e o risco dentro do prazo.

## Consequências

- Positivas: custo de licença zero e transparência sobre as ressalvas.

- Negativas: a pilha atual não é 100% open source pelo critério da OSI; retirar o Redis ou migrar o bronze para PostgreSQL (JSONB) exige retrabalho e testes.

- Custo de infraestrutura (servidores, operação) não é zero e depende do dimensionamento do ADR-005.
