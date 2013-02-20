"""
$Id$
"""

from __future__ import print_function

import sys, traceback
from libs import color

basepath = ''
cmdMgr = None
eventMgr = None
pluginMgr = None
config = None
proxy = None
logger = None

connected = False

def msg(msg, dtype='default'):
  """send a msg through the logger
argument 1: the message to send
argument 2: (optional) the data type, the default is 'default"""
  if logger:
    logger.msg({'msg':msg}, dtype)
   
   
def addtriggerevent(name, regex):
  """add a trigger
argument 1: the name of the trigger
argument 2: the regex for the trigger"""
  eventMgr.addtriggerevent(name, regex)


def registerevent(name, func, prio=50):
  """register an event in the event manager
argument 1: the name of the event
argument 2: the function to call
argument 3: (optional) the priority of the event, default is 50"""
  eventMgr.registerevent(name, func, prio)


def unregisterevent(name, func):
  """unregister an event
argument 1: the name of the event
argument 2: the function to call"""
  eventMgr.unregisterevent(name, func)


def raiseevent(name, args):
  """process an event and call all functions associated with ht
argument 1: the name of the event
argument 2: the argument list"""
  return eventMgr.raiseevent(name, args)


def write_traceback(message=""):
  """write a traceback through the logger
argument 1: (optional) the message to show with the traceback"""
  exc = "".join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  write_error(message)


def write_error(text):
  """write an error through the logger
argument 1: the text of the error"""
  text = str(text)
  test = []
  for i in text.split('\n'):
    test.append(color.convertcolors('@x136%s@w' % i))
  msg = '\n'.join(test)
  logger.msg({'msg':msg, 'dtype':'error'})


def sendtoclient(text, raw=False):
  """send text to the clients converting color codes
argument 1: the text to send
argument 2: (optional) if this argument is True, do
             not convert color codes"""
  if isinstance(text, basestring):
    text = text.split('\n')
  
  if not raw:
    test = []
    for i in text:
      test.append(color.convertcolors('@R#BP@w: ' + i))
    text = test
 
  eventMgr.raiseevent('to_client_event', {'todata':'\n'.join(text), 'raw':raw, 'dtype':'fromproxy'})

write_message = sendtoclient


def addtimer(name, func, seconds, onetime=False):
  """add a timer
argument 1: the name of the timer
argument 2: the function to call when this timer fires
argument 3: the # of seconds in the future to fire the timer
argument 4: (optional) if True, only fire this timer once. Default is False"""
  eventMgr.addtimer(name, func, seconds, onetime)


def deletetimer(name):
  """delete a timer
argument 1: the name of the timer to delete"""
  eventMgr.deletetimer(name)


def enabletimer(name):
  """enable a timer
argument 1: the name of the timer to enable"""
  eventMgr.enabletimer(name)


def disabletimer(name):
  """disable a timer
argument 1: the name of the timer to disable"""
  eventMgr.disabletimer(name)


def execute(cmd):
  """execute a command through the interpreter
argument 1: the cmd to execute
  It will first be checked to see if it is an internal command
  and then sent to the mud if not"""
  raiseevent('to_mud_event', {'data':cmd, 'dtype':'fromclient'})
  