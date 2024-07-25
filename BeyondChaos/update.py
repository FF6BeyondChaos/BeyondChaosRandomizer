#!/usr/bin/env python3
import platform
import time
import shutil
import os
import sys
import tempfile
import subprocess
from randomizer import config
from config import check_custom, check_ini, set_config_value, get_config_value
from utils import extract_archive, get_directory_hash, md5_update_from_file
from PyQt5.QtWidgets import QApplication, QMessageBox

# TODO: Combine the get_directory_hash, md5_update_from_dir, and md5_update_from_file into a single
#   method that will take a path and optional hash value and return the hash regardless of whether the path
#   leads to a file or directory.
#   Then, add a list of required hash paths to _assets.
#   Then, turn the whole 'detect if x has been customized' into a separate method

# TODO: Instead of replacing directories wholesale, develop a way to snag specific necessary files. For example,
#   if we're missing a specific custom file, grab just that file and not replace the whole custom directory.

# TODO: Think about how our GitHub repositories are structured. Do we really need 3 repos? Is there a release
#   structure that would facilitate easier updating?

# This is not part of the stdlib
try:
    import requests
except ImportError:
    sys.exit('Please install the `requests` python package '
             'before running updater. Try "pip install requests".')
try:
    import psutil
except ImportError:
    sys.exit('Please install the `psutil` python package '
             'before running updater. Try "pip install psutil".')
try:
    import jwt
except ImportError:
    sys.exit('Please install the `jwt` python package '
             'before running updater. Try "pip install jwt".')

caller = None
remaining_api_calls = 0
request_headers = {}
available_updates = []
back_up_skip = []
updated = False

TEST = False
BASE_DIRECTORY = os.getcwd()
CONFIG_PATH = os.path.join(BASE_DIRECTORY, 'config.ini')
CONSOLE_PATH = os.path.join(BASE_DIRECTORY, 'beyondchaos_console.exe')
GUI_PATH = os.path.join(BASE_DIRECTORY, 'beyondchaos.exe')
_BASE_PROJ_URL = 'https://api.github.com/repos/FF6BeyondChaos/'

# Update: Does this asset require an update?
# Prompt: What should be displayed to the user to confirm the update?
# Location: Where should the asset be downloaded and extracted to?
# URL: What web address is the asset located at?
# Data: The data from the URL, so we don't need to hit the API multiple times.
_ASSETS = {
    'core': {
        'prompt': 'There is an update available for the Beyond Chaos core files.\n'
                  'Would you like to download the update from GitHub?\n'
                  'This will replace the version of Beyond Chaos you are currently running.\n',
        'location': BASE_DIRECTORY,
        'URL': os.path.join(_BASE_PROJ_URL, 'BeyondChaosRandomizer/releases/latest'),
        'data': {}
    },
    'custom': {
        'prompt': '',
        'location': os.path.join(BASE_DIRECTORY, 'custom'),
        'URL': os.path.join(_BASE_PROJ_URL, 'BeyondChaosRandomizer/releases/latest'),
        'data': {}
    },
    'character_sprites': {
        'prompt': "There is an update available for Beyond Chaos' character sprites.\n"
                  'They are required to use the makeover code.\n'
                  'Would you like to download the new sprites from GitHub?\n',
        'location': os.path.join(BASE_DIRECTORY, 'custom'),
        'URL': os.path.join(_BASE_PROJ_URL, 'BeyondChaosSprites/releases/latest'),
        'data': {}
    },
    'monster_sprites': {
        'prompt': "There is an update available for Beyond Chaos' monster sprites.\n"
                  'They are required to use the remonsterate code.\n'
                  'Would you like to download the new sprites from GitHub?\n',
        'location': os.path.join(BASE_DIRECTORY, 'remonsterate'),
        'URL': os.path.join(_BASE_PROJ_URL, 'BeyondChaosMonsterSprites/releases/latest'),
        'data': {}
    }
}


def internet_connectivity_available():
    try:
        requests.head(url='http://www.google.com')
        return True
    except Exception:
        return False


