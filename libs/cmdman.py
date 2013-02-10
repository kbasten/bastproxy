"""
$Id$
"""
from libs import exported
import shlex

class CmdMgr:
  def __init__(self):
    self.cmds = {}
    self.addCmd('help', 'Help', 'list', self.listCmds)
    self.addCmd('help', 'Help', 'default', self.listCmds)
    exported.registerevent('from_client_event', self.chkCmd)

  def chkCmd(self, data):
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
        targs.insert(0, scmd)
        targs.insert(0, sname)
        if 'help' in targs:
          hindex = targs.index('help')
          try:
            del targs[targs.index(None)]
          except ValueError:
            pass
          try:
            del targs[targs.index('help')]            
          except ValueError:
            pass
          self.listCmds(targs)
        elif sname:
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
              exported.sendtouser("@R%s.%s@W is not a command" % (sname, scmd))
            else:
              retval = self.cmds[sname][stcmd]['func'](targs)
              if not retval:
                self.listCmds([sname, scmd])              
          else:  
            exported.sendtouser("@R%s.%s@W is not a command" % (sname, scmd))
        else:
          try:
            del targs[targs.index(None)]
          except ValueError:
            pass
          try:
            del targs[targs.index('help')]            
          except ValueError:
            pass
          print 'targs before calling help 2', targs
          self.listCmds(targs)
        return {'fromdata':''}
    else:
      return data
    
  def addCmd(self, sname, lname, cmd, tfunction, shelp="", lhelp=""):
    if not (sname in self.cmds):
      self.cmds[sname] = {}
    self.cmds[sname][cmd] = {'func':tfunction, 'lname':lname, 'lhelp':lhelp, 'shelp':shelp}
    
  def setDefault(self, sname, cmd):
    if sname in self.cmds and cmd in self.cmds[sname]:
      self.cmds[sname]['default'] = self.cmds[sname][cmd]
    
  def listCmds(self, args):
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
            thelp = self.cmds[sname][cmd]['func'].__doc__ % {'name':self.cmds[sname][cmd]['lname'], 'cmdname':cmd}
          elif self.cmds[sname][cmd]['shelp']:
            thelp = self.cmds[sname][cmd]['shelp']
          exported.sendtouser(thelp)
        else:
          exported.sendtouser('Commands in category: %s' % sname)
          for i in self.cmds[sname]:
            if i != 'default':
              exported.sendtouser('  %-10s : %s' % (i, self.cmds[sname][i]['shelp']))
      else:
        exported.sendtouser('There is no category named %s' % sname)
    else:
      exported.sendtouser('Command Categories:')
      for i in self.cmds:
        exported.sendtouser('  %s' % i)
            