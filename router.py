#!python3
#router.py - router

import socket, json, sys, time
from threading import Thread
from math import inf

#used to listen for updates
class Server(Thread):
    def __init__(self, rID):
        super(Server, self).__init__()
        self.rID = rID
        self.host = '127.0.0.1'
        self.configData = getConfig(self.rID)
        self.port = int(self.configData['portListen'])
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.routeTable = getRouteTable(rID)
        self.staticTable = getRouteTable(rID)

    def run(self):
        self.serverSocket.bind((self.host, self.port))
        self.timeOut = {}

        for router in self.routeTable:
            if self.routeTable[router]['descr'] == 'n':
                self.timeOut[router] = [time.time(), 'active']

        while True:
            data, clientAddr = self.serverSocket.recvfrom(512)

            ## Lock self.routeTable ##
            message = json.loads(data.decode())

            #get sender
            for router in message:
                if message[router]['descr'] == 's':
                    sender = router
                    break

            print(f'message: {sender}')
            
            self.evalTimeout(sender)
            self.computeRoutes(message, sender)
            ## unlock self.routeTable ##

    #distanceVector algorithm
    def computeRoutes(self, nTable, sender):

        dist = self.staticTable[sender]['dist']  #  <----Original neighbor(sender) distance

        for route in self.routeTable:
            if route in self.timeOut:
                if self.timeOut[route][1] == 'inactive':
                    self.routeTable[route]['dist'] = inf

        for dest in nTable:
            #dont compute your own route table
            if sender == self.rID:
                break
        
            #don't trust if i'm the next hop
            if nTable[dest]['nxtHop'] == self.rID:
                continue

            #add items not in rTable          I1
            if dest not in self.routeTable:
                self.routeTable[dest] = {'dist': (dist + nTable[dest]['dist']), 'nxtHop': sender, 'descr': 'e'}


            #Is route a neighbor?
            if dest in self.timeOut:
                if self.timeOut[dest][1] == 'active': 
                    #Yes: Is the route shorter than the current route?
                    if (nTable[dest]['dist'] + dist) < self.routeTable[dest]['dist']:
                        #Yes: Accept route
                        self.routeTable[dest] = {'dist': (dist + nTable[dest]['dist']), 'nxtHop': sender, 'descr': 'e'}

                    #Yes: Is the original route shorter than the current route?
                    if self.staticTable[dest]['dist'] < self.routeTable[dest]['dist']:
                        #yes: use original route
                        self.routeTable[dest] = self.staticTable[dest]

                #No: Use original route from staticTable (assign infite dist) and continue
                else:
                    self.routeTable[dest] = {'dist': inf, 'nxtHop': self.staticTable[dest]['nxtHop'], 'descr': 'n'}

            else:
                #destination unreachable?
                if nTable[dest]['dist'] == inf:
                    self.routeTable[dest] = {'dist': inf, 'nxtHop': sender, 'descr': 'e'}
            
                #Is the route shorter than the current route?
                elif (nTable[dest]['dist'] + dist) < self.routeTable[dest]['dist']:
                    #Yes: Accept Route
                    self.routeTable[dest] = {'dist': (nTable[dest]['dist'] + dist), 'nxtHop': sender, 'descr': 'e'}


    #evaluate timeouts
    def evalTimeout(self, sender):
        #resent sender clock: every time an nTable comes- change to active/ reset clock
        if sender != self.rID:
            self.timeOut[sender][0] = time.time()

        #check other entries - assign inactivity
        for entry in self.timeOut:
            if time.time() > (self.timeOut[entry][0] + 10):
                self.timeOut[entry][1] = 'inactive'
            else:
                self.timeOut[entry][1] = 'active'
        
        for route in self.routeTable:
            nxtHop = self.routeTable[route]['nxtHop']
            if nxtHop in self.timeOut:
                if self.timeOut[nxtHop][1] == 'inactive':
                    self.routeTable[route]['dist'] = inf

    def changeTable(self):
        global routeTable
        routeTable = self.routeTable



#used to send updates
class Client(Thread):
    def __init__(self, rID):
        super(Client, self).__init__()
        self.rID = rID
        self.configData = getConfig(self.rID)
        self.port = int(self.configData['portSend'])
        self.host = '127.0.0.1'
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clientSocket.bind((self.host, self.port))
        self.staticTable = getRouteTable(self.rID)

    def sendTable(self):
        
        global routeTable
        for router in self.staticTable:
            #send table to neighbors only
            if routeTable[router]['descr'] == 'n' or 's':
                self.sendTo(router)
            else:
                continue
        

    def sendTo(self, nID):
        server = (self.host, self.getNeighbor(nID))

        message = json.dumps(routeTable)
        self.clientSocket.sendto(message.encode(), server)


    def getNeighbor(self, nID):
        return int(getConfig(nID)['portListen'])



#retrieve configData
def getConfig(rID):
    configFile = input('Enter configFile: ')
    #configFile = f'/Users/BillyBuehl/Dropbox/ITS_6250/finalProject/configFiles/{rID}_config.json'
    with open(configFile, 'r') as f:
        data = json.load(f)

    return(data[rID]['configuration'])

#retrieve routeTable
def getRouteTable(rID):
    configFile = input('Enter configFile: ')
    #configFile = f'/Users/BillyBuehl/Dropbox/ITS_6250/finalProject/configFiles/{rID}_config.json'
    with open(configFile, 'r') as f:
        data = json.load(f)

    return(data[rID]['routeTable'])

def output(rTable):
    for route in rTable:
        print('{} | {} | {} | {}'.format(route, str(rTable[route]['dist']), rTable[route]['nxtHop'], rTable[route]['descr']))


##### START APP #####
try:
    rID = sys.argv[1]
except:
    rID = input('Router ID: ')


routeTable = getRouteTable(rID)

t1 = Server(rID)
t2 = Client(rID)

t2.start()
t1.start()


while True:
    output(routeTable)
    t2.sendTable()
    t1.changeTable()
    time.sleep(5)