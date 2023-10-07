from your_app.extensions import db
import flask_login
class User(flask_login.UserMixin,db.Model):
    #__tablename__ = "user"
    uid=db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20))
    password = db.Column(db.String(100))

    #pass
