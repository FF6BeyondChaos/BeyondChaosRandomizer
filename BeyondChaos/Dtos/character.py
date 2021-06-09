import os
from typing import List

from constants import char_stat_names
from utils import make_table

equip_offsets = {"weapon": 15,
                 "shield": 16,
                 "helm": 17,
                 "armor": 18,
                 "relic1": 19,
                 "relic2": 20}

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


class Character:
    def __init__(self, char_id: int, address: int, name: str, byte_block: List[bytes]):
        assert len(byte_block) == 22
        self.address = address
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
        level_and_run = byte_block[21]
        self.level_modifier = level_and_run & 0b00001100
        self.run_chance = level_and_run & 0b00000011

        self.level_modifier_mutated = level_and_run & 0b00001100
        self.run_chance_mutated = level_and_run & 0b00000011


    def __repr__(self):
        s = "{0:02d}. {1}".format(self.id + 1, self.newname) + "\n"
        command_names = []
        for c in self.command_objs:
            if c is not None:
                command_names.append(c.name.lower())
        s += "Commands: "
        s += ", ".join(command_names) + "\n"
        if self.original_appearance and self.new_appearance:
            s += "Looks like: %s\n" % self.new_appearance
            s += "Originally: %s\n" % self.original_appearance

        stat_blurbs = {}
        for name in char_stat_names:
            blurb = "{0:8} {1}".format(name.upper() + ":", self.stats[name])
            stat_blurbs[name] = blurb
        column1 = [stat_blurbs[n] for n in ["hp", "mp", "evade", "mblock"]]
        column2 = [stat_blurbs[n] for n in ["vigor", "m.power", "speed", "stamina"]]
        column3 = [stat_blurbs[n] for n in ["attack", "defense", "m.def"]]
        s += make_table([column1, column2, column3]) + os.linesep
        # TODO: Refactor Items and make get_notable_equips() work
        # if self.id < 14:
        #    s += "Notable equipment: "
        #    s += ", ".join([n.name for n in self.get_notable_equips()])
        #    s += "\n"
        if self.wor_location is not None:
            s += "World of Ruin location: %s\n" % self.wor_location
        if self.natural_magic:
            s += "Has natural magic.\n"
            for level, spell in self.natural_magic:
                s += "  LV %s - %s\n" % (level, spell.name)
        return s.strip()
