import json
import os
import sys
import time
from datetime import datetime
from threading import Lock
from nokov.nokovsdk import *

CAMERA_LOCATION_FILE = os.path.join(os.path.dirname(__file__), 'camera_location.json')
SDK_SERVER = bytes("10.1.1.198", encoding="utf8")


def get_frame_timestamp(frame_data):
    frame = frame_data.contents
    return frame.iTimeStamp


def get_frame_coords(frame_data):
    frame = frame_data.contents
    return [list(frame.OtherMarkers[i]) for i in range(frame.nOtherMarkers)]


class CameraLocationRecorder(object):
    def __init__(self, save_path=CAMERA_LOCATION_FILE):
        self.save_path = save_path
        self.lock = Lock()
        self.latest = None
        self.time_stamp = None

        self.client = PySDKClient()
        ver = self.client.PySeekerVersion()
        print('SeekerSDK Sample Client 2.4.0.3142(SeekerSDK ver. %d.%d.%d.%d)' % (ver[0], ver[1], ver[2], ver[3]))

        self.client.PySetVerbosityLevel(0)
        self.client.PySetMessageCallback(CameraLocationRecorder.log_callback)
        self.client.PySetDataCallback(self.data_callback, None)

        ret = self.client.Initialize(SDK_SERVER)
        if ret != 0:
            print('MC_Connection_Error')
            sys.exit(-1)

        print(f'Connected to motion capture server, writing camera location to {self.save_path}')

    def data_callback(self, mc_data, user_data):
        if mc_data is None:
            print('No_Data_This_Frame')
            return

        coords = get_frame_coords(mc_data)
        time_stamp = get_frame_timestamp(mc_data)

        if len(coords) == 0:
            print('Camera_Not_Detected_This_Frame')
            return

        if len(coords) != 1:
            print(f'Invalid_Marker_Count: expected 1, got {len(coords)}. Skipping update.')
            return

        camera_loc = list(coords[0])
        if len(camera_loc) != 3:
            print('Invalid_Camera_Location_Length')
            return

        with self.lock:
            self.latest = camera_loc
            self.time_stamp = time_stamp
            self._write_location(camera_loc, time_stamp)

    def _write_location(self, camera_loc, time_stamp):
        payload = {
            'camera_loc': [float(c) for c in camera_loc],
            'time_stamp': int(time_stamp),
            'updated_at': datetime.now().astimezone().isoformat()
        }

        with open(self.save_path, 'w') as f:
            json.dump(payload, f)

        print(f'Camera location updated -> {payload["camera_loc"]}')

    @staticmethod
    def log_callback(log_level, log_msg):
        log_level_str = {
            1: "Error",
            2: "Warning",
            3: "Info",
            4: "Debug"
        }
        log_level_msg = log_level_str.get(log_level, "None")
        log_msg_value = cast(log_msg, c_char_p).value
        print(f"[{log_level_msg}] {log_msg_value}")


def main():
    recorder = CameraLocationRecorder()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Camera location recorder stopped')


if __name__ == '__main__':
    main()
