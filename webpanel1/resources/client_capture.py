#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 15:21:30 2020

@author: pi
"""

import cv2
from valkka.api2 import ShmemRGBClient
#import time
import redis # ch_v0r85 (added)
import numpy as np
from . import settings # ch_v0r89 (added)
from datetime import datetime

class client_capture():
    """ valkka client-server based video capture """
    
    def __init__(self, url, ID):
        """Open stream"""
        self.r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB) # ch_v0r89 (added)
        self.ind = int(ID)-1
        self.r.lset('All_Cams_live_status', self.ind,  0)
        self.shmem_name    =str(self.r.lindex('All_Cams_shmem_name', self.ind))        # This identifies posix shared memory - must be same as in the server side
        self.shmem_buffers =15              # Size of the shmem ringbuffer
        self.frameHeight = 480
        self.frameWidth = 864
        self.client=ShmemRGBClient(
          name          =self.shmem_name, 
          n_ringbuffer  =self.shmem_buffers,   
          width         =self.frameWidth,
          height        =self.frameHeight,
          mstimeout     =1000,        # client timeouts if nothing has been received in 1000 milliseconds
          verbose       =False)
        self.counter_timeout=0
        self.delay_time = datetime.now()
        self.start_delay_cnt = 0
        self.capture = cv2.VideoCapture(url)
        self.fps = int(str(int(self.capture.get(cv2.CAP_PROP_FPS)))[:2])
        self.prev_frame_time = 0
        
        
    def setProperties(self, properties):
        """ Set VideoCapture properties """
        if properties != None:
            for item in properties:
                self.capture.set(item[0], item[1])
    
    def load_new_client_prep(self):
        self.r.lset('All_Cams_live_status', self.ind,  0)
        self.shmem_name = 'CAM_'+str(self.ind+1)+'_'+str(np.random.randint(low=1000, high=99999, size=1)[0])
        self.r.lset("All_Cams_shmem_name"  , self.ind, self.shmem_name)
        self.delay_time = datetime.now()
        self.start_delay_cnt = 1
    
    def load_new_client(self):
        self.start_delay_cnt = 0
        self.counter_timeout=0
        self.client=None
        self.client=ShmemRGBClient(
                name          =self.shmem_name, 
                n_ringbuffer  =self.shmem_buffers,   
                width         =self.frameWidth,
                height        =self.frameHeight,
                mstimeout     =1000,        # client timeouts if nothing has been received in 1000 milliseconds
                verbose       =False)
        
    def getFrame(self):
        """ """
        if self.counter_timeout>1 and self.start_delay_cnt==0:
            if int(self.r.lindex('All_Cams_live_status', self.ind))==1 :
                print('new client is going to load')
                self.load_new_client_prep()
            
        if self.start_delay_cnt ==1:
            if (datetime.now() - self.delay_time).total_seconds() > 3 :
                print('new client loaded', self.shmem_name)
                self.load_new_client()
            
        
        index=None
        s = False
        if int(self.r.lindex('All_Cams_live_status', self.ind)) == 1:
            #index, meta = self.client.pullFrame()  #
            index, meta = self.client.pullFrameThread()
        if (index==None):
            
            s, image = self.capture.read() # In case the valkka not work get the frame from OpenCV
            #print(s, image)
            if s != False:
                image = cv2.resize(image, (self.frameWidth, self.frameHeight))
            
            mstimestamp = datetime.now()
            #time_ms = mstimestamp.timestamp() * 1000
            self.counter_timeout +=1
        
        else:
            if self.counter_timeout > 0:
                self.counter_timeout = 0
                
            data=self.client.shmem_list[index][0:meta.size]
            #time_ms = meta.mstimestamp
            mstimestamp         =datetime.fromtimestamp(meta.mstimestamp/1000.0)
            
            image = data.reshape((meta.height, meta.width, 3))
        '''    
        FPS                 = 1000/(time_ms - self.prev_frame_time)
        self.prev_frame_time     =time_ms
        print(f"So, The FPS is --> {FPS} ")  
        '''
        return image, mstimestamp, s
   
    def decodeFrame(self, image):
        """ valkka will not return a raw image, so we just return the decoded image passed """
        return image
   
    def close(self):
        """ Clean up resources """
        print('Stopping camera thread due to inactivity!')
        self.r.lset('All_Cams_live_status', self.ind,  -1)
        self.capture.release()
