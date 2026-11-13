"""Match an earthquake to alert areas and notify recipients."""

import logging
import threading

from app.extensions import db
from app.models import Earthquake
from app.utils.notifications.recipients import matching_recipients
from app.utils.notifications.send import send_notification

logger = logging.getLogger("app.notifications")


def dispatch_earthquake_notifications(earthquake):
    """Find matching devices for ``earthquake`` and send each an FCM push.

    Returns ``(matched, notified)`` counts.
    """
    recipients = matching_recipients(
        earthquake.latitude,
        earthquake.longitude,
        earthquake.magnitude_value,
    )
    event_id = earthquake.ies_event_id
    notified = 0
    for recipient in recipients:
        ok = send_notification(
            recipient["device_id"],
            event_id,
            fcm_token=recipient["fcm_token"],
            language=recipient["language"],
            latitude=earthquake.latitude,
            longitude=earthquake.longitude,
            magnitude=float(earthquake.magnitude_value),
            location_ge=earthquake.location_ge,
            location_en=earthquake.location_en,
        )
        if ok:
            notified += 1
    return len(recipients), notified


def dispatch_earthquake_notifications_by_id(earthquake_id):
    """Load an earthquake by primary key and dispatch notifications."""
    earthquake = db.session.get(Earthquake, earthquake_id)
    if earthquake is None:
        logger.warning("notification dispatch skipped: earthquake id=%s not found", earthquake_id)
        return 0, 0
    return dispatch_earthquake_notifications(earthquake)


def schedule_earthquake_notifications(app, earthquake_id):
    """Run dispatch in a background thread so the HTTP response is not delayed."""

    def _run():
        with app.app_context():
            try:
                matched, notified = dispatch_earthquake_notifications_by_id(earthquake_id)
                logger.info(
                    "background notification dispatch finished earthquake_id=%s matched=%s notified=%s",
                    earthquake_id,
                    matched,
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
