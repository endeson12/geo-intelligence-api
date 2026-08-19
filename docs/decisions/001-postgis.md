# ADR 001 — PostgreSQL com PostGIS

**Status:** aceito

## Contexto

As consultas exigem distância geodésica, envelopes e índices espaciais, não apenas armazenamento de latitude e longitude.

## Decisão

Usar PostgreSQL 16 com PostGIS, tipo `geography(Point, 4326)` e índice GiST.

## Consequências

Ganha-se semântica espacial explícita, migrações e planos de execução auditáveis. Em troca, o ambiente depende de uma extensão nativa e os testes de integração precisam de PostGIS real; a CI fornece esse serviço.
