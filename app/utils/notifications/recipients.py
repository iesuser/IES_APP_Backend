"""Select devices whose alert polygon contains an earthquake epicenter."""

from uuid import UUID

from app.extensions import db


def matching_recipients(latitude, longitude, magnitude):
    """Return recipients whose enabled alert area covers the epicenter.

    Each item is ``{"device_id", "fcm_token", "language"}``. A device matches
    when alert settings are enabled, magnitude is at least ``min_magnitude``,
    the device is active, it has an FCM token with notifications enabled, and
    the epicenter intersects the stored area.
    """
    rows = db.session.execute(
        db.text(
            """
            SELECT DISTINCT ON (d.device_id)
                   d.device_id,
                   ft.fcm_token,
                   d.language
            FROM alert_settings AS a
            JOIN devices AS d ON d.device_id = a.device_id
            JOIN fcm_tokens AS ft ON ft.device_id = d.device_id
            WHERE a.enabled
              AND d.is_active
              AND a.min_magnitude <= :magnitude
              AND ft.notifications_enabled
              AND ST_Intersects(
                    a.area,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                  )
            ORDER BY d.device_id, ft.updated_at DESC NULLS LAST, ft.id DESC
            """
        ),
        {
            "magnitude": float(magnitude),
            "longitude": float(longitude),
            "latitude": float(latitude),
        },
    ).mappings()

    recipients = []
    for row in rows:
        device_id = row["device_id"]
        if not isinstance(device_id, UUID):
            device_id = UUID(str(device_id))
        recipients.append(
            {
                "device_id": device_id,
                "fcm_token": row["fcm_token"],
                "language": row["language"] or "ka",
            }
        )
    return recipients


def matching_device_ids(latitude, longitude, magnitude):
    """Return only the device UUIDs for matching recipients."""
    return [item["device_id"] for item in matching_recipients(latitude, longitude, magnitude)]
