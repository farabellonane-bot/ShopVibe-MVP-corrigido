# ADR-004 — Redis e FastAPI para consulta (diferencial)

- **Status**: Aceito para o MVP, com ressalva de licença (ver ADR-006)
- **Data**: 21/10/2026
- **Autoria**: \[nome da dupla\]
- **Requisito**: Diferencial (não obrigatório): painel de vendas e alerta de fraude

## Contexto

A diretoria quer um painel ao vivo de vendas e o time antifraude quer ser alertado em segundos. Painel e alertas não precisam ser construídos neste trabalho, mas o MVP inclui uma primeira versão para mostrar que o fluxo já serve ao negócio.

## Decisão

Usar o **Redis** para os contadores de pedidos e valor do dia e para uma janela deslizante de 120 segundos por cliente (Sorted Set). A regra de alerta é: **mais de 5 pedidos do mesmo cliente em 120 segundos**. Usar o **FastAPI** para expor `/health`, `/vendas/hoje`, `/pedidos/{id}`, `/alertas/fraude` e `/eventos/brutos`, com documentação Swagger automática.

## Alternativas consideradas

- **Calcular tudo no PostgreSQL com consultas:** simples, mas coloca a carga analítica no banco que atende o site.

- **Consultar direto a coleção bruta do MongoDB:** funciona, mas é lento para métricas e para janelas de tempo.

- **Flask em vez de FastAPI:** exige mais montagem manual de validação e documentação.

## Consequências positivas

- Leitura em milissegundos e estrutura adequada para janelas de tempo.

- API documentada e separada do processamento, o que facilita trocar o consumidor (por exemplo, um painel de BI).

- As métricas podem ser reconstruídas a partir da camada bronze.

## Consequências negativas e limitações

- O Redis guarda dados em memória; a persistência é limitada e o estado pode ser perdido numa falha.

- O Redis 7.4 usa licenças RSALv2/SSPLv1, que não são open source segundo a OSI; alternativa no ADR-006.

- A API não tem autenticação no MVP e depende de MongoDB e Redis.

## Evolução

Painel ao vivo consumindo a API, notificação ao time antifraude e serviço de estoque lendo o mesmo tópico.
