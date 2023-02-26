import re
from dataclasses import dataclass, field
from typing import List, Set, Union


@dataclass(frozen=True)
class Mode:
    name: str
    description: str
    forced_flags: List[str] = field(default_factory=list)
    # prohibited_codes: List[str] = field(default_factory=list)
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
        if re.search(r'\b' + re.escape(name) + r":", flag_string):
            string_after_key = flag_string[flag_string.index(name + ":") + len(name + ":"):]
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
        elif re.search(r'\b' + re.escape(name) + r"\b", flag_string):
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
        if len(name) == 1 and invert_simple_flags:
            return True, True, re.sub(r'\b' + re.escape(name) + r'\b',
                                      '',
                                      flag_string,
                                      re.IGNORECASE)

        return False, False, flag_string


@dataclass
class Options:
    mode: Mode
    active_flags = {}
    shuffle_commands: bool = field(init=False, default=False)
    replace_commands: bool = field(init=False, default=False)
    sprint: bool = field(init=False, default=False)
    fix_exploits: bool = field(init=False, default=False)
    random_enemy_stats: bool = field(init=False, default=False)
    random_palettes_and_names: bool = field(init=False, default=False)
    random_items: bool = field(init=False, default=False)
    random_character_stats: bool = field(init=False, default=False)
    random_espers: bool = field(init=False, default=False)
    random_treasure: bool = field(init=False, default=False)
    random_zerker: bool = field(init=False, default=False)
    random_blitz: bool = field(init=False, default=False)
    random_window: bool = field(init=False, default=False)
    random_formations: bool = field(init=False, default=False)
    swap_sprites: bool = field(init=False, default=False)
    random_animation_palettes: bool = field(init=False, default=False)
    random_final_dungeon: bool = field(init=False, default=False)
    random_dances: bool = field(init=False, default=False)
    random_clock: bool = field(init=False, default=False)
    shuffle_wor: bool = field(init=False, default=False)
    randomize_forest: bool = field(init=False, default=False)
    randomize_magicite: bool = field(init=False, default=False)
    random_final_party: bool = field(init=False, default=False)

    def is_flag_active(self, flag_name: str):
        if flag_name in self.active_flags.keys():
            return True
        return False

    def is_any_flag_active(self, flag_names: List[str]):
        for flag in flag_names:
            if flag in self.active_flags.keys():
                return True
        return False

    def get_flag_value(self, flag_name: str):
        try:
            return self.active_flags[flag_name]
        except KeyError:
            return None

    def activate_flag(self, flag_name: str, flag_value=None):
        for flag in ALL_FLAGS:
            if flag.name == flag_name:
                self.active_flags[flag_name] = flag_value
                if flag in MAKEOVER_MODIFIER_FLAGS:
                    self.activate_flag("makeover")
                if flag in RESTRICTED_VANILLA_SPRITE_FLAGS:
                    self.activate_flag("frenchvanilla")
                return

    def activate_from_string(self, flag_string):
        s = ""
        flags = read_Options_from_string(flag_string, self.mode)

        for flag in flags:
            # Detect incompatible and prohibited flags
            if flag.name in self.mode.prohibited_flags:
                # The flag is prohibited. Notify the user and do not activate it.
                print("The flag '" + flag.name + "' has been deactivated. It is incompatible with " +
                      self.mode.name + ".")
                continue
            if flag.name == 'sketch' and [f for f in flags if f.name == 'remonsterate']:
                print("The flag '" + flag.name + "' has been deactivated. It is incompatible with remonsterate.")
                continue

            if len(flag.name) > 1:
                if not flag.category == 'spriteCategories':
                    s += f"SECRET CODE: {flag.description} ACTIVATED\n"
                else:
                    s += f"SECRET CODE: {str(flag.value).upper()} {str(flag.name).upper()} MODE ACTIVATED\n"
            self.activate_flag(flag.name, flag.value)

        for flag in [f for f in self.mode.forced_flags if not self.is_flag_active(f)]:
            self.activate_flag(flag)
        if self.is_flag_active('strangejourney'):
            self.activate_flag('notawaiter')

        return s


