import re
from dataclasses import dataclass, field
from typing import List, Set, Union
from utils import pipe_print


@dataclass(frozen=True)
class Mode:
    name: str
    display_name: str
    description: str
    forced_flags: List[str] = field(default_factory=list)
    prohibited_flags: Set[str] = field(default_factory=set)


@dataclass(unsafe_hash=True)
class Flag:
    name: str = field(default="")
    description: str = field(default="", compare=False)
    long_description: str = field(default="", compare=False)
    value: str = field(default='', compare=False)
    category: str = field(default="", compare=False)
    input_type: str = field(default="", compare=False)
    choices: [str] = field(default_factory=tuple, compare=False)
    default_index: int = field(default=0, compare=False)
    default_value: str = field(default="", compare=False)
    minimum_value: float = field(default=0, compare=False)
    maximum_value: float = field(default=255, compare=False)
    special_value_text: str = field(default=None, compare=False)
    always_on: bool = field(default=False, compare=False)

    # List for gui controls associated with the Flag.
    controls: {} = field(default_factory=dict, compare=False)

    # Conflicts is a list of other Flag names that conflict with this Flag. If any conflicting Flags are active,
    #   this Flag will be disabled (and deactivated).
    conflicts: ['str'] = field(default_factory=list, compare=False)

    # Requirements is a list of dictionaries. Each dictionary should be flag_name:flag_value pairs. Inside each
    #   dictionary, flags are processed as 'is flag 1 set to value 1 AND flag 2 set to value 2 AND ...'. Each separate
    #   dict is processed as 'is dict 1 requirements fulfilled OR dict 2 requirements fulfilled OR...'.
    #   The flag_value can be set to '*' to let a non-boolean flag accept any active value
    requirements: [] = field(default_factory=list, compare=False)

    # Children is a dictionary of child_flag_name:parent_flag_value. The child Flags are hidden if the parent
    #   Flag (this Flag) is not set to the indicated value.
    children: {} = field(default_factory=dict, compare=False)

    def get_requirement_string(self) -> str:
        """
        Returns a string describing a Flag's requirements.

        Returns:
            string
        """
        result = ''
        single_ors = []
        for index, requirement in enumerate(self.requirements):
            if len(requirement) > 1:
                result += '('
            for required_flag_name, required_value in requirement.items():
                required_flag = Options_.get_flag(required_flag_name)
                if required_flag.input_type == 'boolean':
                    if required_value:
                        # Add requirement to single_ors if this is the only requirement UNLESS single_ors is empty
                        #   and this is the last requirement
                        if (len(requirement) == 1 and not
                                (len(single_ors) == 0 and index + 1 >= len(self.requirements))):
                            single_ors.append(required_flag.name)
                        else:
                            result += 'Flag "' + required_flag.name + '" must be active'
                    else:
                        result += 'Flag "' + required_flag.name + '" must be inactive'
                elif required_flag.input_type in ['integer', 'float2']:
                    if required_value == '*':
                        # Add requirement to single_ors if this is the only requirement UNLESS single_ors is empty
                        #   and this is the last requirement
                        if (len(requirement) == 1 and not
                                (len(single_ors) == 0 and index + 1 >= len(self.requirements))):
                            single_ors.append(required_flag.name)
                        else:
                            result += 'Flag "' + required_flag.name + '" must be active'
                    else:
                        result += 'Flag "' + required_flag.name + '" must be set to "' + str(required_value) + '"'
                elif required_flag.input_type == 'combobox':
                    if required_value == '*':
                        # Add requirement to single_ors if this is the only requirement UNLESS single_ors is empty
                        #   and this is the last requirement
                        if (len(requirement) == 1 and not
                                (len(single_ors) == 0 and index + 1 >= len(self.requirements))):
                            single_ors.append(required_flag.name)
                        else:
                            result += 'Flag "' + required_flag.name + '" must be active'
                    else:
                        result += 'Flag "' + required_flag.name + ' must be set to ' + str(required_value) + '"'
                result += ' AND '
            result = result.strip(' AND ').strip('"').strip()
            if len(requirement) > 1:
                result += ') '
            if not len(requirement) == 1 and not index + 1 >= len(self.requirements):
                result += ' OR '

        # We use single_ors to build a list of individual flags that must be active to meet requirements.
        #   In other words, instead of doing 'Flag1 must be active OR flag2 must be active OR flag3 must be...'
        #   We collapse them into 'One of the following flags must be active: Flag1, Flag2, Flag3, ...'
        #   Doing this saves space for flags such as capslockoff that have a large number of requirements.
        if single_ors:
            temp = 'One of the following flags must be active: '
            for single_or in single_ors:
                temp += single_or + ', '
            temp = temp[:-2]
            if result:
                result = temp + ' OR ' + result
            else:
                result = temp
        result = result.strip()
        return result

    def has_requirement(self, flag_name, requirement_list=None):
        if not requirement_list:
            requirement_list = self.requirements
        for requirement in requirement_list:
            if isinstance(requirement, list):
                if self.has_requirement(flag_name=flag_name, requirement_list=requirement):
                    return True
            elif isinstance(requirement, dict):
                if flag_name in requirement.keys():
                    return True
        return False

    def remove_from_string(self, flag_string: str, mode: Mode):
        name = self.name
        invert_simple_flags = flag_string.startswith("-")

        # Search for a match for the flag ending in a colon. If a match is found, it's a flag that
        #     has a value, like swdtechspeed
        if re.search(r'\b' + re.escape(name.lower()) + r":", flag_string.lower()):
            string_after_key = flag_string[flag_string.index(name.lower() + ":") + len(name.lower() + ":"):]
            try:
                value = string_after_key[:string_after_key.index(" ")]
            except ValueError:
                # A space did not exist after the flag. Get the entire rest of the flag string.
                value = string_after_key

            return True, value, re.sub(r'\b' + re.escape(name) + r':' + re.escape(value) + r'\b',
                                       '',
                                       flag_string,
                                       re.IGNORECASE)

        # Search for a match for the flag ending in a word boundary. If a match is found, it's a flag that
        #     is on/off.
        elif re.search(r'\b' + re.escape(name.lower()) + r"\b", flag_string.lower()):
            if len(name) == 1 and invert_simple_flags:
                return False, False, re.sub(r'\b' + re.escape(name) + r'\b',
                                            '',
                                            flag_string,
                                            re.IGNORECASE)
            else:
                return True, True, re.sub(r'\b' + re.escape(name) + r'\b',
                                          '',
                                          flag_string,
                                          re.IGNORECASE)

        # The flag was not found. Is it a simple flag and needs to be turned on?
        # We need to account for the possibility of spaces or no spaces
        # spaces = '- p i e' - caught by re.search
        # no spaces = '-pie' - caught by flags_before_space
        try:
            flags_before_space = flag_string[:flag_string.index(" ")]
        except ValueError:
            flags_before_space = flag_string

        if len(name) == 1 and invert_simple_flags and not \
                (re.search(r'\b' + re.escape(name.lower()) + r"\b", flag_string.lower())
                 or name in flags_before_space):
            return True, True, re.sub(r'\b' + re.escape(name) + r'\b',
                                      '',
                                      flag_string,
                                      re.IGNORECASE)
        return False, False, flag_string


