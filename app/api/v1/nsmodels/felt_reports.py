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
        "device_id": fields.String(required=True),
        "intensity": fields.String(required=True, example="MODERATE", enum=["MILD", "MODERATE", "SEVERE"]),
        "time_ago": fields.Integer(required=True, example=5),
        "latitude": fields.Float(required=True, example=41.7151),
        "longitude": fields.Float(required=True, example=44.8271),
        "accuracy": fields.Float(required=False, example=10),
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

felt_report_device_list_model = felt_reports_ns.model(
    "DeviceFeltReportList",
    {
        "device_id": fields.String(required=True),
        "items": fields.List(fields.Nested(felt_report_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

felt_reports_get_parser = reqparse.RequestParser()
felt_reports_get_parser.add_argument("limit", type=int, required=False, location="args")

felt_report_parser = reqparse.RequestParser()
felt_report_parser.add_argument("intensity", type=str, required=True, location="json", choices=("MILD", "MODERATE", "SEVERE"))
felt_report_parser.add_argument("time_ago", type=int, required=True, location="json")
felt_report_parser.add_argument("latitude", type=float, required=True, location="json")
felt_report_parser.add_argument("longitude", type=float, required=True, location="json")
felt_report_parser.add_argument("accuracy", type=float, required=False, location="json")
