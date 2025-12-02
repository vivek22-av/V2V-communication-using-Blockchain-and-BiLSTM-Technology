import csv
import socket
import threading
import time
import hashlib
import random
import os

RouteA = 22000
RouteB = 7000
RouteC = 40000
RouteD = 55000
RouteZ = 0

route_distances = {
    "RouteZ": (RouteZ, ("LocationZ",)),
    "RouteA": (RouteA, ("LocationA", "LocationB", "LocationC", "LocationD")),
    "RouteB": (RouteB, ("LocationE", "LocationF", "LocationG")),
    "RouteC": (RouteC, ("LocationH", "LocationI", "LocationJ", "LocationK", "LocationL")),
    "RouteD": (RouteD, ("LocationM", "LocationN", "LocationO", "LocationP", "LocationQ", "LocationR")),
}

class Vehicle:
    def __init__(self, owner, license_plate, port, blockchain_address):
        self.owner = owner
        self.license_plate = license_plate
        self.current_route = "RouteZ"
        self.current_location_index = 0
        self.last_move_time = time.time()
        self.static_time = random.randint(20, 150)
        self.total_time = random.randint(855, 2370)
        self.velocity = random.randint(8, 23)
        self.visited_locations = []
        self.vehicle_is_in_traffic = True
        self.count = 0
        self.previous_hash = "0" * 64
        self.stake = 0
        self.port = port
        self.blockchain_address = blockchain_address
        self.running = True

    def compute_hash(self):
        vehicle_string = f"{self.owner}{self.license_plate}{self.current_route}{self.current_location_index}{self.static_time}{self.total_time}{self.velocity}{self.previous_hash}".encode()
        return hashlib.sha256(vehicle_string).hexdigest()

    def move_to_next_location(self):
        locations = route_distances[self.current_route][1]
        if self.current_location_index < len(locations) - 1:
            self.current_location_index += 1
        else:
            self.current_location_index = 0
            self.update_route()

    def get_current_location(self):
        locations = route_distances[self.current_route][1]
        return locations[self.current_location_index]

    def complete_route(self):
        locations = route_distances[self.current_route][1]
        return set(self.visited_locations) == set(locations)

    def update_route(self):
        possible_routes = [route for route in route_distances.keys() if route != "RouteZ"]
        self.current_route = random.choice(possible_routes)
        self.visited_locations = []
        self.current_location_index = 0
        self.update_stake()
        print(f"Updated route for {self.license_plate} to {self.current_route}")

    def update_stake(self):
        if self.complete_route():
            self.stake += 1

    def send_location_update(self):
        while self.running:
            current_location = self.get_current_location()
            message = f"UPDATE_LOCATION,{self.owner},{current_location}"
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect(self.blockchain_address)
                client_socket.send(message.encode())
                print(f"Sent location update for {self.license_plate}: {current_location}")
            except ConnectionRefusedError:
                print(f"Connection refused for vehicle: {self.license_plate}. Server may not be running.")
            except Exception as e:
                print(f"Error sending location update for {self.license_plate}: {e}")
            finally:
                client_socket.close()
            time.sleep(5)

    def stop(self):
        self.running = False

class Block:
    def __init__(self, index, previous_hash, timestamp, vehicles, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.vehicles = vehicles
        self.nonce = nonce

    def compute_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{self.vehicles}{self.nonce}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, difficulty):
        self.nonce = 0
        hash_value = self.compute_hash()
        while not hash_value.startswith("0" * difficulty):
            self.nonce += 1
            hash_value = self.compute_hash()
        return hash_value