# def set_mode(mode_name: str) -> None:
#     mode = get_mode(mode_name)
#     if not mode:
#         pipe_print('ERROR: Attempted to activate a Mode that does not exist.')
#     else:
#         global active_mode
#         active_mode = mode


def get_mode(mode_name: str) -> Mode:
    for mode in ALL_MODES:
        if mode_name in (mode.name, mode.display_name):
            return mode


# def get_active_mode() -> (Mode | None):
#     global active_mode
#     if active_mode:
#         return active_mode


def get_flag_string():
    flag_string = ''
    for flag in ALL_FLAGS:
        if flag.value:
            if str(flag.value).lower() == 'true':
                flag_string += flag.name + ' '
            else:
                flag_string += flag.name + ':' + str(flag.value) + ' '
    return flag_string.strip()


def activate_from_string(flag_string, append=False):
    flags = {}
    for flag in flag_string.split(' '):
        if ':' in flag:
            flags[flag.split(':')[0]] = flag.split(':')[1]
        else:
            flags[flag] = 'True'

    for flag_name in Options_.mode.prohibited_flags:
        flag = Options_.get_flag(flag_name)
        if flag and flag.name in flags.keys():
            # The flag is prohibited. Notify the user and do not activate it.
            pipe_print("The flag '" + flag_name + "' has been deactivated. It is incompatible with " +
                       Options_.mode.name + ".")
            flags.pop(flag_name)

    if 'remonsterate' in flags.keys() and 'sketch' in flags.keys():
        pipe_print("The Flag 'sketch' has been deactivated. It is incompatible with remonsterate.")
        flags.pop('sketch')

    for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
        try:
            flag.value = flags[flag.name]
        except KeyError:
            if not append:
                flag.value = ''

    return get_flag_string()


# def get_flag(flag_attribute: str) -> Flag:
#     for flag in ALL_FLAGS:
#         if flag.name.lower() == flag_attribute.lower() or flag.description.lower() == flag_attribute.lower():
#             return flag


# def is_flag_active(flag_attribute: str):
#     flag = get_flag(flag_attribute)
#     if not flag:
#         pipe_print('ERROR: Attempted to check state of a Flag that does not exist: ' + str(flag_attribute))
#     elif not flag.value == '':
#         return True
#     return False


# def is_any_flag_active(flag_names: List[str]):
#     for flag_name in flag_names:
#         if is_flag_active(flag_name):
#             return True
#     return False


# def get_flag_value(flag_name: str):
#     flag = get_flag(flag_name)
#     if not flag:
#         pipe_print('ERROR: Attempted to check value of a Flag that does not exist: ' + str(flag_name))
#         raise RuntimeError()
#     else:
#         return flag.value


# def activate_flag(flag_name: str, flag_value=True):
#     flag = get_flag(flag_name)
#     if not flag:
#         pipe_print('ERROR: Attempted to set the value of a Flag that does not exist: ' + str(flag_name))
#         return
#
#     if flag.input_type == 'boolean':
#         try:
#             flag.value = bool(flag_value)
#         except ValueError:
#             pipe_print('ERROR: Attempted to set the value of a True/False Flag with an invalid value.')
#             return
#     elif flag.input_type == 'integer':
#         try:
#             flag.value = int(flag_value)
#         except ValueError:
#             pipe_print('ERROR: Attempted to set the value of an integer Flag with non-numeric value.')
#             return
#     elif flag.input_type == 'float2':
#         try:
#             flag.value = float(flag_value)
#         except ValueError:
#             pipe_print('ERROR: Attempted to set the value of a numeric Flag with non-numeric value.')
#             return
#     elif flag.input_type == 'combobox':
#         if str(flag_value).lower() in [choice.lower() for choice in flag.choices]:
#             flag.value = str(flag_value).lower()
#         else:
#             pipe_print('ERROR: Attempted to set the value of a Flag with an invalid value. Valid values are ' +
#                        str(flag.choices) + '.')
#             return


