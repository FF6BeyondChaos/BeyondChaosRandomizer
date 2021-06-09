from typing import List

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
        pass
