"""Persist notification outbox rows and FCM attempts."""

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.extensions import db
from app.models import NotificationAttempt, NotificationOutbox

ALERT_TYPE = "alert"


def enqueue_recipients(earthquake_id, device_ids):
    """Insert pending outbox rows for new (earthquake, device) pairs.

    Existing unique pairs are skipped. Returns
    ``[{"outbox_id", "device_id"}, ...]`` for newly inserted rows only.
    """
    inserted = []
    for device_id in device_ids:
        row = db.session.execute(
            insert(NotificationOutbox)
            .values(
                earthquake_id=earthquake_id,
                device_id=device_id,
                notification_type=ALERT_TYPE,
                status="pending",
            )
            .on_conflict_do_nothing(constraint="uq_notification_outbox_recipient")
            .returning(NotificationOutbox.id, NotificationOutbox.device_id)
        ).first()
        if row is not None:
            inserted.append({"outbox_id": row.id, "device_id": row.device_id})
    db.session.commit()
    return inserted


def ensure_recipients(earthquake_id, device_ids, *, reset_existing=False):
    """Return outbox rows for every device, creating missing ones.

    When ``reset_existing`` is true, existing rows are reset to ``pending`` so
    they can be sent again. Returns
    ``[{"outbox_id", "device_id", "created"}, ...]`` in device order.
    """
    rows = []
    for device_id in device_ids:
        existing = NotificationOutbox.query.filter_by(
            earthquake_id=earthquake_id,
            device_id=device_id,
            notification_type=ALERT_TYPE,
        ).first()
        if existing is None:
            created = db.session.execute(
                insert(NotificationOutbox)
                .values(
                    earthquake_id=earthquake_id,
                    device_id=device_id,
                    notification_type=ALERT_TYPE,
                    status="pending",
                )
                .returning(NotificationOutbox.id, NotificationOutbox.device_id)
            ).first()
            rows.append(
                {
                    "outbox_id": created.id,
                    "device_id": created.device_id,
                    "created": True,
                }
            )
            continue

        if reset_existing:
            existing.status = "pending"
            existing.locked_at = None
            existing.processed_at = None

        rows.append(
            {
                "outbox_id": existing.id,
                "device_id": existing.device_id,
                "created": False,
            }
        )

    db.session.commit()
    return rows


def mark_processing(outbox_ids):
    """Mark outbox rows as processing before an FCM send."""
    if not outbox_ids:
        return
    now = datetime.now(timezone.utc)
    (
        NotificationOutbox.query.filter(NotificationOutbox.id.in_(list(outbox_ids))).update(
            {
                NotificationOutbox.status: "processing",
                NotificationOutbox.locked_at: now,
            },
            synchronize_session=False,
        )
    )
    db.session.commit()


def record_attempts(results):
    """Update outbox rows and insert attempt rows for a batch of send results.

    Each item needs ``outbox_id`` and ``success``. Optional: ``message_id``,
    ``error_message``.
    """
    if not results:
        return

    now = datetime.now(timezone.utc)
    outbox_ids = [item["outbox_id"] for item in results]
    rows = {
        row.id: row
        for row in NotificationOutbox.query.filter(NotificationOutbox.id.in_(outbox_ids)).all()
    }

    for item in results:
        outbox = rows.get(item["outbox_id"])
        if outbox is None:
            continue

        success = bool(item.get("success"))
        outbox.attempt_count = int(outbox.attempt_count or 0) + 1
        outbox.locked_at = None
        if success:
            outbox.status = "ok"
            outbox.processed_at = now
        else:
            outbox.status = "error"

        error = item.get("error_message")
        if error is not None and not isinstance(error, str):
            error = str(error)

        # Reuse expo_ticket_id for the FCM message id until the column is renamed.
        db.session.add(
            NotificationAttempt(
                outbox_id=outbox.id,
                expo_ticket_id=item.get("message_id"),
                status="ok" if success else "error",
                error_message=error,
                attempted_at=now,
            )
        )

    db.session.commit()
