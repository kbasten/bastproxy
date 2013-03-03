"""
$Id$

#BP: quest: {'eventname': 'GMCP:comm.quest', 'data': {u'action': u'ready'}, 
    'module': 'comm.quest', 
    'server': <libs.net.proxy.Proxy connected aardmud.org:4000 at 0xb689f530>}
#BP: quest: {'eventname': 'GMCP:comm.quest', 'data': {u'action': u'start', 
    u'targ': u'A Blood Ring soldier', u'room': u'In the village', 
    u'timer': 55, u'area': u'The Desert Prison'}, 'module': 'comm.quest', 
    'server': <libs.net.proxy.Proxy connected aardmud.org:4000 at 0xb689f530>}
#BP: quest: {'eventname': 'GMCP:comm.quest', 'data': {u'action': u'killed', 
    u'time': 55}, 'module': 'comm.quest', 
    'server': <libs.net.proxy.Proxy connected aardmud.org:4000 at 0xb689f530>}
#BP: quest: {'eventname': 'GMCP:comm.quest', 'data': {u'qp': 11, u'mccp': 2, 
    u'gold': 3430, u'double': 0, u'completed': 14867, u'totqp': 14, 
    u'lucky': 0, u'tp': 0, u'pracs': 0, u'daily': 0, u'trains': 0, 
    u'action': u'comp', u'tierqp': 1, u'wait': 30}, 'module': 'comm.quest', 
    'server': <libs.net.proxy.Proxy connected aardmud.org:4000 at 0xb689f530>}
"""
import time, copy
from libs import exported
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
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.events['GMCP:comm.quest'] = {'func':self.quest}
    self.queststuff = {}
    
  def quest(self, args):
    """
    process the quest event
    """
    questi = args['data']
    self.msg('quest: %s' % questi)
    if questi['action'] == 'ready':
      exported.event.eraise('aard_quest_ready', {})
      self.queststuff = {}
    elif questi['action'] == 'start':
      self.queststuff['mob'] = questi['targ']
      self.queststuff['area'] = questi['area']
      self.queststuff['room'] = questi['room']
      self.queststuff['stimer'] = questi['timer']
      self.queststuff['starttime'] = time.mktime(time.localtime())
      exported.event.eraise('aard_quest_start', self.queststuff)
    elif questi['action'] == 'killed':
      self.queststuff['killedtime'] = time.mktime(time.localtime())
      exported.event.eraise('aard_quest_killed', self.queststuff)
    elif questi['action'] == 'comp':
      print 'completed quest'
      self.queststuff['finishtime'] = time.mktime(time.localtime())
      self.queststuff['qp'] = questi['qp']
      self.queststuff['tierqp'] = questi['tierqp']
      self.queststuff['pracs'] = questi['pracs']
      self.queststuff['trains'] = questi['trains']
      self.queststuff['tp'] = questi['tp']
      self.queststuff['mccp'] = questi['mccp']
      self.queststuff['lucky'] = questi['lucky']
      self.queststuff['daily'] = questi['daily']
      self.queststuff['double'] = questi['double']
      self.queststuff['totqp'] = questi['totqp']
      self.queststuff['gold'] = questi['gold']
      exported.event.eraise('aard_quest_comp', copy.copydeep(self.queststuff))
    elif questi['action'] == 'failed':
      exported.event.eraise('aard_quest_failed', {})
    elif questi['action'] == 'status':
      exported.event.eraise('aard_quest_status', questi)
    elif questi['action'] == 'reset':
      #reset the timer to 60 seconds
      #when_required = os.time() + (stuff.timer * 60)
      #update_timer()
      exported.event.eraise('aard_quest_reset', {})
      

