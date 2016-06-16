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



from datetime import datetime
from datetime import date
from glob import glob
from random import random
from time import time
from twython import Twython
from twython import TwythonStreamer
from twython.exceptions import TwythonError
from uuid import uuid4


import json
import os.path
import sys

from jsonSettings import JsonSettings as Settings


# if we're started without a config file, we create a default/empty 
# file that the user can fill in and then restart the app.
kDefaultConfigDict = {
   "appKey"             : "!!! Your app's 'Consumer Key'",
   "appSecret"          : "!!! Your app's 'Consumer Secret'",
   "accessToken"        : "!!! your access token",
   "accessTokenSecret"  : "!!! your access token secret",
   "lyricFilePath"      : "*.lyric",
   "tweetProbability"   : 24.0 / 1440,
   "minimumSpacing"     : 60*60,
   "minimumDaySpacing"  : 30,
   "logFilePath"        : "%Y-%m.txt"
}

kSettingsFileErrorMsg = '''\
There was no settings file found at {0}, so I just created an empty/default
file for you. Please edit it, adding the correct/desired values for each
setting as is appropriate.
'''

kStreamFileExtension = ".stream"


class NanobotStreamer(TwythonStreamer):

   def SetOutputPath(self, path):
      self.path = path

   def on_success(self, data):
      ''' Called when we detect an event through the streaming API. 
         The base class version looks for quoted tweets and for each one it 
         finds, we write out a text file that contains the ID of the tweet 
         that mentions us.
         
         The other (cron-job) version of your bot will look for any files with the 
         correct extension (identified by `kStreamFileExtension`) in its 
         HandleQuotes() method and favorite^H^H^H^H like those tweets.

         See https://dev.twitter.com/streaming/userstreams
      '''
      # for now, all we're interested in handling are events. 
      if 'event' in data:
         # Dump the data into a JSON file for the other cron-process to 
         # handle the next time it wakes up.
         fileName = os.path.join(self.path, "{0}.{1}".format(
            uuid4().hex, kStreamFileExtension))
         with open(fileName, "wt") as f:
            f.write(json.dumps(data).encode("utf-8"))
         

   def on_error(self, status_code, data):
      print "ERROR: {0}".format(status_code)
      self.disconnect()

         
 


