from pathlib import Path


def test_migracao_cria_indice_funcional_para_consultas_geography() -> None:
    migration = Path("migrations/versions/0003_geography_gist.py").read_text(encoding="utf-8")

    assert "geom::geography" in migration
    assert "ix_facilities_geog_gist" in migration


def test_ci_executa_benchmark_e_publica_artefato() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/benchmark_postgis.py" in workflow
    assert "scripts/import_territories.py" in workflow
    assert "actions/upload-artifact@v5" in workflow


def test_migracao_cria_territorios_com_indice_espacial() -> None:
    migration = Path("migrations/versions/0004_territories.py").read_text(encoding="utf-8")

    assert "territories" in migration
    assert "MULTIPOLYGON" in migration
    assert "ix_territories_geom_gist" in migration
