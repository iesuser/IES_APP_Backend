from datetime import datetime, timezone

from flask import request
from flask_restx import Resource, marshal
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.nsmodels.earthquakes import (
    earthquake_input_model,
    earthquake_list_model,
    earthquake_model,
    earthquakes_get_parser,
    earthquakes_ns,
    error_model,
)
from app.extensions import db
from app.models import Earthquake

LIST_DEFAULT_LIMIT = 100
LIST_MAX_LIMIT = 200


def _limit(value):
    if value is None:
        return LIST_DEFAULT_LIMIT, None
    if value < 1 or value > LIST_MAX_LIMIT:
        return None, (
            {
                "error": "validation_error",
                "message": f"limit must be between 1 and {LIST_MAX_LIMIT}.",
            },
            400,
        )
    return value, None


def _error(message):
    return {"error": "validation_error", "message": message}, 400


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        return None, _error(f"{name} must be an integer.")
    return value, None


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, _error(f"{name} must be a number.")
    return float(value), None


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        return None, _error(f"{name} is required.")
    return value.strip(), None


def _parse_actor(value, name):
    if value is None:
        return None, None
    if not isinstance(value, dict):
        return None, _error(f"{name} must be an object.")
    kind, error = _text(value.get("kind"), f"{name}.kind")
    if error:
        return None, error
    kind = kind.lower()
    if kind not in ("user", "service"):
        return None, _error(f"{name}.kind must be user or service.")
    actor_name, error = _text(value.get("name"), f"{name}.name")
    if error:
        return None, error
    return {"kind": kind, "name": actor_name}, None


def _chosen_magnitude(magnitudes):
    for item in magnitudes:
        if item["type"] == "ML":
            return item
    return magnitudes[0]


def _parse_earthquake(payload):
    if not isinstance(payload, dict):
        return None, _error("JSON object is required.")

    event_id, error = _integer(payload.get("event_id"), "event_id")
    if error:
        return None, error
    if event_id < 1:
        return None, _error("event_id must be a positive integer.")

    iesdata_id, error = _integer(payload.get("iesdata_id"), "iesdata_id")
    if error:
        return None, error
    if iesdata_id < 1:
        return None, _error("iesdata_id must be a positive integer.")

    seiscomp_oid, error = _text(payload.get("seiscomp_oid"), "seiscomp_oid")
    if error:
        return None, error
    if not isinstance(payload.get("is_automatic"), bool):
        return None, _error("is_automatic must be true or false.")

    origin = payload.get("origin")
    if not isinstance(origin, dict):
        return None, _error("origin is required.")
    origin_time, error = _text(origin.get("time"), "origin.time")
    if error:
        return None, error
    try:
        parsed_time = datetime.fromisoformat(origin_time.replace("Z", "+00:00"))
    except ValueError:
        return None, _error("origin.time must be an ISO 8601 datetime.")
    if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
        return None, _error("origin.time must include a timezone.")

    latitude, error = _number(origin.get("latitude"), "origin.latitude")
    if error:
        return None, error
    longitude, error = _number(origin.get("longitude"), "origin.longitude")
    if error:
        return None, error
    depth, error = _number(origin.get("depth"), "origin.depth")
    if error:
        return None, error
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None, _error("origin coordinates are out of range.")
    if depth < 0:
        return None, _error("origin.depth must be zero or greater.")
    location_ge, error = _text(origin.get("location_ge"), "origin.location_ge")
    if error:
        return None, error
    location_en, error = _text(origin.get("location_en"), "origin.location_en")
    if error:
        return None, error

    raw_magnitudes = payload.get("magnitudes")
    if not isinstance(raw_magnitudes, list) or not raw_magnitudes:
        return None, _error("magnitudes must contain at least one value.")
    magnitudes = []
    for index, item in enumerate(raw_magnitudes):
        if not isinstance(item, dict):
            return None, _error(f"magnitudes[{index}] must be an object.")
        magnitude_type, error = _text(item.get("type"), f"magnitudes[{index}].type")
        if error:
            return None, error
        magnitude_value, error = _number(item.get("value"), f"magnitudes[{index}].value")
        if error:
            return None, error
        if not 0 <= magnitude_value <= 10:
            return None, _error(f"magnitudes[{index}].value must be between 0 and 10.")
        magnitudes.append({"type": magnitude_type.upper(), "value": magnitude_value})

    created_by, error = _parse_actor(payload.get("created_by"), "created_by")
    if error:
        return None, error
    updated_by, error = _parse_actor(payload.get("updated_by"), "updated_by")
    if error:
        return None, error

    return {
        "event_id": event_id,
        "iesdata_id": iesdata_id,
        "seiscomp_oid": seiscomp_oid,
        "is_automatic": payload["is_automatic"],
        "origin": {
            "time": parsed_time,
            "latitude": latitude,
            "longitude": longitude,
            "depth": depth,
            "location_ge": location_ge,
            "location_en": location_en,
        },
        "magnitudes": magnitudes,
        "created_by": created_by,
        "updated_by": updated_by,
    }, None


