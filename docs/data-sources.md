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

### Limite municipal do IBGE

`data/ibge-teresina-boundary.geojson` contém uma feição oficial simplificada do município de Teresina, código territorial `2211001`, obtida pela [API de Malhas Geográficas v3 do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3).

- **Fonte:** IBGE — API de Malhas Geográficas;
- **URL reproduzível:** registrada em `metadata.source_url`;
- **Coleta:** `2026-08-19T16:38:33Z`;
- **Qualidade solicitada:** `minima`;
- **Uso no projeto:** metadado explícito `crs=EPSG:4326`, validação de topologia/faixas WGS84, persistência como `MultiPolygon` e consulta inclusiva `ST_Covers`;
- **Atribuição:** o nome da instituição e a URL oficial permanecem no arquivo e na resposta da API.

A própria documentação do IBGE descreve essas malhas como **simplificadas**, voltadas a aplicações web. Como o parâmetro `periodo` foi omitido, a API informa que retorna a malha mais recente disponível no momento da coleta. O arquivo não representa bairros, setores censitários nem precisão cadastral e não deve ser usado como levantamento de limites.

Importação reproduzível após as migrações:

```bash
uv run python scripts/import_territories.py data/ibge-teresina-boundary.geojson
```

## Reproduzir a coleta

```bash
uv run python scripts/fetch_osm.py
```

A Overpass API é um serviço comunitário e pode aplicar limites. Evite execuções frequentes, identifique o cliente e preserve a atribuição.

## Relatório reproduzível de qualidade

O pipeline local verifica estrutura da `FeatureCollection`, geometrias `Point`, faixa WGS84, campos obrigatórios, duplicidades exatas e atribuição da fonte:

```bash
uv run python scripts/data_quality.py data/osm-teresina-health.geojson
```

O resultado versionado está em [`data-quality-report.json`](data-quality-report.json). Na fotografia incluída, 20 de 20 feições passaram pelas regras automatizadas e nenhuma duplicidade exata foi encontrada. Isso **não comprova completude, atualidade nem acurácia posicional**; essas dimensões exigem comparação com fonte autorizada e revisão de domínio.

## Checklist antes de uso institucional

1. Definir responsável, finalidade, fonte autorizada e base legal.
2. Registrar data de referência, licença, cobertura territorial e frequência de atualização.
3. Validar CRS, geometrias, duplicidades, campos obrigatórios e valores aceitos.
4. Medir completude, consistência, acurácia posicional e atualidade.
5. Tratar coordenadas sensíveis e dados pessoais conforme LGPD e política interna.
6. Manter linhagem, versão do lote, relatório de rejeições e possibilidade de rollback.
7. Fazer revisão amostral com especialistas do domínio antes de apoiar decisões.
