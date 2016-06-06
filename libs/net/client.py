"""
$Id$

this module holds the proxy client class
"""
import time

from libs.api import API
from libs.net.telnetlib import Telnet

PASSWORD = 0
CONNECTED = 1

class Client(Telnet):
  """
  a class to hand a proxy client
  """
  def __init__(self, sock, host, port):
    """
    init the class
    """
    Telnet.__init__(self, sock=sock)
    self.host = host
    self.port = port
    self.api = API()
    self.ttype = 'Client'
    self.connectedtime = None
    self.supports = {}
    self.pwtries = 0
    self.banned = False
    self.viewonly = False

    if sock:
      self.connected = True
      self.connectedtime = time.mktime(time.localtime())

    self.api('events.register')('to_client_event',
                                self.addtooutbufferevent, prio=99)

    self.api('options.prepareclient')(self)

    self.state = PASSWORD
    self.addtooutbufferevent({'original':self.api('colors.convertcolors')(
        '@R#BP@w: @RPlease enter the proxy password:@w'),
                              'dtype':'passwd'})

  def addtooutbufferevent(self, args):
    """
    this function adds to the output buffer
    """
    outbuffer = args['original']
    dtype = None
    raw = False
    if 'dtype' in args:
      dtype = args['dtype']
    if not dtype:
      dtype = 'fromproxy'
    if 'raw' in args:
      raw = args['raw']
    if outbuffer != None:
      if (dtype == 'fromproxy' or dtype == 'frommud') \
            and self.state == CONNECTED:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer, raw)
      elif len(dtype) == 1 and ord(dtype) in self.options \
            and self.state == CONNECTED:
        Telnet.addtooutbuffer(self, outbuffer, raw)
      elif dtype == 'passwd' and self.state == PASSWORD:
        outbuffer = outbuffer + '\r\n'
        Telnet.addtooutbuffer(self, outbuffer, raw)

  def handle_read(self):
    """
    handle a read
    """

    proxy = self.api('managers.getm')('proxy')

    if not self.connected:
      return
    Telnet.handle_read(self)

    data = self.getdata()

    if data:
      if self.state == CONNECTED:
        if self.viewonly:
          self.addtooutbufferevent(
              {'todata':self.api('colors.convertcolors')(
                  '@R#BP@w: @RYou are in view mode!@w')})
        else:
          if len(data) > 0:
            self.api('send.execute')(data, fromclient=True)

      elif self.state == PASSWORD:
        data = data.strip()
        proxyp = self.api('plugins.getp')('proxy')
        dpw = proxyp.api('proxy.proxypw')()
        vpw = proxyp.api('proxy.proxypwview')()

        if dpw and  data == dpw:
          self.api('send.msg')('Successful password from %s : %s' % \
                                            (self.host, self.port), 'net')
          self.state = CONNECTED
          self.viewonly = False
          proxy.addclient(self)
          self.api('events.eraise')('client_connected', {'client':self})
          self.api('send.client')("%s - %s: Client Connected" % \
                                      (self.host, self.port))
        elif vpw and data == vpw:
          self.api('send.msg')('Successful view password from %s : %s' % \
                              (self.host, self.port), 'net')
          self.state = CONNECTED
          self.viewonly = True
          self.addtooutbufferevent(
              {'original':self.api('colors.convertcolors')(
                  '@R#BP@W: @GYou are connected in view mode@w')})
          proxy.addclient(self)
          self.api('events.eraise')('client_connected_view',
                                    {'client':self})
          self.api('send.client')(
              "%s - %s: Client Connected (View Mode)" % \
                  (self.host, self.port))
        else:
          self.pwtries += 1
          if self.pwtries == 5:
            self.addtooutbufferevent(
                {'original':self.api('colors.convertcolors')(
                    '@R#BP@w: @RYou have been BANNED for 10 minutes:@w'),
                 'dtype':'passwd'})
            self.api('send.msg')('%s has been banned.' % self.host, 'net')
            proxy.removeclient(self)
            proxy.addbanned(self.host)
            self.close()
          else:
            self.addtooutbufferevent(
                {'original':self.api('colors.convertcolors')(
                    '@R#BP@w: @RPlease try again! Proxy Password:@w'),
                 'dtype':'passwd'})

  def handle_close(self):
    """
    handle a close
    """
    self.api('send.client')("%s - %s: Client Disconnected" % \
                                (self.host, self.port))
    self.api('managers.getm')('proxy').removeclient(self)
    self.api('events.eraise')('client_disconnected', {'client':self})
    self.api('events.unregister')('to_client_event', self.addtooutbuffer)
    Telnet.handle_close(self)

