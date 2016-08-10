# This encapsulates the data and objects to execute a game of euchre: it
# starts the server, creates and connects the players, and runs the game.
# The intention is that the mainline script will instantiate multiple of
# of these, each in its own thread, to increase hps.  The lock passed in
# with the init call is used to control access to the Record object, to
# track stats across all games.


from threading import Thread
import time
import socket
import subprocess
import select

import logging
from logging import warning as warn, log, debug, info, error, critical

class Game(Thread):

    ###########################################################################
    # initialize ourselves
    #
    def __init__(self,**kwargs):
        # initialize our superclass
        Thread.__init__(self)

        # decompose our kwargs to store the info 
        if 'gcount' in kwargs:
            self.gcount = kwargs['gcount']
        if 'lock' in kwargs:
            self.lock = kwargs['lock']
        if 'stats' in kwargs:
            self.stats = kwargs['stats']
        if 'record' in kwargs:
            self.record = kwargs['record']
        if 'team1' in kwargs:
            self.team1 = kwargs['team1']
        if 'team2' in kwargs:
            self.team2 = kwargs['team2']
        if 'timeout' in kwargs:
            self.timeout = kwargs['timeout']

        # get a port to use for the server
        self.port = self.getPort()


    ########################################################################### 
    # Since we're subclassing Thread, this is the routine used to run the
    # thread: it will start a server, instantiate the players, and then play
    # a game.  Once the game is done, it will exit, which will be seen by
    # the parent script and trigger it to be respawned (if more games are
    # needed).
    #
    def run(self):
        # start the server
        self.startServer()
        time.sleep(0.01)

        # now play the game
        self.playGame()

        # when playGame() returns, the game is ended, so we kill the server
        self.server.kill()


    ###########################################################################
    # This takes a port number and starts a server for this game
    #
    def startServer(self):
        # this starts the server:
        #  -m           : reduces the protocol
        #  -L /dev/null : eliminates the log file
        #  -p <port>    : sets the port number
        self.server = subprocess.Popen(["/usr/src/euchred/src/euchred",
            "-m","-L","/dev/null","-p","%d" % (self.port)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            )


    ###########################################################################
    # This returns true if all 4 players are in joined state, false otherwise
    #
    def allJoined(self, players):
        # default to true
        state = True

        # if any player has not joined, set to false
        for player in players:
            if 'state' not in player.state or player.state['state'] != 2:
                state = False

        return state


    ###########################################################################
    # This sends a start message to begin the game: it figures out who the
    # creator is and sends a message as that person
    #
    def sendStart(self, players):
        # figure out the creator
        for player in players:
            if player.state['creator'] == 1:
                player.sendStart()
                return


    ###########################################################################
    # This routine plays a game:
    #  - it instantiates 4 players and connects them to the server
    #  - it serves messages from the server to the players until a
    #    parseMessage() call returns false
    #  - then it exits
    #
    def playGame(self):
        # we use this to track active sockets and players
        inputs = []
        players = []

        # we track whether we've sent a start message or not
        started = 0

        # first we create up to 4 players and join them to the server: we
        # stagger the player joins by team, since the server will assign the
        # added players to team 0, then team 1, then team 0 again, then team
        # 1 again; after each join, we check if the join succeeded, and if so,
        # we add the player to the list of players and sockets
        player = self.team1(
            server="127.0.0.1", port=self.port, name="p0t1",
            record=self.record, gcount=self.gcount, lock=self.lock)
        if player.sendJoin():
            players.append(player)
            inputs.append(player.s)

        player = self.team2(
            server="127.0.0.1", port=self.port, name="p1t2",
            record=self.record, gcount=self.gcount, lock=self.lock)
        if player.sendJoin():
            players.append(player)
            inputs.append(player.s)

        player = self.team1(
            server="127.0.0.1", port=self.port, name="p2t1",
            record=self.record, gcount=self.gcount, lock=self.lock)
        if player.sendJoin():
            players.append(player)
            inputs.append(player.s)

        player = self.team2(
            server="127.0.0.1", port=self.port, name="p3t2",
            record=self.record, gcount=self.gcount, lock=self.lock)
        if player.sendJoin():
            players.append(player)
            inputs.append(player.s)

        # loop across our player sockets checking for input to process
        while players:
            readable, writable, exceptional = \
                select.select(inputs, [], [], self.timeout)

            # if there are no results in inputs, then we hit the timeout, which
            # probably means something went wrong (a client died?) and we should
            # just reset the whole thing
            if len(readable) == 0:
                error("uh-oh, hit timeout, terminating game")
                return

            # loop across each readable socket
            for player in players:
                if player.s in readable:
                    if not player.parseMessage():
                        players.remove(player)
                        inputs.remove(player.s)

            # Ugh, the server doesn't support a STARTOFFER message (yet), so
            # we need to detect when we have 4 connected players to know when
            # to start
            if players and self.allJoined(players):
                # this sends the start message: let the games begin!
                if players[0].state['hstate'] == 0 and started != 1:
                    info("")
                    info("server: everyone is joined, p%d sending start"
                        % (started))
                    self.sendStart(players)
                    started = 1

        # if we get here, all the clients have left, so we just return and a
        # new game will be triggered
        return


    ###########################################################################
    # This is just a utility routine that returns a free port: it's got
    # a minor race condition, since it's possible something else will
    # open and use the port between the time we choose and the time the
    # server opens it, but that's not really siginficant.
    #
    def getPort(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        #s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port
