"""Match an earthquake to alert areas and notify recipients."""

import logging

from app.extensions import db
from app.models import Earthquake
from app.utils.notifications.outbox import (
    enqueue_recipients,
    ensure_recipients,
    mark_processing,
)
from app.utils.notifications.recipients import matching_recipients
from app.utils.notifications.send import send_notifications

logger = logging.getLogger("app.notifications")


def dispatch_earthquake_notifications(earthquake, *, force_resend=False):
    """Match devices, update outbox rows, and send FCM pushes in bulk.

    By default only newly inserted outbox rows are sent (idempotent).

    With ``force_resend=True``, every current match is sent again even if that
    device already has an outbox row / prior attempt for this earthquake.

    Returns ``(matched, inserted, notified)`` where ``inserted`` is the number
    of outbox rows prepared for this send.
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
    device_ids = list(by_device.keys())

    if force_resend:
        outbox_rows = ensure_recipients(
            earthquake.id,
            device_ids,
            reset_existing=True,
        )
    else:
        outbox_rows = [
            {**row, "created": True}
            for row in enqueue_recipients(earthquake.id, device_ids)
        ]

    inserted = len(outbox_rows)
    if not outbox_rows:
        return matched, 0, 0

    to_send = []
    for row in outbox_rows:
        recipient = by_device[row["device_id"]]
        to_send.append(
            {
                "device_id": recipient["device_id"],
                "fcm_token": recipient["fcm_token"],
                "language": recipient["language"],
                "outbox_id": row["outbox_id"],
            }
        )

    mark_processing([row["outbox_id"] for row in outbox_rows])
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


def dispatch_earthquake_notifications_by_id(earthquake_id, *, force_resend=False):
    """Load an earthquake by primary key and dispatch notifications."""
    earthquake = db.session.get(Earthquake, earthquake_id)
    if earthquake is None:
        logger.warning("notification dispatch skipped: earthquake id=%s not found", earthquake_id)
        return 0, 0, 0
    return dispatch_earthquake_notifications(earthquake, force_resend=force_resend)