#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  9 11:54:01 2019

@author: pi
"""

        
from skimage.feature import greycomatrix, greycoprops
import numpy as np
from numpy import ma
import warnings
import time, sys
warnings.simplefilter('error', RuntimeWarning)
import cv2

def tic():
    #Homemade version of matlab tic and toc functions    
    global startTime_for_tictoc
    startTime_for_tictoc = time.time()

def toc():
    if 'startTime_for_tictoc' in globals():
        print "Elapsed time is " + str(time.time() - startTime_for_tictoc) + " seconds."
    else:
        print "Toc: start time not set"
        
class congestion_recognition(object):
    """Tracker class that updates track vectors of object tracked
    Attributes:
        None
    """

    def __init__(self, congestion_thresh, max_level):
        """
        paper: Real-time Road Congestion Detection Based on Image Texture Analysis
        
        Initialize variable used by Tracker class
        Args:
            dist_thresh: distance threshold. When exceeds the threshold,
                         track will be deleted and new track is created
            max_frames_to_skip: maximum allowed frames to be skipped for
                                the track object undetected
            max_trace_lenght: trace path history length
            trackIdCount: identification of each track object
        Return:
            None
        """
        self.congestion_thresh = congestion_thresh
        self.max_level = max_level
    #---------------------------------------------------------
    def ASM(self, f):
        h = np.array(f).shape[0]
        w = np.array(f).shape[1]
        z = np.array(f).shape[3]
        
        # Calculate 'entropy feature'
        S_p = np.zeros((4,1))
        S_g = np.zeros((4,1))
        for i in range(0,z):
            for ii in range(0,h):
                for iii in range(0,w): 
                    S_g[i] = S_g[i] + f[ii,iii,0,i]**2
                    if f[ii,iii,0,i] !=0:
                        S_p[i]  = S_p[i] + f[ii,iii,0,i] * ( -np.log( f[ii,iii,0,i] ) )
        S_hat_g = -np.log(S_g) # new  energy feature
        return S_hat_g, S_p

    #---------------------------------------------------------
    def GLCM(self, image):
        
        #clipped = np.clip(image, a_min=0, a_max=4-1)
        clipped = np.uint8(np.digitize(image, np.arange(0, 256, int(256/self.max_level)))) - 1
        
        # compute the GLCM
        # f[i,j,d,theta] is the number of times that grey-level j occurs at a distance d and at an angle theta from grey-level i
        f = greycomatrix(clipped, [1], [0, np.pi/4, np.pi/2, 3*np.pi/4], levels=self.max_level,normed=True, symmetric=False)
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
    
    def congestion_recognition(self, frame, background, mask):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_masked = cv2.bitwise_and(frame, frame, mask = mask.copy())
        
        #background = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
        background_masked = cv2.bitwise_and(background, background, mask = mask.copy())
        
        E_frame_mean = self.GLCM(frame_masked)
        E_back_mean = self.GLCM(background_masked) 
               
        return round(np.abs(E_frame_mean - E_back_mean)/E_back_mean * 100, 2)


if __name__ == '__main__':
    print('hi')
    
    path = "/home/pi/From_pi/congestion/mask_ready.png"
    mask_image=cv2.imread(path,0)
    fgbg = cv2.bgsegm.createBackgroundSubtractorCNT()
    C_R = congestion_recognition(10, 32)
    
    video = "../Hakim01.mp4"
    video = "../Azmar_traffic.mp4"
    cap = cv2.VideoCapture(video)
    detection_scale = 4
    newH_1, newW_1 = 480/detection_scale, 864/detection_scale; 
    resolution_1=(newW_1, newH_1)
    
    sharpening_kernel = np.array([[-1,-1,-1,-1,-1], [-1,2,2,2,-1],
                                      [-1,2,8,2,-1],[-2,2,2,2,-1],
                                      [-1,-1,-1,-1,-1]])/8.0 # edge_enhance
    mask_image = cv2.resize(mask_image, resolution_1)
    frameID = 1
    while(cap.isOpened() and frameID<4000 ):
        try:
            ret, frame = cap.read()
            frameID +=1;
            #print(frameID)
            if (frameID % 3) == 0:
                #tic()
                frame_2 = cv2.resize(frame, resolution_1)
                
                fgmask = fgbg.apply(frame_2)
                backgroundImage = fgbg.getBackgroundImage()
                
                diff_percent = C_R.congestion_recognition(frame_2, backgroundImage,  mask_image)
                #toc()
                
                if 20 < diff_percent < 40:
                    print(diff_percent)#, np.mean(S_p))
                    
                    mask_3_channel = cv2.cvtColor(backgroundImage, cv2.COLOR_GRAY2BGR)
                    numpy_horizontal_concat = np.concatenate((frame_2, mask_3_channel), axis=1)
                    cv2.imshow('numpy_horizontal_concat', numpy_horizontal_concat)
                
                    #cv2.imshow("Frame2", frame);
                    #cv2.imshow("Frame", numpy_horizontal_concat); 
                    cv2.waitKey(100)
        except:
            cv2.destroyAllWindows()
            cap.release()
    cv2.destroyAllWindows()
    cap.release()
    
    
