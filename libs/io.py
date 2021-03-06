"""
handle output and input functions, adds items under the send api
"""
import time
import sys
import traceback
import re
from libs.api import API as BASEAPI

API = BASEAPI()

# send a message
def api_msg(tmsg, primary='default', secondary=None):
  """  send a message through the log plugin
    @Ymsg@w        = This message to send
    @Yprimary@w    = the primary datatype of the message (default: 'default')
    @Ysecondary@w  = the secondary datatype of the message
                        (default: 'None')

  this function returns no values"""
  if primary == 'default':
    try:
      primary = API('utils.funccallerplugin')() or primary
    except (AttributeError, RuntimeError):
      pass

  if not isinstance(secondary, list):
    tmpl = []
    if secondary:
      tmpl.append(secondary)
    secondary = tmpl

  try:
    API('log.msg')({'msg':tmsg},
                   {'primary':primary, 'secondary':secondary})
  except (AttributeError, RuntimeError): #%s - %-10s :
    print '%s - %-10s : %s' % (time.strftime(API.timestring,
                                             time.localtime()), primary, tmsg)

# write and format a traceback
def api_traceback(message=""):
  """  handle a traceback
    @Ymessage@w  = the message to put into the traceback

  this function returns no values"""
  exc = "".join(traceback.format_exception(sys.exc_info()[0],
                                           sys.exc_info()[1],
                                           sys.exc_info()[2]))

  if message:
    message = message + "\n" + exc
  else:
    message = exc

  API('send.error')(message)

# write and format an error
def api_error(text):
  """  handle an error
    @Ytext@w  = The error to handle

  this function returns no values"""
  text = str(text)
  test = []
  for i in text.split('\n'):
    if API('api.has')('colors.convertcolors'):
      test.append(API('colors.convertcolors')('@x136%s@w' % i))
    else:
      test.append(i)
  tmsg = '\n'.join(test)

  try:
    API('log.msg')({'msg':tmsg, 'primary':'error'})
  except (AttributeError, TypeError):
    print '%s - No Log Plugin - %s : %s' % (time.strftime(API.timestring,
                                                          time.localtime()),
                                            'error', tmsg)

  try:
    API('errors.add')(time.strftime(API.timestring,
                                    time.localtime()),
                      tmsg)
  except (AttributeError, TypeError):
    pass

# send text to the clients
def api_client(text, raw=False, preamble=True):
  """  handle a traceback
    @Ytext@w      = The text to send to the clients
    @Yraw@w       = if True, don't convert colors
    @Ypreamble@w  = if True, send the preamble

  this function returns no values"""
  if isinstance(text, basestring):
    text = text.split('\n')

  if not raw:
    test = []
    for i in text:
      if preamble:
        i = '@C#BP@w: ' + i
      if API('api.has')('colors.convertcolors'):
        test.append(API('colors.convertcolors')(i))
      else:
        test.append(i)
    text = test

  try:
    API('events.eraise')('to_client_event', {'original':'\n'.join(text),
                                             'raw':raw, 'dtype':'fromproxy'})
  except (NameError, TypeError, AttributeError):
    API('send.msg')("couldn't send msg to client: %s" % '\n'.join(text),
                    primary='error')

# execute a command through the interpreter
def api_execute(command, fromclient=False, history=True):
  """  execute a command through the interpreter
  It will first check to see if it is an internal command, and then
  send to the mud if not.
    @Ycommand@w      = the command to send through the interpreter

  this function returns no values"""
  API('send.msg')('got command %s from client' % repr(command),
                  primary='inputparse')

  if command == '\r\n':
    API('send.msg')('sending %s to the mud' % repr(command),
                    primary='inputparse')
    API('events.eraise')('to_mud_event', {'data':command,
                                          'dtype':'fromclient',
                                          'history':history})
    return

  command = command.strip()

  commands = command.split('\r\n')

  for tcommand in commands:
    newdata = API('events.eraise')('from_client_event',
                                   {'fromdata':tcommand,
                                    'fromclient':fromclient,
                                    'internal':not fromclient,
                                    'history':history})

    if 'fromdata' in newdata:
      tcommand = newdata['fromdata']
      tcommand = tcommand.strip()

    if tcommand:
      datalist = re.split(API.splitre, tcommand)
      if len(datalist) > 1:
        API('send.msg')('broke %s into %s' % (tcommand, datalist),
                        primary='inputparse')
        for cmd in datalist:
          api_execute(cmd, history=history)
      else:
        tcommand = tcommand.replace('||', '|')
        if tcommand[-1] != '\n':
          tcommand = tcommand + '\n'
        API('send.msg')('sending %s to the mud' % tcommand.strip(),
                        primary='inputparse')
        API('events.eraise')('to_mud_event',
                             {'data':tcommand,
                              'dtype':'fromclient',
                              'history':history})

# send data directly to the mud
def api_tomud(data):
  """ send data directly to the mud

  This does not go through the interpreter
    @Ydata@w     = the data to send

  this function returns no values
  """
  if data[-1] != '\n':
    data = data + '\n'
  API('events.eraise')('to_mud_event',
                       {'data':data,
                        'dtype':'fromclient'})

API.add('send', 'msg', api_msg)
API.add('send', 'error', api_error)
API.add('send', 'traceback', api_traceback)
API.add('send', 'client', api_client)
API.add('send', 'mud', api_tomud)
API.add('send', 'execute', api_execute)
