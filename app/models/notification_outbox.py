from app.extensions import db
from app.models.base import BaseModel


class NotificationOutbox(db.Model, BaseModel):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'processing', 'ok', 'error')",
            name="ck_notification_outbox_status",
        ),
        db.UniqueConstraint(
            "earthquake_id",
            "device_id",
            "notification_type",
            name="uq_notification_outbox_recipient",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    earthquake_id = db.Column(
        db.BigInteger,
        db.ForeignKey("earthquakes.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id = db.Column(
        db.Uuid,
        db.ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False, server_default=db.text("'pending'"))
    attempt_count = db.Column(db.Integer, nullable=False, server_default=db.text("0"))
    available_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    locked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    earthquake = db.relationship("Earthquake", back_populates="outbox")
    device = db.relationship("Device", back_populates="outbox")
    attempts = db.relationship(
        "NotificationAttempt",
        back_populates="outbox",
        cascade="all, delete-orphan",
        order_by="NotificationAttempt.attempted_at.desc()",
    )

    def to_dict(self):
        latest = self.attempts[0] if self.attempts else None
        return {
            "id": self.id,
            "event_id": self.earthquake.ies_event_id,
            "device_id": str(self.device_id),
            "notification_type": self.notification_type,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "expo_ticket_id": latest.expo_ticket_id if latest else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

    def __repr__(self):
        return f"<NotificationOutbox id={self.id} earthquake_id={self.earthquake_id} device_id={self.device_id}>"