class Nanobot(object):
   '''
      A tiny little twitterbot framework in Python.
   '''

   def __init__(self, argDict=None):
      if not argDict:
         argDict = { 'debug' : False, "force": False, 'stream': False, 'botPath' : "."}
      # update this object's internal dict with the dict of args that was passed
      # in so we can access those values as attributes.   
      self.__dict__.update(argDict)

      # we build a list of dicts containing status (and whatever other args 
      # we may need to pass to the update_status function as we exit, most 
      # probably 'in_reply-to_status_id' when we're replying to someone.)
      self.tweets = []




   ##
   ## Methods That Your Bot Might Wish To Override
   ##
   
   def GetDefaultConfigOptions(self):
      ''' 
         Override this in your derived class if you'd like to ensure that
         there's one or more specific key/value pairs present in the 
         settings file for a user to edit by hand as needed.
      '''
      return {}

   def IsReadyForUpdate(self):
      ''' Check to see if we should be generating a tweet this time.
         Defaults to the built-in logic where we prevent tweets happening
         too closely together or too far apart, and this can be overridden 
         if self.force is True.

         Derived classes are free to create their own version of this method.
      '''
      doUpdate = self.force
      last = self.settings.lastUpdate or 0
      now = int(time())
      lastTweetAge = now - last

      # default to creating a tweet at *least* every 4 hours.
      maxSpace = self.settings.GetOrDefault("maximumSpacing", 4 * 60 * 60)

      if lastTweetAge > maxSpace:
         # been too long since the last tweet. Make a new one for our fans!
         doUpdate = True

      elif random() < self.settings.tweetProbability:
         # Make sure that we're not tweeting too frequently. Default is to enforce 
         # a 1-hour gap between tweets (configurable using the 'minimumSpacing' key
         # in the config file, providing a number of minutes we must remain silent.)
         requiredSpace = self.settings.GetOrDefault("minimumSpacing",  60*60)

         if lastTweetAge > requiredSpace:
            # Our last tweet was a while ago, let's make another one.
            doUpdate = True

      return doUpdate



   def CreateUpdateTweet(self):
      ''' Override this method in your derived bot class. '''
      pass

   def HandleOneMention(self, mention):
      ''' should be overridden by derived classes. Base version 
      likes any tweet that mentions us.
      '''
      who = mention['user']['screen_name']
      text = mention['text']
      theId = mention['id_str']

      # we favorite every mention that we see
      if self.debug:
         print "Faving tweet {0} by {1}:\n {2}".format(theId, who, text.encode("utf-8"))
      else:
         self.twitter.create_favorite(id=theId)

   def PreRun(self):
      ''' 
         override in derived class to perform any actions that need
         to happen before the body of the Run() method.
      '''
      pass

   def PostRun(self):
      ''' 
         override in derived class to perform any actions that need
         to happen after the body of the Run() method.
      '''
      pass



   ##
   ## Methods That Your Bot Probably Won't Want To Override
   ## 

   def GetPath(self, path):
      '''
         Put all the relative path calculations in one place. If we're given a path
         that has a leading slash, we treat it as absolute and do nothing. Otherwise, 
         we treat it as a relative path based on the botPath setting in our config file.
      '''
      if not path.startswith(os.sep):
         path = os.path.join(self.botPath, path)
      return path

   def Log(self, eventType, dataList):
      '''
         Create an entry in the log file. Each entry will look like:
         timestamp\tevent\tdata1\tdata2 <etc>\n
         where:
         timestamp = integer seconds since the UNIX epoch
         event = string identifying the event
         data1..n = individual data fields, as appropriate for each event type.
         To avoid maintenance issues w/r/t enormous log files, the log filename 
         that's stored in the settings file is passed through datetime.strftime()
         so we can expand any format codes found there against the current date/time
         and create e.g. a monthly log file.
      '''
      now = int(time())
      today = datetime.fromtimestamp(now)
      # if there's no explicit log file path/name, we create one
      # that's the current year & month.
      fileName = self.settings.logFilePath
      if not fileName:
         fileName = "%Y-%m.txt"
         self.settings.logFilePath = fileName
      path = self.GetPath(fileName)
      path = today.strftime(path)
      with open(path, "a+t") as f:
         f.write("{0}\t{1}\t".format(now, eventType))
         f.write("\t".join(dataList))
         f.write("\n")

   def SendTweets(self):
      ''' send each of the status updates that are collected in self.tweets 
      '''
      for msg in self.tweets:
         if self.debug:
            print "TWEET: {0}".format(msg['status'].encode("UTF-8"))
         else:
            self.twitter.update_status(**msg)


   def CreateUpdate(self):
      '''
         Called everytime the bot is Run(). 

         Checks to see if the bot thinks that it's ready to generate new output, 
         and if so, calls CreateUpdateTweet to generate it.

      '''

      if self.IsReadyForUpdate():
         self.CreateUpdateTweet()


   def HandleMentions(self):
      '''
         Get all the tweets that mention us since the last time we ran and 
         process each one.
      '''
      mentions = self.twitter.get_mentions_timeline(since_id=self.settings.lastMentionId)
      if mentions:
         # Remember the most recent tweet id, which will be the one at index zero.
         self.settings.lastMentionId = mentions[0]['id_str']
         for mention in mentions:
            self.HandleOneMention(mention)


   def HandleStreamEvents(self):
      ''' 
         There may be a bot process that's waiting for stream events. When it
         encounters one, it writes the data out into a file with the extension
         ".stream". Handle any of those files that are present and delete them when
         we're done. 

         See https://dev.twitter.com/node/201
         for more information on the events that your bot can be sent.

         The event types that are listed at the time of writing are:
         access_revoked, block, unblock, favorite, unfavorite, follow, 
         unfollow, list_created, list_destroyed, list_updated,
         list_member_added, list_member_removed, list_user_subscribed,
         list_user_unsubscribed, quoted_tweet, user_update. 
      '''
      events = glob(self.GetPath("*.{0}".format(kStreamFileExtension)))
      for fileName in events:
         with open(fileName, "rt") as f:
            data = json.loads(f.read().decode("utf-8"))
            eventType = data["event"]
            handlerName = "Handle_{0}".format(eventType)
            handler = getattr(self, handlerName, None)
            if handler:
               handler(data)
            else:
               # log that we got something we didn't know how to handle.
               self.Log("UnknownStreamEvent", [eventType])
         # remove the file so we don't process it again!
         os.remove(self.GetPath(fileName))




   def Run(self):
      '''
         All the high-level logic of the bot is driven from here:
         - load settings
         - connect to twitter
         - (let your derived bot class get set up)
         - either:
            - wait for events from the streaming API
            - do bot stuff:
               - maybe create one or more tweets
               - handle any mentions
               - handle any streaming API events that were saved
               - send tweets out
         - (let your derived bot class clean up)
      '''

      # load the settings file.
      # If one doesn't exist, we create one that's populated with 
      # defaults, print a message to the console telling the user to
      # edit the file with correct values, and  exit.
      defaultSettings = kDefaultConfigDict.copy()
      defaultSettings.update(self.GetDefaultConfigOptions())
      self.settings = Settings(self.GetPath("{}.json".format(self.botName)), 
         defaultSettings)

      # create the Twython object that's going to communicate with the
      # twitter API.
      appKey = settings.appKey
      appsecret = settings.appSecret
      accesstoken = settings.accessToken
      accessTokenSecret = settings.accessTokenSecret
      if self.stream:
         self.twitter = NanobotStreamer(appKey, appSecret, accessToken, accessTokenSecret)
         self.twitter.SetOutputPath(self.botPath)
      else:
         self.twitter = Twython(appKey, appSecret, accessToken, accessTokenSecret)


      # give the derived bot class a chance to do whatever it needs
      # to do before we actually execute. 
      self.PreRun()
      if self.stream:
         if self.debug:
            print "About to stream from user account."
         try:
            # The call to user() will sit forever waiting for events on 
            # our user account to stream down. Those events will be handled 
            # for us by the BotStreamer object that we created above
            self.twitter.user()
         except KeyboardInterrupt:
            # disconnect cleanly from the server.
            self.twitter.disconnect()
      else:
         self.CreateUpdate()
         self.HandleMentions()
         self.HandleStreamEvents()
         self.SendTweets()

         # if anything we did changed the settings, make sure those changes 
         # get written out.
         self.settings.lastExecuted = str(datetime.now())
         self.settings.Write()

      # ...and let the derived bot class clean up as it needs to.
      self.PostRun()



   @classmethod
   def CreateAndRun(cls, argDict):
      '''
         Use this class method together with the below `GetBotArguments()`
         function to create an initialized instance of your derived bot 
         class and start it running. 
      '''
      try:
         bot = cls(argDict)
         bot.Run()
      except Exception as e:
         print str(e)
         bot.Log("ERROR", [str(e)])


