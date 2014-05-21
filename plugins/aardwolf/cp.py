"""
This plugin handles cp events for Aardwolf
"""
import time
import os
import copy
import re
import argparse
from libs.persistentdict import PersistentDict
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf CP Events'
SNAME = 'cp'
PURPOSE = 'Events for Aardwolf CPs'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.savecpfile = os.path.join(self.savedir, 'cp.txt')
    self.cpinfo = PersistentDict(self.savecpfile, 'c')
    self.mobsleft = []
    self.cpinfotimer = {}
    self.nextdeath = False

    self.cmdqueue = None

    self.api.get('dependency.add')('cmdq')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.cmdqueue = self.api.get('cmdq.baseclass')()(self)

    self.cmdqueue.addcmdtype('cpcheck', 'campaign check', "^campaign check$",
                       self.cpcheckbefore, self.cpcheckafter)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show cp info')
    self.api.get('commands.add')('show', self.cmd_show,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='refresh cp info')
    self.api.get('commands.add')('refresh', self.cmd_refresh,
                                parser=parser)

    self.api.get('watch.add')('cp_check',
      '^(cp|campa|campai|campaig|campaign) (c|ch|che|chec|check)$')

    self.api.get('triggers.add')('cpnew',
      "^Commander Barcett tells you " \
        "'Type 'campaign info' to see what you must kill.'$")
    self.api.get('triggers.add')('cpnone',
      "^You are not currently on a campaign.$",
      enabled=False, group='cpcheck', omit=True)
    self.api.get('triggers.add')('cptime',
      "^You have (?P<time>.*) to finish this campaign.$",
      enabled=False, group='cpcheck', omit=True)
    self.api.get('triggers.add')('cpmob',
      "^You still have to kill \* (?P<mob>.*) " \
            "\((?P<location>.*?)(?P<dead> - Dead|)\)$",
      enabled=False, group='cpcheck', omit=True)
    self.api.get('triggers.add')('cpscramble',
      "Note: One or more target names in this " \
            "campaign might be slightly scrambled.$",
      enabled=False, group='cpcheck', omit=True)
    self.api.get('triggers.add')('cpneedtolevel',
      "^You will have to level before you" \
                " can go on another campaign.$",
      enabled=False,
      group='cpin')
