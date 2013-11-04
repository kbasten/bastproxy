"""
$Id$

This module will do both debugging and logging, didn't know what
else to name it
"""
from __future__ import print_function
import sys
import time
import os
import shutil
import zipfile

import libs.color as color
from libs.persistentdict import PersistentDict
from libs import utils
from plugins._baseplugin import BasePlugin

NAME = 'Logging'
SNAME = 'log'
PURPOSE = 'Handle logging to file and console, errors'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 5

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a class to manage internal commands
  """
  def __init__(self, *args, **kwargs):
    """
    init the class
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    #print('log api.api', self.api.api)
    #print('log basepath', self.api.BASEPATH)
    self.savedir = os.path.join(self.api.BASEPATH, 'data',
                                          'plugins', self.sname)
    self.logdir = os.path.join(self.api.BASEPATH, 'data', 'logs')
    #print('logdir', self.logdir)
    try:
      os.makedirs(self.savedir)
    except OSError:
      pass
    self.dtypes = {}
    self.sendtoclient = PersistentDict(
                          os.path.join(self.savedir, 'sendtoclient.txt'),
                          'c')
    self.sendtoconsole = PersistentDict(
                          os.path.join(self.savedir, 'sendtoconsole.txt'),
                          'c')
    self.sendtofile = PersistentDict(
                          os.path.join(self.savedir, 'sendtofile.txt'),
                          'c')
    self.openlogs = {}
    self.currentlogs = {}
    self.colors = {}

    #self.sendtofile['default'] = {
                                #'logdir':os.path.join(self.logdir, 'default'),
                                #'file':'%a-%b-%d-%Y.log', 'timestamp':True
                                  #}

    self.colors['error'] = '@x136'

    self.api.get('api.add')('msg', self.api_msg)
    self.api.get('api.add')('adddtype', self.api_adddtype)
    self.api.get('api.add')('console', self.api_toggletoconsole)
    self.api.get('api.add')('file', self.api_toggletofile)
    self.api.get('api.add')('client', self.api_toggletoclient)

    self.api.get('log.adddtype')('default')
    self.api.get('log.adddtype')('frommud')
    self.api.get('log.adddtype')('startup')
    self.api.get('log.adddtype')('error')

    self.api.get('log.client')('error')
    self.api.get('log.console')('error')
    self.api.get('log.console')('default')
    self.api.get('log.console')('startup')

    self.api.get('log.file')('default')


  # add a datatype to the log
  def api_adddtype(self, datatype):
    """  add a datatype
    @Ydatatype@w  = the datatype to add

    this function returns no values"""
    if not (datatype in self.dtypes):
      self.dtypes[datatype] = True
      self.sendtoclient[datatype] = False
      self.sendtoconsole[datatype] = False

  def process_msg(self, msg, dtype, priority='primary'):
    """
    process a message
    """
    tstring = '%s - %-10s : ' % (
                time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()),
                dtype)
    if dtype in self.colors:
      tstring = color.convertcolors(self.colors[dtype] + tstring)
    tmsg = [tstring]
    tmsg.append(msg)

    timestampmsg = ''.join(tmsg)
    nontimestamp = msg

    if dtype in self.sendtoclient and self.sendtoclient[dtype]:
      self.api.get('output.client')(timestampmsg)

    if dtype in self.sendtoconsole and self.sendtoconsole[dtype]:
      print(timestampmsg, file=sys.stderr)

    if priority == 'primary':
      if dtype in self.sendtofile and self.sendtofile[dtype]['file']:
        self.logtofile(color.strip_ansi(nontimestamp), dtype)

      if 'default' in self.sendtofile:
        self.logtofile(timestampmsg, 'default')

  # process a message, use output.msg instead for the api
  def api_msg(self, args, dtypedict={'primary':'default'}):
    """  send a message
    @Ymsg@w        = This message to send
    @Ydatatype@w   = the type to toggle

    this function returns no values"""
    dtype = dtypedict['primary']
    if 'dtype' in args:
      dtype = args['dtype']

    self.process_msg(args['msg'], dtype)

    if 'secondary' in dtypedict \
        and dtypedict['secondary'] != 'None' \
        and dtypedict['secondary'] != 'default':
      self.process_msg(args['msg'], dtypedict['secondary'], priority='secondary')

  # archive a log fle
  def archivelog(self, dtype):
    """
    archive the previous log
    """
    tfile = os.path.split(self.currentlogs[dtype])[-1]
    self.openlogs[self.currentlogs[dtype]].close()
    curfile = self.currentlogs[dtype]
    backupfile = os.path.join(self.sendtofile[dtype]['logdir'],
                          tfile)
    backupzipfile = os.path.join(self.sendtofile[dtype]['logdir'], 'archive',
                          tfile + '.zip')
    with zipfile.ZipFile(backupzipfile, 'w', zipfile.ZIP_DEFLATED) as myzip:
      myzip.write(backupfile, arcname=self.currentlogs[dtype])
    os.remove(backupfile)
    del self.openlogs[self.currentlogs[dtype]]

  # log something to a file
  def logtofile(self, msg, dtype):
    """
    send a message to a log file
    """
    #print('logging', dtype)
    tfile = os.path.join(self.sendtofile[dtype]['logdir'],
                  time.strftime(self.sendtofile[dtype]['file'],
                  time.localtime()))
    if not os.path.exists(self.sendtofile[dtype]['logdir']):
      os.makedirs(os.path.join(self.sendtofile[dtype]['logdir'], 'archive'))
    if (not (dtype in self.currentlogs)) or \
       (dtype in self.currentlogs and not self.currentlogs[dtype]):
      self.currentlogs[dtype] = tfile
    elif tfile != self.currentlogs[dtype]:
      self.archivelog(dtype)
      self.currentlogs[dtype] = tfile
    if not (self.currentlogs[dtype] in self.openlogs):
      self.openlogs[self.currentlogs[dtype]] = \
                      open(self.currentlogs[dtype], 'a')
    #print('logging to %s' % tfile)
    if self.sendtofile[dtype]['timestamp']:
      tstring = '%s : ' % \
            (time.strftime(self.api.timestring, time.localtime()))
      msg = tstring + msg
    self.openlogs[self.currentlogs[dtype]].write(color.strip_ansi(msg) + '\n')
    self.openlogs[self.currentlogs[dtype]].flush()

  # toggle logging a datatype to the clients
  def api_toggletoclient(self, datatype, flag=True):
    """  toggle a data type to show to clients
    @Ydatatype@w  = the type to toggle, can be multiple (list)
    @Yflag@w      = True to send to clients, false otherwise (default: True)

    this function returns no values"""
    if datatype in self.sendtoclient and datatype != 'frommud':
      self.sendtoclient[datatype] = flag

    self.api.get('output.msg')('setting %s to log to client' % \
                      datatype)

    self.sendtoclient.sync()

  # toggle logging datatypes to the clients
  def cmd_client(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to clients
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle
    if no arguments, list types that are sent to client"""
    tmsg = []
    if len(args) > 0:
      for i in args:
        if i in self.sendtoclient and i != 'frommud':
          self.sendtoclient[i] = not self.sendtoclient[i]
          if self.sendtoclient[i]:
            tmsg.append('sending %s to client' % i)
          else:
            tmsg.append('no longer sending %s to client' % i)

        elif i != 'frommud':
          tmsg.append('Type %s does not exist' % i)
      self.sendtoclient.sync()
      return True, tmsg
    else:
      tmsg.append('Current types going to client')
      for i in self.sendtoclient:
        if self.sendtoclient[i]:
          tmsg.append(i)
      return True, tmsg

  # toggle logging a datatype to the console
  def api_toggletoconsole(self, datatype, flag=True):
    """  toggle a data type to show to console
    @Ydatatype@w  = the type to toggle
    @Yflag@w      = True to send to console, false otherwise (default: True)

    this function returns no values"""
    if datatype in self.sendtoconsole and datatype != 'frommud':
      self.sendtoconsole[datatype] = flag

    self.api.get('output.msg')('setting %s to log to console' % \
                      datatype, self.sname)

    self.sendtoconsole.sync()

  # toggle logging datatypes to the console
  def cmd_console(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show in the console
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple (list)
    if no arguments, list types that are sent to console"""
    tmsg = []
    if len(args) > 0:
      for i in args:
        if i in self.sendtoconsole and i != 'frommud':
          self.sendtoconsole[i] = not self.sendtoconsole[i]
          if self.sendtoconsole[i]:
            tmsg.append('sending %s to console' % i)
          else:
            tmsg.append('no longer sending %s to console' % i)

        elif i != 'frommud':
          tmsg.append('Type %s does not exist' % i)
      self.sendtoconsole.sync()
      return True, tmsg
    else:
      tmsg.append('Current types going to console')
      for i in self.sendtoconsole:
        if self.sendtoconsole[i]:
          tmsg.append(i)
      return True, tmsg

  # toggle logging a datatype to a file
  def api_toggletofile(self, datatype, flag=True, timestamp=True):
    """  toggle a data type to show to file
    @Ydatatype@w  = the type to toggle
    @Yflag@w      = True to send to file, false otherwise (default: True)

    this function returns no values"""
    if datatype in self.sendtofile:
      del self.sendtofile[datatype]
    else:
      tfile = '%a-%b-%d-%Y.log'

      self.sendtofile[datatype] = {'file':tfile,
                                'logdir':os.path.join(self.logdir, datatype),
                                'timestamp':timestamp}
      self.api.get('output.msg')('setting %s to log to %s' % \
                      (datatype, self.sendtofile[datatype]['file']), self.sname)
      self.sendtofile.sync()

  # toggle logging datatypes to a file
  def cmd_file(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to file
  @CUsage@w: show @Y<datatype>@w @Y<timestamp>@w
    @Ydatatype@w  = the type to toggle, can be multiple (list)
    @Ytimestamp@W = (optional) if True, then add timestamps before each line
           if False, do not add timestamps
           the default is True
    the file will be located in the data/logs/<dtype> directory
    the filename for the log will be <date>.log
           Example: Tue-Feb-26-2013.log
    if no arguments, list types that are sent to file"""
    tmsg = []
    timestamp = True
    if len(args) >= 1:
      dtype = args[0]
      try:
        timestamp = utils.verify(args[1], bool)
      except IndexError:
        pass

      if dtype in self.sendtofile:
        del self.sendtofile[dtype]
        tmsg.append('removing %s from logging' % dtype)
      else:
        tfile = '%a-%b-%d-%Y.log'

        self.sendtofile[dtype] = {'file':tfile,
                                  'logdir':os.path.join(self.logdir, dtype),
                                  'timestamp':timestamp}
        tmsg.append('setting %s to log to %s' % \
                        (dtype, self.sendtofile[dtype]['file']))
        self.sendtofile.sync()
      return True, tmsg
    else:
      tmsg.append('Current types going to file')
      for i in self.sendtofile:
        if self.sendtofile[i]:
          tmsg.append('%s - %s - %s' % \
             (i, self.sendtofile[i]['file'], self.sendtofile[i]['timestamp']))
      return True, tmsg

  # archive a datatype
  def cmd_archive(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  archive a log file
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple (list)
    if no arguments, list types that are sent to client"""
    tmsg = []
    if len(args) > 0:
      for i in args:
        if i in self.dtypes:
          self.archivelog(i)
        else:
          tmsg.append('%s does not exist' % i)
      return True, tmsg
    else:
      tmsg = self.cmd_types()
      return True, tmsg

  # show all types
  def cmd_types(self, _=None):
    """@G%(name)s@w - @B%(cmdname)s@w
  show data types
  @CUsage@w: types"""
    tmsg = []
    tmsg.append('Data Types')
    tmsg.append('-' *  30)
    for i in self.dtypes:
      tmsg.append(i)
    return True, tmsg

  def logmud(self, args):
    """
    log all data from the mud
    """
    if 'frommud' in self.sendtofile and self.sendtofile['frommud']['file']:
      if args['eventname'] == 'from_mud_event':
        data = args['nocolordata']
      elif args['eventname'] == 'to_mud_event':
        data = 'tomud: ' + args['data'].strip()
      self.logtofile(data, 'frommud')
    return args


  def load(self):
    """
    load external stuff
    """
    BasePlugin.load(self)
    #print('log api before adding', self.api.api)
    self.api.get('managers.add')('log', self)

    #print('log api after adding', self.api.api)
    self.api.get('events.register')('from_mud_event', self.logmud)
    self.api.get('events.register')('to_mud_event', self.logmud)

    self.api.get('commands.add')('client', self.cmd_client,
                        lname='Logger',
                         shelp='Send message of a type to clients')
    self.api.get('commands.add')('file', self.cmd_file,
                        lname='Logger',
                        shelp='Send message of a type to a file')
    self.api.get('commands.add')('console', self.cmd_console,
                        lname='Logger',
                        shelp='Send message of a type to console')
    self.api.get('commands.add')('types', self.cmd_types,
                        lname='Logger',
                        shelp='Show data types')

    #print('log loaded')

