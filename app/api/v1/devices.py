from uuid import UUID

from flask_restx import Resource, marshal
from sqlalchemy.exc import IntegrityError

from app.api.v1.nsmodels.devices import (
    device_list_model,
    device_model,
    device_parser,
    devices_get_parser,
    devices_ns,
    error_model,
)
from app.extensions import db
from app.models import Device

LIST_DEFAULT_LIMIT = 100
LIST_MAX_LIMIT = 200


def _clean(value):
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _limit(value):
    if value is None:
        return LIST_DEFAULT_LIMIT, None
    if value < 1 or value > LIST_MAX_LIMIT:
        return None, (
            {
                "error": "validation_error",
                "message": f"limit must be between 1 and {LIST_MAX_LIMIT}.",
            },
            400,
        )
    return value, None


@devices_ns.route("/devices/")
class DevicesApi(Resource):
    @devices_ns.expect(devices_get_parser)
    @devices_ns.response(200, "Success", device_list_model)
    @devices_ns.response(400, "Validation Error", error_model)
    def get(self):
        """List devices, most recently seen first."""
        limit, error = _limit(devices_get_parser.parse_args().get("limit"))
        if error:
            return error
        total = Device.query.count()
        rows = (
            Device.query.order_by(Device.last_seen_at.desc(), Device.device_id.desc())
            .limit(limit)
            .all()
        )
        return marshal(
            {"items": [row.to_dict() for row in rows], "total": total, "limit": limit},
            device_list_model,
        ), 200

    @devices_ns.expect(device_parser)
    @devices_ns.response(201, "Created", device_model)
    @devices_ns.response(200, "Updated", device_model)
    @devices_ns.response(400, "Validation Error", error_model)
    @devices_ns.response(409, "Conflict", error_model)
    def post(self):
        """Register a device or refresh last_seen_at for an existing device_id."""
        args = device_parser.parse_args()
        try:
            device_id = UUID(args["device_id"])
        except (TypeError, ValueError):
            return {"error": "validation_error", "message": "device_id must be a UUID."}, 400

        push_token = _clean(args.get("push_token"))
        app_version = _clean(args.get("app_version"))
        if push_token is not None and len(push_token) > 4096:
            return {"error": "validation_error", "message": "push_token is too long."}, 400
        if app_version is not None and len(app_version) > 64:
            return {"error": "validation_error", "message": "app_version is too long."}, 400

        if push_token:
            holder = Device.query.filter(
                Device.push_token == push_token,
                Device.device_id != device_id,
            ).first()
            if holder is not None:
                holder.push_token = None
                db.session.flush()

        device = db.session.get(Device, device_id)
        created = device is None
        if device is None:
            device = Device(
                device_id=device_id,
                push_token=push_token,
                platform=args["platform"],
                language=args.get("language") or "ka",
                app_version=app_version,
            )
            db.session.add(device)
        else:
            device.push_token = push_token
            device.platform = args["platform"]
            device.language = args.get("language") or "ka"
            device.app_version = app_version
            device.last_seen_at = db.session.scalar(db.select(db.func.now()))
            device.updated_at = device.last_seen_at

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {"error": "conflict", "message": "Could not store the device."}, 409

        db.session.refresh(device)
        return marshal(device.to_dict(), device_model), 201 if created else 200


@devices_ns.route("/devices/<string:device_id>")
class DeviceDetailApi(Resource):
    @devices_ns.response(200, "Success", device_model)
    @devices_ns.response(400, "Validation Error", error_model)
    @devices_ns.response(404, "Not Found", error_model)
    def get(self, device_id):
        """Return one device."""
        try:
            device_uuid = UUID(device_id)
        except (TypeError, ValueError):
            return {"error": "validation_error", "message": "device_id must be a UUID."}, 400
        device = db.session.get(Device, device_uuid)
        if device is None:
            return {"error": "not_found", "message": "Device not found."}, 404
        return marshal(device.to_dict(), device_model), 200
