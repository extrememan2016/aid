#!/usr/bin/env python3
import cv2
import get_video
### from AID.VideoStream.fps import FPS

import time

import numpy as np

import datetime

from flask import Flask, render_template, Response, request, redirect, url_for
from flask import flash, send_from_directory# ch_v0r90 (send_from_directory added)
from pprint import pprint
from flask import jsonify

import flask # ch_v0r96 (added by m.taheri)
import flask_login # ch_v0r96 (added by m.taheri)
from flask import session # ch_v0r96 (added by m.taheri)
from datetime import timedelta # ch_v0r96 (added by m.taheri)


import pymysql # ch_v0r96 (added by m.taheri)
pymysql.install_as_MySQLdb() # ch_v0r96 (added by m.taheri)
from flask_mysqldb import MySQL # ch_v0r96 (added by m.taheri)
from datetime import timedelta
from your_app.extensions import db
import re# ch_v0r85 (added)


### from your_app.man_calibration import man_calib
from your_app.least_squares import ls_fine_tune_parameters
### from your_app.calculateSpeeds import Speed_Calc


### from your_app.utils import add_remove_stopped_vehicle_2,  ROI_transparent  # ch_v0r90 (moved to AID_Loop)
### from your_app.utils import scale_function# , camera_calib    # ch_v0r90 ('camera_calib' moved to AID_Loop)
### from your_app.utils import getPrmLeast, getPrmDflt# , getPrmDfs_calib_1  # ch_v0r90 ('getPrmDfs_calib_1' moved to AID_Loop)
### from your_app.utils import angle_between_points, camera_stop #, line_to_vanish  # ch_v0r90 ('line_to_vanish' moved to AID_Loop)
### from your_app.utils import save_frame# , getPrmDfs_calib_2 # ch_v0r90 ('getPrmDfs_calib_2' moved to AID_Loop)
from your_app.utils import verify_url, read_from_db, write_to_db_cams, write_to_db_CAM_ID, write_to_db_any, read_from_db_all, check_for_1_week_period # ch_v0r89 (read_from_db_all, check_for_1_week_period added)
from your_app.utils import  write_to_db_roi, VP1_from_DB # ch_v0r90 (VP1_from_DB added)
from your_app.utils import make_classification_staff ###, reset_counter_and_speeds # ch_v0r91 ('make_classification_staff', 'reset_counter_and_speeds' added)

### from your_app.KeyClipWriter import KeyClipWriter # ch_v0r86 

### from your_app.utils import poitsROIstr_to_pointsROInp#, point_inside_ROI # ch_v0r88 (added)
from your_app.utils import get_lock   # ch_v0r88 (added)
### from your_app.utils import points_roi_To_mask  # ch_v0r92 (added)

### from your_app.utils import computeCameraCalibration  # ch_v0r87 added

### from Kalman_filter.detectors import Detectors
### from Kalman_filter.tracker import Tracker
import os, glob

import sys, traceback, importlib, threading # ch_v0r84 (added)
from  your_app.config import config# ch_v0r84 (added)
import redis # ch_v0r85 (added)
### from collections import deque # ch_v0r86 (added)

## from your_app.AID_Loop import AID_loop # ch_v0r89 (added)
from your_app import settings # ch_v0r89 (added)


from sqlalchemy import func,select

from your_app.models.camera import Camera
from your_app.models.vevhicle_interval_counts import VEHICLE_INTERVAL_COUNTS
from your_app.models.lkp_vehicle_type import LKP_VEHICLE_TYPE

#===============================  initializing calibration parameters =========

h_rsz, w_rsz = 480, 864; 
rsz_shape = (h_rsz, w_rsz)  # new size for the shown video
W, L = 0, 0
swing_angle, focal, h_camera, h_camera_real = 0,0,0, 0.00 
camera = video = fps =  None
save_frame_global = None # ch_v0r85
videoLoop = None  # ch_v0r84
VP1 = VP2 = VP3 = road_camera_staff = []
calib = h = w = 0
real_line_meseares = points_roi = []
kcw = [] # ch_v0r86 (added)


# define REDIS connection information for Redis
# Replaces with your configuration information



r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB) # ch_v0r89 (added)


#================= Initializing flask app =====================================
app = Flask(__name__)
app.secret_key = b'_5#y1L"F4Q8z\n\xec]/'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=5)


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'raspberry'
app.config['MYSQL_DB'] = 'pythonprogramming'



mysql = MySQL(app)


app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:raspberry@localhost/pythonprogramming"

db.init_app(app)

#================= Initializing Login manager ===================================== # ch_v0r96 (added by m.taheri)

login_manager = flask_login.LoginManager()


login_manager.init_app(app)

# Our mock database.
# user = {'foo@bar.tld': {'password': 'secret'}}



#================= how to load a user from a Flask request and from its session ===================================== # ch_v0r96 (added by m.taheri)





class User(flask_login.UserMixin,db.Model):
    #__tablename__ = "user"
    uid = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    username = db.Column(db.String(20))
    password = db.Column(db.String(100))
    #pass



@login_manager.user_loader
def user_loader(username):
    
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
    user_data = cursor.fetchone()
    if user_data:
        # create a User object from the database data
        user=User()
        user.id=user_data[0]
        user.username=user_data[1]
        user.password=user_data[2]
        #return User(user_data[0], user_data[1], user_data[2])
        return user
    else:
        return None


@login_manager.request_loader
def request_loader(request):
    # get the authorization header from the request
    auth_header = request.headers.get('Authorization')
    
    # check if the header is valid and contains a token
    if auth_header and auth_header.startswith('Bearer '):
        # get the token from the header
        token = auth_header.split()[1]
        
        # verify the token and get the user data
        user_data = verify_token(token)
        
        if user_data:
            # create a User object from the user data
            user=User()
            user.id=user_data[0]
            user.username=user_data[1]
            user.password=user_data[2]
            return user
            #return User(user_data[0], user_data[1], user_data[2])
            #return User(user_data['uid'], user_data['username'], user_data['password'])
    
    # return None if no valid header or token found
    return None


@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=10)
    session.modified = True

