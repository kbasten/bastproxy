"""
This plugin sends pushbullet alerts when certain events happen in aardwolf

It sends alerts for the following:

 * quests available
 * gq available
 * ice age
"""
import time

from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Pushbullet Alerts'
SNAME = 'pbalerts'
PURPOSE = 'Pushbullet Alert for Aardwolf Events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf quest events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.api.get('dependency.add')('utils.pb')
    self.api.get('dependency.add')('aardwolf.gq')
    self.api.get('dependency.add')('aardwolf.quest')
    self.api.get('dependency.add')('aardwolf.iceage')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('events.register')('aard_gq_declared', self._gqdeclared)
    self.api.get('events.register')('aard_quest_ready', self._quest)
    self.api.get('events.register')('aard_iceage', self._iceage)
    self.api.get('events.register')('aard_reboot', self._reboot)

  def _gqdeclared(self, args):
    """
    send an pushbullet note that a gq has been declared
    """
    proxy = self.api.get('managers.getm')('proxy')
    times = time.asctime(time.localtime())
    msg = '%s:%s - A GQuest has been declared for levels %s to %s. (%s)' % (
              proxy.host, proxy.port,
              args['lowlev'], args['highlev'], times)
    self.api.get('pb.note')('New GQuest', msg)

  def _quest(self, _=None):
    """
    send an pushbullet note that it is time to quest
    """
    proxy = self.api.get('managers.getm')('proxy')
    times = time.asctime(time.localtime())
    msg = '%s:%s - Time to quest! (%s)' % (
              proxy.host, proxy.port, times)
    self.api.get('pb.note')('Quest Time', msg)

  def _iceage(self, _=None):
    """
    send an pushbullet note that an iceage approaches
    """
    proxy = self.api.get('managers.getm')('proxy')
    times = time.asctime(time.localtime())
    msg = '%s:%s - An ice age approaches! (%s)' % (
              proxy.host, proxy.port, times)
    self.api.get('pb.note')('Ice Age', msg)

  def _reboot(self, _=None):
    """
    send an pushbullet note that Aardwolf is rebooting
    """
    proxy = self.api.get('managers.getm')('proxy')
    times = time.asctime(time.localtime())
    msg = '%s:%s - Aardwolf is rebooting (%s)' % (
              proxy.host, proxy.port, times)
    self.api.get('pb.note')('Reboot', msg)
