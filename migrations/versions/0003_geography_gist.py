"""Adiciona GiST funcional compatível com consultas por geography."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_facilities_geog_gist ON facilities USING gist ((geom::geography))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_facilities_geog_gist")
