from resources.extensions import db

class Incidents(db.Model):
    #__tablename__ = "incidents"
    id=db.Column(db.Integer, primary_key=True)
    camera_name = db.Column(db.String(20))
    videodatetime = db.Column(db.DATETIME(timezone=True))
    name= db.Column(db.String(50))
    type= db.Column(db.String(50))
    video_path= db.Column(db.String(200))


    #pass
