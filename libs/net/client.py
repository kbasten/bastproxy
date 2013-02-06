"""
$Id$
"""
from libs.net.telnetlib import Telnet, IAC, WILL, DO, SE, SB, DONT
from libs import exported
from libs.net.options import toptionMgr
from libs.color import convertcolors
import zlib

PASSWORD = 0
CONNECTED = 1

class ProxyClient(Telnet):
  def __init__(self, sock, host, port):
    Telnet.__init__(self, sock=sock)
    self.host = host
    self.port = port
    self.ttype = 'Client'
    self.supports = {}
    if sock:
      self.connected = True
    exported.registerevent('to_client_event', self.addtooutbufferevent, 99)
    toptionMgr.addtoclient(self)
    exported.proxy.addclient(self)
    self.state = PASSWORD
    self.addtooutbufferevent({'todata':convertcolors('@R#BP@w: @RPlease enter the proxy password:@w'), 'dtype':'passwd'})

  def addtooutbufferevent(self, args):  
    outbuffer = args['todata']
    dtype = None
    raw = False
    if 'dtype' in args:
      dtype = args['dtype']
    if not dtype:
      dtype = 'fromproxy'
    if 'raw' in args:
      raw = args['raw']
    if outbuffer != None:
      if (dtype == 'fromproxy' or dtype == 'frommud') and self.state == CONNECTED:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer, raw)
      elif len(dtype) == 1 and ord(dtype) in self.options and self.state == CONNECTED:
        Telnet.addtooutbuffer(self, outbuffer, raw)
      elif dtype == 'passwd' and self.state == PASSWORD:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer, raw)

  def handle_read(self):
    if self.connected == False:
      return
    Telnet.handle_read(self)

    data = self.getdata()

    if data:
      if self.state == CONNECTED:
        if not exported.proxy.connected:
          exported.proxy.connectmud()
        newdata = {}
        if len(data) > 0:
          newdata = exported.processevent('from_client_event', {'fromdata':data})

        if 'fromdata' in newdata:
          data = newdata['fromdata']

        if data[0:4] == '#bp.':
          print('got a command:', data.strip())
        else:
          exported.processevent('to_mud_event', {'data':data})
                
      elif self.state == PASSWORD:
        data = data.strip()
        if data ==  exported.config.get("proxy", "password"):
          exported.debug('Successful password from %s:%s' % (self.host, self.port))
          self.state = CONNECTED
          if not exported.proxy.connected:
            exported.proxy.connectmud()
          else:
            self.addtooutbufferevent({'todata':convertcolors('@R#BP@W: @GThe proxy is already connected to the mud@w')})
        else:
          self.addtooutbufferevent({'todata':convertcolors('@R#BP@w: @RPlease try again! Proxy Password:@w'), 'dtype':'passwd'})

  def handle_close(self):
    print "Client Disconnected"
    exported.proxy.removeclient(self)
    exported.unregisterevent('to_client_event', self.addtooutbuffer)
    Telnet.handle_close(self)

