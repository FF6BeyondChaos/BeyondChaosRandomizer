from random import random

from utils import hex2int


class ItemBlock:
    def __init__(self, itemid, pointer, name):
        self.itemid = hex2int(itemid)
        self.pointer = hex2int(pointer)
        self.name = name
        self.degree = None
        self.banned = False
        self.itemtype = 0

        self.price = 0
        self._rank = None
        self.dataname = bytes()
        self.heavy = False

    @property
    def is_tool(self):
        return self.itemtype & 0x0f == 0x00

    @property
    def is_weapon(self):
        return self.itemtype & 0x0f == 0x01

    @property
    def is_armor(self):
        return self.is_body_armor or self.is_shield or self.is_helm

    @property
    def is_body_armor(self):
        return self.itemtype & 0x0f == 0x02

    @property
    def is_shield(self):
        return self.itemtype & 0x0f == 0x03

    @property
    def is_helm(self):
        return self.itemtype & 0x0f == 0x04

    @property
    def is_relic(self):
        return self.itemtype & 0x0f == 0x05

    @property
    def is_consumable(self):
        return self.itemtype & 0x0f == 0x06
