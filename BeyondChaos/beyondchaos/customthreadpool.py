import multiprocessing.pool

# TODO: send to utils

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

