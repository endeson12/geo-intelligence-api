# Política de segurança

## Versões suportadas

Enquanto o projeto estiver em fase demonstrativa, apenas a branch principal recebe correções.

## Reporte responsável

Não publique vulnerabilidades em issues. Envie um aviso privado ao mantenedor pelo recurso **Security advisories** do repositório, com versão, impacto, reprodução mínima e mitigação sugerida. Não inclua dados pessoais ou segredos. O recebimento será confirmado quando possível; prazos de correção dependem da severidade e da disponibilidade do projeto, sem SLA comercial.

## Modelo de ameaça resumido

Principais riscos: chave de importação exposta, GeoJSON abusivo, exaustão por consultas espaciais, SQL injection, vazamento de localização e dependências/tiles externos. Há validação e limite de payload lógico, SQL parametrizado, transação, usuário de contêiner não-root e headers defensivos. Para produção ainda são obrigatórios TLS no proxy, OIDC/RBAC, rate limiting, limites de corpo, rotação de segredo, backups testados e observabilidade protegida.
