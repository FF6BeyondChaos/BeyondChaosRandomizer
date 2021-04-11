from configparser import ConfigParser
from pathlib import Path
import os
config = ConfigParser()

CoreVersion = ""
SpriteVersion = ""

def Writeflags(name, flags):
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