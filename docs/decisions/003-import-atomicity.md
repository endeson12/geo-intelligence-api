# ADR 003 — importação validada e atômica

**Status:** aceito

## Contexto

Um lote parcialmente importado dificulta auditoria e pode misturar versões de dados.

## Decisão

Validar toda a `FeatureCollection` antes de persistir e consolidar o lote em uma única transação. Qualquer erro causa rollback. A mutação exige `X-API-Key` no protótipo.

## Consequências

Lotes inválidos não deixam estado parcial, mas o limite atual de 10 mil feições e a transação única não servem para cargas muito grandes. Evoluções futuras devem usar jobs assíncronos, idempotência, versão de lote, relatório de rejeições e RBAC.
