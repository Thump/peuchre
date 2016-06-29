# This class implements a card

import struct
import logging
import sys
import string

from logging import warning as warn, log, debug, info, error, critical

class Card:

    # these are the values, in numeric order
    TWO     =  2
    THREE   =  3
    FOUR    =  4
    FIVE    =  5
    SIX     =  6
    SEVEN   =  7
    EIGHT   =  8
    NINE    =  9
    TEN     = 10
    JACK    = 11
    QUEEN   = 12
    KING    = 13
    ACE     = 14

    # these are the suits, in alphabetic order
    CLUBS    = 0
    DIAMONDS = 1
    HEARTS   = 2
    SPADES   = 3


    ###########################################################################
    #
    def __init__(self, **kwargs):
        self.value = 0
        self.suit = -1

        # override the defaults if we were passed relevant arguments
        if 'value' in kwargs:
            if kwargs['value'] < 2 or kwargs['value'] > 14:
                error('bad value for card: %d' % (kwargs['value']))
            else:
                self.value = kwargs['value']
        if 'suit' in kwargs:
            if kwargs['suit'] < 0 or kwargs['suit'] > 4:
                error('bad suit for card: %d' % (kwargs['suit']))
            else:
                self.suit = kwargs['suit']


    ###########################################################################
    #
    def __str__(self):
        # set the value string
        if self.value < 11:
            value = str(self.value)
        elif self.value == 11:
            value = "J"
        elif self.value == 12:
            value = "Q"
        elif self.value == 13:
            value = "K"
        elif self.value == 14:
            value = "A"

        # set the suit
        if self.suit == 0:
            suit = "c"
        elif self.suit == 1:
            suit = "d"
        elif self.suit == 2:
            suit = "h"
        elif self.suit == 3:
            suit = "s"

        return(value+suit)
