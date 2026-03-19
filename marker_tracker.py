import numpy as np
import winsound
import copy
from threading import Lock
import heapq

NUMBER_MARKERS = 12

class Tracker:
    def __init__(self, vis=False):
        self.index_coords_map = None  # 把上一帧的坐标作为分配标准
        self.coords_this_frame = None  # 当前帧的坐标
        self.time_stamp = None
        self.vis = vis
        self.lock = Lock()

    def assign(self, time_stamp, loc: list):
        self.lock.acquire()
        self.time_stamp = time_stamp

        if self.index_coords_map is None:
            if len(loc) != NUMBER_MARKERS:
                print(len(loc))
                winsound.MessageBeep()
            assert len(loc) == NUMBER_MARKERS
            self.index_coords_map = {i: c for i, c in enumerate(loc)}
            self.coords_this_frame = copy.deepcopy(loc)
        else:
            now_loc = copy.deepcopy(loc)
            dist = []
            ref_coords = np.array([self.index_coords_map[i] for i in range(NUMBER_MARKERS)])
            
            for i, loc in enumerate(now_loc):
                for j, prev_loc in enumerate(ref_coords):
                    assert len(loc) == 3
                    assert len(prev_loc) == 3

                    d = np.linalg.norm(np.array(loc) - np.array(prev_loc))
                    heapq.heappush(dist, (d, i, j))

            assigned_result = [None] * NUMBER_MARKERS
            used_i = [False] * len(now_loc)
            while len(dist) != 0:
                d, i, j = heapq.heappop(dist)
                if used_i[i]:
                    continue
                # i -> j
                if assigned_result[j] is None:
                    assigned_result[j] = now_loc[i]
                    self.index_coords_map[j] = now_loc[i]
                    used_i[i] = True
            self.coords_this_frame = copy.deepcopy(assigned_result)
        self.lock.release()

    def get(self):
        self.lock.acquire()
        coords = copy.deepcopy(self.coords_this_frame)

        result = {self.time_stamp: coords}
        self.lock.release()
        return result