#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat May 25 15:20:01 2019

@author: pi
"""
import requests as req

class get_http_cam_GetPost(object):
    def __init__(self,IP_address, url, cam_user,cam_pass):
        """Initialize variables
        Args:
            URL:'192.168.1.201/cgi-bin/dido/getdo.cgi?do0'
        Return:
            None
        """
        self.user=cam_user
        self.cam_pass=cam_pass
        self.url=url
        self.IP_address = IP_address
        self.URL=('http://'+self.user+':'+self.cam_pass+'@'+self.IP_address+self.url)
        
        
    def request(self):
        r = req.get(url = self.URL)
        
        s1=r.text
        return s1#
case = 2
if case == 1:
    search_for = 'tampered'
    url = '/cgi-bin/dido/getdo.cgi?do0'
elif case ==2:
    search_for = 'focus_motor_range'
    url = '/cgi-bin/admin/remotefocus.cgi?function=getstatus'

IP_address = '192.168.1.210'
user = 'root'
password = 'raad123'
img_width = 1280 #pixel
Image_Sensor_width = 1/2.7 * 25.4 # mm (1/2.7 inch)

get_post = get_http_cam_GetPost(IP_address, url, user,password)
s1 = get_post.request()
print(s1)
if search_for =='tampered':
    s2 = "="
    value = int(s1[s1.index(s2) + len(s2):])
    print('tampered detecte:', value)
elif search_for =='focus_motor_range':
    searching_string = "remote_focus_focus_motor="
    for item in s1.split("\n"):
        if searching_string in item:
            print( item.strip(),  item.partition(searching_string)) 
            before_keyword, keyword, after_keyword =  item.partition(searching_string)
            remote_focus_focus_motor = (int(after_keyword.split()[0].replace("'", '')))
            focus_mm = 0.002787879*remote_focus_focus_motor + 2.8
            focus_pixel = focus_mm/Image_Sensor_width * img_width
            print(focus_mm, focus_pixel)
            