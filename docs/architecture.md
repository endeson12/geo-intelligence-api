# Arquitetura

## Contexto

A aplicação demonstra uma API geoespacial B2B/B2G sem alegar operação institucional. O objetivo é tornar consultas territoriais reproduzíveis e auditáveis, separando ingestão, validação, persistência espacial e leitura.

## Componentes

```mermaid
flowchart LR
  OSM[Overpass / OSM] --> FETCH[Coleta reproduzível]
  IBGE[API de Malhas / IBGE] --> TERR[Importação territorial]
  FETCH --> QUALITY[Relatório de qualidade]
  QUALITY --> IMPORT[Importação autenticada e lote idempotente]
  IMPORT --> PG[(PostgreSQL + PostGIS)]
  TERR --> PG
  CLIENT[Analista / sistema] --> API[FastAPI]
  MAP[Mapa Leaflet] --> API
  API --> PG
  API --> OBS[Logs JSON / métricas]
```

## Fronteiras

- `scripts/`: coleta, validação e seed fora do tráfego HTTP;
- `src/geo_intelligence_api/api.py`: contratos e casos de uso HTTP;
- `database.py` e `models.py`: persistência e tipos espaciais;
- `migrations/`: extensão PostGIS, lotes, territórios e índices GiST;
- `tests/`: contratos, falhas e integração PostGIS real na CI.

## Decisões

- [ADR 001 — PostgreSQL/PostGIS](decisions/001-postgis.md)
- [ADR 002 — CRS EPSG:4326](decisions/002-crs.md)
- [ADR 003 — importação atômica](decisions/003-import-atomicity.md)

## Limites deliberados

Monólito modular, API key única e cobertura radial são escolhas de demonstração. O catálogo atual registra lote, versão declarada, hash e proveniência, mas não substitui reconciliação por identificador externo nem uma plataforma de governança. O uso institucional exige identidade federada, autorização granular, revisão de qualidade e operação com SLOs.
