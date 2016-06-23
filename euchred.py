# This class allows for interaction with a euchred server.

import socket
import struct
import logging

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


    ###########################################################################
    #
    def __init__(self):
        self.server = "0.0.0.0"
        self.port = 0


    ###########################################################################
    #
    def status(self):
        info("")
        info("euchred client status: ")
        info("server: " + self.server)
        info("port  : " + str(self.port))


    ###########################################################################
    # this routine will connect to the game server
    #
    def join(self):
        # create the socket for connection to the server: we'll need this
        # for use in the rest of the object
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.server,self.port))

        # make and send a join message
        message = self.joinMessage("foo")
        self.printMessage(message)
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
            size, self.JOIN, 1, len(name), str.encode(name), 250, 222)

        # debug the message
        #self.printMessage(message)

        # return it
        return(message)


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