class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = []
        self.current_vehicles = {}
        self.time_limit = 100
        self.difficulty = difficulty
        self.create_block(previous_hash='1')
        self.lock = threading.Lock()
        self.validators = []

    def create_block(self, previous_hash):
        block = Block(len(self.chain) + 1, previous_hash, time.time(), self.current_vehicles)
        mined_hash = block.mine_block(self.difficulty)
        block.previous_hash = mined_hash
        if self.validate_block(block):
            self.chain.append(block)
        else:
            print(f"Block {block.index} failed validation.")
        return block

    def register_vehicle(self, owner, license_plate, port):
        with self.lock:
            if owner not in self.current_vehicles:
                self.current_vehicles[owner] = Vehicle(owner, license_plate, port, ("localhost", 5000))
                self.validators.append(self.current_vehicles[owner])
                print(f"Vehicle registered: {license_plate}, Owner: {owner}")
                return True
            print(f"Vehicle already registered {license_plate}, Owner: {owner}.")
            return False

    def update_location(self, owner, new_location):
        with self.lock:
            if owner in self.current_vehicles:
                vehicle = self.current_vehicles[owner]
                expected_location = vehicle.get_current_location()

                if expected_location == new_location:
                    if new_location not in vehicle.visited_locations:
                        vehicle.visited_locations.append(new_location)

                vehicle.move_to_next_location()

                current_time = time.time()
                elapsed_time = current_time - vehicle.last_move_time
                vehicle.last_move_time = current_time

                vehicle.static_time = random.randint(20, 150)
                vehicle.total_time += int(elapsed_time + random.randint(855, 2370) + vehicle.static_time)

                distance = route_distances[vehicle.current_route][0]

                if vehicle.static_time >= self.time_limit:
                    print(f"Static time exceeded for vehicle: {vehicle.license_plate}, Time: {vehicle.static_time}, Velocity: {vehicle.velocity}")
                    vehicle.vehicle_is_in_traffic = True
                else:
                    vehicle.vehicle_is_in_traffic = False

                vehicle.velocity = distance / vehicle.total_time
                vehicle.count += 1
                self.save_vehicle_to_csv(owner, vehicle)
                return True
            return False

    def save_vehicle_to_csv(self, owner, vehicle):
        filename = fr'C:\Users\vivek\OneDrive\Desktop\Mhmm\data\vehicle_{owner}.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        file_exists = os.path.exists(filename)

        distance = route_distances[vehicle.current_route][0]
        current_location = vehicle.get_current_location()

        if vehicle.current_route == "RouteZ":
            print("Vehicle on RouteZ; no CSV data saved.")
            return

        previous_hash = vehicle.previous_hash
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists or os.path.getsize(filename) == 0:
                writer.writerow(["S.no", "Owner", "License Plate", "Current Route", "Location", "Distance (m)", "Time", "Static Time (s)", "Total Time (s)", "Velocity (m/sec)", "Previous Hash", "Hash", "vehicle is in traffic (y/n)"])

            hash_value = vehicle.compute_hash()
            writer.writerow([vehicle.count, owner, vehicle.license_plate, vehicle.current_route, current_location, distance, time.time(), vehicle.static_time, vehicle.total_time, vehicle.velocity, previous_hash, hash_value, vehicle.vehicle_is_in_traffic])

            vehicle.previous_hash = hash_value
            print(f"Data saved from vehicle: {vehicle.license_plate}, Current Route: {vehicle.current_route}, Location: {current_location}")

    def set_time_limit(self, new_time_limit):
        self.time_limit = new_time_limit
        print(f"Time limit set to: {new_time_limit} seconds.")

    def validate_block(self, block):
        total_stake = sum(vehicle.stake for vehicle in self.validators)
        stake_threshold = total_stake / len(self.validators) if self.validators else 0
        if stake_threshold > 0 and block.vehicles:
            selected_validator = random.choices(self.validators, weights=[v.stake for v in self.validators])[0]
            print(f"Block validated by vehicle: {selected_validator.license_plate}")
            return True
        return False

class P2PBlockchain(Blockchain):
    def __init__(self, difficulty=2):
        super().__init__(difficulty)
        self.network = set()
        self.listener_thread = None

    def add_peer(self, peer_address):
        self.network.add(peer_address)

    def remove_peer(self, peer_address):
        self.network.discard(peer_address)

    def synchronize_chain(self):
        print("Synchronizing blockchain with peers...")
        for peer in self.network:
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect(peer)

                request_message = "GET_BLOCKCHAIN"
                peer_socket.send(request_message.encode())

                response = peer_socket.recv(4096).decode()
                if response.startswith("BLOCKCHAIN:"):
                    received_chain = response[len("BLOCKCHAIN:"):].strip().splitlines()
                    received_blocks = [Block(int(block.split(',')[0]), block.split(',')[1], float(block.split(',')[2]), eval(block.split(',')[3]), int(block.split(',')[4])) for block in received_chain]

                    if len(received_blocks) > len(self.chain):
                        print(f"Received longer chain from {peer}. Validating blocks...")

                        for block in received_blocks:
                            if self.validate_block(block):
                                self.chain.append(block)
                                print(f"Block {block.index} validated and added.")
                            else:
                                print(f"Block {block.index} failed validation.")
                    else:
                        print(f"Received chain from {peer} is not longer than the local chain.")
                peer_socket.close()

            except socket.error as e:
                print(f"Socket error while synchronizing with {peer}: {e}")
            except Exception as e:
                print(f"Unexpected error during synchronization with {peer}: {e}")

    def start_peer_listener(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("localhost", 5000))
        server_socket.listen(5)
        print("Listening for peer connections...")

        while True:
            try:
                client_socket, addr = server_socket.accept()
                print(f"Accepted connection from {addr}")
                threading.Thread(target=self.handle_peer_connection, args=(client_socket,)).start()
            except OSError:
                break 

    def handle_peer_connection(self, client_socket):
        try:
            message = client_socket.recv(1024).decode()
            if message.startswith("UPDATE_LOCATION"):
                _, owner, new_location = message.split(",")
                if self.update_location(owner, new_location):
                    client_socket.send(b"Location updated")
                else:
                    client_socket.send(b"Location update failed")
            client_socket.close()
        except Exception as e:
            print(f"Error handling peer connection: {e}")

def main():
    blockchain = P2PBlockchain()
    blockchain.set_time_limit(100)

    n = random.randint(250, 300)
    with open('no(vehicles).txt', 'w') as file:
        file.write(f"{n}")
    vehicles = []
    for i in range(n):
        owner = f"0x{random.randint(100, 999)}"
        license_plate = f"ABC{random.randint(100, 999)}"
        port = random.randint(5000, 6000)
        blockchain.register_vehicle(owner, license_plate, port)
        vehicles.append(owner)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', 8000))

    for owner in vehicles:
        vehicle = blockchain.current_vehicles[owner] 
        threading.Thread(target=vehicle.send_location_update).start()

    listener_thread = threading.Thread(target=blockchain.start_peer_listener)
    listener_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    main()