#================= Initializing Login/Logout Routes ===================================== # ch_v0r96 (added by m.taheri)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return render_template('login.html')



    username = flask.request.form['username']
    password = flask.request.form['password']

    #cursor = mysql.connection.cursor()
    #cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
    #cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s', (username, password,))
    #account = cursor.fetchone()
    
    account =   User.query.filter_by(username=username).first()

    #if account:
    if account.password == password:
    
        user = User()
        user.id = username
        flask_login.login_user(user)
        session['username'] = username
        return flask.redirect(flask.url_for('protected'))
    else:
        flash("The username or password is incorrect", "warning")
    return render_template('login.html')


@app.route('/protected')
@flask_login.login_required
def protected():
    #return 'Logged in as: ' + flask_login.current_user.username
    if flask_login.current_user.username =='user':
        next = url_for('event')
    else:
        next = url_for('home')
    return render_template('landing.html',next = next)


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('logout.html')

@login_manager.unauthorized_handler
def unauthorized_handler():
    #return 'Unauthorized', 401
    
    if(request.path == '/'):
        return redirect(url_for('login'))
    else:
        return render_template('401.html')

#--------------- # ch_v0r90 (display video) ---------------------------------------
app.config['UPLOAD_FOLDER'] = 'your_app/output'
@app.route('/send_file/<filename>')
@flask_login.login_required
def send_file(filename):
    print('filename -------------------> ', filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
# use decorators to link the function to a url

@app.route('/', methods=['GET', 'POST'])
@flask_login.login_required
def home():
    if flask_login.current_user.username =='user':
        return redirect(url_for('event'))

    ID = "1" # r.get("ID") # ch_v0r91 added
    #row_cam = list(read_from_db("CAM_"+ID)) # ch_v0r96 (commented by m.taheri)
    allcams = Camera.query.filter_by(did=ID).first() # ch_v0r96 (added by m.taheri)
    del ID
    #row = list(read_from_db('CAMS_VALID')) # ch_v0r96 (commented by m.taheri)
    validcams = Camera.query.with_entities(Camera.did,Camera.url_cam,Camera.isenable,Camera.isvalid,Camera.pingok).all()
    
    #pprint(validcams)
    # if request from html
    if request.method == "POST":
        # verify the IP cam URL
        cam_remove_val = 'off'
        cam_en_val_temp = ''
        change_ind = 0
        verify_indx = -1
        submit = 0
        IP_add = key_url = ''
        cam_num = Camera.query.count()
        vid_dirname = 'static/videos/' # ch_v0r87 (added)
       
        if str(request.form.getlist('actions')[0]) == 'submit':#if request.form.post['actions']# submit button clicked else calib button clicked
            submit = 1
        elif str(request.form.getlist('actions')[0]) == 'calib': # ch_v0r87 (added)
            submit = 2 # ch_v0r87 (added)
        elif str(request.form.getlist('actions')[0]) == 'analytic':# ch_v0r87 (added)
            submit = 3 # ch_v0r87 (added)

       
        for key in request.form:
            for cam in validcams:
                if key.startswith(str(cam.did)+'_'):
                    ID = str(cam.did) 
                    """ ind_row = i+(i-1)*2
                    cam_en_val = row[ind_row]
                    cam_valid_val = row[ind_row+1] """

                    selectedcam=Camera.query.filter_by(did=cam.did).first()


                    cam_en_val = selectedcam.isenable
                    cam_valid_val = selectedcam.isvalid


                    if key.endswith("_URL"):
                        key_url = request.form.get(str(key),"")
                    elif key.endswith("_en"):
                        cam_en_val_temp = request.form.get(str(key),"")                    
                    elif key.endswith("_rm"):
                        cam_remove_val = request.form.get(str(key),"")
                    break
            
        if submit == 1:

            try:
                # If Cam Enable is 'ON'
                if cam_en_val_temp == 'on':
                    if cam_en_val == 0:
                        cam_en_val = 1
                        change_ind = 1
                else: 
                    if cam_en_val == 1:
                        cam_en_val = 0
                        change_ind = 1
            except:
                flash(u'Error occured. Please try again', 'danger') # Categories: success (green), info (blue), warning (yellow), danger (red)

            # If url is not empty --> check for url validity 
            if key_url != '':
                verify_indx, isfile = verify_url(key_url, 'Cam_'+ID)
                if verify_indx == 1:
                    if isfile == 1: 
                        IP_add = '127.0.0.1'
                        key_url = vid_dirname+key_url # ch_v0r87 ('key_url' --> 'vid_dirname+key_url')
                    else:
                        IP_add = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', key_url).group()

            # If remove checkbox is checked
            if cam_remove_val == 'on':
                cam_valid_val = 0
                change_ind = 1
                #write_to_db_CAM_ID(str(ID), '', '',0, '')  # ch_v0r89 commented
                
                db.session.delete(Camera.query.filter_by(did=ID).first()) # ch_v0r96 (added by m.taheri)
                db.session.commit()

                #cam_dict={'IP_cam': '', 'url_cam': '','cam_FPS': 0 }  # ch_v0r89 (added) # ch_v0r96 (commented by m.taheri)
                # write_to_db_any("CAM_"+str(ID), cam_dict) # ch_v0r96 (commented by m.taheri)

                flash(u'You have successfully removed the camera setting', 'success') # Categories: success (green), info (blue), warning (yellow), danger (red)
            elif verify_indx == 0: # Invalid URL
                flash(u'Invalid URL provided', 'warning') # Categories: success (green), info (blue), warning (yellow), danger (red)
            elif verify_indx == 1: # Valid URL --> save it
                flash(u'Valid URL provided', 'success')
                change_ind = 1
                cam_en_val = 1
                cam_valid_val = 1
                # write_to_db_CAM_ID(str(ID), '', '',0, '')  # ch_v0r96 (commented by m.taheri)
                
                cam_dict={'cam_FPS': 0 } # ch_v0r96 (added by m.taheri)
                write_to_db_any(ID,cam_dict) # ch_v0r96 (added by m.taheri)

            # save the changes
            if change_ind == 1:
                cam_en_str = "cam_"+str(ID)+"_enable"  # not using in ch_v0r96 (added by m.taheri)
                cam_valid_str = "cam_"+str(ID)+"_valid" # not using in ch_v0r96 (added by m.taheri)

                cam_dict={'isenable': cam_en_val , 'isvalid': cam_valid_val,'url_cam': key_url, 'IP_cam':IP_add } # ch_v0r96 (added by m.taheri)

                write_to_db_any(ID,cam_dict) # ch_v0r96 (added by m.taheri)
                
                #write_to_db_cams(cam_en_str,cam_en_val,cam_valid_str,cam_valid_val,key_url, IP_add, str(ID)) # ch_v0r96 (commented by m.taheri)
                #row = list(read_from_db('CAMS_VALID')) # ch_v0r96 (commented by m.taheri)
                validcams = Camera.query.with_entities(Camera.did,Camera.url_cam,Camera.isenable,Camera.isvalid,Camera.pingok).all()  # ch_v0r96 (added by m.taheri)
            return render_template('index.html',validcams=validcams, allcams=allcams )  # ch_v0r91 (row --> row_val and  'row=row_cam' added)
        elif  submit == 2:
            #session['ID'] = str(ID)
            # r.set("ID", str(ID))
            return redirect(url_for('roi',camid=request.form.getlist('camid')[0]))
        elif  submit == 3: # ch_v0r87 (added)
            # r.set("ID", str(ID)) # ch_v0r87 (added)
            return redirect(url_for('analytic',camid=request.form.getlist('camid')[0])) # ch_v0r87 (added)
            
    else:
        return render_template('index.html',validcams=validcams, allcams=allcams )  # ch_v0r91 (row --> row_val and  'row=row_cam' added)
    
#============================= analytic =======================================
@app.route('/analytic',  methods=['GET', 'POST'])
@flask_login.login_required
def analytic():
    if flask_login.current_user.username =='user':
        return redirect(url_for('event'))
        # ---------------------- ch_v0r87 (POST method added)
    ID = request.args.get('camid')
    camid = ID
    if request.method == 'POST':
        
        if  "draw_smoke" in request.form:
            pprint(request.form)
            try:
                
                camid = request.form['camid']
                smoke_ROI_points = request.form['points_smoke_x'] + ';' + request.form['points_smoke_y'] +';'

                cam_dict={'smoke_ROI_points': smoke_ROI_points }
                write_to_db_any(camid,cam_dict)
                flash(u'Smoke Region Setting Applied!', 'success')
                #return redirect(url_for('analytic')) 
            except Exception as e:
                print("ERROR" + str(e))
                flash(u'Error! Cant Apply Smoke ROI Setting!', 'warning ')
                #return redirect(url_for('roi',camid=request.form.getlist('camid')[0]))




        if "my_range" in request.form: # Detection Form
            detection_condition = ["Very Low <br /> (Very low light condition or very blurry image)", "Low <br />(Low light condition or blurry image)", "Default <br />(Normal light with normal image quality)", "High <br />(High light condition and sharp image)"];
            my_range = request.form['my_range']
            for (i, text) in enumerate(detection_condition):
                if text == my_range:
                    break
            try:
                if str(request.form['draw_3d']) == 'on':
                    draw_3d = 1
            except:
                draw_3d = 0


            cam_dict={'detection_type': i, 'draw_3d': draw_3d }
            #write_to_db_any("CAM_"+ID, cam_dict)
            write_to_db_any(camid,cam_dict)
            
        elif "stop_vehicle_th" in request.form: # Stop vehicle Form
            try:
                
                camid = request.form['camid']
                stop_vehicle_th = int(request.form['stop_vehicle_th'])
                stop_vehicle_dur_th = int(request.form['stop_vehicle_dur_th'])

                ################how to use points_stop_x and points_stop_y ????????????????

                try:
                    if str(request.form['disp_stop_roi']) == 'on': # display_roi_checkbox
                        disp_stop_roi = 1
                except Exception as e:
                    disp_stop_roi = 0
                    
                print("we do ::: "+request.form['points_stop_x'])    
                cam_dict={'stop_vehicle_th': stop_vehicle_th, 'stop_vehicle_dur_th': stop_vehicle_dur_th, 'disp_stop_roi': disp_stop_roi } # disp_stop_roi # ch_v0r89 (added)
                write_to_db_any(camid,cam_dict) # ch_v0r96 (added by m.taheri)

                flash(u'STOP Region Setting Applied!', 'success')
            except:
                flash(u'Error! Cant Apply STOP Setting!', 'warning ')


        elif 'slow_vehicle_th' in request.form: 
            try:
                camid = request.form['camid']

                slow_vehicle_th = int(request.form['slow_vehicle_th'])
                cam_dict={'slow_vehicle_th': slow_vehicle_th }

                write_to_db_any(camid,cam_dict)
                flash(u'Slow vehicle Threshold Setting Applied!', 'success')
            except Exception as e:
                flash(u'Error! Cant Apply Slow vehicle Threshold Setting!' + str(e) , 'warning ')

        elif 'roi_up_line' in request.form:
            try:
                if str(request.form['disp_dim']) == 'on': 
                    disp_dimensions = 1
            except:
                disp_dimensions = 0
            
            roi_up_line    = int(float(request.form['roi_up_line']))
            roi_low_line   = int(float(request.form['roi_low_line']))

            W_low_bike     = float(request.form['W_low_bike'])
            W_hi_bike      = float(request.form['W_hi_bike'])
            L_low_bike     = float(request.form['L_low_bike'])
            L_hi_bike      = float(request.form['L_hi_bike'])
            H_low_bike     = float(request.form['H_low_bike'])
            H_hi_bike      = float(request.form['H_hi_bike'])
            W_low_car      = W_hi_bike
            W_hi_car       = float(request.form['W_hi_car'])
            L_low_car      = float(request.form['L_low_car'])
            L_hi_car       = float(request.form['L_hi_car'])
            H_low_car      = float(request.form['H_low_car'])
            H_hi_car       = float(request.form['H_hi_car'])
            W_low_truck   = float(request.form['W_low_truck'])
            W_hi_truck    = float(request.form['W_hi_truck'])
            L_low_truck   = L_hi_car
            L_hi_truck    = float(request.form['L_hi_truck'])
            H_low_truck   = float(request.form['H_low_truck'])
            H_hi_truck    = float(request.form['H_hi_truck'])
            
            class_lines_roi= str(roi_up_line)+','+str(roi_low_line)+';'
            bike_dimensions= str(W_low_bike)+','+str(W_hi_bike)+';'+str(L_low_bike)+','+str(L_hi_bike)+';'+str(H_low_bike)+','+str(H_hi_bike)+';'
            car_dimensions= str(W_low_car)+','+str(W_hi_car)+';'+str(L_low_car)+','+str(L_hi_car)+';'+str(H_low_car)+','+str(H_hi_car)+';'
            truck_dimensions= str(W_low_truck)+','+str(W_hi_truck)+';'+str(L_low_truck)+','+str(L_hi_truck)+';'+str(H_low_truck)+','+str(H_hi_truck)+';'
            
            cam_dict={'class_lines_roi': class_lines_roi, 'bike_dimensions':bike_dimensions, 'car_dimensions':car_dimensions, 'truck_dimensions':truck_dimensions, 'disp_dimensions': disp_dimensions} # disp_dimensions # ch_v0r91 (added)
            #write_to_db_any("CAM_"+ID, cam_dict)
            write_to_db_any(camid,cam_dict)
    """ else:
        try:
            pprint(request.form)
            print(request.args.get(is_apply_smoke_success))
        except:

            print("emptty") """
           
    try:
        #row_cam = list(read_from_db("CAM_"+ID))
        cam = Camera.query.filter_by(did=ID).first()
        # ----------------- ch_v0r91 (added) -------------------------------
        classification_staff = make_classification_staff(cam) 
        counting_list = []
        for k in classification_staff.keys():
            counting_list +=list(classification_staff[k])
        counting_list[3] = 100 - counting_list[3]

        # detect_type_ind = 1
        # slow_vehicle_th = 40
        # stop_vehicle_th = 2
        # stop_vehicle_dur_th = 1
        detect_type_ind=cam.detection_type              #row_cam[16]
        slow_vehicle_th=cam.slow_vehicle_th              #row_cam[17]
        stop_vehicle_th=cam.stop_vehicle_th              #row_cam[18]
        stop_vehicle_dur_th=cam.stop_vehicle_dur_th      #row_cam[22]
        # --------------------   Notice: ROI should be returned to html ----------------------
        return render_template('analytic.html',h_rsz=h_rsz, w_rsz=w_rsz, detect_type_ind=detect_type_ind, slow_vehicle_th=slow_vehicle_th, stop_vehicle_th=stop_vehicle_th, stop_vehicle_dur_th=stop_vehicle_dur_th, row=cam, counting_list=counting_list )
    except Exception as e:
        print("ERROR IS: "+str(e))
        #flash(u'Invalid URL provided', 'warning')
        return redirect(url_for('roi',camid=ID))
        #return redirect(url_for('roi'))
    
#============================= info ======================================= #### ch_v0r96 (edited by m.taheri)
@app.route('/info')
@flask_login.login_required
def info():
    if flask_login.current_user.username =='user':
        return redirect(url_for('event'))

    try:
        ID = r.get("ID") # ch_v0r91 added
        row_cam = list(read_from_db("CAM_"+ID)) # ch_v0r91 added
        
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time()) #  ch_v0r92 (added)
        uptime2 = check_output(["uptime"])    
        
        return render_template('info.html', row=row_cam, setting_class = "active",
                uptime = str(uptime).split('.')[0], uptime2=uptime2)  # render a template # ch_v0r91 row added
    except:
        flash(u'Error occured. Please contact Admin', 'danger') # Categories: success (green), info (blue), warning (yellow), danger (red)
