#!/usr/bin/env python
"""
$Id$

This is the beginnings of a Mud Proxy that can have triggers, aliases, gags

TODO:
-- debug manager
     - every debug message has a type
     - on startup, plugins and other things register types
     - command to enable/disable output of types
     - can go to clients, logs, or both
-- general logging manager
-- triggers
     - need to also be able to check colors
  
"""
import asyncore
import ConfigParser
import os
import sys
import socket

from libs import exported

def setuppaths():
  """
  setup paths
  """
  npath = os.path.abspath(__file__)
  index = npath.rfind(os.sep)
  if index == -1:
    exported.BASEPATH = os.curdir + os.sep
  else:
    exported.BASEPATH = npath[:index]

  print 'setting basepath to', exported.BASEPATH

  try:
    os.makedirs(os.path.join(exported.BASEPATH, 'data', 'logs'))
  except OSError:
    pass  

setuppaths()

from libs.logger import Logger
exported.LOGGER = Logger()

from libs.event import EventMgr
exported.EVENTMGR = EventMgr()

from libs.cmdman import CmdMgr
exported.CMDMGR = CmdMgr()

from plugins import PluginMgr
exported.PLUGINMGR = PluginMgr()

exported.LOGGER.load()
exported.CMDMGR.load()
exported.PLUGINMGR.load()
exported.EVENTMGR.load()

exported.LOGGER.adddtype('net')
exported.LOGGER.cmd_console(['net'])

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
    exported.msg("Forwarder bound on", listen_port)

  def handle_error(self):
    """
    show the traceback for an error in the listener
    """
    exported.write_traceback("Forwarder error:")

  def handle_accept(self):
    """
    accept a new client
    """
    if not self.proxy:
      # do proxy stuff here
      self.proxy = Proxy(self.server_address, self.server_port)
      exported.PROXY = self.proxy
    client_connection, source_addr = self.accept()

    try:
      ipaddress = source_addr[0]
      if self.proxy.checkbanned(ipaddress):
        exported.msg("HOST: %s is banned" % ipaddress, 'net')
        client_connection.close()
      elif len(self.proxy.clients) == 5:
        exported.msg("Only 5 clients can be connected at the same time", 'net')
        client_connection.close()
      else:
        exported.msg("Accepted connection from %s : %s" % 
                                      (source_addr[0], source_addr[1]), 'net')
                                      
        #Proxy client keeps up with itself
        ProxyClient(client_connection, source_addr[0], source_addr[1])
    except:
      exported.write_traceback('Error handling client')


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
      exported.EVENTMGR.checktimerevents()

  except KeyboardInterrupt:
    pass

  exported.msg("Shutting down...")

def main():
  """
  the main function that runs everything
  """
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
    exported.CONFIG = ConfigParser.RawConfigParser()
    exported.CONFIG.read(config)
  except:
    print "Error parsing config!"
    sys.exit(1)

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

  listen_port = guard(lambda:exported.CONFIG.getint("proxy", "listen_port"),
    "listen_port is a required field")
  server_address = guard(lambda:exported.CONFIG.get("proxy", "server_address"),
    "server is a required field")
  server_port = guard(lambda:exported.CONFIG.getint("proxy", "server_port"),
    "server_port is a required field")

  if not daemon:
    try:
      start(listen_port, server_address, server_port)
    except KeyboardInterrupt:
      exported.event.eraise('savestate', {})
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
        sys.exit(start(listen_port, server_address, server_port))
      except KeyboardInterrupt:
        print
      sys.exit(0)

  
if __name__ == "__main__":
  main()
  
  