import random

from gameobjects.character import Character
from randomizers.baserandomizer import Randomizer
from options import Options
from typing import List


class CharacterStats(Randomizer):

    def __init__(self, rng: random.Random, options: Options, characters: List[Character]):
        super().__init__(options)
        self._randomize_level = not self._Options.is_flag_active('worringtriad')
        self._characters = characters
        self._rng = rng

    @property
    def priority(self):
        return 50

    @property
    def is_active(self):
        return self._Options.random_character_stats

    def randomize(self):
        if not self.is_active:
            return
        for character in self._characters:
            if character.id == 1:
                character.initial_level_override = int(self._rng.choice([1,2,2,3,3,3,4,4,4,4,5,5,5,5,6,6,6,7,7,8]))
            for stat in character.stats_mutated:
                continue_mutating = True
                if character.berserk:
                    character.stats_mutated[stat] += 1
                new_stat = character.stats_mutated[stat]
                while continue_mutating:
                    multiplier = max(.5, min(self._rng.gauss(1, 0.17), 1.5))
                    new_stat *= multiplier
                    continue_mutating = self._rng.choice(list(range(10))) == 0
                    # berserker character should not have stats reduced.
                    if character.berserk and int(new_stat) <= character.stats_original[stat]:
                        new_stat = character.stats_mutated[stat]
                        continue_mutating = True
                new_stat = max(1, min(round(new_stat), 254))
                character.stats_mutated[stat] = new_stat
            self.modify_level_and_run_modifiers(character)

    def modify_level_and_run_modifiers(self, character):
        # probability a given run or level chance will change to the given index.
        # e.g. is a character starts with run chance of 1, there is a 13% chance it becomes 0 (index 0),
        # a 70% chance it remains the same (index 1), etc etc.
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
        run_roll = self._rng.randint(0, 99)
        run_chance_array = run_map[character.run_chance]
        new_run_chance = 0
        while run_roll >= 0:
            run_roll -= run_chance_array[new_run_chance]
            new_run_chance += 1
        character.run_chance_mutated = new_run_chance - 1
        # Don't randomize Terra's level because it gets added for
        # every loop through the title screen, apparently.
        if self._randomize_level and character.id != 1:
            level_roll = self._rng.randint(0, 99)
            level_chance_array = level_map[character.level_modifier]
            new_level_modifier = 0
            while level_roll >= 0:
                level_roll -= level_chance_array[new_level_modifier]
                new_level_modifier += 1
            character.level_modifier_mutated = new_level_modifier - 1
