#!python3
# router.py - router/ listens on configured port and sends updates to configured neighbors

import json
import socket
import sys
import time
from threading import Thread
from math import inf


class Server(Thread):
    # listen for server updates
    def __init__(self, rID):
        super(Server, self).__init__()
        self.rID = rID
        self.host = '127.0.0.1'
        self.config_data = get_config(self.rID)
        self.port = int(self.config_data['portListen'])
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.route_table = get_route_table(rID)
        self.static_table = get_route_table(rID)

    def run(self):
        self.server_socket.bind((self.host, self.port))
        self.timeout = {}

        for router in self.route_table:
            if self.route_table[router]['descr'] == 'n':
                self.timeout[router] = [time.time(), 'active']

        while True:
            data, client_address = self.server_socket.recvfrom(512)

            # lock self.routeTable
            message = json.loads(data.decode())

            for router in message:
                # router is itself
                if message[router]['descr'] == 's':
                    sender = router
                    break

            print(f'message: {sender}')
            
            self.eval_timeout(sender)
            self.compute_routes(message, sender)
            #unlock self.routeTable

    def compute_routes(self, n_table, sender):
        # distance vector algorithm
        dist = self.static_table[sender]['dist']  # configured distance from sender to neighbor

        for route in self.route_table:
            if route in self.timeout:
                if self.timeout[route][1] == 'inactive':
                    self.route_table[route]['dist'] = inf

        for dest in n_table:
            # don't compute your own route table
            if sender == self.rID:
                break
        
            # don't trust if this router is the next hop
            if n_table[dest]['nxtHop'] == self.rID:
                continue

            # add items not in route_table
            if dest not in self.route_table:
                self.route_table[dest] = {'dist': (dist + n_table[dest]['dist']), 'nxtHop': sender, 'descr': 'e'}


            # is route a neighbor?
            if dest in self.timeout:
                if self.timeout[dest][1] == 'active': 
                    # is route shorter than the current route?
                    if (n_table[dest]['dist'] + dist) < self.route_table[dest]['dist']:
                        # accept route
                        self.route_table[dest] = {'dist': (dist + n_table[dest]['dist']), 'nxtHop': sender, 'descr': 'e'}
                    # is original route shorter than the current route?
                    if self.static_table[dest]['dist'] < self.route_table[dest]['dist']:
                        # use original route
                        self.route_table[dest] = self.static_table[dest]
                # use original route from staticTable (assign infite dist) and continue
                else:
                    self.route_table[dest] = {'dist': inf, 'nxtHop': self.static_table[dest]['nxtHop'], 'descr': 'n'}

            else:
                # is destination unreachable?
                if n_table[dest]['dist'] == inf:
                    self.route_table[dest] = {'dist': inf, 'nxtHop': sender, 'descr': 'e'}
                # is proposed route shorter than current route?
                elif (n_table[dest]['dist'] + dist) < self.route_table[dest]['dist']:
                    # accept route
                    self.route_table[dest] = {'dist': (n_table[dest]['dist'] + dist), 'nxtHop': sender, 'descr': 'e'}

    def eval_timeout(self, sender):
        # reset sender clock
        # every time an n_table comes change to active/ reset clock

        if sender != self.rID:
            self.timeout[sender][0] = time.time()

        # check other entries - assign inactivity
        for entry in self.timeout:
            if time.time() > (self.timeout[entry][0] + 10):
                self.timeout[entry][1] = 'inactive'
            else:
                self.timeout[entry][1] = 'active'
        
        for route in self.route_table:
            next_hop = self.route_table[route]['nxtHop']
            if next_hop in self.timeout:
                if self.timeout[next_hop][1] == 'inactive':
                    self.route_table[route]['dist'] = inf

    def changeTable(self):
        global route_table
        route_table = self.route_table


class Client(Thread):
    # send routetable updates to neighbors
    def __init__(self, rID):
        super(Client, self).__init__()
        self.rID = rID
        self.config_data = get_config(self.rID)
        self.port = int(self.config_data['portSend'])
        self.host = '127.0.0.1'
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind((self.host, self.port))
        self.static_table = get_route_table(self.rID)

    def sendTable(self):
        
        global route_table
        for router in self.static_table:
            # send table to neighbors only
            if route_table[router]['descr'] == 'n' or 's':
                self.send_to(router)
            else:
                continue
        
    def send_to(self, nID):
        # send table to neighor
        server = (self.host, self.get_neighbor(nID))

        message = json.dumps(route_table)
        self.client_socket.sendto(message.encode(), server)

    def get_neighbor(self, nID):
        # get neightbor listening port
        return int(get_config(nID)['portListen'])


def get_config(rID):
    # retrieve configuration data for router
    config_file = f'configFiles/{rID}_config.json'
    with open(config_file, 'r') as f:
        data = json.load(f)

    return(data[rID]['configuration'])

def get_route_table(rID):
    # retrieve route table for router
    config_file = f'configFiles/{rID}_config.json'
    with open(config_file, 'r') as f:
        data = json.load(f)

    return(data[rID]['routeTable'])

def output(route_table):
    # print formatted output
    for route in route_table:
        print('{} | {} | {} | {}'.format(route, str(route_table[route]['dist']), route_table[route]['nxtHop'], route_table[route]['descr']))


if __name__ == '__main__':
    ##### START APP #####
    try:
        rID = sys.argv[1]
    except:
        rID = input('Router ID: ')


    route_table = get_route_table(rID)

    t1 = Server(rID)
    t2 = Client(rID)

    t2.start()
    t1.start()


    while True:
        output(route_table)
        t2.sendTable()
        t1.changeTable()
        time.sleep(5)