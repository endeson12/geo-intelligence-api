from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class DatasetBatch(Base):
    __tablename__ = "dataset_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    source: Mapped[str] = mapped_column(String(200))
    source_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    tipo: Mapped[str] = mapped_column(String(80), index=True)
    fonte: Mapped[str] = mapped_column(String(200), default="não informada")
    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_batches.id", ondelete="SET NULL"), nullable=True
    )
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_facilities_geom_gist", "geom", postgresql_using="gist"),)


class Territory(Base):
    __tablename__ = "territories"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(160))
    source_url: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(String(200))
    acquired_at: Mapped[str] = mapped_column(String(40))
    quality: Mapped[str] = mapped_column(Text)
    territory_type: Mapped[str] = mapped_column(String(40), default="municipio", index=True)
    parent_code: Mapped[str | None] = mapped_column(
        ForeignKey("territories.code", ondelete="CASCADE"), nullable=True, index=True
    )
    geom: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
