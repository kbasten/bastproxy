"""
$Id$

This plugin handles slist from Aardwolf
"""
import time
import os
import copy
import fnmatch
import argparse
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin
from libs.persistentdict import PersistentDict
from libs.timing import timeit

NAME = 'Aardwolf Skills'
SNAME = 'skills'
PURPOSE = 'keep up with skills using slist'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

FAILREASON = {}
FAILREASON[1] = 'lostconc' # Regular fail, lost concentration.
FAILREASON[2] = 'alreadyaff' # Already affected.
FAILREASON[3] = 'recblock' # Cast blocked by a recovery, see below.
FAILREASON[4] = 'nomana' # Not enough mana.
FAILREASON[5] = 'nocastroom' # You are in a nocast room.
FAILREASON[6] = 'fighting' # Fighting or other 'cant concentrate'.
FAILREASON[8] = 'dontknow' # You don't know the spell.
FAILREASON[9] = 'wrongtarget' # Tried to cast self only on other.
FAILREASON[10] = 'notactive' # - You are resting / sitting.
FAILREASON[11] = 'disabled' # Skill/spell has been disabled.
FAILREASON[12] = 'nomoves' # Not enough moves.

TARGET = {}
TARGET[0] = 'special' # Target decided in spell (gate etc)
TARGET[1] = 'attack'
TARGET[2] = 'spellup'
TARGET[3] = 'selfonly'
TARGET[4] = 'object'
TARGET[5] = 'other' # Spell has extended / unique syntax.

STYPE = {}
STYPE[1] = 'spell'
STYPE[2] = 'skill'

FAILTARG = {0:'self', 1:'other'}


