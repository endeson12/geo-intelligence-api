"""Benchmark reproduzível do índice GiST funcional usado nas buscas por raio."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
from pathlib import Path
from typing import Any

import psycopg

QUERY = """EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT COUNT(*)
FROM benchmark_facilities
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_MakePoint(-42.80, -5.09), 4326)::geography,
    1000
)"""


def normalize_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def extract_plan_nodes(plan: dict[str, Any]) -> list[str]:
    """Lista os nós do plano em ordem de percurso."""
    label = str(plan["Node Type"])
    if index_name := plan.get("Index Name"):
        label += f" ({index_name})"
    nodes = [label]
    for child in plan.get("Plans", []):
        nodes.extend(extract_plan_nodes(child))
    return nodes


def summarize_explain(explain: list[dict[str, Any]]) -> dict[str, Any]:
    root = explain[0]
    return {
        "execution_ms": round(float(root["Execution Time"]), 3),
        "plan_nodes": extract_plan_nodes(root["Plan"]),
    }


def _measure(connection: psycopg.Connection[Any], repetitions: int = 3) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    for _ in range(repetitions):
        with connection.cursor() as cursor:
            cursor.execute(QUERY)
            explain = cursor.fetchone()[0]
        samples.append(summarize_explain(explain))
    median_ms = statistics.median(sample["execution_ms"] for sample in samples)
    return {
        "execution_ms_median": round(median_ms, 3),
        "samples_ms": [sample["execution_ms"] for sample in samples],
        "plan_nodes": samples[-1]["plan_nodes"],
    }


def run_benchmark(database_url: str, dataset_size: int) -> dict[str, Any]:
    with psycopg.connect(normalize_database_url(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cursor.execute(
                """CREATE TEMP TABLE benchmark_facilities AS
                SELECT id,
                    ST_SetSRID(
                        ST_MakePoint(
                            -42.95 + MOD(id, 1000) * 0.0003,
                            -5.24 + (id / 1000) * 0.0003
                        ),
                        4326
                    )::geometry(Point, 4326) AS geom
                FROM generate_series(1, %s) AS id""",
                (dataset_size,),
            )
            cursor.execute("ANALYZE benchmark_facilities")

        before = _measure(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE INDEX benchmark_geog_gist "
                "ON benchmark_facilities USING gist ((geom::geography))"
            )
            cursor.execute("ANALYZE benchmark_facilities")
        after = _measure(connection)

        with connection.cursor() as cursor:
            cursor.execute("SELECT version(), PostGIS_Full_Version()")
            postgres_version, postgis_version = cursor.fetchone()

    before_ms = float(before["execution_ms_median"])
    after_ms = float(after["execution_ms_median"])
    return {
        "scope": "benchmark sintético local/CI; não representa carga de produção",
        "dataset": {
            "rows": dataset_size,
            "geometry": "Point EPSG:4326 gerado deterministicamente",
        },
        "query": "ST_DWithin sobre geom::geography, raio de 1000 m",
        "environment": {
            "python": platform.python_version(),
            "postgresql": postgres_version,
            "postgis": postgis_version,
        },
        "without_functional_gist": before,
        "with_functional_gist": after,
        "observed_speedup": round(before_ms / after_ms, 2) if after_ms else None,
        "conclusion": (
            "Resultado desta execução; repetir no ambiente-alvo antes de decisões de capacidade."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--dataset-size", type=int, default=100_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("defina DATABASE_URL ou --database-url")
    if args.dataset_size < 10_000:
        parser.error("--dataset-size deve ser pelo menos 10000")

    report = run_benchmark(args.database_url, args.dataset_size)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
