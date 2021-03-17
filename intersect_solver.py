import argparse
import requests
import time
import uuid
import math


INTERSECT_ASSIGNMENT_ENDPOINT = '/intersect_assignment'
FINISHED_INTERSECT_ASSIGNMENT_ENDPOINT = '/finished_intersect_assignment'
CANCEL_ENDPOINT = '/cancel_assignment'
DEFAULT_WAIT_TIME = 10 # seconds
STOP_RESPONSE = None # Not implemented


def validate_connection():
    pass

def start(server, wait_time=None):
    validate_connection()

    container_id = str(uuid.uuid4())

    while True:


        cam_pos = None
        assignment = None
        squares = None
        while True:
            print("[{} {}] looking for new assignment".format(container_id, "Intersect_solver"))
            # Step 0:  poll server for next assignment
            payload = {"container_id": container_id}

            url = "http://" + server + INTERSECT_ASSIGNMENT_ENDPOINT
            response = requests.post(url, data=payload)

            if response is None or not response.ok:
                print("[{} - intersect_solver] Cannot reach server".format(container_id))
                time.sleep (wait_time if wait_time is not None else DEFAULT_WAIT_TIME)
                continue
            else:
                r_json = response.json()
                assignment = r_json['assignment']
                cam_pos = r_json['camera_position']
                squares = r_json['squares']

                if assignment == -2:
                    print("Whoops, we already have an assignment? Cancel it.")
                    payload = {"container_id": container_id}
                    requests.post("http://" + server + CANCEL_ENDPOINT, data=payload)
                    continue

                if assignment == -4:
                    print("There are no assignments yet. Wait!")
                    time.sleep(wait_time if wait_time is not None else DEFAULT_WAIT_TIME)
                    continue

                if assignment == -3:
                    print("We're done! Exiting.")
                    exit(0)
                break # We have received an assignment

        # Now we have our assignment, we can calculate which points intersect with each square.

        print("[{} {}] Beginning assignment: {}".format(container_id, "Intersect_solver", assignment))
        solution = {}

        for s in squares:
            solution["{}:{}:{}:{}".format(s[0], s[1], s[2], s[3])] = 0

        for point in assignment:

            # line from point to camera
            vec_n = normalize(minus(cam_pos, point))
            for s in squares:
                tri1 = [s[0], s[1], s[2]]
                tri2 = [s[1], s[2], s[3]]

                if ray_triangle_intersect(point, vec_n, tri1) or ray_triangle_intersect(point, vec_n, tri2):
                    solution["{}:{}:{}:{}".format(s[0], s[1], s[2], s[3])] = solution["{}:{}:{}:{}".format(s[0], s[1], s[2], s[3])] + 1


        print("[{}] finished assignment!".format(container_id))

        payload = {
            'container_id': container_id,
            'solution': solution
        }

        url = "http://" + server + FINISHED_INTERSECT_ASSIGNMENT_ENDPOINT
        requests.post(url, data=payload)
        time.sleep(1) # Wait for server

def cross(a, b):
    c = [a[1]*b[2] - a[2]*b[1],
         a[2]*b[0] - a[0]*b[2],
         a[0]*b[1] - a[1]*b[0]]

    return c


def midpoint(A, B):
    '''
    Return the midpoint between Points A and B
    '''

    return [(A[0] + B[0])/2, (A[1] + B[1])/2, (A[2] + B[2])/2]

def dot(a, b):
    return (a[0]*b[0]) + (a[1]*b[1]) + (a[2] * b[2])


def minus(p1, p2):
    return [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]]


def distance(p1, p2):
    x2mx1 = p2[0] - p1[0]
    y2my1 = p2[1] - p1[1]
    z2mz1 = p2[2] - p1[2]

    return abs(math.sqrt(x2mx1**2 + y2my1**2 + z2mz1**2))


def normalize(vector):
    vec_mag = math.sqrt((vector[0] * vector[0]) + (vector[1] * vector[1]) + (vector[2] * vector[2]))
    vec_n = (
        vector[0] / vec_mag,
        vector[1] / vec_mag,
        vector[2] / vec_mag
    )

    return vec_n


def ray_triangle_intersect(rayOrigin, rayVector, triangle, EPSILON=0.0000001):
    # Bastardized implementation of the "Möller–Trumbore intersection algorithm"
    # Shamelessly ripped from Wikipedia and translated into python

    p0 = triangle[0]
    p1 = triangle[1]
    p2 = triangle[2]

    edge1 = minus(p1, p0)
    edge2 = minus(p2, p0)

    h = cross(rayVector, edge2)

    a = dot(edge1, h)
    if a > -1 * EPSILON and a < EPSILON:
        return False  # This ray is parallel to this triangle.

    f = 1.0 / a

    s = minus(rayOrigin, p0)

    u = f * (dot(s, h))
    if u < 0.0 or u > 1.0:
        return False

    q = cross(s, edge1)
    v = f * dot(rayVector, q)
    if v < 0.0 or u + v > 1.0:
        return False

    # At this stage we can compute t to find out where the intersection point is on the line.
    t = f * dot(edge2, q)
    if t > EPSILON:  # ray intersection
        return True
    else:  # This means that there is a line intersection but not a ray intersection.
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', type=str, required=True)
    args = parser.parse_args()

    server_address = args.server
    start(server_address)