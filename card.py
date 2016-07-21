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
    # these operators help automatic string conversions
    def __add__(self,other):
        return str(self) + other

    def __radd__(self,other):
        return other + str(self)

    def __str__(self):
        # set the value and suit string
        value = Card.valueName(self.value)
        suit = Card.suitName(self.suit)
        return(value+suit)


    ###########################################################################
    # This takes a suit value and returns the name of the suit
    #
    @staticmethod
    def suitName(index):
        if   index == 0: return "c"
        elif index == 1: return "d"
        elif index == 2: return "h"
        elif index == 3: return "s"


    ###########################################################################
    # This takes a suit value and returns the name of the suit
    #
    @staticmethod
    def nameSuit(index):
        if   index == "c": return 0
        elif index == "d": return 1
        elif index == "h": return 2
        elif index == "s": return 3


    ########################################################################### 
    # This takes a card value and returns the name of the card
    @staticmethod
    def valueName(index):
        if   index < 10:  return str(index)
        elif index == 10: return "T"
        elif index == 11: return "J"
        elif index == 12: return "Q"
        elif index == 13: return "K"
        elif index == 14: return "A"


    ########################################################################### 
    # This takes a card value and returns the name of the card
    @staticmethod
    def nameValue(index):
        if   index ==  "2": return  2
        elif index ==  "3": return  3
        elif index ==  "4": return  4
        elif index ==  "5": return  5
        elif index ==  "6": return  6
        elif index ==  "7": return  7
        elif index ==  "8": return  8
        elif index ==  "9": return  9
        elif index == "10": return 10
        elif index ==  "T": return 10
        elif index ==  "J": return 11
        elif index ==  "K": return 12
        elif index ==  "Q": return 13
        elif index ==  "A": return 14


    ###########################################################################
    # This takes a suit value and returns the complimentary trump suit,
    # ie. the suit of the same color as trump
    #
    @staticmethod
    def suitComp(index):
        if   index == 0: return 3
        elif index == 1: return 2
        elif index == 2: return 1
        elif index == 3: return 0
