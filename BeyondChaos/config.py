from configparser import ConfigParser, DuplicateSectionError, NoSectionError, NoOptionError
from pathlib import Path
import os

try:
    from sys import _MEIPASS

    TABLE_PATH = os.path.dirname(os.path.abspath(__file__))
except ImportError:
    TABLE_PATH = os.path.join(os.getcwd(), "tables")

VERSION = "CE-6.0.0"
BETA = False
VERSION_ROMAN = 'V BETA' if BETA else 'V'
DEFAULT_CONFIG = {
    "Version": {
        'core': VERSION
    }
}
CONFIG_PATH = Path(os.path.join(os.getcwd(), "config.ini"))

MD5HASHNORMAL = "e986575b98300f721ce27c180264d890"
MD5HASHTEXTLESS = "f08bf13a6819c421eee33ee29e640a1d"
MD5HASHTEXTLESS2 = "e0984abc9e5dd99e4bc54e8f9e0ff8d0"

# Supported preset names must be lowercase.
SUPPORTED_PRESETS = {
    'new player': 'b c e f g i n o p q r s t w y z alphalores informativemiss '
                  'magicnumbers mpparty nicerpoison questionablecontent regionofdoom relicmyhat '
                  'slowerbg tastetherainbow makeover partyparty alasdraco capslockoff johnnydmad '
                  'dancelessons lessfanatical expboost:2.0 gpboost:2.0 mpboost:2.0 '
                  'swdtechspeed:faster shadowstays ',
    'intermediate player': 'b c d e f g i j k m n o p q r s t u w y z alphalores '
                           'informativemiss magicnumbers mpparty nicerpoison questionablecontent '
                           'regionofdoom relicmyhat slowerbg tastetherainbow makeover partyparty '
                           'alasdraco capslockoff johnnydmad notawaiter remonsterate dancelessons '
                           'electricboogaloo lessfanatical swdtechspeed:faster shadowstays ',
    'advanced player': 'b c d e f g h i j k m n o p q r s t u w y z alphalores '
                       'informativemiss magicnumbers mpparty nicerpoison questionablecontent '
                       'regionofdoom relicmyhat slowerbg tastetherainbow makeover partyparty '
                       'alasdraco capslockoff johnnydmad notawaiter remonsterate dancelessons '
                       'electricboogaloo randombosses dancingmaduin:1 swdtechspeed:random '
                       'bsiab mimetime morefanatical mementomori:14',
    'chaotic player': 'b c d e f g h i j k m n o p q r s t u w y z alphalores informativemiss '
                      'magicnumbers mpparty nicerpoison questionablecontent regionofdoom relicmyhat '
                      'slowerbg tastetherainbow makeover partyparty alasdraco capslockoff johnnyachaotic '
                      'notawaiter remonsterate dancelessons electricboogaloo randombosses dancingmaduin:chaos '
                      'masseffect:med swdtechspeed:random bsiab mimetime randomboost:2 allcombos supernatural '
                      'mementomori:random thescenarionottaken',
    'race easy': 'b c d e f g i j k m n o p q r s t w y z alphalores informativemiss magicnumbers mpparty '
                 'nicerpoison questionablecontent regionofdoom relicmyhat slowerbg tastetherainbow makeover '
                 'partyparty capslockoff johnnydmad notawaiter remonsterate madworld',
    'race medium': 'b c d e f g i j k m n o p q r s t u w y z alphalores informativemiss magicnumbers '
                   'mpparty nicerpoison questionablecontent regionofdoom relicmyhat slowerbg tastetherainbow '
                   'makeover partyparty capslockoff johnnydmad notawaiter remonsterate electricboogaloo '
                   'madworld randombosses',
    'race insane': 'b c d e f g i j k m n o p q r s t u w y z alphalores informativemiss magicnumbers '
                   'mpparty nicerpoison questionablecontent regionofdoom relicmyhat slowerbg tastetherainbow '
                   'makeover partyparty capslockoff johnnydmad notawaiter remonsterate darkworld electricboogaloo '
                   'madworld nobreaks randombosses bsiab mementomori:14'
}

# Load configuration data
# Read DEFAULT CONFIG and then read the config.ini file in the directory to fill in any missing values
config = ConfigParser()
config.read_dict(DEFAULT_CONFIG)
files_loaded = config.read(CONFIG_PATH)
with open(CONFIG_PATH, 'w') as config_file:
    config.write(config_file)


def set_config_value(section, option, value):
    config.read(CONFIG_PATH)
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, option, value)
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)


def get_config_items(section):
    config.read(CONFIG_PATH)
    results = {}
    if config.has_section(section):
        for option in config.options(section):
            results[option] = config.get(section, option)
    return results


def write_flags(name, flags):
    config.read(CONFIG_PATH)
    try:
        config.add_section('Flags')
    except DuplicateSectionError:
        pass

    config.set('Flags', name, flags)
    with open('config.ini', 'w') as f:
        config.write(f)


def read_flags():
    print("Loading saved flags.")
    config.read(CONFIG_PATH)
    try:
        flags = dict(config.items('Flags'))
    except (NoSectionError, NoOptionError):
        print("No saved flags to load.")
        return
    return flags


