"""
$Id$
#TODO: add a timing flag
"""
import time

def timeit(func):
  """
  a decorator to time a function
  """
  def wrapper(*arg):
    """
    the wrapper to time a function
    """
    from libs import exported
    time1 = time.time()
    exported.msg('%s: started %s' % (func.func_name, arg), 'timing')
    res = func(*arg)
    time2 = time.time()
    exported.LOGGER.adddtype('timing')
    exported.msg('%s: %0.3f ms' % \
              (func.func_name, (time2-time1)*1000.0), 'timing')
    return res
  return wrapper
