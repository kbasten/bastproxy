"""
$Id$

This will do both debugging and logging, didn't know what
else to name it
"""
from __future__ import print_function
import sys
import time
import os
import shutil

from libs import exported
from libs.color import strip_ansi
from libs.persistentdict import PersistentDict
from libs import utils

class Logger:
  """
  a class to manage logging and its related activities
  """
  def __init__(self):
    """
    init the class
    """
    self.sname = 'log'
    self.savedir = os.path.join(exported.BASEPATH, 'data', 
                                          'plugins', self.sname)
    self.logdir = os.path.join(exported.BASEPATH, 'data', 'logs')
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
    self.adddtype('default')
    self.adddtype('frommud')
    self.sendtoconsole['default'] = True
    self.sendtofile['default'] = {
                                'logdir':os.path.join(self.logdir, 'default'), 
                                'file':'%a-%b-%d-%Y.log', 'timestamp':True
                                  }
    self.adddtype('error')
    self.sendtoconsole['error'] = True
    self.sendtoclient['error'] = True
    self.colors['error'] = '@x136'
    self.sendtoclient.sync()
    self.sendtoconsole.sync()
    self.sendtofile.sync()
  
  def adddtype(self, dtype):
    """
    add a datatype
    """
    if not (dtype in self.dtypes):
      self.dtypes[dtype] = True
      self.sendtoclient[dtype] = False
      self.sendtoconsole[dtype] = False    
    
  def msg(self, args, dtype='default'):
    """
    process a message
    """
    if 'dtype' in args:
      dtype = args['dtype']
      
    tstring = '%s - %-10s : ' % (
                time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()), 
                dtype)
    if dtype in self.colors:
      tstring = exported.color.convertcolors(self.colors[dtype] + tstring)
    tmsg = [tstring]
    tmsg.append(args['msg'])
    
    timestampmsg = ''.join(tmsg)
    nontimestamp = args['msg']
    
    if dtype in self.sendtoclient and self.sendtoclient[dtype]:
      exported.sendtoclient(timestampmsg)
      
    if dtype in self.sendtofile and self.sendtofile[dtype]['file']:
      self.logtofile(exported.color.strip_ansi(nontimestamp), dtype)
        
    
    if dtype in self.sendtoconsole and self.sendtoconsole[dtype]:
      print(timestampmsg, file=sys.stderr)
      
    self.logtofile(timestampmsg, 'default')
    
  def logtofile(self, msg, dtype):
    """
    send a message to a log file
    """
    #print('logging', dtype)
    tfile = os.path.join(self.sendtofile[dtype]['logdir'], 
                  time.strftime(self.sendtofile[dtype]['file'], 
                  time.localtime()))
    if not os.path.exists(self.sendtofile[dtype]['logdir']):
      os.makedirs(self.sendtofile[dtype]['logdir'])
      os.makedirs(os.path.join(self.sendtofile[dtype]['logdir'], 'archive'))
    if (not (dtype in self.currentlogs)) or \
       (dtype in self.currentlogs and not self.currentlogs[dtype]):
      self.currentlogs[dtype] = tfile
    elif tfile != self.currentlogs[dtype]:
      self.openlogs[self.currentlogs[dtype]].close()
      shutil.move(self.currentlogs[dtype], 
                  os.path.join(self.sendtofile[dtype]['logdir'], 'archive'))
      del self.openlogs[self.currentlogs[dtype]]
      self.currentlogs[dtype] = tfile      
    
    if not (self.currentlogs[dtype] in self.openlogs):
      self.openlogs[self.currentlogs[dtype]] = \
                      open(self.currentlogs[dtype], 'a')
    #print('logging to %s' % tfile)
    if self.sendtofile[dtype]['timestamp']:
      tstring = '%s : ' % \
            (time.strftime('%a %b %d %Y %H:%M:%S', time.localtime()))
      msg = tstring + msg
    self.openlogs[self.currentlogs[dtype]].write(strip_ansi(msg) + '\n')
    self.openlogs[self.currentlogs[dtype]].flush()
   
  def cmd_client(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to clients
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple
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

  def cmd_console(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show in the console
  @CUsage@w: show @Y<datatype>@w
    @Ydatatype@w  = the type to toggle, can be multiple
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

  def cmd_file(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  toggle a message type to show to file
  @CUsage@w: show @Y<datatype>@w @Y<timestamp>@w
    @Ydatatype@w  = the type to toggle, can be multiple
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
   
  def cmd_types(self, args):
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
      self.logtofile(args['nocolordata'], 'frommud')
    return args
   
  def load(self):
    """
    load external stuff
    """
    exported.cmd.add('log', 'client', 
                        {'lname':'Logger', 'func':self.cmd_client, 
                         'shelp':'Send message of a type to clients'})
    exported.cmd.add('log', 'file', 
                        {'lname':'Logger', 'func':self.cmd_file, 
                        'shelp':'Send message of a type to a file'})
    exported.cmd.add('log', 'console', 
                        {'lname':'Logger', 'func':self.cmd_console, 
                        'shelp':'Send message of a type to console'})
    exported.cmd.add('log', 'types', 
                        {'lname':'Logger', 'func':self.cmd_types, 
                        'shelp':'Show data types'})
    exported.event.register('from_mud_event', self.logmud)
  
  