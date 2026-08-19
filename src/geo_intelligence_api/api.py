from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db
from .models import Facility
from .schemas import FeatureCollectionResponse, GeoJSONFeatureCollection

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


def _feature(row: Any) -> dict[str, Any]:
    item = dict(row)
    props = {"id": item["id"], "nome": item["nome"], "tipo": item["tipo"]}
    if "fonte" in item:
        props["fonte"] = item["fonte"]
    if "distancia_m" in item:
        props["distancia_m"] = round(float(item["distancia_m"]), 2)
    return {
        "type": "Feature",
        "id": item["id"],
        "geometry": {"type": "Point", "coordinates": [float(item["lon"]), float(item["lat"])]},
        "properties": props,
    }


@router.get("/facilities", response_model=FeatureCollectionResponse)
def facilities(
    db: DB, tipo: str | None = Query(None, max_length=80), bbox: str | None = None
) -> dict[str, Any]:
    where: list[str] = ["1=1"]
    params: dict[str, Any] = {}
    if tipo:
        where.append("tipo = :tipo")
        params["tipo"] = tipo
    if bbox:
        try:
            xmin, ymin, xmax, ymax = (float(v) for v in bbox.split(","))
            if (
                xmin >= xmax
                or ymin >= ymax
                or not (
                    -180 <= xmin <= 180
                    and -180 <= xmax <= 180
                    and -90 <= ymin <= 90
                    and -90 <= ymax <= 90
                )
            ):
                raise ValueError
        except ValueError as exc:
            raise HTTPException(422, "bbox deve ser xmin,ymin,xmax,ymax em WGS84") from exc
        where.append("geom && ST_MakeEnvelope(:xmin,:ymin,:xmax,:ymax,4326)")
        params.update(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
    sql = text(
        "SELECT id,nome,tipo,fonte,ST_X(geom) lon,ST_Y(geom) lat "
        "FROM facilities WHERE " + " AND ".join(where) + " ORDER BY id LIMIT 1000"
    )  # noqa: S608
    rows = db.execute(sql, params).mappings().all()
    return {"type": "FeatureCollection", "features": [_feature(r) for r in rows]}


@router.get("/facilities/nearest", response_model=FeatureCollectionResponse)
def nearest(
    db: DB,
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    limit: int = Query(5, ge=1, le=100),
    raio_m: float = Query(50_000, gt=0, le=500_000),
) -> dict[str, Any]:
    sql = text(
        """SELECT id, nome, tipo, fonte, ST_X(geom) AS lon, ST_Y(geom) AS lat,
        ST_DistanceSphere(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            AS distancia_m
        FROM facilities
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :raio
        )
        ORDER BY distancia_m
        LIMIT :limite"""
    )
    rows = (
        db.execute(sql, {"lat": lat, "lon": lon, "raio": raio_m, "limite": limit}).mappings().all()
    )
    return {"type": "FeatureCollection", "features": [_feature(r) for r in rows]}


@router.get("/coverage")
def coverage(
    db: DB,
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    raio_m: float = Query(gt=0, le=500_000),
    tipo: str | None = None,
) -> dict[str, Any]:
    base_sql = """SELECT id, nome, tipo, fonte, ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM facilities
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :raio
        )"""
    sql = text(base_sql + (" AND tipo = :tipo" if tipo else "") + " ORDER BY id LIMIT 1000")
    params: dict[str, Any] = {"lat": lat, "lon": lon, "raio": raio_m}
    if tipo:
        params["tipo"] = tipo
    rows = db.execute(sql, params).mappings().all()
    features = [_feature(row) for row in rows]
    return {
        "type": "FeatureCollection",
        "features": features,
        "summary": {
            "centro": {"lat": lat, "lon": lon},
            "raio_m": raio_m,
            "tipo": tipo,
            "total": len(features),
        },
    }


@router.post("/import/geojson", status_code=status.HTTP_201_CREATED)
def import_geojson(
    payload: GeoJSONFeatureCollection,
    db: DB,
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "API key inválida", headers={"WWW-Authenticate": "ApiKey"}
        )
    items = [
        Facility(
            nome=f.properties.nome,
            tipo=f.properties.tipo,
            fonte=f.properties.fonte,
            geom=from_shape(Point(f.geometry.coordinates), srid=4326),
        )
        for f in payload.features
    ]
    try:
        db.add_all(items)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "importação revertida") from exc
    return {"importados": len(items)}
