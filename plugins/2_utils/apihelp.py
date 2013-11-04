"""
$Id$

This plugin will show information about connections to the proxy
#TODO: add overload vs regular info and file locations
"""
import inspect
from libs import utils
from plugins._baseplugin import BasePlugin

#these 5 are required
NAME = 'API help'
SNAME = 'apihelp'
PURPOSE = 'show info about the api'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to show connection information
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('commands.add')('list', self.cmd_list,
                                 shelp='list functions in the api')
    self.api.get('commands.add')('detail', self.cmd_detail,
                                 shelp='detail a function in the api')


  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    detail a function in the api
      @CUsage@w: detail @Y<api>@w
      @Yapi@w = (optional) the api to detail
    """
    tmsg = []
    apia = None
    apio = None
    apiapath = None
    apiopath = None
    if len(args) > 0:
      apiname = args[0]
      name, cmdname = apiname.split('.')
      tdict = {'name':name, 'cmdname':cmdname, 'apiname':apiname}
      try:
        apia = self.api.get(apiname, True)
      except AttributeError:
        pass

      try:
        apio = self.api.get(apiname)
      except AttributeError:
        pass

      if not apia and not apio:
        tmsg.append('%s is not in the api' % apiname)
      else:
        if apia and not apio:
          apif = apia
          apiapath = inspect.getsourcefile(apia)
          apiapath = apiapath[len(self.api.BASEPATH)+1:]

        elif apio and not apia:
          apif = apio
          apiopath = inspect.getsourcefile(apio)
          apiopath = apiopath[len(self.api.BASEPATH)+1:]

        elif not (apio == apia) and apia and apio:
          apif = apia
          apiapath = inspect.getsourcefile(apia)
          apiopath = inspect.getsourcefile(apio)
          apiapath = apiapath[len(self.api.BASEPATH)+1:]
          apiopath = apiopath[len(self.api.BASEPATH)+1:]

        else:
          apif = apia
          apiapath = inspect.getsourcefile(apia)
          apiapath = apiapath[len(self.api.BASEPATH)+1:]

        src = inspect.getsource(apif)
        dec = src.split('\n')[0]
        args = dec.split('(')[-1].strip()
        args = args.split(')')[0]
        argsl = args.split(',')
        argn = []
        for i in argsl:
          if i == 'self':
            continue
          argn.append('@Y%s@w' % i.strip())

        args = ', '.join(argn)
        tmsg.append('@G%s@w(%s)' % (apiname, args))
        tmsg.append(apif.__doc__ % tdict)

        tmsg.append('')
        if apiapath:
          tmsg.append('original defined in %s' % apiapath)
        if apiopath and apiapath:
          tmsg.append('overloaded in %s' % apiopath)
        elif apiopath:
          tmsg.append('original defined in %s' % apiopath)

    else: # args <= 0
      tmsg.append('Please provide an api to detail')

    return True, tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List functions in the api
      @CUsage@w: list @Y<apiname>@w
      @Yapiname@w = (optional) the toplevel api to show
    """
    tmsg = []
    apilist = {}
    if len(args) == 1:
      i = args[0]
      if i in self.api.api:
        apilist[i] = {}
        for k in self.api.api[i]:
          tstr = i + '.' + k
          apilist[i][k] = True
      if i in self.api.overloadedapi:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api.overloadedapi[i]:
          tstr = i + '.' + k
          apilist[i][k] = True
      if not apilist:
        tmsg.append('%s does not exist in the api' % i)

    else:
      for i in self.api.api:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api.api[i]:
          tstr = i + '.' + k
          apilist[i][k] = True

      for i in self.api.overloadedapi:
        if not (i in apilist):
          apilist[i] = {}
        for k in self.api.overloadedapi[i]:
          tstr = i + '.' + k
          apilist[i][k] = True

    tkeys = apilist.keys()
    tkeys.sort()
    for i in tkeys:
      tmsg.append('@G%-10s@w' % i)
      tkeys2 = apilist[i].keys()
      tkeys2.sort()
      for k in tkeys2:
        apif = self.api.get('%s.%s' % (i,k))
        comments = inspect.getcomments(apif)
        if comments:
          comments = comments.strip()
        tmsg.append('  @G%-15s@w : %s' % (k, comments))

    return True, tmsg

