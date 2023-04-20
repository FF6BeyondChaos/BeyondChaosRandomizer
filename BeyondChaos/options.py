import re
from dataclasses import dataclass, field
from typing import List, Set, Union
from utils import pipe_print


@dataclass(frozen=True)
class Mode:
    name: str
    description: str
    forced_flags: List[str] = field(default_factory=list)
    prohibited_flags: Set[str] = field(default_factory=set)


@dataclass(unsafe_hash=True)
class Flag:
    name: str = field(default="")
    description: str = field(default="", compare=False)
    long_description: str = field(default="", compare=False)
    category: str = field(default="", compare=False)
    inputtype: str = field(default="", compare=False)
    choices: [str] = field(default_factory=list, compare=False)
    default_index: int = field(default=0, compare=False)
    default_value: str = field(default="", compare=False)
    minimum_value: int = field(default=0, compare=False)
    maximum_value: int = field(default=255, compare=False)

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

@dataclass
class Options:
    mode: Mode
    active_flags: [Flag] = field(default_factory=list)

    def is_flag_active(self, flag_attribute: str):
        for flag in self.active_flags:
            if flag.name.lower() == flag_attribute.lower() or flag.description.lower() == flag_attribute.lower():
                return True

    def is_any_flag_active(self, flag_names: List[str]):
        for flag in self.active_flags:
            if flag.name.lower() in [flag_name.lower() for flag_name in flag_names]:
                return True

    def get_flag_value(self, flag_name: str):
        try:
            for flag in self.active_flags:
                if flag.name.lower() == flag_name.lower():
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

    def activate_from_string(self, flag_string):
        s = ""
        flags = read_Options_from_string(flag_string, self.mode)

        for flag in flags.values():
            # Detect incompatible and prohibited flags
            if flag.name in self.mode.prohibited_flags:
                # The flag is prohibited. Notify the user and do not activate it.
                pipe_print("The flag '" + flag.name + "' has been deactivated. It is incompatible with " +
                      self.mode.name + ".")
                continue
            if flag.name == 'sketch' and [f for f in flags if f.name == 'remonsterate']:
                pipe_print("The flag '" + flag.name + "' has been deactivated. It is incompatible with remonsterate.")
                continue

            if len(flag.name) > 1:
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


def read_Options_from_string(flag_string: str, mode: Union[Mode, str]):
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


ANCIENT_CAVE_PROHIBITED_FLAGS = {
    "d",
    "k",
    "r",
    "j",
    "airship",
    "alasdraco",
    "notawaiter",
    "strangejourney",
    "worringtriad",
    "thescenarionottaken",
    "mimetime"
}

ALL_MODES = [
    Mode(name="normal", description="Play through the normal story."),
    Mode(name="ancientcave",
         description="Play through a long randomized dungeon.",
         forced_flags=["ancientcave"],
         prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS),
    Mode(name="speedcave",
         description="Play through a medium-sized randomized dungeon.",
         forced_flags=["speedcave", "ancientcave"],
         prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS),
    Mode(name="racecave",
         description="Play through a short randomized dungeon.",
         forced_flags=["racecave", "speedcave", "ancientcave"],
         prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS),
    Mode(name="katn",
         description="Play the normal story up to Kefka at Narshe. Intended for racing.",
         prohibited_flags={"d", "k", "r", "airship", "alasdraco", "worringtriad", "mimetime"}),
    # Static number of encounters on Lete River, No charm drops, Start with random Espers,
    # Curated enemy specials, Banned Baba Breath & Seize
    Mode(name="dragonhunt",
         description="Kill all 8 dragons in the World of Ruin. Intended for racing.",
         forced_flags=["worringtriad"],
         prohibited_flags={"j", "airship", "alasdraco", "thescenarionottaken"}),
]

