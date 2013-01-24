"""
$Id$
"""
from libs import exported

name = 'Simple Substitute'

sman = None

class Substitute:
  def __init__(self):
    self._substitutes = {}

  def findsub(self, args):
    data = args['todata']
    for mem in self._substitutes.keys():
      data = data.replace(mem, self._substitutes[mem])
    args['todata'] = data
    return args

  def addsub(self, item, sub):
    self._substitutes[item] = sub

  def onload(self):
    exported.registerevent('to_client_event', self.findsub)

  def onunload(self):
    exported.unregisterevent('to_client_event', self.findsub)


def load():
  sman = Substitute()
  sman.onload()
  sman.addsub('Neil', 'Bast')
  sman.addsub('bug', 'peanut')

def unload():
  sman.onunload()