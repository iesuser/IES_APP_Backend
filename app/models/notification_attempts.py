from app.extensions import db
from app.models.base import BaseModel


class NotificationAttempt(db.Model, BaseModel):
    __tablename__ = "notification_attempts"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('ok', 'error')",
            name="ck_notification_attempts_status",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    outbox_id = db.Column(
        db.BigInteger,
        db.ForeignKey("notification_outbox.id", ondelete="CASCADE"),
        nullable=False,
    )
    expo_ticket_id = db.Column(db.Text, nullable=True)
    expo_receipt_id = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    attempted_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    outbox = db.relationship("NotificationOutbox", back_populates="attempts")

    def to_dict(self):
        return {
            "id": self.id,
            "outbox_id": self.outbox_id,
            "expo_ticket_id": self.expo_ticket_id,
            "expo_receipt_id": self.expo_receipt_id,
            "status": self.status,
            "error_message": self.error_message,
            "attempted_at": self.attempted_at.isoformat() if self.attempted_at else None,
        }

    def __repr__(self):
        return f"<NotificationAttempt id={self.id} outbox_id={self.outbox_id} status={self.status}>"
