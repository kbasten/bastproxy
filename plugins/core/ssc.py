"""
this module is for saving settings that should not appear in memory
the setting is saved to a file with read only permissions for the user
the proxy is running under

## Using
See the source for [net.net](/bastproxy/plugins/net/net.html)
for an example of using this plugin

'''python
    ssc = self.api('ssc.baseclass')()
    self.apikey = ssc('somepassword', self, desc='Password for something')
'''
"""
import os
import stat
import argparse

from plugins._baseplugin import BasePlugin

NAME = 'Secret Setting Class'
SNAME = 'ssc'
PURPOSE = 'Class to save settings that should not stay in memory'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

class SSC(object):
  """
  a class to manage settings
  """
  def __init__(self, ssname, plugin, **kwargs):
    """
    initialize the class
    """
    self.ssname = ssname
    self.plugin = plugin
    self.sname = plugin.sname
    self.name = plugin.name
    self.api = plugin.api

    if 'default' in kwargs:
      self.default = kwargs['default']
    else:
      self.default = ''

    if 'desc' in kwargs:
      self.desc = kwargs['desc']
    else:
      self.desc = 'setting'

    self.api('api.add')(self.ssname, self.getss)

    parser = argparse.ArgumentParser(add_help=False,
                                     description='set the %s' % self.desc)
    parser.add_argument('value',
                        help=self.desc,
                        default='',
                        nargs='?')
    self.api('commands.add')(self.ssname,
                             self.cmd_setssc,
                             history=False,
                             parser=parser)


  # read the secret from a file
  def getss(self):
    """
    read the secret from a file
    """
    first_line = ''
    filen = os.path.join(self.plugin.savedir, self.ssname)
    try:
      with open(filen, 'r') as fileo:
        first_line = fileo.readline()

      return first_line.strip()
    except IOError:
      self.api('send.error')('Please set the %s with #bp.%s.%s' % (self.desc,
                                                                   self.sname,
                                                                   self.ssname))

    return self.default

  def cmd_setssc(self, args):
    """
    set the secret
    """
    if args['value']:
      filen = os.path.join(self.plugin.savedir, self.ssname)
      sscfile = open(filen, 'w')
      sscfile.write(args['value'])
      os.chmod(filen, stat.S_IRUSR | stat.S_IWUSR)
      return True, ['%s saved' % self.desc]
    else:
      return True, ['Please enter the %s' % self.desc]

class Plugin(BasePlugin):
  """
  a plugin to handle secret settings
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.reloaddependents = True

    self.api('api.add')('baseclass', self.api_baseclass)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

  # return the secret setting baseclass
  def api_baseclass(self):
    # pylint: disable=no-self-use
    """
    return the sql baseclass
    """
    return SSC
