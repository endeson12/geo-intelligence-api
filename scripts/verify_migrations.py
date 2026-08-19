"""Executa upgrade/downgrade real preservando um registro legado."""

import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url

from geo_intelligence_api.config import get_settings


def _assert_regclass(connection: Connection, name: str, present: bool) -> None:
    result = connection.execute(text("SELECT to_regclass(:name)"), {"name": name}).scalar_one()
    if (result is not None) is not present:
        state = "existir" if present else "não existir"
        raise RuntimeError(f"esperado {name} {state}")


def main() -> None:
    config = Config("alembic.ini")
    database_url = get_settings().database_url
    database_name = make_url(database_url).database or ""
    if os.getenv("MIGRATION_TEST_ALLOW_DESTRUCTIVE") != "1" or not database_name.endswith(
        "_migration_test"
    ):
        raise RuntimeError(
            "verificação destrutiva bloqueada: use opt-in explícito e banco *_migration_test"
        )
    engine = create_engine(database_url)

    command.downgrade(config, "base")
    command.upgrade(config, "0001")
    with engine.begin() as connection:
        connection.execute(
            text(
                """INSERT INTO facilities (nome, tipo, fonte, geom)
                VALUES ('legacy-preserved', 'teste', 'migration-cycle',
                        ST_SetSRID(ST_MakePoint(-42.8, -5.09), 4326))"""
            )
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM facilities WHERE nome = 'legacy-preserved'")
        ).scalar_one()
        if count != 1:
            raise RuntimeError("registro legado não foi preservado no upgrade")
        _assert_regclass(connection, "ix_facilities_geog_gist", True)
        _assert_regclass(connection, "ix_territories_geom_gist", True)

    command.downgrade(config, "0002")
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM facilities WHERE nome = 'legacy-preserved'")
        ).scalar_one()
        if count != 1:
            raise RuntimeError("registro legado não foi preservado no downgrade")
        _assert_regclass(connection, "territories", False)
        _assert_regclass(connection, "ix_facilities_geog_gist", False)

    command.upgrade(config, "head")
    with engine.begin() as connection:
        _assert_regclass(connection, "ix_facilities_geog_gist", True)
        _assert_regclass(connection, "ix_territories_geom_gist", True)
        connection.execute(text("DELETE FROM facilities WHERE nome = 'legacy-preserved'"))

    engine.dispose()
    print("status=ok upgrade=0001->head downgrade=head->0002 dados_legados=preservados")


if __name__ == "__main__":
    main()
