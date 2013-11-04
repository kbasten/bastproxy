"""
$Id$

this module is for timing functions
"""
import time
from libs.api import API
api = API()

def timeit(func):
  """
  a decorator to time a function
  """
  def wrapper(*arg):
    """
    the wrapper to time a function
    """
    time1 = time.time()
    api.get('output.msg')('%s: started %s' % (func.func_name, arg), 'timing')
    res = func(*arg)
    time2 = time.time()
    api.get('log.adddtype')('timing')
    api.get('output.msg')('%s: %0.3f ms' % \
              (func.func_name, (time2-time1)*1000.0), 'timing')
    return res
  return wrapper