# def deactivate_flag(flag_name: str):
#     flag = get_flag(flag_name)
#     if not flag:
#         pipe_print('ERROR: Attempted to deactivate a Flag that does not exist.')
#     else:
#         flag.value = ''

def read_options_from_string(flag_string: str, mode: Union[Mode, str]):
    flags = {}

    if flag_string.startswith('-'):
        pipe_print("NOTE: Using all flags EXCEPT the specified flags.")

    if isinstance(mode, str):
        mode = [m for m in ALL_MODES if m.name == mode][0]

    # Ensures the makeover groups are included in MAKEOVER_MODIFIER_FLAGS
    get_makeover_groups()
    for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
        if len(flag_string) == 0:
            break
        found, value, flag_string = flag.remove_from_string(flag_string, mode)
        if found:
            flag.value = value
            flags[flag.name] = flag
    return flags


@dataclass
class Options:
    mode: Mode
    active_flags: [Flag] = field(default_factory=list)

    @staticmethod
    def get_flag_string():
        flag_string = ''
        for flag in ALL_FLAGS:
            if flag.value:
                if str(flag.value).lower() == 'true':
                    flag_string += flag.name + ' '
                else:
                    flag_string += flag.name + ':' + str(flag.value) + ' '
        return flag_string.strip()

    @staticmethod
    def get_flag(flag_name: str) -> Flag:
        for flag in ALL_FLAGS:
            if flag.name.lower() == flag_name.lower() or flag.description.lower() == flag_name.lower():
                return flag

    def is_flag_active(self, flag_attribute: str):
        for flag in self.active_flags:
            if flag.name.lower() == flag_attribute.lower() or flag.description.lower() == flag_attribute.lower():
                return flag

    def is_any_flag_active(self, flag_names: List[str]):
        for flag in self.active_flags:
            if flag.name.lower() in [flag_name.lower() for flag_name in flag_names]:
                return True

    def get_flag_value(self, flag_name: str):
        try:
            for flag in self.active_flags:
                if flag.name.lower() == flag_name.lower():
                    if not isinstance(flag.value, bool):
                        return flag.value
        except KeyError:
            return None

    def activate_flag(self, flag_name: str, flag_value=True):
        for flag in ALL_FLAGS:
            if flag.name.lower() == flag_name.lower():
                if flag in self.active_flags:
                    return
                flag.value = flag_value
                self.active_flags.append(flag)
                if flag in MAKEOVER_MODIFIER_FLAGS:
                    self.activate_flag("makeover", True)
                if flag in RESTRICTED_VANILLA_SPRITE_FLAGS:
                    self.activate_flag("frenchvanilla", True)
                return

    def deactivate_flag(self, flag_name: str):
        for index, flag in enumerate(self.active_flags):
            if flag.name == flag_name:
                del self.active_flags[index]

    def activate_from_string(self, flag_string):
        s = ""
        flags = read_options_from_string(flag_string, self.mode)

        for flag in flags.values():
            # Detect incompatible and prohibited flags
            if flag.name in self.mode.prohibited_flags:
                # The flag is prohibited. Notify the user and do not activate it.
                pipe_print("The flag '" + flag.name + "' has been deactivated. It is incompatible with " +
                           self.mode.name + ".")
                continue
            if flag.name == 'sketch' and 'remonsterate' in flags.keys():
                pipe_print("The flag '" + flag.name + "' has been deactivated. It is incompatible with remonsterate.")
                continue

            if len(flag.name) > 1:
                if flag.description:
                    if not flag.category == 'spriteCategories':
                        s += f"SECRET CODE: {flag.description} ACTIVATED\n"
                    else:
                        s += f"SECRET CODE: {str(flag.value).upper()} {str(flag.name).upper()} MODE ACTIVATED\n"
            self.activate_flag(flag.name, flag.value)

        for flag in [f for f in self.mode.forced_flags if not self.is_flag_active(f)]:
            self.activate_flag(flag, True)
        if self.is_flag_active('strangejourney'):
            self.activate_flag('notawaiter', True)

        return s


ANCIENT_CAVE_PROHIBITED_FLAGS = {
    "d",
    "k",
    "r",
    "j",
    "airship",
    "alasdraco",
    "lessfanatical",
    "mimetime",
    "morefanatical",
    "notawaiter",
    "rushforpower",
    "strangejourney",
    "worringtriad",
    "thescenarionottaken",

}

ALL_MODES = [
    Mode(
        name="normal",
        display_name='Normal',
        description="Play through the normal story."
    ),
    Mode(
        name="katn",
        display_name='Race - Kefka @ Narshe',
        description="Play the normal story up to Kefka at Narshe. Intended for racing.",
        prohibited_flags={"d", "k", "r", "airship", "alasdraco", "worringtriad", "mimetime"}
    ),
    Mode(
        name="ancientcave",
        display_name='Ancient Cave',
        description="Play through a long randomized dungeon.",
        forced_flags=["ancientcave"],
        prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS
    ),
    Mode(
        name="speedcave",
        display_name='Speed Cave',
        description="Play through a medium-sized randomized dungeon.",
        forced_flags=["speedcave", "ancientcave"],
        prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS
    ),
    Mode(
        name="racecave",
        display_name='Race - Randomized Cave',
        description="Play through a short randomized dungeon.",
        forced_flags=["racecave", "speedcave", "ancientcave"],
        prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS
    ),
    # Static number of encounters on Lete River, No charm drops, Start with random Espers,
    # Curated enemy specials, Banned Baba Breath & Seize
    Mode(
        name="dragonhunt",
        display_name='Race - Dragon Hunt',
        description="Kill all 8 dragons in the World of Ruin. Intended for racing.",
        forced_flags=["worringtriad"],
        prohibited_flags={"j", "airship", "alasdraco", "thescenarionottaken"}
    ),
]

