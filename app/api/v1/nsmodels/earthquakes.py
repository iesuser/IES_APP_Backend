from flask_restx import fields, reqparse

from app.extensions import api

earthquakes_ns = api.namespace(
    "Earthquakes",
    description="Earthquakes received for notification",
    path="/api/v1",
)

error_model = earthquakes_ns.model(
    "EarthquakeError",
    {
        "error": fields.String(required=True, example="not_found"),
        "message": fields.String(required=True, example="Earthquake not found."),
    },
)

origin_model = earthquakes_ns.model(
    "StoredOrigin",
    {
        "time": fields.String(required=True),
        "latitude": fields.Float(required=True, example=42.0218),
        "longitude": fields.Float(required=True, example=43.6916),
        "depth": fields.Float(required=True, example=16.46),
        "location_ge": fields.String(required=True),
        "location_en": fields.String(required=True),
    },
)

actor_model = earthquakes_ns.model(
    "EarthquakeActor",
    {
        "kind": fields.String(required=True, enum=["user", "service"], example="user"),
        "name": fields.String(required=True, example="Roma Grigalashvili"),
    },
)

magnitude_model = earthquakes_ns.model(
    "StoredMagnitude",
    {
        "type": fields.String(required=True, example="ML"),
        "value": fields.Float(required=True, example=3.28),
    },
)

earthquake_input_model = earthquakes_ns.model(
    "EarthquakeInput",
    {
        "event_id": fields.Integer(required=True, example=16),
        "iesdata_id": fields.Integer(required=True, example=591862),
        "seiscomp_oid": fields.String(required=True, example="ies2026nrtc"),
        "is_automatic": fields.Boolean(required=True, example=False),
        "origin": fields.Nested(origin_model, required=True),
        "magnitudes": fields.List(
            fields.Nested(magnitude_model),
            required=True,
            example=[{"type": "ML", "value": 3.8}, {"type": "Mw", "value": 3.6}],
        ),
    },
)

earthquake_model = earthquakes_ns.model(
    "Earthquake",
    {
        "id": fields.Integer(required=True, example=1),
        "event_id": fields.Integer(required=True, example=6),
        "iesdata_id": fields.Integer(required=False, example=591034),
        "seiscomp_oid": fields.String(required=False, example="ies2026nrtc"),
        "is_automatic": fields.Boolean(required=True, example=False),
        "origin": fields.Nested(origin_model, required=True),
        "magnitude": fields.Nested(magnitude_model, required=True),
        "created_by": fields.Nested(actor_model, required=False, allow_null=True),
        "created_at": fields.String(required=True),
        "updated_by": fields.Nested(actor_model, required=False, allow_null=True),
        "updated_at": fields.String(required=False),
    },
)

earthquake_list_model = earthquakes_ns.model(
    "EarthquakeList",
    {
        "items": fields.List(fields.Nested(earthquake_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

earthquakes_get_parser = reqparse.RequestParser()
earthquakes_get_parser.add_argument("limit", type=int, required=False, location="args")