class Plugin(AardwolfBasePlugin):
  """
  a plugin manage info about spells and skills
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.saveskillfile = os.path.join(self.savedir, 'skills.txt')
    self.skills = PersistentDict(self.saveskillfile, 'c', format='json')
    self.skillsnamelookup = {}
    for i in self.skills:
      self.skillsnamelookup[self.skills[i]['name']] = i

    self.saverecovfile = os.path.join(self.savedir, 'recoveries.txt')
    self.recoveries = PersistentDict(self.saverecovfile, 'c', format='json')
    self.recoveriesnamelookup = {}
    for i in self.recoveries:
      self.recoveriesnamelookup[self.recoveries[i]['name']] = i

    self.current = ''
    self.isuptodatef = False

    self.api.get('dependency.add')('cmdq')

    self.api.get('api.add')('gets', self.api_getskill)
    self.api.get('api.add')('isspellup', self.api_isspellup)
    self.api.get('api.add')('getspellups', self.api_getspellups)
    self.api.get('api.add')('sendcmd', self.api_sendcmd)
    self.api.get('api.add')('isaffected', self.api_isaffected)
    self.api.get('api.add')('isblockedbyrecovery',
                                        self.api_isblockedbyrecovery)
    self.api.get('api.add')('ispracticed', self.api_ispracticed)
    self.api.get('api.add')('canuse', self.api_canuse)
    self.api.get('api.add')('isuptodate', self.api_isuptodate)

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('send.msg')('running load function of skills')

    parser = argparse.ArgumentParser(add_help=False,
                 description='refresh skills and spells')
    self.api.get('commands.add')('refresh', self.cmd_refresh,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='lookup skill or spell by name or sn')
    parser.add_argument('skill', help='the skill to lookup',
                        default='', nargs='?')
    self.api.get('commands.add')('lu', self.cmd_lu,
                                 parser=parser)

    self.api.get('triggers.add')('spellh_noprompt',
            "^\{spellheaders noprompt\}$",
            group='slist', enabled=False, omit=True)
    self.api.get('triggers.add')('spellh_spellup_noprompt',
            "^\{spellheaders spellup noprompt\}$",
            group='slist', enabled=False, omit=True)
    self.api.get('triggers.add')('spellh_affected_noprompt',
            "^\{spellheaders affected noprompt\}$",
            group='slist', enabled=False, omit=True)
    self.api.get('triggers.add')('spellh_spellline',
            "^(?P<sn>\d+),(?P<name>.+),(?P<target>\d+)," \
              "(?P<duration>\d+),(?P<pct>\d+),(?P<rcvy>-?\d+),(?P<type>\d+)$",
            group='spellhead', enabled=False, omit=True)
    self.api.get('triggers.add')('spellh_end_noprompt',
            "^\{/spellheaders\}$",
            group='spellhead', enabled=False, omit=True)
    self.api.get('triggers.add')('affoff',
            "^\{affoff\}(?P<sn>\d+)$")
    self.api.get('triggers.add')('affon',
            "^\{affon\}(?P<sn>\d+),(?P<duration>\d+)$")
    self.api.get('triggers.add')('recov_noprompt',
            "^\{recoveries noprompt\}$",
            group='slist', enabled=False, omit=True)
    self.api.get('triggers.add')('recov_affected_noprompt',
            "^\{recoveries affected noprompt\}$",
            group='slist', enabled=False, omit=True)
    self.api.get('triggers.add')('spellh_recovline',
            "^(?P<sn>\d+),(?P<name>.+),(?P<duration>\d+)$",
            group='recoveries', enabled=False, omit=True)
    self.api.get('triggers.add')('recov_end_noprompt',
            "^\{/recoveries\}$",
            group='recoveries', enabled=False, omit=True)
    self.api.get('triggers.add')('recoff',
            "^\{recoff\}(?P<sn>\d+)$")
    self.api.get('triggers.add')('recon',
            "^\{recon\}(?P<sn>\d+),(?P<duration>\d+)$")
    self.api.get('triggers.add')('skillgain',
            "^\{skillgain\}(?P<sn>\d+),(?P<percent>\d+)$")
    self.api.get('triggers.add')('skillfail',
            "^\{sfail\}(?P<sn>\d+),(?P<target>\d+)," \
              "(?P<reason>\d+),(?P<recovery>-?\d+)$")

    self.api.get('events.register')('trigger_spellh_noprompt',
                                    self.skillstart)
    self.api.get('events.register')('trigger_spellh_spellup_noprompt',
                                    self.skillstart)
    self.api.get('events.register')('trigger_spellh_affected_noprompt',
                                    self.skillstart)
    self.api.get('events.register')('trigger_spellh_spellline',
                                    self.skillline)
    self.api.get('events.register')('trigger_spellh_end_noprompt',
                                    self.skillend)
    self.api.get('events.register')('trigger_affoff', self.affoff)
    self.api.get('events.register')('trigger_affon', self.affon)
    self.api.get('events.register')('trigger_recov_noprompt',
                                    self.recovstart)
    self.api.get('events.register')('trigger_recov_affected_noprompt',
                                    self.recovstart)
    self.api.get('events.register')('trigger_spellh_recovline',
                                    self.recovline)
    self.api.get('events.register')('trigger_recov_end_noprompt',
                                    self.recovend)
    self.api.get('events.register')('trigger_recoff', self.recoff)
    self.api.get('events.register')('trigger_recon', self.recon)

    self.api.get('events.register')('trigger_skillgain', self.skillgain)
    self.api.get('events.register')('trigger_skillfail', self.skillfail)

    self.api.get('events.register')('GMCP:char.status', self.checkskills)

    self.cmdqueue = self.api.get('cmdq.baseclass')()(self)
    self.cmdqueue.addcmdtype('slist', 'slist', "^slist\s*(.*)$",
                       self.slistbefore, self.slistafter)

    self.checkskills()

  def slistbefore(self):
    """
    stuff to do before doing slist command
    """
    self.api.get('triggers.togglegroup')('slist', True)

  def slistafter(self):
    """
    stuff to do after doing slist command
    """
    self.savestate()
    self.api.get('triggers.togglegroup')('slist', False)

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)
    self.checkskills()

  def api_isuptodate(self):
    """
    return True if we have seen affected or all spells refresh
    """
    return self.isuptodatef

  def cmd_lu(self, args):
    """
    cmd to lookup a spell
    """
    msg = []
    skill = self.api.get('skills.gets')(args['skill'])
    if skill:
      msg.append('%-8s : %s' % ('SN', skill['sn']))
      msg.append('%-8s : %s' % ('Name', skill['name']))
      msg.append('%-8s : %s' % ('Percent', skill['percent']))
      if skill['duration'] > 0:
        msg.append('%-8s : %s' % ('Duration',
            self.api.get('utils.timedeltatostring')(time.time(),
              skill['duration'])))
      msg.append('%-8s : %s' % ('Target', skill['target']))
      msg.append('%-8s : %s' % ('Spellup', skill['spellup']))
      msg.append('%-8s : %s' % ('Type', skill['type']))
      if skill['recovery']:
        recov = skill['recovery']
        if recov['duration'] > 0:
          duration =  self.api.get('utils.timedeltatostring')(time.time(),
              recov['duration'])
          msg.append('%-8s : %s (%s)' % ('Recovery',
                                      recov['name'], duration))
        else:
          msg.append('%-8s : %s' % ('Recovery', recov['name']))
    else:
      msg.append('Could not find: %s' % args['skill'])

    return True, msg

  def cmd_refresh(self, args):
    """
    refresh spells and skills
    """
    self.skills.clear()
    self.recoveries.clear()
    self.cmdqueue.addtoqueue('slist', 'noprompt')
    self.cmdqueue.addtoqueue('slist', 'spellup noprompt')
    msg = ['Refreshing spells and skills']
    return True, msg

  def checkskills(self, _=None):
    """
    check to see if we have spells
    """
    state = self.api.get('GMCP.getv')('char.status.state')
    if state == 3:
      self.api.get('send.msg')('refreshing skills')
      self.api.get('events.unregister')('GMCP:char.status', self.checkskills)
      self.api.get('A102.toggle')('SPELLUPTAGS', True)
      self.api.get('A102.toggle')('SKILLGAINTAGS', True)
      self.api.get('A102.toggle')('QUIETTAGS', False)
      if len(self.skills) == 0:
        self.cmd_refresh({})
      else:
        self.resetskills()
        self.cmdqueue.addtoqueue('slist', 'affected noprompt')

  def resetskills(self):
    """
    reset the skills
    """
    for i in self.skills:
      self.skills[i]['duration'] = 0
    for i in self.recoveries:
      self.recoveries[i]['duration'] = 0

  def skillgain(self, args):
    """
    handle a skillgain tag
    """
    spellnum = int(args['sn'])
    pct = int(args['percent'])
    if spellnum in self.skills:
      self.skills[spellnum]['percent'] = pct
      self.api.get('events.eraise')('aard_skill_gain',
                                    {'sn':spellnum, 'percent':pct})

  def skillfail(self, args):
    """
    raise an event when we fail a skill/spell
    """
    ndict = {'sn': int(args['sn']), 'reason':FAILREASON[int(args['reason'])],
            'target':FAILTARG[int(args['target'])],
            'recovery':int(args['recovery'])}
    self.api.get('send.msg')('raising skillfail: %s' % ndict)
    self.api.get('events.eraise')('skill_fail_%s' % args['sn'], ndict)
    self.api.get('events.eraise')('skill_fail', ndict)

  def affoff(self, args):
    """
    set the affect to off for spell that wears off
    """
    spellnum = int(args['sn'])
    if spellnum in self.skills:
      self.skills[spellnum]['duration'] = 0
      self.savestate()
      self.api.get('events.eraise')('aard_skill_affoff_%s' % spellnum,
                                              {'sn':spellnum})
      self.api.get('events.eraise')('aard_skill_affoff', {'sn':spellnum})

  def affon(self, args):
    """
    set the spell's duration when we see an affon
    """
    spellnum = int(args['sn'])
    duration = int(args['duration'])
    if spellnum in self.skills:
      self.skills[spellnum]['duration'] = time.mktime(time.localtime()) + \
                                                        duration
      self.savestate()
      self.api.get('events.eraise')('aard_skill_affon_%s' % spellnum,
                                              {'sn':spellnum,
                              'duration':self.skills[spellnum]['duration']})
      self.api.get('events.eraise')('aard_skill_affon', {'sn':spellnum,
                              'duration':self.skills[spellnum]['duration']})

  def recovstart(self, args):
    """
    show that the trigger fired
    """
    if 'triggername' in args \
        and args['triggername'] == 'trigger_recov_affected_noprompt':
      self.current = 'affected'
    else:
      self.current = ''
    self.api.get('triggers.togglegroup')('recoveries', True)

  def recovline(self, args):
    """
    parse a recovery line
    """
    spellnum = int(args['sn'])
    name = args['name']
    if int(args['duration']) != 0:
      duration = time.mktime(time.localtime()) + int(args['duration'])
    else:
      duration = 0

    if not (spellnum in self.recoveries):
      self.recoveries[spellnum] = {}

    self.recoveries[spellnum]['name'] = name
    self.recoveries[spellnum]['duration'] = duration
    self.recoveries[spellnum]['sn'] = spellnum

    self.recoveriesnamelookup[name] = spellnum

  def recovend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.api.get('triggers.togglegroup')('recoveries', False)
    if self.current == '' or self.current == 'affected':
      self.isuptodatef = True
      self.api.get('send.msg')('sending skills_affected_update')
      self.api.get('events.eraise')('skills_affected_update', {})
    self.cmdqueue.cmddone('slist')

  def recoff(self, args):
    """
    set the affect to off for spell that wears off
    """
    spellnum = int(args['sn'])
    if spellnum in self.recoveries:
      self.recoveries[spellnum]['duration'] = 0
      self.savestate()
      self.api.get('events.eraise')('aard_skill_recoff', {'sn':spellnum})

  def recon(self, args):
    """
    set the spell's duration when we see an affon
    """
    spellnum = int(args['sn'])
    duration = int(args['duration'])
    if spellnum in self.recoveries:
      self.recoveries[spellnum]['duration'] = \
                        time.mktime(time.localtime()) + duration
      self.savestate()
      self.api.get('events.eraise')('aard_skill_recon', {'sn':spellnum,
                            'duration':self.recoveries[spellnum]['duration']})

  def skillstart(self, args):
    """
    show that the trigger fired
    """
    if 'triggername' in args \
        and args['triggername'] == 'spellh_spellup_noprompt':
      self.current = 'spellup'
    elif 'triggername' in args \
        and args['triggername'] == 'spellh_affected_noprompt':
      self.current = 'affected'
    else:
      self.current = ''
    self.api.get('triggers.togglegroup')('spellhead', True)

  def skillline(self, args):
    """
    parse spell lines
    """
    spellnum = int(args['sn'])
    name = args['name']
    target = int(args['target'])
    if int(args['duration']) != 0:
      duration = time.mktime(time.localtime()) + int(args['duration'])
    else:
      duration = 0
    percent = int(args['pct'])
    recovery = int(args['rcvy'])
    stype = int(args['type'])

    if not (spellnum in self.skills):
      self.skills[spellnum] = {}

    self.skills[spellnum]['name'] = name
    self.skills[spellnum]['target'] = TARGET[target]
    self.skills[spellnum]['duration'] = duration
    self.skills[spellnum]['percent'] = percent
    self.skills[spellnum]['recovery'] = recovery
    self.skills[spellnum]['type'] = STYPE[stype]
    self.skills[spellnum]['sn'] = spellnum
    if not ('spellup' in self.skills[spellnum]):
      self.skills[spellnum]['spellup'] = False
    if self.current == 'spellup':
      self.skills[spellnum]['spellup'] = True

    self.skillsnamelookup[name] = spellnum

  def skillend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.api.get('triggers.togglegroup')('spellhead', False)
    self.savestate()
    if self.current:
      evname = 'aard_skill_ref_%s' % self.current
    else:
      evname = 'aard_skill_ref'
    self.api.get('events.eraise')(evname, {})
    self.current = ''

  @timeit
  def api_getskill(self, tsn):
    """
    get a skill
    """
    #self.api.get('send.msg')('looking for %s' % tsn)
    spellnum = -1
    name = tsn
    try:
      spellnum = int(tsn)
    except ValueError:
      pass

    tskill = None
    if spellnum >= 1:
      #self.api.get('send.msg')('%s >= 0' % spellnum)
      if spellnum in self.skills:
        #self.api.get('send.msg')('found spellnum')
        tskill = copy.deepcopy(self.skills[spellnum])
        #tskill = self.skills[spellnum]
      else:
        self.api.get('send.msg')('did not find skill for int')

    if not tskill and name:
      #self.api.get('send.msg')('trying name')
      tlist = self.api.get('utils.checklistformatch')(name,
                                                self.skillsnamelookup.keys())
      if len(tlist) == 1:
        tskill = copy.deepcopy(self.skills[self.skillsnamelookup[tlist[0]]])

    if tskill:
      if tskill['recovery'] and tskill['recovery'] != -1:
        tskill['recovery'] = copy.deepcopy(self.recoveries[tskill['recovery']])
      else:
        tskill['recovery'] = None

    return tskill

  def api_sendcmd(self, spellnum):
    """
    send the command to activate a skill/spell
    """
    skill = self.api.get('skills.gets')(spellnum)
    if skill:
      if skill['type'] == 'spell':
        self.api.get('send.msg')('casting %s' % skill['name'])
        self.api.get('send.execute')('cast %s' % skill['sn'])
      else:
        name = skill['name'].split()[0]
        self.api.get('send.msg')('sending skill %s' % skill['name'])
        self.api.get('send.execute')(name)

  def api_canuse(self, spellnum):
    """
    return True if the spell can be used
    """
    if self.api.get('skills.isaffected')(spellnum) \
        or self.api.get('skills.isblockedbyrecovery')(spellnum) \
        or not self.api.get('skills.ispracticed')(spellnum):
      return False

    return True

  def api_isspellup(self, spellnum):
    """
    return True for a spellup, else return False
    """
    spellnum = int(spellnum)
    if spellnum in self.skills:
      return self.skills[spellnum]['spellup']

    return False

  def api_isaffected(self, spellnum):
    """
    return True for a spellup, else return False
    """
    skill = self.api.get('skills.gets')(spellnum)
    if skill:
      return skill['duration'] > 0

    return False

  def api_isblockedbyrecovery(self, spellnum):
    """
    check to see if a spell/skill is blocked by a recovery
    """
    skill = self.api.get('skills.gets')(spellnum)
    if skill:
      if 'recovery' in skill and skill['recovery'] and \
          skill['recovery']['duration'] > 0:
        return True

    return False

  def api_ispracticed(self, spellnum):
    """
    is the spell learned
    """
    skill = self.api.get('skills.gets')(spellnum)
    if skill:
      if skill['percent'] > 1:
        return True

    return False

  def api_getspellups(self):
    """
    return a list of spellup spells
    """
    sus = [x for x in self.skills.values() if x['spellup']]
    return sus

  def savestate(self):
    """
    save states
    """
    AardwolfBasePlugin.savestate(self)
    self.skills.sync()
    self.recoveries.sync()
