"""
$Id$
"""
import sqlite3
import os
import shutil

from libs import exported
exported.LOGGER.adddtype('sqlite')
exported.LOGGER.cmd_file(['sqlite'])
exported.LOGGER.cmd_console(['sqlite'])

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
  
def fixsql(tstr, like=False):
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
  

class Sqldb:
  """
  a class to manage sqlite3 databases
  """
  def __init__(self, dbname=None, dbdir=None):
    """
    initialize the class
    """
    self.dbname = dbname or "\\sqlite.sqlite"
    self.dbdir = dbdir or os.path.join(exported.BASEPATH, 'data', 'db')
    try:
      os.makedirs(self.dbdir)
    except OSError:
      pass
    self.dbfile = os.path.join(self.dbdir, self.dbname)
    self.dbconn = sqlite3.connect(self.dbfile)
    self.dbconn.row_factory = dict_factory
    # only return byte strings so is easier to send to a client or the mud
    self.dbconn.text_factory = str
    self.turnonpragmas()    
    self.conns = 0
    self.version = 1
    self.versionfuncs = {}
    self.tableids = {}
    self.tables = {}

  def postinit(self):
    """
    do post init stuff, checks and upgrades the database, creates tables
    """
    self.checkversion()
    
    for i in self.tables:
      self.checktable(i)

  def turnonpragmas(self):
    """
    turn on pragmas
    """
    pass

  def addtable(self, tablename, sql, args=None):
    """
    add a table to the database
    """
    if args == None:
      args = {}
    
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
  
  def converttoupdate(self, tablename, wherekey='', nokey={}):
    """
    create an update statement based on the columns of a table
    """
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
        cur.execute(self.tables[tablename]['createsql'])
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
    exported.msg('updating %s from version %s to %s' % (self.dbfile, 
                                            oldversion, newversion), 'sqlite')
    #self.backupdb('v%s' % oldversion)
    for i in range(oldversion + 1, newversion + 1):
      try:
        self.versionfuncs[i]()
        exported.msg('updated to version %s' % i, 'sqlite')
      except:
        exported.write_traceback('could not upgrade db: %s' % self.dbloc)
        return
    self.setversion(newversion)
    exported.msg('Done upgrading!', 'sqlite')
    
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
      exported.write_traceback('could not run sql statement : %s' % \
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
      exported.write_traceback('could not run sql statement : %s' % \
                                      selectstmt)
    cur.close()
    return result

  #def getlastrowid(self, tablename):
    #"""
    #get the last rowid of a table
    #"""
    #print 'getlastrowid'
    #colid = self.tables[tablename].keyfield
    #lastid = 0
    #try:
      #res = self.runselect("SELECT MAX('%s') AS MAX FROM %s" % \
                    #(colid, tablename))
      #print 'getlastrowid', res
      #lastid = res[0]['MAX']
    #except:
      #exported.write_traceback('could not get last row id for : %s' % \
                    #tablename)      
    #print 'lastid', lastid
    #return lastid   
  
  def getlast(self, tablename, num, where=''):
    """
    get the last x items from the table
    """
    colid = self.tables[tablename].keyfield
    execstr = ''
    if where:
      execstr = "SELECT * FROM %s WHERE %s ORDER by %s desc limit %d;" % \
                           (tablename, where, colid, num)
    else:
      execstr = "SELECT * FROM %s ORDER by %s desc limit %d;" % \
                           (tablename, colid, num)
    res = self.runselect(execstr)
    items = {}
    for row in res:
      items[row[colid]] = row
    return items
      
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

  def backupdb(self, name):
    """
    backup the database
    """
    exported.msg('backing up database', 'sqlite')
    cur = self.dbconn.cursor()
    integrity = True
    for row in cur.execute('PRAGMA integrity_check'):
      if row['integrity_check'] != 'ok':
        integrity = False
        
    if not integrity:
      exported.msg('Integrity check failed, aborting backup', 'sqlite')
      return
    self.dbconn.close()
    try:
      os.makedev(os.path.join(self.dbdir, 'backup'))
    except OSError:
      pass
    backupfile = os.path.join(self.dbdir, 'backup', self.dbname + '.' + name)
    try:
      shutil.copy(self.dbfile, backupfile)
      exported.msg('%s was backed up to %s' % (self.dbfile, backupfile), 
                                          'sqlite')
    except IOError:
      exported.msg('backup failed, could not copy file', 'sqlite')      
    self.dbconn = sqlite3.connect(self.dbfile)
    