def read_Options_from_string(flag_string: str, mode: Union[Mode, str]):
    flags = set()

    if isinstance(mode, str):
        mode = [m for m in ALL_MODES if m.name == mode][0]

    for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
        if len(flag_string) == 0:
            break
        found, value, flag_string = flag.remove_from_string(flag_string, mode)
        if found:
            flag.value = value
            flags.add(flag)

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
         inputtype="checkbox"),
    Flag(name='c',
         description='random_palettes_and_names',
         long_description='Randomize palettes and names of various things.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='d',
         description='random_final_dungeon',
         long_description='Randomize final dungeon.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='e',
         description='random_espers',
         long_description='Randomize esper spells and levelup bonuses.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='f',
         description='random_formations',
         long_description='Randomize enemy formations.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='g',
         description='random_dances',
         long_description='Randomize dances.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='h',
         description='random_final_party',
         long_description='Your party in the Final Kefka fight will be random.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='i',
         description='random_items',
         long_description='Randomize the stats of equippable items.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='j',
         description='randomize_forest',
         long_description='Randomize the phantom forest.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='k',
         description='random_clock',
         long_description='Randomize the clock in Zozo.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='l',
         description='random_blitz',
         long_description='Randomize blitz inputs.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='m',
         description='random_enemy_stats',
         long_description='Randomize enemy stats.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='n',
         description='random_window',
         long_description='Randomize window background colors.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='o',
         description='shuffle_commands',
         long_description="Shuffle characters' in-battle commands.",
         category="flags",
         inputtype="checkbox"),
    Flag(name='p',
         description='random_animation_palettes',
         long_description='Randomize the palettes of spells and weapon animations.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='q',
         description='random_character_stats',
         long_description='Randomize what equipment each character can wear and character stats.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='r',
         description='shuffle_wor',
         long_description='Randomize character locations in the world of ruin.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='s',
         description='swap_sprites',
         long_description='Swap character graphics around.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='t',
         description='random_treasure',
         long_description='Randomize treasure including chests, colosseum, shops, and enemy drops.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='u',
         description='random_zerker',
         long_description='Umaro risk. (Random character will be berserk)',
         category="flags",
         inputtype="checkbox"),
    Flag(name='w',
         description='replace_commands',
         long_description='Generate new commands for characters,replacing old commands.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='y',
         description='randomize_magicite',
         long_description='Shuffle magicite locations.',
         category="flags",
         inputtype="checkbox"),
    Flag(name='z',
         description='sprint',
         long_description='Always have "Sprint Shoes" effect.',
         category="flags",
         inputtype="checkbox"),

    # Sprite codes
    Flag(name='bravenudeworld',
         description="TINA PARTY MODE",
         long_description="All characters use the Esper Terra sprite.",
         category="sprite",
         inputtype="checkbox"),
    Flag(name='makeover',
         description="SPRITE REPLACEMENT MODE",
         long_description="Some sprites are replaced with new ones (like Cecil or Zero Suit Samus).",
         category="sprite",
         inputtype="checkbox"),
    Flag(name='kupokupo',
         description="MOOGLE MODE",
         long_description="All party members are moogles except Mog. With partyparty, "
                          "all characters are moogles, except Mog, Esper Terra, and Imps.",
         category="sprite",
         inputtype="checkbox"),
    Flag(name='partyparty',
         description="CRAZY PARTY MODE",
         long_description="Kefka, Trooper, Banon, Leo, Ghost, Merchant, Esper Terra, "
                          "and Soldier are included in the pool of sprite randomization",
         category="sprite",
         inputtype="checkbox"),
    Flag(name='quikdraw',
         description="QUIKDRAW MODE",
         long_description="All characters look like imperial soldiers, and none of them have Gau's Rage skill.",
         category="sprite",
         inputtype="checkbox"),

    # Aesthetic codes
    Flag(name='alasdraco',
         description="JAM UP YOUR OPERA MODE",
         long_description="Randomizes various aesthetic elements of the Opera.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='bingoboingo',
         description="BINGO BONUS",
         long_description="Generates a Bingo table with various game elements to witness and check off. "
                          "The ROM does not interact with the bingo board.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='capslockoff',
         description="Mixed Case Names Mode",
         long_description="Names use whatever capitalization is in the name lists instead of all caps.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='johnnydmad',
         description="MUSIC REPLACEMENT MODE",
         long_description="Randomizes music with regard to what would make sense in a given location.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='johnnyachaotic',
         description="MUSIC MANGLING MODE",
         long_description="Randomizes music with no regard to what would make sense in a given location.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='notawaiter',
         description="CUTSCENE SKIPS",
         long_description="Up to Kefka at Narshe, the vast majority of mandatory cutscenes are completely removed. "
                          "Optional cutscenes are not removed.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='removeflashing',
         description="NOT SO FLASHY MODE",
         long_description="Removes most white flashing effects from the game, such as Bum Rush.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='nicerpoison',
         description="LOW PIXELATION POISON MODE",
         long_description="Drastically reduces the pixelation effect of poison when in dungeons.",
         category="aesthetic",
         inputtype="checkbox"),
    Flag(name='remonsterate',
         description="MONSTER SPRITE REPLACEMENT MODE",
         long_description="Replaces monster sprites with sprites from other games. "
                          "Requires sprites in the remonstrate\\sprites folder.",
         category="aesthetic",
         inputtype="checkbox"),

    # battle codes
    Flag(name='electricboogaloo',
         description="WILD ITEM BREAK MODE",
         long_description="Increases the list of spells that items can break and proc for from just "
                          "magic and some summons to include almost any skill.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='collateraldamage',
         description="ITEM BREAK MODE",
         long_description="All pieces of equipment break for spells. Characters only have the Fight and "
                          "Item commands, and enemies will use items drastically more often than usual.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='masseffect',
         description="WILD EQUIPMENT EFFECT MODE",
         long_description="Increases the number of rogue effects on equipment by a large amount.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='randombosses',
         description="RANDOM BOSSES MODE",
         long_description="Causes boss skills to be randomized similarly to regular enemy skills. "
                          "Boss skills can change to similarly powerful skills.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='dancingmaduin',
         description="RESTRICTED ESPERS MODE",
         long_description="Restricts Esper usage such that most Espers can only be equipped by one character. "
                          "Also usually changes what spell the Paladin Shld teaches.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='darkworld',
         description="SLASHER'S DELIGHT MODE",
         long_description="Drastically increases the difficulty of the seed, akin to a hard mode. "
                          "Mostly meant to be used in conjunction with the madworld flag.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='easymodo',
         description="EASY MODE",
         long_description="All enemies have 1 HP.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='madworld',
         description="TIERS FOR FEARS MODE",
         long_description='Creates a "true tierless" seed, with enemies having a higher degree of '
                          'randomization and shops being very randomized as well.',
         category="battle",
         inputtype="checkbox"),
    Flag(name='playsitself',
         description="AUTOBATTLE MODE",
         long_description="All characters will act automatically, in a manner similar to "
                          "when Coliseum fights are fought.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='rushforpower',
         description="OLD VARGAS FIGHT MODE",
         long_description="Reverts the Vargas fight to only require that Vargas take any "
                          "damage to begin his second phase.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='norng',
         description="NO RNG MODE",
         long_description="Almost all calls to the RNG are removed, and actions are much less random as a result.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='expboost',
         description="MULTIPLIED EXP MODE",
         long_description="All battles will award multiplied exp.",
         category="battle",
         inputtype="float2"),
    Flag(name='gpboost',
         description="MULTIPLIED GP MODE",
         long_description="All battles will award multiplied gp.",
         category="battle",
         inputtype="float2"),
    Flag(name='mpboost',
         description="MULTIPLIED MP MODE",
         long_description="All battles will award multiplied magic points.",
         category="battle",
         inputtype="float2"),
    Flag(name='dancelessons',
         description="NO DANCE FAILURES",
         long_description="Removes the 50% chance that dances will fail when used on a different terrain.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='nobreaks',
         description="NO ITEM BREAKS MODE",
         long_description="Causes no items to break for spell effects.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='unbreakable',
         description="UNBREAKABLE ITEMS MODE",
         long_description="Causes all items to be indestructible when broken for a spell.",
         category="battle",
         inputtype="checkbox"),
    Flag(name='swdtechspeed',
         description="CHANGE SWDTECH SPEED MODE",
         long_description="Alters the speed at which the SwdTech bar moves.",
         category="battle",
         inputtype="combobox",
         choices=("Fastest", "Faster", "Fast", "Vanilla", "Random"),
         default_value="Vanilla",
         default_index=3),
    Flag(name='cursepower',
         description="CHANGE CURSED SHIELD MODE",
         long_description="Set the number of battles required to uncurse a Cursed Shield. (Vanilla = 255, 0 = Random)",
         category="battle",
         inputtype="integer",
         default_value="255",
         maximum_value=255),
    Flag(name='lessfanatical',
         description="EASY FANATICS TOWER MODE",
         long_description="Disables forced magic command in Fanatic's Tower.",
         category="battle",
         inputtype="checkbox"),

    # field codes
    Flag(name='fightclub',
         description="MORE LIKE COLI-DON'T-SEE-'EM",
         long_description="Does not allow you to see the coliseum rewards before betting, "
                          "but you can often run from the coliseum battles to keep your item.",
         category="field",
         inputtype="checkbox"),
    Flag(name='bsiab',
         description="UNBALANCED MONSTER CHESTS MODE",
         long_description="Greatly increases the variance of monster-in-a-box encounters and removes "
                          "some sanity checks, allowing them to be much more difficult and volatile",
         category="field",
         inputtype="checkbox"),
    Flag(name='mimetime',
         description='ALTERNATE GOGO MODE',
         long_description="Gogo will be hidden somewhere in the World of Ruin disguised as another character. "
                          "Bring that character to him to recruit him.",
         category="field",
         inputtype="checkbox"),
    Flag(name='dearestmolulu',
         description="ENCOUNTERLESS MODE",
         long_description="No random encounters occur. Items that alter encounter rates increase them. "
                          "EXP flag recommended",
         category="field",
         inputtype="checkbox"),
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
         inputtype="checkbox"),
    Flag(name='questionablecontent',
         description="RIDDLER MODE",
         long_description="When items have significant differences from vanilla, a question mark "
                          "is appended to the item's name, including in shop menus.",
         category="field",
         inputtype="checkbox"),
    Flag(name='nomiabs',
         description='NO MIAB MODE',
         long_description="Chests will never have monster encounters in them.",
         category="field",
         inputtype="checkbox"),
    Flag(name='cursedencounters',
         description="EXPANDED ENCOUNTERS MODE",
         long_description="Increases all zones to have 16 possible enemy encounters.",
         category="field",
         inputtype="checkbox"),
    Flag(name='morefanatical',
         description='HORROR FANATICS TOWER',
         long_description="Fanatic's Tower is even more confusing than usual.",
         category="field",
         inputtype="checkbox"),

    # character codes
    Flag(name='replaceeverything',
         description="REPLACE ALL SKILLS MODE",
         long_description="All vanilla skills that can be replaced, are replaced.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='allcombos',
         description="ALL COMBOS MODE",
         long_description="All skills that get replaced with something are replaced with combo skills.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='nocombos',
         description="NO COMBOS MODE",
         long_description="There will be no combo(dual) skills.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='endless9',
         description="ENDLESS NINE MODE",
         long_description="All R-[skills] are automatically changed to 9x[skills]. W-[skills] will become 8x[skills].",
         category="characters",
         inputtype="checkbox"),
    Flag(name='supernatural',
         description="SUPER NATURAL MAGIC MODE",
         long_description="Makes it so that any character with the Magic command will have natural magic.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='canttouchthis',
         description="INVINCIBILITY",
         long_description="All characters have 255 Defense and 255 Magic Defense, as well as 128 Evasion "
                          "and Magic Evasion.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='naturalstats',
         description="NATURAL STATS MODE",
         long_description="No Espers will grant stat bonuses upon leveling up.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='metronome',
         description="R-CHAOS MODE",
         long_description="All characters have Fight, R-Chaos, Magic, and Item as their skillset, "
                          "except for the Mime, who has Mimic instead of Fight, and the Berserker, "
                          "who only has R-Chaos.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='naturalmagic',
         description="NATURAL MAGIC MODE",
         long_description="No Espers or equipment will teach spells. The only way for characters to "
                          "learn spells is through leveling up, if they have their own innate magic list.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='suplexwrecks',
         description="SUPLEX MODE",
         long_description="All characters use the Sabin sprite, have a name similar to Sabin, have the "
                          "Blitz and Suplex commands, and can hit every enemy with Suplex.",
         category="characters",
         inputtype="checkbox"),
    Flag(name='desperation',
         description="DESPERATION MODE",
         long_description="Guarantees one character will have R-Limit, and greatly increases the chance "
                          "of having desperation attacks as commands.",
         category="characters",
         inputtype="checkbox"),

    # gamebreaking codes

    Flag(name='airship',
         description="AIRSHIP MODE",
         long_description="The player can access the airship after leaving Narshe, or from any chocobo stable. "
                          "Doing events out of order can cause softlocks.",
         category="gamebreaking",
         inputtype="checkbox"),
    Flag(name='sketch',
         description="ENABLE SKETCH GLITCH",
         long_description="Enables sketch bug. Not recommended unless you know what you are doing.",
         category="gamebreaking",
         inputtype="checkbox"),
    Flag(name='equipanything',
         description="EQUIP ANYTHING MODE",
         long_description="Items that are not equippable normally can now be equipped as weapons or shields. "
                          "These often give strange defensive stats or weapon animations.",
         category="gamebreaking",
         inputtype="checkbox"),

    # experimental codes
    Flag(name='strangejourney',
         description="BIZARRE ADVENTURE",
         long_description="A prototype entrance randomizer, similar to the ancientcave mode. "
                          "Includes all maps and event tiles, and is usually extremely hard to beat by itself.",
         category="experimental",
         inputtype="checkbox"),
    Flag(name='thescenarionottaken',
         description='DIVERGENT PATHS MODE',
         long_description="Changes the way the 3 scenarios are split up, to resemble PowerPanda's "
                          "'Divergent Paths' mod.",
         category="experimental",
         inputtype="checkbox"),

    # beta codes

]

