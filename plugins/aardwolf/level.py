"""
$Id$
"""
import time
import os
import copy
import re
from libs import exported
from libs.persistentdict import PersistentDict
from plugins import BasePlugin

NAME = 'Aardwolf Level Events'
SNAME = 'level'
PURPOSE = 'Events for Aardwolf Level'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.savelevelfile = os.path.join(self.savedir, 'level.txt')
    self.levelinfo = PersistentDict(self.savelevelfile, 'c', format='json')
    self.dependencies.append('aardu')

    self.addsetting('preremort', False, bool, 'flag for pre remort')
    self.addsetting('remortcomp', False, bool, 'flag for remort completion')
    self.addsetting('tiering', False, bool, 'flag for tiering')
    self.addsetting('seen2', False, bool, 'we saw a state 2 after tiering')

    exported.watch.add('shloud', {
            'regex':'^superhero loud$'})
    exported.watch.add('shsilent', {
            'regex':'^superhero silent$'})
    exported.watch.add('shconfirm', {
            'regex':'^superhero confirm$'})
    exported.watch.add('shloudconfirm', {
            'regex':'^superhero loud confirm$'})

    self.triggers['lvlpup'] = {
      'regex':"^Congratulations, hero. You have increased your powers!$"}
    self.triggers['lvlpupbless'] = {
      'regex':"^You gain a powerup\.$"}
    self.triggers['lvllevel'] = {
      'regex':"^You raise a level! You are now level (?P<level>\d*).$",
      'argtypes':{'level':int}}
    self.triggers['lvlsh'] = {
      'regex':"^Congratulations! You are now a superhero!$",
      'argtypes':{'level':int}}
    self.triggers['lvlbless'] = {
      'regex':"^You gain a level - you are now level (?P<level>\d*).$",
      'argtypes':{'level':int}}
    self.triggers['lvlgains'] = {
      'regex':"^You gain (?P<hp>\d*) hit points, (?P<mp>\d*) mana, "\
          "(?P<mv>\d*) moves, (?P<pr>\d*) practices and (?P<tr>\d*) trains.$",
            'enabled':False, 'group':'linfo',
            'argtypes':{'hp':int, 'mn':int, 'mv':int, 'pr':int, 'tr':int}}
    self.triggers['lvlblesstrain'] = {
      'regex':"^You gain (?P<tr>\d*) extra trains? daily blessing bonus.$",
      'enabled':False, 'group':'linfo',
      'argtypes':{'tr':int}}
    self.triggers['lvlpupgains'] = {
      'regex':"^You gain (?P<tr>\d*) trains.$",
      'enabled':False, 'group':'linfo',
      'argtypes':{'tr':int}}
    self.triggers['lvlbonustrains'] = {
      'regex':"^Lucky! You gain an extra (?P<tr>\d*) training sessions?!$",
      'enabled':False, 'group':'linfo',
      'argtypes':{'tr':int}}
    self.triggers['lvlbonusstat'] = {
      'regex':"^You gain a bonus (?P<stat>.*) point!$",
      'enabled':False, 'group':'linfo'}

    self.triggers['lvlshbadstar'] = {
      'regex':"^%s$" % re.escape("*******************************" \
              "****************************************"),
      'enabled':False, 'group':'superhero'}
    self.triggers['lvlshbad'] = {
      'regex':"^Use either: 'superhero loud'   - (?P<mins>.*) mins of " \
              "double xp, (?P<qp>.*)qp and (?P<gold>.*) gold$",
      'enabled':False, 'group':'superhero'}
    self.triggers['lvlshnogold'] = {
      'regex':"^You must be carrying at least 500,000 gold coins.$",
      'enabled':False, 'group':'superhero'}
    self.triggers['lvlshnoqp'] = {
      'regex':"^You must have at least 1000 quest points.$",
      'enabled':False, 'group':'superhero'}

    self.triggers['lvlpreremort'] = {
      'regex':"^You are now flagged as remorting.$",
      'enabled':True, 'group':'remort'}
    self.triggers['lvlremortcomp'] = {
      'regex':"^\* Remort transformation complete!$",
      'enabled':True, 'group':'remort'}
    self.triggers['lvltier'] = {
      'regex':"^## You have already remorted the max number of times.$",
      'enabled':True, 'group':'remort'}

    self.events['trigger_lvlpup'] = {'func':self._lvl}
    self.events['trigger_lvlpupbless'] = {'func':self._lvl}
    self.events['trigger_lvllevel'] = {'func':self._lvl}
    self.events['trigger_lvlbless'] = {'func':self._lvl}
    self.events['trigger_lvlgains'] = {'func':self._lvlgains}
    self.events['trigger_lvlpupgains'] = {'func':self._lvlgains}
    self.events['trigger_lvlblesstrain'] = {'func':self._lvlblesstrains}
    self.events['trigger_lvlbonustrains'] = {'func':self._lvlbonustrains}
    self.events['trigger_lvlbonusstat'] = {'func':self._lvlbonusstat}

    self.events['trigger_lvlshbadstar'] = {'func':self._superherobad}
    self.events['trigger_lvlshbad'] = {'func':self._superherobad}
    self.events['trigger_lvlshnogold'] = {'func':self._superherobad}
    self.events['trigger_lvlshnoqp'] = {'func':self._superherobad}

    self.events['cmd_shloud'] = {'func':self.cmd_superhero}
    self.events['cmd_shsilent'] = {'func':self.cmd_superhero}
    self.events['cmd_shconfirm'] = {'func':self.cmd_superhero}
    self.events['cmd_shloudconfirm'] = {'func':self.cmd_superhero}

    self.events['trigger_lvlpreremort'] = {'func':self._preremort}
    self.events['trigger_lvlremortcomp'] = {'func':self._remortcomp}
    self.events['trigger_lvltier'] = {'func':self._tier}

  def _gmcpstatus(self, _=None):
    """
    check gmcp status when tiering
    """
    state = exported.GMCP.getv('char.status.state')
    if state == 2:
      exported.sendtoclient('seen2')
      self.variables['seen2'] = True
      exported.event.unregister('GMCP:char.status', self._gmcpstatus)
      exported.event.register('GMCP:char.base', self._gmcpbase)

  def _gmcpbase(self, _=None):
    """
    look for a new base when we remort
    """
    exported.sendtoclient('called char.base')
    state = exported.GMCP.getv('char.status.state')
    if self.variables['tiering'] and self.variables['seen2'] and state == 3:
      exported.sendtoclient('in char.base')
      exported.event.unregister('GMCP:char.base', self._gmcpstatus)
      self._lvl({'level':1})

  def _tier(self, _=None):
    """
    about to tier
    """
    self.variables['tiering'] = True
    exported.sendtoclient('tiering')
    exported.event.register('GMCP:char.status', self._gmcpstatus)

  def _remortcomp(self, _=None):
    """
    do stuff when a remort is complete
    """
    self.variables['preremort'] = False
    self.variables['remortcomp'] = True
    self._lvl({'level':1})

  def _preremort(self, _=None):
    """
    set the preremort flag
    """
    self.variables['preremort'] = True
    exported.event.eraise('aard_level_preremort', {})

  def cmd_superhero(self, _=None):
    """
    figure out what is done when superhero is typed
    """
    exported.sendtoclient('superhero was typed')
    print 'trying to got a sh'
    exported.trigger.togglegroup('superhero', True)
    self._lvl({'level':201})

  def _superherobad(self, _=None):
    """
    undo things that we typed if we didn't really superhero
    """
    exported.sendtoclient('didn\'t sh though')
    print 'didn\'t sh though'
    exported.trigger.togglegroup('superhero', False)
    exported.trigger.togglegroup('linfo', False)
    exported.event.unregister('trigger_emptyline', self._finish)

  def resetlevel(self):
    """
    reset the level info, use the finishtime of the last level as
    the starttime of the next level
    """
    if 'finishtime' in self.levelinfo and self.levelinfo['finishtime'] > 0:
      starttime = self.levelinfo['finishtime']
    else:
      starttime = time.time()
    self.levelinfo.clear()
    self.levelinfo['type'] = ""
    self.levelinfo['level'] = -1
    self.levelinfo['str'] = 0
    self.levelinfo['int'] = 0
    self.levelinfo['wis'] = 0
    self.levelinfo['dex'] = 0
    self.levelinfo['con'] = 0
    self.levelinfo['luc'] = 0
    self.levelinfo['starttime'] = starttime
    self.levelinfo['hp'] = 0
    self.levelinfo['mp'] = 0
    self.levelinfo['mv'] = 0
    self.levelinfo['pracs'] = 0
    self.levelinfo['trains'] = 0
    self.levelinfo['bonustrains'] = 0
    self.levelinfo['blessingtrains'] = 0
    self.levelinfo['totallevels'] = 0

  def _lvl(self, args=None):
    """
    trigger for leveling
    """
    if not args:
      return

    self.resetlevel()
    if 'triggername' in args and (args['triggername'] == 'lvlpup' \
        or args['triggername'] == 'lvlpupbless'):
      self.levelinfo['level'] = exported.GMCP.getv('char.status.level')
      self.levelinfo['totallevels'] = exported.aardu.getactuallevel()
      self.levelinfo['type'] = 'pup'
    else:
      self.levelinfo['level'] = args['level']
      self.levelinfo['totallevels'] = exported.aardu.getactuallevel(
                                                            args['level'])
      self.levelinfo['type'] = 'level'

    exported.trigger.togglegroup('linfo', True)
    exported.event.register('trigger_emptyline', self._finish)


  def _lvlblesstrains(self, args):
    """
    trigger for blessing trains
    """
    self.levelinfo['blessingtrains'] = args['tr']

  def _lvlbonustrains(self, args):
    """
    trigger for bonus trains
    """
    self.levelinfo['bonustrains'] = args['tr']

  def _lvlbonusstat(self, args):
    """
    trigger for bonus stats
    """
    self.levelinfo[args['stat'][:3].lower()] = 1

  def _lvlgains(self, args):
    """
    trigger for level gains
    """
    self.levelinfo['trains'] = args['tr']

    if args['triggername'] == "lvlgains":
      self.levelinfo['hp'] = args['hp']
      self.levelinfo['mp'] = args['mp']
      self.levelinfo['mv'] = args['mv']
      self.levelinfo['pracs'] = args['pr']

  def _finish(self, _):
    """
    finish up and raise the level event
    """
    if self.levelinfo['trains'] == 0 and not (self.variables['remortcomp'] \
            or self.variables['tiering']):
      return
    self.levelinfo['finishtime'] = time.time()
    self.levelinfo.sync()
    exported.trigger.togglegroup('linfo', False)
    exported.event.unregister('trigger_emptyline', self._finish)
    exported.event.eraise('aard_level_gain', copy.deepcopy(self.levelinfo))
    if self.levelinfo['level'] == 200 and self.levelinfo['type'] == 'level':
      exported.msg('raising hero event', 'level')
      exported.event.eraise('aard_level_hero', {})
    elif self.levelinfo['level'] == 201 and self.levelinfo['type'] == 'level':
      exported.msg('raising superhero event', 'level')
      exported.event.eraise('aard_level_superhero', {})
    elif self.levelinfo['level'] == 1:
      if self.variables['tiering']:
        exported.msg('raising tier event', 'level')
        self.variables['tiering'] = False
        self.variables['seen2'] = False
        exported.event.eraise('aard_level_tier', {})
      else:
        exported.msg('raising remort event', 'level')
        self.variables['remortcomp'] = False
        exported.event.eraise('aard_level_remort', {})

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.levelinfo.sync()

