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

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.firstactive = False

    # the firstactive flag
    self.api.get('api.add')('firstactive', self.api_firstactive)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('events.register')('GMCP:char.status', self._charstatus)

    self._charstatus()

  def disconnect(self, _=None):
    """
    reattach to GMCP:char.status
    """
    BasePlugin.disconnect(self)
    self.api.get('events.register')('GMCP:char.status', self._charstatus)

  # returns the firstactive flag
  def api_firstactive(self):
    """  return the firstactive flag
    this function returns True or False"""
    return self.firstactive

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
      self.api.get('send.msg')('sending first active')
      self.api.get('events.eraise')('firstactive', {})

