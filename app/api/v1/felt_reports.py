from datetime import datetime, timedelta
from uuid import UUID

from flask_restx import Resource, marshal

from app.api.v1.nsmodels.felt_reports import (
    error_model,
    felt_report_list_model,
    felt_report_model,
    felt_report_parser,
    felt_reports_get_parser,
    felt_reports_ns,
)
from app.extensions import db
from app.models import Device, FeltReport

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


@felt_reports_ns.route("/felt-reports/")
class FeltReportsApi(Resource):
    @felt_reports_ns.expect(felt_reports_get_parser)
    @felt_reports_ns.response(200, "Success", felt_report_list_model)
    @felt_reports_ns.response(400, "Validation Error", error_model)
    def get(self):
        """List felt reports, newest reported_at first."""
        limit, error = _limit(felt_reports_get_parser.parse_args().get("limit"))
        if error:
            return error
        total = FeltReport.query.count()
        rows = (
            FeltReport.query.order_by(FeltReport.reported_at.desc(), FeltReport.id.desc())
            .limit(limit)
            .all()
        )
        return marshal(
            {"items": [row.to_dict() for row in rows], "total": total, "limit": limit},
            felt_report_list_model,
        ), 200

    @felt_reports_ns.expect(felt_report_parser)
    @felt_reports_ns.response(201, "Created", felt_report_model)
    @felt_reports_ns.response(400, "Validation Error", error_model)
    @felt_reports_ns.response(404, "Not Found", error_model)
    def post(self):
        """Store a felt report. felt_at is reported_at minus minutes_ago."""
        args = felt_report_parser.parse_args()
        try:
            reported_at = datetime.fromisoformat(args["reported_at"].replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            return {"error": "validation_error", "message": "reported_at must be an ISO 8601 datetime."}, 400
        if reported_at.tzinfo is None or reported_at.utcoffset() is None:
            return {"error": "validation_error", "message": "reported_at must include a timezone."}, 400

        minutes_ago = args.get("minutes_ago")
        if minutes_ago is not None and minutes_ago < 0:
            return {"error": "validation_error", "message": "minutes_ago must be zero or greater."}, 400

        device_id = None
        if args.get("device_id"):
            try:
                device_id = UUID(args["device_id"])
            except (TypeError, ValueError):
                return {"error": "validation_error", "message": "device_id must be a UUID."}, 400
            if db.session.get(Device, device_id) is None:
                return {"error": "not_found", "message": "Device not found."}, 404

        felt_at = None
        if minutes_ago is not None:
            felt_at = reported_at - timedelta(minutes=minutes_ago)

        report = FeltReport(
            device_id=device_id,
            intensity=args["intensity"],
            minutes_ago=minutes_ago,
            reported_at=reported_at,
            felt_at=felt_at,
            language=args.get("language"),
            platform=args.get("platform"),
        )
        report.create()
        return marshal(report.to_dict(), felt_report_model), 201


@felt_reports_ns.route("/felt-reports/<int:report_id>")
class FeltReportDetailApi(Resource):
    @felt_reports_ns.response(200, "Success", felt_report_model)
    @felt_reports_ns.response(404, "Not Found", error_model)
    def get(self, report_id):
        """Return one felt report."""
        report = db.session.get(FeltReport, report_id)
        if report is None:
            return {"error": "not_found", "message": "Felt report not found."}, 404
        return marshal(report.to_dict(), felt_report_model), 200
