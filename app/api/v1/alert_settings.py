import logging
from decimal import Decimal, InvalidOperation
from uuid import UUID

from flask import request
from flask_restx import Resource, marshal
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.nsmodels.alert_settings import (
    alert_settings_get_parser,
    alert_settings_list_model,
    alert_settings_model,
    alert_settings_ns,
    error_model,
)
from app.extensions import db
from app.models import AlertSettings, Device
from app.utils.geo import multipolygon_from_circle, multipolygon_from_geojson

logger = logging.getLogger("app.alert_settings")

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


def _error(message, status=400):
    return {"error": "validation_error" if status == 400 else "not_found", "message": message}, status


@alert_settings_ns.route("/alert-settings/")
class AlertSettingsListApi(Resource):
    @alert_settings_ns.expect(alert_settings_get_parser)
    @alert_settings_ns.response(200, "Success", alert_settings_list_model)
    @alert_settings_ns.response(400, "Validation Error", error_model)
    def get(self):
        """List stored alert areas."""
        limit, error = _limit(alert_settings_get_parser.parse_args().get("limit"))
        if error:
            return error
        total = AlertSettings.query.count()
        rows = (
            AlertSettings.query.order_by(AlertSettings.updated_at.desc())
            .limit(limit)
            .all()
        )
        return marshal(
            {"items": [row.to_dict() for row in rows], "total": total, "limit": limit},
            alert_settings_list_model,
        ), 200


@alert_settings_ns.route("/devices/<string:device_id>/alert-settings")
class AlertSettingsApi(Resource):
    @alert_settings_ns.response(200, "Success", alert_settings_model)
    @alert_settings_ns.response(400, "Validation Error", error_model)
    @alert_settings_ns.response(404, "Not Found", error_model)
    def get(self, device_id):
        """Return the alert area stored for one device."""
        try:
            device_uuid = UUID(device_id)
        except (TypeError, ValueError):
            return _error("device_id must be a UUID.")
        if db.session.get(Device, device_uuid) is None:
            return _error("Device not found.", 404)
        settings = db.session.get(AlertSettings, device_uuid)
        if settings is None:
            return _error("Alert settings not found.", 404)
        return marshal(settings.to_dict(), alert_settings_model), 200

    @alert_settings_ns.expect(alert_settings_model, validate=False)
    @alert_settings_ns.response(201, "Created", alert_settings_model)
    @alert_settings_ns.response(200, "Updated", alert_settings_model)
    @alert_settings_ns.response(400, "Validation Error", error_model)
    @alert_settings_ns.response(404, "Not Found", error_model)
    def put(self, device_id):
        """Save the single alert area for a device. A circle is stored as a polygon."""
        try:
            device_uuid = UUID(device_id)
        except (TypeError, ValueError):
            return _error("device_id must be a UUID.")

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error("JSON object is required.")

        if db.session.get(Device, device_uuid) is None:
            return _error("Device not found.", 404)

        enabled = payload.get("enabled", True)
        if not isinstance(enabled, bool):
            return _error("enabled must be true or false.")

        area_source = payload.get("area_source", "custom")
        if area_source not in {"custom", "circle"}:
            return _error("area_source must be custom or circle.")

        try:
            magnitude = Decimal(str(payload.get("min_magnitude", "3.0"))).quantize(Decimal("0.1"))
        except (InvalidOperation, ValueError):
            return _error("min_magnitude must be a number.")
        if magnitude < 0 or magnitude > Decimal("10.0"):
            return _error("min_magnitude must be between 0 and 10.")

        try:
            if area_source == "circle":
                latitude = payload.get("latitude")
                longitude = payload.get("longitude")
                radius_m = payload.get("radius_m")
                if not all(isinstance(value, (int, float)) for value in (latitude, longitude, radius_m)):
                    return _error("circle needs latitude, longitude, and radius_m.")
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    return _error("coordinates are out of range.")
                if not (0 < radius_m <= 2_000_000):
                    return _error("radius_m must be between 0 and 2000000.")
                area = multipolygon_from_circle(longitude, latitude, radius_m)
            else:
                area = multipolygon_from_geojson(payload.get("area"))
        except ValueError as exc:
            return _error(str(exc))

        settings = db.session.get(AlertSettings, device_uuid)
        created = settings is None
        if settings is None:
            settings = AlertSettings(
                device_id=device_uuid,
                enabled=enabled,
                min_magnitude=magnitude,
                area=area,
                area_source=area_source,
            )
            db.session.add(settings)
        else:
            settings.enabled = enabled
            settings.min_magnitude = magnitude
            settings.area = area
            settings.area_source = area_source
            settings.updated_at = db.session.scalar(db.select(db.func.now()))

        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("alert settings were not stored")
            return {"error": "server_error", "message": "Could not store alert settings."}, 500

        db.session.refresh(settings)
        return marshal(settings.to_dict(), alert_settings_model), 201 if created else 200
