from your_app.extensions import db
from datetime import datetime

class VEHICLE_INTERVAL_COUNTS(db.Model):
    #__tablename__ = "VEHICLE_INTERVAL_COUNTS"
    interval_id=db.Column(db.Integer, primary_key=True)
    cam_id = db.Column(db.Integer)
    interval_datetime = db.Column(db.DATETIME(timezone=True))
    lkp_vehicle_type = db.Column(db.Integer)
    vehicle_count = db.Column(db.Integer) 