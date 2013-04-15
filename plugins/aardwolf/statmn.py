"""
$Id$
"""
from libs import exported
from libs import utils
from plugins import BasePlugin
import time
import copy

NAME = 'StatMonitor'
SNAME = 'statmn'
PURPOSE = 'Monitor for Aardwolf Events'
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
    self.events['aard_quest_comp'] = {'func':self.compquest}
    self.events['aard_cp_comp'] = {'func':self.compcp}
    self.events['aard_level_gain'] = {'func':self.levelgain}
    self.events['aard_gq_won'] = {'func':self.compgq}
    self.events['aard_gq_done'] = {'func':self.compgq}
    self.events['aard_gq_completed'] = {'func':self.compgq}
    self.events['statmn_showminutes'] = {'func':self.showchange}
    self.addsetting('statcolor', '@W', 'color', 'the stat color')
    self.addsetting('infocolor', '@x33', 'color', 'the info color')
    self.addsetting('showminutes', 5, int,
                    'show the report every x minutes, set to 0 to turn off')
    self.addsetting('reportminutes', 60, int,
                      'the # of minutes for the report to show')
    self.addsetting('exppermin', 20, int,
                'the threshhold for showing exp per minute')
    self.cmds['rep'] = {'func':self.cmd_rep,
              'shelp':'show report'}
    self.timers['statrep'] = {'func':self.timershow,
                                'seconds':5*60, 'nodupe':True}
    self.msgs = []

  def showchange(self, args):
    """
    do something when the reportminutes changes
    """
    exported.timer.remove('statrep')
    if int(args['newvalue']) > 0:
      exported.timer.add('statrep',
               {'func':self.timershow,
                'seconds':int(args['newvalue']) * 60,
                'nodupe':True})
    else:
      exported.sendtoclient('Turning off the statmon report')

  def timershow(self):
    """
    show the report
    """
    self.cmd_rep([])

  def compquest(self, args):
    """
    handle a quest completion
    """
    msg = []
    msg.append('%sStatMonitor: Quest finished for ' % \
                      self.variables['infocolor'])
    msg.append('%s%s' % (self.variables['statcolor'], args['qp']))
    if args['lucky'] > 0:
      msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], args['lucky']))
    if args['mccp'] > 0:
      msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], args['mccp']))
    if args['tier'] > 0:
      msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], args['tier']))
    if args['daily'] == 1:
      msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], 'E'))
    if args['double'] == 1:
      msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], 'D'))
    msg.append(' %s= ' % self.variables['infocolor'])
    msg.append('%s%s%sqp' % (self.variables['statcolor'],
            args['totqp'], self.variables['infocolor']))
    if args['tp'] > 0:
      msg.append(' %s%s%sTP' % (self.variables['statcolor'],
            args['tp'], self.variables['infocolor']))
    if args['trains'] > 0:
      msg.append(' %s%s%str' % (self.variables['statcolor'],
            args['trains'], self.variables['infocolor']))
    if args['pracs'] > 0:
      msg.append(' %s%s%spr' % (self.variables['statcolor'],
            args['pracs'], self.variables['infocolor']))
    msg.append('. It took %s%s%s.' % (
         self.variables['statcolor'],
         utils.timedeltatostring(args['starttime'], args['finishtime'],
         fmin=True, colorn=self.variables['statcolor'],
         colors=self.variables['infocolor']),
         self.variables['infocolor']))

    if exported.plugins.isinstalled('statdb'):
      stmt = "SELECT COUNT(*) as COUNT, AVG(totqp) as AVEQP " \
              "FROM quests where failed = 0"
      tst = exported.statdb.runselect(stmt)
      quest_total = tst[0]['COUNT']
      quest_avg = tst[0]['AVEQP']
      if quest_total > 1:
        msg.append(" %sAvg: %s%02.02f %sqp/quest over %s%s%s quests." % \
          (self.variables['infocolor'], self.variables['statcolor'],
           quest_avg, self.variables['infocolor'],
           self.variables['statcolor'], quest_total,
           self.variables['infocolor']))

    self.addmessage(''.join(msg))

  def compcp(self, args):
    """
    handle a cp completion
    """
    self.msg('compcp: %s' % args)
    msg = []
    msg.append('%sStatMonitor: CP finished for ' % \
                  self.variables['infocolor'])
    if args['bonusqp'] > 0:
      totalqp = args['bonusqp'] + args['qp']
      msg.append('%s%s%s+%s%sB%s=%s%sqp' % (self.variables['statcolor'],
                  args['qp'], self.variables['infocolor'],
                  self.variables['statcolor'], args['bonusqp'],
                  self.variables['infocolor'], self.variables['statcolor'],
                  totalqp))
    else:
      msg.append('%s%s%sqp' % (self.variables['statcolor'], args['qp'],
                  self.variables['infocolor']))
    if args['tp'] > 0:
      msg.append(' %s%s%sTP' % (self.variables['statcolor'],
            args['tp'], self.variables['infocolor']))
    if args['trains'] > 0:
      msg.append(' %s%s%str' % (self.variables['statcolor'],
            args['trains'], self.variables['infocolor']))
    if args['pracs'] > 0:
      msg.append(' %s%s%spr' % (self.variables['statcolor'],
            args['pracs'], self.variables['infocolor']))
    msg.append('. %sIt took %s.' % (
         self.variables['infocolor'],
         utils.timedeltatostring(args['starttime'], args['finishtime'],
         fmin=True, colorn=self.variables['statcolor'],
         colors=self.variables['infocolor'])))

    self.addmessage(''.join(msg))

  def compgq(self, args):
    """
    handle a gq completion
    """
    self.msg('compgq: %s' % args)
    msg = []
    msg.append('%sStatMonitor: GQ finished for ' % \
                  self.variables['infocolor'])
    msg.append('%s%s%s' % (self.variables['statcolor'], args['qp'],
                  self.variables['infocolor']))
    msg.append('+%s%s%sqp' % (self.variables['statcolor'], args['qpmobs'],
                  self.variables['infocolor']))
    if args['tp'] > 0:
      msg.append(' %s%s%sTP' % (self.variables['statcolor'],
            args['tp'], self.variables['infocolor']))
    if args['trains'] > 0:
      msg.append(' %s%s%str' % (self.variables['statcolor'],
            args['trains'], self.variables['infocolor']))
    if args['pracs'] > 0:
      msg.append(' %s%s%spr' % (self.variables['statcolor'],
            args['pracs'], self.variables['infocolor']))
    msg.append('.')
    msg.append(' %sIt took %s.' % (
         self.variables['infocolor'],
         utils.timedeltatostring(args['starttime'], args['finishtime'],
         fmin=True, colorn=self.variables['statcolor'],
         colors=self.variables['infocolor'])))

    self.addmessage(''.join(msg))

  def levelgain(self, args):
    """
    handle a level or pup gain
    """
    self.msg('levelgain: %s' % args)
    msg = []
    msg.append('%sStatMonitor: Gained a %s:' % (self.variables['infocolor'],
                args['type']))
    if args['type'] == 'level':
      msg.append(' %s%s%shp' % (self.variables['statcolor'],
            args['hp'], self.variables['infocolor']))
    if args['type'] == 'level':
      msg.append(' %s%s%smn' % (self.variables['statcolor'],
            args['mp'], self.variables['infocolor']))
    if args['type'] == 'level':
      msg.append(' %s%s%smv' % (self.variables['statcolor'],
            args['mv'], self.variables['infocolor']))
    if 'trains' in args:
      trains = args['trains']
      msg.append(' %s%d' % (self.variables['statcolor'], args['trains']))
      if args['blessingtrains'] > 0:
        trains = trains + args['blessingtrains']
        msg.append('%s+%s%dE' % (self.variables['infocolor'],
              self.variables['statcolor'], args['blessingtrains']))
      if args['bonustrains'] > 0:
        trains = trains + args['bonustrains']
        msg.append('%s+%s%dB' % (self.variables['infocolor'],
              self.variables['statcolor'], args['bonustrains']))
      if trains != args['trains']:
        msg.append('%s=%s%d' % (self.variables['infocolor'],
              self.variables['statcolor'], trains))
      msg.append(' %strains ' % self.variables['infocolor'])
    if args['type'] == 'level':
      msg.append(' %s%d %spracs ' % (self.variables['statcolor'],
              args['pracs'], self.variables['infocolor']))
    stats = False
    for i in ['str', 'dex', 'con', 'luc', 'int', 'wis']:
      if args[i] > 0:
        if not stats:
          stats = True
          msg.append('%s%s' % (self.variables['statcolor'], i))
        else:
          msg.append('%s+%s%s' % (self.variables['infocolor'],
            self.variables['statcolor'], i))
    if stats:
      msg.append(' %sbonus ' % self.variables['infocolor'])

    if args['starttime'] > 0 and args['finishtime'] > 0:
      msg.append(utils.timedeltatostring(args['starttime'],
              args['finishtime'], fmin=True,
              colorn=self.variables['statcolor'],
              colors=self.variables['infocolor']))

    if exported.plugins.isinstalled('statdb'):
      stmt = "SELECT count(*) as count, AVG(xp + bonusxp) as average FROM " \
            "mobkills where time > %d and time < %d and xp > 0" % \
             (args['starttime'], args['finishtime'])
      tst = exported.statdb.runselect(stmt)
      count = tst[0]['count']
      ave = tst[0]['average']
      if count > 0 and ave > 0:
        length = args['finishtime'] - args['starttime']
        msg.append(' %s%s %smobs killed' % (self.variables['statcolor'],
          count, self.variables['infocolor']))
        msg.append(' (%s%02.02f%sxp/mob' % (self.variables['statcolor'],
          ave, self.variables['infocolor']))
        if length:
          expmin = exported.GMCP.getv('char.base.perlevel')/(length/60)
          if int(expmin) > self.variables['exppermin']:
            msg.append(' %s%02d%sxp/min' % (self.variables['statcolor'],
              expmin, self.variables['infocolor']))
        msg.append(')')

    self.addmessage(''.join(msg))

  def addmessage(self, msg):
    """
    add a message to the out queue
    """
    self.msgs.append(msg)

    exported.event.register('trigger_emptyline', self.showmessages)

    #exported.timer.add('msgtimer',
                #{'func':self.showmessages, 'seconds':1, 'onetime':True,
                 #'nodupe':True})

  def showmessages(self, _=None):
    """
    show a message
    """
    exported.event.unregister('trigger_emptyline', self.showmessages)
    for i in self.msgs:
      exported.sendtoclient(i, preamble=False)

    self.msgs = []

  def statreport(self, tminutes=None):
    """
    return a report of stats for a # of minutes
    """
    if not exported.plugins.isinstalled('statdb'):
      return []

    linelen = 50
    msg = ['']
    finishtime = time.time()

    emptystats = {'infocolor':self.variables['infocolor'],
                  'statcolor':self.variables['statcolor'],
                  'xp':0,
                  'qp':0,
                  'total':0,
                  'gold':0,
                  'tp':0}

    queststats = copy.deepcopy(emptystats)
    queststats['type'] = 'Quests'
    cpstats = copy.deepcopy(emptystats)
    cpstats['type'] = 'CPs'
    gqstats = copy.deepcopy(emptystats)
    gqstats['type'] = 'GQs'
    mobstats = copy.deepcopy(emptystats)
    mobstats['type'] = 'Mobs'
    hourtotals = copy.deepcopy(emptystats)
    hourtotals['type'] = 'Total'

    minutes = tminutes or self.variables['reportminutes']
    starttime = finishtime - (minutes * 60)

    timestr = '%s' % utils.timedeltatostring(starttime,
              finishtime,
              colorn=self.variables['statcolor'],
              colors=self.variables['infocolor'],
              nosec=True)

    stmt = """SELECT COUNT(*) as total,
                     SUM(totqp) as qp,
                     SUM(gold) as gold,
                     SUM(tp) as tp
                     FROM quests where finishtime > %d""" % starttime
    tst = exported.statdb.runselect(stmt)
    if tst[0]['total'] > 0:
      queststats.update(tst[0])

    stmt = """SELECT COUNT(*) as total,
                     SUM(qp) as qp,
                     SUM(gold) as gold,
                     SUM(tp) as tp
                     FROM campaigns
                     where finishtime > %d and failed = 0""" % starttime
    tst = exported.statdb.runselect(stmt)
    if tst[0]['total'] > 0:
      cpstats.update(tst[0])

    stmt = """SELECT COUNT(*) as total,
                     SUM(qp + qpmobs) as qp,
                     SUM(gold) as gold,
                     SUM(tp) as tp
                     FROM gquests where finishtime > %d""" % starttime
    tst = exported.statdb.runselect(stmt)
    if tst[0]['total'] > 0:
      gqstats.update(tst[0])

    stmt = """SELECT COUNT(*) as total,
                     SUM(totalxp) as xp,
                     SUM(gold) as gold,
                     SUM(tp) as tp
                     FROM mobkills where time > %d""" % starttime
    tst = exported.statdb.runselect(stmt)
    if tst[0]['total'] > 0:
      mobstats.update(tst[0])

    hourtotals['total'] = ""
    hourtotals['xp'] = mobstats['xp'] + gqstats['xp'] + \
                        cpstats['xp'] + queststats['xp']

    hourtotals['qp'] = mobstats['qp'] + gqstats['qp'] + \
                        cpstats['qp'] + queststats['qp']

    hourtotals['tp'] = mobstats['tp'] + gqstats['tp'] + \
                        cpstats['tp'] + queststats['tp']

    hourtotals['gold'] = mobstats['gold'] + gqstats['gold'] + \
                        cpstats['gold'] + queststats['gold']

    namestr = "Stats for {timestr}".format(
                  infocolor=self.variables['infocolor'],
                  statcolor=self.variables['statcolor'],
                  timestr=timestr)

    msg.append(self.variables['infocolor'] + \
                  utils.center(namestr, '-', linelen))
    fstring = "{infocolor}{type:<10} | {total:>6} " \
              "{xp:>6} {qp:>5} {tp:>5} {gold:>10}"
    msg.append(fstring.format(type='Type',
        total='Total', xp='XP', qp='QP', tp='TP', gold='Gold',
        infocolor=self.variables['infocolor']))
    msg.append(self.variables['infocolor'] + '-' * linelen)

    fstring = "{statcolor}{type:<10} {infocolor}| {statcolor}" \
              "{total:>6} {xp:>6} {qp:>5} {tp:>5} {gold:>10}"

    msg.append(fstring.format(**queststats))

    msg.append(fstring.format(**cpstats))

    msg.append(fstring.format(**gqstats))

    msg.append(fstring.format(**mobstats))

    msg.append(self.variables['infocolor'] + '-' * linelen)

    msg.append(fstring.format(**hourtotals))

    msg.append('')
    return msg

  def cmd_rep(self, args):
    """
    do a cmd report
    """
    minutes = None
    if len(args) > 0:
      minutes = int(args[0])
    else:
      minutes = self.variables['reportminutes']

    msg = self.statreport(minutes)

    exported.sendtoclient('\n'.join(msg), preamble=False)

    return True, []

