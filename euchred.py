# This class allows for interaction with a euchred server.

import socket
import struct
import logging
import sys
import random
import string

from logging import warning as warn, log, debug, info, error, critical
from card import Card

class Euchred:
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
        self.port = 0
        self.playerhandle = 0
        self.gamehandle = 0
        self.team = 0

        # this tracks the data from the most recent state information
        self.state = {}
        self.state[0] = {}
        self.state[1] = {}
        self.state[2] = {}
        self.state[3] = {}

        # randomize that name!
        self.name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))

        # override the defaults if we were passed relevant arguments
        if 'server' in kwargs:
            self.server = kwargs['server']
        if 'port' in kwargs:
            self.port = kwargs['port']
        if 'name' in kwargs:
            self.name = kwargs['name']



    ###########################################################################
    #
    def status(self):
        info("")
        info(self.name + ": euchred client status: ")
        info(self.name + ": server: " + self.server)
        info(self.name + ": port  : " + str(self.port))
        info("")
        info(self.name + ": Name  : " + str(self.name))
        info(self.name + ": Player: " + str(self.playerhandle))
        info(self.name + ": Team  : " + str(self.team))
        info(self.name + ": Game  : " + str(self.gamehandle))
        info("")


    ###########################################################################
    # this routine will connect to the game server
    #
    def join(self):
        # create the socket for connection to the server: we'll need this
        # for use in the rest of the object
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.server,self.port))

        # make and send a join message
        message = self.joinMessage(self.name)
        #self.printMessage(message)
        self.s.send(message)


    ###########################################################################
    # this takes a name and returns a byte array for the ecuhre daemon JOIN
    # message
    #
    def joinMessage(self,name):
        # get the length of the name and use that length in the format strign
        namelen = len(name)
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
            len(name),
            str.encode(name),
            self.messageId['TAIL1'],
            self.messageId['TAIL2'],
        )

        # debug the message
        #self.printMessage(message)

        # return it
        return(message)


    ###########################################################################
    # this reads a message from the server socket, and processes it
    #
    def parseMessage(self):
        # we read  single int from the socket: this should represent the
        # length of the entire message
        (size,) = struct.unpack("!i",self.s.recv(4))

        # read the specified number of bytes from the socket
        bytes = self.s.recv(size)
        #info(self.name + ": len of bytes is " + str(len(bytes)))

        # decode the message identifier
        (id,) = struct.unpack_from("!i",bytes)
        info(self.name + ": message is: %s (%d)" % (self.messageName[id],id))

        # now we mung out a case switch on the message identifier
        if ( id == self.messageId['JOINACCEPT'] ):
            return(self.parseJoinAccept(bytes))
        elif ( id == self.messageId['JOINDENY'] ):
            return(self.parseJoinDeny(bytes))
        elif ( id == self.messageId['CHAT'] ):
            return(self.parseChat(bytes))
        elif ( id == self.messageId['STATE'] ):
            return(self.parseState(bytes))
        elif ( id == self.messageId['DEAL'] ):
            return(self.parseDeal(bytes))
        elif ( id == self.messageId['ORDEROFFER'] ):
            return(self.parseOrderOffer(bytes))
        else:
            return(self.badMessage(bytes))


    ###########################################################################
    # This routine parses a JOINACCEPT message
    #
    def parseJoinAccept(self, bytes):
        debug(self.name + ": parsing JOINACCEPT")
        #self.printMessage(bytes)

        # the format of a JOINACCEPT message is:
        #   <msg> : <msglen> <JOINACCEPT> <gh> <ph> <team> <tail>
        # where we've already read the msglen bytes
        (msg, gh, ph, team, tail1, tail2) = struct.unpack("!iiiiBB",bytes)

        # run some sanity checks
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.name + ": bad tail value in parseJoinAccept()")
            return(False)

        # ok, otherwise we carry on
        self.gamehandle   = gh
        self.playerhandle = ph
        self.team         = team


    ###########################################################################
    # This routine parses a JOINDENY message
    #
    def parseJoinDeny(self, bytes):
        debug(self.name + ": parsing JOINDENY")
        #self.printMessage(bytes)

        return(True)


    ###########################################################################
    # This routine parses a CHAT message
    #
    def parseChat(self, bytes):
        debug(self.name + ": parsing CHAT")
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
            error(self.name + ": bad tail value in parseChat()")
            return(False)

        # ok, log the chat
        info(self.name + ": received chat: " + chat)


    ###########################################################################
    # This routine parses a string component of a message: it expects
    # to be passed a bytes array beginning with the string length
    #
    def parseString(self, bytes):
        #debug(self.name + ": parsing string")
        #self.printMessage(bytes)

        # the format of a string is:
        #   <string> : <textlen> <text>
        (len,) = struct.unpack_from("!i",bytes)
        #info(self.name + ": string len: " + str(len))

        # now parse out the text of the string
        format = "!"+str(len)+"s"
        #info(self.name + ": format is "+format)
        (chat,) = struct.unpack_from(format,bytes[4:])
        #info(self.name + ": chat is: " + chat.decode("utf-8"))

        return(chat.decode("utf-8"))


    ###########################################################################
    # This routine parses a string component of a message: it expects
    # to be passed a bytes array beginning with the string length
    #
    def parseState(self, bytes):
        debug(self.name + ": parsing STATE")
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
        #            <creator>|<ordered>|<dealer>|<alone>|<defend>|<leader>|<maker>
        #            <playoffer>|<orderoffer>|<dropoffer>|<calloffer>|<defendoffer>
        #            <cardinplay> <passed>
        #                   : <boolean>
        #      <gamedata> : <ingame> <suspend> <holein> <hole> <trumpset> <trump>
        #                   <tricks> <score> <options>
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
        info("")
        offset += self.parseStateGame(bytes[4+offset:])

        # next we parse the cards, which may number 0 if we haven't been
        # dealt any yet
        info("")
        offset += self.parseStateCards(bytes[4+offset:])

        # check that we have a valid tail
        (tail1,tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.name + ": bad tail value in parseState()")
            return(False)

        return(True)


    ###########################################################################
    # This routine parses the player data of the <STATE> message
    #
    def parseStatePlayer(self, bytes):
        debug(self.name + ": parsing player STATE")
        offset = 0

        info("")
        offset += self.parseStatePlayerN(bytes[offset:],0)
        info("")
        offset += self.parseStatePlayerN(bytes[offset:],1)
        info("")
        offset += self.parseStatePlayerN(bytes[offset:],2)
        info("")
        offset += self.parseStatePlayerN(bytes[offset:],3)

        return offset


    ###########################################################################
    # This reads the N'th player state information
    #
    def parseStatePlayerN(self, bytes, n):
        debug(self.name + ": parsing player STATE for player %d" % (n))
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

        # if player state is 2 (ie. connected), then read the rest of the info
        if self.state[n]['state'] == 2:
            # get the player handle: not sure why I duped this, since the
            # handle is implicit in the order, but anyway...
            (ph,) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the name
            self.state[ph]['name'] = self.parseString(bytes[offset:])
            offset += 4+len(self.state[ph]['name'])
            info(self.name + ": player name is " + self.state[ph]['name'])

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
            (self.state[ph]['numcards'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the creator boolean
            (self.state[ph]['creator'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the ordered boolean
            (self.state[ph]['ordered'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the dealer boolean
            (self.state[ph]['dealer'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the alone boolean
            (self.state[ph]['alone'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the defend boolean
            (self.state[ph]['defend'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the leader boolean
            (self.state[ph]['leader'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the maker boolean
            (self.state[ph]['maker'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the playoffer boolean
            (self.state[ph]['playoffer'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the orderoffer boolean
            (self.state[ph]['orderoffer'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the dropoffer boolean
            (self.state[ph]['dropoffer'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the calloffer boolean
            (self.state[ph]['calloffer'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the defendoffer boolean
            (self.state[ph]['defendoffer'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # get the cardinplay boolean
            (self.state[ph]['cardinplay'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

            # if there is a card in play, read it
            if self.state[ph]['cardinplay'] == 1:
                (value,suit) = struct.unpack_from("!ii",bytes[offset:])
                offset += 8
                self.state[ph]['card'] = Card(value=value,suit=suit)

            # get whether they've passed or not
            (self.state[ph]['passed'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4

        else:
            info(self.name + ": no player for slot %d" % (n))

        return offset


    ###########################################################################
    # This routine parses the game data of the <STATE> message
    #
    def parseStateGame(self, bytes):
        debug(self.name + ": parsing game STATE")
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
            info(self.name + ": parsing hole card")
            (value,suit) = struct.unpack_from("!ii",bytes[offset:])
            self.state['hole'] = Card(value=value,suit=suit)
            info(self.name + ": hole card: " + self.state['hole'])
            offset += 8
        else:
            info(self.name + ": no hole card to parse")

        # read whether trump has been set
        (self.state['trumpset'],) = struct.unpack_from("!i",bytes[offset:])
        offset += 4

        # if it has, read the trump suit
        if self.state['trumpset'] == 1:
            info(self.name + ": parsing trump suit")
            (self.state['trump'],) = struct.unpack_from("!i",bytes[offset:])
            offset += 4
        else:
            info(self.name + ": no trump suit to parse")

        # and set the number of tricks for each team
        (tricks0,tricks1) = struct.unpack_from("!ii",bytes[offset:])
        offset += 8

        # set the tricks as an "ustricks" and "themtricks", to make things
        # easier to parse later
        if self.team == 0:
            self.state['ustricks']   = tricks0
            self.state['themtricks'] = tricks1
        else:
            self.state['ustricks']   = tricks1
            self.state['themtricks'] = tricks0

        # similarly, parse the score values into usscore and themscore
        (score0,score1) = struct.unpack_from("!ii",bytes[offset:])
        offset += 8

        # set the tricks as an "usscore" and "themscore", to make things
        # easier to parse later
        if self.team == 0:
            self.state['usscore']   = score0
            self.state['themscore'] = score1
        else:
            self.state['usscore']   = score1
            self.state['themscore'] = score0

        # and then read a bunch of options
        ( self.state['defend'], self.state['aloneonorder'], self.state['screw'],) \
            = struct.unpack_from("!iii",bytes[offset:])
        offset += 12

        return offset


    ###########################################################################
    # This reads the cards information in the state message
    #
    def parseStateCards(self, bytes):
        debug(self.name + ": parsing cards STATE")
        #self.printMessage(bytes)
        offset = 0

        # The cards data looks like this:
        #      <cards> : <numcards> <card1> .. <cardN>
        #        <cardN> : <value> <suit>

        # get the number of cards to be read
        (self.state['numcards'],) = struct.unpack_from("!i",bytes)
        offset += 4

        # if we have a non-zero number of cards, read them
        self.hand = set([])
        for i in range(self.state['numcards']):
            (value,suit) = struct.unpack_from("!ii",bytes[offset:])
            self.hand.add(Card(value=value,suit=suit))
            offset += 8

        # if we have a hand, print it
        if self.state['numcards'] > 0:
            self.printHand()
        else:
            info(self.name + ": no hand yet")

        return offset


    ###########################################################################
    # This routine parses a DEAL message
    #
    def parseDeal(self, bytes):
        debug(self.name + ": parsing DEAL")
        #self.printMessage(bytes)

        # the format of a DEAL message is:
        #   <msg> : <msglen> <DEAL> <tail>
        # it's really just a notification message, so check we have a valid
        # tail and otherwise do nothing

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.name + ": bad tail value in parseDeal()")
            return(False)

        return(True)


    ###########################################################################
    # This routine parses an ORDEROFFER message
    #
    def parseOrderOffer(self, bytes):
        debug(self.name + ": parsing ORDEROFFER")
        #self.printMessage(bytes)

        # the format of an ORDEROFFER message is:
        #   <msg> : <msglen> <ORDEROFFER> <ph> <tail>
        # it's really just a notification message, unless we're the <ph>
        (msg, ph) = struct.unpack_from("!ii",bytes)
        info(self.name + ": order is offered to %s (%d)" %
            (self.state[ph]['name'],ph))

        # check we have a valid tail
        (tail1, tail2) = struct.unpack("!BB",bytes[-2:])
        if tail1 != self.messageId['TAIL1'] or tail2 != self.messageId['TAIL2']:
            error(self.name + ": bad tail value in parseOrderOffer()")
            return(False)

        return(True)


    ###########################################################################
    # This routine parses a random bad message
    #
    def badMessage(self, bytes):
        debug(self.name + ": parsing bad message")
        self.printMessage(bytes)

        return(False)


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
    def printHand(self):
        string = ""
        for i in self.hand:
            string += " " + i

        info(self.name + ": hand: " + string)