#============================= create new camera =======================================
@app.route('/createcam',methods=['POST'])
@flask_login.login_required
def createcam():
    if flask_login.current_user.username =='user':
        return redirect(url_for('event'))
    newcam = Camera()

    maxid = db.session.query(db.func.max(Camera.did)).scalar() or 0    
    for i in range(1,maxid+2):
        cam = Camera.query.filter_by(did=i).with_entities(Camera.did).first()
        if cam is None:
            newcam.did = i
            print("test "+str(newcam.did))
            break
    newcam.pingok = 1
    newcam.cam_VP1_X = 200 #619.24
    newcam.cam_VP1_y = 200 #-116.37

    newcam.cam_center_X = 640
    newcam.cam_center_Y = 360
    newcam.cam_swing = 2.85

    newcam.cam_focal = 873.57
    newcam.cam_height = 7.33



    newcam.detection_type= 0
    newcam.slow_vehicle_th = 40
    newcam.stop_vehicle_th = 2
    newcam.stop_vehicle_dur_th = 20

    newcam.class_lines_roi = "58,45;"
    newcam.bike_dimensions = "0.2,1.0;0.2,3.0;1.2,7.0;"
    newcam.car_dimensions = "1.0,3.0;1.5,6.2;0.8,3.4;"
    newcam.truck_dimensions = "1.7,3.2;6.2,18.0;3.0,5.0;"


    db.session.add(newcam)
    db.session.commit()
    print("we decied to create cam with id : "+str(newcam.did))


    items = []
    item = newcam.did
    items.append(item)
    return jsonify({'items': items})


    #return newcam.did
    #return redirect(url_for('home'))
