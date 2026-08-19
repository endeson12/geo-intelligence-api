"""Reconstrói índices espaciais sem bloquear escritas durante o build."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    context = op.get_context()
    with context.autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_facilities_geog_gist_concurrent")
        op.execute(
            "CREATE INDEX CONCURRENTLY ix_facilities_geog_gist_concurrent "
            "ON facilities USING gist ((geom::geography))"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_territories_geom_gist_concurrent")
        op.execute(
            "CREATE INDEX CONCURRENTLY ix_territories_geom_gist_concurrent "
            "ON territories USING gist (geom)"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_facilities_geog_gist")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_territories_geom_gist")
        op.execute(
            "ALTER INDEX ix_facilities_geog_gist_concurrent RENAME TO ix_facilities_geog_gist"
        )
        op.execute(
            "ALTER INDEX ix_territories_geom_gist_concurrent RENAME TO ix_territories_geom_gist"
        )


def downgrade() -> None:
    # O estado lógico em 0004 usa os mesmos nomes e expressões de índice.
    # O modo de criação concorrente é uma propriedade operacional, não de schema.
    pass
