"""
$Id$
"""
from libs import exported
import shlex

class CmdMgr:
  """
  a class to manage internal commands
  """
  def __init__(self):
    """
    init the class
    """
    self.cmds = {}
    self.nomultiplecmds = {}
    self.regexlookup = {}
    self.addcmd('help', 'list', {'lname':'Help', 'func':self.listcmds})
    self.addcmd('help', 'default', {'lname':'Help', 'func':self.listcmds})
    
    #exported.add(self.addwatch, 'cmdwatch', 'add')    
    #exported.add(self.removewatch, 'cmdwatch', 'remove')
    
    exported.add(self.addcmd, 'cmd', 'add')    
    exported.add(self.removecmd, 'cmd', 'remove')
    exported.add(self.setdefault, 'cmd', 'default')
    exported.add(self.resetcmds, 'cmd', 'reset')
    
  def formatretmsg(self, msg, sname, stcmd):
    """
    format a return message
    """
    msg.insert(0, '')
    msg.insert(1, '#bp.%s.%s' % (sname, stcmd))
    msg.insert(2, '@G' + '-' * 60 + '@w')
    msg.append('@G' + '-' * 60 + '@w')                  
    msg.append('')
    return msg

  def runcmd(self, tfunction, targs, sname, stcmd, scmd):
    """
    run a command
    """
    retvalue = tfunction(targs)
      
    if isinstance(retvalue, tuple):
      retval = retvalue[0]
      msg = retvalue[1]
    else:
      retval = retvalue
      msg = []
      
    if retval:
      if msg and isinstance(msg, list):
        exported.sendtoclient('\n'.join(self.formatretmsg(msg, sname, stcmd)))
        return True
    else:
      _, msg = self.listcmds([sname, scmd])    
      exported.sendtoclient('\n'.join(self.formatretmsg(
                                                  msg, 'plugins', 'help'))) 
    return retval

  def chkcmd(self, data):
    """
    check a line from a client for a command
    """
    tdat = data['fromdata']
    if tdat[0:3] == '#bp':
      cmd = tdat.split(" ")[0]
      args = tdat.replace(cmd, "").strip()
      targs = []
      targs = shlex.split(args)
      tst = cmd.split('.')
      try:
        sname = tst[1].strip()
      except IndexError:
        sname = None
      try:
        scmd = tst[2].strip()        
      except IndexError:
        scmd = None
      if scmd:
        targs.insert(0, scmd)
      elif len(targs) > 0:
        scmd = targs[0]
      targs.insert(0, sname)
      if 'help' in targs:
        try:
          del targs[targs.index(None)]
        except ValueError:
          pass
        try:
          del targs[targs.index('help')]            
        except ValueError:
          pass
        _, msg = self.listcmds(targs)    
        exported.sendtoclient('\n'.join(self.formatretmsg(
                                              msg, 'plugins', 'help'))) 
      elif sname and scmd:
        if sname in self.cmds:
          stcmd = None
          if scmd in self.cmds[sname]:
            stcmd = scmd
          elif not scmd and 'default' in self.cmds[sname]:
            stcmd = 'default'
          try:
            del targs[targs.index(scmd)]
          except ValueError:
            pass
          try:
            del targs[targs.index(sname)]            
          except ValueError:
            pass
          if not stcmd:
            exported.sendtoclient("@R%s.%s@W is not a command" % \
                                                        (sname, scmd))
          else:
            self.runcmd(self.cmds[sname][stcmd]['func'], targs, 
                                                  sname, stcmd, scmd)
        else:  
          exported.sendtoclient("@R%s.%s@W is not a command." % \
                                                  (sname, scmd))
      else:
        try:
          del targs[targs.index(None)]
        except ValueError:
          pass
        try:
          del targs[targs.index('help')]            
        except ValueError:
          pass
        _, msg = self.listcmds(targs)    
        exported.sendtoclient('\n'.join(self.formatretmsg(
                                                msg, 'plugins', 'help'))) 
        
      return {'fromdata':''}
    else:
      if tdat in self.nomultiplecmds:
        return {'fromdata':''}

      return data
    
  def addcmd(self, sname, cmdname, args):
    """
    add a command
    """
    #lname, cmd, tfunction, shelp="", lhelp=""
    #{'func':tfunction, 'lname':lname, 'lhelp':lhelp, 'shelp':shelp}
    if not ('lname' in args):
      exported.msg('cmd %s.%s has no long name, not adding' % \
                                                (sname, cmdname), 'cmd')
      return    
    if not ('func' in args):
      exported.msg('cmd %s.%s has no function, not adding' % \
                                                (sname, cmdname), 'cmd')
      return     
    if not (sname in self.cmds):
      self.cmds[sname] = {}
    self.cmds[sname][cmdname] = args
    
  def removecmd(self, sname, cmdname):
    """
    remove a command
    """
    if sname in self.cmds and cmdname in self.cmds[sname]:
      del self.cmds[sname][cmdname]
    else:
      exported.msg('removecmd: cmd %s.%s does not exist' % \
                                                (sname, cmdname), 'cmd') 
      
  def setdefault(self, sname, cmd):
    """
    set the default command for a plugin or commandset
    """
    if sname in self.cmds and cmd in self.cmds[sname]:
      self.cmds[sname]['default'] = self.cmds[sname][cmd]

  def resetcmds(self, sname):
    """
    reset the commands for a plugin
    """
    if sname in self.cmds:
      del self.cmds[sname]
    else:
      exported.msg('resetcmds: cmd %s does not exist' % sname, 'cmd')      
    
  def listcmds(self, args):
    """
    list commands
    """
    tmsg = []
    if len(args) > 0 and args[0]:
      sname = args[0]
      try:
        cmd = args[1]
      except IndexError:
        cmd = None
      if sname in self.cmds:
        if cmd and cmd in self.cmds[sname]:
          thelp = 'No help for this command'
          if self.cmds[sname][cmd]['func'].__doc__:
            thelp = self.cmds[sname][cmd]['func'].__doc__ % \
                      {'name':self.cmds[sname][cmd]['lname'], 'cmdname':cmd}
          elif self.cmds[sname][cmd]['shelp']:
            thelp = self.cmds[sname][cmd]['shelp']
          tmsg.append(thelp)
        else:
          tmsg.append('Commands in category: %s' % sname)
          for i in self.cmds[sname]:
            if i != 'default':
              tmsg.append('  %-10s : %s' % (i, self.cmds[sname][i]['shelp']))
      else:
        tmsg.append('There is no category named %s' % sname)
    else:
      tmsg.append('Command Categories:')
      for i in self.cmds:
        tmsg.append('  %s' % i)
    return True, tmsg
      
  def load(self):
    """
    load external stuff
    """
    exported.event.register('from_client_event', self.chkcmd, 1)
    exported.LOGGER.adddtype('cmds')
    exported.LOGGER.cmd_console(['cmds'])
    
    
    