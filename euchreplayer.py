# This class implements an interface for a single player to the euchred
# server.  This class expects to be used as a base class for an actual
# player class that can be used with the peuchre program.  The real
# player class is expected to be called Player, it needs to sub-class
# EuchrePlayer, and needs to implement the following methods:
#
#  - decideOrderPass()
#  - decideDrop()
#  - decideDefend()
#  - decidePlayLead()
#  - decidePlayFollow()

import socket
import struct
import logging
import sys
import random
import string
import select

from logging import warning as warn, log, debug, info, error, critical
from card import Card

class EuchrePlayer:
    # this is the dict that maps message ID to message name: we also generate
    # a reverse mapping at the end
    messageId = {

        # sent by the client after connection, as well as the server's replies
        'JOIN'       : 123401 ,
        'JOINDENY'   : 123402 ,
        'JOINACCEPT' : 123403 ,

        # sent by the server to connected clients when the server is quitting */
        'SERVERQUIT' : 123404 ,

        # sent by the client to the server when the client is quitting */
        'CLIENTQUIT' : 123405 ,

        # sent if the server is full when the client tries to connect */
        'DECLINE' : 123406 ,

        # sent by the server when the client is about to be terminated */
        'KICK' : 123407 ,

        # the ID messages, request from client, responses from server */
        'ID'       : 123408 ,
        'IDACCEPT' : 123409 ,
        'IDDENY'   : 123410 ,

        # sent by the client when sending in a chat message, sent by the server
        # when broadcasting the chat message
        'CHAT' : 123411 ,

        # sent by server to clients after game state change: provides all info
        # needed by client to enter or resume game
        'STATE' : 123412 ,

        # sent as a request when the creator wants to kick another player */
        'KICKPLAYER' : 123413 ,
        'KICKDENY'   : 123414 ,

        # sent by a client setting options */
        'OPTIONS'     : 123415 ,
        'OPTIONSDENY' : 123416 ,

        # sent by the creator to start the game */
        'START'     : 123417 ,
        'STARTDENY' : 123418 ,

        # sent by the creator to end or reset the game and sent by the server
        # to tell the clients the game is ending */
        'END'     : 123419 ,
        'ENDDENY' : 123420 ,

        # sent by client as responses to an order offer */
        'ORDER'      : 123421 ,
        'ORDERALONE' : 123422 ,
        'ORDERPASS'  : 123423 ,
        'ORDERDENY'  : 123424 ,

        # sent by client to indicate dropped card, and the deny message */
        'DROP'     : 123425 ,
        'DROPDENY' : 123426 ,

        # sent by client as responses to a call offer */
        'CALL'      : 123427 ,
        'CALLALONE' : 123428 ,
        'CALLPASS'  : 123429 ,
        'CALLDENY'  : 123430 ,

        # sent by client as responses to a defend offer */
        'DEFEND'     : 123431 ,
        'DEFENDPASS' : 123432 ,
        'DEFENDDENY' : 123433 ,

        # sent by client as responses to a play offer */
        'PLAY'     : 123434 ,
        'PLAYDENY' : 123435 ,

        # flag messages sent by server */
        'TRICKOVER'   : 123436 ,
        'HANDOVER'    : 123437 ,
        'GAMEOVER'    : 123438 ,
        'PLAYOFFER'   : 123439 ,
        'DEFENDOFFER' : 123440 ,
        'CALLOFFER'   : 123441 ,
        'ORDEROFFER'  : 123442 ,
        'DROPOFFER'   : 123443 ,
        'DEAL'        : 123444 ,

        # these are the trailing bytes, to indicate the end of a message
        'TAIL1' : 250 ,
        'TAIL2' : 222 ,
    }

    # now generate the reverse mapping: thanks stack overflow!
    #messageName = {v: k for k,v in messageId.items()}
    messageName = {}
    for k, v in messageId.items():
        messageName[v] = k


    ###########################################################################
    #
    def __init__(self, **kwargs):
        self.server = "0.0.0.0"
        self.port = -1
        self.playerhandle = -1
        self.gamehandle = -1
        self.team = -1

        # this tracks the data from the most recent state information
        self.state = {}
        self.state[0] = {}
        self.state[1] = {}
        self.state[2] = {}
        self.state[3] = {}
        self.state['state'] = 0

        # initialize scores and tricks to 0
        self.state['usscore']   = 0
        self.state['themscore'] = 0
        self.state['ustricks']   = 0
        self.state['themtricks'] = 0

        # randomize that name!
        self.name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))

        # override the defaults if we were passed relevant arguments
        if 'server' in kwargs:
            self.server = kwargs['server']
        if 'port' in kwargs:
            self.port = kwargs['port']
        if 'name' in kwargs:
            self.name = kwargs['name']

        # if we were passed a record object, save it
        if 'record' in kwargs:
            self.record = kwargs['record']

        # we use this to ID hands in the log
        self.gcount = 0
        if 'gcount' in kwargs:
            self.gcount = kwargs['gcount']
        self.hcount = 0
        self.tcount = 0
        self.setId()


    ###########################################################################
    # This is a utility function to set the self.id string: it uses the
    # game, hand, and trick count variables to compose a self.id string
    # which is included in every log message, to make the log files easier
    # to parse.
    #
    def setId(self):
        self.id = \
            "%s g%dh%dt%d : " % (self.name,self.gcount,self.hcount,self.tcount)


    ###########################################################################
    # prints the score
    #
    def printScore(self):
        info(self.id+"score us:%d  them:%d" %
            (self.state['usscore'],self.state['themscore']) )


    ###########################################################################
    # print out the detailed state information
    #
    def status(self):
        info("")
        info(self.id+"My Status")
        info(self.id+"    server: " + self.server)
        info(self.id+"    port  : " + str(self.port))
        info("")
        info(self.id+"    Name  : " + str(self.name))
        info(self.id+"    Player: " + str(self.playerhandle))
        info(self.id+"    Team  : " + str(self.team))
        info(self.id+"    Game  : " + str(self.gamehandle))

        # just the game stuff
        self.gameStatus()

        # if we've got a hand state information, we should have all the
        # player information, so print that
        if 'hstate' in self.state:
            self.playerStatus()


    ###########################################################################
    # print out the game state information
    #
    def gameStatus(self):
        info("")
        info(self.id+"Game Status:")
        info(self.id+"    Score : %d vs %d"
            % (self.state['usscore'],self.state['themscore']))
        info(self.id+"    Tricks: %d vs %d"
            % (self.state['ustricks'],self.state['themtricks']))
        info(self.id+"    Game Started: %d" % (self.state['ingame']))
        info(self.id+"    Hand Status : %d" % (self.state['hstate']))
        info(self.id+"    options:")
        info(self.id+"        Can Defend Alone:       %d"
            % (self.state['defend']))
        info(self.id+"        Must Go Alone on Order: %d"
            % (self.state['aloneonorder']))
        info(self.id+"        Screw the Dealer:       %d"
            % (self.state['screw']))
        info(self.id+"    Number of cards: %d (%s)"
            % (self.state['numcards'], self.printHand(self.hand)) )
        info(self.id+"    Trump is Set: %d" % (self.state['trumpset']))
        if not self.state['holein']:
            info(self.id+"    Hole Card: not dealt")
        else:
            info(self.id+"    Hole Card: " + self.state['hole'])


    ###########################################################################
    # print out all the player state info
    #
    def playerStatus(self):
        for i in (0,1,2,3):
            # skip this player if their state isn't joined
            if self.state[i]['state'] != 2:
                continue

            # otherwise print all the info
            info("")
            info(self.id+"Player %d:" % (i))
            info(self.id+"    Name: %s" % (self.state[i]['name']))
            info(self.id+"    Team: %d" % (self.state[i]['team']))
            info(self.id+"    Dealer: %d" % (self.state[i]['dealer']))
            info(self.id+"    Ordered: %d" % (self.state[i]['ordered']))
            info(self.id+"    Passed: %d" % (self.state[i]['passed']))
            info(self.id+"    Made It: %d" % (self.state[i]['maker']))
            info(self.id+"    Alone: %d" % (self.state[i]['alone']))
            info(self.id+"    Lead: %d" % (self.state[i]['leader']))
            info(self.id+"    Creator: %d" % (self.state[i]['creator']))
            info(self.id+"    Offers:")
            info(self.id+"        Drop: %d" % (self.state[i]['dropoffer']))
            info(self.id+"        Order: %d"
                % (self.state[i]['orderoffer']))
            info(self.id+"        Call: %d" % (self.state[i]['calloffer']))
            info(self.id+"        Play: %d" % (self.state[i]['playoffer']))
            info(self.id+"        Defend: %d"
                % (self.state[i]['defendoffer']))

            # if the player has a card in play, show it
            if self.state[i]['cardinplay']:
                info(self.id+"    Card Played: " + self.state[i]['card'])
            else:
                info(self.id+"    Card Played: none")


    ###########################################################################
    # this routine will connect to the game server
    #
    def sendJoin(self):
        # create the socket for connection to the server: we'll need this
        # for use in the rest of the object
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.server,self.port))

        # get the length of the name and use that length in the format strign
        namelen = len(self.name)
        format = "!iiii" + str(namelen) + "sBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            self.messageId['JOIN'],
            1,
            len(self.name),
            str.encode(self.name),
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #self.printMessage(message)
        self.s.send(message)

        # set up a select with this socket
        inputs = [ self.s ]

        # wait for a message to come in
        readable, writable, exceptional = select.select(inputs, [], inputs)

        # we read  single int from the socket: this should represent the
        # length of the entire message
        (size,) = struct.unpack("!i",self.s.recv(4))

        # read the specified number of bytes from the socket
        bytes = self.s.recv(size)
        #info(self.id+"len of bytes is " + str(len(bytes)))

        # decode the message identifier
        (id,) = struct.unpack_from("!i",bytes)
        #info(self.id+"message is: %s (%d)" % (self.messageName[id],id))

        # now we mung out a case switch on the message identifier
        if ( id == self.messageId['JOINACCEPT'] ):
            info(self.id+"join successful")
            return self.parseJoinAccept(bytes)
        elif ( id == self.messageId['JOINDENY'] ):
            return self.parseJoinDeny(bytes)
        elif ( id == self.messageId['DECLINE'] ):
            return self.parseDecline(bytes)
        else:
            info(self.id+"unknown join response: %s (%d)" %
                (self.messageName[id],id))
            return self.badMessage(bytes)


    ###########################################################################
    # this routine will send the start message to the game server
    #
    def sendStart(self):
        # a start message looks like this:
        #  <msg> : <msglen> <START> <gh> <ph> <tail>

        # prep the format string
        format = "!iiiiBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            self.messageId['START'],
            self.gamehandle,
            self.playerhandle,
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # this routine will send an order message: it always orders up, as the
    # most basic strategy
    #
    def sendOrderPass(self):
        # a start message looks like this:
        #  <msg> : <msglen> <ORDER> <gh> <ph> <tail>

        # get the message we should send to the server: this should be one
        # of ORDER, ORDERALONE, or ORDERPASS
        message = self.decideOrderPass()

        # prep the format string
        format = "!iiiiBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            message,
            self.gamehandle,
            self.playerhandle,
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # this routine will randomly drop a card, in response to a drop offer
    #
    def sendDrop(self):
        # a start message looks like this:
        #  <msg> : <msglen> <DROP> <gh> <ph> <card> <tail>

        # call decideDrop() which should return a card to drop
        card = self.decideDrop()

        # prep the format string
        format = "!iiiiiiBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            self.messageId['DROP'],
            self.gamehandle,
            self.playerhandle,
            card.value,
            card.suit,
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # this routine will always decline a defend offer
    #
    def sendDefend(self):
        # a start message looks like this:
        #  <msg> : <msglen> <DEFEND> <gh> <ph> <card> <tail>

        # call the decideDefend() routine to determine if we should
        # defend alone or not
        message = self.decideDefend()

        # prep the format string
        format = "!iiiiBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            message,
            self.gamehandle,
            self.playerhandle,
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # this routine will play a card
    #
    def sendPlay(self):
        # a start message looks like this:
        #  <msg> : <msglen> <PLAY> <gh> <ph> <card> <tail>

        # are we leading?
        me = self.playerhandle
        leader = self.state[me]['leader']

        # if we're the leader, we can play anything
        if leader:
            self.sendPlayLead()
        else:
            self.sendPlayFollow()


    ###########################################################################
    # This plays a card to lead a new trick, for the moment it will play
    # anything
    #
    def sendPlayLead(self):
        # call decidePlayLead() to determine what card we should play as
        # a lead
        card = self.decidePlayLead()

        # remove the card from our hand
        self.removeCard(card)

        # prep the format string
        format = "!iiiiiiBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            self.messageId['PLAY'],
            self.gamehandle,
            self.playerhandle,
            card.value,
            card.suit,
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #info(self.id+"sending PLAY")
        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # This plays a card to follow in a new trick, for the moment it will
    # play a random (valid) card
    #
    def sendPlayFollow(self):
        # call decidePlayFollow() to determine the card we should follow
        # with: this assumes that the returned card is valid
        card = self.decidePlayFollow()

        # remove the card from our hand
        self.removeCard(card)

        # prep the format string
        format = "!iiiiiiBB"
        size = struct.calcsize(format)
        # reduce the size by 4, to leave out the space needed for the
        # leading size value
        size = size - 4

        # now generate a packed array of bytes for the message using that
        # format string
        message = struct.pack(format,
            size,
            self.messageId['PLAY'],
            self.gamehandle,
            self.playerhandle,
            card.value,
            card.suit,
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        #info(self.id+"sending PLAY")
        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # this reads a message from the server socket, and processes it
    #
    def parseMessage(self):
        # we read  single int from the socket: this should represent the
        # length of the entire message
        (size,) = struct.unpack("!i",self.s.recv(4))

        # read the specified number of bytes from the socket
        bytes = self.s.recv(size)
        #info(self.id+"len of bytes is " + str(len(bytes)))

        # decode the message identifier
        (id,) = struct.unpack_from("!i",bytes)
        #info(self.id+"message is: %s (%d)" % (self.messageName[id],id))

        # now we mung out a case switch on the message identifier
        if ( id == self.messageId['JOINACCEPT'] ):
            return self.parseJoinAccept(bytes)
        elif ( id == self.messageId['JOINDENY'] ):
            return self.parseJoinDeny(bytes)
        elif ( id == self.messageId['CHAT'] ):
            return self.parseChat(bytes)
        elif ( id == self.messageId['STATE'] ):
            return self.parseState(bytes)
        elif ( id == self.messageId['DEAL'] ):
            return self.parseDeal(bytes)
        elif ( id == self.messageId['STARTDENY'] ):
            return self.parseStartDeny(bytes)
        elif ( id == self.messageId['ORDEROFFER'] ):
            return self.parseOrderOffer(bytes)
        elif ( id == self.messageId['DROPOFFER'] ):
            return self.parseDropOffer(bytes)
        elif ( id == self.messageId['DEFENDOFFER'] ):
            return self.parseDefendOffer(bytes)
        elif ( id == self.messageId['DEFENDDENY'] ):
            return self.parseDefendDeny(bytes)
        elif ( id == self.messageId['PLAYOFFER'] ):
            return self.parsePlayOffer(bytes)
        elif ( id == self.messageId['PLAYDENY'] ):
            return self.parsePlayDeny(bytes)
        elif ( id == self.messageId['TRICKOVER'] ):
            return self.parseTrickOver(bytes)
        elif ( id == self.messageId['HANDOVER'] ):
            return self.parseHandOver(bytes)
        elif ( id == self.messageId['GAMEOVER'] ):
            return self.parseGameOver(bytes)
        else:
            info(self.id+"message is: %s (%d)" % (self.messageName[id],id))
            return self.badMessage(bytes)


    ###########################################################################
    # This routine parses a JOINACCEPT message
    #
    def parseJoinAccept(self, bytes):
        #debug(self.id+"parsing JOINACCEPT")
        #self.printMessage(bytes)

        # the format of a JOINACCEPT message is:
        #   <msg> : <msglen> <JOINACCEPT> <gh> <ph> <team> <tail>
        # where we've already read the msglen bytes
        (msg, gh, ph, team, tail1, tail2) = struct.unpack("!iiiiBB",bytes)

        # run some sanity checks
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseJoinAccept()")
            return False

        # ok, otherwise we carry on
        self.gamehandle   = gh
        self.playerhandle = ph
        self.team         = team

        return True


    ###########################################################################
    # This routine parses a JOINDENY message
    #
    def parseJoinDeny(self, bytes):
        #debug(self.id+"parsing JOINDENY")
        #self.printMessage(bytes)

        # the format of a JOINDENY message is:
        #   <msg> : <msglen> <JOINDENY> <string> <tail>
        # where the string explains why it was denied
        message = self.parseString(bytes[4:-2])

        info(self.id+"join denied: " + message)

        return(False)


    ###########################################################################
    # This routine parses a DECLINE message
    #
    def parseDecline(self, bytes):
        #debug(self.id+"parsing DECLINE")
        #self.printMessage(bytes)

        # the format of a DECLINE message is:
        #   <msg> : <msglen> <DECLINE> <string> <tail>
        # where the string explains why it was denied
        message = self.parseString(bytes[4:-2])

        info(self.id+"join declined: " + message)

        return(False)


    ###########################################################################
    # This routine parses a CHAT message
    #
    def parseChat(self, bytes):
        #debug(self.id+"parsing CHAT")
        #self.printMessage(bytes)

        # the format of a CHAT message is:
        #   <msg> : <msglen> <CHAT> <string> <tail>
        # where we've already read the msglen bytes
        # since the only content we have is the string, we slice the leading
        # <CHAT> (ie. 4 bytes) off the bytes array and pass it to a
        # specialized string parser
        chat = self.parseString(bytes[4:-2])

        # now we peel off the tail and make sure it's sane
        (tail1,tail2) = struct.unpack("!BB",bytes[-2:])

        # run some sanity checks
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseChat()")
            return False

        # ok, log the chat
        #info(self.id+"" + chat)

        return True


    ###########################################################################
    # This routine parses a string component of a message: it expects
    # to be passed a bytes array beginning with the string length
    #
    def parseString(self, bytes):
        #debug(self.id+"parsing string")
        #self.printMessage(bytes)

        # the format of a string is:
        #   <string> : <textlen> <text>
        (len,) = struct.unpack_from("!i",bytes)
        #info(self.id+"string len: " + str(len))

        # now parse out the text of the string
        format = "!"+str(len)+"s"
        #info(self.id+"format is "+format)
        (chat,) = struct.unpack_from(format,bytes[4:])
        #info(self.id+"chat is: " + chat.decode("utf-8"))

        return(chat.decode("utf-8"))


    ###########################################################################
    # This routine parses a string component of a message: it expects
    # to be passed a bytes array beginning with the string length
    #
    def parseState(self, bytes):
        #info(self.id+"parsing STATE")
        #self.printMessage(bytes)
        offset = 0

        # the format of a state is:
        #  <msg> : <msglen> <STATE> <statedata> <tail>
        #    <statedata> : <playersdata> <gamedata> <cards>
        #      <playersdata> : <p1> <p2> <p3> <p4>
        #        <pN> : <pstate> <pdata>
        #          <pstate> : {0|1|2} # unconnected, connected, joined
        #          <pdata> : if <pstate> == joined
        #                      <ph> <nmstring> <clstring> <hwstring> <osstring>
        #                      <cmtstring> <team> <numcards> <creator> <ordered>
        #                      <dealer> <alone> <defend> <leader> <maker>
        #                      <playoffer> <orderoffer> <dropoffer> <calloffer>
        #                      <defendoffer> <cardinplay> [<card>] <passed>
        #                    else
        #                      <NULL>
        #            <NULL> :  # no data
        #            <team> : {-1|0|1} # no team, team 0, or team 1
        #            <creator>|<ordered>|<dealer>|<alone>|<defend>|<leader>|
        #            <maker>|<playoffer>|<orderoffer>|<dropoffer>|<calloffer>|
        #            <defendoffer>|<cardinplay>|<passed>
        #                   : <boolean>
        #      <gamedata> : <ingame> <suspend> <holein> <hole> <trumpset>
        #                   <trump> <tricks> <score> <options>
        #        <ingame> : <boolean>
        #        <hstate> : <0|1|2|3|4> # pregame,hole,trump,defend,play
        #        <suspend> : <boolean>
        #        <holein> : <boolean> # true if hole card
        #        <hole> : <card> # only packed if <holein> true
        #        <card> : <value> <suit>
        #          <value> : {2|3|4|5|6|7|8|9|10|11|12|13|14}
        #          <suit> : {0|1|2|3}
        #        <trumpset> : <boolean> # true if trump set
        #        <trump> : <suit> # only packed if <trumpset> true
        #        <tricks> : <tricks0> <tricks1>
        #          <tricks0> : # tricks for team 0
        #          <tricks1> : # tricks for team 1
        #        <score> : <team0> <team1>
        #          <team0> : # score of team 0
        #          <team1> : # score of team 1
        #        <options> : <defend> <aloneonorder> <screw>
        #          <defend>|<aloneonorder>|<screw> : <boolean>
        #      <cards> : <numcards> <card1> .. <cardN>
        #        <cardN> : <value> <suit>

        # we pass a slice of the bytes array with the <STATE> removed;
        # parseStatePlayer() will return the parsed length, which we'll
        # then use to compose further slices to parse the game and cards
        offset += self.parseStatePlayer(bytes[4:])

        # next we parse the game state, for which we use the offset
        # returned from the parseStatePlayer() routine to build a new
        # slice of the bytes array
        #info("")
        offset += self.parseStateGame(bytes[4+offset:])

        # next we parse the cards, which may number 0 if we haven't been
        # dealt any yet
        #info("")
        offset += self.parseStateCards(bytes[4+offset:])

        # check that we have a valid tail
        (tail1,tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseState()")
            return False

        return True


    ###########################################################################
    # This routine parses the player data of the <STATE> message
    #
    def parseStatePlayer(self, bytes):
        #debug(self.id+"parsing player STATE")
        offset = 0

        #info("")
        offset += self.parseStatePlayerN(bytes[offset:],0)
        #info("")
        offset += self.parseStatePlayerN(bytes[offset:],1)
        #info("")
        offset += self.parseStatePlayerN(bytes[offset:],2)
        #info("")
        offset += self.parseStatePlayerN(bytes[offset:],3)

        return offset


    ###########################################################################
    # This reads the N'th player state information
    #
    def parseStatePlayerN(self, bytes, n):
        #debug(self.id+"parsing player STATE for player %d" % (n))
        offset = 0

        # The player data looks like this:
        #   <playersdata> : <p1> <p2> <p3> <p4>
        #     <pN> : <pstate> <pdata>
        #       <pstate> : {0|1|2} # unconnected, connected, joined
        #       <pdata> : if <pstate> == joined
        #                   <ph> <nmstring> <clstring> <hwstring> <osstring>
        #                   <cmtstring> <team> <numcards> <creator> <ordered>
        #                   <dealer> <alone> <defend> <leader> <maker>
        #                   <playoffer> <orderoffer> <dropoffer> <calloffer>
        #                   <defendoffer> <cardinplay> [<card>] <passed>
        #                 else
        #                   <NULL>
        #         <NULL> :  # no data
        #         <team> : {-1|0|1} # no team, team 0, or team 1
        #         <creator>|<ordered>|<dealer>|<alone>|<defend>|<leader>|<maker>
        #         <playoffer>|<orderoffer>|<dropoffer>|<calloffer>|<defendoffer>
        #         <cardinplay> <passed>
        #                : <boolean>
        #

        # pull player 0 state: 0 is unconnected, 1 is connected, 2 is joined;
        # if the value is 2, there will be further player data
        (self.state[n]['state'],) = struct.unpack_from("!i",bytes)
        offset += 4 # track the offset into the bytes array

        # if this is our state, promote it up
        if n == self.playerhandle:
            self.state['state'] = self.state[n]['state']

        # if player state is 2 (ie. connected), then read the rest of the info
        if self.state[n]['state'] == 2:
            # get the player handle: not sure why I duped this, since the
            # handle is implicit in the order, but anyway...
            (ph,) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the name
            self.state[ph]['name'] = self.parseString(bytes[offset:])
            offset += 4+len(self.state[ph]['name'])
            #info(self.id+"player name is " + self.state[ph]['name'])

            # get the client name
            self.state[ph]['clientname'] = self.parseString(bytes[offset:])
            offset += 4+len(self.state[ph]['clientname'])

            # get the client hardware
            self.state[ph]['hardware'] = self.parseString(bytes[offset:])
            offset += 4+len(self.state[ph]['hardware'])

            # get the OS
            self.state[ph]['os'] = self.parseString(bytes[offset:])
            offset += 4+len(self.state[ph]['os'])

            # get the comment
            self.state[ph]['comment'] = self.parseString(bytes[offset:])
            offset += 4+len(self.state[ph]['comment'])

            # get the team number
            (self.state[ph]['team'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the number of cards
            (self.state[ph]['numcards'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the creator boolean
            (self.state[ph]['creator'],) = \
                struct.unpack_from("!i",bytes[offset:])
            if ph == self.playerhandle:
                self.state['creator'] = self.state[ph]['creator']
            offset += 4

            # get the ordered boolean
            (self.state[ph]['ordered'],) = \
                struct.unpack_from("!i",bytes[offset:])
            if self.state[ph]['ordered'] == 1:
                self.state['orderer'] = ph
            offset += 4

            # get the dealer boolean
            (self.state[ph]['dealer'],) = \
                struct.unpack_from("!i",bytes[offset:])
            if self.state[ph]['dealer'] == 1:
                self.state['dealer'] = ph
            offset += 4

            # get the alone boolean
            (self.state[ph]['alone'],) = struct.unpack_from("!i",bytes[offset:])
            if self.state[ph]['alone'] == 1:
                self.state['aloner'] = ph
            offset += 4

            # get the defend boolean
            (self.state[ph]['defend'],) = \
                struct.unpack_from("!i",bytes[offset:])
            if self.state[ph]['defend'] == 1:
                self.state['defender'] = ph
            offset += 4

            # get the leader boolean
            (self.state[ph]['leader'],) = \
                struct.unpack_from("!i",bytes[offset:])
            if self.state[ph]['leader'] == 1:
                self.state['leader'] = ph
            offset += 4

            # get the maker boolean
            (self.state[ph]['maker'],) = struct.unpack_from("!i",bytes[offset:])
            if self.state[ph]['maker'] == 1:
                self.state['maker'] = ph
            offset += 4

            # get the playoffer boolean
            (self.state[ph]['playoffer'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the orderoffer boolean
            (self.state[ph]['orderoffer'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the dropoffer boolean
            (self.state[ph]['dropoffer'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the calloffer boolean
            (self.state[ph]['calloffer'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the defendoffer boolean
            (self.state[ph]['defendoffer'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the cardinplay boolean
            (self.state[ph]['cardinplay'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # if there is a card in play, read it
            if self.state[ph]['cardinplay'] == 1:
                (value,suit) = struct.unpack_from("!ii",bytes[offset:])
                offset += 8
                self.state[ph]['card'] = Card(value=value,suit=suit)

            # get whether they've passed or not
            (self.state[ph]['passed'],) = \
                struct.unpack_from("!i",bytes[offset:])
            offset += 4

        return offset


    ###########################################################################
    # This routine parses the game data of the <STATE> message
    #
    def parseStateGame(self, bytes):
        #debug(self.id+"parsing game STATE")
        #self.printMessage(bytes)
        offset = 0

        # The game data looks like this:
        #   <gamedata> : <ingame> <hstate> <suspend> <holein> <hole> <trumpset>
        #                <trump> <tricks> <score> <options>
        #     <ingame> : <boolean>
        #     <hstate> : <0|1|2|3|4> # pregame,hole,trump,defend,play
        #     <suspend> : <boolean>
        #     <holein> : <boolean> # true if hole card
        #     <hole> : <card> # only packed if <holein> true
        #     <card> : <value> <suit>
        #       <value> : {2|3|4|5|6|7|8|9|10|11|12|13|14}
        #       <suit> : {0|1|2|3}
        #     <trumpset> : <boolean> # true if trump set
        #     <trump> : <suit> # only packed if <trumpset> true
        #     <tricks> : <tricks0> <tricks1>
        #       <tricks0> : # tricks for team 0
        #       <tricks1> : # tricks for team 1
        #     <score> : <team0> <team1>
        #       <team0> : # score of team 0
        #       <team1> : # score of team 1
        #     <options> : <defend> <aloneonorder> <screw>
        #       <defend>|<aloneonorder>|<screw> : <boolean>

        # get the ingame boolean
        (self.state['ingame'],) = struct.unpack_from("!i",bytes[offset:])
        offset += 4

        # get the hand state: 0, 1, 2, 3, or 4, corresponding to a hand state
        # of pregame (hands haven't been dealt yet), hole (hole card ordering
        # is available), trump (arbitrary trump can be called), defend (defend
        # alone is on offer), play (game is underway)
        (self.state['hstate'],) = struct.unpack_from("!i",bytes[offset:])
        offset += 4

        # get the suspend state: this would be true only if the number of
        # players drops below 4
        (self.state['suspend'],) = struct.unpack_from("!i",bytes[offset:])
        offset += 4

        # get the hole card available state: this would be true if there is a
        # a hole card on offer
        (self.state['holein'],) = struct.unpack_from("!i",bytes[offset:])
        offset += 4

        # if there is a hole card on offer, read it
        if self.state['holein'] == 1:
            #info(self.id+"parsing hole card")
            (value,suit) = struct.unpack_from("!ii",bytes[offset:])
            self.state['hole'] = Card(value=value,suit=suit)
            offset += 8

        # read whether trump has been set
        (self.state['trumpset'],) = struct.unpack_from("!i",bytes[offset:])
        offset += 4

        # if it has, read the trump suit
        if self.state['trumpset'] == 1:
            (self.state['trump'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4
            #info("")
            #info(self.id+"trump is " + Card.suitName(self.state['trump']))

        # and set the number of tricks for each team
        (tricks0,tricks1) = struct.unpack_from("!ii",bytes[offset:])
        offset += 8

        # store the previous us and them tricks, so we can compute deltas
        prevus   = self.state['ustricks']
        prevthem = self.state['themtricks']

        # set the tricks as an "ustricks" and "themtricks", to make things
        # easier to parse later
        if self.team == 1:
            self.state['ustricks']   = tricks0
            self.state['themtricks'] = tricks1
        elif self.team == 2:
            self.state['ustricks']   = tricks1
            self.state['themtricks'] = tricks0

        # if the tricks have changed, compute the delta: either ustricks
        # has changed, or themtricks, but can't (shouldn't) be both
        if prevus != self.state['ustricks']:
            self.state['trickdelta'] = self.state['ustricks'] - prevus
        if prevthem != self.state['themtricks']:
            self.state['trickdelta'] = -1*(self.state['themtricks'] - prevthem)

        # similarly, parse the score values into usscore and themscore
        (score0,score1) = struct.unpack_from("!ii",bytes[offset:])
        offset += 8

        # store the previous us and them scores, so we can compute deltas
        prevus   = self.state['usscore']
        prevthem = self.state['themscore']

        # set the scores as an "usscore" and "themscore", to make things
        # easier to parse later
        if self.team == 1:
            self.state['usscore']   = score0
            self.state['themscore'] = score1
        elif self.team == 2:
            self.state['usscore']   = score1
            self.state['themscore'] = score0

        # if the score has changed, compute the delta: either usscore
        # has changed, or themscore, but can't (shouldn't) be both
        if prevus != self.state['usscore']:
            self.state['scoredelta'] = self.state['usscore'] - prevus
        if prevthem != self.state['themscore']:
            self.state['scoredelta'] = -1*(self.state['themscore'] - prevthem)

        # and then read a bunch of options
        (self.state['defend'],self.state['aloneonorder'],self.state['screw'],)\
            = struct.unpack_from("!iii",bytes[offset:])
        offset += 12

        return offset


    ###########################################################################
    # This reads the cards information in the state message
    #
    def parseStateCards(self, bytes):
        #debug(self.id+"parsing cards STATE")
        #self.printMessage(bytes)
        offset = 0

        # The cards data looks like this:
        #      <cards> : <numcards> <card1> .. <cardN>
        #        <cardN> : <value> <suit>

        # get the number of cards to be read
        (self.state['numcards'],) = struct.unpack_from("!i",bytes)
        offset += 4

        # if we have a non-zero number of cards, read them
        self.hand = list([])
        for i in range(self.state['numcards']):
            (value,suit) = struct.unpack_from("!ii",bytes[offset:])
            self.hand.append(Card(value=value,suit=suit))
            offset += 8

        return offset


    ###########################################################################
    # This routine parses a DEAL message: this message is sent after cards
    # for the deal are completed.  The state structure for the player
    # receiving the deal message should be fully populated
    #
    def parseDeal(self, bytes):
        debug("")
        debug(self.id+"parsing DEAL")
        #self.printMessage(bytes)

        # the format of a DEAL message is:
        #   <msg> : <msglen> <DEAL> <tail>
        # it's really just a notification message, so check we have a valid
        # tail and otherwise do nothing

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseDeal()")
            return False

        # at this point we've received and parsed the state message with
        # our hand details in it: we will want to know our original hand
        # later, to run stats on it, so we record the original hand now
        self.originalHand = self.hand

        return True


    ###########################################################################
    # This routine parses a STARTDENY message
    #
    def parseStartDeny(self, bytes):
        #debug(self.id+"parsing STARTDENY")
        #self.printMessage(bytes)

        # the format of a STARTDENY message is:
        #   <msg> : <msglen> <STARTDENY> <string> <tail>
        # where the string explains why it was denied
        message = self.parseString(bytes[4:-2])

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseStartDeny()")
            return False

        info("")
        info(self.id+"uh-oh, got a STARTDENY message: " + message)

        return False


    ###########################################################################
    # This routine parses an ORDEROFFER message
    #
    def parseOrderOffer(self, bytes):
        debug(self.id+"parsing ORDEROFFER")
        #self.printMessage(bytes)

        # the format of an ORDEROFFER message is:
        #   <msg> : <msglen> <ORDEROFFER> <ph> <tail>
        # it's really just a notification message, unless we're the <ph>
        (msg, ph) = struct.unpack_from("!ii",bytes)

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseOrderOffer()")
            return False

        # if the person offered the order is us, call sendOrderPass()
        if ph == self.playerhandle:
            self.sendOrderPass()

        return True


    ###########################################################################
    # This routine parses a DROPOFFER message
    #
    def parseDropOffer(self, bytes):
        #debug(self.id+"parsing DROPOFFER")
        #self.printMessage(bytes)

        # the format of an DROPOFFER message is:
        #   <msg> : <msglen> <DROPOFFER> <ph> <tail>
        # it's really just a notification message, unless we're the <ph>
        (msg, ph) = struct.unpack_from("!ii",bytes)

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseDropOffer()")
            return False

        # if the person offered the drop is us, call sendDrop()
        if ph == self.playerhandle:
            self.sendDrop()

        return True


    ###########################################################################
    # This routine parses a DEFENDOFFER message
    #
    def parseDefendOffer(self, bytes):
        #debug(self.id+"parsing DEFENDOFFER")
        #self.printMessage(bytes)

        # the format of an DEFENDOFFER message is:
        #   <msg> : <msglen> <DEFENDOFFER> <ph> <tail>
        # it's really just a notification message, unless we're the <ph>
        (msg, ph) = struct.unpack_from("!ii",bytes)

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseDefendOffer()")
            return False

        # if the person offered the defend is us, call sendDefend()
        if ph == self.playerhandle:
            info("")
            info(self.id+"declining defend alone")
            self.sendDefend()

        return True


    ###########################################################################
    # This routine parses a DEFENDDENY message
    #
    def parseDefendDeny(self, bytes):
        #debug(self.id+"parsing DEFENDDENY")
        #self.printMessage(bytes)

        # the format of a DEFENDDENY message is:
        #   <msg> : <msglen> <DEFENDDENY> <string> <tail>
        # where the string explains why it was denied
        message = self.parseString(bytes[4:-2])

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseDefendDeny()")
            return False

        info("")
        info(self.id+"uh-oh, got a DEFENDDENY message: " + message)

        return False


    ###########################################################################
    # This routine parses a PLAYOFFER message
    #
    def parsePlayOffer(self, bytes):
        #info(self.id+"parsing PLAYOFFER")
        #self.printMessage(bytes)

        # the format of an PLAYOFFER message is:
        #   <msg> : <msglen> <PLAYOFFER> <ph> <tail>
        # it's really just a notification message, unless we're the <ph>
        (msg, ph) = struct.unpack_from("!ii",bytes)
        #info("")
        #info(self.id+"got PLAYOFFER for %s" % (self.state[ph]['name']))

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseDropOffer()")
            return False

        # if the person offered the play is us, call sendPlay()
        if ph == self.playerhandle:
            self.sendPlay()

        return True


    ###########################################################################
    # This routine parses a PLAYDENY message
    #
    def parsePlayDeny(self, bytes):
        #debug(self.id+"parsing PLAYDENY")
        #self.printMessage(bytes)

        # the format of a PLAYDENY message is:
        #   <msg> : <msglen> <PLAYDENY> <string> <tail>
        # where the string explains why it was denied
        message = self.parseString(bytes[4:-2])

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parsePlayDeny()")
            return False

        info("")
        info(self.id+"uh-oh, got a PLAYDENY message: " + message)

        return False


    ###########################################################################
    # This routine parses a TRICKOVER message
    #
    def parseTrickOver(self, bytes):
        #debug(self.id+"parsing TRICKOVER")
        #self.printMessage(bytes)

        # the format of a TRICKOVER message is:
        #   <msg> : <msglen> <TRICKOVER> <tail>
        # ie. it's just an alert, so no need to parse anything out of it

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseTrickOver()")
            return False

        # we don't want to clutter the log by reporting all instances
        # of the trick over message, so we only print it for the maker
        if self.playerhandle == self.state['maker']:
            if self.state['trickdelta'] < 0: wl="lost"
            elif self.state['trickdelta'] > 0: wl="won"
            else: wl="bad bad bad"
            info(self.id+"trick is over, we %s, now %d to %d"
                % (wl,self.state['ustricks'],self.state['themtricks']))

        # increment the trick counter for the id string
        self.tcount += 1
        self.setId()

        return True


    ###########################################################################
    # This routine parses a HANDOVER message
    #
    def parseHandOver(self, bytes):
        #info("")
        #info(self.id+"parsing HANDOVER")
        #self.printMessage(bytes)

        # the format of a HANDOVER message is:
        #   <msg> : <msglen> <HANDOVER> <tail>
        # ie. it's just an alert, so no need to parse anything out of it

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseHandOver()")
            return False

        # if we were the maker, print some info and then record the score
        # delta for this hand
        if self.playerhandle == self.state['maker']:
            info("")
            info(self.id+"hand is over")
            self.printScore()
            info(self.id+"score delta: %d" % (self.state['scoredelta']))
            remap = self.record.addChand(
                self.originalHand,self.state['trump'],self.state['scoredelta'])
            info(self.id+"original hand: %s, trump: %s"
                % (self.printHand(self.originalHand),
                   Card.suitName(self.state['trump'])))
            info(self.id+"remapped hand: %s" % (remap))

        # increment the hand and trick counters for the id string
        self.hcount += 1
        self.tcount  = 0
        self.setId()

        return True


    ###########################################################################
    # This routine parses a GAMEOVER message
    #
    def parseGameOver(self, bytes):
        #info("")
        #info(self.id+"parsing GAMEOVER")
        #self.printMessage(bytes)

        # the format of a GAMEOVER message is:
        #   <msg> : <msglen> <GAMEOVER> <tail>
        # ie. it's just an alert, so no need to parse anything out of it

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.id+"bad tail value in parseHandOver()")
            return False

        # we don't want to clutter the log by reporting all instances
        # of the trick over message, so we only print it for the maker
        if self.playerhandle == self.state['maker']:
            info("")
            info(self.id+"game is over")
            self.printScore()
            info("")
            self.record.addGame()

        # we set the new game, hand, and trick values: this is really
        # mostly useless, since when the game is over, the player object
        # is going to deleted, but I think it's useful to do this for
        # completeness
        self.gcount += 1
        self.hcount  = 0
        self.tcount  = 0
        self.setId()

        # return False to indicate this client is finished
        return False


    ###########################################################################
    # This routine parses a random bad message
    #
    def badMessage(self, bytes):
        debug(self.id+"parsing bad message")
        self.printMessage(bytes)

        return False


    ###########################################################################
    # this takes a byte array and displays it as a series of bytes, useful
    # for decoding and debugging messages
    #
    def printMessage(self, message):
        print()
        print("decoded message:")
        hex_string = "".join("%02x " % b for b in message)
        print("hex: " + hex_string)
        print()


    ###########################################################################
    # this prints out all the cards in our hand
    #
    def printHand(self,hand):
        string = ""
        sep = ""
        for i in hand:
            string += sep + i
            sep = " "

        return string


    ###########################################################################
    # This takes a suit (the lead suit), and returns the set of cards from
    # the player's hand which can be played to legally follow it.  So if the
    # player has one or more cards of that suit, the returned set will contain
    # those cards, and if the player has no cards of that suit, then all
    def followCards(self):
        # begin by determining who the leader of the hand was
        leader = -1
        for i in (0,1,2,3):
            if self.state[i]['leader'] == 1:
                leader = i

        # set the trump and complimentary suits
        trumpsuit = self.state['trump']
        compsuit  = Card.suitComp(self.state['trump'])

        # set the leadsuit to the suit of the lead card, unless the lead
        # card is the left (ie. the J of compsuit), in which case set the
        # leadsuit to trump
        leadsuit  = self.state[leader]['card'].suit
        if leadsuit == compsuit and \
           self.state[leader]['card'].value == Card.nameValue("J"):
            leadsuit = trumpsuit

        # step through the player's hand: anything with the same suit
        # gets added to the playable cards list
        playable = list([])
        for card in self.hand:
            # put the suit and value of this card into temporary variables
            csuit  = card.suit
            cvalue = card.value

            # if the card value is a J and its suit is the compsuit (ie.
            # the complimentary suit of trump), then rewrite the suit as
            # trump
            if cvalue == Card.nameValue("J") and csuit == compsuit:
                csuit = trumpsuit

            # now if the possible-remapped csuit value matches the lead
            # suit, add the card to the playable hand
            if csuit == leadsuit:
                playable.append(card)

        # if we have no playable cards by suit, then we can play anything
        #info(self.id+"before playable cards: " + self.printHand(playable))
        if len(playable) == 0:
            playable = self.hand.copy()

        # print the hand
        info(self.id+"playable cards: " + self.printHand(playable)
            + ", lead: " + Card.suitName(leadsuit)
            + ", trump: " + Card.suitName(trumpsuit) )

        # generate some stats for follow requirements
        self.record.addFollow(len(self.hand),len(playable))

        return playable

    ###########################################################################
    # This takes a card and removes it from the player's hand: we need to
    # do it like this because sometimes we're working with a copy of the
    # card (ie. when we're using playable sets to follow), so we need to
    # remove by value and not by reference
    #
    def removeCard(self, card):
        # get the card value and suit
        value = card.value
        suit = card.suit

        # loop across all cards in the hand
        for card in self.hand:
            if card.value == value and card.suit == suit:
                self.hand.remove(card)
