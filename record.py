###########################################################################
# This object is used by peuchre to keep track of various stats of the
# hands.  We create one record item, and pass it to the player objects
# when it's created, and then the player object will call methods on the
# record object at various points.  At the moment, the Record object records
# these stats:
#  - remapped calling hand, hand result
#  - trick, % of hand can be used to follow
#  - number of hands
#  - number of tricks
#  - % of total possible calling hands
#  - some time stamps to compute hands/s

import os
import time
import sys
from card import Card

class Record: 

    ########################################################################### 
    # This initializes the object
    #
    def __init__(self,**kwargs):
        # records the time of the first submitted hand, in seconds
        self.start = time.time()

        # set up some game tracking stats
        self.gcount = 0

        # set up some hand tracking stats
        self.hcount = 0
        self.ecount = 0

        # set up the call hand stats dict
        self.chand  = {}
        self.ccount = 0
        self.cmax   = 0

        # set up the follow stats dict
        self.follow    = {}
        self.follow[1] = {}
        self.follow[2] = {}
        self.follow[3] = {}
        self.follow[4] = {}
        self.follow[5] = {}

        # initialize the lastwrite time to 0
        self.lastwrite = 0

        # if we were passed the name of the team1 and team2 algorithms,
        # store them, otherwise default to "unknown"
        self.team1 = "unknown"
        if "team1" in kwargs:
            self.team1 = kwargs['team1']
        self.team2 = "unknown"
        if "team2" in kwargs:
            self.team2 = kwargs['team2']


    ###########################################################################
    # This tracks overall game counts
    #
    def addGame(self):
        self.gcount += 1

        # write if it's time to
        self.write()


    ########################################################################### 
    # This takes a list of cards, a trump card, and a score.  It remaps the
    # hand according to the trump suit, and then stores the hand along with
    # the relative score (which will be either -4, -2, 1, 2, or 4, depending).
    # It then stores the result in a list, so we can compute averages,
    # histograms, sdev, etc.
    # 
    # We return the remapped string as a convenience: the player will print
    # this in the log, which will allow us to track back the details on a
    # specific result
    #
    def addChand(self, hand, trump, score):
        # track overall hand information
        self.hcount += 1

        # if the score is negative, then it was a euchre
        if score < 0:
            self.ecount += 1

        # remap the hand by calling remap(hand,trump): this returns a string
        # representation of the hand which is independent of the specific
        # trump suit
        remap = self.remap(hand,trump)

        # now use the remap string to index into the chand dict, and store
        # the score result; if the index for this remap doesn't exist,
        # make
        if remap not in self.chand:
            self.chand[remap] = {}
            self.chand[remap]['count'] = 0
            self.chand[remap]['sum'] = 0
            self.chand[remap]['scores'] = list([])

        # store the passed in information
        self.chand[remap]['count'] += 1
        self.chand[remap]['sum']   += score
        self.chand[remap]['scores'].append(score)

        # track the maximum number of repeats we've seen
        if self.chand[remap]['count'] > self.cmax:
            self.cmax = self.chand[remap]['count']

        # keep track of the total hands processed
        self.ccount += 1

        # write if it's time to
        self.write()

        # return the remap string so the player can log it
        return remap


    ###########################################################################
    # This tracks follow stats: it takes the number of cards in the hand
    # and the number of cards that are playable, and computes and stores
    # the running % of playable cards in each trick
    #
    def addFollow(self,hand,playable):
        # the number of cards in the hand determines the trick:
        #  5 cards - trick 1
        #  4 cards - trick 2
        # etc...
        trick = 6 - hand
    
        # compute the % playable by playable/hand
        ratio = playable/hand

        # initialize some elements
        if 'sum' not in self.follow[trick]:
            self.follow[trick]['sum'] = 0
        if 'count' not in self.follow[trick]:
            self.follow[trick]['count'] = 0

        # and store the data
        self.follow[trick]['sum']   += ratio
        self.follow[trick]['count'] += 1

        # write if it's time to
        self.write()


    ########################################################################### 
    # This prints out a screen full of information related to the records
    # object
    #
    def printCDetails(self):
        # print the details of the chand dict
        print("hand          count scores")
        for remap in self.chand:
            print("%s: %8d " % (remap,self.chand[remap]['count'])
                + str(self.chand[remap]['scores']))


    ########################################################################### 
    # This prints some high level info for the record
    #
    def print(self,**kwargs):
        # clear the screen to start
        if 'clear' not in kwargs \
           or ('clear' in kwargs and kwargs['clear'] != False ):
            os.system('clear')

        # compute the run time
        t = time.gmtime(time.time() - self.start)
        runtime = "%dd %02d:%02d:%02d" \
            % (t.tm_mday-1,t.tm_hour,t.tm_min,t.tm_sec)

        # a header
        print("Peuchre Stats ( %s )   Team 1: %s   Team 2: %s"
            % (runtime,self.team1,self.team2))
        print("")

        # print the game stats
        gps = 0
        if self.start != time.time():
            gps = self.gcount / (time.time() - self.start)
        print("Games:")
        print("  Total: %6d" % (self.gcount))
        print("Games/s:    %6.2f" % (gps))
        print("")

        # % euchres
        pereuchre = 0
        if self.hcount > 0:
            pereuchre = 100*(self.ecount/self.hcount)

        # print the hand stats
        hps = 0
        if self.start != time.time():
            hps = self.hcount / (time.time() - self.start)
        hpg = 0
        if self.gcount > 0:
            hpg = self.hcount / self.gcount
        print("Hands:")
        print("  Total: %6d          Euchres: %6d"
            % (self.hcount,self.ecount) )
        print("Hands/s:    %6.2f      %%euchres:    %6.2f" % (hps,pereuchre))
        print("Hands/g:    %6.2f" % (hpg))
        print("")
        
        # print the call hand stats
        numunique = len(self.chand)
        avg = 0
        if numunique > 0:
            avg = self.ccount / numunique
        print("Call Hands:")
        print(" Total:  %6d         Max Reps: %6d" % (self.ccount,self.cmax) )
        print("Unique:  %6d         Avg Reps:    %6.2f" % (numunique,avg) )
        print("%%cover:     %6.2f" % (100*numunique/10422) )
        print("")
        
        # print the follow stats
        avg = {}
        for i in (1,2,3,4,5):
            avg[i] = 0
            if 'count' in self.follow[i] and self.follow[i]['count'] > 0:
                avg[i] = self.follow[i]['sum'] / self.follow[i]['count']
        print("Follow Ratio:")
        for i in (1,2,3,4,5):
            print("Trick%d:     %6.2f" % (i,avg[i]))

        # write if it's time to
        self.write()


    ###########################################################################
    # This acts as a single method to call all the write methods: it
    # implements a timer mechanism, so even if this is called very
    # frequently, data is only written once every minute
    #
    def write(self):
        # if we're less than 60 seconds since the last write time,
        # skip this
        if (time.time() - self.lastwrite) < 60: return

        # otherwise call the write routines
        self.writeChandCsv()
        self.writeFollowCsv()

        # and update the last write time
        self.lastwrite = time.time()


    ###########################################################################
    # This acts as a single method to call all the write methods, but
    # will always force a write (as opposed to write() which only writes
    # once per minute): this is intended solely as a helper routine, to
    # guarantee that a write is performed, which is useful for example
    # when the overall program is exiting and we want to make sure we write
    # the most up to date information
    #
    def writeForce(self):
        # call the write routines
        self.writeChandCsv()
        self.writeFollowCsv()


    ########################################################################### 
    # This routine will print out the chand information (specifically the
    # remapped hand info, the overall average expected points, and the
    # detailed points data, into a file called peuchre-chand.csv
    #
    def writeChandCsv(self):
        # open the file to write
        f = open("peuchre-chand.csv","w")

        # print the header
        f.write("peuchre call stats\n")
        f.write("%s\n" % (time.strftime("%Y/%m/%d %H:%M:%S %Z")))
        f.write("team 1: %s\n" % (self.team1))
        f.write("team 2: %s\n" % (self.team2))
        f.write("\n")
        f.write("hand, ep, details\n")

        # step through all remapped hands and print them out
        for hand in sorted(self.chand):
            # we should never have 'count' = 0, but we'll be cautious
            avg = 0
            if self.chand[hand]['count'] > 0:
                avg = self.chand[hand]['sum'] / self.chand[hand]['count']
            string = "%s,%f" % (hand,avg)

            # now append a list of the detailed data points
            for score in self.chand[hand]['scores']:
                string += ",%d" % (score)

            # then write this line
            f.write(string+"\n")

        # close 'er up
        f.close()


    ########################################################################### 
    # This routine will print out the follow information (specifically the
    # % of cards that can be followed with in each trick) into a file
    # called peuchre-follow.csv
    #
    def writeFollowCsv(self):
        # open the file to write
        f = open("peuchre-follow.csv","w")

        # print the header
        f.write("peuchre follow stats\n")
        f.write("%s\n" % (time.strftime("%Y/%m/%d %H:%M:%S %Z")))
        f.write("team 1: %s\n" % (self.team1))
        f.write("team 2: %s\n" % (self.team2))
        f.write("\n")
        f.write("trick, %follow\n")

        # print the data
        avg = {}
        for i in (1,2,3,4,5):
            avg[i] = 0
            if 'count' in self.follow[i] and self.follow[i]['count'] > 0:
                avg[i] = self.follow[i]['sum'] / self.follow[i]['count']
        for i in (1,2,3,4,5):
            f.write("%d,%6.2f\n" % (i,avg[i]))

        # close 'er up
        f.close()


    ###########################################################################
    # This routine takes a set of cards and a trump suit, and returns a string
    # with the cards remapped to a suit-independent view of that hand:
    #     input: 'Jd', 'Ks', 'Qc', '9h', 'Jh', d trump
    #    output: RLtKaQb9c
    # which is read as: right and left of trump, K of off-suit a, Q of off-suit
    # b, 9 of off-suit c
    #
    # The intention is that this remapping of suits will be the same for any
    # trump suit, and symmetric for the off-suit cards.
    #
    #  - the J of trump and J of comp are remapped to R and L, both of suit
    #    "t' ("trump")
    #  - all non-trump suits are separated by their suit, ordered, and then
    #    relabeled as suit "a", "b", and "c"
    #
    def remap2(hand, trumpsuit):
        # set the trump and complementary suit
        compsuit = Card.suitName(Card.suitComp(trumpsuit))
        trumpsuit = Card.suitName(trumpsuit)

        # set the asuit and bsuit arbitrarily: we'll be sorting them later
        if trumpsuit == "c":
            asuit = "d"
            bsuit = "h"
            csuit = "s"
        if trumpsuit == "d":
            asuit = "c"
            bsuit = "h"
            csuit = "s"
        if trumpsuit == "h":
            asuit = "c"
            bsuit = "d"
            csuit = "s"
        if trumpsuit == "s":
            asuit = "c"
            bsuit = "d"
            csuit = "h"
    
        # set up our cardsets
        trump = list([])
        a     = list([])
        b     = list([])
        c     = list([])
    
        # go through each card, add it to the respective sets
        for card in hand:
            v = Card.valueName(card.value)
            s = Card.suitName(card.suit)
    
            # if it's the trump suit, add it to the trump set
            if s == trumpsuit:
                # if it's the J, relabel it as R
                if v == "J": v = "R"
                trump.append(v)
                continue
    
            # if it's the comp suit and it's the left, add it to the trump set
            if s == compsuit and v == "J":
                trump.append("L")
                continue
    
            # we've already arbitrarily set the asuit and bsuit values, so
            # now we add cards to them: we'll make decisions about the final
            # order in a moment
            if s == asuit:
                a.append(v)
            if s == bsuit:
                b.append(v)
            if s == csuit:
                c.append(v)
    
        # now we compose the remapped hand string; first add the trump set
        remap = ""
        if len(trump) > 0:
            remap = "".join(sorted(trump))
            #print("trump: %s  remap: %s" % (trump,remap))
        remap += "t"
    
        # we compose sorted strings for the a, b, and c sets, and then sort and
        # add them to the remap string
        abc = list([])
        abc.append("".join(sorted(a)))
        abc.append("".join(sorted(b)))
        abc.append("".join(sorted(c)))
        suitchars = ["a","b","c"]
        i = 0
        for s in sorted(abc):
            remap += s
            remap += suitchars[i]
            i += 1
    
        return remap
