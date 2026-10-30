from flask_restx import fields, reqparse

from app.extensions import api

notifications_ns = api.namespace(
    "Notifications",
    description="Which devices are notified for a published earthquake",
    path="/api/v1",
)

error_model = notifications_ns.model(
    "NotificationError",
    {
        "error": fields.String(required=True, example="validation_error"),
        "message": fields.String(required=True, example="status must be pending, ok, or error."),
    },
)

notification_model = notifications_ns.model(
    "Notification",
    {
        "id": fields.Integer(required=True, example=1),
        "event_id": fields.Integer(required=True, example=6),
        "device_id": fields.String(required=True),
        "notification_type": fields.String(required=True, example="alert"),
        "status": fields.String(required=True, example="pending", enum=["pending", "processing", "ok", "error"]),
        "attempt_count": fields.Integer(required=True, example=0),
        "expo_ticket_id": fields.String(required=False),
        "created_at": fields.String(required=True),
        "processed_at": fields.String(required=False),
    },
)

attempt_model = notifications_ns.model(
    "NotificationAttempt",
    {
        "id": fields.Integer(required=True, example=1),
        "outbox_id": fields.Integer(required=True, example=1),
        "expo_ticket_id": fields.String(required=False),
        "expo_receipt_id": fields.String(required=False),
        "status": fields.String(required=True, example="ok", enum=["ok", "error"]),
        "error_message": fields.String(required=False),
        "attempted_at": fields.String(required=True),
    },
)

attempt_list_model = notifications_ns.model(
    "NotificationAttemptList",
    {
        "items": fields.List(fields.Nested(attempt_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

notification_list_model = notifications_ns.model(
    "NotificationList",
    {
        "items": fields.List(fields.Nested(notification_model), required=True),
        "total": fields.Integer(required=True, example=1),
        "limit": fields.Integer(required=True, example=100),
    },
)

status_counts_model = notifications_ns.model(
    "NotificationStatusCounts",
    {
        "pending": fields.Integer(required=True, example=0),
        "processing": fields.Integer(required=True, example=0),
        "ok": fields.Integer(required=True, example=1),
        "error": fields.Integer(required=True, example=0),
    },
)

event_stats_model = notifications_ns.model(
    "NotificationEventStats",
    {
        "event_id": fields.Integer(required=True, example=6),
        "total": fields.Integer(required=True, example=1),
        "pending": fields.Integer(required=True, example=0),
        "processing": fields.Integer(required=True, example=0),
        "ok": fields.Integer(required=True, example=1),
        "error": fields.Integer(required=True, example=0),
    },
)

notification_stats_model = notifications_ns.model(
    "NotificationStats",
    {
        "total": fields.Integer(required=True, example=1),
        "devices": fields.Integer(required=True, example=1),
        "events": fields.Integer(required=True, example=1),
        "by_status": fields.Nested(status_counts_model, required=True),
        "by_event": fields.List(fields.Nested(event_stats_model), required=True),
    },
)

earthquake_notice_model = notifications_ns.model(
    "NotificationRequest",
    {"event_id": fields.Integer(required=True, example=16)},
)

notification_dispatch_model = notifications_ns.model(
    "NotificationDispatch",
    {
        "event_id": fields.Integer(required=True, example=16),
        "matched": fields.Integer(required=True, example=1),
        "inserted": fields.Integer(required=True, example=1),
    },
)

notifications_get_parser = reqparse.RequestParser()
notifications_get_parser.add_argument("limit", type=int, required=False, location="args")
notifications_get_parser.add_argument("event_id", type=int, required=False, location="args")
notifications_get_parser.add_argument("device_id", type=str, required=False, location="args")
notifications_get_parser.add_argument(
    "status",
    type=str,
    required=False,
    location="args",
    choices=("pending", "processing", "ok", "error"),
)