def _earthquake_values(notice):
    magnitude = _chosen_magnitude(notice["magnitudes"])
    origin = notice["origin"]
    values = {
        "iesdata_id": notice["iesdata_id"],
        "seiscomp_oid": notice["seiscomp_oid"],
        "is_automatic": notice["is_automatic"],
        "origin_time": origin["time"],
        "latitude": origin["latitude"],
        "longitude": origin["longitude"],
        "depth": origin["depth"],
        "location_ge": origin["location_ge"],
        "location_en": origin["location_en"],
        "magnitude_type": magnitude["type"],
        "magnitude_value": magnitude["value"],
    }
    return values


def _apply_values(earthquake, values):
    for name, value in values.items():
        setattr(earthquake, name, value)


@earthquakes_ns.route("/earthquakes/")
class EarthquakesApi(Resource):
    @earthquakes_ns.expect(earthquakes_get_parser)
    @earthquakes_ns.response(200, "Success", earthquake_list_model)
    @earthquakes_ns.response(400, "Validation Error", error_model)
    def get(self):
        """List stored earthquakes, newest first."""
        limit, error = _limit(earthquakes_get_parser.parse_args().get("limit"))
        if error:
            return error
        total = Earthquake.query.count()
        rows = Earthquake.query.order_by(Earthquake.created_at.desc(), Earthquake.id.desc()).limit(limit).all()
        return marshal(
            {"items": [row.to_dict() for row in rows], "total": total, "limit": limit},
            earthquake_list_model,
        ), 200

    @earthquakes_ns.expect(earthquake_input_model, validate=False)
    @earthquakes_ns.response(201, "Created", earthquake_model)
    @earthquakes_ns.response(400, "Validation Error", error_model)
    @earthquakes_ns.response(409, "Conflict", error_model)
    def post(self):
        """Store a new earthquake sent by ies_monitoring."""
        notice, error = _parse_earthquake(request.get_json(silent=True))
        if error:
            return error
        if Earthquake.query.filter_by(ies_event_id=notice["event_id"]).first() is not None:
            return {"error": "conflict", "message": "Earthquake already exists."}, 409
        created_by = notice["created_by"]
        updated_by = notice["updated_by"]
        earthquake = Earthquake(
            ies_event_id=notice["event_id"],
            created_by_kind=created_by["kind"] if created_by else None,
            created_by_name=created_by["name"] if created_by else None,
            updated_by_kind=updated_by["kind"] if updated_by else None,
            updated_by_name=updated_by["name"] if updated_by else None,
            updated_at=datetime.now(timezone.utc) if updated_by else None,
            **_earthquake_values(notice),
        )
        try:
            earthquake.create()
        except SQLAlchemyError:
            db.session.rollback()
            return {"error": "server_error", "message": "Earthquake could not be stored."}, 500
        db.session.refresh(earthquake)
        return marshal(earthquake.to_dict(), earthquake_model), 201


@earthquakes_ns.route("/earthquakes/<int:event_id>")
class EarthquakeDetailApi(Resource):
    @earthquakes_ns.response(200, "Success", earthquake_model)
    @earthquakes_ns.response(404, "Not Found", error_model)
    def get(self, event_id):
        """Return one stored earthquake. event_id is the published event id."""
        earthquake = Earthquake.query.filter_by(ies_event_id=event_id).first()
        if earthquake is None:
            return {"error": "not_found", "message": "Earthquake not found."}, 404
        return marshal(earthquake.to_dict(), earthquake_model), 200

    @earthquakes_ns.expect(earthquake_input_model, validate=False)
    @earthquakes_ns.response(200, "Updated", earthquake_model)
    @earthquakes_ns.response(400, "Validation Error", error_model)
    @earthquakes_ns.response(404, "Not Found", error_model)
    def put(self, event_id):
        """Replace the stored fields of an existing earthquake."""
        notice, error = _parse_earthquake(request.get_json(silent=True))
        if error:
            return error
        if notice["event_id"] != event_id:
            return {"error": "validation_error", "message": "event_id does not match the URL."}, 400
        earthquake = Earthquake.query.filter_by(ies_event_id=event_id).first()
        if earthquake is None:
            return {"error": "not_found", "message": "Earthquake not found."}, 404
        _apply_values(earthquake, _earthquake_values(notice))
        earthquake.updated_at = datetime.now(timezone.utc)
        updated_by = notice["updated_by"]
        if updated_by:
            earthquake.updated_by_kind = updated_by["kind"]
            earthquake.updated_by_name = updated_by["name"]
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return {"error": "server_error", "message": "Earthquake could not be stored."}, 500
        db.session.refresh(earthquake)
        return marshal(earthquake.to_dict(), earthquake_model), 200

    @earthquakes_ns.response(204, "Deleted")
    @earthquakes_ns.response(404, "Not Found", error_model)
    def delete(self, event_id):
        """Delete one earthquake. Queued notifications go with it."""
        earthquake = Earthquake.query.filter_by(ies_event_id=event_id).first()
        if earthquake is None:
            return {"error": "not_found", "message": "Earthquake not found."}, 404
        try:
            earthquake.delete()
        except SQLAlchemyError:
            db.session.rollback()
            return {"error": "server_error", "message": "Earthquake could not be deleted."}, 500
        return "", 204
