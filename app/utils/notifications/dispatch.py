"""Match an earthquake to alert areas and notify recipients."""

import logging
import threading

from app.extensions import db
from app.models import Earthquake
from app.utils.notifications.outbox import enqueue_recipients, mark_processing
from app.utils.notifications.recipients import matching_recipients
from app.utils.notifications.send import send_notifications

logger = logging.getLogger("app.notifications")


def dispatch_earthquake_notifications(earthquake):
    """Match devices, write outbox rows, and send new FCM pushes in bulk.

    Already-queued (earthquake, device) pairs are not inserted again and are
    not re-sent. Returns ``(matched, inserted, notified)``.
    """
    recipients = matching_recipients(
        earthquake.latitude,
        earthquake.longitude,
        earthquake.magnitude_value,
    )
    matched = len(recipients)
    if not recipients:
        return 0, 0, 0

    by_device = {recipient["device_id"]: recipient for recipient in recipients}
    inserted_rows = enqueue_recipients(earthquake.id, list(by_device.keys()))
    inserted = len(inserted_rows)
    if not inserted_rows:
        return matched, 0, 0

    to_send = []
    for row in inserted_rows:
        recipient = by_device[row["device_id"]]
        to_send.append(
            {
                "device_id": recipient["device_id"],
                "fcm_token": recipient["fcm_token"],
                "language": recipient["language"],
                "outbox_id": row["outbox_id"],
            }
        )

    mark_processing([row["outbox_id"] for row in inserted_rows])
    notified = send_notifications(
        to_send,
        earthquake.ies_event_id,
        latitude=earthquake.latitude,
        longitude=earthquake.longitude,
        magnitude=float(earthquake.magnitude_value),
        location_ge=earthquake.location_ge,
        location_en=earthquake.location_en,
    )
    return matched, inserted, notified


def dispatch_earthquake_notifications_by_id(earthquake_id):
    """Load an earthquake by primary key and dispatch notifications."""
    earthquake = db.session.get(Earthquake, earthquake_id)
    if earthquake is None:
        logger.warning("notification dispatch skipped: earthquake id=%s not found", earthquake_id)
        return 0, 0, 0
    return dispatch_earthquake_notifications(earthquake)


def schedule_earthquake_notifications(app, earthquake_id):
    """Run dispatch in a background thread so the HTTP response is not delayed."""

    def _run():
        with app.app_context():
            try:
                matched, inserted, notified = dispatch_earthquake_notifications_by_id(earthquake_id)
                logger.info(
                    "background notification dispatch finished earthquake_id=%s "
                    "matched=%s inserted=%s notified=%s",
                    earthquake_id,
                    matched,
                    inserted,
                    notified,
                )
            except Exception:
                logger.exception(
                    "background notification dispatch failed earthquake_id=%s",
                    earthquake_id,
                )

    threading.Thread(
        target=_run,
        name=f"notify-earthquake-{earthquake_id}",
        daemon=True,
    ).start()
