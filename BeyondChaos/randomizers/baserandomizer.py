from abc import ABC, abstractmethod

from options import Options


class Randomizer(ABC):

    def __init__(self, options: Options):
        self._Options = options

    @property
    @abstractmethod
    def is_active(self):
        """Determines if the given Randomizer is active or not based on flag configuration"""
        raise NotImplementedError

    @property
    @abstractmethod
    def priority(self):
        """What order this randomizer should come in. If this randomizer requires another to run before it,
        this should be a larger number (e.g. if stat mutation requires berserker mutation, stat mutation's priority
        should be a larger number)"""
        raise NotImplementedError

    @abstractmethod
    def randomize(self):
        """The actual randomization for a given flag happens here.

        Note that it should operate on a GameObject (or list of GameObjects) and have no access to the actual ROM."""
        raise NotImplementedError
