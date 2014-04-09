"""
$Id$

This plugin holds a stat database for quests/cp/gqs/mobkills
"""
import copy
import time
import argparse
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'StatDB'
SNAME = 'statdb'
PURPOSE = 'Add events to the stat database'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

def format_float(item, addto=""):
  """
  format a floating point #
  """
  if item:
    tempt = "%.03f%s" % (item, addto)
  else:
    tempt = 0
  return tempt

def dbcreate(Sqldb, plugin, **kwargs):
  """
  create the statdb class, this is needed because the Sqldb baseclass
  can be reloaded since it is a plugin
  """
  class Statdb(Sqldb):
    """
    a class to manage a sqlite database for aardwolf events
    """
    def __init__(self, plugin, **kwargs):
      """
      initialize the class
      """
      Sqldb.__init__(self, plugin, **kwargs)

      self.version = 13

      self.versionfuncs[13] = self.addrarexp_v13

      self.addtable('stats', """CREATE TABLE stats(
            stat_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            name TEXT NOT NULL,
            level INT default 1,
            totallevels INT default 1,
            remorts INT default 1,
            tiers INT default 0,
            race TEXT default "",
            sex TEXT default "",
            subclass TEXT default "",
            qpearned INT default 0,
            questscomplete INT default 0 ,
            questsfailed INT default 0,
            campaignsdone INT default 0,
            campaignsfld INT default 0,
            gquestswon INT default 0,
            duelswon INT default 0,
            duelslost INT default 0,
            timeskilled INT default 0,
            monsterskilled INT default 0,
            combatmazewins INT default 0,
            combatmazedeaths INT default 0,
            powerupsall INT default 0,
            totaltrivia INT default 0,
            time INT default 0,
            milestone TEXT,
            redos INT default 0
          );""", keyfield='stat_id')

      self.addtable('quests', """CREATE TABLE quests(
            quest_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            starttime INT default 0,
            finishtime INT default 0,
            mobname TEXT default "Unknown",
            mobarea TEXT default "Unknown",
            mobroom TEXT default "Unknown",
            qp INT default 0,
            double INT default 0,
            daily INT default 0,
            totqp INT default 0,
            gold INT default 0,
            tier INT default 0,
            mccp INT default 0,
            lucky INT default 0,
            tp INT default 0,
            trains INT default 0,
            pracs INT default 0,
            level INT default -1,
            failed INT default 0
          );""", keyfield='quest_id')

      self.addtable('classes', """CREATE TABLE classes(
              class TEXT NOT NULL PRIMARY KEY,
              remort INTEGER
            );""", keyfield='class', postcreate=self.initclasses)

      self.addtable('levels', """CREATE TABLE levels(
            level_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            type TEXT default "level",
            level INT default -1,
            str INT default 0,
            int INT default 0,
            wis INT default 0,
            dex INT default 0,
            con INT default 0,
            luc INT default 0,
            starttime INT default -1,
            finishtime INT default -1,
            hp INT default 0,
            mp INT default 0,
            mv INT default 0,
            pracs INT default 0,
            trains INT default 0,
            bonustrains INT default 0,
            blessingtrains INT default 0
          )""", keyfield='level_id')

      self.addtable('campaigns', """CREATE TABLE campaigns(
            cp_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            starttime INT default 0,
            finishtime INT default 0,
            qp INT default 0,
            bonusqp INT default 0,
            gold INT default 0,
            tp INT default 0,
            trains INT default 0,
            pracs INT default 0,
            level INT default -1,
            failed INT default 0
          );""", keyfield='cp_id')

      self.addtable('cpmobs', """CREATE TABLE cpmobs(
            cpmob_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            cp_id INT NOT NULL,
            name TEXT default "Unknown",
            location TEXT default "Unknown"
          )""", keyfield='cpmob_id')

      self.addtable('mobkills', """CREATE TABLE mobkills(
            mk_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            name TEXT default "Unknown",
            xp INT default 0,
            rarexp INT default 0,
            bonusxp INT default 0,
            blessingxp INT default 0,
            totalxp INT default 0,
            gold INT default 0,
            tp INT default 0,
            time INT default -1,
            vorpal INT default 0,
            banishment INT default 0,
            assassinate INT default 0,
            slit INT default 0,
            disintegrate INT default 0,
            deathblow INT default 0,
            wielded_weapon TEXT default '',
            second_weapon TEXT default '',
            room_id INT default 0,
            level INT default -1
          )""", keyfield='mk_id')

      self.addtable('gquests', """CREATE TABLE gquests(
            gq_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            starttime INT default 0,
            finishtime INT default 0,
            qp INT default 0,
            qpmobs INT default 0,
            gold INT default 0,
            tp INT default 0,
            trains INT default 0,
            pracs INT default 0,
            level INT default -1,
            won INT default 0,
            completed INT default 0
          )""", keyfield='gq_id')


      self.addtable('gqmobs', """CREATE TABLE gqmobs(
            gqmob_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            gq_id INT NOT NULL,
            num INT,
            name TEXT default "Unknown",
            location TEXT default "Unknown"
          )""", keyfield='gqmob_id')

      # Need to do this after adding tables
      self.postinit()

    def turnonpragmas(self):
      #-- PRAGMA foreign_keys = ON;
      self.dbconn.execute("PRAGMA foreign_keys=On;")
      #-- PRAGMA journal_mode=WAL
      self.dbconn.execute("PRAGMA journal_mode=WAL;")

    def savequest(self, questinfo):
      """
      save a quest in the db
      """
      if questinfo['failed'] == 1:
        self.addtostat('questsfailed', 1)
      else:
        self.addtostat('questscomplete', 1)
        self.addtostat('questpoints', questinfo['totqp'])
        self.addtostat('qpearned', questinfo['totqp'])
        self.addtostat('triviapoints', questinfo['tp'])
        self.addtostat('totaltrivia', questinfo['tp'])

      cur = self.dbconn.cursor()
      stmt = self.converttoinsert('quests', keynull=True)
      cur.execute(stmt, questinfo)
      rowid = cur.lastrowid
      self.dbconn.commit()
      cur.close()
      self.api.get('send.msg')('added quest: %s' % rowid)
      return rowid

    def setstat(self, stat, value):
      """
      set a stat
      """
      cur = self.dbconn.cursor()
      stmt = 'update stats set %s=%s where milestone = "current"' % (
                                                        stat, value)
      cur.execute(stmt)
      self.dbconn.commit()
      cur.close()
      self.api.get('send.msg')('set %s to %s' % (stat, value))

    def getstat(self, stat):
      """
      get a stat from the stats table
      """
      tstat = None
      cur = self.dbconn.cursor()
      cur.execute('SELECT * FROM stats WHERE milestone = "current"')
      row = cur.fetchone()
      if row and stat in row:
        tstat = row[stat]
      cur.close()
      return tstat

    def addtostat(self, stat, add):
      """
      add to  a stat in the stats table
      """
      if add <= 0:
        return True

      if self.checkcolumnexists('stats', stat):
        cur = self.dbconn.cursor()
        cur.execute(
            "UPDATE stats SET %s = %s + %s WHERE milestone = 'current'" \
            % (stat, stat, add))
        self.dbconn.commit()
        cur.close()

    def savewhois(self, whoisinfo):
      """
      save info into the stats table
      """
      cur = self.dbconn.cursor()
      if self.getstat('totallevels'):
        nokey = {}
        nokey['stat_id'] = True
        nokey['totaltrivia'] = True
        whoisinfo['milestone'] = 'current'
        whoisinfo['time'] = 0
        stmt = self.converttoupdate('stats', 'milestone', nokey)
        cur.execute(stmt, whoisinfo)
      else:
        whoisinfo['milestone'] = 'current'
        whoisinfo['totaltrivia'] = 0
        whoisinfo['time'] = 0
        stmt = self.converttoinsert('stats', True)
        cur.execute(stmt, whoisinfo)
        #add a milestone here
        self.addmilestone('start')

      self.dbconn.commit()
      cur.close()
      self.api.get('send.msg')('updated stats')
      # add classes here
      self.addclasses(whoisinfo['classes'])

    def addmilestone(self, milestone):
      """
      add a milestone
      """
      if not milestone:
        return

      trows = self.runselect('SELECT * FROM stats WHERE milestone = "%s"' \
                                                            % milestone)
      if len(trows) > 0:
        self.api.get('send.client')('@RMilestone %s already exists' % milestone)
        return -1

      stats = self.runselect('SELECT * FROM stats WHERE milestone = "current"')
      tstats = stats[0]

      if tstats:
        tstats['milestone'] = milestone
        tstats['time'] = time.time()
        stmt = self.converttoinsert('stats', True)
        cur = self.dbconn.cursor()
        cur.execute(stmt, tstats)
        trow = cur.lastrowid
        self.dbconn.commit()
        cur.close()

        self.api.get('send.msg')('inserted milestone %s with rowid: %s' % (
                                              milestone, trow))
        return trow

      return -1

    def addclasses(self, classes):
      """
      add classes from whois
      """
      stmt = 'UPDATE CLASSES SET REMORT = :remort WHERE class = :class'
      cur = self.dbconn.cursor()
      cur.executemany(stmt, classes)
      self.dbconn.commit()
      cur.close()

    def getclasses(self):
      """
      get all classes
      """
      classes = []
      tclasses = self.runselect('SELECT * FROM classes ORDER by remort ASC')
      for i in tclasses:
        if i['remort'] != -1:
          classes.append(i['class'])

      return classes

    def initclasses(self):
      """
      initialize the class table
      """
      classabb = self.api.get('aardu.classabb')()
      classes = []
      for i in classabb:
        classes.append({'class':i})
      stmt = "INSERT INTO classes VALUES (:class, -1)"
      cur = self.dbconn.cursor()
      cur.executemany(stmt, classes)
      self.dbconn.commit()
      cur.close()

    def resetclasses(self):
      """
      reset the class table
      """
      classabb = self.api.get('aardu.classabb')()
      classes = []
      for i in classabb:
        classes.append({'class':i})
      stmt = """UPDATE classes SET remort = -1
                      WHERE class = :class"""
      cur = self.dbconn.cursor()
      cur.executemany(stmt, classes)
      self.dbconn.commit()
      cur.close()

    def savecp(self, cpinfo):
      """
      save cp information
      """
      if cpinfo['failed'] == 1:
        self.addtostat('campaignsfld', 1)
      else:
        self.addtostat('campaignsdone', 1)
        self.addtostat('questpoints', cpinfo['qp'])
        self.addtostat('qpearned', cpinfo['qp'])
        self.addtostat('triviapoints', cpinfo['tp'])
        self.addtostat('totaltrivia', cpinfo['tp'])

      stmt = self.converttoinsert('campaigns', keynull=True)
      cur = self.dbconn.cursor()
      cur.execute(stmt, cpinfo)
      rowid = self.getlastrowid('campaigns')
      self.dbconn.commit()
      cur.close()
      self.api.get('send.msg')('added cp: %s' % rowid)

      for i in cpinfo['mobs']:
        i['cp_id'] = rowid
      stmt2 = self.converttoinsert('cpmobs', keynull=True)
      cur = self.dbconn.cursor()
      cur.executemany(stmt2, cpinfo['mobs'])
      self.dbconn.commit()
      cur.close()

    def savegq(self, gqinfo):
      """
      save gq information
      """
      self.addtostat('questpoints', int(gqinfo['qp']) + int(gqinfo['qpmobs']))
      self.addtostat('qpearned', int(gqinfo['qp']) + int(gqinfo['qpmobs']))
      self.addtostat('triviapoints', gqinfo['tp'])
      self.addtostat('totaltrivia', gqinfo['tp'])
      if gqinfo['won'] == 1:
        self.addtostat('gquestswon', 1)

      stmt = self.converttoinsert('gquests', keynull=True)
      cur = self.dbconn.cursor()
      cur.execute(stmt, gqinfo)
      rowid = self.getlastrowid('gquests')
      self.dbconn.commit()
      cur.close()
      self.api.get('send.msg')('added gq: %s' % rowid)

      for i in gqinfo['mobs']:
        i['gq_id'] = rowid
      stmt2 = self.converttoinsert('gqmobs', keynull=True)
      cur = self.dbconn.cursor()
      cur.executemany(stmt2, gqinfo['mobs'])
      self.dbconn.commit()
      cur.close()

    def savelevel(self, levelinfo, first=False):
      """
      save a level
      """
      rowid = -1
      if not first:
        if levelinfo['type'] == 'level':
          if levelinfo['totallevels'] and levelinfo['totallevels'] > 0:
            self.setstat('totallevels', levelinfo['totallevels'])
            self.setstat('level', levelinfo['level'])
          else:
            self.addtostat('totallevels', 1)
            self.addtostat('level', 1)
        elif levelinfo['type'] == 'pup':
          self.addtostat('powerupsall', 1)
        if levelinfo['totallevels'] and levelinfo['totallevels'] > 0:
          levelinfo['level'] = levelinfo['totallevels']
        else:
          levelinfo['level'] = self.getstat('totallevels')

      levelinfo['finishtime'] = -1
      cur = self.dbconn.cursor()
      stmt = self.converttoinsert('levels', keynull=True)
      cur.execute(stmt, levelinfo)
      rowid = self.getlastrowid('levels')
      self.api.get('send.msg')('inserted level %s' % rowid)
      if rowid > 1:
        stmt2 = "UPDATE levels SET finishtime = %s WHERE level_id = %d" % (
                      levelinfo['starttime'], int(rowid) - 1)
        cur.execute(stmt2)
      self.dbconn.commit()
      cur.close()

      if levelinfo['type'] == 'level':
        self.addmilestone(str(levelinfo['totallevels']))

      return rowid

    def savemobkill(self, killinfo):
      """
      save a mob kill
      """
      self.addtostat('totaltrivia', killinfo['tp'])
      self.addtostat('monsterskilled', 1)
      if not killinfo['name']:
        killinfo['name'] = 'Unknown'
      cur = self.dbconn.cursor()
      stmt = self.converttoinsert('mobkills', keynull=True)
      cur.execute(stmt, killinfo)
      self.dbconn.commit()
      rowid = self.getlastrowid('mobkills')
      cur.close()
      self.api.get('send.msg')('inserted mobkill: %s' % rowid)

    def addrarexp_v13(self):
      """
      add rare xp into the database
      """
      if not self.checktableexists('mobkills'):
        return

      oldmobst = self.runselect('SELECT * FROM mobkills ORDER BY mk_id ASC')

      cur = self.dbconn.cursor()
      cur.execute('DROP TABLE IF EXISTS mobkills;')
      cur.close()
      self.close()

      self.open()
      cur = self.dbconn.cursor()
      cur.execute("""CREATE TABLE mobkills(
            mk_id INTEGER NOT NULL PRIMARY KEY autoincrement,
            name TEXT default "Unknown",
            xp INT default 0,
            rarexp INT default 0,
            bonusxp INT default 0,
            blessingxp INT default 0,
            totalxp INT default 0,
            gold INT default 0,
            tp INT default 0,
            time INT default -1,
            vorpal INT default 0,
            banishment INT default 0,
            assassinate INT default 0,
            slit INT default 0,
            disintegrate INT default 0,
            deathblow INT default 0,
            wielded_weapon TEXT default '',
            second_weapon TEXT default '',
            room_id INT default 0,
            level INT default -1
          )""")
      cur.close()

      cur = self.dbconn.cursor()
      stmt2 = """INSERT INTO mobkills VALUES (:mk_id, :name, :xp, 0,
                    :bonusxp, :blessingxp, :totalxp, :gold, :tp, :time, :vorpal,
                    :banishment, :assassinate, :slit, :disintegrate, :deathblow,
                    :wielded_weapon, :second_weapon, :room_id, :level)"""
      cur.executemany(stmt2, oldmobst)
      cur.close()

  return Statdb(plugin, **kwargs)


