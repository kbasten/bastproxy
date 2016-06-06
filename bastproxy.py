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
 * Download the zip file from
      [here](https://github.com/endavis/bastproxy/archive/master.zip).
 * Unzip into a directory

## Getting Started

### Starting
 * From the installation directory, ```python bastproxy.py```

```
usage: bastproxy.py [-h] [-p PORT] [-d]

A python mud proxy

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  the port for the proxy to listen on
  -d, --daemon          run in daemon mode
```

### Connecting
 * Connect a client to the listen_port above on the host the proxy is running,
      and then login with the password
  * Default Port: 9999
  * Default Password: "defaultpass"

### Help
  * Use the following commands to get help
   * Show command categories
     * ```#bp.commands```
   * show commands in a category
     * ```#bp.commands.list "category"```
     * ```#bp."category"```
   * Show loaded plugins
     * ```#bp.plugins```
   * Show plugins that are not loaded
     * ```#bp.plugins -n```

## Basics
### Plugins
  * Plugins are the basic building block for bastproxy, and are used through
  the commands that are added by the plugin.

### Commands
#### Help
  * Any command will show a help when adding a -h

#### Arguments
  * command line arguments are parsed like a unix shell command line
  * to specify an argument with spaces, surround it with double 's or "s
   * Examples:
    * ```#bp.plugins.cmd first second```
     * 1st argument = 'first'
     * 2nd argument = 'second'
    * ```#bp.plugins.cmd 'this is the first argument'
              "this is the second argument"```
     * 1st argument = 'this is the first argument'
     * 2nd argument = 'this is the second argument'
"""
import asyncore
import argparse
import os
import sys
import socket
#import signal
from libs.api import API as BASEAPI

# import io so we can get the "send" functions added to the api
from libs import io # pylint: disable=unused-import

sys.stderr = sys.stdout

API = BASEAPI()
BASEAPI.loading = True

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

  API('send.msg')('setting basepath to: %s' % tpath, 'startup')
  BASEAPI.BASEPATH = tpath

  try:
    os.makedirs(os.path.join(API.BASEPATH, 'data', 'logs'))
  except OSError:
    pass

class Listener(asyncore.dispatcher):
  """
  This is the class that listens for new clients
  """
  def __init__(self, listen_port):
    """
    init the class

    required:
      listen_port - the port to listen on
    """
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(("", listen_port))
    self.listen(50)
    self.proxy = None
    self.clients = []
    API('send.msg')("Listener bound on: %s" % listen_port, 'startup')

  def handle_error(self):
    """
    show the traceback for an error in the listener
    """
    API('send.traceback')("Forwarder error:")

  def handle_accept(self):
    """
    accept a new client
    """
    if not self.proxy:
      from libs.net.proxy import Proxy

      # do proxy stuff here
      self.proxy = Proxy()
      API('managers.add')('proxy', self.proxy)

    client_connection, source_addr = self.accept()

    try:
      ipaddress = source_addr[0]
      if self.proxy.checkbanned(ipaddress):
        API('send.msg')("HOST: %s is banned" % ipaddress, 'net')
        client_connection.close()
      elif len(self.proxy.clients) == 5:
        API('send.msg')(
            "Only 5 clients can be connected at the same time", 'net')
        client_connection.close()
      else:
        API('send.msg')("Accepted connection from %s : %s" %
                        (source_addr[0], source_addr[1]), 'net')

        #client keeps up with itself
        from libs.net.client import Client
        Client(client_connection, source_addr[0], source_addr[1])

    # catch everything because we don't want to exit if we can't connect a
    # client
    except Exception: # pylint: disable=broad-except
      API('send.traceback')('Error handling client')

def start(listen_port):
  """
  start the proxy

  we do a single asyncore.loop then we check timers
  """
  API('managers.add')('listener', Listener(listen_port))

  #if getattr(signal, 'SIGCHLD', None) is not None:
   # signal.signal(signal.SIGCHLD, signal.SIG_IGN)

  try:
    while True:

      asyncore.loop(timeout=.25, count=1)
     # check our timer event
      API('events.eraise')('global_timer', {})

  except KeyboardInterrupt:
    pass

  API('send.msg')("Shutting down...", 'shutdown')

def main():
  """
  the main function that runs everything
  """
  setuppaths()

  parser = argparse.ArgumentParser(description='A python mud proxy')
  parser.add_argument('-p', "--port",
                      help="the port for the proxy to listen on",
                      default=9999)
  parser.add_argument('-d', "--daemon",
                      help="run in daemon mode",
                      action='store_true')
  targs = vars(parser.parse_args())

  daemon = bool(targs['daemon'])

  API('send.msg')('Plugin Manager - loading', 'startup')
  from plugins import PluginMgr
  pluginmgr = PluginMgr()
  pluginmgr.load()
  API('send.msg')('Plugin Manager - loaded', 'startup')

  API('log.adddtype')('net')
  API('log.console')('net')
  API('log.adddtype')('inputparse')
  API('log.adddtype')('ansi')

  proxyp = API('plugins.getp')('proxy')

  if targs['port'] != 9999:
    proxyp.api('setting.change')('listenport', targs['port'])

  listen_port = proxyp.api('setting.gets')('listenport')

  BASEAPI.loading = False
  if not daemon:
    try:
      start(listen_port)
    except KeyboardInterrupt:
      proxy = API('managers.getm')('proxy')
      proxy.shutdown()
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
        sys.exit(start(listen_port))
      except KeyboardInterrupt:
        pass
      sys.exit(0)


if __name__ == "__main__":
  main()

