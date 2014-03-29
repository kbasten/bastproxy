"""
$Id$

This plugin is a utility plugin for aardwolf functions
It adds functions to exported.aardu
"""
import math
import re
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Item Utils'
SNAME = 'itemu'
PURPOSE = 'Aard item and inventory functions'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

WEARLOCS = [
 'light',
 'head',
 'eyes',
 'lear',
 'rear',
 'neck1',
 'neck2',
 'back',
 'medal1',
 'medal2',
 'medal3',
 'medal4',
 'torso',
 'body',
 'waist',
 'arms',
 'lwrist',
 'rwrist',
 'hands',
 'lfinger',
 'rfinger',
 'legs',
 'feet',
 'shield',
 'wielded',
 'second',
 'hold',
 'float',
 'tattoo1',
 'tattoo2',
 'above',
 'portal',
 'sleeping',
]

WEARLOCSREV = {}
for i in WEARLOCS:
  WEARLOCSREV[i] = WEARLOCS.index(i)

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.api.get('api.add')('dataparse', self.api_dataparse)
    self.api.get('api.add')('wearlocs', self.api_wearlocs)

    self.invlayout = {}
    self.invlayout['invheader'] = ["serial", "level", "type", "worth",
                                "weight", "wearable", "flags", "owner",
                                "fromclan", "timer", "u1", "u2", "u3",
                                "score"]
    self.invlayout['container'] = ["capacity", "heaviestitem", "holding",
                                "itemsinside", "totalweight", "itemburden",
                                "itemweightpercent"]
    self.invlayout['statmod'] = ['stat', 'value']
    self.invlayout['resistmod'] = ['resist', 'value']
    self.invlayout['weapon'] = ["wtype", "avedam", "inflicts", "damtype",
                             "special"]
    self.invlayout['skillmod'] = ['skillnum', 'value']
    self.invlayout['spells'] = ["uses", "level", "sn1", "sn2", "sn3", "sn4",
                             "u1"]
    self.invlayout['food'] = ['percent']
    self.invlayout['drink'] = ["servings", "liquid", "liquidmax", "liquidleft",
                            "thirstpercent", "hungerpercent", "u1"]
    self.invlayout['furniture'] = ["hpregen", "manaregen", "u1"]
    self.invlayout['eqdata'] = ["serial", "shortflags", "cname", "level",
                             "type", "unique", "wearslot", "timer"]
    self.invlayout['light'] = ['duration']
    self.invlayout['portal'] = ['uses']


  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

  # get the wear locations table
  def api_wearlocs(self, rev=False):
    """  get the wear locations table
    @Yrev@w  = if True, return the reversed table
    """
    if rev:
      return WEARLOCSREV
    else:
      return WEARLOCS

  # parse a line from invitem, invdata, eqdata, invdetails
  def api_dataparse(self, line, layoutname):
    """ parse a line of data from invdetails, invdata, eqdata, invdetails
    @Yline@w       = The line to parse
    @ylayoutname@w = The layout of the line

    this function returns a dictionary"""
    tlist = line.split(',')
    titem = {}
    for i in xrange(len(self.invlayout[layoutname])):
      v = self.invlayout[layoutname][i]
      value = tlist[i]
      if v == 'wearslot' or v == 'itemtype' or v == 'level' or v == 'serial' \
         or v == 'type':
        value = int(value)

      titem[v] = value

    if layoutname == 'eqdata':
      titem['name'] = self.api.get('colors.stripansi')(titem['cname'])

    return titem
