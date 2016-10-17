"""
make all functions that add things use kwargs instead of a table
"""

import glob
import os
import sys
import inspect
import operator
import argparse
import fnmatch

from libs.persistentdict import PersistentDict
from libs.api import API
from plugins._baseplugin import BasePlugin

def find_files(directory, filematch):
  """
  find files in a directory that match a filter
  """
  matches = []
  if os.sep in filematch:
    tstuff = filematch.split(os.sep)
    directory = os.path.join(directory, tstuff[0])
    filematch = tstuff[-1]
  for root, _, filenames in os.walk(directory, followlinks=True):
    for filename in fnmatch.filter(filenames, filematch):
      matches.append(os.path.join(root, filename))

  return matches

def get_module_name(modpath):
  """
  get a module name
  """
  tpath = os.path.split(modpath)
  base = os.path.basename(tpath[0])
  mod = os.path.splitext(tpath[1])[0]
  if not base:
    return '.'.join([mod]), mod
  else:
    return '.'.join([base, mod]), mod

class PluginMgr(object):
  # pylint: disable=too-many-public-methods
  """
  a class to manage plugins
  """
  def __init__(self):
    """
    initialize the instance
    """
    self.plugins = {}
    self.pluginl = {}
    self.pluginm = {}
    self.pluginp = {}
    self.options = {}
    self.plugininfo = {}

    index = __file__.rfind(os.sep)
    if index == -1:
      self.basepath = "." + os.sep
    else:
      self.basepath = __file__[:index]

    self.api = API()
    self.savefile = os.path.join(self.api.BASEPATH, 'data',
                                 'plugins', 'loadedplugins.txt')
    self.loadedplugins = PersistentDict(self.savefile, 'c')
    self.sname = 'plugins'
    self.lname = 'Plugin Manager'

    self.api.add(self.sname, 'isloaded', self.api_isloaded)
    self.api.add(self.sname, 'getp', self.api_getp)
    self.api.add(self.sname, 'module', self.api_getmodule)
    self.api.add(self.sname, 'allplugininfo', self.api_allplugininfo)
    self.api.add(self.sname, 'savestate', self.savestate)

  # return the dictionary of all plugins
  def api_allplugininfo(self):
    """
    return the plugininfo dictionary
    """
    return self.plugininfo

  def findplugin(self, name):
    """
    find a plugin file
    """
    if '.' in name:
      tlist = name.split('.')
      name = tlist[-1]
      del tlist[-1]
      npath = os.sep.join(tlist)

    _module_list = find_files(self.basepath, name + ".py")

    if len(_module_list) == 1:
      return _module_list[0], self.basepath
    else:
      for i in _module_list:
        if npath in i:
          return i, self.basepath

    return '', ''

  def findloadedplugin(self, plugin):
    """
    find a plugin
    """
    if plugin and plugin in self.plugins:
      return plugin

    fullimploc = 'plugins.' + plugin
    for tplugin in self.plugins:
      if self.plugins[tplugin].fullimploc == fullimploc:
        return tplugin

    return None

  # get a plugin instance
  def api_getmodule(self, pluginname):
    """  returns the module of a plugin
    @Ypluginname@w  = the plugin to check for"""
    if pluginname in self.pluginm:
      return self.pluginm[pluginname]

    return None

  # get a plugin instance
  def api_getp(self, pluginname):
    """  get a plugin instance
    @Ypluginname@w  = the plugin to get for"""

    if isinstance(pluginname, basestring):
      if pluginname in self.plugins:
        return self.plugins[pluginname]
      if pluginname in self.pluginl:
        return self.pluginl[pluginname]
      if pluginname in self.pluginm:
        return self.pluginm[pluginname]
      if pluginname in self.pluginp:
        return self.pluginp[pluginname]
    elif isinstance(pluginname, BasePlugin):
      return pluginname

    return None

  # check if a plugin is loaded
  def api_isloaded(self, pluginname):
    """  check if a plugin is loaded
    @Ypluginname@w  = the plugin to check for"""
    if pluginname in self.plugins or pluginname in self.pluginl:
      return True
    return False

  def loaddependencies(self, pluginname, dependencies):
    """
    load a list of modules
    """
    for i in dependencies:
      if i in self.plugins or i in self.pluginl:
        continue

      self.api.get('send.msg')('%s: loading dependency %s' % (pluginname, i),
                               pluginname)

      name, path = self.findplugin(i)
      if name:
        modpath = name.replace(path, '')
        self.load_module(modpath, path, force=True)

  def getnotloadedplugins(self):
    """
    create a message of all not loaded plugins
    """
    msg = []
    badplugins = self.updateallplugininfo()
    for modpath in sorted(self.plugininfo.keys()):
      sname = self.plugininfo[modpath]['sname']
      fullimploc = self.plugininfo[modpath]['fullimploc']
      if sname not in self.plugins:
        msg.append("%-20s : %-25s %-10s %-5s %s@w" % \
                  (fullimploc.replace('plugins.', ''),
                   self.plugininfo[modpath]['name'],
                   self.plugininfo[modpath]['author'],
                   self.plugininfo[modpath]['version'],
                   self.plugininfo[modpath]['purpose']))
    if len(msg) > 0:
      msg.insert(0, '-' * 75)
      msg.insert(0, "%-20s : %-25s %-10s %-5s %s@w" % \
                          ('Location', 'Name', 'Author', 'Vers', 'Purpose'))
      msg.insert(0, 'The following plugins are not loaded')

    if badplugins:
      msg.append('')
      msg.append('The following files would not import')
      for bad in badplugins:
        msg.append(bad.replace('plugins.', ''))

    return msg

  def getchangedplugins(self):
    """
    create a message of plugins that are changed on disk
    """
    msg = []

    plugins = sorted(self.plugins.values(),
                     key=operator.attrgetter('package'))
    packageheader = []

    msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                        ('Short Name', 'Name', 'Author', 'Vers', 'Purpose'))
    msg.append('-' * 75)
    for tpl in plugins:
      if tpl.ischangedondisk():
        if tpl.package not in packageheader:
          if len(packageheader) > 0:
            msg.append('')
          packageheader.append(tpl.package)
          limp = 'plugins.%s' % tpl.package
          mod = __import__(limp)
          try:
            desc = getattr(mod, tpl.package).DESCRIPTION
          except AttributeError:
            desc = ''
          msg.append('@GPackage: %s%s@w' % \
                  (tpl.package, ' - ' + desc if desc else ''))
          msg.append('@G' + '-' * 75 + '@w')
        msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                  (tpl.sname, tpl.name,
                   tpl.author, tpl.version, tpl.purpose))

    return msg

  def getpackageplugins(self, package):
    """
    create a message of plugins in a package
    """
    msg = []

    plist = []
    for plugin in self.plugins.values():
      if plugin.package == package:
        plist.append(plugin)

    if len(plist) > 0:
      plugins = sorted(plist, key=operator.attrgetter('sname'))
      limp = 'plugins.%s' % package
      mod = __import__(limp)
      try:
        desc = getattr(mod, package).DESCRIPTION
      except AttributeError:
        desc = ''
      msg.append('@GPackage: %s%s@w' % \
            (package, ' - ' + desc if desc else ''))
      msg.append('@G' + '-' * 75 + '@w')
      msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                          ('Short Name', 'Name',
                           'Author', 'Vers', 'Purpose'))
      msg.append('-' * 75)

      for tpl in plugins:
        msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                  (tpl.sname, tpl.name,
                   tpl.author, tpl.version, tpl.purpose))
    else:
      msg.append('That is not a valid package')

    return msg

  def getallplugins(self):
    """
    create a message of all plugins
    """
    msg = []

    plugins = sorted(self.plugins.values(),
                     key=operator.attrgetter('package'))
    packageheader = []
    msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                        ('Short Name', 'Name', 'Author', 'Vers', 'Purpose'))
    msg.append('-' * 75)
    for tpl in plugins:
      if tpl.package not in packageheader:
        if len(packageheader) > 0:
          msg.append('')
        packageheader.append(tpl.package)
        limp = 'plugins.%s' % tpl.package
        mod = __import__(limp)
        try:
          desc = getattr(mod, tpl.package).DESCRIPTION
        except AttributeError:
          desc = ''
        msg.append('@GPackage: %s%s@w' % \
            (tpl.package, ' - ' + desc if desc else ''))
        msg.append('@G' + '-' * 75 + '@w')
      msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                  (tpl.sname, tpl.name,
                   tpl.author, tpl.version, tpl.purpose))
    return msg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List plugins
      @CUsage@w: list
    """
    msg = []

    if args['notloaded']:
      msg.extend(self.getnotloadedplugins())
    elif args['changed']:
      msg.extend(self.getchangedplugins())
    elif args['package']:
      msg.extend(self.getpackageplugins(args['package']))
    else:
      msg.extend(self.getallplugins())
    return True, msg

  def cmd_load(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Load a plugin
      @CUsage@w: load @Yplugin@w
        @Yplugin@w    = the name of the plugin to load
               use the name without the .py
    """
    tmsg = []
    plugin = args['plugin']
    if plugin:

      fname = plugin.replace('.', os.sep)
      _module_list = find_files(self.basepath, fname + ".py")

      if len(_module_list) > 1:
        tmsg.append('There is more than one module that matches: %s' % \
                                                              plugin)
      elif len(_module_list) == 0:
        tmsg.append('There are no modules that match: %s' % plugin)
      else:
        modpath = _module_list[0].replace(self.basepath, '')
        sname, reason = self.load_module(modpath, self.basepath, True)
        if sname:
          if reason == 'already':
            tmsg.append('Module %s is already loaded' % sname)
          else:
            tmsg.append('Load complete: %s - %s' % \
                                          (sname, self.plugins[sname].name))
        else:
          tmsg.append('Could not load: %s' % plugin)
      return True, tmsg
    else:
      return False, ['@Rplease specify a plugin@w']

  def cmd_unload(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      unload a plugin
      @CUsage@w: unload @Yplugin@w
        @Yplugin@w    = the shortname of the plugin to load
    """
    tmsg = []
    plugina = args['plugin']

    if not plugina:
      return False, ['@Rplease specify a plugin@w']

    plugin = self.findloadedplugin(plugina)

    if plugin and plugin in self.plugins:
      if self.plugins[plugin].canreload:
        if self.unload_module(self.plugins[plugin].fullimploc):
          tmsg.append("Unloaded: %s" % plugin)
        else:
          tmsg.append("Could not unload:: %s" % plugin)
      else:
        tmsg.append("That plugin can not be unloaded")
      return True, tmsg
    elif plugin:
      tmsg.append('plugin %s does not exist' % plugin)
      return True, tmsg

    return False, ['@Rplease specify a plugin@w']

  def cmd_reload(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      reload a plugin
      @CUsage@w: reload @Yplugin@w
        @Yplugin@w    = the shortname of the plugin to reload
    """
    tmsg = []
    plugina = args['plugin']

    if not plugina:
      return False, ['@Rplease specify a plugin@w']

    plugin = self.findloadedplugin(plugina)

    if plugin and plugin in self.plugins:
      if self.plugins[plugin].canreload:
        tret, _ = self.reload_module(plugin, True)
        if tret and tret != True:
          tmsg.append("Reload complete: %s" % self.plugins[tret].fullimploc)
          return True, tmsg
      else:
        tmsg.append("That plugin cannot be reloaded")
        return True, tmsg
    else:
      tmsg.append('plugin %s does not exist' % plugin)
      return True, tmsg

    return False, tmsg

  def load_modules(self, tfilter):
    """
    load modules in all directories under plugins
    """
    _module_list = find_files(self.basepath, tfilter)
    _module_list.sort()

    load = False

    for fullpath in _module_list:
      modpath = fullpath.replace(self.basepath, '')
      force = False
      if modpath in self.loadedplugins:
        force = True
      modname, dummy = self.load_module(modpath, self.basepath,
                                        force=force, runload=load)

      if modname == 'log':
        self.api.get('log.adddtype')(self.sname)
        self.api.get('log.console')(self.sname)
        self.api.get('log.adddtype')('upgrade')
        self.api.get('log.console')('upgrade')

    if not load:
      testsort = sorted(self.plugins.values(),
                        key=operator.attrgetter('priority'))
      for i in testsort:
        try:
          #check dependencies here
          self.loadplugin(i)
        except Exception: # pylint: disable=broad-except
          self.api.get('send.traceback')(
              "load: had problems running the load method for %s." \
                          % i.fullimploc)
          del sys.modules[i.fullimploc]

  def updateallplugininfo(self):
    """
    find plugins that are not in self.plugininfo
    """
    _module_list = find_files(self.basepath, '*.py')
    _module_list.sort()

    self.plugininfo = {}
    badplugins = []

    for fullpath in _module_list:
      modpath = fullpath.replace(self.basepath, '')

      imploc, modname = get_module_name(modpath)

      if not modname.startswith("_"):
        fullimploc = "plugins" + '.' + imploc
        if fullimploc in sys.modules:
          self.plugininfo[modpath] = {}
          self.plugininfo[modpath]['sname'] = self.pluginp[modpath].sname
          self.plugininfo[modpath]['name'] = self.pluginp[modpath].name
          self.plugininfo[modpath]['purpose'] = self.pluginp[modpath].purpose
          self.plugininfo[modpath]['author'] = self.pluginp[modpath].author
          self.plugininfo[modpath]['version'] = self.pluginp[modpath].version
          self.plugininfo[modpath]['modpath'] = modpath
          self.plugininfo[modpath]['fullimploc'] = fullimploc

        else:
          try:
            _module = __import__(fullimploc)
            _module = sys.modules[fullimploc]

            self.plugininfo[modpath] = {}
            self.plugininfo[modpath]['sname'] = _module.SNAME
            self.plugininfo[modpath]['name'] = _module.NAME
            self.plugininfo[modpath]['purpose'] = _module.PURPOSE
            self.plugininfo[modpath]['author'] = _module.AUTHOR
            self.plugininfo[modpath]['version'] = _module.VERSION
            self.plugininfo[modpath]['modpath'] = modpath
            self.plugininfo[modpath]['fullimploc'] = fullimploc

            del sys.modules[fullimploc]

          except Exception: # pylint: disable=broad-except
            badplugins.append(fullimploc)

    return badplugins

  def load_module(self, modpath, basepath, force=False, runload=True):
    # pylint: disable=too-many-branches
    """
    load a single module
    """
    if basepath in modpath:
      modpath = modpath.replace(basepath, '')

    imploc, modname = get_module_name(modpath)

    if modname.startswith("_"):
      return False, 'dev'

    try:
      fullimploc = "plugins" + '.' + imploc
      if fullimploc in sys.modules:
        return sys.modules[fullimploc].SNAME, 'already'

      self.api.get('send.msg')('importing %s' % fullimploc, self.sname)
      _module = __import__(fullimploc)
      _module = sys.modules[fullimploc]
      self.api.get('send.msg')('imported %s' % fullimploc, self.sname)
      load = True

      if 'AUTOLOAD' in _module.__dict__ and not force:
        if not _module.AUTOLOAD:
          load = False
      elif 'AUTOLOAD' not in _module.__dict__:
        load = False

      if modpath not in self.plugininfo:
        self.plugininfo[modpath] = {}
        self.plugininfo[modpath]['sname'] = _module.SNAME
        self.plugininfo[modpath]['name'] = _module.NAME
        self.plugininfo[modpath]['purpose'] = _module.PURPOSE
        self.plugininfo[modpath]['author'] = _module.AUTHOR
        self.plugininfo[modpath]['version'] = _module.VERSION
        self.plugininfo[modpath]['modpath'] = modpath
        self.plugininfo[modpath]['fullimploc'] = fullimploc

      if load:
        if "Plugin" in _module.__dict__:
          self.add_plugin(_module, modpath, basepath, fullimploc, runload)

        else:
          self.api.get('send.msg')('Module %s has no Plugin class' % \
                                              _module.NAME,
                                   self.sname)

        _module.__dict__["proxy_import"] = 1

        return _module.SNAME, 'Loaded'
      else:
        if fullimploc in sys.modules:
          del sys.modules[fullimploc]
        self.api.get('send.msg')(
            'Not loading %s (%s) because autoload is False' % \
                                    (_module.NAME, fullimploc),
            self.sname)
      return True, 'not autoloaded'
    except Exception: # pylint: disable=broad-except
      if fullimploc in sys.modules:
        del sys.modules[fullimploc]

      self.api.get('send.traceback')(
          "Module '%s' refuses to import/load." % fullimploc)
      return False, 'error'

  def unload_module(self, fullimploc):
    """
    unload a module
    """
    if fullimploc in sys.modules:

      _module = sys.modules[fullimploc]
      try:
        if "proxy_import" in _module.__dict__:
          self.api.get('send.client')(
              'unload: unloading %s' % fullimploc)
          if "unload" in _module.__dict__:
            try:
              _module.unload()
            except Exception: # pylint: disable=broad-except
              self.api.get('send.traceback')(
                  "unload: module %s didn't unload properly." % fullimploc)

          if not self.remove_plugin(_module.SNAME):
            self.api.get('send.client')(
                'could not remove plugin %s' % fullimploc)

        del sys.modules[fullimploc]
        self.api.get('send.client')("unload: unloaded %s." % fullimploc)

      except Exception: # pylint: disable=broad-except
        self.api.get('send.traceback')(
            "unload: had problems unloading %s." % fullimploc)
        return False

    return True

  def reload_module(self, modname, force=False):
    """
    reload a module
    """
    if modname in self.plugins:
      plugin = self.plugins[modname]
      fullimploc = plugin.fullimploc
      basepath = plugin.basepath
      modpath = plugin.modpath
      sname = plugin.sname
      try:
        reloaddependents = plugin.reloaddependents
      except Exception: # pylint: disable=broad-except
        reloaddependents = False
      plugin = None
      if not self.unload_module(fullimploc):
        return False, ''

      if modpath and basepath:
        retval = self.load_module(modpath, basepath, force)
        if retval and reloaddependents:
          self.reloaddependents(sname)
        return retval

    else:
      return False, ''

  def reloaddependents(self, reloadedplugin):
    """
    reload all dependents
    """
    testsort = sorted(self.plugins.values(),
                      key=operator.attrgetter('priority'))
    for plugin in testsort:
      if plugin.sname != reloadedplugin:
        if reloadedplugin in plugin.dependencies:
          self.api.get('send.msg')('reloading dependent %s of %s' % \
                      (plugin.sname, reloadedplugin))
          plugin.savestate()
          self.reload_module(plugin.sname, True)

  def loadplugin(self, plugin):
    """
    check dependencies and run the load function
    """
    self.api.get('send.msg')('loading dependencies for %s' % \
                                  plugin.fullimploc,
                             self.sname)
    self.loaddependencies(plugin.sname, plugin.dependencies)
    self.api.get('send.client')("load: loading %s with priority %s" % \
			    (plugin.fullimploc, plugin.priority))
    self.api.get('send.msg')('loading %s (%s: %s)' % \
              (plugin.fullimploc, plugin.sname, plugin.name),
                             self.sname)
    plugin.load()
    self.api.get('send.client')("load: loaded %s" % plugin.fullimploc)
    self.api.get('send.msg')('loaded %s (%s: %s)' % \
              (plugin.fullimploc, plugin.sname, plugin.name),
                             self.sname)

    self.api.get('events.eraise')('%s_plugin_loaded' % plugin.sname, {})
    self.api.get('events.eraise')('plugin_loaded', {'plugin':plugin.sname})

  def add_plugin(self, module, modpath, basepath, fullimploc, load=True):
    # pylint: disable=too-many-arguments
    """
    add a plugin to be managed
    """
    module.__dict__["lyntin_import"] = 1
    plugin = module.Plugin(module.NAME, module.SNAME,
                           modpath, basepath, fullimploc)
    plugin.author = module.AUTHOR
    plugin.purpose = module.PURPOSE
    plugin.version = module.VERSION
    try:
      plugin.priority = module.PRIORITY
    except AttributeError:
      pass
    if plugin.name in self.pluginl:
      self.api.get('send.msg')('Plugin %s already exists' % plugin.name,
                               self.sname)
      return False
    if plugin.sname in self.plugins:
      self.api.get('send.msg')('Plugin %s already exists' % plugin.sname,
                               self.sname)
      return False

    if load:
      try:
        #check dependencies here
        self.loadplugin(plugin)
      except Exception: # pylint: disable=broad-except
        self.api.get('send.traceback')(
            "load: had problems running the load method for %s." \
                                                % fullimploc)
        del sys.modules[fullimploc]
        return False
    self.pluginl[plugin.name] = plugin
    self.plugins[plugin.sname] = plugin
    self.pluginm[plugin.sname] = module
    self.pluginp[modpath] = plugin
    self.loadedplugins[modpath] = True
    self.loadedplugins.sync()

    return True

  def remove_plugin(self, pluginname):
    """
    remove a plugin
    """
    plugin = None
    if pluginname in self.plugins:
      plugin = self.plugins[pluginname]
      try:
        plugin.unload()
        self.api.get('events.eraise')('%s_plugin_unload' % plugin.sname, {})
        self.api.get('events.eraise')('plugin_unloaded', {'name':plugin.sname})
        self.api.get('send.msg')('Plugin %s unloaded' % plugin.sname,
                                 self.sname, plugin.sname)
      except Exception: # pylint: disable=broad-except
        self.api.get('send.traceback')(
            "unload: had problems running the unload method for %s." \
                                  % plugin.sname)
        return False

      del self.plugins[plugin.sname]
      del self.pluginl[plugin.name]
      del self.pluginm[plugin.sname]
      del self.loadedplugins[plugin.modpath]
      self.loadedplugins.sync()

      plugin = None

      return True
    else:
      return False

  # save all plugins
  def savestate(self):
    """
    save all plugins
    """
    for i in self.plugins:
      self.plugins[i].savestate()

  def load(self):
    """
    load various things
    """
    self.load_modules("*.py")

    parser = argparse.ArgumentParser(add_help=False,
                                     description="list plugins")
    parser.add_argument('-n',
                        "--notloaded",
                        help="list plugins that are not loaded",
                        action="store_true")
    parser.add_argument('-c',
                        "--changed",
                        help="list plugins that are load but are changed on disk",
                        action="store_true")
    parser.add_argument('package',
                        help='the to list',
                        default='',
                        nargs='?')
    self.api.get('commands.add')('list',
                                 self.cmd_list,
                                 lname='Plugin Manager',
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                                     description="load a plugin")
    parser.add_argument('plugin',
                        help='the plugin to load, don\'t include the .py',
                        default='',
                        nargs='?')
    self.api.get('commands.add')('load',
                                 self.cmd_load,
                                 lname='Plugin Manager',
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                                     description="unload a plugin")
    parser.add_argument('plugin',
                        help='the plugin to unload',
                        default='',
                        nargs='?')
    self.api.get('commands.add')('unload',
                                 self.cmd_unload,
                                 lname='Plugin Manager',
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                                     description="reload a plugin")
    parser.add_argument('plugin',
                        help='the plugin to reload',
                        default='',
                        nargs='?')
    self.api.get('commands.add')('reload',
                                 self.cmd_reload,
                                 lname='Plugin Manager',
                                 parser=parser)

    self.api.get('commands.default')('list', self.sname)
    self.api.get('events.register')('savestate', self.savestate,
                                    plugin=self.sname)

    self.api.get('timers.add')('save', self.savestate, 60, nodupe=True, log=False)

