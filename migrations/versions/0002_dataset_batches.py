"""Versiona lotes de dados e relaciona feições importadas."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("content_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=True),
        sa.Column("license", sa.String(100), nullable=True),
        sa.Column("feature_count", sa.Integer(), nullable=False),
        sa.Column(
            "imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column("facilities", sa.Column("batch_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_facilities_batch_id",
        "facilities",
        "dataset_batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_facilities_batch_id", "facilities", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_facilities_batch_id", table_name="facilities")
    op.drop_constraint("fk_facilities_batch_id", "facilities", type_="foreignkey")
    op.drop_column("facilities", "batch_id")
    op.drop_table("dataset_batches")
