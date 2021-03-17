
import ast
import math
import flask
import random
from flask import request
from flask import jsonify



app = flask.Flask(__name__)

assignment_manager = None


class Pixel:

    def __init__(self, top_left, vertical_direction, horizontal_direction, side_len):
        self.top_left = top_left
        self.v_dir = vertical_direction
        self.h_dir = horizontal_direction
        self.side_len = side_len
        # self.cam_pos = None

        self.initialize()

        self.num_hits = 0
        self.tri_1 = [self.top_left, self.top_right, self.bottom_right]
        self.tri_2 = [self.top_left, self.bottom_left, self.bottom_right]

    def initialize(self):
        # Start at top left. We need a top right, and bottom right/left point.

        self.top_right = self.travel_in_direction(self.top_left, self.h_dir, self.side_len, False)
        self.bottom_left = self.travel_in_direction(self.top_left, [self.v_dir[0] * -1, self.v_dir[1] * -1, self.v_dir[2] * -1], self.side_len, False)
        self.bottom_right = self.travel_in_direction(self.bottom_left, self.h_dir, self.side_len, False)

    def normalize(self, vector):
        vec_mag = math.sqrt((vector[0] * vector[0]) + (vector[1] * vector[1]) + (vector[2] * vector[2]))
        vec_n = (
            vector[0] / vec_mag,
            vector[1] / vec_mag,
            vector[2] / vec_mag
        )

        return vec_n

    def travel_in_direction(self, start_point, direction, distance, should_normalize=True):
        '''
            Given start_point, return a point that is 'distance' away from start_point in 'direction'
        '''

        if should_normalize:
            direction = self.normalize(direction)

        return [start_point[0] + distance * direction[0], start_point[1] + distance * direction[1],
                start_point[2] + distance * direction[2]]