#Note: One or more target names in this campaign might be slightly scrambled.
    self.api.get('triggers.add')('cpcantake',
      "^You may take a campaign at this level.$",
      enabled=False,
      group='cpin')
    self.api.get('triggers.add')('cpshnext',
      "^You cannot take another campaign for (?P<time>.*).$",
      enabled=False,
      group='cpin')
    self.api.get('triggers.add')('cpmobdead',
      "^Congratulations, that was one of your CAMPAIGN mobs!$",
      enabled=False,
      group='cpin')
    self.api.get('triggers.add')('cpcomplete',
      "^CONGRATULATIONS! You have completed your campaign.$",
      enabled=False,
      group='cpin')
    self.api.get('triggers.add')('cpclear',
      "^Campaign cleared.$",
      enabled=False,
      group='cpin')
    self.api.get('triggers.add')('cpreward',
      "^\s*Reward of (?P<amount>\d+) (?P<type>.+) .+ added.$",
      enabled=False,
      group='cprew',
      argtypes={'amount':int})
    self.api.get('triggers.add')('cpcompdone',
      "^--------------------------" \
            "------------------------------------$",
      enabled=False,
      group='cpdone')

    self.api.get('events.register')('trigger_cpnew', self._cpnew)
    self.api.get('events.register')('trigger_cpnone', self._cpnone)
    self.api.get('events.register')('trigger_cptime', self._cptime)
    #self.api.get('events.register')('watch_cp_check', self._cpcheckcmd)
    self.api.get('events.register')('trigger_cpmob', self._cpmob)
    self.api.get('events.register')('trigger_cpneedtolevel',
                                    self._cpneedtolevel)
    self.api.get('events.register')('trigger_cpcantake', self._cpcantake)
    self.api.get('events.register')('trigger_cpshnext', self._cpshnext)
    self.api.get('events.register')('trigger_cpmobdead', self._cpmobdead)
    self.api.get('events.register')('trigger_cpcomplete', self._cpcomplete)
    self.api.get('events.register')('trigger_cpclear', self._cpclear)
    self.api.get('events.register')('trigger_cpreward', self._cpreward)
    self.api.get('events.register')('trigger_cpcompdone', self._cpcompdone)

  def cmd_show(self, args):
    """
    show the cp mobs
    """
    msg = []
    if self.cpinfo['oncp']:
      msg.append('Mobs left:')
      msg.append('%-40s %s' % ('Mob Name', 'Area/Room'))
      msg.append('@G' + '-' * 60)
      for i in self.mobsleft:
        color = '@w'
        if i['mobdead']:
          color = '@R'
        msg.append('%s%-40s %s' % (color, i['name'], i['location']))
    else:
      msg.append('You are not on a cp')

    return True, msg

  def cmd_refresh(self, args):
    """
    cmd to refresh cp info
    """
    msg = []
    if self.cpinfo['oncp']:
      msg.append('Refreshing cp mobs')
      self.cmdqueue.addtoqueue('cpcheck', '')
    else:
      msg.append('You are not on a cp')

    return True, msg

  def cpcheckbefore(self):
    """
    function to run before send the command
    """
    self.mobsleft = []
    self.cpinfotimer = {}
    self.api.get('triggers.togglegroup')('cpcheck', True)

  def cpcheckafter(self):
    """
    function to run after the command is finished
    """
    self.api.get('triggers.togglegroup')("cpin", True)
    self.api.get('triggers.togglegroup')('cpcheck', False)

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)
    self.cmdqueue.addtoqueue('cpcheck', '')

  def _cpreset(self):
    """
    reset the cp
    """
    self.cpinfo.clear()
    self.cpinfo['mobs'] = {}
    self.cpinfo['trains'] = 0
    self.cpinfo['pracs'] = 0
    self.cpinfo['gold'] = 0
    self.cpinfo['tp'] = 0
    self.cpinfo['qp'] = 0
    self.cpinfo['bonusqp'] = 0
    self.cpinfo['failed'] = 0
    self.cpinfo['level'] = self.api.get('aardu.getactuallevel')(
                        self.api.get('GMCP.getv')('char.status.level'))
    self.cpinfo['starttime'] = time.time()
    self.cpinfo['finishtime'] = 0
    self.cpinfo['oncp'] = True
    self.cpinfo['cantake'] = False
    self.cpinfo['shtime'] = None
    self.savestate()

  def _cpnew(self, args=None):
    """
    handle a new cp
    """
    self.api.get('send.msg')('cpnew: %s' % args)
    self._cpreset()
    self.cmdqueue.addtoqueue('cpcheck', '')

  def _cpnone(self, _=None):
    """
    handle a none cp
    """
    self.api.get('send.msg')('cpnone')
    self.cpinfo['oncp'] = False
    self.savestate()
    self.api.get('triggers.togglegroup')('cpcheck', False)
    self.api.get('triggers.togglegroup')('cpin', False)
    self.api.get('triggers.togglegroup')('cprew', False)
    self.api.get('triggers.togglegroup')('cpdone', False)
    #check(EnableTimer("cp_timer", false))
    self.cpinfotimer = {}
    self.cmdqueue.cmddone('cpcheck')

  def _cptime(self, _=None):
    """
    handle cp time
    """
    self.api.get('send.msg')('handling cp time')
    self.api.get('send.msg')('%s' % self.cpinfo)
    if not self.cpinfo['mobs']:
      self.api.get('send.msg')('copying mobsleft')
      self.cpinfo['mobs'] = self.mobsleft[:]
      self.api.get('events.eraise')('aard_cp_mobsorig',
                    copy.deepcopy({'mobsleft':self.mobsleft}))
      self.savestate()

    self.api.get('send.msg')('raising aard_cp_mobsleft %s' % self.mobsleft)
    self.api.get('events.eraise')('aard_cp_mobsleft',
                    copy.deepcopy({'mobsleft':self.mobsleft}))

    self.cmdqueue.cmddone('cpcheck')

  def _cpneedtolevel(self, _=None):
    """
    handle cpneedtolevel
    """
    self.cpinfo['cantake'] = False
    self.savestate()

  def _cpcantake(self, _=None):
    """
    handle cpcantake
    """
    self.cpinfo['cantake'] = True
    self.savestate()

  def _cpshnext(self, args=None):
    """
    handle cpshnext
    """
    self.cpinfo['shtime'] = args['time']
    self.savestate()

  def _cpmob(self, args=None):
    """
    handle cpmob
    """
    name = args['mob']
    mobdead = self.api.get('utils.verify')(args['dead'], bool)
    location = args['location']

    if not name or not location:
      self.api.get('send.msg')("error parsing line: %s" % args['line'])
    else:
      self.mobsleft.append({'name':name,
                      'nocolorname':self.api.get('colors.stripansi')(name),
                      'location':location, 'mobdead':mobdead})

  def _cpmobdead(self, _=None):
    """
    handle cpmobdead
    """
    self.api.get('events.register')('aard_mobkill', self._mobkillevent)
    #self.api.get('send.execute')("cp check")

  def _cpcomplete(self, _=None):
    """
    handle cpcomplete
    """
    self.api.get('triggers.togglegroup')('cprew', True)
    self.cpinfo['finishtime'] = time.time()
    self.cpinfo['oncp'] = False
    self.savestate()

  def _cpreward(self, args=None):
    """
    handle cpreward
    """
    rtype = args['type']
    ramount = int(args['amount'])
    rewardt = self.api.get('aardu.rewardtable')()
    self.cpinfo[rewardt[rtype]] = ramount
    self.savestate()
    self.api.get('triggers.togglegroup')('cpdone', True)

  def _cpcompdone(self, _=None):
    """
    handle cpcompdone
    """
    self.api.get('events.register')('trigger_all', self._triggerall)

  def _triggerall(self, args=None):
    """
    check to see if we have the bonus qp message
    """
    if 'first campaign completed today' in args['line']:
      mat = re.match('^You receive (?P<bonus>\d*) quest points bonus ' \
                  'for your first campaign completed today.$', args['line'])
      self.cpinfo['bonusqp'] = int(mat.groupdict()['bonus'])
      self.api.get('events.unregister')('trigger_all', self._triggerall)
      self.api.get('events.eraise')('aard_cp_comp', copy.deepcopy(self.cpinfo))
    elif re.match("^You have completed (\d*) campaigns today.$", args['line']):
      self.api.get('events.unregister')('trigger_all', self._triggerall)
      self.api.get('events.eraise')('aard_cp_comp', copy.deepcopy(self.cpinfo))

  def _cpclear(self, _=None):
    """
    handle cpclear
    """
    self.cpinfo['failed'] = 1
    self.api.get('events.eraise')('aard_cp_failed', copy.deepcopy(self.cpinfo))
    self._cpnone()

  def _cpcheckcmd(self, args=None):
    """
    handle when we get a cp check
    """
    self.mobsleft = []
    self.cpinfotimer = {}
    self.api.get('triggers.togglegroup')('cpcheck', True)
    return args

  def _mobkillevent(self, args):
    """
    this will be registered to the mobkill hook
    """
    self.api.get('send.msg')('checking kill %s' % args['name'])
    self.api.get('events.unregister')('aard_mobkill', self._mobkillevent)

    found = False
    removeitem = None
    for i in range(len(self.mobsleft)):
      tmob = self.mobsleft[i]
      if tmob['name'] == args['name']:
        self.api.get('send.msg')('found %s' % tmob['name'])
        found = True
        removeitem = i

    if removeitem:
      del(self.mobsleft[removeitem])

    if found:
      self.api.get('events.eraise')('aard_cp_mobsleft',
                        copy.deepcopy({'mobsleft':self.mobsleft}))
    else:
      self.api.get('send.msg')("CP: could not find mob: %s" % args['name'])
      self.cmdqueue.addtoqueue('cpcheck', '')

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.cpinfo.sync()
