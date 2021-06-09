from abc import ABC, abstractmethod
from typing import List

from options import Options


class Randomizer(ABC):

    def __init__(self, options: Options):
        self._Options = options

    @property
    @abstractmethod
    def is_active(self):
        raise NotImplementedError

    @abstractmethod
    def randomize(self):
        raise NotImplementedError