class AssignmentManager():

    def __init__(self, search_for_sum):
        self.square_solution_assignments = []
        self.square_solutions = []
        self.intersect_assignments = []
        self.intersect_solutions = []
        self.intersect_squares = []

        self.active_assignments = {}
        self.sum = search_for_sum

        # camera properties TODO add as parameters.
        self.lookat = [0,0,0]
        self.resolution = [2048, 2048]
        self.pixels = []

        pos = int(self.sum * .75)
        self.camera_position = [pos, pos, pos]

        A = [self.sum, 0, 0]
        B = [0, self.sum, 0]
        C = [0, 0, self.sum]

        mid_AB = self.midpoint(A, B)

        gradient = self.minus(C, mid_AB)

        self.up = self.normalize(gradient)

        self.dist = int(self.sum * .1)

        self.fov = [110, 110]


        # generate a list of all square numbers less than sum
        self.squares = []

        i = 0
        diff = 1
        while i < self.sum:
            self.squares.append(i)
            i += diff
            diff += 2

        self.initialize_square_solution_assignments()
        self.initialize_intersection_assignments()



    def initialize_square_solution_assignments(self):
        chunk_size = min((len((str(self.sum))) - 1) * 1000, int(self.sum/10), int(len(self.squares)/100))

        self.square_solution_assignments = [self.squares[i:i + chunk_size] for i in
                                            range(0, len(self.squares), chunk_size)]

        print("[AssignmentManager] - creating manager for sum: {}, with chunk size: {}. "
              "There are {} total assignments.".format(self.sum, chunk_size, len(self.square_solution_assignments)))
        print(self.square_solution_assignments)

    def initialize_intersection_assignments(self):
        # The plane should sit self.dist units away from the location of the camera.

        # first create a vector between the camera location and the lookat point
        l_at_vec = (
            self.lookat[0] - self.camera_position[0],
            self.lookat[1] - self.camera_position[1],
            self.lookat[2] - self.camera_position[2]
        )

        # normalize vector
        vec_n = self.normalize(l_at_vec)
        plane_center = self.travel_in_direction(self.camera_position, vec_n, self.dist)

        # Now that we have our center, we can use the fov specified in the camera options
        # to determine the boundary of our picture plane.

        # horizontal fov angle
        h_fov = self.fov[0]

        # vertical fov angle
        v_fov = self.fov[1]

        # find the boundary points.
        h_angle = h_fov / 2
        v_angle = v_fov / 2

        # horizontal boundary distance from center Soh Cah TOAAAAAAAH
        hbdfc = self.dist * math.tan(math.radians(h_angle))

        # vertical boundary distance from center
        vbdfc = self.dist * math.tan(math.radians(v_angle))

        # find horizontal unit vector for the plane. Vert unit vec is self.up
        horizontal_raw = self.cross(l_at_vec, self.up)
        h_unit = self.normalize(horizontal_raw)

        # These are the four corner points of the picture plane
        self.bounds = [
            # bottom left
            [plane_center[0] + (h_unit[0] * hbdfc) + (self.up[0] * vbdfc),
             plane_center[1] + (h_unit[1] * hbdfc) + (self.up[1] * vbdfc),
             plane_center[2] + (h_unit[2] * hbdfc) + (self.up[2] * vbdfc)],
            # top left
            [plane_center[0] + (h_unit[0] * hbdfc) - (self.up[0] * vbdfc),
             plane_center[1] + (h_unit[1] * hbdfc) - (self.up[1] * vbdfc),
             plane_center[2] + (h_unit[2] * hbdfc) - (self.up[2] * vbdfc)],
            # bottom right
            [plane_center[0] - (h_unit[0] * hbdfc) + (self.up[0] * vbdfc),
             plane_center[1] - (h_unit[1] * hbdfc) + (self.up[1] * vbdfc),
             plane_center[2] - (h_unit[2] * hbdfc) + (self.up[2] * vbdfc)],
            # top right
            [plane_center[0] - (h_unit[0] * hbdfc) - (self.up[0] * vbdfc),
             plane_center[1] - (h_unit[1] * hbdfc) - (self.up[1] * vbdfc),
             plane_center[2] - (h_unit[2] * hbdfc) - (self.up[2] * vbdfc)],
        ]
        # now that we have our bounds, we can create our pixels based on the resolution.
        # square res for now.

        length = vbdfc * 2
        width = hbdfc * 2

        side_len = length / self.resolution[0]

        start_point = self.bounds[1]  # top left boundary point
        for i in range(self.resolution[0]):
            line_start = None
            for j in range(self.resolution[0]):
                p = Pixel(start_point, h_unit, self.up, side_len)
                if j == 0:
                    line_start = p
                self.pixels.append(p)
                start_point = p.top_right
            start_point = line_start.bottom_left

        for p in self.pixels:
            self.intersect_squares.append([p.top_left,
                                           p.top_right,
                                           p.bottom_left,
                                            p.bottom_right])


    def cancel_assignment(self, container_id):
        if container_id in self.active_assignments:
            print("Canceling assignment for {}".format(container_id))
            assignment, type = self.active_assignments[container_id]

            del(self.active_assignments[container_id])

            if type == "square":
                self.square_solution_assignments.append(assignment)
            elif type == "intersect":
                for each in assignment:
                    self.square_solutions.append(each)
            else:
                print("Error, invalid type: {} requesting cancel".format(type))

            del()

    def get_square_solution_assignment(self, container_id):
        if container_id is None:
            return -1, None, None
        elif container_id in self.active_assignments:
            return -2, None, None
        elif len(self.square_solution_assignments) == 0:
            return -3, None, None

        print("Assignment Manager: Found {} total square solution assignments available".format(len(self.square_solution_assignments)))

        assignment = self.square_solution_assignments.pop(0)

        self.active_assignments[container_id] = assignment, "square"

        return assignment, self.sum, self.squares

    def finish_square_assignment(self, container_id, solutions):
        # remove active assignment
        print("AssignmentManager, clearing assignment for: {}".format(container_id))
        del (self.active_assignments[container_id])

        print("AssignmentManager, parsing {} solutions found: ".format(len(solutions), solutions))
        for solution in solutions:
            print("\t{}".format(solution))
            self.square_solutions.append(solution)

        print("Finished processing square solutions from {}".format(container_id))

        return ''



    def get_intersect_assignment(self, container_id):
        if container_id is None:
            return -1, None, None
        elif container_id in self.active_assignments:
            return -2, None, None
        elif len(self.square_solutions) == 0:
            if len(self.square_solution_assignments) > 0:
                return -4, None, None # wait
            else:
                return -3, None, None # exit


        chunk_size = 35

        assignment = []
        for _ in range(chunk_size):
            try:
                assignment.append(self.square_solutions.pop(0))
            except IndexError:
                break
        self.active_assignments[container_id] = assignment, "intersect"

        return assignment, self.camera_position, self.intersect_squares

    def finish_intersect_assignment(self, container_id, solution):
        self.intersect_solutions.append(solution)

        # remove active assignment
        del(self.active_assignments[container_id])

    def cross(self, a, b):
        c = [a[1] * b[2] - a[2] * b[1],
             a[2] * b[0] - a[0] * b[2],
             a[0] * b[1] - a[1] * b[0]]

        return c

    def midpoint(self, A, B):
        '''
        Return the midpoint between Points A and B
        '''

        return [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2, (A[2] + B[2]) / 2]

    def dot(self, a, b):
        return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])

    def minus(self, p1, p2):
        return [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]]

    def distance(self, p1, p2):
        x2mx1 = p2[0] - p1[0]
        y2my1 = p2[1] - p1[1]
        z2mz1 = p2[2] - p1[2]

        return abs(math.sqrt(x2mx1 ** 2 + y2my1 ** 2 + z2mz1 ** 2))

    def normalize(self, vector):
        vec_mag = math.sqrt((vector[0] * vector[0]) + (vector[1] * vector[1]) + (vector[2] * vector[2]))
        vec_n = (
            vector[0] / vec_mag,
            vector[1] / vec_mag,
            vector[2] / vec_mag
        )

        return vec_n

    def travel_in_direction(self, start_point, direction, distance, should_normalize=True):
        '''
            Given start_point, return a point that is 'distance' away from start_point in 'direction'
        '''

        if should_normalize:
            direction = self.normalize(direction)

        return [start_point[0] + distance * direction[0], start_point[1] + distance * direction[1],
                start_point[2] + distance * direction[2]]

