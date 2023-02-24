from dataclasses import dataclass, field
from typing import List, Set, Union
from appearance import get_makeover_groups


@dataclass(frozen=True)
class Mode:
    name: str
    description: str
    forced_codes: List[str] = field(default_factory=list)
    prohibited_codes: List[str] = field(default_factory=list)
    prohibited_flags: Set[str] = field(default_factory=set)


@dataclass(order=True, frozen=True)
class Flag:
    name: str
    attr: str
    description: str
    inputtype: str

    def __post_init__(self):
        object.__setattr__(self, 'name', self.name[0])


@dataclass(frozen=True)
class Code:
    name: str
    description: str
    long_description: str
    category: str
    inputtype: str
    key1: str = ''
    key2: str = ''
    choices: [str] = field(default_factory=list)

    def remove_from_string(self, s: str):
        name = self.name
        if name in s:
            if name + ":" in s:
                # A value was supplied, return the value
                string_after_key = s[s.index(name + ":") + len(name + ":"):]
                try:
                    value = string_after_key[:string_after_key.index(" ")]
                except ValueError:
                    # A space did not exist after the flag. Get the entire rest of the flag string.
                    value = string_after_key
                return True, value, s.replace(name + ":" + value, '')
            else:
                # No value was supplied, return True
                return True, True, s.replace(name, '')
        return False, False, s


@dataclass
class Options:
    mode: Mode
    active_codes = {}
    active_flags: Set[Flag] = field(default_factory=set)
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

    def is_code_active(self, code_name: str):
        if code_name in self.active_codes.keys():
            return True
        # for code in self.active_codes:
        #    if code.name == code_name:
        #        return True
        return False

    def is_any_code_active(self, code_names: List[str]):
        for code in code_names:
            if code in self.active_codes.keys():
                return True
        # for code in self.active_codes:
        #    if code.name in code_names:
        #        return True
        return False

    def get_code_value(self, code_name: str):
        try:
            return self.active_codes[code_name]
        except KeyError:
            return None

    def is_flag_active(self, flag_name: str):
        for flag in self.active_flags:
            if flag.name == flag_name:
                return True
        return False

    def activate_code(self, code_name: str, code_value=None):
        for code in ALL_CODES:
            if code.name == code_name:
                self.active_codes[code_name] = code_value
                if code in MAKEOVER_MODIFIER_CODES:
                    self.activate_code("makeover")
                if code in RESTRICTED_VANILLA_SPRITE_CODES:
                    self.activate_code("frenchvanilla")
                return

    def activate_flag(self, flag: Flag):
        self.active_flags.add(flag)
        setattr(self, flag.attr, True)

    def activate_from_string(self, flag_string):
        for code in self.mode.forced_codes:
            self.activate_code(code)

        s = ""
        flags, codes = read_Options_from_string(flag_string, self.mode)
        for code, value in codes.items():
            if code == 'sketch' and ('sketch' in codes.keys() and 'remonsterate' in codes.keys()):
                s += f"SECRET CODE: 'sketch' is not compatible with remonsterate code.\n"
                continue
            if code in self.mode.prohibited_codes:
                s += f"SECRET CODE: '{code}' is not compatible with {self.mode.name} mode.\n"
                continue
            for code_object in NORMAL_CODES + MAKEOVER_MODIFIER_CODES:
                if code_object.name == code:
                    if code_object.category == "spriteCategories":
                        s += f"SECRET CODE: {str(value).upper()} {str(code).upper()} MODE ACTIVATED\n"
                    else:
                        s += f"SECRET CODE: {code_object.description} ACTIVATED\n"
            self.activate_code(code, codes[code])

        if self.is_code_active('strangejourney'):
            self.activate_code('notawaiter')

        flags -= self.mode.prohibited_flags
        if not flags:
            flags = {f for f in ALL_FLAGS if f not in self.mode.prohibited_flags}

        for flag in flags:
            self.activate_flag(flag)

        return s


def read_Options_from_string(flag_string: str, mode: Union[Mode, str]):
    flags = set()
    codes = {}

    if isinstance(mode, str):
        mode = [m for m in ALL_MODES if m.name == mode][0]

    for code in NORMAL_CODES + MAKEOVER_MODIFIER_CODES:
        found, value, flag_string = code.remove_from_string(flag_string)
        if found:
            codes[code.name] = value

    if '-' in flag_string:
        print("NOTE: Using all flags EXCEPT the specified flags.")
        flags = {f for f in ALL_FLAGS if f.name not in flag_string}
    else:
        flags = {f for f in ALL_FLAGS if f.name in flag_string}

    flags -= mode.prohibited_flags
    if not flags:
        flags = {f for f in ALL_FLAGS if f not in mode.prohibited_flags}

    return flags, codes


