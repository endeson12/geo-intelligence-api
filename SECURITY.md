# Política de segurança

## Versões suportadas

Enquanto o projeto estiver em fase demonstrativa, apenas a branch principal recebe correções.

## Reporte responsável

Não publique vulnerabilidades em issues. Envie um aviso privado ao mantenedor pelo recurso **Security advisories** do repositório, com versão, impacto, reprodução mínima e mitigação sugerida. Não inclua dados pessoais ou segredos. O recebimento será confirmado quando possível; prazos de correção dependem da severidade e da disponibilidade do projeto, sem SLA comercial.

## Modelo de ameaça resumido

Principais riscos: chave de importação exposta, GeoJSON abusivo, exaustão por consultas espaciais, SQL injection, conteúdo externo no mapa, vazamento de localização e dependências/tiles externos. Há validação e limite de payload lógico, paginação territorial, renderização segura como texto, SQL parametrizado, transação, usuário de contêiner não-root e headers defensivos. Para produção ainda são obrigatórios TLS no proxy, OIDC/RBAC, rate limiting, limites de corpo, rotação de segredo, backups testados e observabilidade protegida.

## Ativos e fronteiras de confiança

- **Ativos:** banco espacial, credencial de importação, proveniência dos datasets, logs e metadados de localização.
- **Entrada pública:** consultas de leitura, parâmetros espaciais e carregamento do mapa.
- **Entrada privilegiada:** importação de GeoJSON; a API key é apenas um controle demonstrativo.
- **Terceiros:** CDN do Leaflet, tiles OpenStreetMap, imagens-base e dependências Python.

## Controles verificáveis

- validação Pydantic, CRS explícito, topologia, geometria vazia e limites WGS84/quantidade;
- consultas parametrizadas e índice espacial;
- resposta territorial paginada e limitada a 500 feições;
- popups e opções da demo construídos com DOM seguro e `textContent`;
- ciclo real de upgrade/downgrade na CI e reconstrução concorrente de índices espaciais;
- importação idempotente por hash, lote versionado e rollback;
- contêiner não-root, filesystem somente leitura e `no-new-privileges`;
- CI com Ruff, mypy, testes contra PostGIS, `pip-audit`, SBOM CycloneDX, build da imagem e Trivy para vulnerabilidades críticas conhecidas;
- `.env.example` sem segredo operacional.

## Riscos aceitos no protótipo

Não há OIDC, RBAC, rate limiting, WAF, limite de corpo em bytes, criptografia de backup nem trilha de auditoria por ator. `/metrics` também deve ficar fora da internet pública em uma implantação real. Essas limitações impedem classificar o projeto como pronto para produção.