def get_remaining_api_calls():
    return send_get_request(url='https://api.github.com/rate_limit')['resources']['core']['remaining']


def get_web_token():
    global request_headers
    if request_headers:
        return request_headers
    # Application has read-only access to the BeyondChaosRandomizer repository
    # Web token lasts 9 minutes
    payload = {
        'iat': int(time.time()) - 30,
        'exp': int(time.time()) + 570,
        'iss': '304388'
    }
    signing_key = jwt.jwk_from_pem(pem_content=bytes('''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAraBSKgFWY8cMaPC8JaluID7YlNm/vOhPIzQVqKczBKP3YDyT
VmCupXLXkIL7TtclhIruclm80NsAqx4IkyCxrauicLVeXlqFINPCWl7sbdQBgnkk
aw5VK44BWZIFKemf4qKtIJRnMA78IFmHJwQVKfPQqs4xByk5vXLsvGH7OCjZJ/Eh
9VP2htNCac5x2H/LaLzuTFbJJPhYTO1QwguSDnu1FJGwAGtqEag4HkfIbVUrZI4V
8oLLglFxlHHPGWH4RLqxE4F2V104c7I+E+fVaRTGV1S26zQ+TLFQGJQgNwPD/61J
BLxIIdr1lw1X18RW1z82Kv5QERzjtN2mV1jllQIDAQABAoIBAAN3G6yy8iJzqo+9
nkOyKfyCxJfT8Lu4dzvgoj4HeEEzdJB7JQWoUFQFAsBjnNhp+tm2XCP0HoycklrX
8pvdHy60Kj3NoOCJNfb9wvdCxb07afxMpqlsU87Wurgq7ed0PjirvoDT9WtEIUwT
/VqN/k4kC5odG2VlMT3SuV7ZJcZtId3K6lRZgmn8T4ODbcqcjIVe6ZvDX4i/WthX
QUKPv7PticuaP1aOZ6zV4ardtBu45WKg9ZTl4O65sUFfxeu/i0KGiX+LzEVqcI3e
8j1OUixVvd3D/ePuBlm1H3b7bSHRz6T33oCWNBts3S+pKHHgW22oOOtYyEsZ3+BP
086YG9ECgYEA1cycMVnhOup0ZxA59gOylj8NASwFisQlaMP007VcjiojH5vLCAPp
a1k6Z2z/koDJiQxOqiyDvUv1bpVo5gOc2OB9BCVnwKKR/+A4l9UiddUXNAYgG1vY
ZP+xcUliXn50j/9mo2isiRRRWkDpLIciO545jcRRroR8difrpEhNE5sCgYEAz+W/
Ywz/HADT/p0dOzx3QuD9oXJTutToJy2/BnrfHDlvu5v/OwJt/IU8yYAVhkfx+VY5
HefD+04dYrCLyd0dyBZid0lxbXG4C+Q1hIhAYvj/fUaqGy8U8Z9N7anVWuunL4rw
omOOb6nsIRr3hlFCVxwfxXOmcEBDd0zOwWOc9o8CgYEAjAUR8jxEBtrP20PEQfuP
9Vhbwv26r3PgcCmN6S0o7a5pDGVy5c/yCi0I0/2Nr7wKwWe/CTJYIRxjI8ZUSffp
vBvhpFp/Baky5xpI1h9vDy68oIS2eFSBdzwCUQhXlT1KR5hj9vcxsCEPWoWScGgc
ImFwngkJ2brI7HUenZwAZqsCgYBKT/NjcofV+K3Oe1axj+GJdGb0yKsJQ4VgS8fW
hyEtM5Ku2woWi73I389kr3YCM8FYwOtVtzyknb1/Q2AUXgeBOA8mWIhE+Lsy9PX0
U8fAGQUqQJIZeXDhFXKDm4t6HnX6Vo3BXhjR7UlMZBlKV82A2bq5l6dMxIvZHwlg
szyuHQKBgBvj2eOo5QzJZp2KCUpHaVfsMtxtLXf8mfmPBkzWEp7yaALEE6opKOeu
+XDiG2cABNW0zHi8It0e81LUB7d1czv0vr3nspLZbbe2rV7p5LeAYKRPPtC34I+Y
IUDMfyYGvvrC9Ajz+gQkT5Lp6flc1aPL5pqtiT/eBi3Tu8xMCH8d
-----END RSA PRIVATE KEY-----''', 'utf-8'))
    jwt_instance = jwt.JWT()
    encoded_jwt = jwt_instance.encode(payload, key=signing_key, alg='RS256')
    response = requests.post(
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + encoded_jwt,
            'X-GitHub-Api-Version': '2022-11-28'
        },
        url='https://api.github.com/app/installations/35180196/access_tokens')

    try:
        access_token = response.json()['token']
    except KeyError:
        raise KeyError('There was an error getting a token from GitHub to check for updates. '
                       'Details of GitHubs response: ' + str(response.json()))

    request_headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': 'Bearer ' + access_token,
        'X-GitHub-Api-Version': '2022-11-28'
    }
    return request_headers


