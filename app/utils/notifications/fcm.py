"""Firebase Cloud Messaging client (HTTP v1 via firebase-admin)."""

import logging
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, messaging
from flask import current_app

logger = logging.getLogger("app.notifications.fcm")

# FCM HTTP v1 multicast limit for send_each_for_multicast.
FCM_MULTICAST_LIMIT = 500


@lru_cache(maxsize=1)
def _initialized_for(credentials_path):
    if not credentials_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_PATH is not set. Point it at the Firebase "
            "service account JSON."
        )
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(credentials_path))
    return True


def _ensure_firebase():
    path = (current_app.config.get("FIREBASE_CREDENTIALS_PATH") or "").strip()
    _initialized_for(path)


def _string_data(data):
    return {
        str(key): str(value)
        for key, value in (data or {}).items()
        if value is not None
    }


def _android_config():
    return messaging.AndroidConfig(
        priority="high",
        notification=messaging.AndroidNotification(channel_id="default"),
    )


def send_fcm_message(token, title, body, data=None):
    """Send one FCM message to a device token. Returns the message id."""
    _ensure_firebase()
    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=_string_data(data),
        android=_android_config(),
    )
    message_id = messaging.send(message)
    logger.info("FCM sent message_id=%s", message_id)
    return message_id


def send_fcm_multicast(tokens, title, body, data=None):
    """Send the same FCM payload to many tokens via send_each_for_multicast.

    Tokens are sent in chunks of ``FCM_MULTICAST_LIMIT`` (500). Returns one
    result dict per input token, in the same order:
    ``{"success", "message_id", "exception"}``.
    """
    _ensure_firebase()
    if not tokens:
        return []

    payload = _string_data(data)
    notification = messaging.Notification(title=title, body=body)
    android = _android_config()
    results = []

    for start in range(0, len(tokens), FCM_MULTICAST_LIMIT):
        chunk = tokens[start : start + FCM_MULTICAST_LIMIT]
        message = messaging.MulticastMessage(
            tokens=chunk,
            notification=notification,
            data=payload,
            android=android,
        )
        batch = messaging.send_each_for_multicast(message)
        logger.info(
            "FCM multicast chunk size=%s success=%s failure=%s",
            len(chunk),
            batch.success_count,
            batch.failure_count,
        )
        for response in batch.responses:
            results.append(
                {
                    "success": bool(response.success),
                    "message_id": response.message_id,
                    "exception": response.exception,
                }
            )

    return results
