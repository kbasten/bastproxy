"""
This plugin is a utility plugin for aardwolf functions

It adds functions to the api as well as takes care of the firstactive flag
"""
from plugins._baseplugin import BasePlugin

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
    self.connected = False

    self.gotchar = False
    self.gotroom = False

    # the firstactive flag
    self.api.get('api.add')('firstactive', self.api_firstactive)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('triggers.add')('reconnect',
            "^############# Reconnecting to Game #############$")

    self.api.get('events.register')('GMCP:char.status', self._charstatus)
    self.api.get('events.register')('GMCP:room.info', self._roominfo)
    self.api.get('events.register')('trigger_reconnect', self.reconnect)

    self._charstatus()

  def reconnect(self, _=None):
    """
    send a look on reconnect
    """
    self.api('send.mud')('look')

  def disconnect(self, _=None):
    """
    reattach to GMCP:char.status
    """
    BasePlugin.disconnect(self)
    self.gotchar = False
    self.gotroom = False
    self.api.get('events.register')('GMCP:char.status', self._charstatus)
    self.api.get('events.register')('GMCP:room.info', self._roominfo)

  # returns the firstactive flag
  def api_firstactive(self):
    """  return the firstactive flag
    this function returns True or False"""
    return self.firstactive

  def sendfirstactive(self):
    """
    send the firstactive event
    """
    proxy = self.api.get('managers.getm')('proxy')
    if self.gotchar and self.gotroom and proxy and proxy.connected:
      self.connected = True
      self.firstactive = True
      self.api.get('send.msg')('sending first active')
      self.api.get('events.eraise')('firstactive', {})

  def _charstatus(self, args=None):
    """
    check status for 3
    """
    state = self.api.get('GMCP.getv')('char.status.state')

    if state == 3:
      self.gotchar = True
      self.api.get('events.unregister')('GMCP:char.status', self._charstatus)
      self.sendfirstactive()

  def _roominfo(self, args=None):
    """
    check status for 3
    """
    self.gotroom = True
    self.api.get('events.unregister')('GMCP:room.info', self._roominfo)
    self.sendfirstactive()
