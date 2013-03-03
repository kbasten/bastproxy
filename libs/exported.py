"""
$Id$
"""

from __future__ import print_function

import sys, traceback
from libs import color
from libs.utils import DotDict

BASEPATH = ''
CMDMGR = None
EVENTMGR = None
PLUGINMGR = None
CONFIG = None
PROXY = None
LOGGER = None

CONNECTED = False

def msg(tmsg, dtype='default'):
  """send a msg through the LOGGER
argument 1: the message to send
argument 2: (optional) the data type, the default is 'default"""
  if LOGGER:
    LOGGER.msg({'msg':tmsg}, dtype)
   
   
def write_traceback(message=""):
  """write a traceback through the LOGGER
argument 1: (optional) the message to show with the traceback"""
  exc = "".join(traceback.format_exception(sys.exc_info()[0],
                    sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  write_error(message)


def write_error(text):
  """write an error through the LOGGER
argument 1: the text of the error"""
  text = str(text)
  test = []
  for i in text.split('\n'):
    test.append(color.convertcolors('@x136%s@w' % i))
  tmsg = '\n'.join(test)
  LOGGER.msg({'msg':tmsg, 'dtype':'error'})


def sendtoclient(text, raw=False, preamble=True):
  """send text to the clients converting color codes
argument 1: the text to send
argument 2: (optional) if this argument is True, do
             not convert color codes"""
  if isinstance(text, basestring):
    text = text.split('\n')
  
  if not raw:
    test = []
    for i in text:
      if preamble:
        i = '@R#BP@w: ' + i
      test.append(color.convertcolors(i))
    text = test
 
  event.eraise('to_client_event', {'todata':'\n'.join(text), 
                                    'raw':raw, 'dtype':'fromproxy'})


def execute(cmd):
  """execute a command through the interpreter
argument 1: the cmd to execute
  It will first be checked to see if it is an internal command
  and then sent to the mud if not"""
  data = None
  if cmd[-1] != '\n':
    cmd = cmd + '\n'
  newdata = event.eraise('from_client_event', {'fromdata':cmd})

  if 'fromdata' in newdata:
    data = newdata['fromdata']

  if data:
    event.eraise('to_mud_event', {'data':data, 'dtype':'fromclient'})
  
  
def add(func, subname=None, funcname=None):
  """add a function to exported
argument 1: the function
argument 2: the subgroup to put the function in"""  
  if not funcname:
    funcname = func.func_name
  if subname:
    if not (subname in globals()):
      globals()[subname] = DotDict()
    globals()[subname][funcname] = func
  else:
    globals()[funcname] = func
    
    
def remove(func=None, subname=None):
  """remove a function or subgroup from exported
argument 1: the function
argument 2: the subgroup"""   
  if subname:
    try:
      del globals()[subname]
    except KeyError:
      msg('exported has no subsection named %s' % subname, 'default')      
  else:
    try:
      del globals()[func.func_name]
    except KeyError:
      msg('exported has no function named %s' % \
                                                func.func_name, 'default')      
    
    