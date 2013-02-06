#!/usr/bin/env python
"""
$Id$

This is the beginnings of a Mud Proxy that can have triggers, aliases, gags

TODO:
-- plugins
    - each plugin is a class, look at lyntin
    - save state (pickle?, sqlitedb?, configparser?)
-- command parser
-- add manager for managers

"""
import asyncore
import ConfigParser
import os
import sys
import traceback
import socket
from libs import exported

from libs.event import EventMgr
exported.eventMgr = EventMgr()

from plugins import PluginMgr
exported.pluginMgr = PluginMgr()

from libs.net.proxy import Proxy
from libs.net.client import ProxyClient



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
    exported.debug("Forwarder bound on", listen_port)

  def handle_error(self):
    """
    show the traceback for an error in the listener
    """
    exported.debug("Forwarder error:", traceback.format_exc())

  def handle_accept(self):
    """
    accept a new client
    """
    if not self.proxy:
      # do proxy stuff here
      self.proxy = Proxy(self.server_address, self.server_port)
      exported.proxy = self.proxy
    client_connection, source_addr = self.accept()

    print "Accepted connection from", source_addr[0], ':', source_addr[1]
    ProxyClient(client_connection, source_addr[0], source_addr[1])


def main(listen_port, server_address, server_port):
  """
  start the proxy
  
  we do a single asyncore.loop then we check timers
  """
  proxy = Listener(listen_port, server_address, server_port)
  try:
    while True:

      asyncore.loop(timeout=.5,count=1)
     # check our timer event
     # timer events can have attributes, run_forever, and how_often
      exported.eventMgr.checktimerevents()

  except KeyboardInterrupt:
       pass

  exported.debug("Shutting down...")


if __name__ == "__main__":
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
    exported.config = ConfigParser.RawConfigParser()
    exported.config.read(config)
  except:
    print "Error parsing config!"
    sys.exit(1)

  def guard(func, message):
    try:
      return func()
    except:
      print "Error:", message
      raise
      sys.exit(1)

  mode = 'proxy'
  listen_port = guard(lambda:exported.config.getint("proxy", "listen_port"),
    "listen_port is a required field")
  server_address = guard(lambda:exported.config.get("proxy", "server_address"),
    "server is a required field")
  server_port = guard(lambda:exported.config.getint("proxy", "server_port"),
    "server_port is a required field")

  if not daemon:
    try:
      main(listen_port, server_address, server_port)
    except KeyboardInterrupt:
      pass
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
        sys.exit(main(listen_port, host, port, mode))
      except KeyboardInterrupt:
        print
      sys.exit(0)

