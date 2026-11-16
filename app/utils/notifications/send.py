"""Deliver push notifications to matched devices via FCM."""

import logging
from collections import defaultdict

from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import UnregisteredError

from app.utils.notifications.fcm import send_fcm_message, send_fcm_multicast
from app.utils.notifications.outbox import record_attempts

logger = logging.getLogger("app.notifications")


def _message_copy(language, *, magnitude, location_ge, location_en):
    mag = f"{float(magnitude):.1f}" if magnitude is not None else "?"
    if (language or "ka").lower().startswith("en"):
        place = location_en or location_ge or "unknown location"
        return "Earthquake", f"M{mag} — {place}"
    place = location_ge or location_en or "უცნობი ადგილი"
    return "მიწისძვრა", f"M{mag} — {place}"


def _language_key(language):
    if (language or "ka").lower().startswith("en"):
        return "en"
    return "ka"


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
    outbox_id=None,
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
        if outbox_id is not None:
            record_attempts(
                [
                    {
                        "outbox_id": outbox_id,
                        "success": False,
                        "error_message": "missing fcm_token",
                    }
                ]
            )
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
        if outbox_id is not None:
            record_attempts(
                [{"outbox_id": outbox_id, "success": True, "message_id": message_id}]
            )
        return True
    except UnregisteredError as exc:
        logger.warning("FCM token unregistered for device_id=%s", device_id)
        print(f"[notification] FCM unregistered device_id={device_id}", flush=True)
        if outbox_id is not None:
            record_attempts(
                [
                    {
                        "outbox_id": outbox_id,
                        "success": False,
                        "error_message": str(exc),
                    }
                ]
            )
        return False
    except FirebaseError as exc:
        logger.exception("FCM send failed device_id=%s event_id=%s", device_id, event_id)
        print(f"[notification] FCM error device_id={device_id}", flush=True)
        if outbox_id is not None:
            record_attempts(
                [
                    {
                        "outbox_id": outbox_id,
                        "success": False,
                        "error_message": str(exc),
                    }
                ]
            )
        return False


def send_notifications(
    recipients,
    event_id,
    *,
    latitude=None,
    longitude=None,
    magnitude=None,
    location_ge=None,
    location_en=None,
):
    """Send FCM pushes in bulk. Groups by language, then multicast in chunks of 500.

    ``recipients`` items need ``device_id``, ``fcm_token``, and ``language``.
    Optional ``outbox_id`` records attempts in ``notification_outbox``.
    Returns the number of successful sends.
    """
    grouped = defaultdict(list)
    for recipient in recipients:
        token = recipient.get("fcm_token")
        if not token:
            logger.warning(
                "skip FCM send: device_id=%s has no token",
                recipient.get("device_id"),
            )
            if recipient.get("outbox_id") is not None:
                record_attempts(
                    [
                        {
                            "outbox_id": recipient["outbox_id"],
                            "success": False,
                            "error_message": "missing fcm_token",
                        }
                    ]
                )
            continue
        grouped[_language_key(recipient.get("language"))].append(recipient)

    notified = 0
    for language, group in grouped.items():
        title, body = _message_copy(
            language,
            magnitude=magnitude,
            location_ge=location_ge,
            location_en=location_en,
        )
        tokens = [item["fcm_token"] for item in group]
        print(
            f"[notification] event_id={event_id} language={language} "
            f"recipients={len(group)} title={title!r} body={body!r}",
            flush=True,
        )
        data = {
            "event_id": event_id,
            "title": title,
            "body": body,
            "latitude": latitude,
            "longitude": longitude,
            "magnitude": magnitude,
        }
        try:
            results = send_fcm_multicast(tokens, title, body, data=data)
        except FirebaseError as exc:
            logger.exception(
                "FCM multicast failed event_id=%s language=%s count=%s",
                event_id,
                language,
                len(group),
            )
            print(
                f"[notification] FCM multicast error event_id={event_id} language={language}",
                flush=True,
            )
            record_attempts(
                [
                    {
                        "outbox_id": item["outbox_id"],
                        "success": False,
                        "error_message": str(exc),
                    }
                    for item in group
                    if item.get("outbox_id") is not None
                ]
            )
            continue

        attempt_rows = []
        for recipient, result in zip(group, results):
            device_id = recipient["device_id"]
            outbox_id = recipient.get("outbox_id")
            if result["success"]:
                notified += 1
                print(
                    f"[notification] FCM ok device_id={device_id} message_id={result['message_id']}",
                    flush=True,
                )
                if outbox_id is not None:
                    attempt_rows.append(
                        {
                            "outbox_id": outbox_id,
                            "success": True,
                            "message_id": result["message_id"],
                        }
                    )
                continue

            exc = result["exception"]
            if isinstance(exc, UnregisteredError):
                logger.warning("FCM token unregistered for device_id=%s", device_id)
                print(f"[notification] FCM unregistered device_id={device_id}", flush=True)
            else:
                logger.error(
                    "FCM send failed device_id=%s event_id=%s error=%s",
                    device_id,
                    event_id,
                    exc,
                )
                print(f"[notification] FCM error device_id={device_id} error={exc}", flush=True)

            if outbox_id is not None:
                attempt_rows.append(
                    {
                        "outbox_id": outbox_id,
                        "success": False,
                        "error_message": str(exc) if exc is not None else "FCM send failed",
                    }
                )

        record_attempts(attempt_rows)

    return notified
