"""Redis Shared memory video capture module."""

import datetime
import struct
from typing import Optional, Tuple  # , Type

import cv2
import numpy as np
import redis  # type: ignore
from redis.client import Redis  # type: ignore


def connect_redis(redis_host: str, redis_port: int, redis_db: int = 0) -> Redis:
    """Connect to redis server."""
    return redis.Redis(host=redis_host, port=redis_port, db=redis_db)


class RedisShmem(object):
    """RedisShmem class."""

    def __init__(self, cam_name):        
        """Initialize the RedisShmem context."""
        host = "localhost"
        port = 6379
        db = 0
        self.__db = connect_redis(host, port, db)  # type: ignore
        Q_name: str = cam_name
        self.Q_name = Q_name + ":web"
        self.key = self.Q_name + ":Q"
        print("Key  ----------------->  ",self.key)


    def get_Q(self, timeout=None):
        # type: (Optional[int] ) -> bytes
        """Get item from the queue."""
        _, item_bytes = self.__db.blpop(self.key, timeout=timeout)
        return item_bytes

    @staticmethod
    def separate_image_timestamp(image_byte):
        # type: (bytes) -> Tuple[datetime.datetime, bytes, bool]
        """Separate image timestamp from image bytes."""
        # fake timestamp
        timestamp_str = "1970-01-00 00:00:00,00000"
        s = bool(image_byte is not None)
        if s:
            timestamp_str = image_byte[:26].decode()
            image_byte = image_byte[26:]
        timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
        return timestamp, image_byte, s

    @staticmethod
    def decodeFrame(encoded: bytes) -> np.ndarray:
        """Decode frame from bytes."""
        h, w = struct.unpack(">II", encoded[:8])
        decoded_image = np.frombuffer(encoded, dtype=np.uint8, offset=8).reshape(h, w, 3)
        return decoded_image

    def getFrame(self):
        # type: () -> Tuple[Optional[np.ndarray], bool, datetime.datetime]
        """Get frame from the queue."""
        time_img_bytes = self.get_Q(1)
        timestamp, img_bytes, grabbed = self.separate_image_timestamp(time_img_bytes)

        if grabbed:
            frame = self.decodeFrame(img_bytes)
        else:
            frame = None
        return frame, grabbed, timestamp


def videoLoop(camid):            # for use in app.py file!
    cam_name = "camid"
    cam_name = "CAM_01"
    shmem = RedisShmem(cam_name)
    while True:
        frame_web, grabbed, _ = shmem.getFrame()
        if grabbed:
            img = cv2.imencode('.jpg', frame_web)[1].tobytes()    
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')
            #print(frame_web.shape)
            #v2.imshow("Web View", frame_web)
            cv2.waitKey(1)

def main():
    cam_name = "CAM_01"
    shmem = RedisShmem(cam_name)
    while True:
        frame_web, grabbed, _ = shmem.getFrame()
        if grabbed:
            print(frame_web.shape)
            cv2.imshow("Web View", frame_web)
            cv2.waitKey(1)
if __name__ == "__main__":
    main()