ANCIENT_CAVE_PROHIBITED_CODES = [
    "airship",
    "alasdraco",
    "notawaiter",
    "strangejourney",
    "worringtriad",
    "thescenarionottaken",
    "mimetime"
]

ANCIENT_CAVE_PROHIBITED_FLAGS = {
    "d",
    "k",
    "r",
    "j",
}

ALL_MODES = [
    Mode(name="normal", description="Play through the normal story."),
    Mode(name="ancientcave",
         description="Play through a long randomized dungeon.",
         forced_codes=["ancientcave"],
         prohibited_codes=ANCIENT_CAVE_PROHIBITED_CODES,
         prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS),
    Mode(name="speedcave",
         description="Play through a medium-sized randomized dungeon.",
         forced_codes=["speedcave", "ancientcave"],
         prohibited_codes=ANCIENT_CAVE_PROHIBITED_CODES,
         prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS),
    Mode(name="racecave",
         description="Play through a short randomized dungeon.",
         forced_codes=["racecave", "speedcave", "ancientcave"],
         prohibited_codes=ANCIENT_CAVE_PROHIBITED_CODES,
         prohibited_flags=ANCIENT_CAVE_PROHIBITED_FLAGS),
    Mode(name="katn",
         description="Play the normal story up to Kefka at Narshe. Intended for racing.",
         prohibited_codes=["airship", "alasdraco", "worringtriad", "mimetime"],
         prohibited_flags={"d", "k", "r"}),
    # Static number of encounters on Lete River, No charm drops, Start with random Espers,
    # Curated enemy specials, Banned Baba Breath & Seize
    Mode(name="dragonhunt",
         description="Kill all 8 dragons in the World of Ruin. Intended for racing.",
         forced_codes=["worringtriad"],
         prohibited_codes=["airship", "alasdraco", "thescenarionottaken"],
         prohibited_flags={"j"}),
]

ALL_FLAGS = [
    Flag(name='b',
         attr='fix_exploits',
         description='Make the game more balanced by removing known exploits.',
         inputtype="checkbox"),
    Flag(name='c',
         attr='random_palettes_and_names',
         description='Randomize palettes and names of various things.',
         inputtype="checkbox"),
    Flag(name='d',
         attr='random_final_dungeon',
         description='Randomize final dungeon.',
         inputtype="checkbox"),
    Flag(name='e',
         attr='random_espers',
         description='Randomize esper spells and levelup bonuses.',
         inputtype="checkbox"),
    Flag(name='f',
         attr='random_formations',
         description='Randomize enemy formations.',
         inputtype="checkbox"),
    Flag(name='g',
         attr='random_dances',
         description='Randomize dances.',
         inputtype="checkbox"),
    Flag(name='h',
         attr='random_final_party',
         description='Your party in the Final Kefka fight will be random.',
         inputtype="checkbox"),
    Flag(name='i',
         attr='random_items',
         description='Randomize the stats of equippable items.',
         inputtype="checkbox"),
    Flag(name='j',
         attr='randomize_forest',
         description='Randomize the phantom forest.',
         inputtype="checkbox"),
    Flag(name='k',
         attr='random_clock',
         description='Randomize the clock in Zozo.',
         inputtype="checkbox"),
    Flag(name='l',
         attr='random_blitz',
         description='Randomize blitz inputs.',
         inputtype="checkbox"),
    Flag(name='m',
         attr='random_enemy_stats',
         description='Randomize enemy stats.',
         inputtype="checkbox"),
    Flag(name='n',
         attr='random_window',
         description='Randomize window background colors.',
         inputtype="checkbox"),
    Flag(name='o',
         attr='shuffle_commands',
         description="Shuffle characters' in-battle commands.",
         inputtype="checkbox"),
    Flag(name='p',
         attr='random_animation_palettes',
         description='Randomize the palettes of spells and weapon animations.',
         inputtype="checkbox"),
    Flag(name='q',
         attr='random_character_stats',
         description='Randomize what equipment each character can wear and character stats.',
         inputtype="checkbox"),
    Flag(name='r',
         attr='shuffle_wor',
         description='Randomize character locations in the world of ruin.',
         inputtype="checkbox"),
    Flag(name='s',
         attr='swap_sprites',
         description='Swap character graphics around.',
         inputtype="checkbox"),
    Flag(name='t',
         attr='random_treasure',
         description='Randomize treasure including chests, colosseum, shops, and enemy drops.',
         inputtype="checkbox"),
    Flag(name='u',
         attr='random_zerker',
         description='Umaro risk. (Random character will be berserk)',
         inputtype="checkbox"),
    Flag(name='w',
         attr='replace_commands',
         description='Generate new commands for characters,replacing old commands.',
         inputtype="checkbox"),
    Flag(name='y',
         attr='randomize_magicite',
         description='Shuffle magicite locations.',
         inputtype="checkbox"),
    Flag(name='z',
         attr='sprint',
         description='Always have "Sprint Shoes" effect.',
         inputtype="checkbox"),
]

