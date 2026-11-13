"""Deliver a push notification to one matched device via FCM."""

import logging

from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import UnregisteredError

from app.utils.notifications.fcm import send_fcm_message

logger = logging.getLogger("app.notifications")


def _message_copy(language, *, magnitude, location_ge, location_en):
    mag = f"{float(magnitude):.1f}" if magnitude is not None else "?"
    if (language or "ka").lower().startswith("en"):
        place = location_en or location_ge or "unknown location"
        return "Earthquake", f"M{mag} — {place}"
    place = location_ge or location_en or "უცნობი ადგილი"
    return "მიწისძვრა", f"M{mag} — {place}"


def send_notification(
    device_id,
    event_id,
    *,
    fcm_token,
    language="ka",
    latitude=None,
    longitude=None,
    magnitude=None,
    location_ge=None,
    location_en=None,
):
    """Send an FCM push for one matched device. Also logs to the console."""
    title, body = _message_copy(
        language,
        magnitude=magnitude,
        location_ge=location_ge,
        location_en=location_en,
    )
    print(
        f"[notification] event_id={event_id} device_id={device_id} "
        f"title={title!r} body={body!r}",
        flush=True,
    )
    if not fcm_token:
        logger.warning("skip FCM send: device_id=%s has no token", device_id)
        return False

    data = {
        "event_id": event_id,
        "title": title,
        "body": body,
        "latitude": latitude,
        "longitude": longitude,
        "magnitude": magnitude,
    }
    try:
        message_id = send_fcm_message(fcm_token, title, body, data=data)
        print(f"[notification] FCM ok device_id={device_id} message_id={message_id}", flush=True)
        return True
    except UnregisteredError:
        logger.warning("FCM token unregistered for device_id=%s", device_id)
        print(f"[notification] FCM unregistered device_id={device_id}", flush=True)
        return False
    except FirebaseError:
        logger.exception("FCM send failed device_id=%s event_id=%s", device_id, event_id)
        print(f"[notification] FCM error device_id={device_id}", flush=True)
        return False