#============================= remove camera =======================================
@app.route('/deletecam',methods=['POST'])
@flask_login.login_required
def deletecam():
    try:
        if flask_login.current_user.username =='user':
            return redirect(url_for('event'))

        if request.method == 'POST':
            camid = request.form['camid']

        cam = Camera.query.filter_by(did=camid).first()
        db.session.delete(cam)
        db.session.commit()

        return jsonify(success=True)
    except:
        return jsonify(error=True)
    #return redirect(url_for('home'))
#============================= event =======================================
@app.route('/event', methods=['GET', 'POST'])
@flask_login.login_required
def event():
    ID = "1"
    row_cam = list(read_from_db("CAM_"+ID))
    error=''
    Num_of_cams = 5 # int(r.get("Num_of_cams"))
    if request.method == "POST": # if the user postes a date filter
        # # ch_v0r91 added
        date_from = request.form['dateTimePick1'] # date_from cannot be empty because it is considered as required field.
        date_to   = request.form['dateTimePick2']
        print(date_from,date_to)
        
        check_week_ind = check_for_1_week_period(date_from,date_to, 60) # ch_v0r91 diff_days_duration added)
        if check_week_ind ==1:
            if date_to !='': # if date_to is not empty
                query = ("SELECT * FROM Incidents WHERE videodatetime >= %s AND videodatetime <= %s") 
                param = (date_from, date_to) 
            else: # if date_to is empty
                query = "SELECT * FROM Incidents WHERE videodatetime >= %s"
                param = (date_from,)
            table = list(read_from_db_all(query, param))
        else:
            error_mes = 'Report duration is Out of Range!'
            table = ''
            flash(error_mes, 'warning')
        print(table)
        return render_template('event.html',table=table, error=error,Range=range(1,Num_of_cams+1), row=row_cam)  # return for user post
    else:
        
        table = ''
        return render_template('event.html',table=table, error=error,Range=range(1,Num_of_cams+1), row=row_cam)  # first opening the page (# ch_v0r91 row added)
    
