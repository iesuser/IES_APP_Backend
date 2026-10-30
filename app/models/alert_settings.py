from geoalchemy2 import Geometry
from sqlalchemy import Index

from app.extensions import db
from app.models.base import BaseModel


class AlertSettings(db.Model, BaseModel):
    __tablename__ = "alert_settings"
    __table_args__ = (
        db.CheckConstraint(
            "area_source IN ('custom', 'circle')",
            name="ck_alert_settings_area_source",
        ),
        Index("alert_settings_area_idx", "area", postgresql_using="gist"),
    )

    device_id = db.Column(
        db.Uuid,
        db.ForeignKey("devices.device_id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled = db.Column(db.Boolean, nullable=False, server_default=db.true())
    min_magnitude = db.Column(db.Numeric(3, 1), nullable=False, server_default="3.0")
    area = db.Column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    area_source = db.Column(db.Text, nullable=False, server_default=db.text("'custom'"))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    device = db.relationship("Device", back_populates="alert_settings")

    def to_dict(self):
        from app.utils.geo import area_geojson

        return {
            "device_id": str(self.device_id),
            "enabled": self.enabled,
            "min_magnitude": float(self.min_magnitude) if self.min_magnitude is not None else None,
            "area_source": self.area_source,
            "area": area_geojson(self.device_id),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AlertSettings device_id={self.device_id} source={self.area_source}>"
