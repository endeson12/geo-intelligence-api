"""Recorta bairros do Censo 2022 para Teresina a partir do GeoPackage oficial do IBGE.

Dependências de preparação (não necessárias em runtime):
uv run --no-project --python 3.12 --with geopandas --with pyogrio \
  python scripts/prepare_ibge_neighborhoods.py INPUT OUTPUT
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyogrio
from shapely.geometry import mapping

SOURCE_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/"
    "bairros/gpkg/UF/PI/PI_bairros_CD2022.gpkg"
)
EXPECTED_SHA256 = "cfd26ee37c8ca666e12eb5719ebdb2e0f7b108ded722cadc716e2ee82e347309"
MUNICIPALITY_CODE = "2211001"
EXPECTED_COUNT = 123


def prepare(source: Path, output: Path) -> None:
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != EXPECTED_SHA256:
        raise ValueError(f"SHA-256 inesperado para a fonte: {source_hash}")

    frame = pyogrio.read_dataframe(
        source,
        where=f"CD_MUN = '{MUNICIPALITY_CODE}'",
        columns=["CD_MUN", "CD_BAIRRO", "NM_BAIRRO"],
    )
    if str(frame.crs).upper() != "EPSG:4674":
        raise ValueError(f"CRS de origem inesperado: {frame.crs}")
    if len(frame) != EXPECTED_COUNT:
        raise ValueError(f"quantidade inesperada de bairros: {len(frame)}")
    if frame["CD_BAIRRO"].duplicated().any():
        raise ValueError("códigos de bairro duplicados")
    if frame.geometry.is_empty.any() or not frame.geometry.is_valid.all():
        raise ValueError("a fonte contém geometrias vazias ou inválidas")

    frame = frame.sort_values("CD_BAIRRO").to_crs("EPSG:4326")
    features: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "territorial_code": str(row.CD_BAIRRO),
                    "name": str(row.NM_BAIRRO),
                },
                "geometry": mapping(row.geometry),
            }
        )

    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "IBGE — Malha de Bairros do Censo Demográfico 2022",
            "source_url": SOURCE_URL,
            "source_version": "publicada em 2024-11-12T20:08:12Z",
            "source_etag": '"f5000-626bcc6daddbf"',
            "source_size_bytes": 1_003_520,
            "source_sha256": source_hash,
            "license": "Dados abertos federais; Decreto 8.777/2016; atribuição ao IBGE",
            "acquired_at": "2026-08-20",
            "quality": (
                "Malha oficial de bairros do Censo 2022; divisão censitária, não equivale "
                "necessariamente ao cadastro municipal vigente"
            ),
            "source_crs": "EPSG:4674",
            "crs": "EPSG:4326",
            "territory_type": "bairro",
            "parent_code": MUNICIPALITY_CODE,
        },
        "features": features,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"status=ok bairros={len(features)} sha256_fonte={source_hash} saida={output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)


if __name__ == "__main__":
    main()
