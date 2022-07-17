#!/usr/bin/env python3
import requests
import shutil
import time
import subprocess
import config
import os
import tempfile
from zipfile import ZipFile


# saves the file to the directory you ran the exe from, the file will be in a zip format
def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename


def get_updater():
    x = requests.get('https://api.github.com/repos/FF6BeyondChaos/BeyondChaosUpdater/releases/latest').json()
    # get the link to download the latest package
    download_link = x['assets'][0]['browser_download_url']
    # download the file and save it.
    temp_dir = tempfile.mkdtemp()
    local_filename = os.path.join(temp_dir, download_link.split('/')[-1])
    with requests.get(download_link, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    dst = os.getcwd()
    with ZipFile(local_filename, 'r') as zip_obj:
        # Extract all the contents of zip file in different directory
        if not os.path.exists(dst):
            os.makedirs(dst)
        zip_obj.extractall(dst)
        # wait 3 seconds
        time.sleep(3)


def update_needed():
    up_to_date = config.check_ini() and config.check_remonsterate()
    if not up_to_date:
        print("Running the updater to create necessary files and folders.")
        run_first_time_setup()
        return True
    else:
        return False


def run_first_time_setup():
    # check for the updater
    if not os.path.isfile("BeyondChaosUpdater.exe"):
        get_updater()
    time.sleep(3)
    subprocess.call(args=[], executable="BeyondChaosUpdater.exe")
