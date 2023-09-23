from your_app.extensions import db
from datetime import datetime

class VEHICLE_INTERVAL_COUNTS(db.Model):
    #__tablename__ = "VEHICLE_INTERVAL_COUNTS"
    interval_id=db.Column(db.Integer, primary_key=True)
    cam_id = db.Column(db.Integer, primary_key=True)
    interval_datetime = db.Column(db.DATETIME(timezone=True))
    lkp_vehicle_type = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, primary_key=True) 
    
    def labels_serializer(self):
        date_format = '%Y-%m-%d %H:%M:%S'
        #return str(self.interval_datetime) 
        return datetime.strftime(self.interval_datetime , date_format)



    
    def dataset_serializer(self):
        return self.count
        
