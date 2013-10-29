"""
$Id$

This plugin handles level events on Aardwolf
"""
import time
import os
import copy
import re
from libs.persistentdict import PersistentDict
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Level Events'
SNAME = 'level'
PURPOSE = 'Events for Aardwolf Level'
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
    self.savelevelfile = os.path.join(self.savedir, 'level.txt')
    self.levelinfo = PersistentDict(self.savelevelfile, 'c', format='json')

    self.api.get('setting.add')('preremort', False, bool, 'flag for pre remort')
    self.api.get('setting.add')('remortcomp', False, bool, 'flag for remort completion')
    self.api.get('setting.add')('tiering', False, bool, 'flag for tiering')
    self.api.get('setting.add')('seen2', False, bool, 'we saw a state 2 after tiering')

    self.api.get('watch.add')('shloud', {
            'regex':'^superhero loud$'})
    self.api.get('watch.add')('shsilent', {
            'regex':'^superhero silent$'})
    self.api.get('watch.add')('shconfirm', {
            'regex':'^superhero confirm$'})
    self.api.get('watch.add')('shloudconfirm', {
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

    self.api.get('events.register')('trigger_lvlpup', self._lvl)
    self.api.get('events.register')('trigger_lvlpupbless', self._lvl)
    self.api.get('events.register')('trigger_lvllevel', self._lvl)
    self.api.get('events.register')('trigger_lvlbless', self._lvl)
    self.api.get('events.register')('trigger_lvlgains', self._lvlgains)
    self.api.get('events.register')('trigger_lvlpupgains', self._lvlgains)
    self.api.get('events.register')('trigger_lvlblesstrain', self._lvlblesstrains)
    self.api.get('events.register')('trigger_lvlbonustrains', self._lvlbonustrains)
    self.api.get('events.register')('trigger_lvlbonusstat', self._lvlbonusstat)

    self.api.get('events.register')('trigger_lvlshbadstar', self._superherobad)
    self.api.get('events.register')('trigger_lvlshbad', self._superherobad)
    self.api.get('events.register')('trigger_lvlshnogold', self._superherobad)
    self.api.get('events.register')('trigger_lvlshnoqp', self._superherobad)

    self.api.get('events.register')('cmd_shloud', self.cmd_superhero)
    self.api.get('events.register')('cmd_shsilent', self.cmd_superhero)
    self.api.get('events.register')('cmd_shconfirm', self.cmd_superhero)
    self.api.get('events.register')('cmd_shloudconfirm', self.cmd_superhero)

    self.api.get('events.register')('trigger_lvlpreremort', self._preremort)
    self.api.get('events.register')('trigger_lvlremortcomp', self._remortcomp)
    self.api.get('events.register')('trigger_lvltier', self._tier)

  def _gmcpstatus(self, _=None):
    """
    check gmcp status when tiering
    """
    state = self.api.get('GMCP.getv')('char.status.state')
    if state == 2:
      self.api.get('ouput.client')('seen2')
      self.api.get('setting.change')('seen2', True)
      self.api.get('events.unregister')('GMCP:char.status', self._gmcpstatus)
      self.api.get('events.register')('GMCP:char.base', self._gmcpbase)

  def _gmcpbase(self, _=None):
    """
    look for a new base when we remort
    """
    self.api.get('output.client')('called char.base')
    state = self.api.get('GMCP.getv')('char.status.state')
    tiering = self.api.get('setting.gets')('tiering')
    seen2 = self.api.get('setting.gets')('seen2')
    if tiering and seen2 and state == 3:
      self.api.get('output.client')('in char.base')
      self.api.get('events.unregister')('GMCP:char.base', self._gmcpstatus)
      self._lvl({'level':1})

  def _tier(self, _=None):
    """
    about to tier
    """
    self.api.get('setting.change')('tiering', True)
    self.api.get('output.client')('tiering')
    self.api.get('events.register')('GMCP:char.status', self._gmcpstatus)

  def _remortcomp(self, _=None):
    """
    do stuff when a remort is complete
    """
    self.api.get('setting.change')('preremort', False)
    self.api.get('setting.change')('remortcomp',  True)
    self._lvl({'level':1})

  def _preremort(self, _=None):
    """
    set the preremort flag
    """
    self.api.get('setting.change')('preremort', True)
    self.api.get('events.eraise')('aard_level_preremort', {})

  def cmd_superhero(self, _=None):
    """
    figure out what is done when superhero is typed
    """
    self.api.get('output.client')('superhero was typed')
    self.api.get('triggers.togglegroup')('superhero', True)
    self._lvl({'level':201})

  def _superherobad(self, _=None):
    """
    undo things that we typed if we didn't really superhero
    """
    self.api.get('output.client')('didn\'t sh though')
    self.api.get('triggers.togglegroup')('superhero', False)
    self.api.get('triggers.togglegroup')('linfo', False)
    self.api.get('events.unregister')('trigger_emptyline', self._finish)

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
      self.levelinfo['level'] = self.api.get('GMCP.getv')('char.status.level')
      self.levelinfo['totallevels'] = self.api.get('aardu.getactuallevel')()
      self.levelinfo['type'] = 'pup'
    else:
      self.levelinfo['level'] = args['level']
      self.levelinfo['totallevels'] = self.api.get('aardu.getactuallevel')(
                                                            args['level'])
      self.levelinfo['type'] = 'level'

    self.api.get('triggers.togglegroup')('linfo', True)
    self.api.get('events.register')('trigger_emptyline', self._finish)


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
    remortcomp = self.api.get('setting.gets')('remortcomp')
    tiering = self.api.get('setting.gets')('tiering')
    if self.levelinfo['trains'] == 0 and not remortcomp or tiering:
      return
    self.levelinfo['finishtime'] = time.time()
    self.levelinfo.sync()
    self.api.get('triggers.togglegroup')('linfo', False)
    self.api.get('events.unregister')('trigger_emptyline', self._finish)
    self.api.get('events.eraise')('aard_level_gain', copy.deepcopy(self.levelinfo))
    if self.levelinfo['level'] == 200 and self.levelinfo['type'] == 'level':
      self.api.get('output.msg')('raising hero event', 'level')
      self.api.get('events.eraise')('aard_level_hero', {})
    elif self.levelinfo['level'] == 201 and self.levelinfo['type'] == 'level':
      self.api.get('output.msg')('raising superhero event', 'level')
      self.api.get('events.eraise')('aard_level_superhero', {})
    elif self.levelinfo['level'] == 1:
      if self.api.get('setting.gets')('tiering'):
        self.api.get('output.msg')('raising tier event', 'level')
        self.api.get('setting.change')('tiering', False)
        self.api.get('setting.change')('seen2', False)
        self.api.get('events.eraise')('aard_level_tier', {})
      else:
        self.api.get('output.msg')('raising remort event', 'level')
        self.api.get('setting.change')('remortcomp', False)
        self.api.get('events.eraise')('aard_level_remort', {})

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.levelinfo.sync()

