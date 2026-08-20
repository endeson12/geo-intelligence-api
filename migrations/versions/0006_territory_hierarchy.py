"""Classifica territórios e registra hierarquia administrativa/censitária."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "territories",
        sa.Column(
            "territory_type", sa.String(length=40), nullable=False, server_default="municipio"
        ),
    )
    op.add_column("territories", sa.Column("parent_code", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "fk_territories_parent_code",
        "territories",
        "territories",
        ["parent_code"],
        ["code"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_territories_parent_type",
        "territories",
        ["parent_code", "territory_type", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_territories_parent_type", table_name="territories")
    op.drop_constraint("fk_territories_parent_code", "territories", type_="foreignkey")
    op.drop_column("territories", "parent_code")
    op.drop_column("territories", "territory_type")
