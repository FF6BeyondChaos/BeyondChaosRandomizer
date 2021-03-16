from configparser import ConfigParser
from pathlib import Path
import os
config = ConfigParser()

CoreVersion = ""
SpriteVersion = ""

def Writeflags(name, flags):
    config.read(Path(os.getcwd()+"/config.ini"))
    config.add_section('Version')
    config.set('Version', 'Core', CoreVersion)
    config.set('Version', 'Sprite', SpriteVersion)
    config.add_section('Flags')
    config.set('Flag', name, flags)

    with open('config.ini', 'w') as f:
        config.write(f)

def readflags():
    config.read(Path(os.getcwd()+"/config.ini"))
    flags = dict(Config.items('Flags'))
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