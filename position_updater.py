import json
import os
import numpy as np
from datetime import datetime
from nokov.nokovsdk import *
import sys
import time
import msgpack
import zmq
from marker_tracker import Tracker

CAMERA_LOCATION_FILE = os.path.join(os.path.dirname(__file__), 'camera_location.json')

ENABLE_PUB = False
PUB_PORT = 5556
PUB_TOPIC = b"mocap"


def load_camera_location(path=CAMERA_LOCATION_FILE):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        camera_loc = data['camera_loc']
        return np.array(camera_loc, dtype=float)
    except Exception as exc:
        print(f'Failed to load camera location from {path}: {exc}')

CAMERA_LOC = load_camera_location()

def get_frame_timestamp(frame_data):
    frame = frame_data.contents
    return frame.iTimeStamp

def get_frame_coords(frame_data):
    frame = frame_data.contents
    n_other_markers = frame.nOtherMarkers
    results = []
    for i in range(n_other_markers):
        results.append(list(frame.OtherMarkers[i]))
    return results

def remove_camera_marker(coords, threshold=50):
    if not coords:
        return coords
    distances = np.linalg.norm(np.array(coords) - CAMERA_LOC, axis=1)
    new_coords = [coord for coord, dist in zip(coords, distances) if dist >= threshold]
    return new_coords

class MarkerPosition(object):
    def __init__(self):
        self.client = PySDKClient()
        ver = self.client.PySeekerVersion()
        print('SeekerSDK Sample Client 2.4.0.3142(SeekerSDK ver. %d.%d.%d.%d)' % (ver[0], ver[1], ver[2], ver[3]))

        self.client.PySetVerbosityLevel(0)
        self.client.PySetMessageCallback(MarkerPosition.log_callback)
        self.client.PySetDataCallback(self.data_callback, None)
        ret = self.client.Initialize(bytes("10.1.1.198", encoding="utf8"))

        if ret != 0:
            print('MC_Connection_Error')
            sys.exit(-1)
        
        self.tracker = Tracker()

    def data_callback(self, mc_data, user_data):
        if mc_data is None:
            print('No_Data_This_Frame')
            return
                
        time_stamp = get_frame_timestamp(mc_data)
        coords = get_frame_coords(mc_data)
        coords = remove_camera_marker(coords)
        self.tracker.assign(time_stamp, coords)
    

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

    def get_position(self):
        return self.tracker.get()

def pprint(locs):
    if locs is None:
        return
    index = 0
    for loc in locs:
        print(index, end=', ')
        if loc is None:
            print('None')
        else:
            print(f'{loc[0]:.1f}, {loc[1]:.1f}, {loc[2]:.1f}')
        index += 1
        

def main():
    mp = MarkerPosition()
    date = datetime.now().strftime("%m%d")
    t = datetime.now().strftime("%H%M")
    log_path = f"./logs/{date}_{t}_mocap_log.txt"

    pub = None
    pub_ctx = None
    if ENABLE_PUB:
        pub_ctx = zmq.Context.instance()
        pub = pub_ctx.socket(zmq.PUB)
        pub.bind(f"tcp://*:{PUB_PORT}")

    with open(log_path, 'w') as logs:
        prev_time = time.time()
        while True:
            locs = mp.get_position()
            current_time = time.time()
            print(locs, file=logs)

            if ENABLE_PUB:
                ts, coords = next(iter(locs.items()))
                if ts is not None and all(x is not None for x in coords):
                    payload = {
                        "src": "mocap",
                        "markers": coords,
                        "timestamp": ts,
                    }
                    pub.send_multipart(
                        [PUB_TOPIC, msgpack.packb(payload, use_bin_type=True)]
                    )
            
            if current_time - prev_time >= 3.0:
                if locs is not None:
                    k = list(locs.keys())[0]
                    print(k)
                    pprint(locs[k])
                print('=====================================')
                prev_time = current_time
        
            time.sleep(0.01)

    if pub is not None:
        pub.close(0)
    if pub_ctx is not None:
        pub_ctx.term()


if __name__ == '__main__':
    time.sleep(11)
    main()
