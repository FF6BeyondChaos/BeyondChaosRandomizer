#!/usr/bin/env python3
import requests
import shutil
import Constants
import time
import subprocess

#our entry point into the updater, called before we display the GUI to the user
def update():
    response = input(Constants.UpdateRequest)
    #If the user types N or n, we will skip, any other value will update.
    if response and response[0].lower() == 'n':
        return
    else:
        # Notify the user we are doing things
        print(Constants.UpdateCheck)
        #ping github and see if there is a new version released
        x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaos/releases/latest').json()   
        latestVersion = x['tag_name']
        currentVersion = Constants.Version

        # We can not have a newer version over an older version if we are checking updater.
        if latestVersion != currentVersion:
            #download the latest package
            print(Constants.UpdateFound)
            downloadlink = x['assets'][0]['browser_download_url']
            download_file(downloadlink)
            print(Constants.UpdateLaunching)
            #launch the updater process
            subprocess.run("BeyondChaosUpdater.exe", shell=True)
            #wait 3 seconds
            time.sleep(3)
            SystemExit();
        else:
            print(Constants.UpdateNotFound)
            return;

#saves the file to the directory you ran the exe from, the file will be in a zip format
def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename

#if response and response[0].lower() == 'y':
#else