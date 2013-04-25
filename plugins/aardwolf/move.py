"""
$Id$
"""
import copy
from plugins import BasePlugin
from libs import exported

NAME = 'movement'
SNAME = 'move'
PURPOSE = 'movement plugin'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.events['GMCP:room.info'] = {'func':self._roominfo}
    self.lastroom = {}


  def _roominfo(self, _=None):
    """
    figure out if we moved or not
    """
    room = exported.GMCP.getv('room.info')
    if not self.lastroom:
      self.lastroom = copy.deepcopy(dict(room))
    else:
      if room['num'] != self.lastroom['num']:
        direction = 'unknown'
        for i in self.lastroom['exits']:
          if self.lastroom['exits'][i] == room['num']:
            direction = i
        exported.sendtoclient('raising moved_room, from: %s, to : %s, dir : %s' % (self.lastroom['num'], room['num'], direction))
        exported.event.eraise('moved_room', {'from':self.lastroom,
            'to': room, 'direction':direction})
        self.lastroom = copy.deepcopy(dict(room))