# Changelog

Todas as mudanças relevantes deste projeto demonstrativo são registradas aqui.

## [0.5.0] — 2026-08-20

### Adicionado

- 123 bairros oficiais da Malha de Bairros do Censo 2022 do IBGE, com SHA-256, CRS e proveniência;
- hierarquia de territórios e endpoint de catálogo por tipo e município;
- limite do corpo HTTP pelos bytes efetivamente recebidos;
- rate limiting local com cabeçalhos de quota e `Retry-After`.

### Segurança

- toda execução exige API key explícita com pelo menos 32 caracteres;
- API key comparada em tempo constante;
- documentação distingue controles locais de OIDC/RBAC, gateway, WAF e quotas distribuídas.

## [0.4.1] — 2026-08-19

### Corrigido

- o verificador destrutivo de migrações agora exige opt-in e banco dedicado `_migration_test`;
- limites territoriais com coordenadas 3D são rejeitados antes do `INSERT` PostGIS;
- a integração PostGIS percorre páginas sucessivas, valida ordenação, total, próxima página e filtro.

## [0.4.0] — 2026-08-19

### Segurança e confiabilidade

- atributos externos da demonstração são inseridos por DOM seguro, sem interpolação de HTML;
- limites territoriais exigem CRS explícito, geometria válida, não vazia e coordenadas WGS84;
- respostas territoriais possuem paginação e limite máximo de 500 equipamentos;
- distância radial usa `geography` de forma consistente no filtro, ordenação e resposta;
- índices espaciais são reconstruídos concorrentemente para evitar bloqueio prolongado de escritas;
- CI executa upgrade, downgrade e novo upgrade em PostGIS real, preservando um registro legado.

### Alterado

- endpoint territorial agora informa total, retornados, limite, offset e próxima página;
- documentação de segurança, fontes e operação atualizada com os controles verificáveis.

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
