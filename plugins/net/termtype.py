"""
$Id$

this module holds the termtype option
"""
from libs.net._basetelnetoption import BaseTelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB, DONT, NOOPT
from plugins._baseplugin import BasePlugin

NAME = 'Terminal Type Telnet Option'
SNAME = 'ttype'
PURPOSE = 'Handle telnet option 24, terminal type'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 35

AUTOLOAD = True

TTYPE = chr(24)  # Terminal Type

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
  the termtype class for the server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, TTYPE)
    #self.telnetobj.debug_types.append('TTYPE')

  def handleopt(self, command, sbdata):
    """
    handle the opt
    """
    self.telnetobj.msg('TTYPE:', ord(command), '- in handleopt',
                                  mtype='TTYPE')
    if command == DO:
      self.telnetobj.msg(
            'TTYPE: sending IAC SB TTYPE NOOPT MUSHclient-Aard IAC SE',
            mtype='TTYPE')
      self.telnetobj.send(
                IAC + SB + TTYPE + NOOPT + self.telnetobj.ttype + IAC + SE)


class CLIENT(BaseTelnetOption):
  """
  the termtype class for the client
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, TTYPE)
    #self.telnetobj.debug_types.append('TTYPE')
    self.telnetobj.msg('TTYPE: sending IAC WILL TTYPE', mtype='TTYPE')
    self.telnetobj.addtooutbuffer(IAC + DO + TTYPE, True)

  def handleopt(self, command, sbdata):
    """
    handle the opt
    """
    self.telnetobj.msg('TTYPE:', ord(command), '- in handleopt: ',
                                  sbdata, mtype='TTYPE')

    if command == WILL:
      self.telnetobj.addtooutbuffer(
                          IAC + SB + TTYPE +  chr(1)  + IAC + SE, True)
    elif command == SE:
      self.telnetobj.ttype = sbdata.strip()

  def negotiate(self):
    """
    negotiate when receiving an op
    """
    self.telnetobj.msg("TTYPE: starting TTYPE", level=2, mtype='TTYPE')
    self.telnetobj.msg('TTYPE: sending IAC SB TTYPE IAC SE', mtype='TTYPE')
    self.telnetobj.send(IAC + SB + TTYPE + IAC + SE)

  def reset(self, onclose=False):
    """
    reset the opt
    """
    self.telnetobj.msg('TTYPE: resetting', mtype='TTYPE')
    if not onclose:
      self.telnetobj.addtooutbuffer(IAC + DONT + TTYPE, True)
    TelnetOption.reset(self)
