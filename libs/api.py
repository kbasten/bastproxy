"""
$Id$

this module handles the api for all other modules
"""
import sys
import time
try:
  from libs import color
except ImportError:
  pass

class API(object):
  """
  A class that exports an api for plugins and modules to use
  """
  api = {} # where the main api resides
  BASEPATH = ''
  MANAGERS = {}

  def __init__(self):
    """
    initialize the class
    """
    self.overloadedapi = {}
    self.timestring = '%a %b %d %Y %H:%M:%S'
    self.overload('managers', 'add', self.addmanager)
    self.overload('managers', 'getm', self.getmanager)

  def add(self, ptype, name, function):
    """
    add stuff to the api
    """
    if not (ptype in API.api):
      API.api[ptype] = {}

    if not (name in API.api[ptype]):
      API.api[ptype][name] = function

  def overload(self, ptype, name, function):
    """
    add stuff to the plugin api
    """
    if not (ptype in self.overloadedapi):
      self.overloadedapi[ptype] = {}

    self.overloadedapi[ptype][name] = function

  def getmanager(self, name):
    if name in self.MANAGERS:
      return self.MANAGERS[name]
    else:
      return None

  def addmanager(self, name, manager):
    self.MANAGERS[name] = manager

  def remove(self, ptype):
    if ptype in API.api:
      del API.api[ptype]

  def get(self, apiname, baseapi=False):
    """
    get an api
    """
    ptype, name = apiname.split('.')
    if not baseapi:
      try:
        return self.overloadedapi[ptype][name]
      except KeyError:
        pass

    try:
      return self.api[ptype][name]
    except KeyError:
      pass

    raise AttributeError('%s is not in the api' % apiname)

if __name__ == '__main__':
  def testapi():
    print 'testapi'

  def testover():
    print 'testover'

  api = API()
  api.add('test', 'api', testapi)
  api.add('test', 'over', testapi)
  print 'test.api', api.get('test.api')()
  print 'test.over', api.get('test.over')()
  print 'dict api.api', api.api
  api.overload('over', 'api', testover)
  print 'dict api.overloadedapi', api.overloadedapi
  print 'over.api', api.get('over.api')()
  api.overload('test', 'over', testover)
  print 'dict api.api', api.api
  print 'dict api.overloadapi', api.overloadedapi
  print 'test.over', api.get('test.over')()
  print 'test.api', api.get('test.api')()
  #print 'test.three', api.test.three()

  api2 = API()
  print 'api2 test.api', api2.get('test.api')()
  print 'api2 test.over', api2.get('test.over')()
  print 'api2 dict api.api', api2.api
  api2.overload('over', 'api', testover)
  print 'api2 dict api.overloadedapi', api2.overloadedapi
  print 'api2 over.api', api2.get('over.api')()
  api2.overload('test', 'over', testover)
  print 'api2 dict api.api', api2.api
  print 'api2 dict api.overloadapi', api2.overloadedapi
  print 'api2 test.over', api2.get('test.over')()
  print 'api2 test.api', api2.get('test.api')()
  print 'test.three', api2.get('test.three')()
