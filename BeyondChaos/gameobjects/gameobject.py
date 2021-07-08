from abc import ABC, abstractmethod
from typing import List

from options import Options


class GameObject(ABC):

    def __init__(self, address: int):
        self.address = address
        pass

    @abstractmethod
    def get_bytes(self):
        """
        Returns a dictionary of address -> value for direct substitution into the ROM.
        """
        pass
