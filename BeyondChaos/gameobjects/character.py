import os
from typing import List

from gameobjects.gameobject import GameObject

char_stat_names_with_offsets = {
    "hp": 0,
    "mp": 1,
    "vigor": 6,
    "speed": 7,
    "stamina": 8,
    "m.power": 9,
    "attack": 10,
    "defense": 11,
    "m.def": 12,
    "evade": 13,
    "m.block": 14
}

level_and_run_offset = 21


class Character(GameObject):

    def __init__(self, char_id: int, address: int, name: str, byte_block: List[bytes]):
        super().__init__(address)
        assert len(byte_block) == 22
        self.name = name.lower().capitalize()
        self.newname = self.name.upper()
        self.battle_commands = [0x00, None, None, None]
        self.id = char_id
        self.berserk = False
        self.original_appearance = None
        self.new_appearance = None
        self.natural_magic = []
        self.palette = None
        self.wor_location = None
        self.command_objs = []
        self.stats_original = {}
        self.stats_mutated = {}
        for stat in char_stat_names_with_offsets:
            self.stats_original[stat] = byte_block[char_stat_names_with_offsets[stat]]
            self.stats_mutated[stat] = byte_block[char_stat_names_with_offsets[stat]]

        # Level modifier and run chance are stored in the same byte.
        # 5 and 6 store the level modifier while bits 7 and 8 store the run chance.
        level_and_run = byte_block[level_and_run_offset]
        self.level_modifier = (level_and_run & 0b00001100) >> 2
        self.run_chance = level_and_run & 0b00000011

        self.level_modifier_mutated = (level_and_run & 0b00001100) >> 2
        self.run_chance_mutated = level_and_run & 0b00000011

    def __repr__(self):
        s = "{0:02d}. {1}".format(self.id + 1, self.newname) + os.linesep
        for name in char_stat_names_with_offsets:
            blurb = "{0:8} {1}".format(name.upper() + ":", self.stats_mutated[name])
            s += blurb + os.linesep
        return s.strip()

    def get_bytes(self):
        substitution = {}
        for stat in self.stats_mutated:
            address = self.address + char_stat_names_with_offsets[stat]
            substitution[address] = self.stats_mutated[stat].to_bytes(1, byteorder="big")
        level_and_run = (self.level_modifier_mutated << 2) | self.run_chance_mutated
        substitution[self.address + level_and_run_offset] = level_and_run.to_bytes(1, byteorder="big")
        return substitution
