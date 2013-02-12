"""
$Id$

This file holds the class that connects to the mud
"""
from libs.net.telnetlib import Telnet
from libs import exported
from libs.color import strip_ansi, convertcolors
from libs.net.options import toptionMgr


class Proxy(Telnet):
  """
  This class is for the proxy that connects to the server
  """
  def __init__(self, host, port):
    """
    init the class
    
    required:
      host - the host to connect to
      port - the port to connect to
    """
    Telnet.__init__(self, host, port)
    self.clients = []

    self.username = None
    self.password = None
    self.lastmsg = ''
    self.clients = []
    self.ttype = 'Server'
    exported.registerevent('to_mud_event', self.addtooutbuffer, 99)
    toptionMgr.addtoserver(self)

  def handle_read(self):
    """
    handle a read
    """
    Telnet.handle_read(self)

    data = self.getdata()
    if data:
      ndata = self.lastmsg + data
      alldata = ndata.replace("\r","")
      ndatal = alldata.split('\n')
      self.lastmsg = ndatal[-1]
      for i in ndatal[:-1]:
        exported.processevent('to_client_event', {'todata':i, 'dtype':'frommud', 'noansidata':strip_ansi(i)})

  def addclient(self, client):
    """
    add a client
    
    required:
      client - the client to add
    """
    self.clients.append(client)

  def connectmud(self):
    """
    connect to the mud
    """
    exported.debug('connectmud')
    self.doconnect()
    exported.processevent('mudconnect', {})

  def handle_close(self):
    """
    hand closing the connection
    """
    exported.debug('Server Disconnected')
    exported.processevent('to_client_event', {'todata':convertcolors('@R#BP@w: The mud closed the connection'), 'dtype':'fromproxy'})
    toptionMgr.resetoptions(self, True)
    Telnet.handle_close(self)
    exported.processevent('muddisconnect', {})  

  def removeclient(self, client):
    """
    remove a client
    
    required:
      client - the client to remove
    """
    if client in self.clients:
      self.clients.remove(client)

  def addtooutbuffer(self, args, raw=False):
    """
    add to the outbuffer
    
    required:
      args - a string 
             or a dictionary that contains a data key and a raw key
    
    optional:
      raw - set a raw flag, which means IAC will not be doubled
    """
    data = ''
    dtype = 'fromclient'
    if isinstance(args, dict):
      data = args['data']
      dtype = args['dtype']
      if 'raw' in args:
        raw = args['raw']
    else:
      data = args

    if len(dtype) == 1 and ord(dtype) in self.options:
      Telnet.addtooutbuffer(self, data, raw)
    elif dtype == 'fromclient':
      Telnet.addtooutbuffer(self, data, raw)
