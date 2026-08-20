from pathlib import Path


def test_migracao_cria_indice_funcional_para_consultas_geography() -> None:
    migration = Path("migrations/versions/0003_geography_gist.py").read_text(encoding="utf-8")

    assert "geom::geography" in migration
    assert "ix_facilities_geog_gist" in migration


def test_ci_executa_benchmark_e_publica_artefato() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/benchmark_postgis.py" in workflow
    assert "scripts/import_territories.py" in workflow
    assert "actions/upload-artifact@v7" in workflow


def test_migracao_cria_territorios_com_indice_espacial() -> None:
    migration = Path("migrations/versions/0004_territories.py").read_text(encoding="utf-8")

    assert "territories" in migration
    assert "MULTIPOLYGON" in migration
    assert "ix_territories_geom_gist" in migration


def test_ci_executa_ciclo_real_de_migracao_com_dados_legados() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    verifier = Path("scripts/verify_migrations.py").read_text(encoding="utf-8")

    assert "scripts/verify_migrations.py" in workflow
    assert 'command.upgrade(config, "0001")' in verifier
    assert 'command.downgrade(config, "0002")' in verifier
    assert "legacy-preserved" in verifier
    assert "ix_facilities_geog_gist" in verifier
    assert "ix_territories_geom_gist" in verifier


def test_verificador_destrutivo_exige_banco_dedicado_e_opt_in() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    verifier = Path("scripts/verify_migrations.py").read_text(encoding="utf-8")

    assert "MIGRATION_TEST_ALLOW_DESTRUCTIVE" in verifier
    assert ".endswith(" in verifier
    assert '"_migration_test"' in verifier
    assert "geo_migration_test" in workflow
    assert 'MIGRATION_TEST_ALLOW_DESTRUCTIVE: "1"' in workflow


def test_migracao_reconstroi_indices_sem_bloquear_escritas() -> None:
    migration = Path("migrations/versions/0005_concurrent_indexes.py").read_text(encoding="utf-8")

    assert "autocommit_block" in migration
    assert "CREATE INDEX CONCURRENTLY" in migration
    assert "DROP INDEX CONCURRENTLY" in migration
    assert "ix_facilities_geog_gist" in migration
    assert "ix_territories_geom_gist" in migration


def test_migracao_classifica_territorios_e_relaciona_pai() -> None:
    migration = Path("migrations/versions/0006_territory_hierarchy.py").read_text(encoding="utf-8")

    assert '"territory_type"' in migration
    assert '"parent_code"' in migration
    assert "ix_territories_parent_type" in migration


def test_ci_importa_bairros_oficiais_no_postgis() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "data/ibge-teresina-neighborhoods.geojson" in workflow
