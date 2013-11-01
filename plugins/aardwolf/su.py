"""
$Id$

This plugin keeps up spells/skills for Aardwolf
"""
import copy
import time
import os
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin
from libs.timing import timeit
from libs.persistentdict import PersistentDict

NAME = 'Spellup'
SNAME = 'su'
PURPOSE = 'spellup plugin'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.spellupfile = os.path.join(self.savedir, 'spellups.txt')
    self.spellups = PersistentDict(self.spellupfile, 'c', format='json')

    self.api.get('dependency.add')('skills')
    self.api.get('dependency.add')('move')

    self.initspellups()

    self.lastmana = -1
    self.lastmoves = -1

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('enabled', True, bool,
                      'auto spellup is enabled')
    self.api.get('setting.add')('waiting', -1, int,
                      'the spell that was just cast',
                      readonly=True)
    self.api.get('setting.add')('nocast', False, bool,
                      'in a nocast room',
                      readonly=True)
    self.api.get('setting.add')('nomoves', False, bool,
                      'need more moves',
                      readonly=True)
    self.api.get('setting.add')('nomana', False, bool,
                      'need more mana',
                      readonly=True)
    self.api.get('setting.add')('nocastrooms', {}, dict,
                      'list of nocast rooms',
                      readonly=True)
    self.api.get('setting.add')('currentroom', -1, int,
                      'the current room',
                      readonly=True)

    self.api.get('commands.add')('sadd', self.cmd_sadd,
              shelp='add a spellup to the self list')
    self.api.get('commands.add')('slist', self.cmd_slist,
              shelp='list spellups')
    self.api.get('commands.add')('srem', self.cmd_srem,
              shelp='remove a spellup from self list')
    self.api.get('commands.add')('sen', self.cmd_sen,
              shelp='enable a spellup on self')
    self.api.get('commands.add')('sdis', self.cmd_sdis,
              shelp='disable a spellup on self')

    self.api.get('events.register')('GMCP:char.vitals', self._charvitals)
    self.api.get('events.register')('GMCP:char.status', self._charstatus)
    self.api.get('events.register')('moved_room', self._moved)
    self.api.get('events.register')('skill_fail', self._skillfail)
    self.api.get('events.register')('aard_skill_affon', self._affon)
    self.api.get('events.register')('aard_skill_affoff', self._affoff)
    self.api.get('events.register')('aard_skill_recoff', self._recoff)
    self.api.get('events.register')('su_enabled', self.enabledchange)
    self.api.get('events.register')('skills_affected_update', self.nextspell)
    self.api.get('events.register')('aard_skill_gain', self.skillgain)

  def skillgain(self, args=None):
    """
    check skills when we gain them
    """
    if args['sn'] in self.spellups['sorder'] and args['percent'] > 50:
      self.nextspell()

  def initspellups(self):
    """
    initialize the spellups dictionary
    """
    if not 'sorder' in self.spellups:
      self.spellups['sorder'] = []
    if not 'self' in self.spellups:
      self.spellups['self'] = {}
    if not 'oorder' in self.spellups:
      self.spellups['oorder'] = []
    if not 'other' in self.spellups:
      self.spellups['other'] = {}

  def enabledchange(self, args):
    """
    do something when enabled is changed
    """
    if args['newvalue']:
      self.nextspell()

  def _affon(self, args):
    """
    catch an affon event
    """
    if args['sn'] == self.api.get('setting.gets')('waiting'):
      self.api.get('setting.change')('waiting', -1)
    self.nextspell()

  def _affoff(self, args):
    """
    catch an affoff event
    """
    self.nextspell()

  def _recoff(self, args):
    """
    catch an affoff event
    """
    self.nextspell()

  def _skillfail(self, args):
    """
    catch a skill fail event
    """
    self.api.get('output.msg')('skillfail: %s' % args)
    sn = args['sn']
    waiting = self.api.get('setting.gets')('waiting')
    if args['reason'] == 'nomana':
      self.api.get('setting.change')('waiting', -1)
      self.api.get('setting.change')('nomana', True)
      self.lastmana = self.api.get('GMCP.getv')('char.vitals.mana')
    elif args['reason'] == 'nocastroom':
      self.api.get('setting.change')('waiting', -1)
      self.api.get('setting.change')('nocast', True)
      nocastrooms = self.api.get('setting.gets')('nocastrooms')
      currentroom = self.api.get('setting.gets')('currentroom')
      nocastrooms[currentroom] = True
    elif args['reason'] == 'fighting' or args['reason'] == 'notactive':
      self.api.get('setting.change')('waiting', -1)
    elif args['reason'] == 'nomoves':
      self.api.get('setting.change')('waiting', -1)
      self.api.get('setting.change')('nomoves', True)
      self.lastmana = self.api.get('GMCP.getv')('char.vitals.moves')
    elif waiting == sn:
      if args['reason'] == 'lostconc':
        self.api.get('skills.sendcmd')(waiting)
      elif args['reason'] == 'alreadyaff':
        self.api.get('setting.change')('waiting', -1)
        skill = self.api.get('skills.gets')(sn)
        self.api.get('output.client')(
          "@BSpellup - disabled %s because you are already affected" % \
                                  skill['name'])
        if sn in self.spellups['self']:
          self.spellups['self'][sn]['enabled'] = False
        #if sn in self.spellups['other']:
          #self.spellups['other'][sn]['enabled'] = False
        self.nextspell()
      elif args['reason'] == 'recblock':
        # do stuff when blocked by a recovery
        self.api.get('setting.change')('waiting', -1)
        self.nextspell()
      elif args['reason'] == 'dontknow':
        # do stuff when spell/skill isn't learned
        self.api.get('setting.change')('waiting', -1)
        self.nextspell()
      elif args['reason'] == 'wrongtarget':
        # do stuff when a wrong target
        self.api.get('setting.change')('waiting', -1)
        self.nextspell()
      elif args['reason'] == 'disabled':
        self.api.get('setting.change')('waiting', -1)
        skill = self.api.get('skills.gets')(sn)
        self.api.get('output.client')(
          "@BSpellup - disabled %s because it is disabled mudside" % \
                                  skill['name'])
        if sn in self.spellups['self']:
          self.spellups['self'][sn]['enabled'] = False
        if sn in self.spellups['other']:
          self.spellups['other'][sn]['enabled'] = False
        self.nextspell()

  def _moved(self, args):
    """
    reset stuff if we move
    """
    self.api.get('setting.change')('currentroom', args['to']['num'])
    nocastrooms = self.api.get('setting.gets')('nocastrooms')
    if args['to']['num'] in nocastrooms:
      self.api.get('setting.change')('nocast', True)
    else:
      self.api.get('setting.change')('nocast', False)

  def _charvitals(self, args):
    """
    check if we have more mana and moves
    """
    if self.api.get('setting.gets')('nomana'):
      newmana = self.api.get('GMCP.getv')('char.vitals.mana')
      if newmana > self.lastmana:
        self.lastmana = -1
        self.api.get('setting.change')('nomana', False)
        self.nextspell()
    if self.api.get('setting.gets')('nomoves'):
      newmoves = self.api.get('GMCP.getv')('char.vitals.moves')
      if newmoves > self.lastmoves:
        self.lastmoves = -1
        self.api.get('setting.change')('nomoves', False)
        self.nextspell()

  def _charstatus(self, _=None):
    """
    check if we have more mana and moves
    """
    status = self.api.get('GMCP.getv')('char.status.state')
    if status == 3 and self.api.get('skills.isuptodate')():
      self.nextspell()

  @timeit
  def check(self, _=None):
    """
    check to cast the next spell
    """
    proxy = self.api.get('managers.getm')('proxy')
    if not proxy:
      return False
    self.api.get('output.msg')('waiting type: %s' % type(self.api.get('setting.gets')('waiting')))
    self.api.get('output.msg')('currentstatus = %s' % self.api.get('GMCP.getv')('char.status.state'))

    if self.api.get('setting.gets')('nomoves') \
        or self.api.get('setting.gets')('nomana') \
        or self.api.get('setting.gets')('nocast') \
        or self.api.get('setting.gets')('waiting') != -1 \
        or not self.api.get('setting.gets')('enabled') \
        or not self.api.get('skills.isuptodate')() or \
       self.api.get('GMCP.getv')('char.status.state') != 3:
      self.api.get('output.msg')('checked returned False')
      return False

    self.api.get('output.msg')('checked returned True')
    return True

  @timeit
  def nextspell(self, _=None):
    """
    try to cast the next spell
    """
    self.api.get('output.msg')('nextspell')
    if self.check():
      for i in self.spellups['sorder']:
        if self.spellups['self'][i]['enabled']:
          if self.api.get('skills.canuse')(i):
            self.api.get('setting.change')('waiting', int(i))
            self.api.get('skills.sendcmd')(i)
            return

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.spellups.sync()

  def _addselfspell(self, sn, place=-1, override=False):
    """
    add a spell internally
    """
    msg = []
    spell = self.api.get('skills.gets')(sn)

    if not spell:
      msg.append('%-20s: does not exist' % tspell)
      return msg

    if not override and not self.api.get('skills.isspellup')(spell['sn']):
      msg.append('%-20s: not a spellup' % spell['name'])
      return msg

    if spell['sn'] in self.spellups['sorder']:
      msg.append('%-30s: already activated' % spell['name'])
      return msg

    self.spellups['self'][spell['sn']] = {'enabled':True}
    if place > -1:
      self.spellups['sorder'].insert(place, spell['sn'])
    else:
      self.spellups['sorder'].append(spell['sn'])
    msg.append('%-20s:  place %s' % (spell['name'],
                        self.spellups['sorder'].index(spell['sn'])))

    return msg

  def cmd_sadd(self, args):
    """
    add a spellup
    """
    #self.api.get('output.client')('%s' % args)
    msg = []
    if len(args) < 1:
      return False, ['Please supply a spell']

    if args[0] == 'all':
      spellups = self.api.get('skills.getspellups')()
      for spell in spellups:
        if spell['percent'] > 1:
          tmsg = self._addselfspell(spell['sn'])
          msg.extend(tmsg)

      self.nextspell()

    elif len(args) == 2 and 'override' in args:
      self.api.get('output.client')('got override')
      aspell = args[0]
      tspell = aspell
      place = -1
      if ':' in aspell:
        tlist = aspell.split(':')
        tspell = tlist[0]
        place = int(tlist[1])

      tmsg = self._addselfspell(tspell, place, True)
      msg.extend(tmsg)

      self.nextspell()

    else:
      for aspell in args:
        if aspell == 'override':
          continue
        tspell = aspell
        place = -1
        if ':' in aspell:
          tlist = aspell.split(':')
          tspell = tlist[0]
          place = int(tlist[1])

        tmsg = self._addselfspell(tspell, place)
        msg.extend(tmsg)

        self.nextspell()

    self.spellups.sync()
    return True, msg

  def cmd_slist(self, args):
    """
    list the spellups
    """
    msg = []
    if len(self.spellups['sorder']) > 0:
      #P  B  D  NP  NL
      msg.append('%-3s - %-30s : %2s %2s %2s %2s  %-2s  %-2s' % (
              'Num', 'Name', 'A', 'P', 'B', 'D', 'NP', 'NL'))
      msg.append('@B' + '-'* 60)
      for i in self.spellups['sorder']:
        skill = self.api.get('skills.gets')(i)
        msg.append('%-3s - %-30s : %2s %2s %2s %2s  %-2s  %-2s' % (
                  self.spellups['sorder'].index(i),
                  skill['name'],
                  'A' if self.api.get('skills.isaffected')(i) else '',
                  'P' if self.api.get('setting.gets')('waiting') == i else '',
                  'B' if self.api.get('skills.isblockedbyrecovery')(i) else '',
                  'D' if not self.spellups['self'][i]['enabled'] else '',
                  'NP' if skill['percent'] == 1 else '',
                  'NL' if skill['percent'] == 0 else '',))
    else:
      msg.append('There are no spellups')
    return True, msg

  def cmd_srem(self, args):
    """
    remove a spellup
    """
    if len(args) < 1:
      return True, ['Please supply a spell/skill to remove']

    msg = []
    if args[0].lower() == 'all':
      del self.spellups['sorder']
      del self.spellups['self']
      self.initspellups()
      msg.append('All spellups to be cast on self cleared')

    else:
      for spella in args:
        spell = self.api.get('skills.gets')(spella)

        if not spell:
          msg.append('%s does not exist' % spella)
          continue

        sn = spell['sn']
        if sn in self.spellups['sorder']:
          self.spellups['sorder'].remove(sn)
        if sn in self.spellups['self']:
          del self.spellups['self'][sn]

        msg.append('Removed %s from spellups to self' % spell['name'])

      self.savestate()
      return True, msg

  def cmd_sen(self, args):
    """
    enable a spellup
    """
    msg = []
    if len(args) > 0:
      for sn in args:
        skill = self.api.get('skills.gets')(sn)
        if skill:
          if skill['sn'] in self.spellups['sorder']:
            self.spellups['self'][skill['sn']]['enabled'] = True
            msg.append('%s: enabled' % skill['name'])
          else:
            msg.append('%s: not in self spellup list' % skill['name'])
        else:
          msg.append('%s: could not find spell' % sn)
      self.nextspell()
      return True, msg

    return False, []

  def cmd_sdis(self, args):
    """
    enable a spellup
    """
    msg = []
    if len(args) > 0:
      for sn in args:
        skill = self.api.get('skills.gets')(sn)
        if skill:
          if skill['sn'] in self.spellups['sorder']:
            self.spellups['self'][skill['sn']]['enabled'] = False
            msg.append('%s: disabled' % skill['name'])
          else:
            msg.append('%s: not in self spellup list' % skill['name'])
        else:
          msg.append('%s: could not find spell' % sn)
      return True, msg

    return False, []

  def reset(self):
    """
    reset all spellups
    """
    AardwolfBasePlugin.reset(self)
    self.spellups.clear()
    self.initspellups()
    self.spellups.sync()

