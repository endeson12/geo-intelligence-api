# Operação e recuperação

Este runbook descreve o ambiente demonstrativo. Não constitui SLA nem comprova operação em produção.

## Verificação inicial

```bash
docker compose config
docker compose up --build -d
docker compose ps
curl -fsS http://localhost:8000/health/live
curl -fsS http://localhost:8000/health/ready
```

## Diagnóstico

1. use o `X-Request-ID` para correlacionar resposta e log JSON;
2. consulte `docker compose logs --since=15m api db`;
3. valide `/metrics` apenas em rede administrativa;
4. confirme a migração com `docker compose exec api alembic current`.

## Backup demonstrativo

```bash
docker compose exec -T db pg_dump -U geo -d geo -Fc > geo.dump
```

O arquivo pode conter dados sensíveis em um ambiente real: criptografe, controle acesso, defina retenção e teste restauração periodicamente.

## Restauração em banco descartável

```bash
docker compose exec -T db createdb -U geo geo_restore
docker compose exec -T db pg_restore -U geo -d geo_restore --clean --if-exists < geo.dump
docker compose exec -T db psql -U geo -d geo_restore -c 'SELECT count(*) FROM facilities;'
```

> Estes comandos estão documentados, mas a restauração não é anunciada como validada neste repositório até existir uma execução automatizada pública.

## Rollback

- aplicação: volte para uma tag aprovada e reconstrua a imagem;
- schema: prefira migração corretiva; `alembic downgrade` exige avaliação de perda de dados;
- dataset: mantenha lote/versionamento antes de substituir dados institucionais.
