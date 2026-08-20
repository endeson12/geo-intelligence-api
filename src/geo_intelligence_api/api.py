import hashlib
import json
import secrets
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db
from .models import DatasetBatch, Facility
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
        ST_Distance(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        ) AS distancia_m
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


@router.get("/datasets")
def datasets(db: DB) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            text(
                """SELECT id, content_sha256, source, source_version, license,
                feature_count, imported_at
                FROM dataset_batches
                ORDER BY imported_at DESC, id DESC
                LIMIT 100"""
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


@router.get("/territories")
def territories(
    db: DB,
    territory_type: str | None = Query(None, max_length=40),
    parent_code: str | None = Query(None, max_length=20),
    limit: int = Query(200, ge=1, le=500),
) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            text(
                """SELECT code, name, territory_type, parent_code, source, acquired_at
                FROM territories
                WHERE (CAST(:territory_type AS varchar) IS NULL
                       OR territory_type = CAST(:territory_type AS varchar))
                  AND (CAST(:parent_code AS varchar) IS NULL
                       OR parent_code = CAST(:parent_code AS varchar))
                ORDER BY name, code
                LIMIT :limit"""
            ),
            {"territory_type": territory_type, "parent_code": parent_code, "limit": limit},
        )
        .mappings()
        .all()
    )
    return [
        {
            "codigo": row["code"],
            "nome": row["name"],
            "tipo": row["territory_type"],
            "codigo_pai": row["parent_code"],
            "fonte": row["source"],
            "adquirido_em": row["acquired_at"],
        }
        for row in rows
    ]


@router.get("/territories/{code}/coverage")
def territory_coverage(
    code: str,
    db: DB,
    tipo: str | None = Query(None, max_length=80),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=100_000),
) -> dict[str, Any]:
    sql = text(
        """SELECT t.code, t.name, t.source, t.source_url, t.license,
        t.acquired_at, t.quality, ST_AsGeoJSON(t.geom)::json AS geometry,
        (
            SELECT count(*)
            FROM facilities f
            WHERE ST_Covers(t.geom, f.geom)
              AND (CAST(:tipo AS varchar) IS NULL OR f.tipo = CAST(:tipo AS varchar))
        ) AS total,
        COALESCE(
            (
                SELECT json_agg(
                    json_build_object(
                    'type', 'Feature',
                    'id', f.id,
                    'geometry', ST_AsGeoJSON(f.geom)::json,
                    'properties', json_build_object(
                        'id', f.id, 'nome', f.nome, 'tipo', f.tipo, 'fonte', f.fonte
                    )
                    ) ORDER BY f.id
                )
                FROM (
                    SELECT f.id, f.nome, f.tipo, f.fonte, f.geom
                    FROM facilities f
                    WHERE ST_Covers(t.geom, f.geom)
                      AND (CAST(:tipo AS varchar) IS NULL OR f.tipo = CAST(:tipo AS varchar))
                    ORDER BY f.id
                    LIMIT :limite OFFSET :offset
                ) f
            ),
            '[]'::json
        ) AS features
        FROM territories t
        WHERE t.code = :code"""
    )
    params: dict[str, Any] = {"code": code, "tipo": tipo, "limite": limit, "offset": offset}
    row = db.execute(sql, params).mappings().first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "território não encontrado")

    item = dict(row)
    geometry = item["geometry"]
    features = item["features"]
    if isinstance(geometry, str):
        geometry = json.loads(geometry)
    if isinstance(features, str):
        features = json.loads(features)
    total = int(item["total"])
    returned = len(features)
    return {
        "territorio": {
            "codigo": item["code"],
            "nome": item["name"],
            "fonte": item["source"],
            "url_fonte": item["source_url"],
            "licenca": item["license"],
            "adquirido_em": item["acquired_at"],
            "qualidade": item["quality"],
            "geometry": geometry,
        },
        "equipamentos": {"type": "FeatureCollection", "features": features},
        "resumo": {
            "total": total,
            "retornados": returned,
            "limite": limit,
            "offset": offset,
            "tem_proxima_pagina": offset + returned < total,
            "tipo": tipo,
            "predicado": "ST_Covers",
        },
    }


@router.post("/import/geojson", status_code=status.HTTP_201_CREATED)
def import_geojson(
    payload: GeoJSONFeatureCollection,
    db: DB,
    response: Response,
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "API key inválida", headers={"WWW-Authenticate": "ApiKey"}
        )
    canonical_payload = json.dumps(
        payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    content_sha256 = hashlib.sha256(canonical_payload).hexdigest()
    existing = (
        db.execute(
            text(
                "SELECT id, feature_count FROM dataset_batches "
                "WHERE content_sha256 = :content_sha256"
            ),
            {"content_sha256": content_sha256},
        )
        .mappings()
        .first()
    )
    if existing:
        response.status_code = status.HTTP_200_OK
        existing_id = existing["id"] if isinstance(existing, dict) else existing.id
        feature_count = (
            existing["feature_count"] if isinstance(existing, dict) else existing.feature_count
        )
        return {
            "status": "ja_importado",
            "lote_id": existing_id,
            "dataset_hash": content_sha256,
            "importados": 0,
            "rejeitados": 0,
            "duplicados": feature_count,
        }

    batch = DatasetBatch(
        id=str(uuid4()),
        content_sha256=content_sha256,
        source=payload.metadata.source,
        source_version=payload.metadata.source_version,
        license=payload.metadata.license,
        feature_count=len(payload.features),
    )
    items = [
        Facility(
            nome=f.properties.nome,
            tipo=f.properties.tipo,
            fonte=f.properties.fonte,
            batch_id=batch.id,
            geom=from_shape(Point(f.geometry.coordinates), srid=4326),
        )
        for f in payload.features
    ]
    try:
        db.add(batch)
        db.flush()
        db.add_all(items)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        concurrent = (
            db.execute(
                text(
                    "SELECT id, feature_count FROM dataset_batches "
                    "WHERE content_sha256 = :content_sha256"
                ),
                {"content_sha256": content_sha256},
            )
            .mappings()
            .first()
        )
        if not concurrent:
            raise HTTPException(500, "importação revertida") from exc
        response.status_code = status.HTTP_200_OK
        concurrent_id = concurrent["id"] if isinstance(concurrent, dict) else concurrent.id
        concurrent_count = (
            concurrent["feature_count"]
            if isinstance(concurrent, dict)
            else concurrent.feature_count
        )
        return {
            "status": "ja_importado",
            "lote_id": concurrent_id,
            "dataset_hash": content_sha256,
            "importados": 0,
            "rejeitados": 0,
            "duplicados": concurrent_count,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "importação revertida") from exc
    return {
        "status": "importado",
        "lote_id": batch.id,
        "dataset_hash": content_sha256,
        "importados": len(items),
        "rejeitados": 0,
        "duplicados": 0,
    }