def send_get_request(url: str, stream=False):
    global request_headers
    resp = requests.get(
        url,
        headers=request_headers,
        stream=stream
    )
    # check request result
    if not resp.ok:
        # Try refreshing the web token
        request_headers = {}
        try:
            get_web_token()
        except KeyError as ex:
            # This should never happen, since prior calls to get_web_token are required to even get to the
            #   section of code where send_get_request is called
            print(str(ex))
            raise ex

        resp = requests.get(
            url,
            headers=request_headers,
            stream=stream
        )
        if not resp.ok:
            prompt(prompt_type='notify',
                   message=f'GitHub returned a bad response.\nDetails:{resp.reason}')
            sys.exit()
    if stream is True:
        return resp
    else:
        return resp.json()


def back_up_folder(asset_name, folder_path):
    if os.path.exists(folder_path):
        timestamp = str(time.time())
        shutil.copytree(folder_path, folder_path + '_backup_' + timestamp)
        print('Your ' + asset_name + ' directory has been backed up to ' + folder_path +
              '_backup_' + timestamp + '.')


def prompt(prompt_type, message):
    global caller
    if caller == 'gui' or isinstance(caller, QApplication):
        prompt = QMessageBox()
        prompt.setWindowTitle('Beyond Chaos Updater')
        prompt.setText(message)
        if prompt_type == 'yesno':
            prompt.setIcon(QMessageBox.Question)
            prompt.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
            response = prompt.exec()
            if response == QMessageBox.Yes:
                return True
            elif response == QMessageBox.No:
                return False
        elif prompt_type == 'notify':
            prompt.setIcon(QMessageBox.Information)
            prompt.setStandardButtons(QMessageBox.Ok)
            prompt.exec()
        elif prompt_type == 'error':
            prompt.setIcon(QMessageBox.Critical)
            prompt.setStandardButtons(QMessageBox.Ok)
            prompt.exec()
    elif caller == 'console':
        while True:
            if prompt_type == 'yesno':
                print(message)
                response = input('Y/N: ')
                if response.lower() in ['y', 'yes']:
                    return True
                elif response.lower() in ['n', 'no']:
                    return False
                else:
                    print('Please choose either (Y)es or (N)o.')
            elif prompt_type == 'notify':
                input('Press any button to continue.')
                return True
            elif prompt_type == 'Error':
                input('Press any button to continue.')
                return True
    else:
        raise ValueError('The update caller is an unexpected value: ' + str(caller))


