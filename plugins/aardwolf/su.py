"""
This plugin does spellups for Aardwolf
"""
import os
import argparse
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
  a plugin that does spellups
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.spellupfile = os.path.join(self.savedir, 'spellups.txt')
    self.spellups = PersistentDict(self.spellupfile, 'c')

    self.api.get('dependency.add')('aardwolf.skills')
    self.api.get('dependency.add')('aardwolf.move')

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

    parser = argparse.ArgumentParser(add_help=False,
                 description='add a spellup to the self list')
    parser.add_argument('spell',
          help='the spells to add, use \'all\' to add all practiced spellups',
          default=[], nargs='*')
    parser.add_argument('-o', "--override",
          help="add even if the spell is not flagged as a spellup by the mud",
              action="store_true")
    self.api.get('commands.add')('add', self.cmd_sadd,
              parser=parser, group='Spellups on Self')

    parser = argparse.ArgumentParser(add_help=False,
              description='list spellups for self')
    parser.add_argument('match',
            help='list only spellups that have this argument in them',
            default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_slist,
              parser=parser, group='Spellups on Self')

    parser = argparse.ArgumentParser(add_help=False,
              description='remove a spellup from the self list')
    parser.add_argument('spell',
              help='the spells to remove, use \'all\' to remove all spellups',
              default=[], nargs='*')
    self.api.get('commands.add')('rem', self.cmd_srem,
              parser=parser, group='Spellups on Self')

    parser = argparse.ArgumentParser(add_help=False,
              description='enable spellups on self')
    parser.add_argument('spell',
            help='the spells to enable, use \'all\' to enable all spellups',
            default=[], nargs='*')
    self.api.get('commands.add')('en', self.cmd_en,
              parser=parser, group='Spellups on Self')

    parser = argparse.ArgumentParser(add_help=False,
              description='disable spells on self')
    parser.add_argument('spell',
            help='the spells to disable, use \'all\' to disable all spellups',
            default=[], nargs='*')
    self.api.get('commands.add')('dis', self.cmd_dis,
              shelp='disable a spellup on self',
              parser=parser, group='Spellups on Self')

    parser = argparse.ArgumentParser(add_help=False,
              description='check all information to cast spells')
    self.api.get('commands.add')('check', self.cmd_check,
              shelp='check data status for casting', group='Spellups on Self')

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

    if self.api.get('skills.isuptodate')():
      self._charstatus()

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
    catch a recoff event
    """
    self.nextspell()

  def _skillfail(self, args):
    """
    catch a skill fail event
    """
    self.api.get('send.msg')('skillfail: %s' % args)
    spellnum = args['sn']
    skill = self.api.get('skills.gets')(spellnum)
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
    elif waiting == spellnum:
      if args['reason'] == 'lostconc':
        self.api.get('skills.sendcmd')(waiting)
      elif args['reason'] == 'alreadyaff':
        self.api.get('setting.change')('waiting', -1)
        self.api.get('send.client')(
          "@BSpellup - disabled %s because you are already affected" % \
                                  skill['name'])
        if spellnum in self.spellups['self']:
          self.spellups['self'][spellnum]['enabled'] = False
        #if spellnum in self.spellups['other']:
          #self.spellups['other'][spellnum]['enabled'] = False
        self.nextspell()
      elif args['reason'] == 'recblock':
        # do stuff when blocked by a recovery
        self.api.get('setting.change')('waiting', -1)
        self.nextspell()
      elif args['reason'] == 'dontknow':
        # do stuff when spell/skill isn't learned
        # don't disable it, hopefully the spell/skill has been updated and
        # won't be cast through nextspell
        self.api.get('setting.change')('waiting', -1)
        self.nextspell()
      elif args['reason'] == 'wrongtarget':
        # do stuff when a wrong target
        self.api.get('setting.change')('waiting', -1)
        self.nextspell()
      elif args['reason'] == 'disabled':
        self.api.get('setting.change')('waiting', -1)
        skill = self.api.get('skills.gets')(spellnum)
        self.api.get('send.client')(
          "@BSpellup - disabled %s because it is disabled mudside" % \
                                  skill['name'])
        if spellnum in self.spellups['self']:
          self.spellups['self'][spellnum]['enabled'] = False
        if spellnum in self.spellups['other']:
          self.spellups['other'][spellnum]['enabled'] = False
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
      lastval = self.api.get('setting.gets')('nocast')
      self.api.get('setting.change')('nocast', False)
      if lastval:
        self.nextspell()

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
    self.api.get('send.msg')('waiting type: %s' % \
                      type(self.api.get('setting.gets')('waiting')))
    self.api.get('send.msg')('currentstatus = %s' % \
                      self.api.get('GMCP.getv')('char.status.state'))

    if self.api.get('setting.gets')('nomoves') \
        or self.api.get('setting.gets')('nomana') \
        or self.api.get('setting.gets')('nocast') \
        or self.api.get('setting.gets')('waiting') != -1 \
        or not self.api.get('setting.gets')('enabled') \
        or not self.api.get('skills.isuptodate')() or \
       self.api.get('GMCP.getv')('char.status.state') != 3:
      self.api.get('send.msg')('checked returned False')
      return False

    self.api.get('send.msg')('checked returned True')
    return True

  @timeit
  def nextspell(self, _=None):
    """
    try to cast the next spell
    """
    self.api.get('send.msg')('nextspell')
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

  def _addselfspell(self, spellnum, place=-1, override=False):
    """
    add a spell internally
    """
    msg = []
    spell = self.api.get('skills.gets')(spellnum)

    if not spell:
      msg.append('%-20s: does not exist' % spellnum)
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
    #self.api.get('send.client')('sadd arguments: %s' % args)
    msg = []
    if len(args['spell']) < 1:
      return False, ['Please supply a spell']

    if args['spell'][0] == 'all':
      spellups = self.api.get('skills.getspellups')()
      for spell in spellups:
        if spell['percent'] > 1:
          tmsg = self._addselfspell(spell['sn'])
          msg.extend(tmsg)

      self.nextspell()

    else:
      for aspell in args['spell']:
        tspell = aspell
        place = -1
        if ':' in aspell:
          tlist = aspell.split(':')
          tspell = tlist[0]
          place = int(tlist[1])

        tmsg = self._addselfspell(tspell, place, args['override'])
        msg.extend(tmsg)

        self.nextspell()

    self.spellups.sync()
    return True, msg

  def cmd_slist(self, args):
    """
    list the spellups
    """
    msg = []
    match = args['match']
    if len(self.spellups['sorder']) > 0:
      #P  B  D  NP  NL
      msg.append('%-3s - %-30s : %2s %2s %2s %2s  %-2s  %-2s' % (
              'Num', 'Name', 'A', 'P', 'B', 'D', 'NP', 'NL'))
      msg.append('@B' + '-'* 60)
      for i in self.spellups['sorder']:
        skill = self.api.get('skills.gets')(i)
        if not match or match in skill['name']:
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
    if len(args['spell']) < 1:
      return True, ['Please supply a spell/skill to remove']

    msg = []
    if args['spell'][0].lower() == 'all':
      del self.spellups['sorder']
      del self.spellups['self']
      self.initspellups()
      msg.append('All spellups to be cast on self cleared')

    else:
      for spella in args['spell']:
        spell = self.api.get('skills.gets')(spella)

        if not spell:
          msg.append('%s does not exist' % spella)
          continue

        spellnum = spell['sn']
        if spellnum in self.spellups['sorder']:
          self.spellups['sorder'].remove(spellnum)
        if spellnum in self.spellups['self']:
          del self.spellups['self'][spellnum]

        msg.append('Removed %s from spellups to self' % spell['name'])

      self.savestate()
      return True, msg

  def cmd_en(self, args):
    """
    enable a spellup
    """
    if len(args['spell']) < 1:
      return True, ['Please supply a spell/skill to enable']

    msg = []

    if args['spell'][0].lower() == 'all':
      for i in self.spellups['self']:
        self.spellups['self'][i]['enabled'] = True

      msg.append('All spellups enabled')

    else:
      for spellnum in args['spell']:
        skill = self.api.get('skills.gets')(spellnum)
        if skill:
          if skill['sn'] in self.spellups['sorder']:
            self.spellups['self'][skill['sn']]['enabled'] = True
            msg.append('%s: enabled' % skill['name'])
          else:
            msg.append('%s: not in self spellup list' % skill['name'])
        else:
          msg.append('%s: could not find spell' % spellnum)
      self.nextspell()
      return True, msg

    return False, []

  def cmd_dis(self, args):
    """
    enable a spellup
    """
    if len(args['spell']) < 1:
      return True, ['Please supply a spell/skill to enable']

    msg = []
    if args['spell'][0].lower() == 'all':
      for i in self.spellups['self']:
        self.spellups['self'][i]['enabled'] = False

      msg.append('All spellups disabled')

    else:
      for spellnum in args['spell']:
        skill = self.api.get('skills.gets')(spellnum)
        if skill:
          if skill['sn'] in self.spellups['sorder']:
            self.spellups['self'][skill['sn']]['enabled'] = False
            msg.append('%s: disabled' % skill['name'])
          else:
            msg.append('%s: not in self spellup list' % skill['name'])
        else:
          msg.append('%s: could not find spell' % spellnum)
      return True, msg

    return False, []

  def cmd_check(self, args):
    """
    list all items that are need for spellups and whether they are known
    """
    tmsg = []
    tformat = '%-25s : %-10s - %s'
    tmsg.append(tformat % ('enabled',
                self.api.get('setting.gets')('enabled'),
                'should be True to cast spells'))
    tmsg.append(tformat % ('waiting',
                self.api.get('setting.gets')('waiting'),
                'the spell that was last cast, should be -1 to cast spells'))
    tmsg.append(tformat % ('nocast',
                self.api.get('setting.gets')('nocast'),
                'the current room is nocast, should be False to cast spells'))
    tmsg.append(tformat % ('nomoves',
                self.api.get('setting.gets')('nomoves'),
                'ran out of moves, should be False to cast spells'))
    tmsg.append(tformat % ('nomana',
                self.api.get('setting.gets')('nomana'),
                'ran out of mana, should be False to cast spells'))
    tmsg.append(tformat % ('Skills are up to date',
                self.api.get('skills.isuptodate')(),
                'should be True to cast spells'))
    tmsg.append(tformat % ('Char state',
                self.api.get('GMCP.getv')('char.status.state'),
                'should be 3 to cast spells'))
    return True, tmsg

  def reset(self):
    """
    reset all spellups
    """
    AardwolfBasePlugin.reset(self)
    self.spellups.clear()
    self.initspellups()
    self.spellups.sync()

