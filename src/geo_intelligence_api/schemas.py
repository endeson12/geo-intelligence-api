from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PointGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: tuple[float, float]

    @field_validator("coordinates")
    @classmethod
    def validar_wgs84(cls, value: tuple[float, float]) -> tuple[float, float]:
        lon, lat = value
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("coordenadas fora dos limites WGS84")
        return value


class FeatureProperties(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    tipo: str = Field(min_length=1, max_length=80)
    fonte: str = Field(default="não informada", max_length=200)


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"]
    properties: FeatureProperties
    geometry: PointGeometry


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: list[GeoJSONFeature] = Field(max_length=10_000)


class FeatureCollectionResponse(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict[str, Any]]