def update_asset_from_web(asset):
    global updated

    data = _ASSETS[asset]['data']
    # get the link to download the latest package
    download_link = data['assets'][0]['browser_download_url']
    # download the file and save it.
    temp_dir = tempfile.mkdtemp()
    local_filename = os.path.join(temp_dir, download_link.split('/')[-1])
    with send_get_request(url=download_link, stream=True) as file_binary:
        with open(local_filename, 'wb') as file_name:
            shutil.copyfileobj(file_binary.raw, file_name)

    if asset == 'core':
        global caller
        if caller == 'console' and os.path.exists(CONSOLE_PATH):
            os.rename(CONSOLE_PATH, os.path.splitext(CONSOLE_PATH)[0] + '.old' + os.path.splitext(CONSOLE_PATH)[1])
        if isinstance(caller, QApplication) and os.path.exists(GUI_PATH):
            os.rename(GUI_PATH, os.path.splitext(GUI_PATH)[0] + '.old' + os.path.splitext(GUI_PATH)[1])
        # Extract the new update
        back_up_folder('custom', os.path.join(_ASSETS[asset]['location'], 'custom'))
        extract_archive(local_filename, _ASSETS[asset]['location'] or os.getcwd())

        set_config_value('Version', asset, data['tag_name'])
        updated = True

    if asset == 'custom':
        # If a hash value for the custom folder exists in config.ini and that value is different from the folder's
        #   current hash value, we back up the folder because we assume somebody has made customizations.
        # print('Custom hash comparison: ' + str(get_directory_hash(_ASSETS[asset]['location']).hexdigest()) + ' vs ' +
        #       str(get_config_value(section='Hashes', option=asset)))
        if (not _ASSETS[asset]['location'] in back_up_skip and not
                get_directory_hash(_ASSETS[asset]['location']).hexdigest() ==
                get_config_value(section='Hashes', option=asset)):
            back_up_folder(
                asset,
                _ASSETS[asset]['location']
            )
        # Either custom is backed up completely or completely replaced. In either case, no need to further back up.
        back_up_skip.append(_ASSETS[asset]['location'])

        # Extract the core files to a temp directory, then copy only the custom folder. Clean up temp after.
        extract_archive(
            local_filename,
            os.path.join(os.getcwd(), 'temp')
        )
        shutil.copytree(
            os.path.join(os.getcwd(), 'temp', 'custom'),
            _ASSETS[asset]['location'],
            dirs_exist_ok=True
        )
        set_config_value('Hashes', asset, str(get_directory_hash(_ASSETS[asset]['location']).hexdigest()))

        try:
            shutil.rmtree(os.path.join(os.getcwd(), 'temp'))
        except PermissionError:
            print('Error: did not have permissions to remove the temp directory at ' +
                  str(os.path.join(os.getcwd(), 'temp')) + '.')

        print(f'{str.replace(asset.title(), "_", " ")} files have been updated.\n')
        updated = True

    if asset == 'character_sprites':
        def get_character_sprite_hash() -> str:
            character_sprite_hash = get_directory_hash(os.path.join(_ASSETS[asset]['location'], 'sprites'))
            character_sprite_hash = md5_update_from_file(os.path.join(_ASSETS[asset]['location'],
                                                                      'spritereplacements.txt'),
                                                         character_sprite_hash)
            character_sprite_hash = md5_update_from_file(os.path.join(_ASSETS[asset]['location'], 'spritecredits.txt'),
                                                         character_sprite_hash)
            character_sprite_hash = md5_update_from_file(os.path.join(_ASSETS[asset]['location'], 'changelog.txt'),
                                                         character_sprite_hash)
            return str(character_sprite_hash.hexdigest())

        back_up_custom = True

        # print('Asset location: ' + str(_ASSETS[asset]['location']))
        # print('Assets backed up: ' + str(back_up_skip))
        # print('Asset has been backed up: ' + str(_ASSETS[asset]['location'] in back_up_skip))
        # print('Hash of character sprites: ' + str(get_character_sprite_hash()))
        # print('Saved hash of character sprites: ' + str(get_config_value(section='Hashes', option=asset)))
        if (_ASSETS[asset]['location'] in back_up_skip or
                get_character_sprite_hash() == get_config_value(section='Hashes', option=asset)):
            back_up_custom = False

        if back_up_custom:
            back_up_folder('custom', _ASSETS['custom']['location'])
            back_up_skip.append(_ASSETS['custom']['location'])

        extract_archive(local_filename, _ASSETS[asset]['location'])
        set_config_value('Hashes', asset, get_character_sprite_hash())
        set_config_value('Version', asset, data['tag_name'])
        print(f'{str.replace(asset.title(), "_", " ")} have been updated.\n')
        updated = True

    if asset == 'monster_sprites':
        def get_monster_sprite_hash() -> str:
            monster_sprite_hash = get_directory_hash(os.path.join(_ASSETS[asset]['location'], 'sprites'))
            monster_sprite_hash = md5_update_from_file(os.path.join(_ASSETS[asset]['location'],
                                                                    'images_and_tags.txt.txt'),
                                                       monster_sprite_hash)
            monster_sprite_hash = md5_update_from_file(os.path.join(_ASSETS[asset]['location'],
                                                                    'monsters_and_tags.txt.txt'),
                                                       monster_sprite_hash)
            monster_sprite_hash = md5_update_from_file(os.path.join(_ASSETS[asset]['location'], 'changelog.txt'),
                                                       monster_sprite_hash)
            return monster_sprite_hash.hexdigest()

        back_up_remonsterate = True

        # print('Asset location: ' + str(_ASSETS[asset]['location']))
        # print('Assets backed up: ' + str(back_up_skip))
        # print('Asset has been backed up: ' + str(_ASSETS[asset]['location'] in back_up_skip))
        # print('Hash of monster sprites: ' + str(get_monster_sprite_hash()))
        # print('Saved hash of monster sprites: ' + str(get_config_value(section='Hashes', option=asset)))
        if (_ASSETS[asset]['location'] in back_up_skip or
                get_monster_sprite_hash() == get_config_value(section='Hashes', option=asset)):
            back_up_remonsterate = False

        if back_up_remonsterate:
            back_up_folder('remonsterate', _ASSETS[asset]['location'])
            back_up_skip.append(_ASSETS[asset]['location'])

        extract_archive(local_filename, _ASSETS[asset]['location'])
        update_remonsterate(force=True)
        set_config_value('Hashes', asset, get_monster_sprite_hash())
        set_config_value('Version', asset, data['tag_name'])
        print(f'{str.replace(asset.title(), "_", " ")} have been updated.\n')
        updated = True

    # if asset == 'character_sprites' or asset == 'monster_sprites':
    #     update_sprites = True
    #     back_up_sprites = False
    #
    #     if os.path.exists(_ASSETS[asset]['location']):
    #         # Compare the stored hash value with the hash of the existing spritereplacements file
    #         sprite_hash = config.get(section='Hashes', option=asset, fallback='Unknown')
    #         if sprite_hash == 'Unknown':
    #             # If the hash for the asset does not exist, we can just back up the files to be safe
    #             back_up_sprites = True
    #         else:
    #             current_hash = None
    #             if asset == 'character_sprites':
    #                 current_hash = get_directory_hash(_ASSETS[asset]['location'] + '/sprites')
    #                 if current_hash:
    #                     # Include spritereplacements.txt in the hash
    #                     current_hash = md5_update_from_file(_ASSETS[asset]['location'] +
    #                                                         '/spritereplacements.txt', current_hash)
    #             elif asset == 'monster_sprites':
    #                 current_hash = get_directory_hash(_ASSETS[asset]['location'])
    #             if current_hash:
    #                 if not sprite_hash == current_hash.hexdigest():
    #                     # The asset has been customized
    #                     while True:
    #                         print(f'It appears your {str.replace(asset, "_", " ")} have been customized.')
    #                         print(f'Would you like to back up the current {str.replace(asset, "_", " ")}'
    #                               ' folder before updating?')
    #                         choice = input('"Y" to create backup, '
    #                                        '"N" to overwrite, or '
    #                                        f'"S" to skip updating the {str.replace(asset, "_", " ")}: ')
    #                         if choice.lower() == 'y' or choice.lower() == 'yes':
    #                             back_up_sprites = True
    #                             break
    #                         elif choice.lower() == 'n' or choice.lower() == 'no':
    #                             break
    #                         elif choice.lower() == 's':
    #                             update_sprites = False
    #                             break
    #                         else:
    #                             print('Please answer "Y" for yes, "N" for no, or "S" to skip.')
    #     else:
    #         os.makedirs(_ASSETS[asset]['location'], exist_ok=True)
    #
    #     if update_sprites:
    #         if back_up_sprites and os.path.exists(_ASSETS[asset]['location']):
    #             back_up_folder('custom', _ASSETS[asset]['location'])
    #
    #         # Extract the new update
    #         extract_archive(local_filename, _ASSETS[asset]['location'] or os.getcwd())
    #         print(f'{str.replace(asset.title(), "_", " ")} have been updated.')
    #         # Set the hash of the new character sprites update
    #         if config:
    #             if not config.has_section('Hashes'):
    #                 config.add_section('Hashes')
    #             if asset == 'character_sprites':
    #                 current_hash = get_directory_hash(_ASSETS[asset]['location'] + '/sprites')
    #                 set_config_valueHashes', asset, md5_update_from_file(_ASSETS[asset]['location'] +
    #                                                                  '/spritereplacements.txt',
    #                                                                  current_hash).hexdigest())
    #             elif asset == 'monster_sprites':
    #                 set_config_value('Hashes', asset,
    #                                  get_directory_hash(_ASSETS[asset]['location']).hexdigest())
    #
    #         if asset == 'monster_sprites':
    #             print(f'Updating remonsterate files.')
    #             update_remonsterate()
    #             print(f'Remonsterate files updated.')
    #
    #         set_config_value('Version', asset, data['tag_name'])
    #     else:
    #         print(f'{str.replace(asset.title(), "_", " ")} update skipped.')