#============================= counting =======================================
@app.route('/counting')
@flask_login.login_required
def counting():
    if flask_login.current_user.username =='user':
        return redirect(url_for('event'))
    ID = "1"
    row_cam = list(read_from_db("CAM_"+ID)) # ch_v0r91 added
    return render_template('counting.html', row=row_cam)  # render a template # ch_v0r91 row added:

#============================= statistic  # ch_v0r91 added =======================================

#=============================below functions create list for the chart==========================#
def labels_serializer(objlist,timeperiod):
    #result = [item.labels_serializer() for item in objlist]

    #date_format = '%Y-%m-%d %H:%M:%S'
    #result = [item.interval_datetime.strftime(date_format) for item in objlist]

    date_format = '%Y-%m-%d'
    if timeperiod == "Hour":
        result = [item.Hour.strftime(date_format) for item in objlist]
    else:
        result = [item.Day.strftime(date_format) for item in objlist]

    return result

def dataset_serializer(objlist):
    #result = [item.dataset_serializer() for item in objlist]
    result = [int(item.vehicle_count) for item in objlist]
    return result

#==================================================================================================#


@app.route('/statistic', methods=['GET', 'POST'])
#@flask_login.login_required
def statistic():
    ID = "1"
    row_cam = list(read_from_db("CAM_"+ID)) # ch_v0r91 added
    #print('row_cam', row_cam)
    error_mes = table =''
    
    if request.method == "POST": # if the user postes a date filter
        # get the filled from_to dates
        date_from = request.form['dateTimePick1'] # date_from cannot be empty because it is considered as required field.
        date_to   = request.form['dateTimePick2']

        #print(date_from,date_to)
        
        check_week_ind = check_for_1_week_period(date_from,date_to, 7)
        if check_week_ind ==1:
            """ if date_to !='': # if date_to is not empty
                query = ("SELECT * FROM Incidents WHERE videodatetime >= %s AND videodatetime <= %s") 
                param = (date_from, date_to) 
            else: # if date_to is empty
                query = "SELECT * FROM Incidents WHERE videodatetime >= %s"
                param = (date_from,)
            table = list(read_from_db_all(query, param)) """
            
            carsdata=""
            motorbikesdata=""
            trucksdata=""
            totaldata=""
            charttype="line" #default type in line
            timeperiod="Day"
            timeperiodvar = func.Date(VEHICLE_INTERVAL_COUNTS.interval_datetime)


            carcheck=False
            motorcheck=False
            truckcheck=False
            totalcheck=False

            if 'Pie' in request.form.getlist('charttype'):
                charttype = "pie"                
            if 'hour' in request.form.getlist('timeperiod'):
                timeperiod = "Hour"
                timeperiodvar = func.Hour(VEHICLE_INTERVAL_COUNTS.interval_datetime)
            
            # Get the `students` table from the Metadata object

            carcount = truckcount= motorbikecount = totalcount = 0

            
            totaltable = db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count'),timeperiodvar.label(timeperiod)).filter(VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).group_by(timeperiod).all()
            
            totalcount = db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).scalar()
            
            totalselected = False
            if (request.form.getlist('Car') == [] and request.form.getlist('Truck') == [] and  request.form.getlist('Motorbike') == []) or (request.form.getlist('Car')  and request.form.getlist('Truck') and  request.form.getlist('Motorbike') ):
                totalselected = True
                print("total calculated")
                totaldata   =  dataset_serializer(totaltable)
            else:
                print("total not calculated")
                
            if request.form.getlist('Car') or totalselected:
                carstable = VEHICLE_INTERVAL_COUNTS.query.with_entities(timeperiodvar, func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count')).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="1",VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).group_by(timeperiod).all()
                carcount =  db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="1",VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).scalar()
                carsdata = dataset_serializer(carstable)
                carcheck=True
            if request.form.getlist('Truck') or totalselected:
                truckstable = VEHICLE_INTERVAL_COUNTS.query.with_entities(timeperiodvar, func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count')).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="3",VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).group_by(timeperiod).all()
                truckcount =  db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="3",VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).scalar()
                trucksdata = dataset_serializer(truckstable)
                truckcheck=True
            if request.form.getlist('Motorbike') or totalselected:
                Motorbikestable = VEHICLE_INTERVAL_COUNTS.query.with_entities(timeperiodvar, func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count')).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="2",VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).group_by(timeperiod).all()
                motorbikecount =  db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="2",VEHICLE_INTERVAL_COUNTS.interval_datetime.between(date_from,date_to)).scalar()
                motorbikesdata  =   dataset_serializer(Motorbikestable)
                motorcheck=True
            if request.form.getlist('total'):
                totalcheck=True
                



        
                

            

            labels=labels_serializer(totaltable,timeperiod)
            

            #return labels
            colors = ['#007bff','#28a745','#FFA500','#dc3545']; #blue, green, orange,red

            datasets = []
            if carsdata != "":
                datasets.append({
                    "label": "Cars",
                    "data": carsdata,
                    "backgroundColor": 'transparent',
                    "borderColor": colors[1],
                    "borderWidth": 4,
                    "pointBackgroundColor": colors[1]
                })
            if motorbikesdata != "":
                 datasets.append({
                    "label": "Motorbikes",
                    "data": motorbikesdata,
                    "backgroundColor": 'transparent',
                    "borderColor": colors[0],
                    "borderWidth": 4,
                    "pointBackgroundColor": colors[0]
                })
            if trucksdata != "":
                 datasets.append({
                    "label": "Truck",
                    "data": trucksdata,
                    "backgroundColor": 'transparent',
                    "borderColor": colors[2],
                    "borderWidth": 4,
                    "pointBackgroundColor": colors[2]
                })     
            if totaldata != "":
                datasets.append({
                    "label": "Total",
                    "data": totaldata,
                    "backgroundColor": 'transparent',
                    "borderColor": colors[3],
                    "borderWidth": 4,
                    "pointBackgroundColor": colors[3]
                })
            chartData = {
                "labels": labels,
                "datasets": datasets
                };


            

            return render_template('statistic.html', error_mes=error_mes,chartdata=chartData,
                                   charttype=charttype,timeperiod=timeperiod,
                                   carcheck=carcheck,truckcheck=truckcheck,motorcheck=motorcheck,totalcheck=totalcheck,
                                   date_from=date_from,date_to=date_to,
                                   carcount=carcount,motorbikecount=motorbikecount,truckcount=truckcount,totalcount=totalcount)
        else:
            error_mes = 'Report duration is Out of Range!'
            flash(error_mes, 'warning')     
        return render_template('statistic.html',table=table, error_mes=error_mes, row=row_cam)  # return for user post
    else:
        carsdata=""
        motorbikesdata=""
        trucksdata=""
        totaldata=""
        charttype="line" #default type in line
        timeperiod="Day"
        timeperiodvar = func.Date(VEHICLE_INTERVAL_COUNTS.interval_datetime)

        carcheck=False
        motorcheck=False
        truckcheck=False
        totalcheck=False

        if 'Pie' in request.form.getlist('charttype'):
            charttype = "pie"

        if 'hour' in request.form.getlist('timeperiod'):
            timeperiod = "Hour"
            timeperiodvar = func.Hour(VEHICLE_INTERVAL_COUNTS.interval_datetime)

        carcount = truckcount= motorbikecount = totalcount = 0

        
        totaltable = db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count'),func.DATE(VEHICLE_INTERVAL_COUNTS.interval_datetime).label(timeperiod)).group_by(timeperiod).all()
        
        totalcount = db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).scalar()
        
        totalselected = False
        if (request.form.getlist('Car') == [] and request.form.getlist('Truck') == [] and  request.form.getlist('Motorbike') == []) or (request.form.getlist('Car')  and request.form.getlist('Truck') and  request.form.getlist('Motorbike') ):
            totalselected = True
            print("total calculated")
            totaldata   =  dataset_serializer(totaltable)
        else:
            print("total not calculated")
            
        if request.form.getlist('Car') or totalselected:
            carstable = VEHICLE_INTERVAL_COUNTS.query.with_entities(timeperiodvar, func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count')).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="1").group_by(timeperiod).all()
            carcount =  db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="1").scalar()
            carsdata = dataset_serializer(carstable)
            carcheck=True
        if request.form.getlist('Truck') or totalselected:
            truckstable = VEHICLE_INTERVAL_COUNTS.query.with_entities(timeperiodvar, func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count')).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="3").group_by(timeperiod).all()
            truckcount =  db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="3").scalar()
            trucksdata = dataset_serializer(truckstable)
            truckcheck=True
        if request.form.getlist('Motorbike') or totalselected:
            Motorbikestable = VEHICLE_INTERVAL_COUNTS.query.with_entities(timeperiodvar, func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count).label('vehicle_count')).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="2").group_by(timeperiod).all()
            motorbikecount =  db.session.query(func.sum(VEHICLE_INTERVAL_COUNTS.vehicle_count)).filter(VEHICLE_INTERVAL_COUNTS.lkp_vehicle_type=="2").scalar()
            motorbikesdata  =   dataset_serializer(Motorbikestable)
            motorcheck=True
        if request.form.getlist('total'):
            totalcheck=True
            



        labels=labels_serializer(totaltable,timeperiod)
        

        #return labels
        colors = ['#007bff','#28a745','#FFA500','#dc3545']; #blue, green, orange,red

        
        chartData = {
            "labels": labels,
            "datasets": [{
                "label": "Motorbikes",
                "data": motorbikesdata,
                "backgroundColor": 'transparent',
                "borderColor": colors[0],
                "borderWidth": 4,
                "pointBackgroundColor": colors[0]
            },
            {
                "label": "Cars",
                "data": carsdata,
                "backgroundColor": 'transparent',
                "borderColor": colors[1],
                "borderWidth": 4,
                "pointBackgroundColor": colors[1]
            }, 
            {
                "label": "Truck",
                "data": trucksdata,
                "backgroundColor": 'transparent',
                "borderColor": colors[2],
                "borderWidth": 4,
                "pointBackgroundColor": colors[2]
            }, 
            {
                "label": "Total",
                "data": totaldata,
                "backgroundColor": 'transparent',
                "borderColor": colors[3],
                "borderWidth": 4,
                "pointBackgroundColor": colors[3]
            }
            ]     
            };

        return render_template('statistic.html', error_mes=error_mes,chartdata=chartData,
                               charttype=charttype,timeperiod=timeperiod,
                               carcheck=carcheck,truckcheck=truckcheck,motorcheck=motorcheck,totalcheck=totalcheck)
