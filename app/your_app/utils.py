#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 11:20:57 2019

@author: pi
"""
import numpy as np
import cv2
import math, time, datetime, os, glob
import subprocess # ch_v0r90 (added)
from flask import url_for #ch_v0r90 (added by m.taheri)
#from imutils.object_detection import non_max_suppression # ch_v0r86 (commented)
import sys # ch_v0r90 (added)
if sys.version_info >= (3, 0): # ch_v0r90 (added to check python version)
    from .dbconnect import connection  # ch_v0r90 (py3 change dbconnect --> .dbconnect)
    from pathlib import Path # ch_v0r90 (added)
else:
    from dbconnect import connection

#import 
 # ch_v0r86 (added)
#
try:
    from  skimage.metrics import structural_similarity  as ssim # ch_v0r90 (will be added)
except:
    from skimage.measure import compare_ssim as ssim # ch_v0r86 (It will be removed from skimage.measure in version 0.18.)
#from imutils.object_detection import non_max_suppression as non_max_suppression_org
import socket # ch_v0r88 (added)
import sys # ch_v0r88 (added)
import threading  # ch_v0r90 (added)
from PIL import Image  # ch_v0r91 (added)
from skimage.feature import graycomatrix, graycoprops  # ch_v0r92 (added) ch_v0r90 (changed by m.taheri)
from collections import deque # ch_v0r92 (added)

from .extensions import db
from your_app.models.camera import Camera



def non_max_suppression(boxes, probs=None, overlapThresh=0.3): # ch_v0r86 (added)
    # if there are no boxes, return an empty list
    if len(boxes) == 0:
        return []
    
    # if the bounding boxes are integers, convert them to floats -- this
    # is important since we'll be doing a bunch of divisions
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")

    # initialize the list of picked indexes
    pick = []

    # grab the coordinates of the bounding boxes
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    # compute the area of the bounding boxes and grab the indexes to sort
    # (in the case that no probabilities are provided, simply sort on the
    # bottom-left y-coordinate)
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = y2

    # if probabilities are provided, sort on them instead
    if probs is not None:
        idxs = probs

    # sort the indexes
    idxs = np.argsort(idxs)

    # keep looping while some indexes still remain in the indexes list
    while len(idxs) > 0:
        # grab the last index in the indexes list and add the index value
        # to the list of picked indexes
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        # find the largest (x, y) coordinates for the start of the bounding
        # box and the smallest (x, y) coordinates for the end of the bounding
        # box
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        # compute the width and height of the bounding box
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        # compute the ratio of overlap
        overlap = (w * h) #/ area[idxs[:last]] # ch_v0r86 (new overlap)
        #Calculating IOUs for all bboxes except reference bbox
        ious = overlap/( area[i] + area[idxs[:last]]-overlap) # ch_v0r86 (intersection over unions (ious) added)
        # delete all indexes from the index list that have overlap greater
        # than the provided overlap threshold
        idxs = np.delete(idxs, np.concatenate(([last],
                                               np.where(ious > overlapThresh)[0]))) # ch_v0r86 (intersection over unions (ious) added)

    # return only the bounding boxes that were picked
    return boxes[pick].astype("int")

#------------------------- # ch_v0r86 (added) -------------------------------------------------
class contour_features():
    def __init__(self, x=64, y=1.0, z = 2):
        self.x = x
        self.y = y
        self.z = z
        
    def find_countours(self, mask):
        cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
        return cnts
    
    def find_moments(self, cnt):
        moments = cv2.moments(cnt)
        return moments
    
    def eccentricity_orientation (self, moments):
        float_formatter = lambda x: "%.2f" % x
        a1 = (moments['mu20']+moments['mu02'])/2
        a2 = np.sqrt(4*moments['mu11']**2+(moments['mu20']-moments['mu02'])**2)/2
    
        minor_axis = a1-a2
        major_axis = a1+a2
        
        eccentricity = np.float(float_formatter(np.sqrt(1-minor_axis/major_axis))) # circle --> 0 and line --> 1
        #orientation = np.float(float_formatter((180 / np.pi)*np.arctan2(2*moments['mu11'], (moments['mu20']-moments['mu02']))/2))
        return eccentricity#, orientation
    
    def convex_hull_solidity(self, cnt):
        # convex hull vertices
        float_formatter = lambda x: "%.2f" % x
        ConvexHull    = cv2.convexHull(cnt)
        ConvexArea    = cv2.contourArea(ConvexHull)
        # Solidity := Area/ConvexArea
        Area = cv2.contourArea(cnt)
        Solidity      = float_formatter(Area/ConvexArea)
        return ConvexHull, ConvexArea, float(Solidity)
    
    def rect_extent(self, cnt):
        rect = cv2.boundingRect(cnt); 
        x,y,w,h = rect;
        (cX, cY) = (w // 2, h // 2)
        rect_area = w*h
        Area = cv2.contourArea(cnt)
        extent = float(Area)/rect_area
        return x,y,w,h,cX, cY, rect_area, round(extent,2)
    
    def min_rect(self, cnt):
        rectang = cv2.minAreaRect(cnt)
        (cx,cy), (width, height), angle = rectang
        box = cv2.boxPoints(rectang)
        box = np.int0(box)
        # the `cv2.minAreaRect` function returns values in the
        # range [-90, 0); as the rectangle rotates clockwise the
        # returned angle trends to 0 -- in this special case we
        # need to add 90 degrees to the angle
        if angle < -45:
        	angle = -(90 + angle)
         
        # otherwise, just take the inverse of the angle to make
        # it positive
        else:
        	angle = -angle
        return round(angle,2)#, box
    
    def real_orientation(self, orientation, angle):
        real_ori = abs(angle)
        diff_ori = abs(abs(angle)-abs(orientation))
        if diff_ori < 15:
            if orientation > 0 and angle < 0:
                real_ori = 180 + angle
            elif orientation < 0 and angle > 0:
                real_ori = angle
        else:
            real_ori = 90 + angle
        return real_ori
    
    def point_inside_cnt(self, tuple_point, cnt):
        rect = cv2.boundingRect(cnt); 
        is_inside = rect[0] < tuple_point[0] < rect[0]+rect[2] and rect[1] < tuple_point[1] < rect[1]+rect[3]
        #is_inside_ind = cv2.pointPolygonTest(cnt,tuple_point,False)
        #is_inside = is_inside_ind>0 # >=0
        #In the function, third argument is measureDist. 
        #If it is True, it finds the signed distance. 
        #If False, it finds whether the point is inside or outside or on the contour (it returns +1, -1, 0 respectively).
        return is_inside
    
    def roi(self, x,y,w,h, mask):
        (startX, startY, endX, endY)  = ([x, y, x + w, y + h])
        roi = mask[startY:endY, startX:endX]
        return roi
    
    def draw_ellipse(self, roi, cnt):
        ellipse = cv2.fitEllipse(cnt)
        angle = round(ellipse[-1],2)
        cv2.ellipse(roi,ellipse,(255,0,255),2)
        return roi, angle
    
    def all_required_features(self, cnt):
        moments = self.find_moments(cnt)
        eccentricity = self.eccentricity_orientation(moments) # eccentricity = (0 --> circle)  and (1 --> line)
        ConvexHull, ConvexArea, Solidity = self.convex_hull_solidity(cnt) # solidity = cnt_Area/Convex_Area
        x,y,w,h,cX,cY,rect_area,extent = self.rect_extent(cnt) # extent = cnt_area/rect_area
        orientation = self.min_rect(cnt)
        return eccentricity, Solidity, extent, x,y,w,h,cX,cY, orientation
#------------------------- # ch_v0r86 (added) -------------------------------------------------

def record_kcw_file_handle(kcw, dfs, r):
    if kcw.recording:
        if dfs['isRecording'] ==0:
            dfs['isRecording'] = 1
        kcw.write() # ch_v0r86 (do recording)
    elif dfs['isRecording'] == 1:
        dfs['isRecording'] = 0
        rec_Thread = threading.Thread(target=video_convert_web_friendly, args=(dfs['record_staff'], r,)) # ch_v0r90 (Added)
        rec_Thread.start() # ch_v0r90 (Added)
        #video_convert_web_friendly(dfs['record_staff'], r) # ch_v0r90 (Added)
    return dfs
#------------------------- # ch_v0r86 (added) -------------------------------------------------
def recording_handle(kcw, Incident_detected, record_staff, frame,  rec_curr_fps, r):  # ch_v0r90 (rec_curr_fps, r added) *bug
    if record_staff['rec_type'] == 'valkka':
        record_status =int(r.lindex('All_Cams_record_status', record_staff['cam_ID']-1))
            
        if Incident_detected and record_status == 0: 
            record_staff['rec_consecFrames'] = 0
            timestamp = datetime.datetime.now()
            rec_name = "{}/{}_{}.avi".format(record_staff['output'],
                        'CAM_'+str(record_staff['cam_ID']), timestamp.strftime("%Y%m%d-%H%M%S"))
            r.lset('All_Cams_record_name', record_staff['cam_ID']-1, rec_name)
            r.lset('All_Cams_record_status', record_staff['cam_ID']-1,  1)

        elif not Incident_detected and record_status == 1: #
            record_staff['rec_consecFrames'] += 1
            if record_staff['rec_consecFrames'] > 3 * rec_curr_fps: # 'record_stopped after 3 seconds'
                r.lset('All_Cams_record_status', record_staff['cam_ID']-1,  0)
                rec_Thread = threading.Thread(target=video_convert_web_friendly, args=(record_staff, r,)) # ch_v0r90 (Added)
                rec_Thread.start() # ch_v0r90 (Added)
                #video_convert_web_friendly(record_staff, r) # ch_v0r90 (Added)
    else: #'cv2'
        
        record_status =  (kcw.recording == True) + 0 # ch_v0r90 (added)
        if Incident_detected and not record_status: # no Incident detected: # ch_v0r90 (kcw.recording --> record_status)
            record_staff['rec_consecFrames'] = 0
    
            # if we are not already recording, start recording
            
            timestamp = datetime.datetime.now()
            rec_name = "{}/{}_{}.avi".format(record_staff['output'], # ch_v0r90 (p --> rec_name)
                    'CAM_'+str(record_staff['cam_ID']), timestamp.strftime("%Y%m%d-%H%M%S")) # # ch_v0r90 ('CAM_'+str(record_staff['cam_ID']) added))
            r.lset('All_Cams_record_name', record_staff['cam_ID']-1, rec_name) # ch_v0r90 (rec_curr_fps, r added) 
            kcw.start(rec_name, cv2.VideoWriter_fourcc(*record_staff['rec_codec']), rec_curr_fps)# ch_v0r90 (record_staff['rec_fps'] --> rec_curr_fps , p --> rec_name) *bug
            
        # otherwise, no action has taken place in this frame, so
        # increment the number of consecutive frames that contain
        # no action
        elif not Incident_detected and record_status: # ch_v0r90 (kcw.recording --> record_status)
        #record_staff['rec_consecFrames'] < kcw.buf_multi_after_record * record_staff['rec_buffer_size'] + 1:# not Incident_detected:	
            record_staff['rec_consecFrames'] += 1
            # if we are recording and reached a threshold on consecutive
            # number of frames with no action, stop recording the clip
            if record_staff['rec_consecFrames'] > kcw.buf_multi_after_record * record_staff['rec_buffer_size']: 
                kcw.finish()
            
        # update the key frame clip buffer
        kcw.update(frame)
        '''
        # if we are recording and reached a threshold on consecutive
        # number of frames with no action, stop recording the clip
        if kcw.recording:
            if record_staff['rec_consecFrames'] == kcw.buf_multi_after_record * record_staff['rec_buffer_size']: 
                kcw.finish()
        '''
        record_staff['kcw'] = kcw ;  
    return record_staff, record_status # ch_v0r90 (record_status added)


  
    
#--------------------------------  # ch_v0r86 (intersection of two lines) ----------------------------------------------
def intersection(L1, L2):
    D  = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return np.array([int(x),int(y)])
    else:
        return False
#--------------------------------- # ch_v0r86 (Line from two points) ---------------------------------------------
def line(p1, p2):
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C

#============================ # ch_v0r85 (added) ============================================
def verify_url(url, cam_name):
    dirname = 'static/imgs/'
    #video path
    lin_vid_dirname = 'static/videos/'  # ch_v0r87 (added)
    win_vid_dirname = "\\app\\static\\videos\\"    # ch_v0r96 (added by m.taheri)

    if os.path.isfile(lin_vid_dirname+url): # ch_v0r88 (check if file)
        url = lin_vid_dirname+url
    elif os.path.isfile(os.getcwd()+ win_vid_dirname+url):
        url =  os.getcwd()+ win_vid_dirname+url

    cap = cv2.VideoCapture(url) # ch_v0r88 ('vid_dirname+url' --> 'url')   
    count = 0

    while(count< 1):
        ret, frame = cap.read()        
        if not ret:
            print('url is Not OK')
            count += 1
            cap.release()
            cv2.destroyAllWindows()
            return 0,0
        else:
            print('url is OK')
            #The received "frame" will be saved. Or you can manipulate "frame" as per your needs.
            name = cam_name+".jpg"
            cv2.resize(frame,(864, 480))
            cv2.imwrite(os.path.join(dirname,name), frame)
            count += 1
            cap.release()
            cv2.destroyAllWindows()
            if os.path.isfile(url): # ch_v0r88 ('vid_dirname+url' --> 'url')  
                return 1,1
            else:
                return 1,0
#------------------------- # ch_v0r85 (added)  --------------------------------------------------# 
# read from DB
#---------------------------------------------------------------------------# 
def read_from_db(device): # ch_v0r85 (added)
    row = ''
    c, conn = connection()
    query = ("SELECT * FROM " + device+" WHERE did = 1")
    data = c.execute(query)        
    if int(data) > 0:
        row = c.fetchone()        
        conn.commit()
        c.close()
        conn.close()
        #gc.collect()
        return row
#------------------------- # ch_v0r85 (added)  --------------------------------------------------# 
# write to DB
#---------------------------------------------------------------------------# 

def write_to_db_cams(cam_en_str,cam_en_val,cam_valid_str,cam_valid_val, key_url, IP_add, ID):
    """ c, conn = connection() # ch_v0r96 (commented by m.taheri)
    c.execute("UPDATE CAMS_VALID SET " +cam_en_str+"=%s,  " +cam_valid_str+"=%s WHERE did=%s;", (cam_en_val,cam_valid_val, 1))
    if IP_add != '':
        c.execute("UPDATE CAM_"+ID+" SET  url_cam=%s, IP_cam=%s WHERE did=%s;", (key_url, IP_add, 1)) 
    conn.commit()            
    c.close()
    conn.close()  """


    selectedcam = Camera.query.filter_by(did=ID).first() # ch_v0r96 (added by m.taheri)
    if selectedcam is not None:
        selectedcam.isenable = cam_en_val
        selectedcam.isvalid =cam_valid_val
        if IP_add != '':
            selectedcam.url_cam = key_url
            selectedcam.IP_cam =IP_add

        db.session.commit() # ch_v0r96 (added by m.taheri)
    # create the application object
#------------------------- # ch_v0r85 (added)  --------------------------------------------------# 
# write to DB VP1
#---------------------------------------------------------------------------# 
def write_to_db_CAM_ID(ID, VP1, road_camera_staff, video_FPS, To_VP):
    
    selectedcam = Camera.query.filter_by(did=ID).first() # ch_v0r96 (addedl by m.taheri)

    # c, conn = connection()  # ch_v0r96 (commented by m.taheri)
    if road_camera_staff == '' and video_FPS == '' and To_VP == '':
        print('Yaah ----------------- VP1 -----------------------> ', VP1)
        #c.execute("UPDATE CAM_"+ID+" SET cam_VP1_X=%s, cam_VP1_y=%s WHERE did=%s;", (VP1[0], VP1[1] , 1))
        selectedcam.cam_VP1_X = VP1[0] # ch_v0r96 (addedl by m.taheri)
        selectedcam.cam_VP1_y = VP1[1]
        
        
    elif video_FPS == '' and road_camera_staff != '' and To_VP == '':
        print('Yaah ----------------- road_camera_staff -----------------------> ', road_camera_staff)
        original_vp1, original_vp2, focal_length, tilt, cam_height, original_centre, swing, video_FPS, Rotation_Matrix, To_VP, VP1_rsz = getPrmLeast(road_camera_staff) # ch_v0r86 (To_VP and VP1_rsz added)
        print('original_vp2 ------> ', original_vp2)    
        querry = "UPDATE CAM_"+ID+" SET cam_focal=%s , cam_height=%s , cam_swing=%s, cam_tilt=%s , cam_center_X=%s , cam_center_Y=%s, cam_VP2_X=%s, cam_VP2_y=%s  WHERE did=%s;"
        #c.execute(querry, (focal_length, cam_height, swing, tilt *( 180 / np.pi), original_centre[0], original_centre[1], round(original_vp2[0],3), round(original_vp2[1],2), 1)) # ch_v0r91 (round(original_vp2[0],3), round(original_vp2[1],2) replaced) # ch_v0r96 (commented by m.taheri)
        
        selectedcam.cam_focal =  focal_length # ch_v0r96 (addedl by m.taheri)
        selectedcam.cam_height =cam_height
        selectedcam.cam_swing= swing
        selectedcam.cam_tilt= tilt *( 180 / np.pi)
        selectedcam.cam_center_X =original_centre[0]
        selectedcam.cam_center_Y =original_centre[1]
        selectedcam.cam_VP2_X =round(original_vp2[0],3)
        selectedcam.cam_VP2_y=round(original_vp2[1],2)





    elif road_camera_staff == '' and VP1 == '' and To_VP == '':
        print('Yaah ----------------- FPS -----------------------> ', int(video_FPS))
        # c.execute("UPDATE CAM_"+ID+" SET cam_FPS=%s WHERE did=%s;", (int(video_FPS), 1)) # ch_v0r96 (commented by m.taheri)
        
        selectedcam.cam_FPS = int(video_FPS)
    else:
        print('Yaah ----------------- To_VP -----------------------> ', int(To_VP))
        # c.execute("UPDATE CAM_"+ID+" SET To_VP=%s WHERE did=%s;", (int(To_VP), 1)) # ch_v0r96 (commented by m.taheri)

        selectedcam.To_VP = int(To_VP) # ch_v0r96 (addedl by m.taheri)

    db.session.commit() # ch_v0r96 (added by m.taheri)
    """ conn.commit()   # ch_v0r96 (commented by m.taheri)
    c.close()
    conn.close() """ 
    # create the application object
#------------------------- # ch_v0r86 (added)  --------------------------------------------------# 
# write to DB roi
#---------------------------------------------------------------------------# 
def write_to_db_roi(ID, points_roi):
    
    #c, conn = connection()
    print('Yaah ----------------- points_roi -----------------------> ', points_roi)
    #c.execute("UPDATE CAM_"+ID+" SET mask_points=%s WHERE did=%s;", (points_roi, 1))

    selectedcam = Camera.query.filter_by(did=ID).first() # ch_v0r96 (addedl by m.taheri)
    selectedcam.mask_points = points_roi

    db.session.commit()
    """ conn.commit()            
    c.close()
    conn.close() """ 
#------------------------- # ch_v0r87  update any field of any cam(Based on python dictionary added)  --------------------------------------------------# 
# write to DB any
#---------------------------------------------------------------------------# 
def write_to_db_any(ID, cam_dict): # ch_v0r90 (ID --> table)
    
    selectedcam = Camera.query.filter_by(did=ID).first()
    if selectedcam is not None:
        for key, value in cam_dict.items():

            if "IP_cam" in key:
                selectedcam.IP_cam = value
            
            elif "url_cam" in key:
                selectedcam.url_cam = value
            
            elif "cam_VP1_X" in key:
                selectedcam.cam_VP1_X =value

            elif "cam_VP1_y" in key:
                selectedcam.cam_VP1_y =value

            elif "cam_focal" in key:
                selectedcam.cam_focal =value
                
            elif "cam_height" in key:
                selectedcam.cam_height =value
            
            elif "cam_swing" in key:
                selectedcam.cam_swing =value

            elif "cam_tilt" in key:
                selectedcam.cam_tilt =value

            elif "cam_center_X" in key:
                selectedcam.cam_center_X =value

            elif "cam_center_Y" in key:
                selectedcam.cam_center_Y =value

            elif "cam_FPS" in key:
                selectedcam.cam_FPS =value

            elif "cam_VP2_X" in key:
                selectedcam.cam_VP2_X =value

            elif "cam_VP2_y" in key:
                selectedcam.cam_VP2_y =value

            elif "To_VP" in key:
                selectedcam.To_VP =value

            elif "mask_points" in key:
                selectedcam.mask_points =value

            elif "detection_type" in key:
                selectedcam.detection_type =value

            elif "slow_vehicle_th" in key:
                selectedcam.slow_vehicle_th =value

            elif "stop_vehicle_th" in key:
                selectedcam.stop_vehicle_th =value

            elif "road_points" in key:
                selectedcam.road_points =value

            elif "ped_walkway_1_points" in key:
                selectedcam.ped_walkway_1_points =value

            elif "ped_walkway_2_points" in key:
                selectedcam.ped_walkway_2_points =value

            elif "stop_vehicle_dur_th" in key:
                selectedcam.stop_vehicle_dur_th =value

            elif "disp_stop_roi" in key:
                selectedcam.disp_stop_roi =value

            elif "draw_3d" in key:
                selectedcam.draw_3d =value

            elif "class_lines_roi" in key:
                selectedcam.class_lines_roi =value

            elif "bike_dimensions" in key:
                selectedcam.bike_dimensions =value

            elif "car_dimensions" in key:
                selectedcam.car_dimensions =value

            elif "truck_dimensions" in key:
                selectedcam.truck_dimensions =value

            elif "disp_dimensions" in key:
                selectedcam.disp_dimensions =value

            elif "theme_ind" in key:
                selectedcam.theme_ind =value

            elif "Background_road_congest" in key:
                selectedcam.Background_road_congest =value

            elif "smoke_ROI_points" in key:
                selectedcam.smoke_ROI_points =value


            elif "smoke_staff" in key:
                selectedcam.smoke_staff =value



            elif "isenable" in key:
                selectedcam.isenable =value



            elif "isvalid" in key:
                selectedcam.isvalid =value


            elif "pingok" in key:
                selectedcam.pingok =value

    db.session.commit()


    """ c, conn = connection()
    #print(table, ' Yaah ----------------- cam_dict -----------------------> ', cam_dict)
    sql = "UPDATE "+table+" SET {} where did = {}".format(', '.join('{}=%s'.format(k) for k in cam_dict), '%s') # ch_v0r90 (CAM_"+ID --> table)
    if sys.version_info >= (3, 0): # ch_v0r92  (In Python3 dict.values() returns "views" instead of lists:)
        values = list(cam_dict.values())
    else:
        values = cam_dict.values()
    print(sql, values)
    values.append(1)
    c.execute(sql, values)
        
    conn.commit()            
    c.close()
    conn.close()  """


#============================  # ch_v0r87 (added)  ============================================
def add_remove_stopped_vehicle(pick, newH_1, stopped_vehicles, frameId, frame_2_masked, backgroundImage_2, scale12_rev, FD_delta_frame_stv = 7):  # ch_v0r87 (frame_2_masked, backgroundImage_2 and newH_1 )--> added

    stopped_vehicles_new = []

    if len(pick) == 0:
        for rect in stopped_vehicles:
            if True: #len(pick) == 0: # ch_v0r87 (commented)
                pick = np.array([rect[0:4]])
            #else: # ch_v0r87 (commented)
            #    pick = np.concatenate((pick, np.array([rect[0:4]])), axis=0) # ch_v0r87 (commented)
            if rect[4] == 0: # has disappeared for the first time
                rect_ = (rect[0:4]*scale12_rev).astype(int)
                SIMS = bbox_img_background_compare_oneBox(rect_, frame_2_masked, backgroundImage_2, method_th=0.65, mse_th_1=900, mse_th_2=1500 , method='SSIM') # ch_v0r87 (added)
                if not np.logical_or(SIMS[0][0],SIMS[0][1]): # ch_v0r87 (added) if background and foreground are different in stopped vehicle area
                    rect[4] = 1
                    rect[6] = frameId
                    stopped_vehicles_new.append(rect) # ch_v0r87 (added) 
            else: # ch_v0r87 (added) 
                stopped_vehicles_new.append(rect) # ch_v0r87 (added) 

    else:
        #print('len(stopped_vehicles) -->',len(stopped_vehicles))
        for rect in stopped_vehicles:
            len_pick = len(pick)
            
            # ----------------------  ch_v0r87 (added)
            if rect[3] > newH_1/float(3):  
                if rect[4] == 0:
                    overlapThresh = 0.85
                else:
                    overlapThresh = 0.6
            else:
                overlapThresh = 0.7
            # ----------------------  ch_v0r87 (added)
            
            pick = np.concatenate((pick, np.array([rect[0:4]])), axis=0)
            pick = non_max_suppression(pick, probs=None, overlapThresh=overlapThresh) # (overlapThresh*100)% overlap ch_v0r87 (added)

            # bigger box --> "stopped vehicle rect" and the smaller one --> "detected object"
            # if before and after appending the stopped vehicle to the pick (detected bonding boxed) it's length does not
            # change, it means that "we can see the stopped vehicle"
            # and it means either it hasn't disappeared yet or it has appeared again.
            #     __________                            __________
            #    |  ______  |                          |          |
            #    | |      | |  non_max_suppression     |          |
            #    | |______| |  ------------------->    |          |
            #    |__________|                          |__________|
            if len(pick) == len_pick: # if you see the object
                if rect[4] == 0: # hasn't disappeared yet
                    #print(" hasn't disappeared yet")
                    stopped_vehicles_new.append(rect)
                elif rect[4] == 1 and np.abs(rect[6] - frameId) < FD_delta_frame_stv: # it should be passed at-least some frames from the first disappearing
                    #print("it should be passed at-least some frames from the first disappearing", np.abs(rect[6] - frameId),FD_delta_frame_stv)
                    stopped_vehicles_new.append(rect)
                else: #---> not append so it will be deleted from stopped_vehicles list so will not be appended to stopped vehicles
                    #print('not append so it will be deleted from stopped_vehicles list so will not be appended to stopped vehicles')
                    pass

            elif len(pick) != len_pick and rect[4] == 0: # first disappearing (has disappeared for the first time)
                #print("first disappearing (has disappeared for the first time)" )
                rect_ = (rect[0:4]*scale12_rev).astype(int)
                SIMS = bbox_img_background_compare_oneBox(rect_, frame_2_masked, backgroundImage_2, method_th=0.65, mse_th_1=900, mse_th_2=1500 , method='SSIM') # ch_v0r87 (added)
                if not np.logical_or(SIMS[0][0],SIMS[0][1]) : # ch_v0r87 (added) if background and foreground are different in stopped vehicle area
                    #print('           save the current frame ID to know the first disappearing frame    ')
                    rect[4] = 1
                    rect[6] = frameId # save the current frame ID to know the first disappearing frame
                    stopped_vehicles_new.append(rect)
            elif len(pick) != len_pick and rect[4] == 1: # hasn't been seen for a while
                #print("hasn't been seen for a while" )
                stopped_vehicles_new.append(rect)
    if len(pick)!=0 and len(stopped_vehicles_new) !=0:
        pick = np.concatenate((pick, np.array(stopped_vehicles_new)[:,0:4]), axis=0) # ch_v0r87 (added)
        pick = non_max_suppression_org(pick, probs=None, overlapThresh=0.7) # 1% overlap # ch_v0r87 (added)
    return pick, stopped_vehicles_new

#============================  # ch_v0r87 (added)  ============================================
def add_remove_stopped_vehicle_2(pick, newH_1, stopped_vehicles, frameId, frame_2_masked, backgroundImage_2, scale12_rev, FPS, stop_vehicle_th, stop_vehicle_dur_th):  # ch_v0r88 (stop_vehicle_dur_th added)

    stopped_vehicles_new = [] # real stopped vehicles 
    stopped_vehicles_final = [] # stopped vehicles that should be alarmed and shown and after a certain time will be cleared 

    if len(stopped_vehicles) != 0:
        for rect in stopped_vehicles:
            rect_ = (rect[0:4]*scale12_rev).astype(int)
            xA, yA, xB, yB = rect_[0:4] # rect = [xA, yA, xB, yB, stopped_bit, tracks_i.track_id, frameId, fg_hash, bg_hash]
            
            h_fg_old_roi = rect[7]
            h_bg_old_roi = rect[8]
            
            fg_new_roi = roi(xA, yA, xB, yB, frame_2_masked)
            
            h_fg_new_roi = dhash(fg_new_roi)
            h_fg_new_roi = convert_hash(h_fg_new_roi)
            
            
            err_hash_fg = hamming(h_fg_old_roi, h_fg_new_roi)
            err_hash_fgbg = hamming(h_fg_new_roi, h_bg_old_roi)
            #print('err_hash_fg-------------------> ',err_hash_fg, 'err_hash_fgbg---------------> ', err_hash_fgbg)
            
            if rect[4] == 0 and err_hash_fg < 9 and err_hash_fgbg > 9: # hasn't disappeared yet
                    rect[4] = 1
                    rect[6] = frameId
                    stopped_vehicles_new.append(rect) # ch_v0r87 (added) 
            elif rect[4] == 1 and err_hash_fg < 17 and err_hash_fgbg > 9: # hasn't disappeared yet
                stopped_vehicles_new.append(rect) # ch_v0r87 (added) 
                if (np.abs(rect[6] - frameId)/np.float(FPS) > stop_vehicle_th) and (np.abs(rect[6] - frameId)/np.float(FPS) < (stop_vehicle_dur_th+stop_vehicle_th)): # ch_v0r88 (stop_vehicle_dur_th) (to ensure delta_time passed to show the stopped vehicle)
                    stopped_vehicles_final.append(rect) # ch_v0r86
            else: #---> not append so it will be deleted from stopped_vehicles list so will not be appended to stopped vehicles
                #print('not append so it will be deleted from stopped_vehicles list so will not be appended to stopped vehicles')
                pass
            
    if len(pick) ==0 and (len(stopped_vehicles_new) !=0 or len(stopped_vehicles_final) !=0):
        for rect in stopped_vehicles_new:
            pick = np.array([rect[0:4]]) 
        for rect in stopped_vehicles_final:
            pick = np.array([rect[0:4]]) 
        pick = non_max_suppression_org(pick, probs=None, overlapThresh=0.7) # 1% overlap # ch_v0r87 (added)
         
    if len(pick)!=0 and (len(stopped_vehicles_new) !=0 or len(stopped_vehicles_final) !=0):
        if len(stopped_vehicles_new) !=0:
            pick = np.concatenate((pick, np.array(stopped_vehicles_new)[:,0:4]), axis=0) # ch_v0r87 (added)
        if len(stopped_vehicles_final) !=0:
            pick = np.concatenate((pick, np.array(stopped_vehicles_final)[:,0:4]), axis=0) # ch_v0r87 (added)
        pick = non_max_suppression_org(pick, probs=None, overlapThresh=0.7) # 1% overlap # ch_v0r87 (added)
    return pick, stopped_vehicles_new, stopped_vehicles_final

        
    
#========================================================================
def ROI_transparent(frame,masked):    
    alpha = 0.65
    cv2.addWeighted(masked, alpha, frame, 1 - alpha, 0, frame)
    return frame
#========================================================================
# =====================================================================
def getPrmLeast(dfs):
    return dfs['vp1'], dfs['vp2'], dfs['focal'], dfs['tilt'], dfs['height'], dfs['centre'], dfs['swing'],  dfs['FPS'],\
           dfs['RotationMatrix2D'], dfs['To_VP'], dfs['VP1_rsz']  # ch_v0r86 ( To_VP and VP1_rsz added)

# =====================================================================
def getPrmDflt(dfs):
    return dfs['video'], dfs['Show'], dfs['StartAt'], dfs['FinishAt'], dfs['FrameStep'], dfs['FocalRange'], dfs['HorizonRange'], dfs['ROI'], dfs['pp']
#===========================================================
def getPrmDfs_calib_1(dfs):
    return dfs['fps_real'], dfs['frame_step_low'], \
            dfs['frame_step_hi'], dfs['frame_step'], \
            dfs['R_C'], dfs['origH'], dfs['origW'], dfs['mask_roi'], \
            dfs['frame_step_tmp'], dfs['debug'], dfs['kernel_lo']
#===========================================================
def getPrmDfs_calib_2(dfs):     
    return dfs['isRecording'], dfs['fps_real'], \
            dfs['resolution_1'], \
            dfs['resolution_2'], dfs['sharpening_kernel'], dfs['mask_roi'], \
            dfs['scale12'], dfs['isWeb'], dfs['stopped_vehicles'], \
            dfs['frameId_last'], dfs['tracker'], \
            dfs['track_len'], dfs['newH_1'], dfs['newW_1'], dfs['trackIdCount'], \
            dfs['track_colors'], dfs['Speed_Calculator'], \
            dfs['road_camera_staff'], dfs['speed_pup'], dfs['detector'], \
            dfs['current_frame_time'], dfs['prev_frame_time'], dfs['To_VP'], \
            dfs['P_intersect'], dfs['wrongWay_vehicles'], \
            dfs['record_staff'], dfs['Pedestrian'], dfs['Slow_vehicles'], \
            dfs['preprocess'], dfs['slow_vehicle_th'], dfs['stop_vehicle_th'], dfs['stop_vehicle_dur_th'], \
            dfs['disp_stop_roi'], dfs['draw_3d'], dfs['urlIsFile'], \
            dfs['stopped_vehicles_final'], dfs['scale12_rev'], dfs['newH_2'], dfs['newW_2'], dfs['class_permit'], \
            dfs['classification_staff'], dfs['disp_dimensions'], \
            dfs['Debris'], dfs['road_masked_roi'], dfs['Congestion_staff'], \
            dfs['backgroundImage_2'], dfs['smoke_staff'] #  ch_v0r92 (Debris, Congestion_staff, backgroundImage_2, smoke_staff added)

#===========================================================

def camera_calib(R_C, masked_frame):
    
    if R_C.B == None:
         R_C.setupImpl(masked_frame)
    R_C.Implementation(masked_frame)
    P1 = R_C.vp[0, 0:2]
    return P1
#===========================================================

def line_to_vanish(frame,P1):
    show_color = (0, 0, 255)
    GREEN_CIRCLE_COLOR = (0, 180,0)
    thickness = 1
    image = frame.copy()
    image = cv2.circle(image, (int(P1[0]), int(P1[1])), 12, GREEN_CIRCLE_COLOR, 3)
    image = cv2.circle(image, (int(P1[0]), int(P1[1])), 2, show_color, 2)
    for i in range(0, 40):
      if int(P1[0]) > image.shape[0] / 2:
          image = cv2.line(image,(int(6 * image.shape[0] / 2.0) - 60 *i, image.shape[1]), (int(P1[0]), int(P1[1])),show_color , thickness, cv2.LINE_AA)
      else:
          image = cv2.line(image,(int(- image.shape[0] / 4.0) + 60 *i, image.shape[1]), (int(P1[0]), int(P1[1])),show_color , thickness, cv2.LINE_AA)
    return image
#===========================================================
def hist_equ(frame, clahe): 
        for c in xrange(0, 2):
            frame[:, :, c] = clahe.apply(frame[:, :, c])
        return frame
#===========================================================
#---------------------------------------------------------
#@timing
def tic():
    #Homemade version of matlab tic and toc functions
    
    global startTime_for_tictoc
    startTime_for_tictoc = time.time()

def toc():
    if 'startTime_for_tictoc' in globals():
        print( "Elapsed time is " + str(time.time() - startTime_for_tictoc) + " seconds.") # ch_v0r90 (py3 change)
    else:
        print( "Toc: start time not set") # ch_v0r90 (py3 change)

#================= Determine the angle between 3 end points ===================
def scale_function( var, newW, newH,origW, origH, scale_type ):    
    if scale_type == 'VP':
        x_scale = origW/np.float(newW)
        y_scale = origH/np.float(newH)
        scaled_var = np.array([var[0]* x_scale, var[1]* y_scale])
        
    elif scale_type == 'P':
        x_scale = origW/np.float(newW)
        y_scale = origH/np.float(newH)
        
        scaled_var = (np.float(var[0])*np.float(x_scale)  , np.float(var[1])*np.float(y_scale))
    
    return scaled_var
#================= Determine the angle between 3 end points ===================
def angle_between_points( p0, p1, p2 ):
  # p1 is the center point; result is in degrees
  a = (p1[0]-p0[0])**2 + (p1[1]-p0[1])**2
  b = (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2
  c = (p2[0]-p0[0])**2 + (p2[1]-p0[1])**2
  return math.acos( (a+b-c) / math.sqrt(4*a*b) ) * 180/np.pi
#==============================================================================
def camera_stop(fps, camera, video,pause, reason, calib, videoLoop):# ch_v0r84 (calib, videoLoop added)
    #global calib
    #global  videoLoop # ch_v0r84
    print('\n'*2)    
    print('------------------------ Stop it -------------------------->', reason)
    print('\n'*2)
    if videoLoop != None:  # ch_v0r84
        videoLoop.framePluginInstance.close() # ch_v0r84
        time.sleep(0.5)# ch_v0r87
        videoLoop = None
        
    if fps != None:
        fps.stop()
        
    if camera != None:
        try:
            camera.release()
        except:
            camera.stop() 
            
        camera = None
    if pause == True:
        time.sleep(0.0)
    else:   
        if fps != None:
            print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
            print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))  
            fps = None
    return videoLoop # ch_v0r85 (added)
#==============================================================================           
def save_frame(step, camera, video, h, w, h_rsz, w_rsz, stop_bit, file_name, videoLoop, points_roi, frame, CAM_ID): # ch_v0r86 ('CAM_ID' added)
    #global camera, video, h, w, h_rsz, w_rsz, stop_bit, file_name
    #global  videoLoop # ch_v0r84
    stop_bit = 0
    
    #frame = cv2.flip(frame, 1);
    path = 'static/images'
    if step == 2: # 'calibration_step_1'
    
        #sharpening_kernel = np.array([[-1, -1, -1, -1, -1], [-1, 2, 2, 2, -1], [-1, 2, 8, 2, -1], [-2, 2, 2, 2, -1],
        #                      [-1, -1, -1, -1, -1]]) / 8.0  # edge_enhance # ch_v0r92 (commented and kernel_lo --> sharpening_kernel)
        sharpening_kernel = np.array(([0, -1, 0],[-1, 5, -1],	[0, -1, 0]), dtype="int") # sharpen moderate  # ch_v0r92 (added)
        frame = cv2.filter2D(frame, -1, sharpening_kernel)  # Enhancing the edges # ch_v0r92 (kernel_lo --> sharpening_kernel)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        frame = hist_equ(frame, clahe) # equalizeHist colored image
        
        
        for filename in glob.glob(path+'/screen_ready*'):
            try:
                os.remove(filename) 
                
            except Exception as e: # ch_v0r90 (change from Exception as e)
                  print("type error: " + str(e))  # ch_v0r90 (py3 change)
        file_name = 'screen_ready_'+datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')+ '.png' 
        cv2.imwrite(os.path.join(path, file_name) , frame)
        
    elif step == 0:   # '/roi_mouse_click'
        #print('frame saved ----------------------------> OK', frame.shape[0])
        for filename in glob.glob(path+'/mask_ready_'+str(CAM_ID)+'*'):
            try:
                os.remove(filename) 
                
            except Exception as e: # ch_v0r90 (change from Exception as e)
                  print("type error: " + str(e))  # ch_v0r90 (py3 change)
        file_name = 'mask_ready_'+str(CAM_ID)+'_'+datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')+ '.png'
        ''' # ch_v0r92 (moved to another place)
        masked_roi = np.zeros(frame.shape).astype(frame.dtype)
        color = [255, 255, 255] 
        cv2.fillPoly(masked_roi, np.int32([points_roi]), color)
        '''
        print('points_roi -------------->', points_roi)
        masked_roi = points_roi_To_mask(frame.shape, frame.dtype, points_roi)
        cv2.imwrite(os.path.join(path, file_name) , masked_roi)
    time.sleep(1.0)
    return file_name, stop_bit # ch_v0r85
    
#=============================================================
    # ----------ch_v0r87 -----------(added)-------------
def computeCameraCalibration(_vp1, _vp2, _pp, focal):
    if False:
        cross_x = np.hstack((_vp1, focal)) - np.hstack((_pp, 0))
        cross_y = np.hstack((_vp2, focal)) - np.hstack((_pp, 0))
        V3 = np.cross(cross_x, cross_y)
        V3 = V3 / V3[2] * focal + V3 # ----------ch_v0r90 (added temp)
        V3 = np.hstack((V3[0:2] , 1.0000)) 
    else:
        vp1W = np.concatenate((_vp1, [focal]))    
        vp2W = np.concatenate((_vp2, [focal]))    
        ppW = np.concatenate((_pp, [0])) 
        vp3W = np.cross(vp1W-ppW, vp2W-ppW)
        V3 = np.concatenate((vp3W[0:2]/vp3W[2]*focal + ppW[0:2], [1]))
        
    return V3#vp3

# ----------ch_v0r87 -----------(added)-------------    
def bbox_img_background_compare_oneBox(rect, frame, background, method_th, mse_th_1, mse_th_2, method='SSIM'):
    
    SIMS = []
    
    xA, yA, xB, yB = rect
    
    
    roi_frame = roi( xA, yA, xB, yB, frame)
    roi_background = roi( xA, yA, xB, yB, background)
    
    
    if method == 'mse' : # ---------> should be more than 1000 to be consider as a foreground (time 0.00023 seconds) the fastest
        sim_Measur_2 = 0
        sim_Measur_1 = 0
        sim_mse = mse(roi_frame, roi_background)
        if sim_mse < mse_th_1:
            sim_Measur_1 = 1
        if mse_th_1 < sim_mse < mse_th_2:
            try:
                if SSIM(roi_frame, roi_background) > method_th:
                    sim_Measur_2 = 1
            except:
                pass
        #print('sim_mse --> ', sim_mse)
   
        
    elif method == 'SSIM' : # ---------> should be less than 0.75 to be consider as a foreground (time 0.0015 seconds) best choice (fastT accurate and robust)
        sim_Measur_2 = 0
        sim_Measur_1 = 0
        try:
            sim_SSIM = SSIM(roi_frame, roi_background)
            if  sim_SSIM > method_th:
                sim_Measur_2 = 1
            elif  0.5 < sim_SSIM < method_th:
                sim_mse = mse(roi_frame, roi_background)
                #print('sim_mse --------------------> ', sim_mse)
                if sim_mse < mse_th_1:
                    sim_Measur_1 = 1
        except:
            sim_mse = mse(roi_frame, roi_background)
            if sim_mse < mse_th_1:
                sim_Measur_1 = 1
               
                
    SIMS.append([sim_Measur_1,sim_Measur_2])
        
    return SIMS

# ----------ch_v0r87 -----------(added)-------------    
def mse(gray_img1, gray_img2):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
    err = np.sum((gray_img1.astype("float") - gray_img2.astype("float")) ** 2)
    err /= float(gray_img1.shape[0] * gray_img1.shape[1])
    return err

#----------------------------------------------------------------------
# ----------ch_v0r87 -----------(added)-------------    
def SSIM(gray_img1, gray_img2):
    return ssim(gray_img1, gray_img2) 
#----------------------------------------------------------------------
# ----------ch_v0r87 -----------(added)-------------
def roi(x1,y1,x2,y2, mask):
    roi = mask[y1:y2, x1:x2]
    return roi
#----------------------------------------------------------------------
# ----------ch_v0r87 -----------(added)------------- 
def remove_wrongWay_Non_vehicles(wrongWay_vehicles, frame_2_masked, backgroundImage_2 , scale12_rev): 
    # wrongWay_vehicles.append([xA, yA, xB, yB, tracks_i.track_id, frameId])
    wrongWay_vehicles_final = []
    for WW_vehicle in wrongWay_vehicles:
        rect = (WW_vehicle[0:4]*scale12_rev).astype(int)
        
        SIMS = bbox_img_background_compare_oneBox(rect, frame_2_masked, backgroundImage_2, method_th=0.65, mse_th_1=900, mse_th_2=1500 , method='SSIM') # ch_v0r87 (added)
        if not np.logical_or(SIMS[0][0],SIMS[0][1]): # ch_v0r87 (added) if background and foreground are different in stopped vehicle area
           wrongWay_vehicles_final.append(WW_vehicle) 
    return wrongWay_vehicles_final
#----------------------------------------------------------------------
# ----------ch_v0r87 -----------(added)------------- 
def refine_pick(pick, SIMS, Pedestrian):
    pick_refined = []
    for rect, sim  in zip(pick,SIMS) :
        if not np.logical_or(sim[0],sim[1]):
            pick_refined.append(rect)
    if len(Pedestrian) != 0:
        if len(pick_refined) != 0:
            pick_refined = np.concatenate((pick_refined, np.array(Pedestrian)[:,0:4]), axis=0) # ch_v0r87 (added)
            pick_refined = non_max_suppression(pick_refined, probs=None, overlapThresh=0.4) # 1% overlap # ch_v0r87 (added)
        #else:
        #    pick_refined = np.array(Pedestrian)[:,0:4]
    return pick_refined

#-----------------------------  dhash  ------------------------------------
# ----------ch_v0r87 -----------(added)------------- ----------------------   
def dhash(gray, hashSize=8):
    # convert the image to grayscale
    #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
     
    # resize the grayscale image, adding a single column (width) so we
    # can compute the horizontal gradient
    resized = cv2.resize(gray, (hashSize + 1, hashSize))
     
    # compute the (relative) horizontal gradient between adjacent
    # column pixels
    diff = resized[:, 1:] > resized[:, :-1]
     
    # convert the difference image to a hash
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def convert_hash(h):
    # convert the hash to NumPy's 64-bit float and then back to
    # Python's built in int
    return int(np.array(h, dtype="float64"))

def hamming(a, b):
    # compute and return the Hamming distance between the integers
    return bin(int(a) ^ int(b)).count("1")

# ---------- ch_v0r92 
def image_to_hash(img):
    h_1 = dhash(img)
    img_hash = convert_hash(h_1)
    return img_hash
    

def fgbg_get_hash(gray_img1, gray_img2):
    ''' ch_v0r92 (commented)
    h_1 = dhash(gray_img1)
    h_1 = convert_hash(h_1)
    
    h_2 = dhash(gray_img2)
    h_2 = convert_hash(h_2)
    '''
    h_1 = image_to_hash(gray_img1) # ch_v0r92 (added)
    h_2 = image_to_hash(gray_img2) # ch_v0r92 (added)
    return h_1, h_2

def dhash_sim(gray_img1, gray_img2):
    # compute the hash for the image and convert it
    h_1, h_2 = fgbg_get_hash(gray_img1, gray_img2)
    return hamming(h_1, h_2)

#---------------------- ch_v0r88 -----------(added)-  ------------------------
def poitsROIstr_to_pointsROInp(points_roi, type_tuple, rect=False): # ch_v0r92 ('rect=False added)
    a=[]
    if rect == False:
        for i in range(points_roi.count(';')):
            pnt = points_roi.split(';')[i].split(',')
            a.append(tuple(np.array(pnt).astype(type_tuple)))# ch_v0r91 (' np.int' ->'type_tuple' )
        points_roi = np.array(a)
    else:
        for i in range(points_roi.count(';')):
            pnt = points_roi.split(';')[i].split(',')
            a.append(int(pnt[0]))
            a.append(int(pnt[1]))
        points_roi = a
            
    return points_roi
#---------------------- ch_v0r88 -----------(added)-  ------------------------
def point_inside_ROI(bbPath, points_roi, point):
    #bbPath = mplPath.Path(points_roi);
    return bbPath.contains_point((point[0], point[1]))
#---------------------- ch_v0r88 -----------(added)-  ------------------------
def get_lock(process_name):
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exits
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        get_lock._lock_socket.bind('\0' + process_name)
        print( process_name +' : I got the lock')  # ch_v0r90 (py3 change)
    except socket.error:
        print(process_name +' : lock exists ')  # ch_v0r90 (py3 change)
        time.sleep(3)
        sys.exit(0)
#---------------------- ch_v0r89 -----------(added to find currend_seconds_of_day % 60 as an index)-  ------------------------

def find_min_day_ind():
    now = datetime.datetime.now()
    seconds_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    one_min_day_ind = int(seconds_since_midnight//60)
    #print("one_min_day_ind is %s :" % str(one_min_day_ind))
    return one_min_day_ind
#---------------------- ch_v0r89 -----------(added to find currend_minutes of this hour)-  ------------------------
def get_minute():
    return datetime.datetime.now().minute

#---------------------------------------------------------------------------# 
# read from DB All    ch_v0r89 added
#---------------------------------------------------------------------------# 
def read_from_db_all(query, param):
    table = ''
    c, conn = connection()
    data = c.execute(query, param) 
           
    if int(data) > 0:
        table = c.fetchall()        
        conn.commit()
        c.close()
        conn.close()
        return table
    else:
        return ''
    
def check_for_1_week_period(date_from, date_to, diff_days_duration): # ch_v0r91 diff_days_duration added)
    if date_to == '':
        today = datetime.date.today()
        date_from_DT = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
        diff_days = (today - date_from_DT.date()).days
    else:
        date_from_DT = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
        date_to_DT = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
        diff_days = (date_to_DT.date() - date_from_DT.date()).days
        
    if diff_days > diff_days_duration: # ch_v0r91 diff_days_duration added)
        return 0
    else:
        return 1
#---------------------------------------------------------------------------# 
# Check Incidents Status    ch_v0r90 added
#---------------------------------------------------------------------------#
def Inci_Check_Status(dfs, Inci_Bits, record_status):
    
    Incident_detected = (len(dfs['stopped_vehicles_final']) != 0  or len(dfs['Pedestrian']) !=0  ) # or len(dfs['wrongWay_vehicles']) !=0 (temp commented)
    # Inci_Bits = {'ST_bit': 0, 'WW_bit': 0, 'Ped_bit':0} # ch_v0r90 (added)
    New_Inci_when_recording = New_Inci = 0
    # check if any Incident detected
    if Incident_detected:
        # if Stopped_Vehicle is dertected for the first time
        if len(dfs['stopped_vehicles_final']) != 0 and Inci_Bits['ST_bit'] == 0: 
            Inci_Bits['ST_bit'] = 1
            New_Inci_when_recording = 1
        
        # if Pedestrian is dertected for the first time    
        if len(dfs['Pedestrian']) !=0 and Inci_Bits['Ped_bit'] == 0: 
            Inci_Bits['Ped_bit'] = 1
            New_Inci_when_recording = 2
        
        # if wrongWay_vehicles is detected for the first time
        if len(dfs['wrongWay_vehicles']) !=0 and Inci_Bits['WW_bit'] == 0: 
            Inci_Bits['WW_bit'] = 1
            New_Inci_when_recording = 3
        
    # if recording finished and No new Incident detected 
    elif record_status == 0 : 
        #  reset Inci_Bits 
        Inci_Bits['ST_bit'] = Inci_Bits['Ped_bit'] =  Inci_Bits['WW_bit'] = 0
    # set Slow_bit only when slow_vehicle detected because 
    # it would not suppose to record if Slow_vehicles detected
    Inci_Bits['Slow_bit'] = (len(dfs['Slow_vehicles']) !=0) 
    # if is_Recording and new Incident detected        
    if record_status and New_Inci_when_recording == 1: 
        pass # Do nothing
    # elif not_recording and new Incident detected   
    elif record_status == False and New_Inci_when_recording != 0:
        New_Inci = 1 # first new_incident detected so we should start recording and log it with new video name
            
    return Incident_detected, Inci_Bits, New_Inci, New_Inci_when_recording

#-------------------------------- # ch_v0r90 (run system commands) -----------------------------------------
def run_cmd(cmd, input=""):
    rst = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, input=input.encode("utf-8"))
    #assert rst.returncode == 0, rst.stderr.decode("utf-8")
    return rst.stdout.decode("utf-8")

#-------------------------------- # ch_v0r90 (video convert) -----------------------------------------
def video_convert_web_friendly(record_staff, r):
    
    video_path = str(r.lindex('All_Cams_record_name', int(record_staff['cam_ID'])-1),'utf-8')
    base_file_name = Path(video_path).stem
    output = "{}/{}.mp4".format(record_staff['output'], base_file_name)
    cmd = "ffmpeg -i "+ video_path+" -c:v libx264 -pix_fmt yuv420p "+ output
    run_cmd(cmd)
    cmd = 'rm '+ video_path
    run_cmd(cmd)
#--------------- # ch_v0r90 (write to DB) ---------------------------------------
# Log the Incidents Status    ch_v0r90 added
#---------------------------------------------------------------------------#   
def write_to_db_any_insert(table, cam_dict): # ch_v0r90 (ID --> table)
    c, conn = connection()
    #print(table, ' Yaah ----------------- cam_dict -----------------------> ', cam_dict)
    sql = "INSERT INTO "+table+" SET {}".format(', '.join('{}=%s'.format(k) for k in cam_dict)) # ch_v0r90 (CAM_"+ID --> table)
    values = cam_dict.values()
    c.execute(sql, values)
    conn.commit()            
    c.close()
    conn.close()
    
#--------------- # ch_v0r90 (Log to DB) ---------------------------------------
# Log the Incidents Status    ch_v0r90 added
#---------------------------------------------------------------------------#
def Log_Incidents_Status(New_Inci, New_Inci_when_recording, r, output, cam_ID, Inci_Names) :
    
    def str_to_datetime(format_time_in, format_time_out):
        dateTimeObj = datetime.datetime.strptime(strptime, format_time_in)
        timestampStr = dateTimeObj.strftime(format_time_out)
        return timestampStr
    # New_Inci_when_recording: 1-->stop, 2-->ped, 3-->WW...
    if New_Inci or New_Inci_when_recording !=0:
        video_path = str(r.lindex('All_Cams_record_name', int(cam_ID)-1),'utf-8')
        base_file_name = Path(video_path).stem
        output = "{}/{}.mp4".format(output, base_file_name)
        strptime = '20'+output[output.find('_20')+len('_20'):output.rfind('.mp4')]
        timestampStr = str_to_datetime("%Y%m%d-%H%M%S", "%Y-%m-%d %H:%M:%S")
        if cam_ID < 10:
            cam_ID_str = '0'+str(cam_ID)
        cam_dict={'camera_name': 'Cam_'+cam_ID_str,'videodatetime':timestampStr, 'name':'lane_1', 'type':Inci_Names[New_Inci_when_recording-1] ,'video_path': base_file_name+'.mp4'}
        write_to_db_any_insert('Incidents', cam_dict)
        '''
        if New_Inci:
            print('New Ever Incident --> '+Inci_Names[New_Inci_when_recording-1], 'video_path--> '+output)
        else:# New_Inci_when_recording !=0:
            print('New Incident --> '+Inci_Names[New_Inci_when_recording-1], 'video_path--> '+output)
        '''
#--------------- # ch_v0r90 (read VP1 from to DB) --------------------------------------- 
def VP1_from_DB(ID, w_rsz, h_rsz):
    #ID = r.get("ID") # ch_v0r85
    row = list(read_from_db("CAM_"+ID))    
    orig_VP1 = np.array([row[3], row[4]])
    (w, h) = (2*int(row[9]), 2*int(row[10]))
    VP1 = scale_function( orig_VP1, w, h, w_rsz, h_rsz, 'VP' )
    print(VP1,orig_VP1, w, h, w_rsz, h_rsz)
    return VP1, orig_VP1, row      
#--------------- # ch_v0r91 (make classification staff) --------------------------------------- 
def make_classification_staff(cam):

    """ class_lines_roi  = row[25]
    bike_dimensions  = row[26]
    car_dimensions   = row[27]
    truck_dimensions = row[28] """
    
    class_lines_roi  = cam.class_lines_roi
    bike_dimensions  = cam.bike_dimensions
    car_dimensions   = cam.car_dimensions
    truck_dimensions = cam.truck_dimensions

    class_lines_roi_np  = poitsROIstr_to_pointsROInp(class_lines_roi, np.int32) # ch_v0r96 (added by m.taheri)
    bike_dimensions_np  = poitsROIstr_to_pointsROInp(bike_dimensions, np.float32)# ch_v0r96 (added by m.taheri)
    car_dimensions_np   = poitsROIstr_to_pointsROInp(car_dimensions, np.float32)# ch_v0r96 (added by m.taheri)
    truck_dimensions_np = poitsROIstr_to_pointsROInp(truck_dimensions, np.float32)# ch_v0r96 (added by m.taheri)
    classification_staff = {'lines_roi_up': (100 -class_lines_roi_np), 'bike_dimensions':bike_dimensions_np, 'car_dimensions':car_dimensions_np, 'truck_dimensions':truck_dimensions_np}
    return classification_staff
    
#--------------- # ch_v0r91 (reset_counter_and_speeds) --------------------------------------- 
def reset_counter_and_speeds(r, CAM_ID, new_rec, class_permit):
    if class_permit:
        types = ['all','car','truck','motorbike']
        for vType in types:
            if vType == 'all':
                counter_tillNow_text           = 'All_Cams_counter_all_tillNow'
                count_untill_prev_minute_text  = 'All_Cams_counter_all_prev'
                MeanSpeed_prev_text            = 'All_Cams_speed_all_1_min'
                count_prev_minute_text         = 'All_Cams_counter_all_1_min'
                Incremental_speed_average_text = 'All_Cams_speed_all_1_min'
                
            elif vType == 'car':
                counter_tillNow_text           = 'All_Cams_counter_car_tillNow'
                count_untill_prev_minute_text  = 'All_Cams_counter_car_prev'
                MeanSpeed_prev_text            = 'All_Cams_speed_car_1_min'
                count_prev_minute_text         = 'All_Cams_counter_car_1_min'
                Incremental_speed_average_text = 'All_Cams_speed_car_1_min'
                
            elif vType == 'truck':
                counter_tillNow_text           = 'All_Cams_counter_truck_tillNow'
                count_untill_prev_minute_text  = 'All_Cams_counter_truck_prev'
                MeanSpeed_prev_text            = 'All_Cams_speed_truck_1_min'
                count_prev_minute_text         = 'All_Cams_counter_truck_1_min'
                Incremental_speed_average_text = 'All_Cams_speed_truck_1_min'
                
            elif vType == 'motorbike':
                counter_tillNow_text           = 'All_Cams_counter_motorbike_tillNow'
                count_untill_prev_minute_text  = 'All_Cams_counter_motorbike_prev'
                MeanSpeed_prev_text            = 'All_Cams_speed_motorbike_1_min'
                count_prev_minute_text         = 'All_Cams_counter_motorbike_1_min'
                Incremental_speed_average_text = 'All_Cams_speed_motorbike_1_min'
                
            if new_rec:  
                r.lset(counter_tillNow_text,           int(CAM_ID)-1,  0) # ch_v0r90 ( int(CAM_ID) --> int(CAM_ID)-1)
                r.lset(count_untill_prev_minute_text,  int(CAM_ID)-1,  0) # ch_v0r90 ( int(CAM_ID) --> int(CAM_ID)-1)
            r.lset(MeanSpeed_prev_text,            int(CAM_ID)-1,  0) # ch_v0r90 ( int(CAM_ID) --> int(CAM_ID)-1)
            r.lset(count_prev_minute_text,         int(CAM_ID)-1,  0) # ch_v0r90 ( added)
            r.lset(Incremental_speed_average_text, int(CAM_ID)-1,  0) # ch_v0r90 ( added)
            
#--------------- # ch_v0r91 (PIL_high_quality_resize) --------------------------------------- 
          
def PIL_high_quality_resize(frame_1, resolution_2):          
    im_pil=Image.fromarray( cv2.cvtColor(frame_1, cv2.COLOR_BGR2RGB) ) #convert cv2 to PIL
    im_pil = im_pil.resize(resolution_2,resample=Image.LANCZOS)
    # For reversing the operation:
    frame_2=cv2.cvtColor(np.asarray(im_pil), cv2.COLOR_RGB2BGR) #convert PIL to cv2
    '''
    frame_3 = cv2.resize(frame_1, resolution_2)
    print('\n'*2)  
    cv2.imshow('cv2', frame_3)
    cv2.imshow('pill', frame_2)
    cv2.waitKey(1)
    '''
    return frame_2
#===========================  # ch_v0r92 (added) =============================================
def stopped_vehicle_pick_handle(pick, stopped_vehicles, Debris):
    
    stopped_vehicles_sure = []
    if len(stopped_vehicles)>0:
        for rect in stopped_vehicles:
            
            if rect[10] == 4: # [xA, yA, xB, yB, debris_bit, track_id, frameId, fg_hash, bg_hash, debris_count, debris_candidate]
                stopped_vehicles_sure.append(rect)
            
        if len(pick)!=0 and len(stopped_vehicles_sure) !=0:
            pick = np.concatenate((pick, np.array(stopped_vehicles_sure)[:,0:4]), axis=0) # ch_v0r87 (added)
            pick = non_max_suppression_org(pick, probs=None, overlapThresh=0.7) # 1% overlap # ch_v0r87 (added)
    return pick

    
#===========================  # ch_v0r92 (added) =============================================
def GLCM(gray_image, max_level=32):
    #clipped = np.clip(image, a_min=0, a_max=4-1)
    clipped = np.uint8(np.digitize(gray_image, np.arange(0, 256, int(256/max_level)))) - 1
    
    # compute the GLCM
    # f[i,j,d,theta] is the number of times that grey-level j occurs at a distance d and at an angle theta from grey-level i
    f = greycomatrix(clipped, [1], [0, np.pi/4, np.pi/2, 3*np.pi/4], levels=max_level,normed=True, symmetric=False)
    f = np.array(f[1:32,1:32,:,:])
    
    #S_hat_g, S_p = self.ASM(f)
    #return round(np.mean(ASM(f)),2)
    
    # compute 'Angular Second Moment(ASM) => Energy = np.sqrt(ASM)'
    S_g = greycoprops(f, 'ASM') + np.finfo(float).eps # Sg 
    
    # The  value  of  Sg is  one  order  of  magnitude  lower  than  the  value  of  Entropt,
    # besides  ASM  is  inversely  proportional  with  vehicle  density.  
    # So  we  use  Eq.  below  to  calculate  new  energy feature 
    S_hat_g = -np.log(S_g ) # new  energy feature
    #print S_hat_g, round(np.mean(S_hat_g), 2)
    return round(np.mean(S_hat_g), 2)
    
# #===========================  # ch_v0r92 (added) =============================================
def points_roi_To_mask(frame_shape, frame_dtype, points_roi):
    masked_roi = np.zeros(frame_shape).astype(frame_dtype)
    color = [255, 255, 255] 
    print('points_roi-->', points_roi)
    cv2.fillPoly(masked_roi, np.int32([points_roi]), color)
    return masked_roi

# #===========================  # ch_v0r92 (added) =============================================
def save_background_road_congest(backgroundImage_2, road_masked_roi, Road_congest_th_1, cam_ID):
    saved_OK = False
    
    backgroundImage_masked = cv2.bitwise_and(backgroundImage_2, backgroundImage_2, mask = road_masked_roi)
    Back_Road_congest_new = GLCM(backgroundImage_masked) # calculate Background road congestion value
    #cv2.imshow(str(cam_ID)+'_back', backgroundImage_masked);  # ch_v0r92 (temp added)
    #cv2.waitKey(0)
    if Back_Road_congest_new < Road_congest_th_1:
        # save Road_congest
        #print(Back_Road_congest_new)
        cam_dict={'Background_road_congest': Back_Road_congest_new }  # ch_v0r89 (added)
        write_to_db_any(cam_ID, cam_dict)
        saved_OK = True
    return saved_OK, Back_Road_congest_new
    
# #===========================  # ch_v0r92 (added) =============================================
def Road_Congestion_calculate(Congestion_staff, frame_2, road_masked_roi):
    
    Back_Road_congest = Congestion_staff['Back_Road_congest']
        
    # Get the frame road mask 
    frame_2 = cv2.cvtColor(frame_2, cv2.COLOR_BGR2GRAY) # could be moved to higher place for optimization purepose
    frame_2_road_masked = cv2.bitwise_and(frame_2, frame_2, mask = road_masked_roi)
    # calculate Background road congestion value
    Foreground_Road_congest = GLCM(frame_2_road_masked) 
    
    # Calculate the foreground Ave_congestion of last 5 measurements and save it to previous one
    Congestion_staff['Ave_congestion_pre'].append(Foreground_Road_congest)
    Incremental_Ave_congestion = round(np.mean(Congestion_staff['Ave_congestion_pre']),2)
    
    # Compute the percentage Difference:  (\v1 - v2\ / average(v1,v2)) * 100
    congest_percent = round(( np.abs(Incremental_Ave_congestion - Back_Road_congest) / np.mean([Incremental_Ave_congestion, Back_Road_congest]) ) * 100, 2)
    
    if congest_percent < Congestion_staff['congest_diff_th1'] and Congestion_staff['congest_status'] != 0:
        
        # Uncongested
        Congestion_staff['congest_status'] = 0
        Congestion_staff['Ave_congestion_pre'] = deque(list(Congestion_staff['Ave_congestion_pre']), maxlen=5) # decrease the average list size to increase sensivity
        print('Back_Road_congest :', Back_Road_congest, '   Foreground_Road_congest :', Foreground_Road_congest, '   Incremental_Ave_congestion : ' , Incremental_Ave_congestion, '  congest_percent %:', congest_percent, Congestion_staff['congest_status'], Congestion_staff['Ave_congestion_pre'])    
    elif (Congestion_staff['congest_diff_th1'] < congest_percent < Congestion_staff['congest_diff_th2']) and Congestion_staff['congest_status'] != 1:
        
        # Near congested
        Congestion_staff['congest_status'] = 1
        Congestion_staff['Ave_congestion_pre'] = deque(list(Congestion_staff['Ave_congestion_pre']), maxlen=10) # icrease the average list size to decrease sensivity and increase robustness
        print('Back_Road_congest :', Back_Road_congest, '   Foreground_Road_congest :', Foreground_Road_congest, '   Incremental_Ave_congestion : ' , Incremental_Ave_congestion, '  congest_percent %:', congest_percent, Congestion_staff['congest_status'], Congestion_staff['Ave_congestion_pre'])    
    elif (Congestion_staff['congest_diff_th2'] < congest_percent) and Congestion_staff['congest_status'] != 2:
        # Congested
        Congestion_staff['congest_status'] = 2
    return Congestion_staff

# #===========================  # ch_v0r92 (added) =============================================
def congest_handle(cam_ID, pick, r, frame_2, backgroundImage_2, road_masked_roi, Congestion_staff, frameId, road_camera_staff):
    #cv2.imshow(str(cam_ID), backgroundImage_2);  # ch_v0r92 (temp added) 
    # if we have permision and the road is empty so get background
    if int(r.lindex('All_set_background_permit', int(cam_ID)-1)) == 1 and len(pick) == 0:
        #print(' *********************  save_background_road_congest *********************')
        #Road_congest_th_1 = 3 # temp threshold

        saved_OK, Back_Road_congest_new = save_background_road_congest(backgroundImage_2, road_masked_roi, Congestion_staff['Road_congest_th_1'], cam_ID)
        if saved_OK:
            print(' ****************  congestion_handle  **************** ')
            # reset the permision value and wait atleast 1 hour (KPI_Logger)
            r.lset("All_set_background_permit", int(cam_ID)-1, 0)
            Congestion_staff['Back_Road_congest'] = Back_Road_congest_new
    N = 1 if Congestion_staff['congest_status'] == 1 else 3    # In case of uncongestion update every 3 seconds else every seconds
    
    if frameId % (N*road_camera_staff['FPS']) == 0: # every 1 second check for road congestion
        Congestion_staff = Road_Congestion_calculate(Congestion_staff, frame_2, road_masked_roi)
    return Congestion_staff

# #===========================  # ch_v0r92 (added) =============================================
def variance_of_laplacian(gray):#, roi_mask):	
    # compute the Laplacian of the gray and then return the focus
    # measure, which is simply the variance of the Laplacian
    
    #w_h = gray.shape[0]*gray.shape[1]
    #sum_roi_mask = np.sum(roi_mask/255)
    return np.int(cv2.Laplacian(gray, cv2.CV_64F).var())#  * sum_roi_mask/float(w_h) )
    
# #===========================  # ch_v0r92 (added) =============================================
def V_Sat(img, V_th, S_th):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    V = hsv[...,2]
    S = hsv[...,1]
    mask_white = (V > V_th) & (S  < S_th)
    #roi_mask = roi_mask/255
    ind_white = np.sum(mask_white)
    ind_mask = img.shape[0] * img.shape[1]
    return round(ind_white/float(ind_mask),3), V, S

def V_Sat_ratio(V,S):
    return round(V.mean()/S.mean(),3)

def frame_smoke_calculate(frame_roi, smoke_staff):

    #cv2.imshow('cv2', frame_roi) # temp
    frame_roi_gray = cv2.cvtColor(frame_roi, cv2.COLOR_BGR2GRAY)
    
    # get blureness
    # with the existence of smoke or fog , this criteria will decrease
    VoL_frame = variance_of_laplacian(frame_roi_gray)
    
    smoke_staff['Ave_smoke_vis'].append(VoL_frame)
    
    Incremental_Ave_vis = round(np.mean(smoke_staff['Ave_smoke_vis']),2)
    
    # get background visibility
    VoL_back = int(smoke_staff['smoke_staff'][1])
    
    # Compute the percentage Difference:  (\v1 - v2\ / average(v1,v2)) * 100
    #visibility_change_percent = round(( (Incremental_Ave_vis - VoL_back) / np.mean([Incremental_Ave_vis, VoL_back]) ) * 100, 2)
    Alarm_percentage = round( ( (VoL_back - Incremental_Ave_vis) / ( VoL_back - smoke_staff['min_darkness_level'])  )*100,  2)
    if Alarm_percentage < smoke_staff['visibility_th1']:# and smoke_staff['smoke_status'] != 0:
        # Uncongested
        smoke_staff['smoke_status'] = 0
        smoke_staff['Ave_smoke_vis'] = deque(list(smoke_staff['Ave_smoke_vis']), maxlen=5) # decrease the average list size to increase sensivity
    elif smoke_staff['visibility_th1'] < Alarm_percentage < smoke_staff['visibility_th2']:# and smoke_staff['smoke_status'] != 1:
        
        # Near congested
        smoke_staff['smoke_status'] = 1
        smoke_staff['Ave_smoke_vis'] = deque(list(smoke_staff['Ave_smoke_vis']), maxlen=10) # icrease the average list size to decrease sensivity and increase robustness
    elif (Alarm_percentage > smoke_staff['visibility_th2']):# and smoke_staff['smoke_status'] != 2:
        # Congested
        smoke_staff['smoke_status'] = 2
    print('foreground_vis :', VoL_frame, '   back_visi :', int(smoke_staff['smoke_staff'][1]), '   Incremental_Ave_vis : ' , Incremental_Ave_vis, '  Alarm_percentage %:', Alarm_percentage, 'smoke_status : ', smoke_staff['smoke_status'])    
    return smoke_staff

def background_smoke_init(back_roi, smoke_staff, cam_ID, r):
    # initilize the smoke_staff list
    smoke_staff_new = []
    
    # get blureness
    # with the existence of smoke or fog , this criteria will decrease
    back_roi_gray = cv2.cvtColor(back_roi, cv2.COLOR_BGR2GRAY)
    VoL_back = variance_of_laplacian(back_roi_gray)
    
    if smoke_staff['smoke_staff'] != '':
        VoL_back_best = int(smoke_staff['smoke_staff'][0])
        visibility_change_percent = round(( np.abs(VoL_back - VoL_back_best) / np.mean([VoL_back, VoL_back_best]) ) * 100, 2)
    else:
        visibility_change_percent = 0
        
    if visibility_change_percent < smoke_staff['V_back_th']:
        # conver ROI RGB to HSV and get the Thresholds of V and Saturation
        hsv_back = cv2.cvtColor(back_roi, cv2.COLOR_BGR2HSV)
        smoke_staff['V_back_th'] = hsv_back[...,2].mean()
        smoke_staff['S_back_th'] = hsv_back[...,1].mean()
        # calculate V and saturation formula  ana also get V and S chanell of back. ROI
        # when Dark smoke apears this index decreases to zero
        V_Sat_back, V_back, S_back = V_Sat(back_roi, smoke_staff['V_back_th'], smoke_staff['S_back_th'])
        
        # compute V to S ratio
        # with the existence of white smoke or fog, this ratio will increase
        V_Sat_ratio_back = V_Sat_ratio(V_back, S_back)
        
        
        VoL_back_best  = VoL_back if smoke_staff['smoke_staff'] == '' else np.minimum(VoL_back, int(smoke_staff['smoke_staff'][0]) )
        smoke_staff_new.append(VoL_back_best)
        smoke_staff_new.append(VoL_back)
        smoke_staff_new.append(V_Sat_back)
        smoke_staff_new.append(V_Sat_ratio_back)
        
        # reset the hourly permision
        r.lset("All_set_background_permit_smoke", int(cam_ID)-1, 0)
        smoke_staff['smoke_staff'] = smoke_staff_new

        # save the background cri to Data-Base
        db_save =  ','.join([str(i) for i in smoke_staff_new])
        cam_dict={'smoke_staff': db_save }  
        write_to_db_any(cam_ID, cam_dict)
    return smoke_staff
# #===========================  # ch_v0r92 (added) =============================================
def smoke_handle(cam_ID, r, frame_2, rgb_background, smoke_staff, frameId, road_camera_staff):
    #print(int(r.lindex('All_set_background_permit_smoke', int(cam_ID)-1)), back_stablished)
    # if permision recieved after 1 houre
    # get smoke ROI and cut the background ROI and convert to gray scale
    N = 1 if smoke_staff['smoke_status'] == 1 else 3    # In case of uncongestion update every 3 seconds else every seconds    
    if frameId % (N*road_camera_staff['FPS']) == 0: # every 1 second check for road congestion
        x1,y1,x2,y2 = smoke_staff['smoke_ROI_points_np']    
        if int(r.lindex('All_set_background_permit_smoke', int(cam_ID)-1)) == 1:
            print(' ****************  smoke_handle  **************** ')
            back_roi = rgb_background[y1:y2, x1:x2,:]
            #cv2.imshow('cv2', back_roi) # temp
            smoke_staff = background_smoke_init(back_roi, smoke_staff, cam_ID, r)
                
        if smoke_staff['smoke_staff'] != '':        
            frame_roi = frame_2[y1:y2, x1:x2,:]
            smoke_staff = frame_smoke_calculate(frame_roi, smoke_staff) 
        
    return smoke_staff

# #===========================  # ch_v0r92 (added) =============================================
def rgb2ii(img, alpha = 0.333): # camera_alpha should be found from catalog
    """Convert RGB image to illumination invariant image. Based on paper :
    Illumination Invariant Imaging: Applications in Robust 
    Vision-basedLocalisation, Mapping and Classification for Autonomous Vehicles"""
    
    ii_image = (0.5 + np.log(img[:, :, 1] / float(255)) -
                alpha * np.log(img[:, :, 2] / float(255)) -
                (1 - alpha) * np.log(img[:, :, 0] / float(255))) #I think : [:, :, 2] <--> [:, :, 0] according to paper
    ii_image /= np.amax(ii_image)
    '''
    cv2.imshow("RGB Image", img)
    cv2.imshow("Illumination Invariant", ii_image)
    cv2.waitKey()
    '''
    return ii_image



        