NORMAL_CODES = [
    # Sprite codes
    Code(name='bravenudeworld',
         description="TINA PARTY MODE",
         long_description="All characters use the Esper Terra sprite.",
         category="sprite",
         inputtype="checkbox"),
    Code(name='makeover',
         description="SPRITE REPLACEMENT MODE",
         long_description="Some sprites are replaced with new ones (like Cecil or Zero Suit Samus).",
         category="sprite",
         inputtype="checkbox"),
    Code(name='kupokupo',
         description="MOOGLE MODE",
         long_description="All party members are moogles except Mog. With partyparty, "
                          "all characters are moogles, except Mog, Esper Terra, and Imps.",
         category="sprite",
         inputtype="checkbox"),
    Code(name='partyparty',
         description="CRAZY PARTY MODE",
         long_description="Kefka, Trooper, Banon, Leo, Ghost, Merchant, Esper Terra, "
                          "and Soldier are included in the pool of sprite randomization",
         category="sprite",
         inputtype="checkbox"),
    Code(name='quikdraw',
         description="QUIKDRAW MODE",
         long_description="All characters look like imperial soldiers, and none of them have Gau's Rage skill.",
         category="sprite",
         inputtype="checkbox"),

    # Aesthetic codes
    Code(name='alasdraco',
         description="JAM UP YOUR OPERA MODE",
         long_description="Randomizes various aesthetic elements of the Opera.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='bingoboingo',
         description="BINGO BONUS",
         long_description="Generates a Bingo table with various game elements to witness and check off. "
                          "The ROM does not interact with the bingo board.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='capslockoff',
         description="Mixed Case Names Mode",
         long_description="Names use whatever capitalization is in the name lists instead of all caps.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='johnnydmad',
         description="MUSIC REPLACEMENT MODE",
         long_description="Randomizes music with regard to what would make sense in a given location.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='johnnyachaotic',
         description="MUSIC MANGLING MODE",
         long_description="Randomizes music with no regard to what would make sense in a given location.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='notawaiter',
         description="CUTSCENE SKIPS",
         long_description="Up to Kefka at Narshe, the vast majority of mandatory cutscenes are completely removed. "
                          "Optional cutscenes are not removed.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='removeflashing',
         description="NOT SO FLASHY MODE",
         long_description="Removes most white flashing effects from the game, such as Bum Rush.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='nicerpoison',
         description="LOW PIXELATION POISON MODE",
         long_description="Drastically reduces the pixelation effect of poison when in dungeons.",
         category="aesthetic",
         inputtype="checkbox"),
    Code(name='remonsterate',
         description="MONSTER SPRITE REPLACEMENT MODE",
         long_description="Replaces monster sprites with sprites from other games. "
                          "Requires sprites in the remonstrate\\sprites folder.",
         category="aesthetic",
         inputtype="checkbox"),

    # battle codes
    Code(name='electricboogaloo',
         description="WILD ITEM BREAK MODE",
         long_description="Increases the list of spells that items can break and proc for from just "
                          "magic and some summons to include almost any skill.",
         category="battle",
         inputtype="checkbox"),
    Code(name='collateraldamage',
         description="ITEM BREAK MODE",
         long_description="All pieces of equipment break for spells. Characters only have the Fight and "
                          "Item commands, and enemies will use items drastically more often than usual.",
         category="battle",
         inputtype="checkbox"),
    Code(name='masseffect',
         description="WILD EQUIPMENT EFFECT MODE",
         long_description="Increases the number of rogue effects on equipment by a large amount.",
         category="battle",
         inputtype="checkbox"),
    Code(name='randombosses',
         description="RANDOM BOSSES MODE",
         long_description="Causes boss skills to be randomized similarly to regular enemy skills. "
                          "Boss skills can change to similarly powerful skills.",
         category="battle",
         inputtype="checkbox"),
    Code(name='dancingmaduin',
         description="RESTRICTED ESPERS MODE",
         long_description="Restricts Esper usage such that most Espers can only be equipped by one character. "
                          "Also usually changes what spell the Paladin Shld teaches.",
         category="battle",
         inputtype="checkbox"),
    Code(name='darkworld',
         description="SLASHER'S DELIGHT MODE",
         long_description="Drastically increases the difficulty of the seed, akin to a hard mode. "
                          "Mostly meant to be used in conjunction with the madworld code.",
         category="battle",
         inputtype="checkbox"),
    Code(name='easymodo',
         description="EASY MODE",
         long_description="All enemies have 1 HP.",
         category="battle",
         inputtype="checkbox"),
    Code(name='madworld',
         description="TIERS FOR FEARS MODE",
         long_description='Creates a "true tierless" seed, with enemies having a higher degree of '
                          'randomization and shops being very randomized as well.',
         category="battle",
         inputtype="checkbox"),
    Code(name='playsitself',
         description="AUTOBATTLE MODE",
         long_description="All characters will act automatically, in a manner similar to "
                          "when Coliseum fights are fought.",
         category="battle",
         inputtype="checkbox"),
    Code(name='rushforpower',
         description="OLD VARGAS FIGHT MODE",
         long_description="Reverts the Vargas fight to only require that Vargas take any "
                          "damage to begin his second phase.",
         category="battle",
         inputtype="checkbox"),
    Code(name='norng',
         description="NO RNG MODE",
         long_description="Almost all calls to the RNG are removed, and actions are much less random as a result.",
         category="battle",
         inputtype="checkbox"),
    Code(name='expboost',
         description="MULTIPLIED EXP MODE",
         long_description="All battles will award multiplied exp.",
         category="battle",
         inputtype="numberbox"),
    Code(name='gpboost',
         description="MULTIPLIED GP MODE",
         long_description="All battles will award multiplied gp.",
         category="battle",
         inputtype="numberbox"),
    Code(name='mpboost',
         description="MULTIPLIED MP MODE",
         long_description="All battles will award multiplied magic points.",
         category="battle",
         inputtype="numberbox"),
    Code(name='dancelessons',
         description="NO DANCE FAILURES",
         long_description="Removes the 50% chance that dances will fail when used on a different terrain.",
         category="battle",
         inputtype="checkbox"),
    Code(name='nobreaks',
         description="NO ITEM BREAKS MODE",
         long_description="Causes no items to break for spell effects.",
         category="battle",
         inputtype="checkbox"),
    Code(name='unbreakable',
         description="UNBREAKABLE ITEMS MODE",
         long_description="Causes all items to be indestructible when broken for a spell.",
         category="battle",
         inputtype="checkbox"),
    Code(name='swdtechspeed',
         description="CHANGE SWDTECH SPEED MODE",
         long_description="Alters the speed at which the SwdTech bar moves.",
         category="battle",
         inputtype="combobox",
         choices=("Fastest", "Faster", "Fast", "Vanilla", "Random")),
    Code(name='cursepower',
         description="CHANGE CURSED SHIELD MODE",
         long_description="Set the number of battles required to uncurse a Cursed Shield. (Vanilla = 256, 0 = Random)",
         category="battle",
         inputtype="numberbox"),
    Code(name='lessfanatical',
         description="EASY FANATICS TOWER MODE",
         long_description="Disables forced magic command in Fanatic's Tower.",
         category="battle",
         inputtype="checkbox"),

    # field codes
    Code(name='fightclub',
         description="MORE LIKE COLI-DON'T-SEE-'EM",
         long_description="Does not allow you to see the coliseum rewards before betting, "
                          "but you can often run from the coliseum battles to keep your item.",
         category="field",
         inputtype="checkbox"),
    Code(name='bsiab',
         description="UNBALANCED MONSTER CHESTS MODE",
         long_description="Greatly increases the variance of monster-in-a-box encounters and removes "
                          "some sanity checks, allowing them to be much more difficult and volatile",
         category="field",
         inputtype="checkbox"),
    Code(name='mimetime',
         description='ALTERNATE GOGO MODE',
         long_description="Gogo will be hidden somewhere in the World of Ruin disguised as another character. "
                          "Bring that character to him to recruit him.",
         category="field",
         inputtype="checkbox"),
    Code(name='dearestmolulu',
         description="ENCOUNTERLESS MODE",
         long_description="No random encounters occur. Items that alter encounter rates increase them. "
                          "EXP code recommended",
         category="field",
         inputtype="checkbox"),
    Code(name='randomboost',
         description="RANDOM BOOST MODE",
         long_description="Prompts for a multiplier, increasing the range of randomization. (0=uniform randomness)",
         category="field",
         inputtype="numberbox"),
    Code(name='worringtriad',
         description="START IN WOR",
         long_description="The player will start in the World of Ruin, with all of the World of Balance "
                          "treasure chests, along with a guaranteed set of items, and more Lores.",
         category="field",
         inputtype="checkbox"),
    Code(name='questionablecontent',
         description="RIDDLER MODE",
         long_description="When items have significant differences from vanilla, a question mark "
                          "is appended to the item's name, including in shop menus.",
         category="field",
         inputtype="checkbox"),
    Code(name='nomiabs',
         description='NO MIAB MODE',
         long_description="Chests will never have monster encounters in them.",
         category="field",
         inputtype="checkbox"),
    Code(name='cursedencounters',
         description="EXPANDED ENCOUNTERS MODE",
         long_description="Increases all zones to have 16 possible enemy encounters.",
         category="field",
         inputtype="checkbox"),
    Code(name='morefanatical',
         description='HORROR FANATICS TOWER',
         long_description="Fanatic's Tower is even more confusing than usual.",
         category="field",
         inputtype="checkbox"),

    # character codes
    Code(name='replaceeverything',
         description="REPLACE ALL SKILLS MODE",
         long_description="All vanilla skills that can be replaced, are replaced.",
         category="characters",
         inputtype="checkbox"),
    Code(name='allcombos',
         description="ALL COMBOS MODE",
         long_description="All skills that get replaced with something are replaced with combo skills.",
         category="characters",
         inputtype="checkbox"),
    Code(name='nocombos',
         description="NO COMBOS MODE",
         long_description="There will be no combo(dual) skills.",
         category="characters",
         inputtype="checkbox"),
    Code(name='endless9',
         description="ENDLESS NINE MODE",
         long_description="All R-[skills] are automatically changed to 9x[skills]. W-[skills] will become 8x[skills].",
         category="characters",
         inputtype="checkbox"),
    Code(name='supernatural',
         description="SUPER NATURAL MAGIC MODE",
         long_description="Makes it so that any character with the Magic command will have natural magic.",
         category="characters",
         inputtype="checkbox"),
    Code(name='canttouchthis',
         description="INVINCIBILITY",
         long_description="All characters have 255 Defense and 255 Magic Defense, as well as 128 Evasion "
                          "and Magic Evasion.",
         category="characters",
         inputtype="checkbox"),
    Code(name='naturalstats',
         description="NATURAL STATS MODE",
         long_description="No Espers will grant stat bonuses upon leveling up.",
         category="characters",
         inputtype="checkbox"),
    Code(name='metronome',
         description="R-CHAOS MODE",
         long_description="All characters have Fight, R-Chaos, Magic, and Item as their skillset, "
                          "except for the Mime, who has Mimic instead of Fight, and the Berserker, "
                          "who only has R-Chaos.",
         category="characters",
         inputtype="checkbox"),
    Code(name='naturalmagic',
         description="NATURAL MAGIC MODE",
         long_description="No Espers or equipment will teach spells. The only way for characters to "
                          "learn spells is through leveling up, if they have their own innate magic list.",
         category="characters",
         inputtype="checkbox"),
    Code(name='suplexwrecks',
         description="SUPLEX MODE",
         long_description="All characters use the Sabin sprite, have a name similar to Sabin, have the "
                          "Blitz and Suplex commands, and can hit every enemy with Suplex.",
         category="characters",
         inputtype="checkbox"),
    Code(name='desperation',
         description="DESPERATION MODE",
         long_description="Guarantees one character will have R-Limit, and greatly increases the chance "
                          "of having desperation attacks as commands.",
         category="characters",
         inputtype="checkbox"),

    # gamebreaking codes

    Code(name='airship',
         description="AIRSHIP MODE",
         long_description="The player can access the airship after leaving Narshe, or from any chocobo stable. "
                          "Doing events out of order can cause softlocks.",
         category="gamebreaking",
         inputtype="checkbox"),
    Code(name='sketch',
         description="ENABLE SKETCH GLITCH",
         long_description="Enables sketch bug. Not recommended unless you know what you are doing.",
         category="gamebreaking",
         inputtype="checkbox"),
    Code(name='equipanything',
         description="EQUIP ANYTHING MODE",
         long_description="Items that are not equippable normally can now be equipped as weapons or shields. "
                          "These often give strange defensive stats or weapon animations.",
         category="gamebreaking",
         inputtype="checkbox"),

    # experimental codes

    # Code(name='repairpalette',
    # "PALETTE REPAIR",
    # long_description="Used for testing changes to palette randomization. Not intended for actual play. "
    #                  "Cannot proceed past Banon's scenario.",
    # category="experimental",
    # "checkbox"),
    Code(name='strangejourney',
         description="BIZARRE ADVENTURE",
         long_description="A prototype entrance randomizer, similar to the ancientcave mode. "
                          "Includes all maps and event tiles, and is usually extremely hard to beat by itself.",
         category="experimental",
         inputtype="checkbox"),
    Code(name='thescenarionottaken',
         description='DIVERGENT PATHS MODE',
         long_description="Changes the way the 3 scenarios are split up, to resemble PowerPanda's "
                          "'Divergent Paths' mod.",
         category="experimental",
         inputtype="checkbox"),

    # beta codes

]

