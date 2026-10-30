import json

from geoalchemy2.elements import WKBElement
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

_POLYGON = """
SELECT ST_AsEWKB(geom)
FROM (
    SELECT ST_Multi(
        ST_CollectionExtract(
            ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)),
            3
        )
    ) AS geom
) AS shaped
WHERE NOT ST_IsEmpty(geom)
"""

_CIRCLE = """
SELECT ST_AsEWKB(
    ST_Multi(
        ST_Buffer(
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
            :radius_m
        )::geometry
    )
)
"""


def _wkb(value):
    return WKBElement(bytes(value), srid=4326)


def multipolygon_from_geojson(geojson):
    geometry = geojson.get("geometry") if isinstance(geojson, dict) and geojson.get("type") == "Feature" else geojson
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("area must be a Polygon or MultiPolygon.")
    try:
        raw = db.session.execute(text(_POLYGON), {"geojson": json.dumps(geometry)}).scalar()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise ValueError("area is not a valid polygon.") from exc
    if raw is None:
        raise ValueError("area did not contain a polygon.")
    return _wkb(raw)


def point_wkb(longitude, latitude):
    raw = db.session.execute(
        text("SELECT ST_AsEWKB(ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))"),
        {"longitude": longitude, "latitude": latitude},
    ).scalar()
    return _wkb(raw)


def multipolygon_from_circle(longitude, latitude, radius_m):
    raw = db.session.execute(
        text(_CIRCLE),
        {"longitude": longitude, "latitude": latitude, "radius_m": radius_m},
    ).scalar()
    return _wkb(raw)


def location_geojson(report_id):
    raw = db.session.execute(
        text("SELECT ST_AsGeoJSON(location) FROM felt_reports WHERE id = :id"),
        {"id": report_id},
    ).scalar()
    if not raw:
        return None
    return json.loads(raw)


def area_geojson(device_id):
    raw = db.session.execute(
        text("SELECT ST_AsGeoJSON(area) FROM alert_settings WHERE device_id = :device_id"),
        {"device_id": device_id},
    ).scalar()
    if raw is None:
        return None
    return json.loads(raw)
