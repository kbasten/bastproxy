"""
This plugin autokeeps item types
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Item autokeep'
SNAME = 'itemkeep'
PURPOSE = 'keep an item type automatically'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf cp events
  """
  def __init__(self, *args, **kwargs):
    AardwolfBasePlugin.__init__(self, *args, **kwargs)

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    itemtypes = self.api.get('itemu.objecttypes')()

    for i in itemtypes:
      self.api.get('setting.add')(i, False, bool,
                                    'autokeep %s' % i)

    self.api.get('events.register')('inventory_added', self.inventory_added)

  def inventory_added(self, args):
    """
    check an item added to inventory to autokeep
    """
    item = args['item']
    itemtypesrev = self.api.get('itemu.objecttypes')()
    ntype = itemtypesrev[item['type']]

    if self.api.get('setting.gets')(ntype):
      if not ('K' in item['shortflags']):
        self.api.get('send.execute')('keep %s' % item['serial'])
