#!/usr/bin/env python
# ch_v0r88
"""
Created on Mon Oct 28 10:36:19 2019

@author: pi
"""
import datetime

# Function to covert string to datetime 
def str_to_dateTime(datetime_str): 
    dateTime = datetime.datetime(*[int(item) for item in datetime_str.split('-')])
    return dateTime
    

def get_counter(r, cam_No, cnt_type):
    
    date = str_to_dateTime(str(r.get("date_today"))) # ch_v3r02 (added)
    now_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    now = str_to_dateTime(now_str)
    
    if date == now:
        r.incr(cam_No+'_counter_'+cnt_type) # increment the counter
        
    else:
        counter = 1
        r.set(cam_No+'_counter_'+cnt_type, counter) # reset the 
        r.set('date_today',now_str)
    

#test:
"""
import redis # ch_v3r02 (added)
#from check_date import get_counter

#---------------------------------------------------------------------------# 
# Redis: It is used for variable sharing on RAM instead of DataBase
#---------------------------------------------------------------------------# 
redis_host = "localhost" # ch_v3r02 (added)
redis_port = 6379 # ch_v3r02 (added)
redis_password = "" # ch_v3r02 (added)
r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True) # ch_v3r02 (added)

cam_No = 'Cam_1'
cnt_type = 'all'
get_counter(r, cam_No, cnt_type);
print('counter --> ',int(r.get(cam_No+'_counter_'+cnt_type)))
"""



