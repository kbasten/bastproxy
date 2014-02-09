"""
$Id$

This plugin handles cp events for Aardwolf
"""
import time
import os
import copy
import re
from libs import utils
from libs.color import strip_ansi
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
    self.cpinfo = PersistentDict(self.savecpfile, 'c', format='json')
    self.mobsleft = []
    self.cpinfotimer = {}
    self.linecount = 0
    self.nextdeath = False

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('watch.add')('cp_check',
      '^(cp|campa|campai|campaig|campaign) (c|ch|che|chec|check)$')

    self.api.get('triggers.add')('cpnew',
      "^Commander Barcett tells you " \
        "'Type 'campaign info' to see what you must kill.'$")
    self.api.get('triggers.add')('cpnone',
      "^You are not currently on a campaign.$",
      enabled=False,
      group='cpcheck')
    self.api.get('triggers.add')('cptime',
      "^You have (?P<time>.*) to finish this campaign.$",
      enabled=False,
      group='cpcheck')
    self.api.get('triggers.add')('cpmob',
      "^You still have to kill \* (?P<mob>.*) " \
            "\((?P<location>.*?)(?P<dead> - Dead|)\)$",
      enabled=False,
      group='cpcheck')
    self.api.get('triggers.add')('cpneedtolevel',
      "^You will have to level before you" \
                " can go on another campaign.$",
      enabled=False,
      group='cpin')
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
    self.api.get('events.register')('watch_cp_check', self._cpcheckcmd)
    self.api.get('events.register')('trigger_cpmob', self._cpmob)
    self.api.get('events.register')('trigger_cpneedtolevel', self._cpneedtolevel)
    self.api.get('events.register')('trigger_cpcantake', self._cpcantake)
    self.api.get('events.register')('trigger_cpshnext', self._cpshnext)
    self.api.get('events.register')('trigger_cpmobdead', self._cpmobdead)
    self.api.get('events.register')('trigger_cpcomplete', self._cpcomplete)
    self.api.get('events.register')('trigger_cpclear', self._cpclear)
    self.api.get('events.register')('trigger_cpreward', self._cpreward)
    self.api.get('events.register')('trigger_cpcompdone', self._cpcompdone)

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
    self.api.get('send.client')('cpnew: %s' % args)
    self._cpreset()

  def _cpnone(self, _=None):
    """
    handle a none cp
    """
    self.cpinfo['oncp'] = False
    self.savestate()
    self.api.get('triggers.togglegroup')('cpcheck', False)
    self.api.get('triggers.togglegroup')('cpin', False)
    self.api.get('triggers.togglegroup')('cprew', False)
    self.api.get('triggers.togglegroup')('cpdone', False)
    #check(EnableTimer("cp_timer", false))
    self.cpinfotimer = {}
    self.api.get('send.client')('cpnone')

  def _cptime(self, _=None):
    """
    handle cp time
    """
    self.api.get('output.msg')('handling cp time')
    self.api.get('output.msg')('%s' % self.cpinfo)
    if not self.cpinfo['mobs']:
      self.api.get('output.msg')('copying mobsleft')
      self.cpinfo['mobs'] = self.mobsleft[:]
      self.savestate()

    self.api.get('output.msg')('raising aard_cp_mobsleft %s' % self.mobsleft)
    self.api.get('events.eraise')('aard_cp_mobsleft',
                    copy.deepcopy({'mobsleft':self.mobsleft}))
    self.api.get('triggers.togglegroup')("cpcheck", False)
    self.api.get('triggers.togglegroup')("cpin", True)

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
    mobdead = utils.verify(args['dead'], bool)
    location = args['location']

    if not name or not location:
      self.api.get('send.client')("error parsing line: %s" % args['line'])
    else:
      #self.mobsleft.append({'name':name, 'location':location,
      #'clean':cleanname(name), 'mobdead':mobdead})
      self.mobsleft.append({'name':name, 'nocolorname':strip_ansi(name),
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
    self.linecount = 0
    self.api.get('events.register')('trigger_all', self._triggerall)

  def _triggerall(self, args=None):
    """
    check to see if we have the bonus qp message
    """
    self.linecount = self.linecount + 1
    if 'first campaign completed today' in args['line']:
      mat = re.match('^You receive (?P<bonus>\d*) quest points bonus ' \
                  'for your first campaign completed today.$', args['line'])
      self.cpinfo['bonusqp'] = int(mat.groupdict()['bonus'])
    if self.linecount > 3:
      self.api.get('events.unregister')('trigger_all', self._triggerall)
    if self.linecount == 3:
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
    self.api.get('output.msg')('checking kill %s' % args['name'])
    self.api.get('events.unregister')('aard_mobkill', self._mobkillevent)

    found = False
    removeitem = None
    for i in range(len(self.mobsleft)):
      tmob = self.mobsleft[i]
      if tmob['name'] == args['name']:
        self.api.get('output.msg')('found %s' % tmob['name'])
        found = True
        removeitem = i

    if removeitem:
      del(self.mobsleft[removeitem])

    if found:
      self.api.get('events.eraise')('aard_cp_mobsleft',
                        copy.deepcopy({'mobsleft':self.mobsleft}))
    else:
      self.api.get('output.msg')("CP: could not find mob: %s" % args['name'])
      self.api.get('send.execute')("cp check")

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.cpinfo.sync()
