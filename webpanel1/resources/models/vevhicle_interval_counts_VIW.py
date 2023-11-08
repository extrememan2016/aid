from resources.extensions import db
from datetime import datetime

class CAR_DAILY_COUNT_VIW(db.Model):
    #__tablename__ = "car_daily_count_viw"
    cam_id = db.Column(db.Integer)
    moment=db.Column(db.DATETIME(timezone=True), primary_key=True)
    vehicle_count = db.Column(db.Integer)
    

class MOTORBIKE_DAILY_COUNT_VIW(db.Model):
    #__tablename__ = "motorbike_daily_count_viw"
    cam_id = db.Column(db.Integer)
    moment=db.Column(db.DATETIME(timezone=True), primary_key=True)
    vehicle_count = db.Column(db.Integer)


class TRUCK_DAILY_COUNT_VIW(db.Model):
    #__tablename__ = "truck_daily_count_viw"
    cam_id = db.Column(db.Integer)
    moment=db.Column(db.DATETIME(timezone=True), primary_key=True)
    vehicle_count = db.Column(db.Integer)
    

class CAR_HOURLY_COUNT_VIW(db.Model):
    #__tablename__ = "car_daily_count_viw"
    cam_id = db.Column(db.Integer)
    moment=db.Column(db.DATETIME(timezone=True), primary_key=True)
    vehicle_count = db.Column(db.Integer)
    

class MOTORBIKE_HOURLY_COUNT_VIW(db.Model):
    #__tablename__ = "motorbike_daily_count_viw"
    cam_id = db.Column(db.Integer)
    moment =db.Column(db.DATETIME(timezone=True), primary_key=True)
    vehicle_count = db.Column(db.Integer)


class TRUCK_HOURLY_COUNT_VIW(db.Model):
    #__tablename__ = "truck_daily_count_viw"
    cam_id = db.Column(db.Integer)
    moment =db.Column(db.DATETIME(timezone=True), primary_key=True)
    vehicle_count = db.Column(db.Integer)
    
    

