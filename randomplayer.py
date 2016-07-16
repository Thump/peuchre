# This class shows a simple implementation of a player class for peuchre:
#  - it inherits from EuchrePlayer
#  - it has a class called Player
#  - it implements the core Player methods:
#     - decideOrderPass)
#     - decideDrop)
#     - decideDefend)
#     - decidePlayLead)
#     - decidePlayFollow)

import random

from logging import warning as warn, log, debug, info, error, critical
from card import Card
from euchreplayer import EuchrePlayer

class Player(EuchrePlayer):

    ###########################################################################
    #
    def __init__(self, **kwargs):
        EuchrePlayer.__init__(self,**kwargs)


    ###########################################################################
    # this routine returns either ORDER, ORDERALONE, or PASS, depending on
    # what the client wishes to do with the hole card; at the moment, this
    # client always returns ORDER
    #
    def decideOrderPass(self):
        info("")
        info(self.name+": I will order " + self.state['hole']
            + " to " + self.state[ self.state['dealer'] ]['name'] )

        return self.messageId['ORDER']


    ###########################################################################
    # this routine is called when the client is the dealer and has been
    # ordered up, and hence must choose a card to drop
    #
    def decideDrop(self):
        # choose a random card from our hand
        (card,) = random.sample(self.hand,1)

        # log our intent
        info("")
        info(self.name+": cards: " + self.printHand(self.hand))
        info(self.name+": gonna drop: " + card)

        return card


    ###########################################################################
    # this routine is called when the client has been offered the chance to
    # defend alone; it should return one of DEFEND or DEFENDPASS
    #
    def decideDefend(self):
        return self.messageId['DEFENDPASS']


    ###########################################################################
    # This routine is called when the client is offered the option to lead
    # a trick; it just returns a random card from the deck
    #
    def decidePlayLead(self):
        # choose a random card from our hand to lead
        (card,) = random.sample(self.hand,1)

        # log our intent
        info(self.name+": cards: " + self.printHand(self.hand))
        info(self.name+": leading with " + card
            + " (" + self.printHand(self.hand) + ")")

        return card


    ###########################################################################
    # This routine is called when the client has to choose a card to follow
    # in a trick; it generates a list of valid cards and then returns a
    # random one of them
    #
    def decidePlayFollow(self):
        # choose a random card from the set of cards that we can follow with
        cards = self.followCards()
        (card,) = random.sample(cards,1)
        
        # log our intent
        info(self.name+": cards: " + self.printHand(self.hand))
        info(self.name+": following with " + card
            + " (" + self.printHand(self.hand) + ")")

        return card
