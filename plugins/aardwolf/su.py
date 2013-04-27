"""
$Id$

#TODO: how to figure out when to start spellups after connecting or
          after a reload
#TODO: add ability to spellup others
#TODO: add ability to have spell blockers
"""
import copy
import time
import os
from plugins import BasePlugin
from libs import exported
from libs.persistentdict import PersistentDict

NAME = 'Spellup'
SNAME = 'su'
PURPOSE = 'spellup plugin'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(BasePlugin):
  """
  a plugin to monitor aardwolf events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.spellupfile = os.path.join(self.savedir, 'spellups.txt')
    self.spellups = PersistentDict(self.spellupfile, 'c', format='json')

    self.dependencies.append('skills')
    self.dependencies.append('move')

    self.initspellups()

    self.lastmana = -1
    self.lastmoves = -1

    # backup the db every 4 hours
    #self.timers['stats_backup'] = {'func':self.backupdb,
                                #'seconds':60*60*4, 'time':'0000'}

    self.addsetting('enabled', True, bool,
                      'auto spellup is enabled')
    self.addsetting('waiting', -1, int,
                      'the spell that was just cast',
                      readonly=True)
    self.addsetting('nocast', False, bool,
                      'in a nocast room',
                      readonly=True)
    self.addsetting('nomoves', False, bool,
                      'need more moves',
                      readonly=True)
    self.addsetting('nomana', False, bool,
                      'need more mana',
                      readonly=True)
    self.addsetting('nocastrooms', {}, dict,
                      'list of nocast rooms',
                      readonly=True)
    self.addsetting('currentroom', -1, int,
                      'the current room',
                      readonly=True)

    self.cmds['sadd'] = {'func':self.cmd_sadd,
              'shelp':'add a spellup to the self list'}
    self.cmds['slist'] = {'func':self.cmd_slist,
              'shelp':'list spellups'}
    self.cmds['srem'] = {'func':self.cmd_srem,
              'shelp':'remove a spellup from self list'}
    self.cmds['sen'] = {'func':self.cmd_sen,
              'shelp':'enable a spellup on self'}
    self.cmds['sdis'] = {'func':self.cmd_sdis,
              'shelp':'disable a spellup on self'}

    #self.triggers['dead'] = {
      #'regex':"^You die.$",
      #'enabled':True, 'group':'dead'}

    self.events['GMCP:char.vitals'] = {'func':self._charvitals}
    self.events['GMCP:char.status'] = {'func':self._charstatus}
    self.events['moved_room'] = {'func':self._moved}
    self.events['skill_fail'] = {'func':self._skillfail}
    self.events['aard_skill_affon'] = {'func':self._affon}
    self.events['aard_skill_affoff'] = {'func':self._affoff}
    self.events['aard_skill_recoff'] = {'func':self._recoff}
    self.events['su_enabled'] = {'func':self.enabledchange}
    self.events['skills_affected_update'] = {'func':self.nextspell}
    self.events['aard_skill_gain'] = {'func':self.skillgain}

  def skillgain(self, args=None):
    """
    check skills when we gain them
    """
    if args['sn'] in self.sorder and args['percent'] > 50:
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
    if args['sn'] == self.variables['waiting']:
      self.variables['waiting'] = -1
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
    self.msg('skillfail: %s' % args)
    sn = args['sn']
    if args['reason'] == 'nomana':
      self.variables['waiting'] = -1
      self.variables['nomana'] = True
      self.lastmana = exported.GMCP.getv('char.vitals.mana')
    elif args['reason'] == 'nocastroom':
      self.variables['waiting'] = -1
      self.variables['nocast'] = True
      self.variables['nocastrooms'][self.variables['currentroom']] = True
    elif args['reason'] == 'fighting' or args['reason'] == 'notactive':
      self.args['waiting'] = -1
    elif args['reason'] == 'nomoves':
      self.variables['waiting'] = -1
      self.variables['nomoves'] = True
      self.lastmana = exported.GMCP.getv('char.vitals.moves')
    elif self.variables['waiting'] == sn:
      if args['reason'] == 'lostconc':
        exported.skills.sendcmd(self.variables['waiting'])
      elif args['reason'] == 'alreadyaff':
        self.variables['waiting'] = -1
        skill = exported.skills.gets(sn)
        exported.sendtoclient(
          "@BSpellup - disabled %s because you are already affected" % \
                                  skill['name'])
        if sn in self.spellups['self']:
          self.spellups['self'][sn]['enabled'] = False
        if sn in self.spellups['other']:
          self.spellups['other'][sn]['enabled'] = False
        self.nextspell()
      elif args['reason'] == 'recblock':
        # do stuff when blocked by a recovery
        pass
      elif args['reason'] == 'dontknow':
        # do stuff when spell/skill isn't learned
        pass
      elif args['reason'] == 'wrongtarget':
        # do stuff when a wrong target
        pass
      elif args['reason'] == 'disabled':
        self.variables['waiting'] = -1
        skill = exported.skills.gets(sn)
        exported.sendtoclient(
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
    self.variables['currentroom'] = args['to']['num']
    if args['to']['num'] in self.variables['nocastrooms']:
      self.variables['nocast'] = True
    else:
      self.variables['nocast'] = False

  def _charvitals(self, args):
    """
    check if we have more mana and moves
    """
    if self.variables['nomana']:
      newmana = exported.GMCP.getv('char.vitals.mana')
      if newmana > self.lastmana:
        self.lastmana = -1
        self.variables['nomana'] = False
        self.nextspell()
    if self.variables['nomoves']:
      newmoves = exported.GMCP.getv('char.vitals.moves')
      if newmoves > self.lastmoves:
        self.lastmoves = -1
        self.variables['nomoves'] = False
        self.nextspell()

  def _charstatus(self, _=None):
    """
    check if we have more mana and moves
    """
    status = exported.GMCP.getv('char.status.state')
    if status == 3 and exported.skills.isuptodate():
      self.nextspell()

  def check(self, _=None):
    """
    check to cast the next spell
    """
    if not exported.PROXY:
      return False
    self.msg('waiting type: %s' % type(self.variables['waiting']))
    self.msg('currentstatus = %s' % exported.GMCP.getv('char.status.state'))

    if self.variables['nomoves'] or self.variables['nomana'] or \
       self.variables['nocast'] or self.variables['waiting'] != -1 or \
       not self.variables['enabled'] or \
       not exported.skills.isuptodate() or \
       exported.GMCP.getv('char.status.state') != 3:
      self.msg('checked returned False')
      return False

    self.msg('checked returned True')
    return True

  def nextspell(self, _=None):
    """
    try to cast the next spell
    """
    self.msg('nextspell')
    self.msg('self: %s' % self.spellups['self'])
    if self.check():
      for i in self.spellups['sorder']:
        if self.spellups['self'][i]['enabled']:
          if exported.skills.canuse(i):
            self.variables['waiting'] = int(i)
            exported.skills.sendcmd(i)
            return

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self.spellups.sync()

  def _addselfspell(self, sn, place=-1, override=False):
    """
    add a spell internally
    """
    msg = []
    spell = exported.skills.gets(sn)

    if not spell:
      msg.append('%-20s: does not exist' % tspell)
      return msg

    if not override and not exported.skills.isspellup(spell['sn']):
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
    #exported.sendtoclient('%s' % args)
    msg = []
    if len(args) < 1:
      return False, ['Please supply a spell']

    if args[0] == 'all':
      spellups = exported.skills.getspellups()
      for spell in spellups:
        if spell['percent'] > 1:
          tmsg = self._addselfspell(spell['sn'])
          msg.extend(tmsg)

      self.nextspell()

    elif len(args) == 2 and 'override' in args:
      exported.sendtoclient('got override')
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
        skill = exported.skills.gets(i)
        msg.append('%-3s - %-30s : %2s %2s %2s %2s  %-2s  %-2s' % (
                      self.spellups['sorder'].index(i),
                      skill['name'],
                      'A' if exported.skills.isaffected(i) else '',
                      'P' if self.variables['waiting'] == i else '',
                      'B' if exported.skills.isblockedbyrecovery(i) else '',
                      'D' if not self.spellups['self'][i]['enabled'] else '',
                      'NP' if skill['percent'] == 1 else '',
                      'NL' if skill['percent'] == -1 else '',))
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
        spell = exported.skills.gets(spella)

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
        skill = exported.skills.gets(sn)
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
        skill = exported.skills.gets(sn)
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
    BasePlugin.reset(self)
    self.spellups.clear()
    self.initspellups()
    self.spellups.sync()

