import argparse
import requests
import time
import uuid


SQUARE_ASSIGNMENT_ENDPOINT = '/square_assignment'
FINISHED_SQUARE_ASSIGNMENT_ENDPOINT = '/finished_square_assignment'
CANCEL_ENDPOINT = '/cancel_assignment'
DEFAULT_WAIT_TIME = 10 # seconds
STOP_RESPONSE = None # Not implemented


def validate_connection():
    pass

def start(server, wait_time=None):
    validate_connection()

    container_id = str(uuid.uuid4())

    while True:
        print("[{} - {}] looking for new assignment".format(container_id, "square_solver"))

        find_sum = None
        assignment = None
        squares = None
        while True:
            # Step 0:  poll server for next assignment
            payload = {"container_id": container_id}

            url = "http://" + server + SQUARE_ASSIGNMENT_ENDPOINT
            print("{} DEBUG url: {} - posting {}".format(container_id, url, payload))

            response = requests.post("http://" + server + SQUARE_ASSIGNMENT_ENDPOINT, data=payload)

            if response is None or not response.ok:
                print("[{} - {}] Unable to contact server: {}".format(container_id, "square_solver", response))
                time.sleep (wait_time if wait_time is not None else DEFAULT_WAIT_TIME)
                continue
            else:
                r_json = response.json()
                assignment = r_json['assignment']
                find_sum = r_json['sum']
                squares = r_json['squares']

                if assignment == -2:
                    print("Whoops, we already have an assignment? Cancel it.")
                    payload = {"container_id": container_id}
                    requests.post("http://" + server + CANCEL_ENDPOINT, data=payload)
                    continue
                if assignment == -3:
                    print("We're done! Exiting!" + str(assignment))
                    exit(0)
                elif assignment == -4:
                    print("Wait!")
                    time.sleep(wait_time if wait_time is not None else DEFAULT_WAIT_TIME)
                    continue

                break # We have received an assignment

        # Now we have our assignment, which is a list of square numbers and the sum we're looking for.

        print("[{} - {}] Start processing assignment {}: {}".format(container_id, "square_solver", type(assignment), assignment))
        solutions = []
        for a in assignment:
            for b in squares:
                ab = a+b
                for c in squares:
                    if ab+c == find_sum:
                        solutions.append([a, b, c])
                        break
                    elif ab+c > find_sum:
                        break

        print("[{}] finished assignment!".format(container_id))

        payload = {
            'container_id': container_id,
            'solutions': str(solutions)
        }
        url = "http://" + server + FINISHED_SQUARE_ASSIGNMENT_ENDPOINT
        print("[{}] Posting {} solutions: {}".format(container_id,  len(solutions), solutions))
        requests.post(url, data=payload)
        time.sleep(2) # Wait for server

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', type=str, required=True)
    args = parser.parse_args()

    server_address = args.server
    start(server_address)