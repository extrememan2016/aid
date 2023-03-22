#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 10 14:08:56 2019

@author: pi
"""

# initialize Redis connection settings
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

name = 'test'

videoCaptureProperties = '((cv2.CAP_PROP_FRAME_WIDTH, 864), (cv2.CAP_PROP_FRAME_HEIGHT, 480))'

# Frame grabber class:
#
# your_app.mjpegclient  = mjpegclient wrapper
# your_app.videocapture = OpenCV cv2.VideoCapture wrapper

framePlugin =  'your_app.videocapture' #'your_app.client_capture' #  ch_v0r90 ('your_app.videocapture' -->  'your_app.client_capture')


# Socket timeout in seconds (only used for mjpegclient)
# Use socketTimeout = 0 to leave default value intact.

socketTimeout = 10

# Set to True for mjpg_streamer since it has an extra readline for some reason
# after reading chunk headers.

extraln = False

# Use to resize image for better detection/performance
#
resizeWidthDiv = 640
#
# FPS sample interval in seconds (how often to calculate FPS for debug logging).
#
# This is also the frequency the health check runs if enabled. 
#
fpsInterval = 5.0
#
# Camera FPS. Set to 0 to use frame plugin FPS.
#
fps = 0
#
# Maximum frame buffer
#
frameBufMax = 1000