import multiprocessing.pool
from threading import Thread


class NonDaemonProcess(multiprocessing.Process):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        super(NonDaemonProcess, self).__init__(group=None, target=target, name=name, args=args, kwargs=kwargs)

    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)


# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class NonDaemonPool(multiprocessing.pool.Pool):
    Process = NonDaemonProcess

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        try:
            if self._target is not None:
                self._return = self._target(*self._args,
                                                    **self._kwargs)
        except:
            pass

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


