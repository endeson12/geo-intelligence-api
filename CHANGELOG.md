# Changelog

Todas as mudanças relevantes deste projeto demonstrativo são registradas aqui.

## [0.3.0] — 2026-08-19

### Adicionado

- lotes persistentes, hash SHA-256, catálogo e reimportação idempotente;
- limite municipal simplificado do IBGE com proveniência e importador reproduzível;
- endpoint territorial baseado em `ST_Covers` e testes PostGIS;
- índice GiST funcional para consultas `geography` e benchmark com `EXPLAIN (ANALYZE, BUFFERS)`;
- `pip-audit`, SBOM CycloneDX e artefatos de evidência na CI;
- demonstração estática pública via GitHub Pages e vídeo curto versionado.

### Alterado

- FastAPI, Starlette, instrumentação Prometheus e pytest atualizados;
- README e documentação de fontes atualizados com distinção entre demo, CI e produção.

## [0.2.0] — 2026-08-19

### Adicionado

- mapa reformulado com filtros e consulta de cobertura ao clicar;
- cobertura em GeoJSON com feições e resumo;
- pipeline e relatório versionado de qualidade da amostra OSM;
- documentação de arquitetura, ADRs e operação/recuperação;
- threat model ampliado e varredura Trivy da imagem na CI;
- screenshot reproduzível da interface local.

### Alterado

- limites e healthcheck dos serviços no Compose;
- README orientado a problema, decisão, evidências e limitações.

## [0.1.1] — 2026-08-19

- correção do teste de autenticação configurável na CI;
- atualização das Actions para runtime Node atual;
- validação da release contra PostGIS real.

## [0.1.0] — 2026-08-19

- primeira versão pública do protótipo geoespacial.
