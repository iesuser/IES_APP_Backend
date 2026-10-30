from flask_restx import fields, reqparse

from app.extensions import api

alert_settings_ns = api.namespace(
    "Alert Settings",
    description="One notification area per device",
    path="/api/v1",
)

error_model = alert_settings_ns.model(
    "AlertSettingsError",
    {
        "error": fields.String(required=True, example="validation_error"),
        "message": fields.String(required=True, example="area must be a Polygon or MultiPolygon."),
    },
)

alert_settings_model = alert_settings_ns.model(
    "AlertSettings",
    {
        "device_id": fields.String(required=True),
        "enabled": fields.Boolean(required=True, example=True),
        "min_magnitude": fields.Float(required=True, example=3.0),
        "area_source": fields.String(required=True, example="custom", enum=["custom", "circle"]),
        "area": fields.Raw(required=True, description="MultiPolygon GeoJSON, SRID 4326"),
        "updated_at": fields.String(required=True),
    },
)

alert_settings_list_model = alert_settings_ns.model(
    "AlertSettingsList",
    {
        "items": fields.List(fields.Nested(alert_settings_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

alert_settings_get_parser = reqparse.RequestParser()
alert_settings_get_parser.add_argument("limit", type=int, required=False, location="args")
