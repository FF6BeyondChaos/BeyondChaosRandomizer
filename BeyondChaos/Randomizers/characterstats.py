from Dtos.character import Character
from Randomizers.baserandomizer import Randomizer
from options import Options


class CharacterStats(Randomizer):
    def __init__(self, options: Options, characters: list[Character]):
        super(options)
        self._characters = characters

    def randomize(self):
        if not self.is_active():
            return
        pass

    @property
    def is_active(self):
        return self._Options.random_character_stats
