# This class shows a simple implementation of a player class for peuchre:
#  - it inherits from EuchrePlayer
#  - it has a class called Player
#  - it implements the core Player methods:
#     - decideOrderPass()
#     - decideCallPass()
#     - decideDrop()
#     - decideDefend()
#     - decidePlayLead()
#     - decidePlayFollow()
#
# This is the basic random player.
#  - has a 25% of ordering the hole card
#  - has a 25% of calling a random suit
#  - if it's the dealer will always call a random suit
#  - never goes alone
#  - drops the ordered card
#  - never defends alone
#  - leads randomly
#  - follows randomly


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
    # This routine returns either ORDER, ORDERALONE, or ORDERPASS, depending
    # on what the client wishes to do with the hole card.  The goal with the
    # random client is that trump will be ordered 50% of the time (and called
    # the other 50% of the time).  To accomplish this, the probability of
    # each (non-dealer-partner) player calling is 15.219%.
    #
    # This magic number is the real solution to this equation:
    #   (1-x)(1-x)(1-2x) = 0.5
    # This represents the probability each of 3 players must satisfy
    # such that their individual probability of calling (by team) is equal,
    # but the overall probability that someone will order is 50%.
    #
    # I've never tested this with aloneonorder false, but it should still work.
    #
    def decideOrderPass(self):
        # randomly choose to order with 15.219% probability
        op = "ORDERPASS"
        if random.random() < 0.15219:
            op = "ORDER"

        # if aloneonorder is true, and we're the dealer's partner, we never
        # order, since it will force a go alone
        if self.state['aloneonorder'] == 1:
            if self.team == self.state[self.state['dealer']]['team']:
                op = "ORDERPASS"
            # to make up for the imbalance caused by the dealer's partner
            # never ordering, the dealer will order with twice the probability
            # of the dealer-opposing team members: thus there is the same
            # probability that the dealer's team will order as the non-dealer's
            # team, it's just that the ordering is only ever done by the dealer
            if self.playerhandle == self.state['dealer']:
                op = "ORDERPASS"
                if random.random() < (0.15219*2):
                    op = "ORDER"
        
        info("")
        info(self.id+"cards: " + self.printHand(self.hand))
        if op == "ORDER":
            info(self.id+"I will order " + self.state['hole']
                + " to " + self.state[ self.state['dealer'] ]['name'] )
        else:
            info(self.id+"I will pass on ordering " + self.state['hole'])

        return self.messageId[op]


    ###########################################################################
    # This routine returns either CALL, CALLALONE, or CALLPASS, and a suit,
    # depending on whether the player whichs to call or call alone a suit,
    # or pass.  This implementation follows this logic:
    #  - if we're not the dealer, randomly choose to call (25%) or pass
    #    (75%)
    #  - if we choose to call, we randomly choose a suit that isn't
    #    the hole suit
    #
    def decideCallPass(self):
        # if we're the dealer, we have to call
        op = "CALL"
        suit = None

        # if we're not the dealer, call with 25% chance
        if self.state['dealer'] != self.playerhandle:
            op = random.choice(["CALL","CALLPASS","CALLPASS","CALLPASS"])
        
        info("")
        info(self.id+"cards: " + self.printHand(self.hand))

        # if we're going to call, get a list of all the suits, remove the
        # suit of the hole card (since it's been declined) and randomly
        # choose amongst the remainder
        if op == "CALL":
            suits = Card.suits()
            suits.remove(self.state['hole'].suit)
            suit = random.choice(suits)
            info(self.id+"I will call " + Card.suitName(suit))
        else:
            info(self.id+"I will pass on calling")

        # returning this dict seems to be the easiest way to return multiple
        # values out a function in python
        return {'op':self.messageId[op], 'suit':suit}


    ###########################################################################
    # this routine is called when the client is the dealer and has been
    # ordered up, and hence must choose a card to drop; hole is the card
    # that was ordered up
    #
    def decideDrop(self, hole):
        # log our intent
        info("")
        info(self.id+"cards: " + self.printHand(self.hand))
        info(self.id+"dropping ordered card: " + hole)
        info("")

        return hole


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
        info("")
        info(self.id+"cards: " + self.printHand(self.hand))
        info(self.id+"leading with " + card
            + " (" + self.printHand(self.hand) + ")")

        return card


    ###########################################################################
    # This routine is called when the client has to choose a card to follow
    # in a trick; it generates a list of valid cards and then returns a
    # random one of them
    #
    def decidePlayFollow(self):
        # choose a random card from the set of cards that we can follow with
        info("")
        info(self.id+"cards: " + self.printHand(self.hand))
        cards = self.followCards()
        (card,) = random.sample(cards,1)

        # log our intent
        info(self.id+"following with " + card
            + " (" + self.printHand(self.hand) + ")")

        return card
