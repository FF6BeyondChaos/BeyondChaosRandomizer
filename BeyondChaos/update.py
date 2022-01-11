#!/usr/bin/env python3
import requests
import shutil
import constants
import time
import subprocess
import config
import os
from pathlib import Path
from zipfile import ZipFile


# our entry point into the updater, called before we display the GUI to the user
def update():
    update_needed = False
    if is_core_update_available():
        update_core()
        update_needed = True
    if is_sprite_update_available():
        update_sprites()
        update_needed = True

    if update_needed:
        # launch the updater process
        subprocess.call("BeyondChaosUpdater.exe")
        # wait 3 seconds
        time.sleep(1)
        SystemExit()


def update_core():
    # ping github and get the new released version
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosRandomizer/releases/latest').json() 
    # get the link to download the latest package
    download_link = x['assets'][0]['browser_download_url']
    # download the file and save it.
    download_file(download_link)


def update_sprites():
    # ping github and get the new released version
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosSprites/releases/latest').json() 
    # get the link to download the latest package
    download_link = x['assets'][0]['browser_download_url']
    # download the file and save it.
    download_file(download_link)


def is_core_update_available():
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosRandomizer/releases/latest').json()   
    latest_version = x['tag_name']
    core_version = config.getCoreVersion()

    # We can not have a newer version over an older version if we are
    # checking updater.
    if latest_version != core_version:
        return True
    else:
        return False


def is_sprite_update_available():
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosSprites/releases/latest').json()   
    latest_version = x['tag_name']
    sprite_version = config.SpriteVersion

    # We can not have a newer version over an older version if we are
    # checking updater.
    if latest_version != sprite_version:
        return True
    else:
        return False


# saves the file to the directory you ran the exe from, the file will be in a zip format
def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename


def get_updater():
    #my_file = Path("BeyondChaosUpdater.exe")
    #if my_file.is_file():
    #    # file exists
    #    return
    #else:
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosUpdater/releases/latest').json()
    # download the latest package
    download_link = x['assets'][0]['browser_download_url']
    download_file(download_link)
    loop = True
    while loop:
        zip_file = Path("BeyondChaosUpdater.zip")
        if zip_file.is_file():
            loop = False
    with ZipFile('BeyondChaosUpdater.zip', 'r') as zipObj:
        # Extract all the contents of zip file in different directory
        zipObj.extractall()


def update_needed():
    up_to_date = config.checkINI() and config.check_remonsterate()
    if not up_to_date:
        print("Running the updater to create necessary files and folders.")
        run_first_time_setup()
        return True
    else:
        return False


def run_first_time_setup():
    # check for the updater
    get_updater()
    time.sleep(3)
    os.startfile("BeyondChaosUpdater.exe")
    SystemExit()

