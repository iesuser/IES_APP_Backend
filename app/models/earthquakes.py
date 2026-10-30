from app.extensions import db
from app.models.base import BaseModel


class Earthquake(db.Model, BaseModel):
    __tablename__ = "earthquakes"
    __table_args__ = (
        db.CheckConstraint(
            "(created_by_kind IS NULL AND created_by_name IS NULL) OR "
            "(created_by_kind IN ('user', 'service') AND created_by_name <> '')",
            name="ck_earthquakes_created_by",
        ),
        db.CheckConstraint(
            "(updated_by_kind IS NULL AND updated_by_name IS NULL) OR "
            "(updated_by_kind IN ('user', 'service') AND updated_by_name <> '')",
            name="ck_earthquakes_updated_by",
        ),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    ies_event_id = db.Column(db.BigInteger, nullable=False, unique=True)
    iesdata_id = db.Column(db.BigInteger, nullable=True)
    seiscomp_oid = db.Column(db.Text, nullable=True)
    is_automatic = db.Column(db.Boolean, nullable=False, server_default=db.false())
    origin_time = db.Column(db.DateTime(timezone=True), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    depth = db.Column(db.Numeric(7, 2), nullable=False)
    location_ge = db.Column(db.Text, nullable=False)
    location_en = db.Column(db.Text, nullable=False)
    magnitude_type = db.Column(db.Text, nullable=False)
    magnitude_value = db.Column(db.Numeric(4, 2), nullable=False)
    created_by_kind = db.Column(db.Text, nullable=True)
    created_by_name = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_by_kind = db.Column(db.Text, nullable=True)
    updated_by_name = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    felt_reports = db.relationship("FeltReport", back_populates="earthquake")
    outbox = db.relationship(
        "NotificationOutbox",
        back_populates="earthquake",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.ies_event_id,
            "iesdata_id": self.iesdata_id,
            "seiscomp_oid": self.seiscomp_oid,
            "is_automatic": self.is_automatic,
            "origin": {
                "time": self.origin_time.isoformat() if self.origin_time else None,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "depth": float(self.depth) if self.depth is not None else None,
                "location_ge": self.location_ge,
                "location_en": self.location_en,
            },
            "magnitude": {
                "type": self.magnitude_type,
                "value": float(self.magnitude_value) if self.magnitude_value is not None else None,
            },
            "created_by": (
                {"kind": self.created_by_kind, "name": self.created_by_name}
                if self.created_by_kind
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_by": (
                {"kind": self.updated_by_kind, "name": self.updated_by_name}
                if self.updated_by_kind
                else None
            ),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Earthquake id={self.id} ies_event_id={self.ies_event_id}>"
