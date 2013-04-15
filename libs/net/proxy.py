"""
$Id$

This file holds the class that connects to the mud
"""
import time
from libs.net.telnetlib import Telnet
from libs import exported
from libs.color import strip_ansi, convertcolors
from libs.net.options import TELOPTMGR


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
    self.ttype = 'BastProxy'
    self.banned = {}
    self.connectedtime = None
    exported.event.register('to_mud_event', self.addtooutbuffer, 99)
    TELOPTMGR.addtoserver(self)

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
        tosend = i
        newdata = exported.event.eraise('from_mud_event', 
            {'fromdata':tosend, 'dtype':'frommud', 
                    'nocolordata':strip_ansi(tosend)})

        if 'fromdata' in newdata:
          tosend = newdata['fromdata']

        if tosend != None:
          #data cannot be transformed here
          exported.event.eraise('to_client_event', 
             {'todata':tosend, 'dtype':'frommud', 
                'nocolordata':strip_ansi(tosend)})        

  def addclient(self, client):
    """
    add a client
    
    required:
      client - the client to add
    """
    self.clients.append(client)
    
  def removeclient(self, client):
    """
    remove a client
    
    required:
      client - the client to remove
    """
    if client in self.clients:
      self.clients.remove(client)
      
  def addbanned(self, clientip):
    """
    add a banned client
    
    required
      clientip - the client ip to ban
    """
    self.banned[clientip] = time.time()

  def checkbanned(self, clientip):
    """
    check if a client is banned
    
    required
      clientip - the client ip to check
    """
    if clientip in self.banned:
      return True
    return False

  def connectmud(self):
    """
    connect to the mud
    """
    self.outbuffer = ''    
    self.doconnect()
    self.connectedtime = time.mktime(time.localtime())
    exported.msg('Connected to mud', 'net')    
    exported.event.eraise('mudconnect', {})

  def handle_close(self):
    """
    hand closing the connection
    """
    exported.msg('Disconnected from mud', 'net')
    exported.event.eraise('to_client_event',
        {'todata':convertcolors('@R#BP@w: The mud closed the connection'), 
        'dtype':'fromproxy'})
    TELOPTMGR.resetoptions(self, True)    
    Telnet.handle_close(self)
    exported.event.eraise('muddisconnect', {})  

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
