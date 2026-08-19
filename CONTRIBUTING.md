# Contribuindo

1. Abra uma issue descrevendo problema, contrato e impacto geoespacial.
2. Use Python 3.12 e `uv sync --all-groups`.
3. Crie branch curta e commits objetivos; não inclua dados pessoais, credenciais ou dados sem licença.
4. Adicione primeiro um teste que reproduza o comportamento; implemente e refatore com a suíte verde.
5. Rode `make lint type test` e, para mudanças de esquema, valide `alembic upgrade head` em PostGIS 16.
6. No PR, documente decisões de CRS, precisão, proveniência, migração e riscos LGPD.

Mudanças incompatíveis exigem versionamento de API e plano de migração. Ao contribuir, você concorda com a licença MIT do projeto.
