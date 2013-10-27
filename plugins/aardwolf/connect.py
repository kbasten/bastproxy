"""
$Id$

This plugin is a utility plugin for aardwolf functions
It adds functions to exported.aardu
"""
from plugins._baseplugin import BasePlugin
import math
import re

NAME = 'Aardwolf Firstactive'
SNAME = 'connect'
PURPOSE = 'send firstactive so we can send mud commands'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.connected = False
    self.firstactive = False

    # the firstactive flag
    self.api.get('api.add')('firstactive', self._firstactive)

    self.api.get('events.register')('mudconnect', self._mudconnect)
    self.api.get('events.register')('muddisconnect', self._muddisconnect)
    self.api.get('events.register')('GMCP:char.status', self._charstatus)

  # returns the firstactive flag
  def _firstactive(self):
    """  return the firstactive flag
    this function returns True or False"""
    return self.firstactive

  def _mudconnect(self, _=None):
    """
    set a flag for connect
    """
    self.connected = True

  def _muddisconnect(self, _None):
    """
    reset for next connection
    """
    self.connected = False
    self.api.get('events.unregister')('GMCP:char.status', self._charstatus)
    self.api.get('events.register')('GMCP:char.status', self._charstatus)

  def _charstatus(self, args=None):
    """
    check status for 3
    """
    state = self.api.get('GMCP.getv')('char.status.state')
    proxy = self.api.get('managers.getm')('proxy')
    if state == 3 and proxy and proxy.connected:
      self.api.get('events.unregister')('GMCP:char.status', self._charstatus)
      self.connected = True
      self.firstactive = True
      self.api.get('output.msg')('sending first active')
      self.api.get('events.eraise')('aardwolf_firstactive', {})

  def load(self):
    BasePlugin.load(self)

    self._charstatus()
