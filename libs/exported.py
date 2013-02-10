"""
$Id$
"""

from __future__ import print_function

import sys, traceback
from libs import color

cmdMgr = None
eventMgr = None
pluginMgr = None
config = None
proxy = None
connected = False

debugf = True

def debug(*args):
  if debugf:
    print(*args, file=sys.stderr)

def addtriggerevent(name, regex):
  eventMgr.addtriggerevent(name, regex)


def registerevent(name, func, prio=50):
  eventMgr.registerevent(name, func, prio)


def unregisterevent(name, func):
  eventMgr.unregisterevent(name, func)


def processevent(name, args):
  return eventMgr.processevent(name, args)


def write_traceback(message=""):
  exc = "".join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  write_error(message)


def write_error(text):
  text = str(text)
  print('Error:', text, file=sys.stderr)


def sendtouser(text, raw=False):
  # parse colors here
  if not raw:
    test = []
    for i in text.split('\n'):
      test.append(color.convertcolors('@R#BP@w: ' + i))
    text = '\n'.join(test)
  eventMgr.processevent('to_client_event', {'todata':text, 'raw':raw, 'dtype':'fromproxy'})


def addtimer(name, func, seconds, onetime=False):
  eventMgr.addtimer(name, func, seconds, onetime)


def deletetimer(name):
  eventMgr.deletetimer(name)


def enabletimer(name):
  eventMgr.enabletimer(name)


def disabletimer(name):
  eventMgr.disabletimer(name)
