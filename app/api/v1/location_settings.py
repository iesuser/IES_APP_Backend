from datetime import datetime, timezone
from uuid import UUID

from flask_restx import Resource

from app.extensions import db
from app.models import Device, LocationSettings

from app.api.v1.nsmodels.location_settings import (
    location_settings_ns,
    location_sharing_parser,
    location_parser,
    location_settings_error_model,
    location_response_model,
)


def _location_response(device, settings=None):
    return {
        "device_id": str(device.device_id),
        "location_sharing_enabled": (
            settings.location_sharing_enabled if settings else False
        ),
        "latitude": settings.last_latitude if settings else None,
        "longitude": settings.last_longitude if settings else None,
        "accuracy": settings.last_accuracy if settings else None,
        "recorded_at": (
            settings.last_location_at.isoformat()
            if settings and settings.last_location_at
            else None
        ),
        "location_updated_at": (
            settings.last_location_updated_at.isoformat()
            if settings and settings.last_location_updated_at
            else None
        ),
    }


def _save_device_location(device_id):
    try:
        device_uuid = UUID(device_id)
    except ValueError:
        return {"message": "Invalid device_id"}, 400

    device = Device.query.get(device_uuid)

    if device is None:
        return {"message": "Device not found"}, 404

    settings = device.location_settings
    if settings is None or not settings.location_sharing_enabled:
        return {"message": "Location sharing is disabled"}, 403

    args = location_parser.parse_args()
    latitude = args["latitude"]
    longitude = args["longitude"]
    accuracy = args.get("accuracy")
    recorded_at = args.get("recorded_at")

    if not -90 <= latitude <= 90:
        return {"message": "Invalid latitude"}, 400

    if not -180 <= longitude <= 180:
        return {"message": "Invalid longitude"}, 400

    if accuracy is not None and accuracy < 0:
        return {"message": "Invalid accuracy"}, 400

    if recorded_at:
        try:
            location_time = datetime.fromisoformat(
                recorded_at.replace("Z", "+00:00")
            )

            if location_time.tzinfo is None:
                return {"message": "recorded_at must include timezone"}, 400

        except ValueError:
            return {"message": "Invalid recorded_at format"}, 400
    else:
        location_time = datetime.now(timezone.utc)

    settings.last_latitude = latitude
    settings.last_longitude = longitude
    settings.last_accuracy = accuracy
    settings.last_location_at = location_time
    settings.last_location_updated_at = datetime.now(timezone.utc)
    device.last_seen_at = datetime.now(timezone.utc)
    device.save()

    return _location_response(device, settings), 200


@location_settings_ns.route("/devices/<string:device_id>/location/")
class LocationSettingsApi(Resource):

    @location_settings_ns.marshal_with(location_response_model)
    @location_settings_ns.response(
        400, "Invalid device ID", location_settings_error_model
    )
    @location_settings_ns.response(
        404, "Device not found", location_settings_error_model
    )
    def get(self, device_id):
        """Return sharing state and the last known location.

        Location fields are null until a location has been received. The
        response distinguishes the device's ``recorded_at`` from the server's
        ``location_updated_at`` timestamp.
        """

        try:
            device_uuid = UUID(device_id)
        except ValueError:
            return {"message": "Invalid device_id"}, 400

        device = Device.query.get(device_uuid)

        if device is None:
            return {"message": "Device not found"}, 404

        return _location_response(device, device.location_settings), 200

    @location_settings_ns.expect(location_sharing_parser)
    @location_settings_ns.marshal_with(location_response_model)
    @location_settings_ns.response(
        400, "Invalid device ID", location_settings_error_model
    )
    @location_settings_ns.response(
        404, "Device not found", location_settings_error_model
    )
    def patch(self, device_id):
        """Enable or disable sharing without deleting the last location.

        Enabling sharing does not create a location; submit one with PUT.
        Disabling sharing preserves the last saved location.
        """

        try:
            device_uuid = UUID(device_id)
        except ValueError:
            return {"message": "Invalid device_id"}, 400

        device = Device.query.get(device_uuid)

        if device is None:
            return {"message": "Device not found"}, 404

        args = location_sharing_parser.parse_args()
        enabled = args["location_sharing_enabled"]

        settings = device.location_settings
        if settings is None:
            settings = LocationSettings(device=device)
            db.session.add(settings)

        settings.location_sharing_enabled = enabled
        settings.location_sharing_updated_at = datetime.now(timezone.utc)

        device.save()

        return _location_response(device, settings), 200

    @location_settings_ns.expect(location_parser)
    @location_settings_ns.marshal_with(location_response_model)
    @location_settings_ns.response(
        400, "Invalid location data", location_settings_error_model
    )
    @location_settings_ns.response(
        403, "Location sharing is disabled", location_settings_error_model
    )
    @location_settings_ns.response(
        404, "Device not found", location_settings_error_model
    )
    def put(self, device_id):
        """Replace the last known location of an already registered device.

        This endpoint does not register devices. The device must already exist
        and location sharing must be enabled; each request replaces the stored
        last known coordinates.
        """

        return _save_device_location(device_id)