#============================= status =======================================
@app.route('/status')
@flask_login.login_required
def status():
    if flask_login.current_user.username =='user':
        return redirect(url_for('event'))
    return render_template('status.html')  # render a template



#================= Getting cordinates of rectangular calibration  ============= 
#================= pattern from user ==========================================
@app.route('/mouse_click1', methods = ['POST'])
@flask_login.login_required
def worker_2():
    return 'OK'
#================= # ch_v0r90 Apply fine-tuning VP1   ====== 
@app.route('/apply_VP1', methods = ['POST'])
@flask_login.login_required
def worker_vp1():
    try:
        print("starting")
        camid = request.form.getlist('camid')[0]
        vp1_x = request.form.getlist('vp1_x')[0]
        vp1_y = request.form.getlist('vp1_y')[0]

        cam_dict={'cam_VP1_X': vp1_x ,'cam_VP1_y': vp1_y } # ch_v0r96 (added by m.taheri)
        write_to_db_any(camid,cam_dict) # ch_v0r96 (added by m.taheri)
        print("SUCCESS")
        return jsonify(success=True)
    except Exception as E:
        print("ERROR: "+ str(E))
        return jsonify(error=True),500

#================= Getting Region of Intrest from user  ====== 
@app.route('/roi_mouse_click', methods = ['POST'])           #### ch_v0r96 (added by m.taheri)
#@timing
def worker_0():
    camid = request.form.getlist('camid')[0]
    points_x, points_y = '', ''
    points_x = request.form.getlist('points_x[]') # x-cordinates of rectangular calibration pattern
    points_y = request.form.getlist('points_y[]') # y-cordinates of rectangular calibration pattern
    #print(points_x,points_y)
    if points_x:
        points_x_db_str=''
        points_roi = np.zeros((len(points_x), 2), dtype=float) 
        for i in range(0,len(points_x)):
            points_roi[i,:] = ((int(points_x[i])  ,int(points_y[i])))
        # ---------------------- ch_v0r86  (points_roi write to DB)-----------------------------
            str_1=(int(points_roi[i,0])).__str__()+','+(int(points_roi[i,1])).__str__()
            if i==0:
                points_x_db_str = str_1+';'
            else:
                points_x_db_str = points_x_db_str+str_1+';'
        

        cam_dict={'mask_points': points_x_db_str } # ch_v0r96 (added by m.taheri)

        write_to_db_any(camid,cam_dict) # ch_v0r96 (added by m.taheri)
                
        #ID = str(r.get("ID")) 
        #write_to_db_roi(str(ID),points_x_db_str)
        # ---------------------- ch_v0r86  -----------------------------
    return 'OK'