def GetBotArguments(argAdder=None):
   '''
      parse command line arguments. If your bot wants to add its
      own args to the ArgumentParser, create a function that 
      accepts an argparse.ArgumentParser object, and pass it 
      into this function. Your bot would start up with code like:

      def MyArgAdder(parser):
         parser.add_argument(...)

      if __name__ == "__main__":
         MyCoolBot.CreateAndRun(GetBotArguments(MyArgAdder))
   '''
   import argparse
   parser = argparse.ArgumentParser()
   parser.add_argument("--debug", action='store_true', 
      help="print to stdout instead of tweeting")
   parser.add_argument("--force", action='store_true', 
      help="force operation now instead of waiting for randomness")
   parser.add_argument("--stream", action="store_true", 
      help="run in streaming mode")

   if argAdder:
      argAdder(parser)

   args = parser.parse_args()
   # convert the object returned from parse_args() to a plain old dict
   argDict = vars(args)


   # Find the path where this source file is being loaded from -- we use
   # this when resolving relative paths (e.g., to the data/ directory)
   mainSourceFile = sys.argv[0]
   botPath = os.path.abspath(os.path.dirname(mainSourceFile))
   argDict['botPath'] = botPath

   # By default, the name of this bot (as used to load the settings file, etc)
   # is taken from the name of the source file that launched us.
   _, fname = os.path.split(mainSourceFile)
   botName, _ = os.path.splitext(fname)
   argDict['botName'] = botName
   

   return argDict


if __name__ == "__main__":
   Nanobot.CreateAndRun(GetBotArguments())