NORMAL_FLAGS = [
    # Flags
    Flag(name='b',
         description='fix_exploits',
         long_description='Make the game more balanced by removing known bugs and exploits.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='c',
         description='random_palettes_and_names',
         long_description='Randomize palettes and names of various things.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='d',
         description='random_final_dungeon',
         long_description='Randomize final dungeon.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='e',
         description='random_espers',
         long_description='Randomize esper spells and levelup bonuses.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='f',
         description='random_formations',
         long_description='Randomize enemy formations.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='g',
         description='random_dances',
         long_description='Randomize dances.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='h',
         description='random_final_party',
         long_description='Your party in the Final Kefka fight will be random.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='i',
         description='random_items',
         long_description='Randomize the stats of equippable items.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='j',
         description='randomize_forest',
         long_description='Randomize the phantom forest.',
         category="core",
         input_type="boolean",
         conflicts=["strangejourney"],
         requirements=[],
         children={}
         ),
    Flag(name='k',
         description='random_clock',
         long_description='Randomize the clock in Zozo.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='l',
         description='random_blitz',
         long_description='Randomize blitz inputs.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='m',
         description='random_enemy_stats',
         long_description='Randomize enemy stats.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='n',
         description='random_window',
         long_description='Randomize window background colors.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='o',
         description='shuffle_commands',
         long_description="Shuffle characters' in-battle commands.",
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='p',
         description='random_animation_palettes',
         long_description='Randomize the palettes of spells and weapon animations.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='q',
         description='random_character_stats',
         long_description='Randomize what equipment each character can wear and character stats.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='r',
         description='shuffle_wor',
         long_description='Randomize character locations in the world of ruin.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='s',
         description='swap_sprites',
         long_description='Swap character graphics around.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='t',
         description='random_treasure',
         long_description='Randomize treasure including chests, colosseum, shops, and enemy drops.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='u',
         description='random_zerker',
         long_description='Umaro risk. (Random character will be berserk)',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='w',
         description='replace_commands',
         long_description='Generate new commands for characters,replacing old commands.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='y',
         description='randomize_magicite',
         long_description='Shuffle magicite locations.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='z',
         description='sprint',
         long_description='Always have "Sprint Shoes" effect.',
         category="core",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),

    # Sprite codes
    Flag(name='bravenudeworld',
         description="TINA PARTY MODE",
         long_description="All characters use the Esper Terra sprite.",
         category="sprites",
         input_type="boolean",
         conflicts=["kupokupo"],
         requirements=[{"s": True}],
         children={}
         ),
    Flag(name='kupokupo',
         description="MOOGLE MODE",
         long_description="All party members are moogles except Mog. With partyparty, "
                          "all characters are moogles, except Mog, Esper Terra, and Imps.",
         category="sprites",
         input_type="boolean",
         conflicts=["bravenudeworld"],
         requirements=[{"s": True}],
         children={}
         ),
    Flag(name='makeover',
         description="SPRITE REPLACEMENT MODE",
         long_description="Some sprites are replaced with new ones (like Cecil or Zero Suit Samus).",
         category="sprites",
         input_type="boolean",
         conflicts=[],
         requirements=[{"s": True}],
         children={'novanilla': True, 'frenchvanilla': True, 'cloneparty': True}
         ),
    Flag(name='novanilla',
         description="COMPLETE MAKEOVER MODE",
         long_description="Use with 'makeover' to have sprites from the vanilla game to be guaranteed "
                          "not to appear.",
         category="sprites",
         input_type="boolean",
         conflicts=['frenchvanilla'],
         requirements=[{'makeover': True}],
         children={}
         ),
    Flag(name='frenchvanilla',
         description="EQUAL RIGHTS MAKEOVER MODE",
         long_description="Use with 'makeover' to have sprites from the vanilla game be selected "
                          "with equal weight to new sprites.",
         category="sprites",
         input_type="boolean",
         conflicts=['novanilla'],
         requirements=[{'makeover': True}],
         children={}
         ),
    Flag(name='cloneparty',
         description="CLONE COSPLAY MAKEOVER MODE",
         long_description="Use with 'makeover' to have the randomizer actively try to choose sprite"
                          "versions of the same character.",
         category="sprites",
         input_type="boolean",
         conflicts=[],
         requirements=[{'makeover': True}],
         children={}
         ),
    Flag(name='partyparty',
         description="CRAZY PARTY MODE",
         long_description="Kefka, Trooper, Banon, Leo, Ghost, Merchant, Esper Terra, "
                          "and Soldier are included in the pool of sprite randomization",
         category="sprites",
         input_type="boolean",
         conflicts=[],
         requirements=[{"s": True}],
         children={}
         ),
    Flag(name='quikdraw',
         description="QUIKDRAW MODE",
         long_description="All characters look like imperial soldiers, and none of them have Gau's Rage skill.",
         category="sprites",
         input_type="boolean",
         conflicts=["bravenudeworld", "kupokupo", "suplexwrecks"],
         requirements=[{"s": True}],
         children={}
         ),

    # Quality of life codes
    Flag(name='alphalores',
         description="ALPHABETIZED LORES MODE",
         long_description="Alphabetizes the in-battle Lore list.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='informativemiss',
         description="INFORMATIVE MISS MODE",
         long_description="Effects will display 'Miss', 'Null', or 'Fail' depending on why the effect failed to land.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='magicnumbers',
         description="COLORFUL MAGIC NUMBERS MODE",
         long_description="Changes MP damage and MP healing to display in a different color than HP damage and HP "
                          "healing.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='mpparty',
         description="PARTY MP REFILL MODE",
         long_description="MP is also refilled when you form a party, instead of just HP.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='nicerpoison',
         description="LOW PIXELATION POISON MODE",
         long_description="Drastically reduces the pixelation effect of poison when in dungeons.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='questionablecontent',
         description="RIDDLER MODE",
         long_description="When items have significant differences from vanilla, a question mark "
                          "is appended to the item's name, including in shop menus.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[{'i': True}],
         children={}
         ),
    Flag(name='regionofdoom',
         description="DOOM FINDER MODE",
         long_description="Enables a dialog on the World of Ruin Airship to automatically find and fight Doom Gaze.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='relicmyhat',
         description="COMBINED EQUIPMENT MENUS",
         long_description="Combines the equipment and relic menus, and makes shop menus more informative.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='removeflashing',
         description="NOT SO FLASHY MODE",
         long_description='"All" removes most white flashing effects from the game. '
                          '"BumRush" just removes the Bum Rush flashing.',
         category="quality_of_life",
         input_type="combobox",
         choices=("Vanilla", "All", "BumRush"),
         default_value="Vanilla",
         default_index=0,
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='slowerbg',
         description="SLOWER BG MODE",
         long_description="Drastically reduces the speed of vertical scrolling backgrounds.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='tastetherainbow',
         description="AURA CYCLING MODE",
         long_description="Enables cycling of status effect auras on characters in-battle.",
         category="quality_of_life",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),

    # Aesthetic codes
    Flag(name='alasdraco',
         description="JAM UP YOUR OPERA MODE",
         long_description="Randomizes various aesthetic elements of the Opera.",
         category="aesthetic",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='bingoboingo',
         description="BINGO BONUS",
         long_description="Generates a Bingo table with various game elements to witness and check off. "
                          "The ROM does not interact with the bingo board.",
         category="aesthetic",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='capslockoff',
         description="Mixed Case Names Mode",
         long_description="Names use whatever capitalization is in the name lists instead of all caps.",
         category="aesthetic",
         input_type="boolean",
         conflicts=[],
         requirements=[{'partyparty': True}, {'bravenudeworld': True}, {'suplexwrecks': True}, {'novanilla': True},
                       {'christmas': True}, {'halloween': True}, {'kupokupo': True}, {'quikdraw': True},
                       {'makeover': True}, {'cloneparty': True}, {'frenchvanilla': True}],
         children={}
         ),
    Flag(name='johnnyachaotic',
         description="MUSIC MANGLING MODE",
         long_description="Randomizes music with no regard to what would make sense in a given location.",
         category="aesthetic",
         input_type="boolean",
         conflicts=["johnnydmad"],
         requirements=[],
         children={}
         ),
    Flag(name='johnnydmad',
         description="MUSIC REPLACEMENT MODE",
         long_description="Randomizes music with regard to what would make sense in a given location.",
         category="aesthetic",
         input_type="boolean",
         conflicts=["johnnyachaotic"],
         requirements=[],
         children={}
         ),
    Flag(name='notawaiter',
         description="CUTSCENE SKIPS",
         long_description="Up to Kefka at Narshe, the vast majority of mandatory cutscenes are completely removed. "
                          "Optional cutscenes are not removed.",
         category="aesthetic",
         input_type="boolean",
         conflicts=["ancientcave"],
         requirements=[],
         children={}
         ),
    Flag(name='remonsterate',
         description="MONSTER SPRITE REPLACEMENT MODE",
         long_description="Replaces monster sprites with sprites from other games. "
                          "Requires sprites in the remonstrate\\sprites folder. May introduce sketch glitching.",
         category="aesthetic",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),

    # battle codes
    Flag(name='collateraldamage',
         description="ITEM BREAK MODE",
         long_description="All equipment break for spells. Characters only have Fight and "
                          "Item commands. Enemies will use items drastically more often than usual.",
         category="battle",
         input_type="boolean",
         conflicts=['suplexwrecks'],
         requirements=[{'o': True}],
         children={}
         ),
    Flag(name='cursepower',
         description="CHANGE CURSED SHIELD MODE",
         long_description="Set the number of battles required to uncurse a Cursed Shield. (Vanilla = 255, 0 = Random)",
         category="battle",
         input_type="integer",
         default_value="255",
         minimum_value=0,
         maximum_value=255,
         special_value_text='Random',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='dancelessons',
         description="NO DANCE FAILURES",
         long_description="Removes the 50% chance that dances will fail when used on a different terrain.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='dancingmaduin',
         description="RESTRICTED ESPERS MODE",
         long_description="Espers can only be equipped by specific characters. Choose the minimum amount "
                          "of characters per Esper. Usually changes Paladin Shld spell. "
                          "\nRandom chooses the same random minimum for all Espers; Chaos chooses them separately.",
         category="battle",
         input_type="combobox",
         choices=("Off", "Chaos", "Random", "1", "2", "3", "4", "5", "6", "7", "8", "10", "11", "12", "13"),
         default_value="Off",
         default_index=0,
         conflicts=[],
         requirements=[{'e': True}],
         children={}
         ),
    Flag(name='darkworld',
         description="SLASHER'S DELIGHT MODE",
         long_description="Drastically increases the difficulty of the seed, akin to a hard mode. "
                          "Mostly meant to be used in conjunction with the madworld flag.",
         category="battle",
         input_type="boolean",
         conflicts=["ancientcave"],
         requirements=[{'m': True}],
         children={}
         ),
    Flag(name='easymodo',
         description="EASY MODE",
         long_description="All enemies have 1 HP.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='electricboogaloo',
         description="WILD ITEM BREAK MODE",
         long_description="Increases the list of spells that items can break and proc for from just "
                          "magic and some summons to include almost any skill.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[{'i': True}],
         children={}
         ),
    Flag(name='expboost',
         description="MULTIPLIED EXP MODE",
         long_description="All battles will award multiplied exp.",
         category="battle",
         input_type="float2",
         default_value="1.00",
         minimum_value=-0.10,
         maximum_value=50,
         special_value_text='Random',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='gpboost',
         description="MULTIPLIED GP MODE",
         long_description="All battles will award multiplied gp.",
         category="battle",
         input_type="float2",
         default_value="1.00",
         minimum_value=-0.10,
         maximum_value=50,
         special_value_text='Random',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='lessfanatical',
         description="EASY FANATICS TOWER MODE",
         long_description="Disables forced magic command in Fanatic's Tower.",
         category="battle",
         input_type="boolean",
         conflicts=["suplexwrecks"],
         requirements=[{'o': True}],
         children={}
         ),
    Flag(name='madworld',
         description="TIERS FOR FEARS MODE",
         long_description='Creates a "true tierless" seed, with enemies having a higher degree of '
                          'randomization and shops being very randomized as well.',
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='masseffect',
         description="WILD EQUIPMENT EFFECT MODE",
         long_description="Increases the number of rogue effects on equipment",
         category="battle",
         input_type="combobox",
         choices=("Off", "Random", "Low", "Med", "High"),
         default_value="Off",
         default_index=0,
         conflicts=[],
         requirements=[{'i': True}],
         children={}
         ),
    Flag(name='mpboost',
         description="MULTIPLIED MP MODE",
         long_description="All battles will award multiplied magic points.",
         category="battle",
         input_type="float2",
         default_value="1.00",
         minimum_value=-0.10,
         maximum_value=50,
         special_value_text='Random',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='nobreaks',
         description="NO ITEM BREAKS MODE",
         long_description="Causes no items to break for spell effects.",
         category="battle",
         input_type="boolean",
         conflicts=["unbreakable"],
         requirements=[{'i': True}],
         children={}
         ),
    Flag(name='norng',
         description="NO RNG MODE",
         long_description="Almost all calls to the RNG are removed, and actions are much less random as a result.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[{'b': True}],
         children={}
         ),
    Flag(name='playsitself',
         description="AUTOBATTLE MODE",
         long_description="All characters will act automatically, in a manner similar to "
                          "when Coliseum fights are fought.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='randombosses',
         description="RANDOM BOSSES MODE",
         long_description="Causes boss skills to be randomized similarly to regular enemy skills. "
                          "Boss skills can change to similarly powerful skills.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[{'m': True}],
         children={}
         ),
    Flag(name='rushforpower',
         description="OLD VARGAS FIGHT MODE",
         long_description="Reverts the Vargas fight to only require that Vargas take any "
                          "damage to begin his second phase.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[{'m': True}, {'o': True}, {'w': True}],
         children={}
         ),
    Flag(name='swdtechspeed',
         description="CHANGE SWDTECH SPEED MODE",
         long_description="Alters the speed at which the SwdTech bar moves.",
         category="battle",
         input_type="combobox",
         choices=("Fastest", "Faster", "Fast", "Vanilla", "Random"),
         default_value="Vanilla",
         default_index=3,
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='unbreakable',
         description="UNBREAKABLE ITEMS MODE",
         long_description="Causes all items to be indestructible when broken for a spell.",
         category="battle",
         input_type="boolean",
         conflicts=[],
         requirements=[{'i': True}],
         children={}
         ),

    # field codes
    Flag(name='bsiab',
         description="UNBALANCED MONSTER CHESTS MODE",
         long_description="Greatly increases the variance of monster-in-a-box encounters and removes "
                          "some sanity checks, allowing them to be much more difficult and volatile",
         category="field",
         input_type="boolean",
         conflicts=["ancientcave"],
         requirements=[{'t': True}],
         children={}
         ),
    Flag(name='cursedencounters',
         description="EXPANDED ENCOUNTERS MODE",
         long_description="Increases all zones to have 16 possible enemy encounters.",
         category="field",
         input_type="boolean",
         conflicts=[],
         requirements=[{'f': True}],
         children={}
         ),
    Flag(name='dearestmolulu',
         description="ENCOUNTERLESS MODE",
         long_description="No random encounters occur. Items that alter encounter rates increase them. "
                          "EXP flag recommended",
         category="field",
         input_type="boolean",
         conflicts=["ancientcave"],
         requirements=[],
         children={}
         ),
    Flag(name='fightclub',
         description="MORE LIKE COLI-DON'T-SEE-'EM",
         long_description="Does not allow you to see the coliseum rewards before betting, "
                          "but you can often run from the coliseum battles to keep your item.",
         category="field",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='mimetime',
         description='ALTERNATE GOGO MODE',
         long_description="Gogo will be hidden somewhere in the World of Ruin disguised as another character. "
                          "Bring that character to him to recruit him.",
         category="field",
         input_type="boolean",
         conflicts=[],
         requirements=[{'o': True}, {'t': True}, {'w': True}],
         children={}
         ),
    Flag(name='morefanatical',
         description='HORROR FANATICS TOWER',
         long_description="Fanatic's Tower is even more confusing than usual.",
         category="field",
         input_type="boolean",
         conflicts=["ancientcave"],
         requirements=[{'d': True}],
         children={}
         ),
    Flag(name='nomiabs',
         description='NO MIAB MODE',
         long_description="Chests will never have monster encounters in them.",
         category="field",
         input_type="boolean",
         conflicts=["ancientcave"],
         requirements=[{'t': True}],
         children={}
         ),
    Flag(name='randomboost',
         description="RANDOM BOOST MODE",
         long_description="Increases the strength of randomization for chests, steals, drops, skills, and "
                          "Esper spells. (0=uniform distribution)",
         category="field",
         input_type="float2",
         default_value="1.00",
         minimum_value=-0.10,
         maximum_value=10.00,
         special_value_text='Random',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='thescenarionottaken',
         description='DIVERGENT PATHS MODE',
         long_description="Changes the way the 3 scenarios are split up, to resemble PowerPanda's "
                          "'Divergent Paths' mod.",
         category="field",
         input_type="boolean",
         conflicts=["strangejourney", "worringtriad"],
         requirements=[],
         children={}
         ),
    Flag(name='worringtriad',
         description="START IN WOR",
         long_description="The player will start in the World of Ruin, with all of the World of Balance "
                          "treasure chests, along with a guaranteed set of items, and more Lores.",
         category="field",
         input_type="boolean",
         conflicts=["thescenarionottaken", "ancientcave"],
         requirements=[],
         children={}
         ),

    # character codes
    Flag(name='allcombos',
         description="ALL COMBOS MODE",
         long_description="All skills that get replaced with something are replaced with combo skills.",
         category="characters",
         input_type="boolean",
         conflicts=["nocombos", "suplexwrecks"],
         requirements=[{'w': True}],
         children={}
         ),
    Flag(name='canttouchthis',
         description="INVINCIBILITY",
         long_description="All characters have 255 Defense and 255 Magic Defense, as well as 128 Evasion "
                          "and Magic Evasion.",
         category="characters",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='desperation',
         description="DESPERATION MODE",
         long_description="Guarantees one character will have R-Limit, and greatly increases the chance "
                          "of having desperation attacks as commands.",
         category="characters",
         input_type="boolean",
         conflicts=['suplexwrecks'],
         requirements=[{'w': True}],
         children={}
         ),
    Flag(name='endless9',
         description="ENDLESS NINE MODE",
         long_description="All R-[skills] are automatically changed to 9x[skills]. W-[skills] will become 8x[skills].",
         category="characters",
         input_type="boolean",
         conflicts=['suplexwrecks'],
         requirements=[{'w': True}],
         children={}
         ),
    Flag(name='levelcap',
         description="LEVEL CAPPED MODE",
         long_description="Set a maximum level for your characters. Toggle on to reveal additional options.",
         category="characters",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={'cap_type': True, 'cap_min': True, 'cap_max': True}
         ),
    Flag(name='cap_type',
         description="",
         long_description="How should the level cap behave? "
                          "Random: Roll one level cap, apply it to all characters. "
                          "Chaos: Roll a different level cap for each character.",
         category="characters",
         input_type="combobox",
         always_on=True,
         choices=("Random", "Chaos"),
         default_value="Random",
         default_index=-1,
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='cap_min',
         description="",
         long_description="The minimum value that characters can roll as their capped level.",
         category="characters",
         input_type="integer",
         always_on=True,
         default_value='1',
         minimum_value=1,
         maximum_value=98,
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='cap_max',
         description="",
         long_description="The maximum value that characters can roll as their capped level.",
         category="characters",
         input_type="integer",
         always_on=True,
         default_value='99',
         minimum_value=2,
         maximum_value=99,
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='mementomori',
         description="INNATE RELIC MODE",
         long_description="Number of characters that begin with an innate relic ability.",
         category="characters",
         input_type="combobox",
         choices=("Random", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"),
         default_value="0",
         default_index=1,
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='metronome',
         description="R-CHAOS MODE",
         long_description="All characters have Fight, R-Chaos, Magic, and Item as their skillset, "
                          "except for the Mime, who has Mimic instead of Fight, and the Berserker, "
                          "who only has R-Chaos.",
         category="characters",
         input_type="boolean",
         conflicts=['suplexwrecks'],
         requirements=[{'o': True}],
         children={}
         ),
    Flag(name='naturalmagic',
         description="NATURAL MAGIC MODE",
         long_description="No Espers or equipment will teach spells. The only way for characters to "
                          "learn spells is through leveling up, if they have their own innate magic list.",
         category="characters",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='naturalstats',
         description="NATURAL STATS MODE",
         long_description="No Espers will grant stat bonuses upon leveling up.",
         category="characters",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='nocombos',
         description="NO COMBOS MODE",
         long_description="There will be no combo(dual) skills.",
         category="characters",
         input_type="boolean",
         conflicts=["allcombos", "suplexwrecks"],
         requirements=[{'w': True}],
         children={}
         ),
    Flag(name='penultima',
         description="PENULTIMATE MODE",
         long_description="Ultima cannot be learned by any means.",
         category="characters",
         input_type="boolean",
         conflicts=["suplexwrecks"],
         requirements=[{'w': True}],
         children={}
         ),
    Flag(name='replaceeverything',
         description="REPLACE ALL SKILLS MODE",
         long_description="All vanilla skills that can be replaced, are replaced.",
         category="characters",
         input_type="boolean",
         conflicts=["suplexwrecks"],
         requirements=[{'w': True}],
         children={}
         ),
    Flag(name='shadowstays',
         description="SHADOW STICKS AROUND MODE",
         long_description="Shadow no longer has a chance to leave the party in random battles",
         category="characters",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='supernatural',
         description="SUPER NATURAL MAGIC MODE",
         long_description="Makes it so that any character with the Magic command will have natural magic.",
         category="characters",
         input_type="boolean",
         conflicts=[],
         requirements=[{'o': True}],
         children={}
         ),
    Flag(name='suplexwrecks',
         description="SUPLEX MODE",
         long_description="All characters use the Sabin sprite, have a name similar to Sabin, have the "
                          "Blitz and Suplex commands, and can hit every enemy with Suplex.",
         category="characters",
         input_type="boolean",
         conflicts=["kupokupo", "bravenudeworld", "quikdraw"],
         requirements=[],
         children={}
         ),

    # gamebreaking codes
    Flag(name='airship',
         description="AIRSHIP MODE",
         long_description="The player can access the airship after leaving Narshe, or from any chocobo stable. "
                          "Doing events out of order can cause softlocks.",
         category="gamebreaking",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='equipanything',
         description="EQUIP ANYTHING MODE",
         long_description="Items that are not equippable normally can now be equipped as weapons or shields. "
                          "These often give strange defensive stats or weapon animations.",
         category="gamebreaking",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='sketch',
         description="ENABLE SKETCH GLITCH",
         long_description="Enables sketch bug. Not recommended unless you know what you are doing.",
         category="gamebreaking",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),

    # experimental codes
    Flag(name='strangejourney',
         description="BIZARRE ADVENTURE",
         long_description="A prototype entrance randomizer, similar to the ancientcave mode. "
                          "Includes all maps and event tiles, and is usually extremely hard to beat by itself.",
         category="experimental",
         input_type="boolean",
         conflicts=["thescenarionottaken", 'j'],
         requirements=[],
         children={}
         ),
    Flag(name='espercutegf',
         description='SUMMONER MODE',
         long_description='Characters gain the traits of equipped espers. '
                          'Casters can change equipped esper mid-battle.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='espffect',
         description='ESPER JUNCTION EFFECTS MODE',
         long_description='Attach random effects from the "Junction" patch '
                          'set to espers.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='effectmas',
         description='EQUIPMENT JUNCTION EFFECTS MODE',
         long_description='Attach random effects from the "Junction" patch '
                          'set to equipment (excluding relics). Low '
                          'potential for softlocks.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='effectory',
         description='RELIC JUNCTION EFFECTS MODE',
         long_description='Attach random effects from the "Junction" patch '
                          'set to relics. Low potential for softlocks.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='effectster',
         description='MONSTER JUNCTION EFFECTS MODE',
         long_description='Attach random effects from the "Junction" patch '
                          'set to monsters, rages, and some statuses. Medium '
                          'potential for softlocks.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='treaffect',
         description='MONSTER EQUIPMENT JUNCTION EFFECTS MODE',
         long_description='Monsters inherit the "Junction" effects of held '
                          'items. Medium potential for softlocks.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='jejentojori',
         description='MEMENTO MORI JUNCTIONS MODE',
         long_description='Innate "mementomori" relics retain their junction '
                          'effects. High potential for softlocks.',
         category='experimental',
         input_type='boolean',
         conflicts=[],
         requirements=[{"mementomori": '*'}],
         children={}
         ),

]

# these are all sprite related codes
MAKEOVER_MODIFIER_FLAGS = []

# TODO: Figure out if this is even used.
RESTRICTED_VANILLA_SPRITE_FLAGS = []

# this is used for the makeover variation codes for sprites
makeover_groups = None


def get_makeover_groups():
    try:
        global makeover_groups
        if makeover_groups:
            return makeover_groups

        from appearance import get_sprite_replacements
        sprite_replacements = get_sprite_replacements()
        makeover_groups = {}

        for sr in sprite_replacements:
            for group in sr.groups:
                if group in makeover_groups:
                    makeover_groups[group] = makeover_groups[group] + 1
                else:
                    makeover_groups[group] = 1

        # this is used for the makeover variation codes for sprites
        for mg in makeover_groups:
            no = Flag(name='no' + mg,
                      description=f"NO {mg.upper()} ALLOWED MODE",
                      long_description="Do not select {mg} sprites.",
                      category="sprite categories",
                      input_type="boolean",
                      conflicts=[],
                      requirements=[{'makeover': True}],
                      children={}
                      )
            MAKEOVER_MODIFIER_FLAGS.extend([
                Flag(name=mg,
                     description=f"CUSTOM {mg.upper()} FREQUENCY MODE",
                     long_description="Adjust probability of selecting " + mg + " sprites.",
                     category="sprite categories",
                     input_type="combobox",
                     choices=("Normal", "No", "Hate", "Like", "Only"),
                     default_value="Normal",
                     default_index=0,
                     conflicts=[],
                     requirements=[{'makeover': True}],
                     children={}
                     )])
            RESTRICTED_VANILLA_SPRITE_FLAGS.append(no)

        global ALL_FLAGS
        ALL_FLAGS = NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS + CAVE_FLAGS + SPECIAL_FLAGS
    except FileNotFoundError:
        pass
    return makeover_groups


# TODO: do this a better way
CAVE_FLAGS = [
    Flag(name='ancientcave',
         description="ANCIENT CAVE MODE",
         long_description="",
         category="cave",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='speedcave',
         description="SPEED CAVE MODE",
         long_description="",
         category="cave",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='racecave',
         description="RACE CAVE MODE",
         long_description="",
         category="cave",
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
]

SPECIAL_FLAGS = [
    Flag(name='christmas',
         description='CHIRSTMAS MODE',
         long_description='',
         category='holiday',
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         ),
    Flag(name='halloween',
         description="ALL HALLOWS' EVE MODE",
         long_description='',
         category='holiday',
         input_type="boolean",
         conflicts=[],
         requirements=[],
         children={}
         )
]

BETA_FLAGS = [

]

ALL_FLAGS = NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS + CAVE_FLAGS + SPECIAL_FLAGS

Options_ = Options(ALL_MODES[0])

Use_new_randomizer = True
