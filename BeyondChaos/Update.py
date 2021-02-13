#!/usr/bin/env python3
import requests
import shutil
import Constants
import time
import subprocess
from pathlib import Path
from zipfile import ZipFile

#our entry point into the updater, called before we display the GUI to the user
def update():
    # Notify the user we are doing things
    print(Constants.UpdateFound)
    #ping github and see if there is a new version released
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaos/releases/latest').json() 
    #download the latest package
    downloadlink = x['assets'][0]['browser_download_url']
    download_file(downloadlink)
    #launch the updater process
    subprocess.run("BeyondChaosUpdater.exe", shell=True)
    #wait 3 seconds
    time.sleep(3)
    SystemExit()
    return

def updateAvailable():
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaos/releases/latest').json()   
    latestVersion = x['tag_name']
    currentVersion = Constants.Version

    # We can not have a newer version over an older version if we are
    # checking updater.
    if latestVersion != currentVersion:
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

