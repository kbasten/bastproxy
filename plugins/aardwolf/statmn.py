"""
$Id$
"""
from libs import exported, utils
from plugins import BasePlugin

NAME = 'StatMonitor'
SNAME = 'statmn'
PURPOSE = 'Monitor for Aardwolf Events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc) 
    self.events['aard_quest_comp'] = {'func':self.compquest}
    self.events['aard_cp_comp'] = {'func':self.compcp}
    self.events['aard_level_gain'] = {'func':self.levelgain}
    self.msgs = {}
    
  def compquest(self, args):
    """
    handle a quest completion
    """
    msg = []
    msg.append('@x172StatMonitor: Quest finished for ')
    msg.append('@w%s@x' % args['qp'])
    if args['lucky'] > 0:
      msg.append('@x172+@w%s' % args['lucky'])
    if args['mccp'] > 0:
      msg.append('@x172+@w%s' % args['mccp'])
    if args['tierqp'] > 0:
      msg.append('@x172+@w%s' % args['tierqp'])
    if args['daily'] == 1:
      msg.append('@x172+@wE')
    if args['double'] == 1:
      msg.append('@x172+@wD')
    msg.append(' @x172= ')
    msg.append('@w%s@x172qp' % args['totqp'])
    if args['tp'] > 0:
      msg.append(' @w%s@x172TP' % args['tp'])
    if args['trains'] > 0:
      msg.append(' @w%s@x172tr' % args['trains'])
    if args['pracs'] > 0:
      msg.append(' @w%s@x172pr' % args['pracs'])
    msg.append('. It took @w%s@x172.' % \
         utils.timedeltatostring(args['starttime'], args['finishtime']))
    self.msgs['quest'] = ''.join(msg)
    exported.timer.add('msgtimer', {'func':self.showmessages, 'seconds':1, 'onetime':True})

  def compcp(self, args):
    """
    handle a cp completion
    """
    self.msg('compcp: %s' % args)
    msg = []
    msg.append('@x172StatMonitor: CP finished for ')    
    msg.append('@w%s@x172qp@w' % args['qp'])
    if args['tp'] > 0:
      msg.append(' @w%s@x172TP' % args['tp'])    
    if args['trains'] > 0:
      msg.append(' @w%s@x172tr' % args['trains'])
    if args['pracs'] > 0:
      msg.append(' @w%s@x172pr' % args['pracs'])    
    msg.append('. It took @w%s@x172.' % \
         utils.timedeltatostring(args['starttime'], args['finishtime']))      
      
    self.msgs['cp'] = ''.join(msg)
    exported.timer.add('msgtimer', {'func':self.showmessages, 'seconds':1, 'onetime':True})
    
  def levelgain(self, args):
    """
    handle a level or pup gain
    """
    self.msg('levelgain: %s' % args)
    
    
  def showmessages(self, args=None):
    """
    show a message
    """
    for i in self.msgs:
      exported.sendtoclient(self.msgs[i], preamble=False)
    self.msgs = {}
      
      