def run_updates(force_download=False, calling_program=None):
    global updated
    global caller
    global remaining_api_calls

    caller = calling_program
    running_os = platform.system()

    try:
        get_web_token()
    except KeyError as ex:
        print(str(ex))
        return

    # Reorder the assets so updater is first, in case somebody reorders _ASSETS
    #   It's better to update the updater first in case it affects the rest of the process.
    ordered_assets = {'core': _ASSETS.get('core'), 'custom': _ASSETS.get('custom'), **_ASSETS}

    for asset in ordered_assets:
        remaining_api_calls = get_remaining_api_calls()
        if remaining_api_calls < 2:
            # Updating an asset requires two API calls: To get the release info, then to download the update
            print('Unable to update remaining assets: GitHub API calls have been exhausted. '
                  'Please try again at the top of the next hour.')
            break
        if asset == 'core' and running_os != 'Windows':
            print('Cannot update randomizer executable for non-Windows OS.')
            continue

        skip_update = False

        # If the version in the config file is greater than or equal to the version in GitHub, we can initially set
        #   skip_update to True.
        if not asset == 'custom':
            # print('Analyzing asset ' + asset)
            # print(str(asset) + ' version number: ' + str(get_config_value(section='Version', option=asset)))
            if get_config_value(section='Version', option=asset):
                github_version = send_get_request(_ASSETS[asset]['URL'])['tag_name']
                # print(str(asset) + ' GitHub version: ' + str(github_version))
                if get_config_value(section='Version', option=asset) >= github_version:
                    # print(str(asset) + ' being skipped because installed version is equal or greater than GitHub.\n')
                    skip_update = True
                # else:
                #     print(str(asset + ' updating because installed version is old.'))
            # else:
            #     print(str(asset + ' updating because there is no installed version recorded in config.'))

        if asset == 'custom':
            if not check_custom():
                # print(str(asset + ' asset is custom and there are no missing files.\n'))
                skip_update = True
            # else:
            #     print(str(asset + ' updating because there are missing files.'))

        # But if we discover that the files for the asset don't exist, we need to update regardless.
        if not os.path.exists(_ASSETS[asset]['location']):
            # print(str(asset + ' updating because asset location does not exist.'))
            skip_update = False

        if TEST and skip_update:
            # print(str(asset) + ' update would have been skipped, but is being forced because TEST mode is on.')
            skip_update = False

        if skip_update:
            continue

        if asset == 'custom' and _ASSETS['core']['data']:
            # If we already had core data retrieved, we can reuse it
            #   Though this should never happen: the whole process restarts completely after core finishes
            _ASSETS[asset]['data'] = _ASSETS['core']['data']
            update_asset_from_web(asset)
        else:
            # Retrieve the updated asset data from GitHub
            _ASSETS[asset]['data'] = send_get_request(url=_ASSETS[asset]['URL'])

            # In the asset, get the ['data']. From the data, get the ['assets'] (releases) returned from GitHub. We want
            # index [0], presumably the newest release, and then we get the download ['size'] attribute from that
            download_size = int(_ASSETS[asset]['data']['assets'][0]['size'])
            if download_size < 1000:
                size_suffix = 'Bytes'
            elif download_size < 1000000:
                size_suffix = 'KB'
                download_size = round(download_size / 1000, 2)
            elif download_size < 1000000000:
                size_suffix = 'MB'
                download_size = round(download_size / 1000000, 2)
            else:
                size_suffix = 'GB'
                download_size = round(download_size / 1000000000, 2)

            # We force download custom, because otherwise randomization cannot run.
            if not force_download and not asset == 'custom':
                response = prompt(prompt_type='yesno',
                                  message=_ASSETS[asset]['prompt'] + 'The download size is ' +
                                  str(download_size) + ' ' + size_suffix + '.')
            else:
                response = True

            if not response:
                print(f'Skipping {asset.replace("_", " ")} update.\n')
                continue

            print(f'Updating the Beyond Chaos {asset.replace("_", " ")}...')
            if asset == 'core':
                update_asset_from_web(asset)
            elif not asset == 'core':
                update_asset_from_web(asset)
            else:
                print("Skipping core download because we're testing.")
                if asset == 'core':
                    if isinstance(caller, QApplication):
                        shutil.copy(GUI_PATH, os.path.splitext(GUI_PATH)[0] + '.old' +
                                    os.path.splitext(GUI_PATH)[1])
                    elif caller == 'console':
                        shutil.copy(CONSOLE_PATH, os.path.splitext(CONSOLE_PATH)[0] + '.old' +
                                    os.path.splitext(CONSOLE_PATH)[1])

            if asset == 'core':
                if running_os == 'Windows' and os.path.isfile(os.path.join(BASE_DIRECTORY, 'BeyondChaos.exe')):
                    prompt(
                        prompt_type='notify',
                        message=f'The Beyond Chaos {asset.replace("_", " ")} ' +
                                ('have' if asset.endswith('s') else 'has') +
                                ' been updated. The application must now '
                                'restart and continue updating.'
                    )
                    new_args = sys.argv
                    new_args.append('update')
                    if isinstance(caller, QApplication):
                        subprocess.Popen(
                            args=new_args,
                            executable='BeyondChaos.exe'
                        )
                    elif caller == 'console':
                        subprocess.Popen(
                            args=new_args,
                            executable='beyondchaos_console.exe'
                        )
                    os.system('cls' if os.name == 'nt' else 'clear')
                    sys.exit()
                else:
                    prompt(
                        prompt_type='notify',
                        message=f'The Beyond Chaos {asset.replace("_", " ")} ' +
                                ('have' if asset.endswith('s') else 'has') +
                                ' been updated. Please restart the application and continue updating.'
                    )
                    sys.exit()

            else:
                print(f'The Beyond Chaos {asset.replace("_", " ")} ' +
                      ('have' if asset.endswith('s') else 'has') + ' been updated.\n')

    update_remonsterate()

    print('Recording version information in config.ini.')
    with open(CONFIG_PATH, 'w') as new_config_file:
        config.write(new_config_file)

    if updated:
        prompt(
            prompt_type='notify',
            message='All update tasks have been completed successfully! '+
                    'The application must now restart to apply all updates.'
        )
        if isinstance(caller, QApplication):
            try:
                subprocess.Popen(
                    args=[],
                    executable='BeyondChaos.exe'
                )
            except FileNotFoundError:
                prompt(
                    prompt_type='error',
                    message='Failed to restart the randomizer: Could not locate BeyondChaos.exe. '
                            'Please restart the application manually.'
                )
        elif caller == 'console':
            try:
                subprocess.Popen(
                    args=[],
                    executable='beyondchaos_console.exe'
                )
            except FileNotFoundError:
                prompt(
                    prompt_type='error',
                    message='Failed to restart the randomizer: Could not locate BeyondChaos_Console.exe. '
                            'Please restart the application manually.'
                )
        # Still clear the console, otherwise console output will still be there after restart
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.exit()
    else:
        prompt(
            prompt_type='notify',
            message='No updates were performed.'
        )
        os.system('cls' if os.name == 'nt' else 'clear')


