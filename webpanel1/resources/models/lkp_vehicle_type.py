from resources.extensions import db

class LKP_VEHICLE_TYPE(db.Model):
    #__tablename__ = "LKP_VEHICLE_TYPE"
    vehicle_id = db.Column(db.Integer)
    vehicle_type = db.Column(db.String(20), primary_key=True)
    
    