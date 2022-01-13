from configparser import ConfigParser
from pathlib import Path
import os
config = ConfigParser()

CoreVersion = ""
SpriteVersion = ""


def writeFlags(name, flags):
    config.read(Path(os.getcwd()+"/config.ini"))
    try:
        config.add_section('Flags')    
    except Exception:
        print("Config Section Flags already exists, skipping writing new section.")
    
    config.set('Flags', name, flags)
    with open('config.ini', 'w') as f:
        config.write(f)


def readFlags():
    print("Loading saved flags.")
    config.read(Path(os.getcwd()+"/config.ini"))
    try:
        flags = dict(config.items('Flags'))
    except Exception:
        print("No saved flags to load.")
        return
    return flags


def readConfig():
    config.read(Path(os.getcwd()+"/config.ini"))
    CoreVersion = config.get('Version', 'Core') # -> "value1"
    SpriteVersion= config.get('Version', 'Sprite') # -> "value2"
    #print config.get('main', 'key3') # -> "value3"


def getCoreVersion():
    readConfig()
    return CoreVersion


def getSpriteVersion():
    readConfig()
    return SpriteVersion


def checkINI():
    my_file = Path(os.getcwd()+"/config.ini")
    if my_file.is_file():
        # file exists
        return True
    else:
        return False


def check_remonsterate():
    current = True
    base_directory = os.path.join(os.getcwd(), "remonsterate")
    sprite_directory = os.path.join(base_directory, "sprites")
    image_file = os.path.join(base_directory, "images_and_tags.txt")
    monster_file = os.path.join(base_directory, "monsters_and_tags.txt")

    if os.path.isdir(base_directory):
        if not os.path.isfile(image_file):
            print("The images_and_tags.txt file is missing from the remonsterate directory.")
            current = False
        if not os.path.isfile(monster_file):
            print("The monsters_and_tags.txt file is missing from the remonsterate directory.")
            current = False
        if not os.path.isdir(sprite_directory):
            print("The sprites folder is missing from the remonsterate directory.")
            current = False
    else:
        print("The remonsterate folder is missing from the Beyond Chaos directory.")
        current = False

    return current
