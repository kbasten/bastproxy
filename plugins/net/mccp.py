"""
$Id$

This module handles mccp
"""
import zlib
from libs.net._basetelnetoption import BaseTelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB, DONT
from plugins._baseplugin import BasePlugin

MCCP2 = chr(86)  # Mud Compression Protocol, v2

NAME = 'MCCP'
SNAME = 'mccp'
PURPOSE = 'Handle telnet option 86, MCCP'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 35

# Plugin
class Plugin(BasePlugin):
  """
  the plugin to handle external a102 stuff
  """
  def __init__(self, tname, tsname, filename, directory, importloc):
    """
    Iniitilaize the class
    """
    BasePlugin.__init__(self, tname, tsname, filename, directory, importloc)

    self.canreload = False

class SERVER(BaseTelnetOption):
  """
  the mccp option class to connect to a server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, MCCP2)
    #self.telnetobj.debug_types.append('MCCP2')
    self.orig_readdatafromsocket = None
    self.zlib_decomp = None

  def handleopt(self, command, sbdata):
    """
    handle the mccp opt
    """
    self.telnetobj.msg('MCCP2:', ord(command), '- in handleopt',
                                                mtype='MCCP2')
    if command == WILL:
      self.telnetobj.msg('MCCP2: sending IAC DO MCCP2', mtype='MCCP2')
      self.telnetobj.send(IAC + DO + MCCP2)
    elif command == SE:
      self.telnetobj.msg('MCCP2: got an SE mccp in handleopt',
                                              mtype='MCCP2')
      self.telnetobj.msg('MCCP2: starting compression with server',
                                              mtype='MCCP2')
      self.telnetobj.options[ord(MCCP2)] = True
      self.negotiate()

  def negotiate(self):
    """
    negotiate the mccp opt
    """
    self.telnetobj.msg('MCCP2: negotiating', mtype='MCCP2')
    self.zlib_decomp = zlib.decompressobj(15)
    if self.telnetobj.rawq:
      ind = self.telnetobj.rawq.find(SE)
      if not ind:
        ind = 0
      else:
        ind = ind + 1
      self.telnetobj.msg('MCCP2: converting rawq in handleopt',
                                                mtype='MCCP2')
      try:
        tempraw = self.telnetobj.rawq[:ind]
        rawq = self.zlib_decomp.decompress(self.telnetobj.rawq[ind:])
        self.telnetobj.rawq = tempraw + rawq
        self.telnetobj.process_rawq()
      except:
        self.telnetobj.handle_error()

    orig_readdatafromsocket = self.telnetobj.readdatafromsocket
    self.orig_readdatafromsocket = orig_readdatafromsocket
    def mccp_readdatafromsocket():
      """
      decompress the data
      """
      # give the original func a chance to munge the data
      data = orig_readdatafromsocket()
      # now do our work
      self.telnetobj.msg('MCCP2: decompressing', mtype='MCCP2')

      return self.zlib_decomp.decompress(data)

    setattr(self.telnetobj, 'readdatafromsocket', mccp_readdatafromsocket)

  def reset(self, onclose=False):
    """
    resetting the option
    """
    self.telnetobj.msg('MCCP: resetting', mtype='MCCP2')
    self.telnetobj.addtooutbuffer(IAC + DONT + MCCP2, True)
    self.telnetobj.rawq = self.zlib_decomp.decompress(self.telnetobj.rawq)
    setattr(self.telnetobj, 'readdatafromsocket',
                                self.orig_readdatafromsocket)
    TelnetOption.reset(self)

class CLIENT(BaseTelnetOption):
  """
  a class to connect to a client to manage mccp
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, MCCP2)
    #self.telnetobj.debug_types.append('MCCP2')
    self.orig_convert_outdata = None
    self.zlib_comp = None
    self.telnetobj.msg('MCCP2: sending IAC WILL MCCP2', mtype='MCCP2')
    self.telnetobj.send(IAC + WILL + MCCP2)

  def handleopt(self, command, sbdata):
    """
    handle the mccp option
    """
    self.telnetobj.msg('MCCP2:', ord(command), '- in handleopt',
                                                        mtype='MCCP2')

    if command == DO:
      self.telnetobj.options[ord(MCCP2)] = True
      self.negotiate()

  def negotiate(self):
    """
    negotiate the mccp option
    """
    self.telnetobj.msg("MCCP2: starting mccp", level=2, mtype='MCCP2')
    self.telnetobj.msg('MCCP2: sending IAC SB MCCP2 IAC SE', mtype='MCCP2')
    self.telnetobj.send(IAC + SB + MCCP2 + IAC + SE)

    self.zlib_comp = zlib.compressobj(9)
    self.telnetobj.outbuffer = \
                      self.zlib_comp.compress(self.telnetobj.outbuffer)

    orig_convert_outdata = self.telnetobj.convert_outdata
    self.orig_convert_outdata = orig_convert_outdata

    def mccp_convert_outdata(data):
      """
      compress outgoing data
      """
      data = orig_convert_outdata(data)
      self.telnetobj.msg('MCCP2: compressing', mtype='MCCP2')
      return self.zlib_comp.compress(data) + \
                                  self.zlib_comp.flush(zlib.Z_SYNC_FLUSH)

    setattr(self.telnetobj, 'convert_outdata', mccp_convert_outdata)

  def reset(self, onclose=False):
    """
    reset the option
    """
    self.telnetobj.msg('MCCP: resetting', mtype='MCCP2')
    if not onclose:
      self.telnetobj.addtooutbuffer(IAC + DONT + MCCP2, True)
    setattr(self.telnetobj, 'convert_outdata', self.orig_convert_outdata)
    self.telnetobj.outbuffer = \
                        self.zlib_comp.uncompress(self.telnetobj.outbuffer)
    TelnetOption.reset(self)