#================= Getting Region of Intrest for road from user  ====== 
@app.route('/roiroad_mouse_click', methods = ['POST'])           #### ch_v0r96 (added by m.taheri)
#@timing
def worker_1():
    camid = request.form.getlist('camid')[0]
    points_x, points_y = '', ''
    points_x = request.form.getlist('points_x[]') # x-cordinates of rectangular calibration pattern
    points_y = request.form.getlist('points_y[]') # y-cordinates of rectangular calibration pattern
    #print(points_x,points_y)
    if points_x:
        points_x_db_str=''
        points_roi = np.zeros((len(points_x), 2), dtype=float) 
        for i in range(0,len(points_x)):
            points_roi[i,:] = ((int(points_x[i])  ,int(points_y[i])))
        # ---------------------- ch_v0r86  (points_roi write to DB)-----------------------------
            str_1=(int(points_roi[i,0])).__str__()+','+(int(points_roi[i,1])).__str__()
            if i==0:
                points_x_db_str = str_1+';'
            else:
                points_x_db_str = points_x_db_str+str_1+';'
        
        cam_dict={'road_points': points_x_db_str } # ch_v0r96 (added by m.taheri)

        write_to_db_any(camid,cam_dict) # ch_v0r96 (added by m.taheri)
                
        #ID = str(r.get("ID")) 
        #write_to_db_roi(str(ID),points_x_db_str)
        # ---------------------- ch_v0r86  -----------------------------
    return 'OK'

#================= Getting Region of Interest from user  ====== ch_v0r87 (module added)
""" @app.route('/SW_roi_mouse_click', methods = ['POST'])
@flask_login.login_required
def worker_SW():
    if request.method == 'POST':
        try:
            camid = request.form['camid']
            if request.form['key']=='smoke':

                smoke_ROI_points = request.form['points_smoke_x'] + ';' + request.form['points_smoke_y'] +';'
                cam_dict={'smoke_ROI_points': smoke_ROI_points }
                write_to_db_any(camid,cam_dict)

            #return redirect(url_for('analytic')) 
        except Exception as e:
            print("ERROR" + str(e))
            #return redirect(url_for('roi',camid=request.form.getlist('camid')[0]))

    return 'OK' """

#================= Getting real measurements of some known length on the road == 
#================= from user to improve camera calibration ====================
@app.route('/mouse_click2', methods = ['POST'])


#================ calibration step 1 (Getting real measurements of rectangular
# =============== patern length and width, and camera height from user)=======
@app.route('/vp1_view' , methods=['GET', 'POST'])    # you can also remove GET Stuff and use like this ID = request.args.get('camid')
@flask_login.login_required
def vp1_view():
    #ID = r.get("ID")
    ID = request.args.get('camid')

    h_rsz, w_rsz= (480, 864) # ----> you can get this from DB (new records)
    if request.method == 'GET':        
        try:
            row_cam = Camera.query.filter_by(did=ID).first()
            return render_template('vp1_view.html',h_rsz=h_rsz, w_rsz=w_rsz,vp1_x=row_cam.cam_VP1_X,vp1_y=row_cam.cam_VP1_y, row=row_cam, camid=ID)   # ch_v0r91 row added)
        except:
            #return redirect(url_for('roi'))
            redirect(url_for('roi',camid=ID))
    elif request.method == 'POST':
        To_VP = 1
        option = request.form['options']
        if option == 'From_VP':
            To_VP = 0

        # write to DB "To_VP" 
        

        # write_to_db_any -> "To_VP"

        if request.form['action'] == "Change it":
            return redirect(url_for('vp1',camid = ID))            
        elif request.form['action'] == "It's OK. Next Step...":
            return redirect(url_for('calibration_step_1',camid = ID))

#================ calibration step 1 (Getting real mesurements of rectangular
# =============== patern length and width, and camera heigth from user)=======
@app.route('/calibration_step_1' , methods=['GET', 'POST'])
@flask_login.login_required
def calibration_step_1():    
    
    W, L = 0, 0 # reset the calibration pattern real measurements
    
    if request.method == 'POST':
        ID =  request.args.get('camid')
        W = request.form['int_W']
        L = request.form['int_L']
        h_camera_tmp = request.form['Cam_h'] # Getting camera height is optional for user
        if h_camera_tmp != '': 
            h_camera_real = float(h_camera_tmp)      #  ch_v0r96 (changed by m.taheri(change from np.float.float))
        
        if W != '' and L != '':
            
            #   W, L, h_camera_real are needed for "man_calib" and "ls_fine_tune_parameters" --> how to save them????
            return redirect(url_for('calibration_step_2',camid = ID, W = W , L = L, h_camera_real = h_camera_real ))
    

    else:        
        try:            
            #------------  ch_v0r85 -----------------------
            #ID = r.get("ID")
            ID =  request.args.get('camid')
            #   Get h_rsz, w_rsz,vp1_x, vp1_y  -> from DB
            
            row_cam = Camera.query.filter_by(did=ID).first()


            return render_template('calibration_step_1.html',h_rsz=h_rsz, w_rsz=w_rsz,vp1_x=row_cam.cam_VP1_X,vp1_y=row_cam.cam_VP1_y, row=row_cam,camid = ID)   # ch_v0r91 row added)
        except:
            return redirect(url_for('roi'))

