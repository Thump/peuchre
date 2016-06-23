# This class allows for interaction with a euchred server.

import socket
import struct
import logging
import sys
import random
import string

from logging import warning as warn, log, debug, info, error, critical

class Euchred:

    # sent by the client after connection, as well as the server's replies
    JOIN=123401
    JOINDENY=123402
    JOINACCEPT=123403

    # sent by the server to connected clients when the server is quitting */
    SERVERQUIT=123404

    # sent by the client to the server when the client is quitting */
    CLIENTQUIT=123405

    # sent if the server is full when the client tries to connect */
    DECLINE=123406

    # sent by the server when the client is about to be terminated */
    KICK=123407

    # the ID messages, request from client, responses from server */
    ID=123408
    IDACCEPT=123409
    IDDENY=123410

    # sent by the client when sending in a chat message, sent by the server
    # when broadcasting the chat message
    CHAT=123411

    # sent by server to clients after game state change: provides all info
    # needed by client to enter or resume game
    STATE=123412

    # sent as a request when the creator wants to kick another player */
    KICKPLAYER=123413
    KICKDENY=123414

    # sent by a client setting options */
    OPTIONS=123415
    OPTIONSDENY=123416

    # sent by the creator to start the game */
    START=123417
    STARTDENY=123418

    # sent by the creator to end or reset the game and sent by the server
    # to tell the clients the game is ending */
    END=123419
    ENDDENY=123420

    # sent by client as responses to an order offer */
    ORDER=123421
    ORDERALONE=123422
    ORDERPASS=123423
    ORDERDENY=123424

    # sent by client to indicate dropped card, and the deny message */
    DROP=123425
    DROPDENY=123426

    # sent by client as responses to a call offer */
    CALL=123427
    CALLALONE=123428
    CALLPASS=123429
    CALLDENY=123430

    # sent by client as responses to a defend offer */
    DEFEND=123431
    DEFENDPASS=123432
    DEFENDDENY=123433

    # sent by client as responses to a play offer */
    PLAY=123434
    PLAYDENY=123435

    # flag messages sent by server */
    TRICKOVER=123436
    HANDOVER=123437
    GAMEOVER=123438
    PLAYOFFER=123439
    DEFENDOFFER=123440
    CALLOFFER=123441
    ORDEROFFER=123442
    DROPOFFER=123443
    DEAL=123444

    # these are the trailing bytes, to indicate the end of a message
    TAIL1=250
    TAIL2=222


    ###########################################################################
    #
    def __init__(self, **kwargs):
        self.server = "0.0.0.0"
        self.port = 0
        self.playerhandle = 0
        self.gamehandle = 0
        self.team = 0

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
        info("euchred client status: ")
        info("server: " + self.server)
        info("port  : " + str(self.port))
        info("")
        info("Name  : " + str(self.name))
        info("Player: " + str(self.playerhandle))
        info("Team  : " + str(self.team))
        info("Game  : " + str(self.gamehandle))
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
            size,self.JOIN,1,len(name),str.encode(name),self.TAIL1,self.TAIL2)

        # debug the message
        #self.printMessage(message)

        # return it
        return(message)


    ###########################################################################
    # this reads a message from the server socket, and processes it
    #
    def readMessage(self):
        # we read  single int from the socket: this should represent the
        # length of the entire message
        (size,) = struct.unpack("!i",self.s.recv(4))

        # read the specified number of bytes from the socket
        bytes = self.s.recv(size)
        info("len of bytes is " + str(len(bytes)))

        # decode the message identifier
        (message,) = struct.unpack_from("!i",bytes)
        info("message ID is: %d" % (message))

        # now we mung out a case switch on the message identifier
        if ( message == self.JOINACCEPT ):
            return(self.joinAccept(bytes))
        elif ( message == self.JOINDENY ):
            return(self.joinDeny(bytes))
        elif ( message == self.CHAT ):
            return(self.chat(bytes))
        elif ( message == self.STATE ):
            return(self.state(bytes))
        else:
            return(self.badMessage(bytes))


    ###########################################################################
    # This routine parses a JOINACCEPT message
    #
    def joinAccept(self, bytes):
        debug("parsing JOINACCEPT")
        #self.printMessage(bytes)

        # the format of a JOINACCEPT message is:
        #   <msg> : <msglen> <JOINACCEPT> <gh> <ph> <team> <tail>
        # where we've already read the msglen bytes
        (msg, gh, ph, team, tail1, tail2) = struct.unpack("!iiiiBB",bytes)

        # run some sanity checks
        if tail1 != self.TAIL1 or tail2 != self.TAIL2:
            error("bad tail value in joinAccept()")
            return(False)

        # ok, otherwise we carry on
        self.gamehandle   = gh
        self.playerhandle = ph
        self.team         = team


    ###########################################################################
    # This routine parses a JOINDENY message
    #
    def joinDeny(self, bytes):
        debug("parsing JOINDENY")
        #self.printMessage(bytes)

        return(True)


    ###########################################################################
    # This routine parses a CHAT message
    #
    def chat(self, bytes):
        debug("parsing CHAT")
        #self.printMessage(bytes)

        # the format of a CHAT message is:
        #   <msg> : <msglen> <CHAT> <string> <tail>
        # where we've already read the msglen bytes
        # since the only content we have is the string, we slice the leading
        # <CHAT> (ie. 4 bytes) off the bytes array and pass it to a
        # specialized string parser
        chat = self.string(bytes[4:-2])

        # now we peel off the tail and make sure it's sane
        (tail1,tail2) = struct.unpack("!BB",bytes[-2:])

        # run some sanity checks
        if tail1 != self.TAIL1 or tail2 != self.TAIL2:
            error("bad tail value in chat()")
            return(False)

        # ok, log the chat
        info("received chat: " + chat)


    ###########################################################################
    # This routine parses a string component of a message: it expects
    # to be passed a bytes array beginning with the string length
    #
    def string(self, bytes):
        debug("parsing string")
        #self.printMessage(bytes)

        # the format of a string is:
        #   <string> : <textlen> <text>
        (len,) = struct.unpack_from("!i",bytes)
        info("string len: " + str(len))

        # now parse out the text of the string
        format = "!"+str(len)+"s"
        info("format is "+format)
        (chat,) = struct.unpack_from(format,bytes[4:])
        #info("chat is: " + chat.decode("utf-8"))

        return(chat.decode("utf-8"))


    ###########################################################################
    # This routine parses a random bad message
    #
    def badMessage(self, bytes):
        debug("parsing bad message")
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