def update_remonsterate(force=False):
    global updated
    from remonsterate.remonsterate import (construct_tag_file_from_dirs, generate_sample_monster_list,
                                           generate_tag_file)
    # Create the remonsterate directory in the game directory
    base_directory = os.path.join(os.getcwd(), 'remonsterate')
    sprite_directory = os.path.join(base_directory, 'sprites')
    image_file = os.path.join(base_directory, 'images_and_tags.txt')
    monster_file = os.path.join(base_directory, 'monsters_and_tags.txt')

    if not os.path.exists(base_directory):
        os.makedirs(base_directory)
        print('Created the remonsterate folder.')

    if not os.path.exists(sprite_directory):
        os.makedirs(sprite_directory)
        print('Created the sprites subfolder in the remonsterate folder.')

    # Generate images_and_tags.txt file for remonsterate based on the sprites in the sprites folder
    if not os.path.isfile(image_file) or force:
        try:
            construct_tag_file_from_dirs(sprite_directory, image_file)
            print('New images_and_tags.txt file generated in the remonsterate folder.')
            updated = True
        except IOError:
            generate_tag_file(image_file)
            if not os.path.isfile(image_file):
                print('Error: Failed to automatically generate an image_and_tags.txt file using the contents of your '
                      'remonsterate sprites subfolder. '
                      'Also failed to generate a blank template image_and_tags.txt file.')
                updated = True
            else:
                print('Error: Failed to automatically generate an image_and_tags.txt file using the contents of your '
                      'remonsterate sprites subfolder. '
                      'A blank template image_and_tags.txt file has been created instead.')

    if not os.path.isfile(monster_file) or force:
        generate_sample_monster_list(monster_file)
        updated = True
        print('Generated a template monsters_and_tags.txt file in the remonsterate folder.')


