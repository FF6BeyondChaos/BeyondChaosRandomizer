from typing import List

from Dtos.character import Character
from Randomizers.baserandomizer import Randomizer
from options import Options


class CharacterStats(Randomizer):
    def __init__(self, options: Options, characters: list[Character]):
        super(options)
        self._characters = characters
        self._stat_offsets = {
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

    def randomize(self, byte_block: List[bytes]):
        if not self.is_active:
            return
        for character_id in range(len(self._characters)):
            character = self._characters[character_id]
            character.id = character_id
            for stat in self._stat_offsets:
                character.stats_original[stat] = byte_block[self._stat_offsets[stat]]
            print(character.stats_original)
        pass
        """
        def mutation(base):
            while True:
                value = max(base // 2, 1)
                if self.beserk:
                    value += 1

                value += random.randint(0, value) + random.randint(0, value)
                while random.randint(1, 10) == 10:
                    value = max(value // 2, 1)
                    value += random.randint(0, value) + random.randint(0, value)
                value = max(1, min(value, 0xFE))

                if not self.beserk:
                    break
                elif value >= base:
                    break

            return value

        self.stats = {}
        fout.seek(self.address)
        hpmp = bytes(fout.read(2))
        if not read_only:
            hpmp = bytes([mutation(v) for v in hpmp])
            fout.seek(self.address)
            fout.write(hpmp)
        self.stats['hp'], self.stats['mp'] = tuple(hpmp)

        fout.seek(self.address + 6)
        stats = fout.read(9)
        if not read_only:
            stats = bytes([mutation(v) for v in stats])
            fout.seek(self.address + 6)
            fout.write(stats)
        for name, value in zip(CHARSTATNAMES[2:], stats):
            self.stats[name] = value

        fout.seek(self.address + 21)
        level_run = fout.read(1)[0]
        run = level_run & 0x03
        level = (level_run & 0x0C) >> 2
        run_map = {
            0: [70, 20, 9, 1],
            1: [13, 70, 13, 4],
            2: [4, 13, 70, 13],
            3: [1, 9, 20, 70]
        }

        level_map = {
            0: [70, 20, 5, 5],  # avg. level + 0
            1: [18, 70, 10, 2],  # avg. level + 2
            2: [9, 20, 70, 1],  # avg. level + 5
            3: [20, 9, 1, 70]  # avg. level - 3
        }

        if not read_only:
            run_chance = random.randint(0, 99)
            for i, prob in enumerate(run_map[run]):
                run_chance -= prob
                if prob < 0:
                    run = i
                    break

            # Don't randomize level average values if worringtriad is active
            # Also don't randomize Terra's level because it gets added for
            # every loop through the title screen, apparently.
            if not start_in_wor and self.id != 0:
                level_chance = random.randint(0, 99)
                for i, prob in enumerate(level_map[level]):
                    level_chance -= prob
                    if level_chance < 0:
                        level = i
                        break
            fout.seek(self.address + 21)
            level_run = (level_run & 0xF0) | level << 2 | run
            fout.write(bytes([level_run]))
        pass
        """
    @property
    def is_active(self):
        return self._Options.random_character_stats
