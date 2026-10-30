from uuid import UUID

from flask import request
from flask_restx import Resource, marshal
from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.nsmodels.notifications import (
    attempt_list_model,
    earthquake_notice_model,
    error_model,
    notification_dispatch_model,
    notification_list_model,
    notification_stats_model,
    notifications_get_parser,
    notifications_ns,
)
from app.extensions import db
from app.models import Earthquake, NotificationAttempt, NotificationOutbox

LIST_DEFAULT_LIMIT = 100
LIST_MAX_LIMIT = 200
STATUSES = ("pending", "processing", "ok", "error")
ALERT_TYPE = "alert"


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


def _status_counts(rows):
    counts = {status: 0 for status in STATUSES}
    for status, total in rows:
        if status in counts:
            counts[status] = int(total)
    return counts


def _filtered_query(args):
    query = NotificationOutbox.query.join(NotificationOutbox.earthquake)
    event_id = args.get("event_id")
    if event_id is not None:
        query = query.filter(Earthquake.ies_event_id == event_id)
    device_id = args.get("device_id")
    if device_id:
        try:
            query = query.filter(NotificationOutbox.device_id == UUID(device_id))
        except (TypeError, ValueError):
            return None, ({"error": "validation_error", "message": "device_id must be a UUID."}, 400)
    status = args.get("status")
    if status:
        query = query.filter(NotificationOutbox.status == status)
    return query, None


def _error(message):
    return {"error": "validation_error", "message": message}, 400


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        return None, _error(f"{name} must be an integer.")
    return value, None



def _matching_device_ids(earthquake):
    rows = db.session.execute(
        db.text(
            """
            SELECT d.device_id
            FROM alert_settings AS a
            JOIN devices AS d ON d.device_id = a.device_id
            WHERE a.enabled
              AND d.is_active
              AND a.min_magnitude <= :magnitude
              AND d.push_token IS NOT NULL
              AND ST_Intersects(
                    a.area,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                  )
            """
        ),
        {
            "magnitude": float(earthquake.magnitude_value),
            "longitude": earthquake.longitude,
            "latitude": earthquake.latitude,
        },
    ).scalars()
    device_ids = []
    for device_id in rows:
        if not isinstance(device_id, UUID):
            device_id = UUID(str(device_id))
        device_ids.append(device_id)
    return device_ids


@notifications_ns.route("/notifications/stats")
class NotificationStatsApi(Resource):
    @notifications_ns.response(200, "Success", notification_stats_model)
    def get(self):
        """Counts for the frontend: totals, status, and each earthquake."""
        status_rows = (
            db.session.query(NotificationOutbox.status, func.count())
            .group_by(NotificationOutbox.status)
            .all()
        )
        event_rows = (
            db.session.query(
                Earthquake.ies_event_id,
                func.count().label("total"),
                func.sum(case((NotificationOutbox.status == "pending", 1), else_=0)).label("pending"),
                func.sum(case((NotificationOutbox.status == "processing", 1), else_=0)).label("processing"),
                func.sum(case((NotificationOutbox.status == "ok", 1), else_=0)).label("ok"),
                func.sum(case((NotificationOutbox.status == "error", 1), else_=0)).label("error"),
            )
            .select_from(NotificationOutbox)
            .join(NotificationOutbox.earthquake)
            .group_by(Earthquake.ies_event_id)
            .order_by(func.count().desc(), Earthquake.ies_event_id.desc())
            .all()
        )
        by_status = _status_counts(status_rows)
        return marshal(
            {
                "total": sum(by_status.values()),
                "devices": int(
                    db.session.query(func.count(func.distinct(NotificationOutbox.device_id))).scalar() or 0
                ),
                "events": len(event_rows),
                "by_status": by_status,
                "by_event": [
                    {
                        "event_id": row.ies_event_id,
                        "total": int(row.total),
                        "pending": int(row.pending or 0),
                        "processing": int(row.processing or 0),
                        "ok": int(row.ok or 0),
                        "error": int(row.error or 0),
                    }
                    for row in event_rows
                ],
            },
            notification_stats_model,
        ), 200


@notifications_ns.route("/notifications/")
class NotificationsApi(Resource):
    @notifications_ns.expect(notifications_get_parser)
    @notifications_ns.response(200, "Success", notification_list_model)
    @notifications_ns.response(400, "Validation Error", error_model)
    def get(self):
        """List sent notifications, newest first."""
        args = notifications_get_parser.parse_args()
        limit, error = _limit(args.get("limit"))
        if error:
            return error
        query, error = _filtered_query(args)
        if error:
            return error
        total = query.count()
        rows = query.order_by(NotificationOutbox.created_at.desc(), NotificationOutbox.id.desc()).limit(limit).all()
        return marshal(
            {"items": [row.to_dict() for row in rows], "total": total, "limit": limit},
            notification_list_model,
        ), 200

    @notifications_ns.expect(earthquake_notice_model, validate=False)
    @notifications_ns.response(200, "Recorded", notification_dispatch_model)
    @notifications_ns.response(400, "Validation Error", error_model)
    def post(self):
        """Queue recipients for an earthquake that is already stored."""
        payload = request.get_json(silent=True)
        event_id, error = _integer((payload or {}).get("event_id") if isinstance(payload, dict) else None, "event_id")
        if error:
            return error
        if event_id < 1:
            return {"error": "validation_error", "message": "event_id must be a positive integer."}, 400
        earthquake = Earthquake.query.filter_by(ies_event_id=event_id).first()
        if earthquake is None:
            return {"error": "not_found", "message": "Earthquake not found."}, 404
        try:
            device_ids = _matching_device_ids(earthquake)
            inserted = 0
            for device_id in device_ids:
                created = db.session.execute(
                    insert(NotificationOutbox)
                    .values(
                        earthquake_id=earthquake.id,
                        device_id=device_id,
                        notification_type=ALERT_TYPE,
                        status="pending",
                    )
                    .on_conflict_do_nothing(constraint="uq_notification_outbox_recipient")
                    .returning(NotificationOutbox.id)
                ).scalar()
                if created is not None:
                    inserted += 1
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return {"error": "server_error", "message": "Notification could not be recorded."}, 500
        return marshal(
            {"event_id": event_id, "matched": len(device_ids), "inserted": inserted},
            notification_dispatch_model,
        ), 200


@notifications_ns.route("/notifications/<int:outbox_id>/attempts")
class NotificationAttemptsApi(Resource):
    @notifications_ns.expect(notifications_get_parser)
    @notifications_ns.response(200, "Success", attempt_list_model)
    @notifications_ns.response(400, "Validation Error", error_model)
    @notifications_ns.response(404, "Not Found", error_model)
    def get(self, outbox_id):
        """List Expo attempts for one outbox row, newest first."""
        if db.session.get(NotificationOutbox, outbox_id) is None:
            return {"error": "not_found", "message": "Notification not found."}, 404
        limit, error = _limit(notifications_get_parser.parse_args().get("limit"))
        if error:
            return error
        query = NotificationAttempt.query.filter_by(outbox_id=outbox_id)
        total = query.count()
        rows = query.order_by(NotificationAttempt.attempted_at.desc(), NotificationAttempt.id.desc()).limit(limit).all()
        return marshal(
            {"items": [row.to_dict() for row in rows], "total": total, "limit": limit},
            attempt_list_model,
        ), 200