@app.route('/', methods=['GET'])
def home():
    return "<h1>Square numbers are cool</h1><p>This is the central server for my distributed system. Why are you here?</p>"

@app.route('/square_assignment', methods=['POST']) # I recognize that POST here doesnt make sense, thinking that I can pass producer_id here as a query parameter.
def square_request_assignment():
    print("Hello!: {}".format(request))

    container_id = request.form['container_id']

    print("Square Solution Assignment requested by container: {}. ".format(container_id))

    assignment = assignment_manager.get_square_solution_assignment(container_id)
    print("\t Assigned: {}".format(assignment))

    if assignment[0] == -1:
        print('producer ids are required. Invalid producer ID: ' + container_id)
    if assignment[0] == -2:
        print('producer already has checked out an assignment')
    if assignment[0] == -3:
        print('There are no assignments left to give.')
    return jsonify({
        'assignment': assignment[0],
        'sum': assignment[1],
        'squares': assignment[2]
    })

@app.route('/finished_square_assignment', methods=['POST'])
def finish_square_assignment():
    container_id = request.form['container_id']
    solutions = ast.literal_eval(request.form['solutions'])

    print("debug: {}".format(request.form))

    print("Container: {} has come up with solutions: {}".format(container_id, solutions))

    assignment_manager.finish_square_assignment(container_id, solutions)

    return ''

@app.route('/intersect_assignment', methods=['POST']) # I recognize that POST here doesnt make sense, thinking that I can pass producer_id here as a query parameter.
def intersect_request_assignment():
    container_id = request.form['container_id']
    assignment = assignment_manager.get_intersect_assignment(container_id)
    if assignment[0] == -1:
        print('producer ids are required. Invalid producer ID: ' + container_id)
    if assignment[0] == -2:
        print('producer already has checked out an assignment')
    if assignment[0] == -3:
        print('There are no assignments left to give.')
    return jsonify({
        'assignment': assignment[0],
        'camera_position': assignment[1],
        'squares': assignment[2]
    })

@app.route('/finished_intersect_assignment', methods=['POST'])
def finish_intersect_assignment():
    container_id = request.form['container_id']
    solution = request.form['solution']

    assignment_manager.finish_intersect_assignment(container_id, solution)

    return ''

@app.route('/cancel_assignment', methods=['POST'])
def cancel_assignment():
    container_id = request.form['container_id']

    assignment_manager.cancel_assignment(container_id)

    return ''

@app.route('/processing_status', methods=['GET'])
def get_processing_status():
    return jsonify({
        'square_solution_assignments': assignment_manager.square_solution_assignments,
        'square_solutions': assignment_manager.square_solutions,
        'intersect_assignments': assignment_manager.intersect_assignments,
        'intersect_solutions': assignment_manager.intersect_solutions
    })


@app.route('/get_pixel_definitions', methods=['GET'])
def get_pixel_defs():

    ret = []
    for p in assignment_manager.pixels:
        ret.append({
            "top_left": p.top_left,
            "top_right": p.top_right,
            "bottom_left": p.bottom_left,
            "bottom_right": p.bottom_right,
            "vertical_direction": p.v_dir,
            "horizontal_direction": p.h_dir,
            "side_len": p.side_len,
            "num_hits": p.num_hits,
            "tri_1": p.tri_1,
            "tri_2": p.tri_2
        })


    return jsonify({
        'pixels': ret
    })


if __name__ == '__main__':

    sum = 10000213

    assignment_manager = AssignmentManager(sum)

    app.run(host='localhost', port=5010)