from geoalchemy2 import Geometry
from sqlalchemy import Index

from app.extensions import db
from app.models.base import BaseModel


class FeltReport(db.Model, BaseModel):
    __tablename__ = "felt_reports"
    __table_args__ = (
        db.CheckConstraint(
            "intensity IN ('MILD', 'MODERATE', 'SEVERE')",
            name="ck_felt_reports_intensity",
        ),
        db.CheckConstraint("minutes_ago >= 0", name="ck_felt_reports_minutes_ago"),
        Index("felt_reports_device_idx", "device_id"),
        Index("felt_reports_earthquake_idx", "earthquake_id"),
        Index("felt_reports_felt_at_idx", "felt_at"),
        Index("felt_reports_location_idx", "location", postgresql_using="gist"),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Uuid, db.ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True)
    intensity = db.Column(db.Text, nullable=False)
    minutes_ago = db.Column(db.Integer, nullable=True)
    reported_at = db.Column(db.DateTime(timezone=True), nullable=False)
    felt_at = db.Column(db.DateTime(timezone=True), nullable=True)
    location = db.Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    earthquake_id = db.Column(
        db.BigInteger,
        db.ForeignKey("earthquakes.id", ondelete="SET NULL"),
        nullable=True,
    )
    language = db.Column(db.Text, nullable=True)
    platform = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    device = db.relationship("Device", back_populates="felt_reports")
    earthquake = db.relationship("Earthquake", back_populates="felt_reports")

    def _location_geojson(self):
        from app.utils.geo import location_geojson

        return location_geojson(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": str(self.device_id) if self.device_id else None,
            "intensity": self.intensity,
            "minutes_ago": self.minutes_ago,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "felt_at": self.felt_at.isoformat() if self.felt_at else None,
            "earthquake_id": self.earthquake_id,
            "location": self._location_geojson(),
            "language": self.language,
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<FeltReport id={self.id} intensity={self.intensity}>"
