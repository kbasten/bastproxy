"""
$Id$

this module is a sqlite3 interface
"""
import sqlite3
import os
import shutil
import time
import zipfile
import argparse
import copy

from plugins._baseplugin import BasePlugin

NAME = 'SQL DB base class'
SNAME = 'sqldb'
PURPOSE = 'Hold the SQL DB baseclass'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

def dict_factory(cursor, row):
  """
  create a dictionary for a sql row
  """
  tdict = {}
  for idx, col in enumerate(cursor.description):
    tdict[col[0]] = row[idx]
  return tdict


class Sqldb(object):
  """
  a class to manage sqlite3 databases
  """
  def __init__(self, plugin, **kwargs):
    """
    initialize the class
    """
    self.dbconn = None
    self.plugin = plugin
    self.sname = plugin.sname
    self.name = plugin.name
    self.api = plugin.api
    if 'dbname' in kwargs:
      self.dbname = kwargs['dbname'] or "db"
    else:
      self.dbname = "db"
    self.api.get('log.adddtype')('sqlite')
    self.api.get('log.console')('sqlite')
    self.backupform = '%s_%%s.sqlite' % self.dbname
    if 'dbdir' in kwargs:
      self.dbdir = kwargs['dbdir'] or os.path.join(self.api.BASEPATH,
                                                   'data', 'db')
    else:
      self.dbdir = os.path.join(self.api.BASEPATH, 'data', 'db')

    try:
      os.makedirs(self.dbdir)
    except OSError:
      pass
    self.dbfile = os.path.join(self.dbdir, self.dbname + '.sqlite')
    self.turnonpragmas()
    self.conns = 0
    self.version = 1
    self.versionfuncs = {}
    self.tableids = {}
    self.tables = {}

  def close(self):
    """
    close the database
    """
    import inspect
    self.api.get('send.msg')('close: called by - %s' % inspect.stack()[1][3])
    try:
      self.dbconn.close()
    except:
      pass
    self.dbconn = None

  def open(self):
    """
    open the database
    """
    import inspect
    funcname = inspect.stack()[1][3]
    if funcname == '__getattribute__':
      funcname = inspect.stack()[2][3]
    self.api.get('send.msg')('open: called by - %s' % funcname)
    self.dbconn = sqlite3.connect(self.dbfile,
                detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    self.dbconn.row_factory = dict_factory
    # only return byte strings so is easier to send to a client or the mud
    self.dbconn.text_factory = str

  def __getattribute__(self, name):
    """
    override getattribute to make sure the database is open
    """
    import inspect
    badfuncs = ['open']
    attr = object.__getattribute__(self, name)
    if inspect.ismethod(attr) and name[0] != '_' and \
            not (name in badfuncs):
      if not self.dbconn:
        self.open()
    return attr

  def fixsql(self, tstr, like=False):
    """
    Fix quotes in a item that will be passed into a sql statement
    """
    if tstr:
      if like:
        return "'%" + tstr.replace("'", "''") + "%'"
      else:
        return "'" + tstr.replace("'", "''") + "'"
    else:
      return 'NULL'

  def addcmds(self):
    """
    add commands to the plugin to use the database
    """
    parser = argparse.ArgumentParser(add_help=False,
                 description='backup the database')
    parser.add_argument('name', help='the name to backup to',
                        default='', nargs='?')
    self.plugin.api.get('commands.add')('dbbackup', self.cmd_backup,
                                           parser=parser, group='DB')

    parser = argparse.ArgumentParser(add_help=False,
                 description='close the database')
    self.plugin.api.get('commands.add')('dbclose', self.cmd_close,
                                           parser=parser, group='DB')

    parser = argparse.ArgumentParser(add_help=False,
                 description='vacuum the database')
    self.plugin.api.get('commands.add')('dbvac', self.cmd_vac,
                                           parser=parser, group='DB')

    parser = argparse.ArgumentParser(add_help=False,
                 description='run a sql statement against the database')
    parser.add_argument('stmt', help='the sql statement', default='', nargs='?')
    self.plugin.api.get('commands.add')('runselect', self.cmd_runselect,
                                           parser=parser, group='DB')

  def cmd_runselect(self, args=None):
    """
    vacuum the database
    """
    msg = []
    if args:
      print args
      sqlstmt = args['stmt']
      if sqlstmt:
        pass
      # check the validity of the sql statement
    else:
      msg.append('Please enter a select statement')
    return True, msg

  def cmd_vac(self, _=None):
    """
    vacuum the database
    """
    msg = []
    self.dbconn.execute('VACUUM')
    msg.append('Database Vacuumed')
    return True, msg

  def cmd_close(self, _):
    """
    backup the database
    """
    msg = []
    self.close()
    msg.append('Database %s was closed' % (self.dbname))

    return True, msg

  def cmd_backup(self, args):
    """
    backup the database
    """
    msg = []
    if args['name']:
      name = args['name']
    else:
      name = time.strftime('%a-%b-%d-%Y-%H-%M', time.localtime())

    newname = self.backupform % name + '.zip'
    if self.backupdb(name):
      msg.append('backed up %s with name %s' % (self.dbname,
                    newname))
    else:
      msg.append('could not back up %s with name %s' % (self.dbname,
                    newname))

    return True, msg

  def postinit(self):
    """
    do post init stuff, checks and upgrades the database, creates tables
    """
    self.addcmds()
    self.checkversion()

    for i in self.tables:
      self.checktable(i)

  def turnonpragmas(self):
    """
    turn on pragmas
    """
    pass

  def addtable(self, tablename, sql, **kwargs):
    """
    add a table to the database

    keyword args:
     precreate
     postcreate
     keyfield

    """
    if not kwargs:
      args = {}
    else:
      args = copy.copy(kwargs)


    if not ('precreate' in args):
      args['precreate'] = None
    if not ('postcreate' in args):
      args['postcreate'] = None
    if not ('keyfield' in args):
      args['keyfield'] = None

    args['createsql'] = sql

    self.tables[tablename] = args
    col, colbykeys = self.getcolumnsfromsql(tablename)
    self.tables[tablename]['columns'] = col
    self.tables[tablename]['columnsbykeys'] = colbykeys

  def getcolumnsfromsql(self, tablename):
    """
    build a list of columns from the create statement for the table
    """
    columns = []
    columnsbykeys = {}
    if self.tables[tablename]:
      tlist = self.tables[tablename]['createsql'].split('\n')
      for i in tlist:
        i = i.strip()
        if i and i[0:2] != '--':
          if not ('CREATE' in i) and not (')' in i):
            ilist = i.split(' ')
            columns.append(ilist[0])
            columnsbykeys[ilist[0]] = True

    return columns, columnsbykeys

  def converttoinsert(self, tablename, keynull=False, replace=False):
    """
    create an insert statement based on the columns of a table
    """
    execstr = ''
    if self.tables[tablename]:
      cols = self.tables[tablename]['columns']
      tlist = [':%s' % i for i in cols]
      colstring = ', '.join(tlist)
      if replace:
        execstr = "INSERT OR REPLACE INTO %s VALUES (%s)" % \
                          (tablename, colstring)
      else:
        execstr = "INSERT INTO %s VALUES (%s)" % (tablename, colstring)
      if keynull and self.tables[tablename]['keyfield']:
        execstr = execstr.replace(":%s" % self.tables[tablename]['keyfield'],
                                                    'NULL')
    return execstr


  def checkcolumnexists(self, table, columnname):
    """
    check if a column exists
    """
    if table in self.tables:
      if columnname in self.tables[table]['columnsbykeys']:
        return True

    return False

  def converttoupdate(self, tablename, wherekey='', nokey=None):
    """
    create an update statement based on the columns of a table
    """
    if nokey == None:
      nokey = {}
    execstr = ''
    if self.tables[tablename]:
      cols = self.tables[tablename]['columns']
      sqlstr = []
      for i in cols:
        if i == wherekey or (nokey and i in nokey):
          pass
        else:
          sqlstr.append(i + ' = :' + i)
      colstring = ','.join(sqlstr)
      execstr = "UPDATE %s SET %s WHERE %s = :%s;" % (tablename, colstring,
                                          wherekey, wherekey)
    return execstr

  def getversion(self):
    """
    get the version of the database
    """
    version = 1
    cur = self.dbconn.cursor()
    cur.execute('PRAGMA user_version;')
    ret = cur.fetchone()
    version = ret['user_version']
    cur.close()
    return version

  def checktable(self, tablename):
    """
    check to see if a table exists, if not create it
    """
    if self.tables[tablename]:
      if not self.checktableexists(tablename):
        if self.tables[tablename]['precreate']:
          self.tables[tablename]['precreate']()
        cur = self.dbconn.cursor()
        cur.executescript(self.tables[tablename]['createsql'])
        self.dbconn.commit()
        cur.close()
        if self.tables[tablename]['postcreate']:
          self.tables[tablename]['postcreate']()
    return True

  def checktableexists(self, tablename):
    """
    query the database master table to see if a table exists
    """
    retv = False
    cur = self.dbconn.cursor()
    for row in cur.execute(
         'SELECT * FROM sqlite_master WHERE name = "%s" AND type = "table";'
                        % tablename):
      if row['name'] == tablename:
        retv = True
    cur.close()
    return retv

  def checkversion(self):
    """
    checks the version of the database, upgrades if neccessary
    """
    dbversion = self.getversion()
    if dbversion == 0:
      self.setversion(self.version)
    elif self.version > dbversion:
      self.updateversion(dbversion, self.version)

  def setversion(self, version):
    """
    set the version of the database
    """
    cur = self.dbconn.cursor()
    cur.execute('PRAGMA user_version=%s;' % version)
    self.dbconn.commit()
    cur.close()

  def updateversion(self, oldversion, newversion):
    """
    update a database from oldversion to newversion
    """
    self.api.get('send.msg')('updating %s from version %s to %s' % (
                                  self.dbfile, oldversion, newversion))
    self.backupdb(oldversion)
    for i in range(oldversion + 1, newversion + 1):
      try:
        self.versionfuncs[i]()
        self.api.get('send.msg')('updated to version %s' % i)
      except:
        self.api.get('send.traceback')(
                      'could not upgrade db: %s in plugin: %s' % (self.dbname,
                                                          self.plugin.sname))
        return
    self.setversion(newversion)
    self.api.get('send.msg')('Done upgrading!')

  def runselect(self, selectstmt):
    """
    run a select statement against the database, returns a list
    """
    result = []
    cur = self.dbconn.cursor()
    try:
      for row in cur.execute(selectstmt):
        result.append(row)
    except:
      self.api.get('send.traceback')('could not run sql statement : %s' % \
                            selectstmt)
    cur.close()
    return result

  def runselectbykeyword(self, selectstmt, keyword):
    """
    run a select statement against the database, return a dictionary
    where the keys are the keyword specified
    """
    result = {}
    cur = self.dbconn.cursor()
    try:
      for row in cur.execute(selectstmt):
        result[row[keyword]] = row
    except:
      self.api.get('send.traceback')('could not run sql statement : %s' % \
                                      selectstmt)
    cur.close()
    return result

  def getlast(self, ttable, num, where=''):
    """
    get the last num items from a table
    """
    results = {}
    if not (ttable in self.tables):
      self.api.get('send.msg')('table %s does not exist in getlast' % ttable)
      return

    colid = self.tables[ttable]['keyfield']
    tstring = ''
    if where:
      tstring = "SELECT * FROM %s WHERE %s ORDER by %s desc limit %d" % \
                        (ttable, where, colid, num)
    else:
      tstring = "SELECT * FROM %s ORDER by %s desc limit %d" % \
                        (ttable, colid, num)

    results = self.runselect(tstring)

    return results

  def getlastrowid(self, ttable):
    """
    return the id of the last row in a table
    """
    last = -1
    colid = self.tables[ttable]['keyfield']
    rows = self.runselect("SELECT MAX(%s) AS MAX FROM %s" % (colid, ttable))
    if len(rows) > 0:
      last = rows[0]['MAX']

    return last

  def backupdb(self, postname):
    """
    backup the database
    """
    success = False
    #self.cmd_vac()
    self.api.get('send.msg')('backing up database %s' % self.dbname)
    integrity = True
    cur = self.dbconn.cursor()
    cur.execute('PRAGMA integrity_check')
    ret = cur.fetchone()
    if ret['integrity_check'] != 'ok':
      integrity = False

    if not integrity:
      self.api.get('send.msg')('Integrity check failed, aborting backup')
      return
    self.close()
    try:
      os.makedirs(os.path.join(self.dbdir, 'archive'))
    except OSError:
      pass

    backupzipfile = os.path.join(self.dbdir, 'archive',
                            self.backupform % postname + '.zip')
    backupfile = os.path.join(self.dbdir, 'archive',
                                self.backupform % postname)

    try:
      shutil.copy(self.dbfile, backupfile)
    except IOError:
      self.api.get('send.msg')('backup failed, could not copy file')
      return success

    try:
      with zipfile.ZipFile(backupzipfile, 'w', zipfile.ZIP_DEFLATED) as myzip:
        myzip.write(backupfile)
      os.remove(backupfile)
      success = True
      self.api.get('send.msg')('%s was backed up to %s' % (self.dbfile,
                                                           backupzipfile))
    except IOError:
      self.api.get('send.msg')('could not zip backupfile')
      return success

    return success

class Plugin(BasePlugin):
  """
  a plugin to handle the base sqldb
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.reloaddependents = True

    self.api.get('api.add')('baseclass', self.api_baseclass)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

  def api_baseclass(self):
    """
    return the sql baseclass
    """
    return Sqldb
