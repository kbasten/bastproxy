"""
$Id$
"""
import os
import time
import copy
from libs import exported
from libs.color import strip_ansi
from libs.persistentdict import PersistentDict
from plugins import BasePlugin

NAME = 'Aardwolf GQ Events'
SNAME = 'gq'
PURPOSE = 'Events for Aardwolf GQuests'
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
    self.dependencies.append('aardu')
    self.savegqfile = os.path.join(self.savedir, 'gq.txt')
    self.gqinfo = PersistentDict(self.savegqfile, 'c', format='json')
    self.addsetting('declared', False, bool, 'flag for a gq being declared')
    self.addsetting('started', False, bool, 'flag for a gq started')
    self.addsetting('joined', False, bool, 'flag for a gq joined')
    self.addsetting('extended', False, bool, 'flag for extended')
    self.mobsleft = []
    self.nextdeath = False
    self.linecount = 0
    exported.watch.add('gq_check', {
      'regex':'^(gq|gqu|gque|gques|gquest) (c|ch|che|chec|check)$'})
    self.triggers['gqdeclared'] = {
      'regex':"^Global Quest: Global quest \# (?P<gqnum>.*) has been " \
                  "declared for levels (?P<lowlev>.*) to (?P<highlev>.*)\.$"}
    self.triggers['gqjoined'] = {
      'regex':"^You have now joined the quest. See 'help gquest' " \
                  "for available commands.$"}
    self.triggers['gqstarted'] = {
      'regex':"^Global Quest: The global quest for levels " \
                  "(.*) to (.*) has now started.$"}
    self.triggers['gqnone'] = {
      'regex':"^You are not on a global quest.$",
      'enabled':False, 'group':'gqcheck'}
    self.triggers['gqitem'] = {
      'regex':"^You still have to kill (?P<num>[\d]*) \* " \
              "(?P<mob>.*?) \((?P<location>.*?)\)(|\.)$",
      'enabled':False, 'group':'gqcheck'}
    self.triggers['gqnotstarted'] = {
      'regex':"^The global quest has not yet started.$",
      'enabled':False, 'group':'gqcheck'}
    self.triggers['gqreward'] = {
      'regex':"^\s*Reward of (?P<amount>\d+) (?P<type>.+) .+ added\.$",
      'enabled':False, 'group':'gqrew'}
    self.triggers['gqmobdead'] = {
      'regex':"^Congratulations, that was one of the GLOBAL QUEST mobs!$",
      'enabled':False, 'group':'gqin'}
    self.triggers['gqwon'] = {
      'regex':"^You were the first to complete this quest!$",
      'enabled':False, 'group':'gqin'}
    self.triggers['gqwon2'] = {
      'regex':"^CONGRATULATIONS! You were the first to " \
              "complete this quest!$",
      'enabled':False, 'group':'gqin'}
    self.triggers['gqdone'] = {
      'regex':"^Global Quest: The global quest has been won " \
              "by (.*) - (.*) win.$",
      'enabled':False, 'group':'gqdone'}
    self.triggers['gqquit'] = {
      'regex':"^You are no longer part of the current quest.$",
      'enabled':False, 'group':'gqdone'}
    self.triggers['gqextover'] = {
      'regex':"^Global Quest: The extended global quest is now over.$",
      'enabled':False, 'group':'gqext'}
    self.triggers['gqextover2'] = {
      'regex':"^Global Quest: No active players remaining, " \
              "global quest is now over.$",
      'enabled':False, 'group':'gqext'}
    self.triggers['gqextfin'] = {
      'regex':"^You have finished this global quest.$",
      'enabled':False, 'group':'gqext'}
    self.triggers['gqnote'] = {
      'regex':"^INFO: New post #(?P<bdnum>.*) in forum Gquest from " \
              "Aardwolf Subj: Lvl (?P<low>.*) to (?P<high>.*) - " \
              "Global quest # (?P<gqnum>.*)$"}

    self.events['trigger_gqdeclared'] = {'func':self._gqdeclared}
    self.events['trigger_gqjoined'] = {'func':self._gqjoined}
    self.events['trigger_gqstarted'] = {'func':self._gqstarted}
    self.events['trigger_gqnone'] = {'func':self._notstarted}
    self.events['trigger_gqitem'] = {'func':self._gqitem}
    self.events['trigger_gqnotstarted'] = {'func':self._notstarted}
    self.events['trigger_gqreward'] = {'func':self._gqreward}
    self.events['trigger_gqmobdead'] = {'func':self._gqmobdead}
    self.events['trigger_gqwon'] = {'func':self._gqwon}
    self.events['trigger_gqwon2'] = {'func':self._gqwon}
    self.events['trigger_gqdone'] = {'func':self._gqdone}
    self.events['trigger_gqquit'] = {'func':self._gqquit}
    self.events['trigger_gqextover'] = {'func':self._gqextover}
    self.events['trigger_gqextover2'] = {'func':self._gqextover}
    self.events['trigger_gqextfin'] = {'func':self._gqextfin}
    self.events['trigger_gqnote'] = {'func':self._gqreset}
    self.events['cmd_gq_check'] = {'func':self._gqcheckcmd}



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
    self.gqinfo['level'] =  exported.aardu.getactuallevel(
                        exported.GMCP.getv('char.status.level'))
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
    exported.trigger.togglegroup('gqdone', True)
    exported.trigger.togglegroup('gq_start', True)
    self.variables['declared'] = True
    exported.event.eraise('aard_gq_declared', args)

  def _gqjoined(self, args):
    """
    do something when a gq is joined
    """
    exported.trigger.togglegroup('gqdone', True)
    exported.trigger.togglegroup('gq_start', True)
    self.variables['joined'] = True
    self.mobsleft = []
    if self.variables['started'] or not self.variables['declared']:
      self.variables['declared'] = True
      self._gqnew()
      self._gqstarted()
    exported.event.eraise('aard_gq_joined', args)

  def _gqstarted(self, args=None):
    """
    do something when a gq starts
    """
    if not args:
      args = {}
    self.variables['started'] = True
    self._gqnew()
    if self.variables['joined']:
      self.gqinfo['starttime'] = time.time()
      exported.trigger.togglegroup("gqin", True)
      exported.execute("gq check")

  def _gqitem(self, args):
    """
    do something with a gq item
    """
    name = args['mob']
    num = args['num']
    location = args['location']
    if not name or not location or not num:
      exported.sendtoclient("error parsing line: %s" % args['line'])
    else:
      self.mobsleft.append({'name':name, 'nocolorname':strip_ansi(name),
            'location':location, 'num':int(num)})

  def _notstarted(self, _=None):
    """
    this will be called when a gq check returns the not started message
    """
    exported.trigger.togglegroup('gqcheck', False)
    exported.trigger.togglegroup('gqin', False)
    exported.event.unregister('trigger_emptyline', self._emptyline)

  def _emptyline(self, _=None):
    """
    this will be enabled when gq check is enabled
    """
    if not self.gqinfo['mobs']:
      self.gqinfo['mobs'] = self.mobsleft[:]
      self.savestate()

    exported.trigger.togglegroup('gqcheck', False)
    exported.event.unregister('trigger_emptyline', self._emptyline)
    exported.event.eraise('aard_gq_mobsleft',
                {'mobsleft':copy.deepcopy(self.mobsleft)})

  def _gqmobdead(self, _=None):
    """
    called when a gq mob is killed
    """
    self.gqinfo['qpmobs'] = self.gqinfo['qpmobs'] + 3
    self.eventregister('aard_mobkill', self._mobkillevent)
    self.nextdeath = True

  def _mobkillevent(self, args):
    """
    this will be registered to the mobkill hook
    """
    exported.msg('checking kill %s' % args['name'], 'gq')
    self.eventregister('aard_mobkill', self._mobkillevent)

    found = False
    removeitem = None
    for i in range(len(self.mobsleft)):
      tmob = self.mobsleft[i]
      if tmob['name'] == args['name']:
        self.msg('found %s' % tmob['name'])
        found = True
        if tmob['num'] == 1:
          removeitem = i
        else:
          tmob['num'] = tmob['num'] - 1

    if removeitem:
      del(self.mobsleft[removeitem])

    if found:
      exported.event.eraise('aard_gq_mobsleft',
                        copy.deepcopy({'mobsleft':self.mobsleft}))
    else:
      exported.msg("GQ: could not find mob: %s" % args['name'], 'gq')
      exported.execute("gq check")

  def _gqwon(self, _=None):
    """
    the gquest was won
    """
    self.gqinfo['won'] = 1
    exported.trigger.togglegroup("gqrew", True)

  def _gqdone(self, _=None):
    """
    do something on the done line
    """
    if self.variables['joined'] == 0:
      return
    if self.gqinfo['won'] == 1:
      #print('I won, so no extra!')
      self._raisegq('aard_gq_won')
    else:
      #need to check for extended time
      self.linecount = 0
      exported.event.register('trigger_all', self._triggerall)

  def _triggerall(self, args=None):
    """
    do something when we see the next line after done
    """
    self.linecount = self.linecount + 1

    if 'extended time for 3 more minutes' in args['line']:
      exported.trigger.togglegroup("gqext", True)
      self.variables['extended'] = True

    if self.linecount < 3:
      return

    exported.event.unregister('trigger_all', self._triggerall)

    if not self.variables['extended']:
      self._raisegq('aard_gq_done')

  def _gqreward(self, args=None):
    """
    handle cpreward
    """
    rtype = args['type']
    ramount = args['amount']
    rewardt = exported.aardu.rewardtable()
    self.gqinfo['won'] = 1
    self.gqinfo[rewardt[rtype]] = ramount
    self.savestate()
    exported.trigger.togglegroup('gqdone', True)

  def _gqcheckcmd(self, args=None):
    """
    do something after we see a gq check
    """
    self.mobsleft = []
    exported.trigger.togglegroup('gqcheck', True)
    exported.event.register('trigger_emptyline', self._emptyline)
    return args

  def _gqquit(self, _=None):
    """
    quit the gq
    """
    self.variables['started'] = False
    self.variables['joined'] = False
    exported.event.eraise('aard_gq_quit', {})

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
    exported.event.eraise(event, copy.deepcopy(self.gqinfo))
    self._gqreset()

  def _gqreset(self, _=None):
    """
    reset gq triggers
    """
    exported.trigger.togglegroup("gqcheck", False)
    exported.trigger.togglegroup("gqin", False)
    exported.trigger.togglegroup("gqrew", False)
    exported.trigger.togglegroup("gqdone", False)
    exported.trigger.togglegroup("gqext", False)
    exported.event.unregister('aard_mobkill', self._mobkillevent)
    self.variables['joined'] = False
    self.variables['started'] = False
    self.variables['declared'] = False
    self.variables['extended'] = False
    self.savestate()

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.gqinfo.sync()
