"""
$Id$

This plugin is a utility plugin for aardwolf functions
It adds functions to exported.aardu
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Item Utils'
SNAME = 'itemu'
PURPOSE = 'Aard item and inventory functions'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

OBJECTTYPES = [
  'none',
  'light',
  'scroll',
  'wand',
  'staff',
  'weapon',
  'treasure',
  'armor',
  'potion',
  'furniture',
  'trash',
  'container',
  'drink',
  'key',
  'food',
  'boat',
  'mobcorpse',
  'corpse',
  'fountain',
  'pill',
  'portal',
  'beacon',
  'giftcard',
  'bold',
  'raw material',
  'campfire'
]
OBJECTTYPESREV = {}
for objectt in OBJECTTYPES:
  OBJECTTYPESREV[objectt] = OBJECTTYPES.index(objectt)

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
for wearlocs in WEARLOCS:
  WEARLOCSREV[wearlocs] = WEARLOCS.index(wearlocs)

ITEMFLAGS = ['K', 'G', 'H', 'I', 'M']

ITEMFLAGSCOLORS = {
 'K':'R',
 'M':'B',
 'G':'W',
 'H':'C',
 'I':'w',
}

ITEMFLAGSNAME = {
 'K':'kept',
 'M':'magic',
 'G':'glow',
 'H':'hum',
 'I':'invis',
}

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.api.get('api.add')('dataparse', self.api_dataparse)
    self.api.get('api.add')('wearlocs', self.api_wearlocs)
    self.api.get('api.add')('objecttypes', self.api_objecttypes)
    self.api.get('api.add')('itemflags', self.api_itemflags)
    self.api.get('api.add')('itemflagscolors', self.api_itemflagscolors)
    self.api.get('api.add')('itemflagsname', self.api_itemflagsname)

    self.invlayout = {}
    self.invlayout['invheader'] = ["serial", "level", "type", "worth",
                                "weight", "wearable", "flags", "owner",
                                "fromclan", "timer", "u1", "u2", "u3",
                                "score"]
    self.invlayout['container'] = ["capacity", "heaviestitem", "holding",
                                "itemsinside", "totalweight", "itemburden",
                                "itemweightpercent"]
    self.invlayout['statmod'] = ['name', 'value']
    self.invlayout['resistmod'] = ['name', 'value']
    self.invlayout['weapon'] = ["wtype", "avedam", "inflicts", "damtype",
                             "special"]
    self.invlayout['skillmod'] = ['name', 'value']
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
    self.invlayout['tempmod'] = ['type', 'u1', 'u2', 'statmod', 'duration']

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

  # get the flags name table
  def api_itemflagsname(self):
    """  get the flags name table
    """
    return ITEMFLAGSNAME

  # get the flags table
  def api_itemflags(self):
    """  get the flags table
    """
    return ITEMFLAGS

  # get the flags color table
  def api_itemflagscolors(self):
    """  get the flags color table
    """
    return ITEMFLAGSCOLORS

  # get the wear locations table
  def api_wearlocs(self, rev=False):
    """  get the wear locations table
    @Yrev@w  = if True, return the reversed table
    """
    if rev:
      return WEARLOCSREV
    else:
      return WEARLOCS

  # get the object types table
  def api_objecttypes(self, rev=False):
    """  get the object types table
    @Yrev@w  = if True, return the reversed table
    """
    if rev:
      return OBJECTTYPESREV
    else:
      return OBJECTTYPES

  # parse a line from invitem, invdata, eqdata, invdetails
  def api_dataparse(self, line, layoutname):
    """ parse a line of data from invdetails, invdata, eqdata, invdetails
    @Yline@w       = The line to parse
    @ylayoutname@w = The layout of the line

    this function returns a dictionary"""
    tlist = [line]
    if layoutname == 'eqdata' or layoutname == 'tempmod':
      tlist = line.split(',')
    else:
      tlist = line.split('|')
    titem = {}
    if layoutname in self.invlayout:
      for i in xrange(len(self.invlayout[layoutname])):
        name = self.invlayout[layoutname][i]
        value = tlist[i]
        try:
          value = int(value)
        except ValueError:
          pass

        if layoutname == 'invheader' and name == 'type':
          try:
            value = value.lower()
          except AttributeError:
            pass

        titem[name] = value

      if layoutname == 'eqdata':
        titem['name'] = self.api.get('colors.stripcolor')(titem['cname'])

      return titem
    else:
      self.api.get('send.msg')('layout %s not found' % layoutname)
