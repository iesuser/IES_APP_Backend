from flask_restx import fields, reqparse

from app.extensions import api

felt_reports_ns = api.namespace(
    "Felt Reports",
    description="Did you feel it reports",
    path="/api/v1",
)

error_model = felt_reports_ns.model(
    "FeltReportError",
    {
        "error": fields.String(required=True, example="validation_error"),
        "message": fields.String(required=True, example="intensity must be MILD, MODERATE, or SEVERE."),
    },
)

felt_report_model = felt_reports_ns.model(
    "FeltReport",
    {
        "id": fields.Integer(required=True, example=1),
        "device_id": fields.String(required=False),
        "intensity": fields.String(required=True, example="MODERATE", enum=["MILD", "MODERATE", "SEVERE"]),
        "minutes_ago": fields.Integer(required=False, example=5),
        "reported_at": fields.String(required=True),
        "felt_at": fields.String(required=False),
        "earthquake_id": fields.Integer(required=False),
        "location": fields.Raw(required=False),
        "language": fields.String(required=False, example="ka"),
        "platform": fields.String(required=False, example="android"),
        "created_at": fields.String(required=True),
    },
)

felt_report_list_model = felt_reports_ns.model(
    "FeltReportList",
    {
        "items": fields.List(fields.Nested(felt_report_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

felt_reports_get_parser = reqparse.RequestParser()
felt_reports_get_parser.add_argument("limit", type=int, required=False, location="args")

felt_report_parser = reqparse.RequestParser()
felt_report_parser.add_argument("intensity", type=str, required=True, location="json", choices=("MILD", "MODERATE", "SEVERE"))
felt_report_parser.add_argument("reported_at", type=str, required=True, location="json")
felt_report_parser.add_argument("minutes_ago", type=int, required=False, location="json")
felt_report_parser.add_argument("device_id", type=str, required=False, location="json")
felt_report_parser.add_argument("language", type=str, required=False, location="json", choices=("ka", "en"))
felt_report_parser.add_argument("platform", type=str, required=False, location="json", choices=("ios", "android", "web"))
