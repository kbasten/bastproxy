"""
$Id$
#TODO: add a timing flag
"""
import time
from libs import exported

exported.LOGGER.adddtype('timing')

def timeit(func):
  """
  a decorator to time a function
  """
  def wrapper(*arg):
    """
    the wrapper to time a function
    """
    time1 = time.time()
    res = func(*arg)
    time2 = time.time()
    exported.msg('%s took %0.3f ms' % \
              (func.func_name, (time2-time1)*1000.0), 'timing')
    return res
  return wrapper