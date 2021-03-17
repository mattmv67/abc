

import argparse
import requests
import time
import uuid
import ast
import math
from PIL import Image
import numpy as np



PROCESSING_STATUS_ENDPOINT = '/processing_status'
PIXEL_DEFS_ENDPOINT = '/get_pixel_definitions'
DEFAULT_WAIT_TIME = 35 # seconds
STOP_RESPONSE = None # Not implemented

class Pixel:

    def __init__(self, top_left, top_right, bottom_left, bottom_right, vertical_direction, horizontal_direction, side_len, num_hits, tri1, tri2):
        self.top_left = top_left
        self.top_right = top_right
        self.bottom_left = bottom_left
        self.bottom_right = bottom_right

        self.v_dir = vertical_direction
        self.h_dir = horizontal_direction
        self.side_len = side_len

        self.num_hits = num_hits
        self.tri_1 = tri1
        self.tri_2 = tri2



def validate_connection():
    pass

def write_image(pixels):

    resolution = 2048
    filename = "test.png"

    pic = []
    row = []
    for p in pixels:
        if len(row) < resolution:
            if p.num_hits > 0:
                row.append([255, 255, 255])
            else:
                row.append([0, 0, 0])
        else:
            pic.append(row.copy())
            row = []
            if p.num_hits > 0:
                row.append([255, 255, 255])
            else:
                row.append([0, 0, 0])

    pil_image = Image.fromarray(np.array(pic, dtype=np.uint8))
    pil_image.save(filename)



def start(server, wait_time=None):
    validate_connection()

    container_id = str(uuid.uuid4())

    print("[{} - {}] collecting pixel information".format(container_id, "create_image"))

    pixels = []
    while True:

        url = "http://" + server + PIXEL_DEFS_ENDPOINT
        response = requests.get(url)
        if response is None or not response.ok:
            time.sleep(10)
            continue
        else:
            r_json = response.json()
            raw_pixels = r_json['pixels']
            for p in raw_pixels:
                pixels.append(Pixel(
                    p['top_left'],
                    p['top_right'],
                    p['bottom_left'],
                    p['bottom_right'],
                    p['vertical_direction'],
                    p['horizontal_direction'],
                    p['side_len'],
                    p['num_hits'],
                    p['tri_1'],
                    p['tri_2']
                ))
            break

    print("[{0} - create_image] Collected: {1} pixels, resolution: {2}x{2}".format(container_id, len(pixels), int(math.sqrt(len(pixels)))))

    intersect_solutions = None

    while True:
        print("[{} - create_image] waiting for processing to complete...".format(container_id))
        # poll server to check if all assignments are complete
        url = "http://" + server + PROCESSING_STATUS_ENDPOINT
        response = requests.get(url)

        if response is None or not response.ok:
            time.sleep (wait_time if wait_time is not None else DEFAULT_WAIT_TIME)
            continue
        else:
            r_json = response.json()

            square_solution_assignments = ast.literal_eval(r_json['square_solution_assignments'])
            square_solutions = ast.literal_eval(r_json['square_solutions'])
            intersect_assignments = ast.literal_eval(r_json['intersect_assignments'])
            intersect_solutions = ast.literal_eval(r_json['intersect_solutions'])

            if len(square_solution_assignments) == 0 and len(square_solutions) == 0 and len(intersect_assignments) == 0:
                # There is no more work to be done!
                break
            else:
                # Work still in flight, sleep
                time.sleep(wait_time if wait_time is not None else DEFAULT_WAIT_TIME)
                continue
    print("[{} - create_image] Processing Complete! Producing image...")

    # cerate a map to reduce iterations!
    p_map = {}
    for p in pixels:
        p_map['{}:{}:{}:{}'.format(p.top_left, p.top_right, p.bottom_left, p.bottom_right)] = p

    for solution in intersect_solutions:
        for key, value in solution.items():
            pixel = p_map[key]
            pixel.num_hits += value

    write_image(pixels)




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', type=str, required=True)
    args = parser.parse_args()

    server_address = args.server
    start(server_address)