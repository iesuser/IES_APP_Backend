from flask_restx import fields, reqparse

from app.extensions import api

devices_ns = api.namespace("Devices", description="Installed application devices", path="/api/v1")

error_model = devices_ns.model(
    "DeviceError",
    {
        "error": fields.String(required=True, example="validation_error"),
        "message": fields.String(required=True, example="platform must be ios, android, or web."),
    },
)

device_model = devices_ns.model(
    "Device",
    {
        "device_id": fields.String(required=True, example="11111111-1111-1111-1111-111111111111"),
        "push_token": fields.String(required=False, example="ExponentPushToken[xxxx]"),
        "platform": fields.String(required=True, example="android", enum=["ios", "android", "web"]),
        "language": fields.String(required=True, example="ka", enum=["ka", "en"]),
        "app_version": fields.String(required=False, example="1.0.0"),
        "is_active": fields.Boolean(required=True, example=True),
        "created_at": fields.String(required=True),
        "last_seen_at": fields.String(required=True),
        "updated_at": fields.String(required=True),
    },
)

device_list_model = devices_ns.model(
    "DeviceList",
    {
        "items": fields.List(fields.Nested(device_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

devices_get_parser = reqparse.RequestParser()
devices_get_parser.add_argument("limit", type=int, required=False, location="args")

device_parser = reqparse.RequestParser()
device_parser.add_argument("device_id", type=str, required=True, location="json")
device_parser.add_argument("push_token", type=str, required=False, location="json")
device_parser.add_argument(
    "platform",
    type=str,
    required=True,
    location="json",
    choices=("ios", "android", "web"),
)
device_parser.add_argument(
    "language",
    type=str,
    required=False,
    location="json",
    choices=("ka", "en"),
    default="ka",
)
device_parser.add_argument("app_version", type=str, required=False, location="json")
