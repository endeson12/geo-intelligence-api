"""Persiste limites territoriais oficiais com proveniência."""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "territories",
        sa.Column("code", sa.String(length=20), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("license", sa.String(length=200), nullable=False),
        sa.Column("acquired_at", sa.String(length=40), nullable=False),
        sa.Column("quality", sa.Text(), nullable=False),
        sa.Column(
            "geom",
            Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("CREATE INDEX ix_territories_geom_gist ON territories USING gist (geom)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_territories_geom_gist")
    op.drop_table("territories")
