"""
$Id$

This plugin highlights cp/gq/quest mobs in scan
"""
import time
import os
import copy
import fnmatch
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin
from libs.persistentdict import PersistentDict
from libs.timing import timeit

NAME = 'Scan Highlight'
SNAME = 'scanh'
PURPOSE = 'highlight cp, gq, quest mobs in scan'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin manage info about spells and skills
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.api.get('dependency.add')('quest')
    self.api.get('dependency.add')('cp')
    self.api.get('dependency.add')('gq')

    self.mobs = {}

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('cpbackcolor', '@z14', 'color',
                        'the background color for cp mobs')
    self.api.get('setting.add')('gqbackcolor', '@z9', 'color',
                        'the background color for gq mobs')
    self.api.get('setting.add')('questbackcolor', '@z13', 'color',
                        'the background color for quest mobs')
    self.api.get('setting.add')('cptextcolor', '@x0', 'color',
                        'the background color for cp mobs')
    self.api.get('setting.add')('gqtextcolor', '@x0', 'color',
                        'the background color for gq mobs')
    self.api.get('setting.add')('questtextcolor', '@x0', 'color',
                        'the background color for quest mobs')

    self.api.get('triggers.add')('scanstart',
            "^\{scan\}$")
    self.api.get('triggers.add')('scanend',
            "^\{/scan\}$",
            enabled=False, group='scan')

    self.api.get('events.register')('trigger_scanstart', self.scanstart)
    self.api.get('events.register')('trigger_scanend', self.scanend)
    self.api.get('events.register')('aard_cp_mobsleft', self.cpmobs)
    self.api.get('events.register')('aard_cp_failed', self.cpclear)
    self.api.get('events.register')('aard_cp_comp', self.cpclear)
    self.api.get('events.register')('aard_gq_mobsleft', self.gqmobs)
    self.api.get('events.register')('aard_gq_done', self.gqclear)
    self.api.get('events.register')('aard_gq_completed', self.gqmobs)
    self.api.get('events.register')('aard_gq_won', self.gqmobs)
    self.api.get('events.register')('aard_quest_start', self.questmob)
    self.api.get('events.register')('aard_quest_failed', self.questclear)
    self.api.get('events.register')('aard_quest_comp', self.questclear)

  def scanstart(self, args):
    """
    show that the trigger fired
    """
    self.api.get('send.msg')('found {scan}')
    self.api.get('triggers.togglegroup')('scan', True)
    self.api.get('events.register')('trigger_all', self.scanline)

  def scanline(self, args):
    """
    parse a scan line
    """
    cptextcolor = self.api.get('setting.gets')('cptextcolor')
    cpbackcolor = self.api.get('setting.gets')('cpbackcolor')
    gqtextcolor = self.api.get('setting.gets')('gqtextcolor')
    gqbackcolor = self.api.get('setting.gets')('gqbackcolor')
    questtextcolor = self.api.get('setting.gets')('questtextcolor')
    questbackcolor = self.api.get('setting.gets')('questbackcolor')
    line = args['line'].lower().strip()
    self.api.get('send.msg')('scanline: %s' % line)
    if 'cp' in self.mobs:
      for i in self.mobs['cp']:
        if i['nocolorname'].lower() in line:
          args['newline'] = cptextcolor + \
                  cpbackcolor + args['line'] + ' - (CP)@x'
          self.api.get('send.msg')('cp newline: %s' % args['newline'])
          break
    if 'gq' in self.mobs:
      for i in self.mobs['gq']:
        if i['name'].lower() in line:
          args['newline'] = gqtextcolor + \
                  gqbackcolor + args['line'] + ' - (GQ)@x'
          self.api.get('send.msg')('gq newline: %s' % args['newline'])
          break
    if 'quest' in self.mobs:
      if self.mobs['quest'].lower() in line:
        args['newline'] = questtextcolor + \
              questbackcolor + args['line'] + ' - (Quest)@x'
        self.api.get('send.msg')('quest newline: %s' % args['newline'])

    return args

  def scanend(self, args):
    """
    reset current when seeing a spellheaders ending
    """
    self.api.get('send.msg')('found {/scan}')
    self.api.get('events.unregister')('trigger_all', self.scanline)
    self.api.get('triggers.togglegroup')('scan', False)

  def cpmobs(self, args):
    """
    get cp mobs left
    """
    self.api.get('send.msg')('got cpmobs')
    if 'mobsleft' in args:
      self.mobs['cp'] = args['mobsleft']

  def cpclear(self, args):
    """
    clear the cp mobs
    """
    self.api.get('send.msg')('clearing cp mobs')
    del(self.mobs['cp'])

  def gqmobs(self, args):
    """
    get gq mobs left
    """
    self.api.get('send.msg')('got gqmobs')
    if 'mobsleft' in args:
      self.mobs['gq'] = args['mobsleft']

  def gqclear(self, args):
    """
    clear the gq mob
    """
    self.api.get('send.msg')('clearing gq mobs')
    del(self.mobs['gq'])

  def questmob(self, args):
    """
    get quest mob
    """
    self.api.get('send.msg')('got quest mob')
    self.mobs['quest'] = args['mobname']

  def questclear(self, args):
    """
    clear the quest mob
    """
    self.api.get('send.msg')('clearing quest mob')
    del(self.mobs['quest'])
