#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 26 11:10:10 2019

@author: pi
"""

import threading
import time
from datetime import datetime

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.is_started = False
        wait_sec = self.get_diff_to_60();print("Please wait %s seconds" % str(wait_sec));
        time.sleep(wait_sec)        
        self.wait_ind = 0
        self.first_time = 0
        self.next_call = time.time()
        self.start()
        #self.first_start()
        
    
    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        
        if not self.is_running:
            
            if self.first_time == 0:
                self.first_time = 1
                next_run_time = 0
               
            else:
                self.next_call += self.interval
                next_run_time = self.next_call - time.time()
                    
            self._timer = threading.Timer(next_run_time, self._run)
            self._timer.start()
            self.is_running = True
            
            
    def stop(self):
        if self._timer:
            self._timer.cancel()
        self.is_running = False
        print("Timer Stopped")
        
    def get_diff_to_60(self):
        wait_sec = int(59 - datetime.now().second)
        return wait_sec
    

'''   
if __name__ == "__main__":
    def find_min_day_ind():
        now = datetime.now()
        seconds_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
        one_min_day_ind = int(seconds_since_midnight//60)
        #print("one_min_day_ind is %s :" % str(one_min_day_ind))
        return one_min_day_ind
    
    def get_minute():
        return datetime.datetime.now().minute
    
    ind = 1
    def hello(name):
        global rt
        
        one_min_day_ind = find_min_day_ind()
        #active_th = rt._timer.is_alive()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print ("%s %s. One_min_day_ind: %s" % (name,now, str(one_min_day_ind) ))
        
    def write_to_DB():
        #ind_min = find_min_day_ind()
        current_min = get_minute()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print ("Write on DB  @ %s and with index of %s" % (now, str(current_min) ))
       
    

    print ("starting     @ %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    if ind == 1:
        rt = RepeatedTimer(2, hello, "Hello World  @" ) # it auto-starts, no need of rt.start()
    else:
        rt = RepeatedTimer(60, write_to_DB)
    try:
        time.sleep(10000) # your long-running job goes here...
    finally:
        rt.stop() # better in a try/finally block to make sure the program ends!
        time.sleep(0.3)
        hello("Goodby World @")
'''