# saves the file to the directory you ran the exe from, the file will be in a zip format
def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_filename


def validate_required_files():
    # Return values:
    # 1) Array of strings representing missing information
    # 2) Boolean that indicates whether the update is required or optional
    # May raise requests.exceptions.ConnectionError if the user is offline
    missing_files = []
    missing_files.extend(check_custom())
    missing_files.extend(check_ini())

    # Missing files are required for the randomizer to function properly, so it triggers a forced update
    if missing_files:
        return missing_files


def list_available_updates(refresh=False):
    global available_updates
    if available_updates and not refresh:
        # Returned cached updates
        return available_updates

    available_updates = []
    if not internet_connectivity_available():
        return available_updates

    try:
        get_web_token()
    except KeyError as ex:
        print(str(ex))
        return []

    for asset in _ASSETS:
        # Don't look for custom here. Custom is only updated if required files are missing.
        if asset == 'custom':
            continue

        version = get_config_value(section='Version', option=asset)
        github_version = send_get_request(
            _ASSETS[asset]['URL']
        )['tag_name']

        if not version:
            available_updates.append(f'{asset.title().replace("_", " ")} version '
                                     f'' + github_version + ' is available for download.')
        elif not version >= github_version:
            available_updates.append(f'The Beyond Chaos {asset.replace("_", " ")} are '
                                     f'currently version ' +
                                     str(version) + '. '
                                     'Version ' + github_version + ' is available.')
    return available_updates


if __name__ == '__main__':
    args = sys.argv
    for arg in args:
        if isinstance(arg, str) and arg.startswith('-pid '):
            parent_process_id = arg[len('-pid '):]

    if internet_connectivity_available():
        run_updates()
    else:
        print('ERROR: No internet connection is available. '
              'Please connect to the internet and try running the updater again.')
        input('Press any key to exit...')
