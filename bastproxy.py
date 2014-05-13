#!/usr/bin/env python
"""
## About
This is a mud proxy.
It runs in python 2.X (>2.6).

It supports MCCP, GMCP, aliases, actions, substitutes, variables
## Installation
### Git
 * ```git clone https://github.com/endavis/bastproxy.git```

### Download
 * Download the zip file from [here](https://github.com/endavis/bastproxy/archive/master.zip).
 * Unzip into a directory

## Getting Started

### Configuration
 * Use one of the included ones,  both for [Aardwolf Mud](http://www.aardwolf.com/)
 * Copy the below to "mud"-config.ini and change the items to suit your needs

---
    [proxy]
    listen_port = 9999
    mud_address = some.mud.address
    mud_port = 4000
    password = somepassword
    viewpw = someviewpassword

---

Don't forget to change the passwords!

### Starting
 * From the installation directory, ```python bastproxy.py "mud"-config.ini```

### Connecting
 * Connect a client to the listen_port above on the host the proxy is running, and then login with the password.

### Help
  * Use the following commands to get help, any command will show help when adding -h
   * Show command categories
     * ```#bp.commands```
   * show commands in a category
     * ```#bp.commands.list "category"```
     * ```#bp."category"```
   * Show loaded plugins
     * ```#bp.plugins```
   * Show plugins that are not loaded
     * ```#bp.plugins -n```

"""
import asyncore
import ConfigParser
import os
import sys
import socket
import signal
from libs import io
from libs.api import API

sys.stderr = sys.stdout

def setuppaths():
  """
  setup paths
  """
  npath = os.path.abspath(__file__)
  index = npath.rfind(os.sep)
  tpath = ''
  if index == -1:
    tpath = os.curdir + os.sep
  else:
    tpath = npath[:index]

  api.get('send.msg')('setting basepath to: %s' % tpath, 'startup')
  API.BASEPATH = tpath

  try:
    os.makedirs(os.path.join(api.BASEPATH, 'data', 'logs'))
  except OSError:
    pass

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

api = API()

class Listener(asyncore.dispatcher):
  """
  This is the class that listens for new clients
  """
  def __init__(self, listen_port, server_address, server_port):
    """
    init the class

    required:
      listen_port - the port to listen on
      server_address - the address of the server
      server_port - the port on the server to connect to
    """
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(("", listen_port))
    self.listen(50)
    self.proxy = None
    self.server_address = server_address
    self.server_port = server_port
    api.get('send.msg')("Listener bound on: %s" % listen_port, 'startup')

  def handle_error(self):
    """
    show the traceback for an error in the listener
    """
    api.get('send.traceback')("Forwarder error:")

  def handle_accept(self):
    """
    accept a new client
    """
    if not self.proxy:
      from libs.net.proxy import Proxy

      # do proxy stuff here
      self.proxy = Proxy(self.server_address, self.server_port)
      api.get('managers.add')('proxy', self.proxy)
    client_connection, source_addr = self.accept()

    try:
      ipaddress = source_addr[0]
      if self.proxy.checkbanned(ipaddress):
        api.get('send.msg')("HOST: %s is banned" % ipaddress, 'net')
        client_connection.close()
      elif len(self.proxy.clients) == 5:
        api.get('send.msg')(
          "Only 5 clients can be connected at the same time", 'net')
        client_connection.close()
      else:
        api.get('send.msg')("Accepted connection from %s : %s" %
                                      (source_addr[0], source_addr[1]), 'net')

        #Proxy client keeps up with itself
        from libs.net.client import ProxyClient
        ProxyClient(client_connection, source_addr[0], source_addr[1])
    except:
      api.get('send.traceback')('Error handling client')


def start(listen_port, server_address, server_port):
  """
  start the proxy

  we do a single asyncore.loop then we check timers
  """
  Listener(listen_port, server_address, server_port)
  try:
    while True:

      asyncore.loop(timeout=.25, count=1)
     # check our timer event
      api.get('events.eraise')('global_timer', {})

  except KeyboardInterrupt:
    pass

  api.get('send.msg')("Shutting down...", 'shutdown')

def main():
  """
  the main function that runs everything
  """
  setuppaths()

  try:
    if sys.argv[1] == "-d":
      daemon = True
      config = sys.argv[2]
    else:
      daemon = False
      config = sys.argv[1]
  except (IndexError, ValueError):
    print "Usage: %s [-d] config" % sys.argv[0]
    sys.exit(1)

  try:
    api.get('send.msg')('Config - loading', 'startup')
    configp = ConfigParser.RawConfigParser()
    api.get('managers.add')('config', configp)
    configp.read(config)
    api.get('send.msg')('Config - loaded', 'startup')
  except:
    api.get('send.traceback')('Error parsing config!')
    sys.exit(1)

  api.get('send.msg')('Plugin Manager - loading', 'startup')
  from plugins import PluginMgr
  pluginmgr = PluginMgr()
  pluginmgr.load()
  api.get('send.msg')('Plugin Manager - loaded', 'startup')

  api.get('log.adddtype')('net')
  api.get('log.console')('net')
  api.get('log.adddtype')('inputparse')
  api.get('log.adddtype')('ansi')

  def guard(func, message):
    """
    a wrap function for getting stuff from the config
    """
    try:
      return func()
    except:
      print "Error:", message
      raise
#      sys.exit(1)

  listen_port = guard(lambda:configp.getint("proxy", "listen_port"),
    "listen_port is a required field")
  mud_address = guard(lambda:configp.get("proxy", "mud_address"),
    "mud_address is a required field")
  mud_port = guard(lambda:configp.getint("proxy", "mud_port"),
    "mud_port is a required field")

  if not daemon:
    try:
      start(listen_port, mud_address, mud_port)
    except KeyboardInterrupt:
      api.get('event.eraise')('shutdown', {})
  else:
    os.close(0)
    os.close(1)
    os.close(2)
    os.open("/dev/null", os.O_RDONLY)
    os.open("/dev/null", os.O_RDWR)
    os.dup(1)

    if os.fork() == 0:
      # We are the child
      try:
        sys.exit(start(listen_port, mud_address, mud_port))
      except KeyboardInterrupt:
        print
      sys.exit(0)


if __name__ == "__main__":
  main()

