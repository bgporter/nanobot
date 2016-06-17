#! /usr/bin/env/python

# Copyright (c) 2016 Brett g Porter
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

'''
   tockbot.py -- simple demo of making a bot with the nanobot 
   framework.
'''

from nanobot.nanobot import Nanobot
from nanobot.nanobot import GetBotArguments

from datetime import datetime

class Tockbot(Nanobot):
   def __init__(self, argDict=None):
      super(Tockbot, self).__init__(argDict)

   def IsReadyForUpdate(self):
      ''' 
         Overridden from base class. 
         We're ready to create an update when it's the top of the hour,
         or if the user is forcing us to tweet. 
      '''

      now = datetime.now()
      return (0 == now.minute) or self.force

   def CreateUpdateTweet(self):
      ''' Chime the clock! '''
      now = datetime.now()
      # figure out how many times to chime; 1x per hour.
      chimeCount = now.hour % 12 or 12

      # create the message to tweet, repeating the chime
      msg = "\n".join(["BONG"] * chimeCount)
      # add the message to the end of the tweets list (rem)
      self.tweets.append({'status': msg})
      self.Log("Tweet", ["{} o'clock".format(chimeCount)])

   def HandleOneMention(self, mention):
      ''' Like the tweet that mentions us. If the word 'tick' appears
         in that tweet, also reply with the current time.
      '''
      who = mention['user']['screen_name']
      text = mention['text']
      theId = mention['id_str']
      eventType = "Mention"

      # we favorite every mention that we see
      if self.debug:
         print "Faving tweet {0} by {1}:\n {2}".format(theId, who, text.encode("utf-8"))
      else:
         self.twitter.create_favorite(id=theId)

      if 'tick' in text.lower():
         # reply to them with the current time.
         now = datetime.now()
         nowStr = now.strftime("It's %-I:%M %p on %A %B %d, %Y")      
         replyMsg = "@{0} {1}".format(who, nowStr)
         if self.debug:
            print "REPLY: {}".format(replyMsg)
         else:
            self.tweets.append({'status': replyMsg, 'in_reply_to_status_id': theId})
         eventType = "Reply"

      self.Log(eventType, [who])

   def Handle_quoted_tweet(self, data):
      '''Like any tweet that quotes us. '''
      tweetId = data['target_object']['id_str']
      if self.debug:
         print "Faving quoted tweet {0}".format(tweetId)
      else:
         try:
            self.twitter.create_favorite(id=tweetId)
         except TwythonError as e:
            self.Log("EXCEPTION", str(e))      


if __name__ == "__main__":
   Tockbot.CreateAndRun(GetBotArguments())
