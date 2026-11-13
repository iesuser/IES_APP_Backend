"""Firebase Cloud Messaging client (HTTP v1 via firebase-admin)."""

import logging
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, messaging
from flask import current_app

logger = logging.getLogger("app.notifications.fcm")


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


def send_fcm_message(token, title, body, data=None):
    """Send one FCM message to a device token. Returns the message id."""
    _ensure_firebase()
    payload = {
        str(key): str(value)
        for key, value in (data or {}).items()
        if value is not None
    }
    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=payload,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(channel_id="default"),
        ),
    )
    message_id = messaging.send(message)
    logger.info("FCM sent message_id=%s", message_id)
    return message_id
