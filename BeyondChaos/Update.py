#!/usr/bin/env python3
import requests
import shutil
import Constants
import time
import subprocess
import Config
import os
from pathlib import Path
from zipfile import ZipFile



#our entry point into the updater, called before we display the GUI to the user
def update():
    update = False
    if (coreUpdateAvailable()):
        updateCore()
        update = True
    if (spriteUpdateAvailable()):
        updateSprites()
        update = True

    if(update):
        #launch the updater process
        subprocess.call("BeyondChaosUpdater.exe")
        #wait 3 seconds
        time.sleep(1)
        SystemExit()


def updateCore():
    #ping github and get the new released version
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosRandomizer/releases/latest').json() 
    # get the link to download the latest package
    downloadlink = x['assets'][0]['browser_download_url']
    #download the file and save it.
    download_file(downloadlink)

def updateSprites():
    #ping github and get the new released version
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosSprites/releases/latest').json() 
    # get the link to download the latest package
    downloadlink = x['assets'][0]['browser_download_url']
    #download the file and save it.
    download_file(downloadlink)

def coreUpdateAvailable():
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosRandomizer/releases/latest').json()   
    latestVersion = x['tag_name']
    coreVersion = Config.getCoreVersion()

    # We can not have a newer version over an older version if we are
    # checking updater.
    if latestVersion != coreVersion:
        return True
    else:
        return False

def spriteUpdateAvailable():
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosSprites/releases/latest').json()   
    latestVersion = x['tag_name']
    spriteVersion = Config.SpriteVersion

    # We can not have a newer version over an older version if we are
    # checking updater.
    if latestVersion != spriteVersion:
        return True
    else:
        return False


#saves the file to the directory you ran the exe from, the file will be in a
#zip format
def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename

def updaterExists():
    my_file = Path("BeyondChaosUpdater.exe")
    if my_file.is_file():
        # file exists
        return
    else:
        x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosUpdater/releases/latest').json() 
        #download the latest package
        downloadlink = x['assets'][0]['browser_download_url']
        download_file(downloadlink)
        loop = True
        while loop:
            zip_file = Path("BeyondChaosUpdater.zip")
            if zip_file.is_file():
                loop = False
        with ZipFile('BeyondChaosUpdater.zip', 'r') as zipObj:
            # Extract all the contents of zip file in different directory
            zipObj.extractall()

def configExists():
    exists = Config.checkINI()
    if exists:
        #make sure our updater exists
        updaterExists()
        return
    else:
        runFirstTimeSetup()

def runFirstTimeSetup():
    #check for the updater
    updaterExists()
    time.sleep(3)
    os.startfile("BeyondChaosUpdater.exe")
    #wait 3 seconds
    time.sleep(3)
    SystemExit()