#==============================================================
@app.route('/calibration_step_2', methods=['GET','POST'])
@flask_login.login_required
def calibration_step_2():
   
    if request.method == 'POST':
        camid = request.form.getlist('camid')[0]
        print("Error is : "+str(request.form.getlist('lines_points_x')[0]));
        lines_points_x = request.form.getlist('lines_points_x')[0]
        lines_points_y = request.form.getlist('lines_points_y')[0]
        member = int(request.form['member'])
        for i in range(0, member):
            i +=1 
            L = float(request.form["L{0}".format(i)])
            real_line_meseares.extend( [L] ) # seve this somewhere to use it in "mouse_click2"


        # mouse_click2 must run here
        print("before error")
        worker_3(camid,lines_points_x,lines_points_y,real_line_meseares)
        print("after error")
        try:
            points = points_roi[0]
            return redirect(url_for('analytic')) 
        except:
            return redirect(url_for('roi',camid=request.form.getlist('camid')[0]))

    else:
        try:
            ID = request.args.get('camid')
            w = request.args.get('W')
            l = request.args.get('L')
            h_camera_real = request.args.get('h_camera_real')

            file_name = "file_name"
            row_cam = Camera.query.filter_by(did=ID).first()
            return render_template('calibration_step_2.html',h_rsz=h_rsz, w_rsz=w_rsz,vp1_x=row_cam.cam_VP1_X,vp1_y=row_cam.cam_VP1_y, file_name=file_name, row=row_cam, camid = ID)   # ch_v0r91 row added)
        except Exception as e:
            print("ERROR IS : "+ str(e))
            return redirect(url_for('roi',camid=request.args.get('camid')))
  
def worker_3(camid,lines_points_x,lines_points_y,real_line_meseares):
    # get real_line_meseares you were saved
    if real_line_meseares != []: ## ch_v0r84
        #ID = r.get("ID") # ch_v0r85
        ID = camid
        row_cam = Camera.query.filter_by(did=ID).first()

		# get focal, h_camera, VP1 and center from DB
		# centre = int(row[9]), int(row[10]) or centre = w//2,h//2
        focal = row_cam.cam_focal
        h_camera = row_cam.cam_height
        centre = int(row_cam.cam_center_X), int(row_cam.cam_center_Y)
        VP1 = int(row_cam.cam_VP1_X), int(row_cam.cam_VP1_y)

        swing_angle = row_cam.cam_swing

        if lines_points_x:
            line_points = np.zeros((len(lines_points_x), 2), dtype=float)

            x0 = np.array([focal,  h_camera])
            # Least square optimization to fine-tuning camera calibration partameters
            road_camera_staff = ls_fine_tune_parameters(centre, VP1, real_line_meseares, line_points, swing_angle, x0, h_camera, 0.0, 1)  # ch_v0r90 (vp1 --> orig_VP1)
            
            
            cam_dict={'cam_focal': focal_length , 'cam_height': cam_height,'cam_swing': swing, 'cam_tilt':tilt *( 180 / np.pi), 'cam_center_X':original_centre[0], 'cam_center_Y': original_centre[1] , 'cam_VP2_X' : round(original_vp2[0],3)  , 'cam_VP2_y' :round(original_vp2[1],2)} # ch_v0r96 (added by m.taheri)
            write_to_db_any(ID,cam_dict) # ch_v0r96 (added by m.taheri)

            print("Success")

           
    else: # ch_v0r84
        print('\n'*2)
        print('=======  Please enter the real line length in meter =======')
        print('\n'*2)
    return 'OK'
#===========================================================
@app.route('/vp1'  , methods=['GET', 'POST'])
@flask_login.login_required
def vp1():

    try:
        #ID = r.get("ID")
        ID =  request.args.get('camid')

        #row_cam = list(read_from_db("CAM_"+ID)) # ch_v0r91 added
        row_cam = Camera.query.filter_by(did=ID).first()

        # get VP1 from DB
        h_rsz, w_rsz= (480, 864) # ----> you can get this from DB (new records)


        return render_template('vp1.html',h_rsz=h_rsz, w_rsz=w_rsz, row=row_cam, camid=ID)   # ch_v0r91 row added)
    except:
        return redirect(url_for('roi'))

    

@app.before_request
def before_request():
    CAMS = Camera.query.filter_by(isenable=1).all()
    request.onlinecams = CAMS

#===========================================================
@app.route('/roi/<camid>',methods = ['POST','GET'])
@flask_login.login_required
def roi(camid):
    print("camid is "+camid)
    return render_template('RoI.html',h_rsz=h_rsz, w_rsz=w_rsz, camid=camid)   # ch_v0r91 row added) # ch_v0r96 (changed by m.taheri)

#===========================================================
@app.route('/roiroad/<camid>',methods = ['POST','GET'])
@flask_login.login_required
def roiroad(camid):
    return render_template('RoIroad.html',h_rsz=h_rsz, w_rsz=w_rsz, camid=camid)   # ch_v0r91 row added) # ch_v0r96 (changed by m.taheri)

#=========================================================== 
@app.errorhandler(404)
def page_not_found(e):
    print( '404 page not found'+ str(request.path)) # ch_v0r90 (py3 change)
    ID = "1"
    row_cam = list(read_from_db("CAM_"+ID)) # ch_v0r91 added
    return render_template('404.html', row=row_cam), 404 

#========================================================================
def calib_step_init(calib, framePluginInstance, fps_capture, CAM_ID):
    """Video streaming generator function."""
    print("some initial condition")
    return "OK"
  
#========================================================================
def main():
    app.run(debug=False,host='0.0.0.0', threaded=True)
    
if __name__ == '__main__':
    main()
    

@app.route('/video_feed',methods = ['POST','GET'])      #Video streaming route. Put this in the src attribute of an img tag
@flask_login.login_required
def video_feed():   
    camid=request.args.get('camid')
    print("it is:"+camid)
    return Response(get_video.videoLoop(camid), mimetype='multipart/x-mixed-replace; boundary=frame')