class Plugin(AardwolfBasePlugin):
  """
  a plugin to catch aardwolf stats and add them to a database
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.api.get('dependency.add')('sqldb')
    self.api.get('dependency.add')('aardwolf.whois')
    self.api.get('dependency.add')('aardwolf.level')
    self.api.get('dependency.add')('aardwolf.mobk')
    self.api.get('dependency.add')('aardwolf.cp')
    self.api.get('dependency.add')('aardwolf.gq')
    self.api.get('dependency.add')('aardwolf.quest')

    self.statdb = None

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.statdb = dbcreate(self.api.get('sqldb.baseclass')(), self,
                           dbname='stats')

    self.api.get('setting.add')('backupstart', '0000', 'miltime',
                      'the time for a db backup, like 1200 or 2000')
    self.api.get('setting.add')('backupinterval', '4h', 'timelength',
                      'the interval to backup the db, default every 4 hours')

    parser = argparse.ArgumentParser(add_help=False,
                 description='show quests stats')
    parser.add_argument('count', help='the number of quests to show', default=0, nargs='?')
    self.api.get('commands.add')('quests', self.cmd_quests,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show level stats')
    parser.add_argument('count', help='the number of levels to show', default=0, nargs='?')
    self.api.get('commands.add')('levels', self.cmd_levels,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show cp stats')
    parser.add_argument('count', help='the number of cps to show', default=0, nargs='?')
    self.api.get('commands.add')('cps', self.cmd_cps,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show gq stats')
    parser.add_argument('count', help='the number of gqs to show', default=0, nargs='?')
    self.api.get('commands.add')('gqs', self.cmd_gqs,
                                parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show mob stats')
    parser.add_argument('count', help='the number of mobkills to show', default=0, nargs='?')
    self.api.get('commands.add')('mobs', self.cmd_mobs,
                                parser=parser)

    self.api.get('triggers.add')('dead',
      "^You die.$",
      enabled=True, group='dead')

    self.api.get('events.register')('aard_quest_comp', self.questevent)
    self.api.get('events.register')('aard_quest_failed', self.questevent)
    self.api.get('events.register')('aard_cp_comp', self.cpevent)
    self.api.get('events.register')('aard_cp_failed', self.cpevent)
    self.api.get('events.register')('aard_whois', self.whoisevent)
    self.api.get('events.register')('aard_level_gain', self.levelevent)
    self.api.get('events.register')('aard_level_hero', self.heroevent)
    self.api.get('events.register')('aard_level_superhero', self.heroevent)
    self.api.get('events.register')('aard_level_remort', self.heroevent)
    self.api.get('events.register')('aard_level_tier', self.heroevent)
    self.api.get('events.register')('aard_mobkill', self.mobkillevent)
    self.api.get('events.register')('aard_gq_completed', self.gqevent)
    self.api.get('events.register')('aard_gq_done', self.gqevent)
    self.api.get('events.register')('aard_gq_won', self.gqevent)
    self.api.get('events.register')('GMCP:char.status', self.checkstats)
    self.api.get('events.register')('var_statdb_backupstart', self.changetimer)
    self.api.get('events.register')('var_statdb_backupinternval', self.changetimer)

    self.api.get('events.register')('trigger_dead', self.dead)

    self.api.get('timers.add')('stats_backup', self.backupdb,
                                self.api.get('setting.gets')('backupinterval'),
                                time=self.api.get('setting.gets')('backupstart'))

    self.api.get('api.add')('runselect', self.api_runselect)

  def changetimer(self, _=None):
    """
    do something when the reportminutes changes
    """
    backupinterval = self.api.get('setting.gets')('backupinterval')
    backupstart = self.api.get('setting.gets')('backupstart')
    self.api.get('timers.remove')('stats_backup')
    self.api.get('timers.add')('stats_backup', self.backupdb,
                               backupinterval, time=backupstart)

  def backupdb(self):
    """
    backup the db from the timer
    """
    tstr = time.strftime('%a-%b-%d-%Y-%H-%M', time.localtime())
    if self.statdb:
      self.statdb.backupdb(tstr)

  def dead(self, _):
    """
    add to timeskilled when dead
    """
    self.statdb.addtostat('timeskilled', 1)

  def checkstats(self, _=None):
    """
    check to see if we have stats
    """
    state = self.api.get('GMCP.getv')('char.status.state')
    if state == 3:
      self.api.get('events.unregister')('GMCP:char.status', self.checkstats)
      if not self.statdb.getstat('monsterskilled'):
        self.api.get('send.execute')('whois')

  def _format_row(self, rowname, data1, data2, datacolor="@W",
                    headercolor="@C"):
    """
    format a row of data
    """
    lstr = '%s%-14s : %s%-12s %s%-12s' % (headercolor, rowname,
      datacolor, data1, datacolor, data2)

    return lstr

  def cmd_quests(self, args=None):
    """
    show quest stats
    """
    count = 0
    if args and args['count']:
      count = args['count']

    msg = []

    if self.statdb.getlastrowid('stats') <= 0:
      return True, ['No stats available']

    if self.statdb.getlastrowid('quests') <= 0:
      return True, ['No quests stats are available']


    tqrow = self.statdb.runselect(
        """SELECT AVG(finishtime - starttime) as avetime,
                      SUM(qp) as qp,
                      SUM(tier) as tier,
                      AVG(tier) as tierave,
                      SUM(mccp) as mccp,
                      AVG(mccp) as mccpave,
                      SUM(lucky) as lucky,
                      AVG(qp) as qpquestave,
                      AVG(lucky) as luckyave,
                      SUM(tp) as tp,
                      AVG(tp) as tpave,
                      SUM(trains) as trains,
                      AVG(trains) as trainsave,
                      SUM(pracs) as pracs,
                      AVG(pracs) as pracsave,
                      COUNT(*) as qindb,
                      SUM(totqp) as dboverall,
                      AVG(totqp) as dboverallave,
                      SUM(gold) as gold,
                      AVG(gold) as avegold FROM quests where failed = 0""")
    stats = tqrow[0]
    tfrow = self.statdb.runselect(
            "SELECT COUNT(*) as failedindb FROM quests where failed != 0")
    stats.update(tfrow[0])
    tsrow = self.statdb.runselect(
         """SELECT qpearned, questscomplete, questsfailed,
            totallevels FROM stats WHERE milestone = 'current'""")
    stats.update(tsrow[0])
    stats['indb'] = stats['failedindb'] + stats['qindb']
    stats['qplevelave'] = stats['qpearned']/float(stats['totallevels'])
    msg.append(self._format_row('DB Stats', 'Total', 'In DB', '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("Quests",
              stats['questscomplete'] + stats['questsfailed'],
              stats['indb']))
    msg.append(self._format_row("Quests Comp",
              stats['questscomplete'], stats['qindb']))
    msg.append(self._format_row("Quests Failed",
              stats['questsfailed'], stats['failedindb']))
    msg.append('')
    msg.append(self._format_row("QP Stats", "Total", "Average", '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("Overall QP", stats['qpearned'],
        format_float(stats['qplevelave'], "/level")))
    msg.append(self._format_row("Quest QP", stats['qp'],
        format_float(stats['qpquestave'], "/quest")))
    msg.append(self._format_row("MCCP", stats['mccp'],
        format_float(stats['mccpave'], "/quest")))
    msg.append(self._format_row("Lucky", stats['lucky'],
        format_float(stats['luckyave'], "/quest")))
    msg.append(self._format_row("Tier", stats['tier'],
        format_float(stats['tierave'], "/quest")))
    msg.append(self._format_row("QP Per Quest", "",
        format_float(stats['dboverallave'], "/quest")))
    msg.append(self._format_row("Gold",
          self.api.get('utils.readablenumber')(stats['gold'], 2),
          "%d/quest" % stats['avegold']))
    msg.append(self._format_row("Time", "", self.api.get('utils.formattime')(stats['avetime'])))
    msg.append('')
    msg.append(self._format_row("Bonus Rewards", "Total",
                              "Average", '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("TP", stats['tp'],
        format_float(stats['tpave'], "/quest")))
    msg.append(self._format_row("Trains", stats['trains'],
        format_float(stats['trainsave'], "/quest")))
    msg.append(self._format_row("Pracs", stats['pracs'],
        format_float(stats['pracsave'], "/quest")))

    if int(count) > 0:
      lastitems = self.statdb.getlast('quests', int(count))
      if len(lastitems) > 0:
        msg.append('')
        msg.append("@G%-6s %-2s %-2s %-2s %-2s %-3s" \
                        " %-2s %-2s %-2s %-2s %-4s %-3s   %s" % ("ID", "QP",
                        "MC", "TR", "LK", "DBL", "TL", "TP", "TN",
                        "PR", "Gold", "Lvl",  "Time"))
        msg.append('@G----------------------------------------------------')

        for item in lastitems:
          dbl = ''
          if int(item['double']) == 1:
            dbl = dbl + 'D'
          if int(item['daily']) == 1:
            dbl = dbl + 'E'

          leveld = self.api.get('aardu.convertlevel')(item['level'])

          ttime = self.api.get('utils.formattime')(item['finishtime'] - item['starttime'])
          if int(item['failed']) == 1:
            ttime = 'Failed'
          msg.append("%-6s %2s %2s %2s %2s %3s" \
                        " %2s %2s %2s %2s %4s %3s %8s" % (
                        item['quest_id'], item['qp'],
                        item['mccp'], item['tier'], item['lucky'],
                        dbl, item['totqp'], item['tp'],
                        item['trains'], item['pracs'], item['gold'],
                        leveld['level'],  ttime))

    return True, msg

  def cmd_levels(self, args=None):
    """
    show level stats
    """
    count = 0
    if args:
      count = args['count']

    msg = []
    pups = {}
    levels = {}

    if self.statdb.getlastrowid('stats') <= 0:
      return True, ['No stats available']

    if self.statdb.getlastrowid('levels') <= 0:
      return True, ['No levels/pups stats available']

    lrow = self.statdb.runselect(
        "SELECT totallevels, qpearned FROM stats WHERE milestone = 'current'")
    levels.update(lrow[0])

    prow = self.statdb.runselect(
        "SELECT MAX(powerupsall) as powerupsall FROM stats")
    pups.update(prow[0])

    levels['qpave'] = int(levels['qpearned']) / int(levels['totallevels'])

    llrow = self.statdb.runselect("""
             SELECT AVG(trains) as avetrains,
                    AVG(bonustrains) as avebonustrains,
                    AVG(blessingtrains) as aveblessingtrains,
                    SUM(trains + bonustrains + blessingtrains) as totaltrains,
                    SUM(pracs) as totalpracs,
                    COUNT(*) as indb
                    FROM levels where type = 'level' and trains > 0
                    """)
    levels.update(llrow[0])

    ltrow = self.statdb.runselect("""
             SELECT AVG(finishtime - starttime) as avetime FROM levels
             where type = 'level' and finishtime <> -1 and trains > 0
                    """)
    levels.update(ltrow[0])

    pprow = self.statdb.runselect("""
             SELECT AVG(trains) as avetrains,
                    AVG(bonustrains) as avebonustrains,
                    AVG(blessingtrains) as aveblessingtrains,
                    SUM(trains + bonustrains + blessingtrains) as totaltrains,
                    COUNT(*) as indb
                    FROM levels where type = 'pup'
                    """)
    pups.update(pprow[0])

    ptrow = self.statdb.runselect("""
             SELECT AVG(finishtime - starttime) as avetime FROM levels
             where type = 'pup' and finishtime <> -1
                    """)
    pups.update(ptrow[0])

    msg.append(self._format_row('Type', 'Levels', 'Pups', '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("Total Overall",
                levels['totallevels'], pups['powerupsall']))
    msg.append(self._format_row("Total In DB",
                levels['indb'], pups['indb']))
    msg.append(self._format_row("Total Trains",
                levels['totaltrains'] or "", pups['totaltrains'] or ""))

    lavet = format_float(levels['avetrains'])
    pavet = format_float(pups['avetrains'])
    msg.append(self._format_row("Ave Trains",
                lavet or "", pavet or ""))

    lbavet = format_float(levels['avebonustrains'])
    pbavet = format_float(pups['avebonustrains'])
    msg.append(self._format_row("Ave Bon Trains",
                lbavet or "", pbavet or ""))

    ldavet = format_float(levels['aveblessingtrains'])
    pdavet = format_float(pups['aveblessingtrains'])
    msg.append(self._format_row("Ave Bls Trains",
                ldavet or "", pdavet or ""))

    latave = float(lavet) + float(lbavet) + float(ldavet)
    patave = float(pavet) + float(pbavet) + float(pdavet)

    msg.append(self._format_row("Ave Overall",
                latave or "", patave or ""))
    msg.append(self._format_row("Total Pracs",
                levels['totalpracs'], ""))

    if levels['avetime']:
      lavetime = self.api.get('utils.formattime')(levels['avetime'])
    else:
      lavetime = ""

    if pups['avetime']:
      pavetime = self.api.get('utils.formattime')(pups['avetime'])
    else:
      pavetime = ""

    msg.append(self._format_row("Time", lavetime, pavetime))

    if int(count) > 0:
      lastitems = self.statdb.getlast('levels', int(count))

      if len(lastitems) > 0:
        msg.append('')
        msg.append("@G%-6s %-3s %2s %2s %-2s %-2s %-2s" \
                  " %-2s %-1s %-1s %-1s %-1s %-1s %-1s   %s" % ("ID", "Lvl",
                  "TR", "BT", "PR", "HP", "MN", "MV", "S",
                  "I", "W", "C",  "D", "L", "Time"))
        msg.append('@G----------------------------------------------------')

        for item in lastitems:
          bonus = 0
          if int(item['bonustrains']) > 0:
            bonus = bonus + int(item['bonustrains'])
          if int(item['blessingtrains']) > 0:
            bonus = bonus + int(item['blessingtrains'])

          leveld = self.api.get('aardu.convertlevel')(item['level'])

          if item['finishtime'] != '-1' and item['starttime'] != '-1':
            ttime = self.api.get('utils.formattime')(item['finishtime'] - item['starttime'])
          else:
            ttime = ''

          msg.append("%-6s %-3s %2s %2s %-2s %-2s %-2s" \
                     " %-2s %-1s %-1s %-1s %-1s %-1s %-1s   %s" % (
                     item['level_id'], leveld['level'], item['trains'],
                     bonus, item['pracs'], item['hp'], item['mp'],
                     item['mv'], item['str'], item['int'], item['wis'],
                     item['con'], item['dex'], item['luc'], ttime))


    return True, msg

  def cmd_cps(self, args=None):
    """
    show cp stats
    """
    count = 0
    if args:
      count = args['count']

    msg = []
    stats = {}

    if self.statdb.getlastrowid('stats') <= 0:
      return True, ['No stats available']

    if self.statdb.getlastrowid('campaigns') <= 0:
      return True, ['No campaign stats available']

    trow = self.statdb.runselect(
        "SELECT campaignsdone, campaignsfld, totallevels " \
        "FROM stats WHERE milestone = 'current'")
    stats.update(trow[0])

    trow = self.statdb.runselect(
        """SELECT AVG(finishtime - starttime) as avetime,
                  SUM(qp) as totalqp,
                  AVG(qp) as aveqp,
                  SUM(tp) as totaltp,
                  AVG(tp) as avetp,
                  SUM(trains) as totaltrains,
                  AVG(trains) as avetrains,
                  SUM(pracs) as totalpracs,
                  AVG(pracs) as avepracs,
                  COUNT(*) as cindb,
                  SUM(gold) as totalgold,
                  AVG(gold) as avegold
                  FROM campaigns where failed = 0""")
    stats.update(trow[0])

    trow = self.statdb.runselect(
       "SELECT COUNT(*) as failedindb FROM campaigns where failed != 0")
    stats.update(trow[0])

    stats['indb'] = int(stats['cindb']) + int(stats['failedindb'])
    stats['totalcps'] = int(stats['campaignsdone']) + \
                        int(stats['campaignsfld'])

    msg.append(self._format_row('DB Stats', 'Total', 'In DB', '@G', '@G'))
    msg.append('@G--------------------------------------------')

    msg.append(self._format_row("Overall",
                stats['totalcps'], stats['indb'] or 0))
    msg.append(self._format_row("Completed",
                stats['campaignsdone'], stats['cindb'] or 0))
    msg.append(self._format_row("Failed",
                stats['campaignsfld'], stats['failedindb'] or 0))

    msg.append('')
    msg.append(self._format_row('CP Stats', 'Total', 'Average', '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("QP",
                stats['totalqp'] or 0,
                format_float(stats['aveqp'], "/CP")))
    if stats['totalgold']:
      tempg = self.api.get('utils.readablenumber')(stats['totalgold'])
    else:
      tempg = 0

    msg.append(self._format_row("Gold",
                tempg,
                "%d/CP" % stats['avegold']))
    if stats['avetime']:
      atime = self.api.get('utils.formattime')(stats['avetime'])
    else:
      atime = ""

    msg.append(self._format_row("Time", "", atime))

    msg.append('')
    msg.append(self._format_row("Bonus Rewards", "Total",
                              "Average", '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("TP",
                stats['totaltp'] or 0,
                format_float(stats['avetp'], "/CP")))
    msg.append(self._format_row("Trains",
                stats['totaltrains'] or 0,
                format_float(stats['avetrains'], "/CP")))

    msg.append(self._format_row("Pracs",
                stats['totalpracs'] or 0,
                format_float(stats['avepracs'], "/CP")))

    if int(count) > 0:
      lastitems = self.statdb.getlast('campaigns', int(count))

      mobc = self.statdb.runselectbykeyword(
          'SELECT cp_id, count(*) as mobcount from cpmobs group by cp_id',
          'cp_id')

      if len(lastitems) > 0:
        msg.append('')
        msg.append("@G%-6s %-12s %-2s %-2s %-2s %-2s %-2s %6s" \
                  " %-4s  %s" % ("ID", "Lvl",
                  "QP", "BN", "TP", "TN", "PR", "Gold", "Mobs", "Time"))
        msg.append('@G----------------------------------------------------')

        for item in lastitems:
          leveld = self.api.get('aardu.convertlevel')(item['level'])
          levelstr = 'T%d R%d L%d' % (leveld['tier'], leveld['remort'],
                              leveld['level'])

          if item['finishtime'] != '-1' and item['starttime'] != '-1':
            ttime = self.api.get('utils.formattime')(item['finishtime'] - item['starttime'])
          else:
            ttime = ''

          if int(item['failed']) == 1:
            ttime = 'Failed'

          msg.append("%-6s %-12s %-2s %2s %2s %2s %2s %6s" \
                     "  %-3s  %s" % (
                     item['cp_id'], levelstr, item['qp'], item['bonusqp'],
                     item['tp'], item['trains'], item['pracs'], item['gold'],
                     mobc[item['cp_id']]['mobcount'], ttime))

    return True, msg

  def cmd_gqs(self, args=None):
    """
    show gq stats
    """
    count = 0
    if args:
      count = args['count']

    msg = []
    stats = {}

    if self.statdb.getlastrowid('stats') <= 0:
      return True, ['No stats available']

    if self.statdb.getlastrowid('gquests') <= 0:
      return True, ['No gq stats available']

    wrow = self.statdb.runselect(
        """SELECT AVG(finishtime - starttime) as avetime,
                  SUM(qp) as qp,
                  AVG(qp) as qpave,
                  SUM(qpmobs) as qpmobs,
                  AVG(qpmobs) as qpmobsave,
                  SUM(tp) as tp,
                  AVG(tp) as tpave,
                  SUM(trains) as trains,
                  AVG(trains) as trainsave,
                  SUM(pracs) as pracs,
                  AVG(pracs) as pracsave,
                  COUNT(*) as indb,
                  SUM(gold) as gold,
                  AVG(gold) as avegold
                  FROM gquests where won = 1""")
    stats['won'] = wrow[0]

    trow = self.statdb.runselect(
        "SELECT gquestswon FROM stats WHERE milestone = 'current'")
    stats.update(trow[0])

    trow = self.statdb.runselect(
       """SELECT AVG(finishtime - starttime) as avetime,
                 SUM(qpmobs) as totalqp,
                 AVG(qpmobs) as aveqp,
                 COUNT(*) as indb
                 FROM gquests where won != 1""")
    stats['lost'] = trow[0]

    trow = self.statdb.runselect(
       """SELECT SUM(qpmobs + qp) as overallqp,
                 AVG(qpmobs + qp) as aveoverallqp
                 FROM gquests""")
    stats.update(trow[0])

    stats['indb'] = stats['won']['indb'] + stats['lost']['indb']
    stats['overall'] = stats['gquestswon'] + stats['lost']['indb']

    msg.append(self._format_row('GQ Stats', 'Total', 'In DB', '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("Won",
                stats['gquestswon'], stats['won']['indb'] or 0))
    msg.append(self._format_row("Lost",
                "", stats['lost']['indb'] or 0))
    msg.append(self._format_row("Overall",
                stats['overall'], stats['indb'] or 0))
    msg.append(self._format_row("QP",
                stats['overallqp'],
                format_float(stats['aveoverallqp'], "/GQ")))

    msg.append('')
    msg.append(self._format_row('GQ Won Stats', 'Total', 'Average',
                                '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("GQ QP",
                stats['won']['qp'],
                format_float(stats['won']['qpave'], "/GQ")))
    msg.append(self._format_row("GQ MOB QP",
                stats['won']['qpmobs'],
                format_float(stats['won']['qpmobsave'], "/GQ")))

    if stats['won']['avetime']:
      atime = self.api.get('utils.formattime')(stats['won']['avetime'])
    else:
      atime = ""

    msg.append(self._format_row("Time", "", atime))
    msg.append(self._format_row("Gold",
                self.api.get('utils.readablenumber')(stats['won']['gold']),
                "%d/GQ" % stats['won']['avegold']))
    msg.append(self._format_row("TP",
                stats['won']['tp'],
                format_float(stats['won']['tpave'], "/GQ")))
    msg.append(self._format_row("Trains",
                stats['won']['trains'],
                format_float(stats['won']['trainsave'], "/GQ")))
    msg.append(self._format_row("Pracs",
                stats['won']['pracs'],
                format_float(stats['won']['pracsave'], "/GQ")))

    msg.append('')
    msg.append(self._format_row('GQ Lost Stats', 'Total', 'Average',
                                '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("GQ MOB QP",
                stats['lost']['totalqp'],
                format_float(stats['lost']['aveqp'], "/GQ")))

    if int(count) > 0:
      lastitems = self.statdb.getlast('gquests', int(count))

      mobc = self.statdb.runselectbykeyword(
          'SELECT gq_id, SUM(num) as mobcount from gqmobs group by gq_id',
          'gq_id')

      if len(lastitems) > 0:
        msg.append('')
        msg.append("@G%-6s %-12s %-2s %-2s %-2s %-2s %-2s %6s" \
                  " %-4s  %s" % ("ID", "Lvl",
                  "QP", "QM", "TP", "TN", "PR", "Gold", "Mobs", "Time"))
        msg.append('@G----------------------------------------------------')

        for item in lastitems:
          leveld = self.api.get('aardu.convertlevel')(item['level'])
          levelstr = 'T%d R%d L%d' % (leveld['tier'], leveld['remort'],
                              leveld['level'])

          if item['finishtime'] != '-1' and item['starttime'] != '-1':
            ttime = self.api.get('utils.formattime')(item['finishtime'] - item['starttime'])
          else:
            ttime = ''

          msg.append("%-6s %-12s %2s %2s %2s %2s %2s %6s" \
                     "  %-3s  %s" % (
                     item['gq_id'], levelstr, item['qp'], item['qpmobs'],
                     item['tp'], item['trains'], item['pracs'], item['gold'],
                     mobc[item['gq_id']]['mobcount'], ttime))

    return True, msg

  def cmd_mobs(self, args=None):
    """
    show mobs stats
    """
    count = 0
    if args:
      count = args['count']

    msg = []
    stats = {}

    if self.statdb.getlastrowid('stats') <= 0:
      return True, ['No stats available']

    if self.statdb.getlastrowid('mobkills') <= 0:
      return True, ['No mob stats available']

    trow = self.statdb.runselect(
        "SELECT monsterskilled FROM stats WHERE milestone = 'current'")
    stats.update(trow[0])

    trow = self.statdb.runselect(
        """SELECT SUM(xp) AS xp,
                  SUM(rarexp) as rarexp,
                  SUM(bonusxp) AS bonusxp,
                  SUM(blessingxp) AS blessingxp,
                  SUM(totalxp) as totalxp,
                  AVG(xp) AS avexp,
                  AVG(totalxp) AS avetotalxp,
                  SUM(tp) AS tp,
                  SUM(vorpal) AS vorpal,
                  SUM(assassinate) AS assassinate,
                  SUM(disintegrate) AS disintegrate,
                  SUM(banishment) AS banishment,
                  SUM(slit) AS slit,
                  SUM(deathblow) AS deathblow,
                  SUM(gold) AS gold,
                  AVG(gold) AS avegold,
                  COUNT(*) AS indb
                  FROM mobkills""")
    stats.update(trow[0])

    trow = self.statdb.runselect(
       """SELECT AVG(bonusxp) as avebonusxp,
                 COUNT(*) as bonusmobsindb
                 FROM mobkills where bonusxp > 0""")
    stats.update(trow[0])

    trow = self.statdb.runselect(
       """SELECT AVG(blessingxp) as aveblessxp,
                 COUNT(*) as blessmobsindb
                 FROM mobkills where blessingxp > 0""")
    stats.update(trow[0])

    trow = self.statdb.runselect(
       """SELECT AVG(rarexp) as averarexp,
                 COUNT(*) as raremobsindb
                 FROM mobkills where rarexp > 0""")
    stats.update(trow[0])

    msg.append(self._format_row('DB Stats', 'Total', 'In DB', '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("Overall",
                stats['monsterskilled'], stats['indb'] or 0))
    msg.append(self._format_row("Rare Mobs",
                "", stats['raremobsindb'] or 0))
    msg.append(self._format_row("Bonus Mobs",
                "", stats['bonusmobsindb'] or 0))
    msg.append(self._format_row("Blessing Mobs",
                "", stats['blessmobsindb'] or 0))

    msg.append('')
    msg.append(self._format_row('Stats', 'Total', 'Average', '@G', '@G'))
    msg.append('@G--------------------------------------------')
    msg.append(self._format_row("XP",
                stats['xp'],
                format_float(stats['avexp'], "/kill")))
    msg.append(self._format_row("Rare XP",
                stats['rarexp'],
                format_float(stats['averarexp'], "/kill")))
    msg.append(self._format_row("Double XP",
                stats['bonusxp'],
                format_float(stats['avebonusxp'], "/kill")))
    msg.append(self._format_row("Blessing XP",
                stats['blessingxp'],
                format_float(stats['aveblessxp'], "/kill")))
    msg.append(self._format_row("Total XP",
                stats['totalxp'],
                format_float(stats['avetotalxp'], "/kill")))
    msg.append(self._format_row("Gold",
                self.api.get('utils.readablenumber')(stats['gold']),
                "%d/kill" % stats['avegold']))
    msg.append(self._format_row("TP",
                stats['tp'],
                format_float(stats['tp'] / float(stats['indb']), "/kill")))

    avetype = stats['vorpal'] / float(stats['indb'])
    msg.append(self._format_row("Vorpal",
                stats['vorpal'],
                format_float(avetype, "/kill") or ""))
    avetype = stats['assassinate'] / float(stats['indb'])
    msg.append(self._format_row("Assassinate",
                stats['assassinate'],
                format_float(avetype, "/kill") or ""))
    avetype = stats['slit'] / float(stats['indb'])
    msg.append(self._format_row("Slit",
                stats['slit'],
                format_float(avetype, "/kill") or ""))
    avetype = stats['banishment'] / float(stats['indb'])
    msg.append(self._format_row("Banishment",
                stats['banishment'],
                format_float(avetype, "/kill") or ""))
    avetype = stats['deathblow'] / float(stats['indb'])
    msg.append(self._format_row("Deathblow",
                stats['deathblow'],
                format_float(avetype, "/kill") or ""))
    avetype = stats['disintegrate'] / float(stats['indb'])
    msg.append(self._format_row("Disintegrate",
                stats['disintegrate'],
                format_float(avetype, "/kill") or ""))

    if int(count) > 0:
      lastitems = self.statdb.getlast('mobkills', int(count))

      if len(lastitems) > 0:
        msg.append('')
        msg.append("@G%3s %-18s %-3s %-3s %-3s %-3s %2s %1s %s" % (
                  "Lvl", "Mob", "TXP", "XP", "RXP", "OXP", "TP", "S", "Gold"))
        msg.append('@G----------------------------------------------------')

        for item in lastitems:
          leveld = self.api.get('aardu.convertlevel')(item['level'])
          levelstr = leveld['level']

          bonus = ''
          if int(item['bonusxp']) != 0:
            bonus = bonus + "D"
          if int(item['blessingxp']) != 0:
            bonus = bonus + "E"

          spec = ''
          if int(item['banishment']) == 1:
            spec = 'B'
          elif int(item['vorpal']) == 1:
            spec = 'V'
          elif int(item['assassinate']) == 1:
            spec = 'A'
          elif int(item['slit']) == 1:
            spec = 'S'
          elif int(item['deathblow']) == 1:
            spec = 'D'
          elif int(item['disintegrate']) == 1:
            spec = 'I'

          mtp = ''
          if int(item['tp']) == 1:
            mtp = '1'

          msg.append("%3s %-18s %3s %3s %3s %-3s %2s %1s %s" \
                     % (levelstr, item['name'][0:18], item['totalxp'],
                          item['xp'], item['rarexp'], bonus, mtp,
                          spec, item['gold']))
    return True, msg

  def questevent(self, args):
    """
    handle a quest completion
    """
    self.statdb.savequest(args)

  def whoisevent(self, args):
    """
    handle whois data
    """
    self.statdb.savewhois(args)

  def cpevent(self, args):
    """
    handle a cp
    """
    self.statdb.savecp(args)

  def gqevent(self, args):
    """
    handle a gq
    """
    self.statdb.savegq(args)

  def levelevent(self, args):
    """
    handle a level
    """
    levelinfo = copy.deepcopy(args)
    self.statdb.savelevel(levelinfo)

  def mobkillevent(self, args):
    """
    handle a mobkill
    """
    self.statdb.savemobkill(args)

  def unload(self, _=None):
    """
    handle unloading
    """
    AardwolfBasePlugin.unload(self)
    self.statdb.close()

  def api_runselect(self, select):
    """
    run a select stmt against the char db
    """
    if self.statdb:
      return self.statdb.runselect(select)

    return None

  def heroevent(self, args):
    """
    add a hero/super milestone
    """
    tlist = self.api.get('aardu.convertlevel')(self.api.get('aardu.getactuallevel')())
    if int(tlist['tier']) == 9:
      milestone = "t%s+%sr%sl%s" % (tlist['tier'], tlist['redos'],
                                    tlist['remort'], tlist['level'])
    else:
      milestone = "t%sr%sl%s" % (tlist['tier'],
                                    tlist['remort'], tlist['level'])

    if args['eventname'] == 'aard_level_remort':
      if self.statdb:
        self.statdb.setstat('remorts', self.api.get('GMCP.getv')('char.base.remorts'))
        self.statdb.setstat('tier', self.api.get('GMCP.getv')('char.base.tier'))
        alev = self.api.get('aardu.getactuallevel')()
        self.statdb.setstat('totallevels', alev)
        self.statdb.setstat('level', 1)

    if self.statdb:
      self.statdb.addmilestone(milestone)

