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

    self.api.get('events.register')('GMCP:room.info', self._roominfo)
    self.lastroom = {}


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
        self.api.get('output.msg')('raising moved_room, from: %s, to : %s, dir : %s' % (
                    self.lastroom['num'], room['num'], direction))
        self.api.get('events.eraise')('moved_room', {'from':self.lastroom,
            'to': room, 'direction':direction})
        self.lastroom = copy.deepcopy(dict(room))

