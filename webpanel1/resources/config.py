"""
Created on Apr 12, 2017

@author: sgoldsmith

Copyright (c) Steven P. Goldsmith

All rights reserved.
"""

import configparser #,cv2
import sys # ch_v0r90 (added)
if sys.version_info >= (3, 0): # ch_v0r90 (added to check python version)
    from . import settings as sett # ch_v0r90 (py3 change detect_utils --> .)
else:
    import settings as sett

class config(object):
    """Configuration class.
    
    This makes it easy to pass around app configuration.

    """   
    
    def __init__(self): #, fileName): # ch_v0r89 (fileName commented)
        
        """ # ch_v0r89 (commented)
        ''' Read configuration from INI file '''
        parser = configparser.SafeConfigParser()
        # Read configuration file
        parser.read(fileName) 
        
        # Set camera related data attributes
        self.camera = {'name' :  parser.get("camera", "name"),
                       'framePlugin' :  parser.get("camera", "framePlugin"),
                       'videoCaptureProperties' :  eval(parser.get("camera", "videoCaptureProperties")),
                       'url' :  parser.get("camera", "url"),
                       'socketTimeout' :  parser.getint("camera", "socketTimeout"),
                       'extraln' :  parser.getboolean("camera", "extraln"),
                       'resizeWidthDiv' :  parser.getint("camera", "resizeWidthDiv"),                       
                       'frameBufMax' :  parser.getint("camera", "frameBufMax"),
                       'fpsInterval' :  parser.getfloat("camera", "fpsInterval"),
                       'fps' :  parser.getint("camera", "fps")}
        """
        # ch_v0r89 (added)
        self.camera = {'name' :  sett.name,
                       'framePlugin' :  sett.framePlugin,
                       'videoCaptureProperties' :  eval(sett.videoCaptureProperties),
                       'socketTimeout' :  sett.socketTimeout,
                       'extraln' :  sett.extraln,
                       'resizeWidthDiv' :  sett.resizeWidthDiv,                       
                       'frameBufMax' :  sett.frameBufMax,
                       'fpsInterval' :  sett.fpsInterval,
                       'fps' :  sett.fps}
"""        
if __name__ == "__main__":
    camera = config("test.ini")        
    print( camera.camera)
"""
