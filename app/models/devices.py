from app.extensions import db
from app.models.base import BaseModel


class Device(db.Model, BaseModel):
    __tablename__ = "devices"
    __table_args__ = (
        db.CheckConstraint("platform IN ('ios', 'android', 'web')", name="ck_devices_platform"),
        db.CheckConstraint("language IN ('ka', 'en')", name="ck_devices_language"),
    )

    device_id = db.Column(db.Uuid, primary_key=True)
    push_token = db.Column(db.Text, unique=True, nullable=True)
    platform = db.Column(db.Text, nullable=False)
    language = db.Column(db.Text, nullable=False, server_default=db.text("'ka'"))
    app_version = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    alert_settings = db.relationship(
        "AlertSettings",
        back_populates="device",
        cascade="all, delete-orphan",
        uselist=False,
    )
    felt_reports = db.relationship("FeltReport", back_populates="device")
    outbox = db.relationship(
        "NotificationOutbox",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "device_id": str(self.device_id),
            "push_token": self.push_token,
            "platform": self.platform,
            "language": self.language,
            "app_version": self.app_version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Device device_id={self.device_id} platform={self.platform}>"