# these are all sprite related codes
MAKEOVER_MODIFIER_CODES = [
    Code(name='novanilla',
         description="COMPLETE MAKEOVER MODE",
         long_description="Same as 'makeover' except sprites from the vanilla game are guaranteed "
                          "not to appear.",
         category="sprite",
         inputtype="checkbox"),
    Code(name='frenchvanilla',
         description="EQUAL RIGHTS MAKEOVER MODE",
         long_description="Same as 'makeover' except sprites from the vanilla game are selected "
                          "with equal weight to new sprites rather than some being guaranteed to appear.",
         category="sprite",
         inputtype="checkbox"),
    Code(name='cloneparty',
         description="CLONE COSPLAY MAKEOVER MODE",
         long_description="Same as 'makeover' except instead of avoiding choosing different "
                          "versions of the same character, it actively tries to do so.",
         category="sprite",
         inputtype="checkbox")
]
RESTRICTED_VANILLA_SPRITE_CODES = []

# this is used for the makeover variation codes for sprites
# makeover_groups = ["anime", "boys", "generic", "girls", "kids", "pets", "potato", "custom"]
makeover_groups = None
try:
    makeover_groups = get_makeover_groups()
    for mg in makeover_groups:
        no = Code(name='no' + mg,
                  description="NO {mg.upper()} ALLOWED MODE",
                  long_description="Do not select {mg} sprites.",
                  category="spriteCategories",
                  inputtype="checkbox")
        MAKEOVER_MODIFIER_CODES.extend([
            Code(name=mg,
                 description="CUSTOM {mg.upper()} FREQUENCY MODE",
                 long_description="Adjust probability of selecting {mg} sprites.",
                 category="spriteCategories",
                 inputtype="combobox",
                 choices=("Normal", "No", "Hate", "Like", "Only"))])
        RESTRICTED_VANILLA_SPRITE_CODES.append(no)
except FileNotFoundError:
    pass

# TODO: do this a better way
CAVE_CODES = [
    Code(name='ancientcave',
         description="ANCIENT CAVE MODE",
         long_description="",
         category="cave",
         inputtype="checkbox"),
    Code(name='speedcave',
         description="SPEED CAVE MODE",
         long_description="",
         category="cave",
         inputtype="checkbox"),
    Code(name='racecave',
         description="RACE CAVE MODE",
         long_description="",
         category="cave",
         inputtype="checkbox"),
]

SPECIAL_CODES = [
    Code(name='christmas',
         description='CHIRSTMAS MODE',
         long_description='',
         category='holiday',
         inputtype="checkbox"),
    Code(name='halloween',
         description="ALL HALLOWS' EVE MODE",
         long_description='',
         category='holiday',
         inputtype="checkbox")
]

BETA_CODES = [

]

ALL_CODES = NORMAL_CODES + MAKEOVER_MODIFIER_CODES + CAVE_CODES + SPECIAL_CODES

Options_ = Options(ALL_MODES[0])

Use_new_randomizer = True
