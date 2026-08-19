"""Habilita PostGIS e cria facilities."""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "facilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("tipo", sa.String(80), nullable=False),
        sa.Column("fonte", sa.String(200), nullable=False, server_default="não informada"),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_facilities_nome", "facilities", ["nome"])
    op.create_index("ix_facilities_tipo", "facilities", ["tipo"])
    op.create_index("ix_facilities_geom_gist", "facilities", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_table("facilities")
