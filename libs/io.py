"""
$Id$

handle output functions
"""
import time
import sys
import traceback
from libs.api import API
from libs import color

# send a message
def msg(tmsg, datatype='default'):
  """  send a message through the logger
    @Ymsg@w        = This message to send
    @Ydatatype@w   = the type to toggle"""
  try:
    api.get('logger.msg')({'msg':tmsg}, datatype)
  except AttributeError: #%s - %-10s :
    print '%s - %-10s : %s' % (time.strftime(api.timestring,
                                          time.localtime()), datatype, tmsg)

# write and format a traceback
def write_traceback(message=""):
  """  handle a traceback
    @Ymessage@w  = the message to put into the traceback"""
  exc = "".join(traceback.format_exception(sys.exc_info()[0],
                    sys.exc_info()[1], sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc
  api.get('output.error')(message)

# write and format an error
def write_error(text):
  """  handle an error
    @Ytext@w  = The error to handle"""
  text = str(text)
  test = []
  for i in text.split('\n'):
    test.append(color.convertcolors('@x136%s@w' % i))
  tmsg = '\n'.join(test)
  try:
    api.get('logger.msg')({'msg':tmsg, 'dtype':'error'})
  except (AttributeError, TypeError):
    print '%s - No Logger - %s : %s' % (time.strftime(api.timestring,
                                          time.localtime()), 'error', tmsg)

# send text to the clients
def sendtoclient(text, raw=False, preamble=True):
  """  handle a traceback
    @Ytext@w      = The text to send to the clients
    @Yraw@w       = if True, don't convert colors
    @Ypreamble@w  = if True, send the preamble"""
  if isinstance(text, basestring):
    text = text.split('\n')

  if not raw:
    test = []
    for i in text:
      if preamble:
        i = '@R#BP@w: ' + i
      test.append(color.convertcolors(i))
    text = test

  try:
    api.get('events.eraise')('to_client_event', {'todata':'\n'.join(text),
                                    'raw':raw, 'dtype':'fromproxy'})
  except (NameError, TypeError, AttributeError):
    api.get('output.msg')("couldn't send msg to client: %s" % '\n'.join(text), 'error')

# execute a command throgh the interpreter
def execute(cmd):
  """  execute a command through the interpreter
  It will first check to see if it is an internal command, and then
  sent to the mud if not.
    @Ycmd@w      = the command to send through the interpreter"""
  data = None
  if cmd[-1] != '\n':
    cmd = cmd + '\n'

  newdata = api.get('events.eraise')('from_client_event', {'fromdata':cmd})

  if 'fromdata' in newdata:
    data = newdata['fromdata']

  if data:
    api.get('events.eraise')('to_mud_event', {'data':data, 'dtype':'fromclient'})

api = API()
api.add('output', 'msg', msg)
api.add('output', 'error', write_error)
api.add('output', 'traceback', write_traceback)
api.add('output', 'client', sendtoclient)
api.add('input', 'execute', execute)