def save_version(version_type, value):
    version_type = str(version_type).lower().replace(' ', '_')
    valid_version_types = ['core', 'monster_sprites', 'character_sprites', 'updater']
    if version_type not in valid_version_types:
        raise ValueError('An invalid version type was specified: ' + version_type + '. Valid version types are ' +
                         ', '.join(valid_version_types))
    set_config_value('Version', version_type, value)


def check_custom():
    missing_files = []
    custom_directory = Path(os.path.join(os.getcwd(), 'custom'))
    if not custom_directory.is_dir():
        missing_files.append('/custom/')
    else:
        # List of all files in /custom/. Some of these may not be required or may depend on chosen flags, but better
        #   safe than sorry
        required_custom_files = ['coralnames.txt', 'dancenames.txt', 'femalenames.txt', 'malenames.txt',
                                 'mooglenames.txt', 'moves.txt', 'opera.txt', 'passwords.txt', 'poems.txt',
                                 'songs.txt']
        for file in required_custom_files:
            file_path = Path(os.path.join(custom_directory, file))
            if not file_path.exists():
                missing_files.append("/custom/" + file)

        opera_directory = Path(os.path.join(custom_directory, 'opera'))
        if not opera_directory.is_dir():
            missing_files.append('/custom/opera/')
        # Put opera files here, if the opera files are required

        # character_sprites_directory = Path(os.path.join(custom_directory, 'Sprites'))
        # if not character_sprites_directory.is_dir():
        #    missing_files.append('/custom/Sprites/')
        # Put Sprite files here, if any are required

    return missing_files


def check_player_sprites():
    missing_files = []
    custom_directory = Path(os.path.join(os.getcwd(), 'custom'))
    if not custom_directory.is_dir():
        missing_files.append('/custom/')
    else:
        # List of all files in /custom/. Some of these may not be required or may depend on chosen flags, but better
        #   safe than sorry
        required_custom_files = ['spritereplacements.txt']
        for file in required_custom_files:
            file_path = Path(os.path.join(custom_directory, file))
            if not file_path.exists():
                missing_files.append("/custom/" + file)
                print("spritereplacements.txt is missing from the Custom directory. The SpriteReplacements category "
                      "and custom character sprite flags will be unavailable.")

    character_sprites_directory = Path(os.path.join(custom_directory, 'Sprites'))
    if not character_sprites_directory.is_dir():
        missing_files.append('/custom/Sprites/')

    return missing_files


def check_tables():
    missing_files = []
    if not TABLE_PATH.is_dir():
        missing_files.append('/tables/')
    else:
        # List of all files in /tables/. Some of these may not be required or may depend on chosen flags, but better
        #   safe than sorry
        required_table_files = ['ancientcheckpoints.txt', 'battlebgpalettes.txt', 'charcodes.txt',
                                'charpaloptions.txt', 'chestcodes.txt', 'commandcodes.txt', 'customitems.txt',
                                'defaultsongs.txt', 'dialoguetext.txt', 'divergentedits.txt', 'enemycodes.txt',
                                'enemynames.txt', 'espercodes.txt', 'eventpalettes.txt', 'finalai.txt',
                                'finaldungeoncheckpoints.txt', 'finaldungeonmaps.txt', 'formationmusic.txt',
                                'generator.txt', 'itemcodes.txt', 'locationformations.txt', 'locationmaps.txt',
                                'locationpaletteswaps.txt', 'magicite.txt', 'mapbattlebgs.txt', 'mapnames.txt',
                                'reachability.txt', 'ridingsprites.txt', 'samples.txt', 'shopcodes.txt',
                                'shorttext.txt', 'skipevents.txt', 'spellbans.txt', 'spellcodes.txt', 'text.txt',
                                'treasurerooms.txt', 'unusedlocs.txt', 'usedlocs.txt', 'wobeventbits.txt',
                                'wobonlytreasure.txt', 'worstartingitems.txt']
        for file in required_table_files:
            file_path = Path(os.path.join(TABLE_PATH, file))
            if not file_path.exists():
                missing_files.append("/tables/" + file)
    print("Hello")

    return missing_files


def check_ini():
    missing_files = []
    ini_file = CONFIG_PATH
    if not ini_file.is_file():
        missing_files.append('config.ini')
    return missing_files


def check_remonsterate():
    missing_files = []
    base_directory = os.path.join(os.getcwd(), "remonsterate")
    sprite_directory = os.path.join(base_directory, "sprites")
    image_file = os.path.join(base_directory, "images_and_tags.txt")
    monster_file = os.path.join(base_directory, "monsters_and_tags.txt")

    if os.path.isdir(base_directory):
        if not os.path.isfile(image_file):
            missing_files.append('/remonsterate/images_and_tags')
            print("The images_and_tags.txt file is missing from the remonsterate directory. The remonsterate flag "
                  "will be unavailable.")
        if not os.path.isfile(monster_file):
            missing_files.append('/remonsterate/monsters_and_tags.txt')
            print("The monsters_and_tags.txt file is missing from the remonsterate directory. The remonsterate "
                  "flag will be unavailable.")
        if not os.path.isdir(sprite_directory):
            missing_files.append('/remonsterate/')
            print("The sprites folder is missing from the remonsterate directory. The remonsterate flag will be "
                  "unavailable.")
    else:
        missing_files.append('/remonsterate/')
        print("The remonsterate folder is missing from the Beyond Chaos directory. The remonsterate flag will be "
              "unavailable.")

    return missing_files
