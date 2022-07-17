import configparser
import requests
from configparser import ConfigParser
from pathlib import Path
import os
config = ConfigParser()


def write_flags(name, flags):
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    try:
        config.add_section('Flags')    
    except Exception:
        print("Config Section Flags already exists, skipping writing new section.")
    
    config.set('Flags', name, flags)
    with open('config.ini', 'w') as f:
        config.write(f)


def read_flags():
    print("Loading saved flags.")
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    try:
        flags = dict(config.items('Flags'))
    except Exception:
        print("No saved flags to load.")
        return
    return flags


def read_config():
    version_information = {}
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    # try:
    #     version_information['updater'] = config.get('Version', 'updater')
    # except configparser.NoOptionError:
    #     version_information['updater'] = None
    try:
        version_information['core'] = config.get('Version', 'core')
    except configparser.NoOptionError:
        version_information['core'] = ''
    try:
        version_information['character_sprites'] = config.get('Version', 'character_sprites')
    except configparser.NoOptionError:
        version_information['character_sprites'] = ''
    try:
        version_information['monster_sprites'] = config.get('Version', 'monster_sprites')
    except configparser.NoOptionError:
        version_information['monster_sprites'] = ''
    return version_information


def get_input_path():
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    if config.has_section('Settings') and config.has_option('Settings', 'input_path'):
        return config.get('Settings', 'input_path')
    else:
        return ''


def save_input_path(path):
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    if not config.has_section('Settings'):
        config.add_section('Settings')
    config.set('Settings', 'input_path', str(path))
    with open(Path(os.path.join(os.getcwd(), "config.ini")), 'w') as f:
        config.write(f)


def get_output_path():
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    if config.has_section('Settings') and config.has_option('Settings', 'output_path'):
        return config.get('Settings', 'output_path')
    else:
        return ''


def save_output_path(path):
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    if not config.has_section('Settings'):
        config.add_section('Settings')
    config.set('Settings', 'output_path', str(path))
    with open(Path(os.path.join(os.getcwd(), "config.ini")), 'w') as f:
        config.write(f)


# def get_updater_version():
#     return read_config()['updater']


def get_core_version():
    return read_config()['core']


def get_character_sprite_version():
    return read_config()['character_sprites']


def get_monster_sprite_version():
    return read_config()['monster_sprites']


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
                                 'songs.txt', 'spritereplacements.txt']
        for file in required_custom_files:
            file_path = Path(os.path.join(custom_directory, file))
            if not file_path.exists():
                missing_files.append("/custom/" + file)

        opera_directory = Path(os.path.join(custom_directory, 'opera'))
        if not opera_directory.is_dir():
            missing_files.append('/custom/opera/')
        # Put opera files here, if the opera files are required

        character_sprites_directory = Path(os.path.join(custom_directory, 'Sprites'))
        if not character_sprites_directory.is_dir():
            missing_files.append('/custom/Sprites/')
        # Put Sprite files here, if any are required

    return missing_files


def check_tables():
    missing_files = []
    tables_directory = Path(os.path.join(os.getcwd(), 'tables'))
    if not tables_directory.is_dir():
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
            file_path = Path(os.path.join(tables_directory, file))
            if not file_path.exists():
                missing_files.append("/tables/" + file)

    return missing_files


def check_ini():
    missing_files = []
    ini_file = Path(os.path.join(os.getcwd(), "config.ini"))
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
            print("The images_and_tags.txt file is missing from the remonsterate directory.")
        if not os.path.isfile(monster_file):
            missing_files.append('/remonsterate/monsters_and_tags.txt')
            print("The monsters_and_tags.txt file is missing from the remonsterate directory.")
        if not os.path.isdir(sprite_directory):
            missing_files.append('/remonsterate/')
            print("The sprites folder is missing from the remonsterate directory.")
    else:
        missing_files.append('/remonsterate/')
        print("The remonsterate folder is missing from the Beyond Chaos directory.")

    return missing_files


def are_updates_hidden():
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    if not config.has_section('Settings') or not config.has_option('Settings', 'updates_hidden'):
        # If the config file does not have this setting, write it and then return false
        updates_hidden(False)
        return False
    try:
        if config.get('Settings', 'updates_hidden') == "True":
            return True
        else:
            return False
    except Exception:
        return False


def updates_hidden(hidden=False):
    config.read(Path(os.path.join(os.getcwd(), "config.ini")))
    if not config.has_section('Settings'):
        config.add_section('Settings')
    config.set('Settings', 'updates_hidden', str(hidden))
    with open(Path(os.path.join(os.getcwd(), "config.ini")), 'w') as f:
        config.write(f)


def validate_files():
    # Return values:
    # 1) Array of strings representing missing information
    # 2) Boolean that indicates whether the update is required or optional
    missing_files = []
    missing_files.extend(check_custom())
    missing_files.extend(check_tables())
    missing_files.extend(check_ini())
    missing_files.extend(check_remonsterate())

    # Missing files are required for the randomizer to function properly, so it triggers a forced update
    if missing_files:
        return '\n'.join(missing_files), True

    version_errors = []
    base_github_url = 'https://api.github.com/repos/FF6BeyondChaos/'
    core_github_url = base_github_url + 'BeyondChaosRandomizer/releases/latest'
    character_sprites_github_url = base_github_url + 'BeyondChaosSprites/releases/latest'
    monster_sprites_github_url = base_github_url + 'BeyondChaosMonsterSprites/releases/latest'

    for type, version in read_config().items():
        if not version:
            # Catches version information with no recorded information - probably should never happen
            version_errors.append('The ' + type + " version was not recorded in config.ini.")
        else:
            # Note: Updater version is not checked.
            if type == 'core':
                response = requests.get(core_github_url)
                if response.ok:
                    github_version = response.json()['tag_name']
                    if not version == github_version:
                        version_errors.append('The core Beyond Chaos files are currently version ' + str(version) + '. '
                                              'Version ' + github_version + ' is available.')
            if type == 'character_sprites':
                response = requests.get(character_sprites_github_url)
                if response.ok:
                    github_version = response.json()['tag_name']
                    if not version == github_version:
                        version_errors.append('The Character Sprite files are currently version ' + str(version) + '. '
                                              'Version ' + github_version + ' is available.')
            if type == 'monster_sprites':
                response = requests.get(monster_sprites_github_url)
                if response.ok:
                    github_version = response.json()['tag_name']
                    if not version == github_version:
                        version_errors.append('The Monster Sprite files are currently version ' + str(version) + '. '
                                              'Version ' + github_version + ' is available.')

    if version_errors:
        return '\n'.join(version_errors), False
    return None, False

