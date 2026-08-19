# Fontes e qualidade dos dados

## Conjuntos incluídos

### Seed sintético

`scripts/seed.py` insere quatro pontos inventados, identificados como `DADO SINTÉTICO — DEMONSTRAÇÃO`. Eles servem apenas para validar a aplicação sem depender de rede ou de uma instituição externa.

### Amostra OpenStreetMap

`data/osm-teresina-health.geojson` é uma fotografia reproduzível de equipamentos de saúde mapeados pela comunidade em Teresina. Ela foi gerada por `scripts/fetch_osm.py` pela Overpass API.

- **Fonte:** OpenStreetMap contributors
- **Licença:** [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
- **Atribuição:** preservada em `properties.fonte`
- **Data-base OSM da fotografia:** `2026-08-19T13:37:17Z`
- **Consulta:** `amenity` igual a `hospital`, `clinic` ou `doctors` na área administrativa chamada Teresina

A amostra **não é um cadastro oficial**. Cobertura, atualização, nomes e classificação podem estar incompletos ou incorretos. O arquivo existe para demonstrar ingestão, proveniência e validação; uma decisão institucional deve usar uma fonte autorizada e critérios de qualidade acordados.

## Reproduzir a coleta

```bash
uv run python scripts/fetch_osm.py
```

A Overpass API é um serviço comunitário e pode aplicar limites. Evite execuções frequentes, identifique o cliente e preserve a atribuição.

## Checklist antes de uso institucional

1. Definir responsável, finalidade, fonte autorizada e base legal.
2. Registrar data de referência, licença, cobertura territorial e frequência de atualização.
3. Validar CRS, geometrias, duplicidades, campos obrigatórios e valores aceitos.
4. Medir completude, consistência, acurácia posicional e atualidade.
5. Tratar coordenadas sensíveis e dados pessoais conforme LGPD e política interna.
6. Manter linhagem, versão do lote, relatório de rejeições e possibilidade de rollback.
7. Fazer revisão amostral com especialistas do domínio antes de apoiar decisões.
