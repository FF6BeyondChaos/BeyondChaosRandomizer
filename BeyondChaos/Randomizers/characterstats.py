from typing import List

from Dtos.character import Character
from Randomizers.baserandomizer import Randomizer
from options import Options
import random

multiplier_percentages = list(range(50, 151))


class CharacterStats(Randomizer):
    def __init__(self, options: Options, characters: list[Character]):
        super().__init__(options)
        self._characters = characters

    def randomize(self):
        if not self.is_active:
            return
        for character in self._characters:
            for stat in character.stats_mutated:
                mutation_check = 0
                if character.berserk:
                    character.stats_mutated[stat] += 1
                new_stat = character.stats_mutated[stat]
                while not mutation_check:
                    multiplier = random.choice(multiplier_percentages) / 100
                    new_stat *= multiplier
                    mutation_check = random.choice(list(range(10)))
                    # berserker character should not have stats reduced.
                    mutation_check = mutation_check or (character.berserk and new_stat < character.stats_original[stat])
                new_stat = max(1, min(int(new_stat), 254))
                character.stats_mutated[stat] = new_stat

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
