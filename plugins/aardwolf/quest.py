"""
$Id$
"""
import time
import copy
import os
from libs import exported
from libs.persistentdict import PersistentDict
from plugins import BasePlugin

NAME = 'Aardwolf Quest Events'
SNAME = 'quest'
PURPOSE = 'Events for Aardwolf Quests'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf quest events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.savequestfile = os.path.join(self.savedir, 'quest.txt')
    self.queststuff = PersistentDict(self.savequestfile, 'c', format='json')
    self.dependencies.append('aardu')
    self.events['GMCP:comm.quest'] = {'func':self.quest}

  def resetquest(self):
    """
    reset the quest info
    """
    self.queststuff.clear()
    self.queststuff['finishtime'] = -1
    self.queststuff['starttime'] = time.time()
    self.queststuff['mobname'] = ''
    self.queststuff['mobarea'] = ''
    self.queststuff['mobroom'] = ''
    self.queststuff['totqp'] = 0
    self.queststuff['daily'] = 0
    self.queststuff['double'] = 0
    self.queststuff['qp'] = 0
    self.queststuff['gold'] = 0
    self.queststuff['tier'] = 0
    self.queststuff['mccp'] = 0
    self.queststuff['lucky'] = 0
    self.queststuff['tp'] = 0
    self.queststuff['level'] = exported.aardu.getactuallevel(
                            exported.GMCP.getv('char.status.level'))
    self.queststuff['trains'] = 0
    self.queststuff['pracs'] = 0
    self.queststuff['failed'] = 0

  def quest(self, args):
    """
    process the quest event
    """
    questi = args['data']
    self.msg('quest: %s' % questi)
    if questi['action'] == 'ready':
      exported.event.eraise('aard_quest_ready', {})
    elif questi['action'] == 'start':
      self.resetquest()
      self.queststuff['mobname'] = questi['targ']
      self.queststuff['mobarea'] = questi['area']
      self.queststuff['mobroom'] = questi['room']
      self.queststuff['stimer'] = questi['timer']
      exported.event.eraise('aard_quest_start', self.queststuff)
    elif questi['action'] == 'killed':
      self.queststuff['killedtime'] = time.time()
      exported.event.eraise('aard_quest_killed', self.queststuff)
    elif questi['action'] == 'comp':
      self.queststuff['finishtime'] = time.time()
      self.queststuff['qp'] = questi['qp']
      self.queststuff['tier'] = questi['tierqp']
      self.queststuff['pracs'] = questi['pracs']
      self.queststuff['trains'] = questi['trains']
      self.queststuff['tp'] = questi['tp']
      self.queststuff['mccp'] = questi['mccp']
      self.queststuff['lucky'] = questi['lucky']
      self.queststuff['daily'] = questi['daily']
      self.queststuff['double'] = questi['double']
      self.queststuff['totqp'] = questi['totqp']
      self.queststuff['gold'] = questi['gold']
      exported.event.eraise('aard_quest_comp', copy.deepcopy(self.queststuff))
    elif questi['action'] == 'fail':
      self.queststuff['finishtime'] = time.time()
      self.queststuff['failed'] = 1
      exported.event.eraise('aard_quest_failed',
                              copy.deepcopy(self.queststuff))
    elif questi['action'] == 'status':
      exported.event.eraise('aard_quest_status', questi)
    elif questi['action'] == 'reset':
      #reset the timer to 60 seconds
      #when_required = os.time() + (stuff.timer * 60)
      #update_timer()
      exported.event.eraise('aard_quest_reset', {})
    self.queststuff.sync()

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.queststuff.sync()


