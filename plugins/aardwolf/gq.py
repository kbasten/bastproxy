"""
This plugin handles gquest events on Aardwolf

Global Quest: Global quest # 2388 has been declared for levels 29 to 40 - Tier 0 only.
Global Quest: The quest will start in 2 ticks and will last for 97 ticks.
Global Quest: See 'Help Global Quests', or, type 'Gquest Join 2388' to take part.

Global Quest: Global quest # 2388 for levels 29 to 40 - Tier 0 only has now started.

Global Quest: Global quest # 2396 has been declared for levels 29 to 40 - 10 or fewer wins only.
Global Quest: The quest will start in 2 ticks and will last for 98 ticks.
Global Quest: See 'Help Global Quests', or, type 'Gquest Join 2396' to take part.

Global Quest: Global quest # 2396 for levels 29 to 40 - 10 or fewer wins only has now started.

Global Quest: Global quest # 2423 has been declared for levels 29 to 40.
Global Quest: The quest will start in 2 ticks and will last for 90 ticks.
Global Quest: See 'Help Global Quests', or, type 'Gquest Join 2423' to take part.

Global Quest: Global quest # 2423 for levels 29 to 40 has now started.



You have now joined Global Quest # 2396. See 'help gquest' for available commands.

Global Quest: Global quest # 2396 for levels 29 to 40 - 10 or fewer wins only has now started.

You were the first to complete this quest!

Global Quest: Global Quest # 2415 will go into extended time for 3 more minutes.

(Extended) You have finished this global quest.

Global Quest: Global Quest # 5004 has been won by Bst - 451st win.
INFO: New post #33 in forum Gquest from Aardwolf Subj: Lvl 105 to 116 - Global quest # 5004

Global Quest: Global quest # 4992 has been cancelled due to lack of participants.
Global Quest: Global quest # 5031 has been cancelled due to lack of activity.

"""
import os
import time
import copy
from libs.persistentdict import PersistentDict
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf GQ Events'
SNAME = 'gq'
PURPOSE = 'Events for Aardwolf GQuests'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf quest events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.savegqfile = os.path.join(self.savedir, 'gq.txt')
    self.gqinfo = PersistentDict(self.savegqfile, 'c')
    self._gqsdeclared = []
    self.api.get('setting.add')('gqnum', -1, int,
                                'the gquest # that was joined')
    self.api.get('setting.add')('declared', False, bool,
                                'flag for a gq being declared')
    self.api.get('setting.add')('started', False, bool,
                                'flag for a gq started')
    self.api.get('setting.add')('joined', False, bool, 'flag for a gq joined')
    self.api.get('setting.add')('extended', False, bool, 'flag for extended')
    self.mobsleft = []
    self.nextdeath = False
    self.linecount = 0

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)
    self.api.get('watch.add')('gq_check',
      '^(gq|gqu|gque|gques|gquest) (c|ch|che|chec|check)$')

    self.api.get('triggers.add')('gqdeclared',
                  "^Global Quest: Global quest \#(?P<gqnum>.*) has been " \
                    "declared for levels (?P<lowlev>.*) to (?P<highlev>.*) .*$")
    self.api.get('triggers.add')('gqjoined',
                  "^You have now joined Global Quest \#(?P<gqnum>.*)\. .*$")
    self.api.get('triggers.add')('gqstarted',
                  "^Global Quest: Global quest \#(.*) for levels .*$")
    self.api.get('triggers.add')('gqnone',
                  "^You are not on a global quest.$",
                  enabled=False, group='gqcheck')
    self.api.get('triggers.add')('gqitem',
                  "^You still have to kill (?P<num>[\d]*) \* " \
                    "(?P<mob>.*?) \((?P<location>.*?)\)(|\.)$",
                  enabled=False, group='gqcheck')
    self.api.get('triggers.add')('gqnotstarted',
                  "^The global quest has not yet started.$",
                  enabled=False, group='gqcheck')
    self.api.get('triggers.add')('gqreward',
                  "^\s*Reward of (?P<amount>\d+) (?P<type>.+) .+ added\.$",
                  enabled=False, group='gqrew')
    self.api.get('triggers.add')('gqmobdead',
                  "^Congratulations, that was one of the GLOBAL QUEST mobs!$",
                  enabled=False, group='gqin')
    self.api.get('triggers.add')('gqwon',
                  "^You were the first to complete this quest!$",
                  enabled=False, group='gqin')
    self.api.get('triggers.add')('gqwon2',
                  "^CONGRATULATIONS! You were the first to " \
                    "complete this quest!$",
                  enabled=False, group='gqin')
    self.api.get('triggers.add')('gqdone',
                  "Global Quest: Global Quest \#(?P<gqnum>.*) has been won " \
                    "by (.*) - (.*) win.$",
                  enabled=False, group='gqdone')
    self.api.get('triggers.add')('gqquit',
                  "^You are no longer part of Global Quest \#(.*) and " \
                    "will be unable to rejoin.$",
                  enabled=False, group='gqdone')
    self.api.get('triggers.add')('gqextover',
                  "^Global Quest: Global quest \#(.*) (extended) is now over.$",
                  enabled=False, group='gqext')
    self.api.get('triggers.add')('gqextover2',
                  "^Global Quest: No active players remaining, " \
                    "global quest \#(.*) is now over.$",
                  enabled=False, group='gqext')
    self.api.get('triggers.add')('gqextfin',
                  "^You have finished this global quest.$",
                  enabled=False, group='gqext')
    self.api.get('triggers.add')('gqnote',
                  "^INFO: New post \#(?P<bdnum>.*) in forum Gquest from " \
                    "Aardwolf Subj: Lvl (?P<low>.*) to (?P<high>.*) - " \
                    "Global quest \#(?P<gqnum>.*)$")
    self.api.get('triggers.add')('gqmaxkills', "^You have reached the " \
        "maximum (.*) kills for which you can earn quest points this level\.$")

    self.api.get('events.register')('trigger_gqdeclared', self._gqdeclared)
    self.api.get('events.register')('trigger_gqjoined', self._gqjoined)
    self.api.get('events.register')('trigger_gqstarted', self._gqstarted)
    self.api.get('events.register')('trigger_gqnone', self._notstarted)
    self.api.get('events.register')('trigger_gqitem', self._gqitem)
    self.api.get('events.register')('trigger_gqnotstarted', self._notstarted)
    self.api.get('events.register')('trigger_gqreward', self._gqreward)
    self.api.get('events.register')('trigger_gqmobdead', self._gqmobdead)
    self.api.get('events.register')('trigger_gqwon', self._gqwon)
    self.api.get('events.register')('trigger_gqwon2', self._gqwon)
    self.api.get('events.register')('trigger_gqdone', self._gqdone)
    self.api.get('events.register')('trigger_gqquit', self._gqquit)
    self.api.get('events.register')('trigger_gqextover', self._gqextover)
    self.api.get('events.register')('trigger_gqextover2', self._gqextover)
    self.api.get('events.register')('trigger_gqextfin', self._gqextfin)
    self.api.get('events.register')('trigger_gqnote', self._gqreset)
    self.api.get('events.register')('trigger_maxkills', self._gqmaxkills)
    self.api.get('events.register')('watch_gq_check', self._gqcheckcmd)

  def _gqnew(self):
    """
    reset the gq info
    """
    self.gqinfo.clear()
    self.gqinfo['mobs'] = {}
    self.gqinfo['trains'] = 0
    self.gqinfo['pracs'] = 0
    self.gqinfo['gold'] = 0
    self.gqinfo['tp'] = 0
    self.gqinfo['qp'] = 0
    self.gqinfo['qpmobs'] = 0
    self.gqinfo['level'] =  self.api.get('aardu.getactuallevel')(
                        self.api.get('GMCP.getv')('char.status.level'))
    self.gqinfo['starttime'] = 0
    self.gqinfo['finishtime'] = 0
    self.gqinfo['length'] = 0
    self.gqinfo['won'] = 0
    self.gqinfo['completed'] = 0
    self.savestate()

  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    self._gqnew()
    self._gqsdeclared.append(int(args['gqnum']))
    self.api.get('triggers.togglegroup')('gqdone', True)
    self.api.get('triggers.togglegroup')('gq_start', True)
    self.api.get('setting.change')('declared', True)
    self.api.get('events.eraise')('aard_gq_declared', args)

  def _gqjoined(self, args):
    """
    do something when a gq is joined
    """
    self.api('send.client')('gq_joined: %s' % args)
    self.api.get('triggers.togglegroup')('gqdone', True)
    self.api.get('triggers.togglegroup')('gq_start', True)
    self.api.get('setting.change')('joined', True)

    self.mobsleft = []
    self.api('setting.change')('gqnum', int(args['gqnum']))
    if self.api.get('setting.gets')('started') \
        or not self.api.get('setting.gets')('declared'):
      self.api.get('setting.change')('declared', True)
      self._gqnew()
      self._gqstarted()
    self.api.get('events.eraise')('aard_gq_joined', args)

  def _gqstarted(self, args=None):
    """
    do something when a gq starts
    """
    if not args:
      args = {}
    self.api.get('setting.change')('started', True)
    self._gqnew()
    if self.api.get('setting.gets')('joined'):
      self.gqinfo['starttime'] = time.time()
      self.api.get('triggers.togglegroup')("gqin", True)
      self.api.get('send.execute')("gq check")

  def _gqitem(self, args):
    """
    do something with a gq item
    """
    name = args['mob']
    num = args['num']
    location = args['location']
    if not name or not location or not num:
      self.api.get('send.client')("error parsing line: %s" % args['line'])
    else:
      self.mobsleft.append({'name':name,
                    'nocolorname':self.api.get('colors.stripansi')(name),
                    'location':location, 'num':int(num)})

  def _notstarted(self, _=None):
    """
    this will be called when a gq check returns the not started message
    """
    self.api.get('triggers.togglegroup')('gqcheck', False)
    self.api.get('triggers.togglegroup')('gqin', False)
    self.api.get('events.unregister')('trigger_emptyline', self._emptyline)

  def _emptyline(self, _=None):
    """
    this will be enabled when gq check is enabled
    """
    if not self.gqinfo['mobs']:
      self.gqinfo['mobs'] = self.mobsleft[:]
      self.savestate()

    self.api.get('triggers.togglegroup')('gqcheck', False)
    self.api.get('events.unregister')('trigger_emptyline', self._emptyline)
    self.api.get('events.eraise')('aard_gq_mobsleft',
                {'mobsleft':copy.deepcopy(self.mobsleft)})

  def _gqmobdead(self, _=None):
    """
    called when a gq mob is killed
    """
    self.gqinfo['qpmobs'] = self.gqinfo['qpmobs'] + 3
    self.api.get('events.register')('aard_mobkill', self._mobkillevent)
    self.nextdeath = True

  def _gqmaxkills(self, args):
   """
   didn't get xp for that last kill
   """
   self.gqinfo['qpmobs'] = self.gqinfo['gqmobs'] - 3

  def _mobkillevent(self, args):
    """
    this will be registered to the mobkill hook
    """
    self.api.get('send.msg')('checking kill %s' % args['name'])
    self.api.get('events.register')('aard_mobkill', self._mobkillevent)

    found = False
    removeitem = None
    for i in range(len(self.mobsleft)):
      tmob = self.mobsleft[i]
      if tmob['name'] == args['name']:
        self.api.get('send.msg')('found %s' % tmob['name'])
        found = True
        if tmob['num'] == 1:
          removeitem = i
        else:
          tmob['num'] = tmob['num'] - 1

    if removeitem:
      del(self.mobsleft[removeitem])

    if found:
      self.api.get('events.eraise')('aard_gq_mobsleft',
                        copy.deepcopy({'mobsleft':self.mobsleft}))
    else:
      self.api.get('send.msg')("GQ: could not find mob: %s" % args['name'])
      self.api.get('send.execute')("gq check")

  def _gqwon(self, _=None):
    """
    the gquest was won
    """
    self.gqinfo['won'] = 1
    self.api.get('triggers.togglegroup')("gqrew", True)

  def _gqdone(self, args=None):
    """
    do something on the done line
    """
    if self.api.get('setting.gets')('joined') == 0:
      return
    if args and int(args['gqnum']) == self.api('setting.gets')('gqnum') and \
                self.gqinfo['won'] == 1:
      #print('I won, so no extra!')
      self._raisegq('aard_gq_won')
    else:
      #need to check for extended time
      self.linecount = 0
      self.api.get('events.register')('trigger_all', self._triggerall)

  def _triggerall(self, args=None):
    """
    do something when we see the next line after done
    """
    self.linecount = self.linecount + 1

    if 'extended time for 3 more minutes' in args['line']:
      self.api.get('triggers.togglegroup')("gqext", True)
      self.api.get('setting.change')('extended', True)

    if self.linecount < 3:
      return

    self.api.get('events.unregister')('trigger_all', self._triggerall)

    if not self.api.get('setting.gets')('extended'):
      self._raisegq('aard_gq_done')

  def _gqreward(self, args=None):
    """
    handle cpreward
    """
    rtype = args['type']
    ramount = args['amount']
    rewardt = self.api.get('aardu.rewardtable')()
    self.gqinfo['won'] = 1
    self.gqinfo[rewardt[rtype]] = ramount
    self.savestate()
    self.api.get('triggers.togglegroup')('gqdone', True)

  def _gqcheckcmd(self, args=None):
    """
    do something after we see a gq check
    """
    self.mobsleft = []
    self.api.get('triggers.togglegroup')('gqcheck', True)
    self.api.get('events.register')('trigger_emptyline', self._emptyline)
    return args

  def _gqquit(self, _=None):
    """
    quit the gq
    """
    self.api.get('setting.change')('started', False)
    self.api.get('setting.change')('joined', False)
    self.api.get('events.eraise')('aard_gq_quit', {})

  def _gqextfin(self, _=None):
    """
    the character finished the extended gq
    """
    self.gqinfo['completed'] = 1
    self._raisegq('aard_gq_completed')

  def _gqextover(self, _=None):
    """
    the character finished the extended gq
    """
    self._raisegq('aard_gq_done')

  def _raisegq(self, event):
    """
    raise a gq event
    """
    self.gqinfo['finishtime'] = time.time()
    self.savestate()
    self.api.get('events.eraise')(event, copy.deepcopy(self.gqinfo))
    self._gqreset()

  def _gqreset(self, args=None):
    """
    reset gq triggers
    """
    if args:
      if not (args['gqnum'] == self.api('setting.gets')('gqnum')):
        return
    self.api.get('triggers.togglegroup')("gqcheck", False)
    self.api.get('triggers.togglegroup')("gqin", False)
    self.api.get('triggers.togglegroup')("gqrew", False)
    self.api.get('triggers.togglegroup')("gqdone", False)
    self.api.get('triggers.togglegroup')("gqext", False)
    self.api.get('events.unregister')('aard_mobkill', self._mobkillevent)
    self.api.get('setting.change')('joined', False)
    self.api.get('setting.change')('started', False)
    self.api.get('setting.change')('declared', False)
    self.api.get('setting.change')('extended', False)
    self.savestate()

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.gqinfo.sync()