NORMAL_FLAGS = [
    # Flags
    Flag(name='b',
         description='fix_exploits',
         long_description='Make the game more balanced by removing known exploits.',
         category="flags",
         inputtype="boolean"),
    Flag(name='c',
         description='random_palettes_and_names',
         long_description='Randomize palettes and names of various things.',
         category="flags",
         inputtype="boolean"),
    Flag(name='d',
         description='random_final_dungeon',
         long_description='Randomize final dungeon.',
         category="flags",
         inputtype="boolean"),
    Flag(name='e',
         description='random_espers',
         long_description='Randomize esper spells and levelup bonuses.',
         category="flags",
         inputtype="boolean"),
    Flag(name='f',
         description='random_formations',
         long_description='Randomize enemy formations.',
         category="flags",
         inputtype="boolean"),
    Flag(name='g',
         description='random_dances',
         long_description='Randomize dances.',
         category="flags",
         inputtype="boolean"),
    Flag(name='h',
         description='random_final_party',
         long_description='Your party in the Final Kefka fight will be random.',
         category="flags",
         inputtype="boolean"),
    Flag(name='i',
         description='random_items',
         long_description='Randomize the stats of equippable items.',
         category="flags",
         inputtype="boolean"),
    Flag(name='j',
         description='randomize_forest',
         long_description='Randomize the phantom forest.',
         category="flags",
         inputtype="boolean"),
    Flag(name='k',
         description='random_clock',
         long_description='Randomize the clock in Zozo.',
         category="flags",
         inputtype="boolean"),
    Flag(name='l',
         description='random_blitz',
         long_description='Randomize blitz inputs.',
         category="flags",
         inputtype="boolean"),
    Flag(name='m',
         description='random_enemy_stats',
         long_description='Randomize enemy stats.',
         category="flags",
         inputtype="boolean"),
    Flag(name='n',
         description='random_window',
         long_description='Randomize window background colors.',
         category="flags",
         inputtype="boolean"),
    Flag(name='o',
         description='shuffle_commands',
         long_description="Shuffle characters' in-battle commands.",
         category="flags",
         inputtype="boolean"),
    Flag(name='p',
         description='random_animation_palettes',
         long_description='Randomize the palettes of spells and weapon animations.',
         category="flags",
         inputtype="boolean"),
    Flag(name='q',
         description='random_character_stats',
         long_description='Randomize what equipment each character can wear and character stats.',
         category="flags",
         inputtype="boolean"),
    Flag(name='r',
         description='shuffle_wor',
         long_description='Randomize character locations in the world of ruin.',
         category="flags",
         inputtype="boolean"),
    Flag(name='s',
         description='swap_sprites',
         long_description='Swap character graphics around.',
         category="flags",
         inputtype="boolean"),
    Flag(name='t',
         description='random_treasure',
         long_description='Randomize treasure including chests, colosseum, shops, and enemy drops.',
         category="flags",
         inputtype="boolean"),
    Flag(name='u',
         description='random_zerker',
         long_description='Umaro risk. (Random character will be berserk)',
         category="flags",
         inputtype="boolean"),
    Flag(name='w',
         description='replace_commands',
         long_description='Generate new commands for characters,replacing old commands.',
         category="flags",
         inputtype="boolean"),
    Flag(name='y',
         description='randomize_magicite',
         long_description='Shuffle magicite locations.',
         category="flags",
         inputtype="boolean"),
    Flag(name='z',
         description='sprint',
         long_description='Always have "Sprint Shoes" effect.',
         category="flags",
         inputtype="boolean"),

    # Sprite codes
    Flag(name='bravenudeworld',
         description="TINA PARTY MODE",
         long_description="All characters use the Esper Terra sprite.",
         category="sprite",
         inputtype="boolean"),
    Flag(name='kupokupo',
         description="MOOGLE MODE",
         long_description="All party members are moogles except Mog. With partyparty, "
                          "all characters are moogles, except Mog, Esper Terra, and Imps.",
         category="sprite",
         inputtype="boolean"),
    Flag(name='makeover',
         description="SPRITE REPLACEMENT MODE",
         long_description="Some sprites are replaced with new ones (like Cecil or Zero Suit Samus).",
         category="sprite",
         inputtype="boolean"),
    Flag(name='partyparty',
         description="CRAZY PARTY MODE",
         long_description="Kefka, Trooper, Banon, Leo, Ghost, Merchant, Esper Terra, "
                          "and Soldier are included in the pool of sprite randomization",
         category="sprite",
         inputtype="boolean"),
    Flag(name='quikdraw',
         description="QUIKDRAW MODE",
         long_description="All characters look like imperial soldiers, and none of them have Gau's Rage skill.",
         category="sprite",
         inputtype="boolean"),

    # Aesthetic codes
    Flag(name='alasdraco',
         description="JAM UP YOUR OPERA MODE",
         long_description="Randomizes various aesthetic elements of the Opera.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='bingoboingo',
         description="BINGO BONUS",
         long_description="Generates a Bingo table with various game elements to witness and check off. "
                          "The ROM does not interact with the bingo board.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='capslockoff',
         description="Mixed Case Names Mode",
         long_description="Names use whatever capitalization is in the name lists instead of all caps.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='johnnyachaotic',
         description="MUSIC MANGLING MODE",
         long_description="Randomizes music with no regard to what would make sense in a given location.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='johnnydmad',
         description="MUSIC REPLACEMENT MODE",
         long_description="Randomizes music with regard to what would make sense in a given location.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='nicerpoison',
         description="LOW PIXELATION POISON MODE",
         long_description="Drastically reduces the pixelation effect of poison when in dungeons.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='notawaiter',
         description="CUTSCENE SKIPS",
         long_description="Up to Kefka at Narshe, the vast majority of mandatory cutscenes are completely removed. "
                          "Optional cutscenes are not removed.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='remonsterate',
         description="MONSTER SPRITE REPLACEMENT MODE",
         long_description="Replaces monster sprites with sprites from other games. "
                          "Requires sprites in the remonstrate\\sprites folder. May introduce sketch glitching.",
         category="aesthetic",
         inputtype="boolean"),
    Flag(name='removeflashing',
         description="NOT SO FLASHY MODE",
         long_description="Removes most white flashing effects from the game, such as Bum Rush.",
         category="aesthetic",
         inputtype="boolean"),

    # battle codes
    Flag(name='collateraldamage',
         description="ITEM BREAK MODE",
         long_description="All pieces of equipment break for spells. Characters only have the Fight and "
                          "Item commands, and enemies will use items drastically more often than usual.",
         category="battle",
         inputtype="boolean"),
    Flag(name='cursepower',
         description="CHANGE CURSED SHIELD MODE",
         long_description="Set the number of battles required to uncurse a Cursed Shield. (Vanilla = 255, 0 = Random)",
         category="battle",
         inputtype="integer",
         default_value="255",
         maximum_value=255),
    Flag(name='dancelessons',
         description="NO DANCE FAILURES",
         long_description="Removes the 50% chance that dances will fail when used on a different terrain.",
         category="battle",
         inputtype="boolean"),
    Flag(name='dancingmaduin',
         description="RESTRICTED ESPERS MODE",
         long_description="Restricts Esper usage such that most Espers can only be equipped by one character. "
                          "Also usually changes what spell the Paladin Shld teaches.",
         category="battle",
         inputtype="boolean"),
    Flag(name='darkworld',
         description="SLASHER'S DELIGHT MODE",
         long_description="Drastically increases the difficulty of the seed, akin to a hard mode. "
                          "Mostly meant to be used in conjunction with the madworld flag.",
         category="battle",
         inputtype="boolean"),
    Flag(name='easymodo',
         description="EASY MODE",
         long_description="All enemies have 1 HP.",
         category="battle",
         inputtype="boolean"),
    Flag(name='electricboogaloo',
         description="WILD ITEM BREAK MODE",
         long_description="Increases the list of spells that items can break and proc for from just "
                          "magic and some summons to include almost any skill.",
         category="battle",
         inputtype="boolean"),
    Flag(name='expboost',
         description="MULTIPLIED EXP MODE",
         long_description="All battles will award multiplied exp.",
         category="battle",
         inputtype="float2",
         default_value="1.00"),
    Flag(name='gpboost',
         description="MULTIPLIED GP MODE",
         long_description="All battles will award multiplied gp.",
         category="battle",
         inputtype="float2",
         default_value="1.00"),
    Flag(name='lessfanatical',
         description="EASY FANATICS TOWER MODE",
         long_description="Disables forced magic command in Fanatic's Tower.",
         category="battle",
         inputtype="boolean"),
    Flag(name='madworld',
         description="TIERS FOR FEARS MODE",
         long_description='Creates a "true tierless" seed, with enemies having a higher degree of '
                          'randomization and shops being very randomized as well.',
         category="battle",
         inputtype="boolean"),
    Flag(name='masseffect',
         description="WILD EQUIPMENT EFFECT MODE",
         long_description="Increases the number of rogue effects on equipment by a large amount.",
         category="battle",
         inputtype="boolean"),
    Flag(name='mpboost',
         description="MULTIPLIED MP MODE",
         long_description="All battles will award multiplied magic points.",
         category="battle",
         inputtype="float2",
         default_value="1.00"),
    Flag(name='nobreaks',
         description="NO ITEM BREAKS MODE",
         long_description="Causes no items to break for spell effects.",
         category="battle",
         inputtype="boolean"),
    Flag(name='norng',
         description="NO RNG MODE",
         long_description="Almost all calls to the RNG are removed, and actions are much less random as a result.",
         category="battle",
         inputtype="boolean"),
    Flag(name='playsitself',
         description="AUTOBATTLE MODE",
         long_description="All characters will act automatically, in a manner similar to "
                          "when Coliseum fights are fought.",
         category="battle",
         inputtype="boolean"),
    Flag(name='randombosses',
         description="RANDOM BOSSES MODE",
         long_description="Causes boss skills to be randomized similarly to regular enemy skills. "
                          "Boss skills can change to similarly powerful skills.",
         category="battle",
         inputtype="boolean"),
    Flag(name='rushforpower',
         description="OLD VARGAS FIGHT MODE",
         long_description="Reverts the Vargas fight to only require that Vargas take any "
                          "damage to begin his second phase.",
         category="battle",
         inputtype="boolean"),
    Flag(name='swdtechspeed',
         description="CHANGE SWDTECH SPEED MODE",
         long_description="Alters the speed at which the SwdTech bar moves.",
         category="battle",
         inputtype="combobox",
         choices=("Fastest", "Faster", "Fast", "Vanilla", "Random"),
         default_value="Vanilla",
         default_index=3),
    Flag(name='unbreakable',
         description="UNBREAKABLE ITEMS MODE",
         long_description="Causes all items to be indestructible when broken for a spell.",
         category="battle",
         inputtype="boolean"),

    # field codes
    Flag(name='bsiab',
         description="UNBALANCED MONSTER CHESTS MODE",
         long_description="Greatly increases the variance of monster-in-a-box encounters and removes "
                          "some sanity checks, allowing them to be much more difficult and volatile",
         category="field",
         inputtype="boolean"),
    Flag(name='cursedencounters',
         description="EXPANDED ENCOUNTERS MODE",
         long_description="Increases all zones to have 16 possible enemy encounters.",
         category="field",
         inputtype="boolean"),
    Flag(name='dearestmolulu',
         description="ENCOUNTERLESS MODE",
         long_description="No random encounters occur. Items that alter encounter rates increase them. "
                          "EXP flag recommended",
         category="field",
         inputtype="boolean"),
    Flag(name='fightclub',
         description="MORE LIKE COLI-DON'T-SEE-'EM",
         long_description="Does not allow you to see the coliseum rewards before betting, "
                          "but you can often run from the coliseum battles to keep your item.",
         category="field",
         inputtype="boolean"),
    Flag(name='mimetime',
         description='ALTERNATE GOGO MODE',
         long_description="Gogo will be hidden somewhere in the World of Ruin disguised as another character. "
                          "Bring that character to him to recruit him.",
         category="field",
         inputtype="boolean"),
    Flag(name='morefanatical',
         description='HORROR FANATICS TOWER',
         long_description="Fanatic's Tower is even more confusing than usual.",
         category="field",
         inputtype="boolean"),
    Flag(name='nomiabs',
         description='NO MIAB MODE',
         long_description="Chests will never have monster encounters in them.",
         category="field",
         inputtype="boolean"),
    Flag(name='questionablecontent',
         description="RIDDLER MODE",
         long_description="When items have significant differences from vanilla, a question mark "
                          "is appended to the item's name, including in shop menus.",
         category="field",
         inputtype="boolean"),
    Flag(name='randomboost',
         description="RANDOM BOOST MODE",
         long_description="Prompts for a multiplier, increasing the range of randomization. (0=uniform randomness)",
         category="field",
         inputtype="integer",
         default_value="0"),
    Flag(name='worringtriad',
         description="START IN WOR",
         long_description="The player will start in the World of Ruin, with all of the World of Balance "
                          "treasure chests, along with a guaranteed set of items, and more Lores.",
         category="field",
         inputtype="boolean"),

    # character codes
    Flag(name='allcombos',
         description="ALL COMBOS MODE",
         long_description="All skills that get replaced with something are replaced with combo skills.",
         category="characters",
         inputtype="boolean"),
    Flag(name='canttouchthis',
         description="INVINCIBILITY",
         long_description="All characters have 255 Defense and 255 Magic Defense, as well as 128 Evasion "
                          "and Magic Evasion.",
         category="characters",
         inputtype="boolean"),
    Flag(name='desperation',
         description="DESPERATION MODE",
         long_description="Guarantees one character will have R-Limit, and greatly increases the chance "
                          "of having desperation attacks as commands.",
         category="characters",
         inputtype="boolean"),
    Flag(name='endless9',
         description="ENDLESS NINE MODE",
         long_description="All R-[skills] are automatically changed to 9x[skills]. W-[skills] will become 8x[skills].",
         category="characters",
         inputtype="boolean"),
    Flag(name='mementomori',
         description="INNATE RELIC MODE",
         long_description="Number of characters that begin with an innate relic ability.",
         category="characters",
         inputtype="combobox",
         choices=("Random", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"),
         default_value="0",
         default_index=1),
    Flag(name='metronome',
         description="R-CHAOS MODE",
         long_description="All characters have Fight, R-Chaos, Magic, and Item as their skillset, "
                          "except for the Mime, who has Mimic instead of Fight, and the Berserker, "
                          "who only has R-Chaos.",
         category="characters",
         inputtype="boolean"),
    Flag(name='naturalmagic',
         description="NATURAL MAGIC MODE",
         long_description="No Espers or equipment will teach spells. The only way for characters to "
                          "learn spells is through leveling up, if they have their own innate magic list.",
         category="characters",
         inputtype="boolean"),
    Flag(name='naturalstats',
         description="NATURAL STATS MODE",
         long_description="No Espers will grant stat bonuses upon leveling up.",
         category="characters",
         inputtype="boolean"),
    Flag(name='nocombos',
         description="NO COMBOS MODE",
         long_description="There will be no combo(dual) skills.",
         category="characters",
         inputtype="boolean"),
    Flag(name='replaceeverything',
         description="REPLACE ALL SKILLS MODE",
         long_description="All vanilla skills that can be replaced, are replaced.",
         category="characters",
         inputtype="boolean"),
    Flag(name='supernatural',
         description="SUPER NATURAL MAGIC MODE",
         long_description="Makes it so that any character with the Magic command will have natural magic.",
         category="characters",
         inputtype="boolean"),
    Flag(name='suplexwrecks',
         description="SUPLEX MODE",
         long_description="All characters use the Sabin sprite, have a name similar to Sabin, have the "
                          "Blitz and Suplex commands, and can hit every enemy with Suplex.",
         category="characters",
         inputtype="boolean"),

    # gamebreaking codes

    Flag(name='airship',
         description="AIRSHIP MODE",
         long_description="The player can access the airship after leaving Narshe, or from any chocobo stable. "
                          "Doing events out of order can cause softlocks.",
         category="gamebreaking",
         inputtype="boolean"),
    Flag(name='equipanything',
         description="EQUIP ANYTHING MODE",
         long_description="Items that are not equippable normally can now be equipped as weapons or shields. "
                          "These often give strange defensive stats or weapon animations.",
         category="gamebreaking",
         inputtype="boolean"),
    Flag(name='sketch',
         description="ENABLE SKETCH GLITCH",
         long_description="Enables sketch bug. Not recommended unless you know what you are doing.",
         category="gamebreaking",
         inputtype="boolean"),

    # experimental codes
    Flag(name='strangejourney',
         description="BIZARRE ADVENTURE",
         long_description="A prototype entrance randomizer, similar to the ancientcave mode. "
                          "Includes all maps and event tiles, and is usually extremely hard to beat by itself.",
         category="experimental",
         inputtype="boolean"),
    Flag(name='thescenarionottaken',
         description='DIVERGENT PATHS MODE',
         long_description="Changes the way the 3 scenarios are split up, to resemble PowerPanda's "
                          "'Divergent Paths' mod.",
         category="experimental",
         inputtype="boolean"),

    # beta codes

]

# these are all sprite related codes
MAKEOVER_MODIFIER_FLAGS = [
    Flag(name='novanilla',
         description="COMPLETE MAKEOVER MODE",
         long_description="Same as 'makeover' except sprites from the vanilla game are guaranteed "
                          "not to appear.",
         category="sprite",
         inputtype="boolean"),
    Flag(name='frenchvanilla',
         description="EQUAL RIGHTS MAKEOVER MODE",
         long_description="Same as 'makeover' except sprites from the vanilla game are selected "
                          "with equal weight to new sprites rather than some being guaranteed to appear.",
         category="sprite",
         inputtype="boolean"),
    Flag(name='cloneparty',
         description="CLONE COSPLAY MAKEOVER MODE",
         long_description="Same as 'makeover' except instead of avoiding choosing different "
                          "versions of the same character, it actively tries to do so.",
         category="sprite",
         inputtype="boolean")
]
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
                      description="NO {mg.upper()} ALLOWED MODE",
                      long_description="Do not select {mg} sprites.",
                      category="spriteCategories",
                      inputtype="boolean")
            MAKEOVER_MODIFIER_FLAGS.extend([
                Flag(name=mg,
                     description="CUSTOM {mg.upper()} FREQUENCY MODE",
                     long_description="Adjust probability of selecting " + mg + " sprites.",
                     category="spriteCategories",
                     inputtype="combobox",
                     choices=("Normal", "No", "Hate", "Like", "Only"),
                     default_value="Normal",
                     default_index=0)])
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
         inputtype="boolean"),
    Flag(name='speedcave',
         description="SPEED CAVE MODE",
         long_description="",
         category="cave",
         inputtype="boolean"),
    Flag(name='racecave',
         description="RACE CAVE MODE",
         long_description="",
         category="cave",
         inputtype="boolean"),
]

SPECIAL_FLAGS = [
    Flag(name='christmas',
         description='CHIRSTMAS MODE',
         long_description='',
         category='holiday',
         inputtype="boolean"),
    Flag(name='halloween',
         description="ALL HALLOWS' EVE MODE",
         long_description='',
         category='holiday',
         inputtype="boolean")
]

BETA_FLAGS = [

]

ALL_FLAGS = NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS + CAVE_FLAGS + SPECIAL_FLAGS

Options_ = Options(ALL_MODES[0])

Use_new_randomizer = True
