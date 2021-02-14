from configparser import ConfigParser
config = ConfigParser()

#plans:
# eventually this is where flags will be saved off to replacing whatever is in beyondchaos.py and moving towards an INI file to remember everything properly will be loaded and unloaded at launch.
CoreVersion = ""
SpriteVersion = ""

def writeConfig():
    config.read('config.ini')
    config.add_section('Version')
    config.set('Version', 'Core', CoreVersion)
    config.set('Version', 'Sprite', SpriteVersion)
    #config.set('main', 'key3', 'value3')

    with open('config.ini', 'w') as f:
        config.write(f)

def readConfig():
    config.read('config.ini')
    CoreVersion = config.get('Version', 'Core') # -> "value1"
    SpriteVersion= config.get('Version', 'Sprite') # -> "value2"
    #print config.get('main', 'key3') # -> "value3"

def setCoreVersion(version):
    readConfig()
    CoreVersion = version
    writeConfig()

def setSpriteVersion(version):
    readConfig()
    SpriteVersion = version
    writeConfig()

def getCoreVersion():
    readConfig()
    return CoreVersion

def getSpriteVersion():
    readConfig()
    return SpriteVersion

#for version 4.0.5 only...
def initialSetup():
    CoreVersion = "4.0.4"
    SpriteVersion = "1.0.1"