# these are all sprite related codes
MAKEOVER_MODIFIER_FLAGS = [
    Flag(name='novanilla',
         description="COMPLETE MAKEOVER MODE",
         long_description="Same as 'makeover' except sprites from the vanilla game are guaranteed "
                          "not to appear.",
         category="sprite",
         inputtype="checkbox"),
    Flag(name='frenchvanilla',
         description="EQUAL RIGHTS MAKEOVER MODE",
         long_description="Same as 'makeover' except sprites from the vanilla game are selected "
                          "with equal weight to new sprites rather than some being guaranteed to appear.",
         category="sprite",
         inputtype="checkbox"),
    Flag(name='cloneparty',
         description="CLONE COSPLAY MAKEOVER MODE",
         long_description="Same as 'makeover' except instead of avoiding choosing different "
                          "versions of the same character, it actively tries to do so.",
         category="sprite",
         inputtype="checkbox")
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
                      inputtype="checkbox")
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
    except FileNotFoundError:
        pass
    return makeover_groups


# TODO: do this a better way
CAVE_FLAGS = [
    Flag(name='ancientcave',
         description="ANCIENT CAVE MODE",
         long_description="",
         category="cave",
         inputtype="checkbox"),
    Flag(name='speedcave',
         description="SPEED CAVE MODE",
         long_description="",
         category="cave",
         inputtype="checkbox"),
    Flag(name='racecave',
         description="RACE CAVE MODE",
         long_description="",
         category="cave",
         inputtype="checkbox"),
]

SPECIAL_FLAGS = [
    Flag(name='christmas',
         description='CHIRSTMAS MODE',
         long_description='',
         category='holiday',
         inputtype="checkbox"),
    Flag(name='halloween',
         description="ALL HALLOWS' EVE MODE",
         long_description='',
         category='holiday',
         inputtype="checkbox")
]

BETA_FLAGS = [

]

ALL_FLAGS = NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS + CAVE_FLAGS + SPECIAL_FLAGS

Options_ = Options(ALL_MODES[0])

Use_new_randomizer = True
