"""
$Id$

This plugin sends events when moving between rooms
"""
import copy
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'movement'
SNAME = 'move'
PURPOSE = 'movement plugin'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.lastroom = {}

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('events.register')('GMCP:room.info', self._roominfo)

  def _roominfo(self, _=None):
    """
    figure out if we moved or not
    """
    room = self.api.get('GMCP.getv')('room.info')
    if not self.lastroom:
      self.lastroom = copy.deepcopy(dict(room))
    else:
      if room['num'] != self.lastroom['num']:
        direction = 'unknown'
        for i in self.lastroom['exits']:
          if self.lastroom['exits'][i] == room['num']:
            direction = i
        newdict = {'from':self.lastroom,
            'to': room, 'direction':direction, 'roominfo':copy.deepcopy(dict(room))}
        self.api.get('output.msg')('raising moved_room, %s' % (newdict))
        self.api.get('events.eraise')('moved_room', newdict)
        self.lastroom = copy.deepcopy(dict(room))

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)

    self.api.get('output.msg')('requesting room')
    self.api.get('GMCP.sendpacket')('request room')
