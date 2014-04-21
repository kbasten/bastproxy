"""
$Id$

This plugin searches inventory for aarcheology items
It can tell how many are in inventory, how many are needed,
which pamplets are in inventory and which are needed
"""
import argparse
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Aarch'
SNAME = 'aarch'
PURPOSE = 'see what aarch items are needed'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

AARCHITEMS = {
 1: "Johnny's Appleseed",
 2: 'An Ancient Skull',
 3: 'A Golden Truffle',
 4: 'An Ancient Game Token',
 5: "Neptune's Retired Staff",
 6: "Percival's Retired Crown",
 7: 'Photo of an F1 Tornado',
 8: 'A Ring of Thandeld',
 9: 'Petrified Volcano Ash',
 10: "An Old Coyote's Tooth",
 11: "Dorothy's Lost Earring",
 12: 'A Golden Cross',
 13: 'Skeleton of a Goblin',
 14: 'A Rusted Coin',
 15: 'A Rusted Trumpet',
 16: 'A Coffin Lid',
 17: 'A Wedding Ring',
 18: 'A Dinosaur Bone',
 19: "A Dragon's Tooth",
 20: 'Unknown Element',
 21: 'A Destroyed Mosaic',
 22: 'A Silver Cross',
 23: 'Lost Binoculars',
 24: "Pirate's Hat",
 25: 'A Rusted Cleaver',
 26: 'Wilted Rose',
 27: 'Casino Chip',
 28: "Torn Visitor's Pass",
 29: 'Ten-year-old Textbook',
 30: 'Ivory Tusks',
 31: 'An Oasis',
 32: 'Skeleton of a Monkey',
 33: 'An Ancient Stalactite',
 34: 'Shoes of a Gnome',
 35: 'A Torn Peace Agreement',
 36: 'Chunk of an Iceberg',
 37: 'Wings of a Harpy',
 38: 'Petrified Tree Branch',
 39: 'A Golden Leaf',
 40: 'Writings of a Dream',
 41: 'An Old Rope',
 42: 'A Broken Twig',
 43: 'Brick from a Castle',
 44: 'A Rusted Belt Buckle',
 45: 'A Biblical Textbook',
 46: 'Frozen Flames',
 47: 'Fox Tooth',
 48: 'Picture of a Forest',
 49: 'Moon in a Bottle',
 50: 'Rotting Reed'
}

AARCHITEMSREV = {}
for AARCHT in AARCHITEMS:
  AARCHITEMSREV[AARCHITEMS[AARCHT]] = AARCHT

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

    self.api.get('dependency.add')('eq')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show needed aarch items')
    self.api.get('commands.add')('need', self.cmd_need,
                                parser=parser)

  def cmd_need(self, args):
    """
    find out which aarch items are needed to complete a set
    """
    tmsg = []
    all = AARCHITEMS.keys()
    have = []

    aarchi = self.api.get('eq.findname')('(Aarchaeology)')
    items = 0
    pam = 0
    for item in aarchi:
      nname = item['name'].replace('(Aarchaeology) ', '')
      if 'Collectable Pamphlet' in nname:
        pam = pam + 1
        pamnum = int(nname.split('#')[1])
        have.append(pamnum)
      else:
        if nname in AARCHITEMSREV:
          items = items + 1
          have.append(AARCHITEMSREV[nname])

    need = set(all) - set(have)
    tmsg.append('You have %s Aarcheology Items and %s Pamphlets' % (items, pam))
    if len(need) > 0:
      tmsg.append('You need %s pieces:' % len(need))
      for i in need:
        tmsg.append('%-2s - %s' % (i, AARCHITEMS[i]))
    else:
      tmsg.append('Congratulations! You have a full set of Aarcheology items.')

    return True, tmsg
