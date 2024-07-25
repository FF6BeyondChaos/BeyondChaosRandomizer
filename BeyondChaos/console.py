import re
import requests.exceptions
import os
import sys
from multiprocessing import Process, Pipe

from randomizer import randomize
from update import validate_required_files, run_updates, list_available_updates, check_ini
from config import (VERSION, BETA, SUPPORTED_PRESETS, MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2,
                    get_config_items, set_config_value, config)
from utils import pipe_print
from options import get_makeover_groups

get_makeover_groups()


def run_console():
    if not BETA:
        try:
            requests.head(url='http://www.google.com')
            validation_result = validate_required_files()
            pipe_print(f'You are using Beyond Chaos CE Randomizer version {VERSION}.')

            while check_ini():
                print(
                    'Welcome to Beyond Chaos Community Edition!\n\n',
                    'As part of first time setup, ',
                    'we need to download the required custom '
                    'files and folders for randomization.\n',
                    'Enter "Y" to launch the updater and download the required files, otherwise enter '
                    '"N" to exit the program.'
                )
                response = input('>')
                if response.lower() == 'n':
                    sys.exit()
                elif response.lower() == 'y':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    run_updates(force_download=True, calling_program='console')
                else:
                    input('Please press "Y" to update or "N" to exit. Press enter to try again.')

            while validation_result:
                print(
                    'Welcome to Beyond Chaos Community Edition!\n\n' +
                    'Files required for the randomizer to function are currently missing: \n' +
                    '\n'.join(validation_result) +
                    '\n\n' +
                    'Enter "Y" to launch the updater and download the required files, otherwise enter '
                    '"N" to exit the program.'
                )
                response = input('>')
                if response.lower() == 'n':
                    sys.exit()
                elif response.lower() == 'y':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    run_updates(force_download=True, calling_program='console')
                    validation_result = validate_required_files()
                else:
                    input('Please press "Y" to update or "N" to exit. Press enter to try again.')

            available_updates = list_available_updates(refresh=True)
            while available_updates:
                pipe_print(
                    'Updates to Beyond Chaos are available!\n\n' +
                    str('\n\n'.join(available_updates)) +
                    '\nWould you like to update? Y/N'
                )
                response = input('>')
                if response.lower() == 'n':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    break
                elif response.lower() == 'y':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    run_updates(calling_program='console')
                    available_updates = list_available_updates(refresh=True)
                else:
                    input('Please press "Y" to update or "N" to skip. Press enter to try again.')

        except requests.exceptions.ConnectionError:
            pipe_print('No internet connection detected. Skipping update check.')
            pass

    # Get the path to the user's ROM file
    infile_rom_path = None
    while not infile_rom_path:
        saved_infile_path = config.get('Settings', 'input_path', fallback='')
        saved_path_text = f' (blank for default: {saved_infile_path})' if saved_infile_path else ''
        infile_rom_path = input(f'Please input the path to your copy of the FF3 US 1.0 rom. '
                                f'{saved_path_text}:\n> ').strip()

        # If no input was supplied
        if not infile_rom_path:
            infile_rom_path = saved_infile_path

        infile_rom_path = infile_rom_path.strip('"')
        infile_rom_path = os.path.abspath(infile_rom_path)

        # Make sure the supplied path is a file.
        if not os.path.isfile(infile_rom_path):
            input('The supplied path was not to a valid file. Press enter to try again.')
            infile_rom_path = None
        else:
            try:
                with open(infile_rom_path, 'rb') as rom_file:
                    rom_data = rom_file.read()
                from hashlib import md5
                if os.stat(infile_rom_path).st_size not in [3145728, 3145728 + 0x200] or \
                        md5(rom_data).hexdigest() not in [MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2]:
                    continue_randomization = input('The supplied ROM had an unusual size or did not match the '
                                                   'hash of known good ROM files. Continue? (Y/N)>')
                    if str(continue_randomization).lower() == 'n':
                        infile_rom_path = None
            except IOError:
                input('The file at the supplied path could not be read. Press enter to try again.')
                infile_rom_path = None

        os.system('cls' if os.name == 'nt' else 'clear')

    os.system('cls' if os.name == 'nt' else 'clear')

    # Get the path the user wants to save the randomized ROM file
    outfile_rom_path = None
    while not outfile_rom_path:
        saved_outfile_path = config.get('Settings', 'output_path', fallback='')
        # Use the last directory from config.ini. If no last directory, default to the same directory as the infile.
        saved_outfile_text = f' (blank for default: {saved_outfile_path})' if saved_outfile_path else \
            f' (blank for default: {os.path.dirname(infile_rom_path)})'
        outfile_rom_path = input(f'Please input the directory to place the randomized ROM file. '
                                 f'{saved_outfile_text}:\n> ').strip().strip('"')

        if not outfile_rom_path and saved_outfile_path:
            outfile_rom_path = saved_outfile_path
        elif not outfile_rom_path and not saved_outfile_path:
            outfile_rom_path = os.path.dirname(infile_rom_path)

        print(str(outfile_rom_path))
        # Make sure the supplied path is valid.
        if not os.path.isdir(outfile_rom_path):
            input('The supplied path was not valid. Press enter to try again.')
            outfile_rom_path = None

        os.system('cls' if os.name == 'nt' else 'clear')

    os.system('cls' if os.name == 'nt' else 'clear')

    # Get the user's game mode
    from options import ALL_MODES
    selected_mode = None
    while not selected_mode:
        for i, mode in enumerate(ALL_MODES):
            pipe_print('{}. {} - {}'.format(i + 1, mode.name, mode.description))
        selected_mode = input('\nEnter desired mode number or name:\n>').strip()
        try:
            selected_mode = int(selected_mode) - 1
            selected_mode = ALL_MODES[selected_mode]
        except ValueError:
            mode_name_match = False
            for mode in ALL_MODES:
                if str(selected_mode).lower() == str(mode.name).lower():
                    selected_mode = mode
                    mode_name_match = True
                    break
            if not mode_name_match:
                input('The supplied input was not a number. Press enter to try again.')
                selected_mode = None

        os.system('cls' if os.name == 'nt' else 'clear')

    os.system('cls' if os.name == 'nt' else 'clear')

    # Flag activation
    from options import ALL_FLAGS
    active_flags = []
    categories = []
    for flag in ALL_FLAGS:
        if flag.category.lower() in ['cave', 'holiday']:
            continue
        if (flag.category[0].capitalize() + flag.category[1:]) not in categories:
            categories.append(flag.category[0].capitalize() + flag.category[1:])

    characters_per_row = 150
    batch = 0
    seed = ''
    flag_input = ''
    flag_string = ''
    bingo_type = None
    bingo_size = None
    bingo_difficulty = None
    bingo_cards = None

    speed_dials = get_config_items('Speeddial').items()

    operations = ['Enter one or more flags.',
                  'Enter a speed dial or preset.',
                  'Submit a full flag string.',
                  'Leave blank to finish.',
                  'Enter "list <category>" to list the available flags in a category.']

    operation_string = '   '
    current_operations = 0
    for operation in operations:
        operation_string += '•' + operation.ljust(35)
        current_operations += 1
        if current_operations == 3:
            operation_string += '\n   '
            current_operations = 0
    operation_string = operation_string.rstrip()

    category_string = ''
    current_characters = 0
    for category in categories:
        category_string += category + ', '
        current_characters += len(category + ', ')
        if current_characters >= characters_per_row:
            category_string += '\n    '
            current_characters = 0
    category_string = category_string.strip(', ')

    preset_string = ''
    current_characters = 0
    for preset in SUPPORTED_PRESETS.keys():
        preset_string += preset.title() + ', '
        current_characters += len(preset.title() + ', ')
        if current_characters >= characters_per_row:
            preset_string += '\n    '
            current_characters = 0
    preset_string = preset_string.strip(', ')

    speed_dial_list = ''
    if speed_dials:
        for number, flags in speed_dials:
            if len(flags) > characters_per_row:
                current_characters = 0
                current_flags = flags.split(' ')
                speed_dial_flag_string = ''
                for flag in current_flags:
                    speed_dial_flag_string += flag + ' '
                    current_characters += len(flag + ' ')
                    if current_characters >= characters_per_row:
                        speed_dial_flag_string += '\n    '
                        current_characters = 0
                speed_dial_list += f'  ({number}) - {speed_dial_flag_string}\n'
            else:
                speed_dial_list += f'  ({number}) - {flags}\n'
        speed_dial_list = speed_dial_list[:-1]

    while (not flag_string) or not flag_input == '':
        flag_string = '\n    ' if len(active_flags) > 0 else ''
        current_characters = 0
        for flag in ALL_FLAGS:
            for active_flag in active_flags:
                if active_flag == flag:
                    new_flag = f'{active_flag.name}:{active_flag.value} ' \
                        if not active_flag.input_type == 'boolean' \
                        else f'{active_flag.name} '
                    flag_string += new_flag
                    current_characters += len(new_flag)
                    if current_characters >= characters_per_row:
                        flag_string += '\n    '
                        current_characters = 0

        if flag_string:
            pipe_print(f'Current flag string: {flag_string}')

        pipe_print(f'Perform one of the following actions:\n' +
                   operation_string + '\n' +
                   'Valid categories are: '.ljust(23) + category_string + '.\n' +
                   'Valid presets are: '.ljust(23) + preset_string + '.')
        if speed_dial_list:
            pipe_print('Valid speed dial numbers are: \n' + speed_dial_list)
        flag_input = input('>')
        skip_error = False
        if flag_input.lower().startswith('list'):
            skip_error = True
            try:
                help_category = flag_input.lower()[flag_input.index(' ') + 1:]
                flag_input = ''
                if help_category.lower() in [category.lower() for category in categories]:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    flag_output_string = ''
                    index = 0
                    set_length = 5
                    longest = 0
                    for flag in ALL_FLAGS:
                        if str(flag.category).lower() == str(help_category).lower():
                            if len(flag.name) > longest:
                                longest = len(flag.name)
                    for flag in ALL_FLAGS:
                        if str(flag.category).lower() == str(help_category).lower():
                            flag_output_string += (f'   •{str.ljust(flag.name, longest, " ")} - '
                                                   f'{flag.long_description}\n')
                            index += 1
                            if index >= set_length:
                                pipe_print(f'\nValid flags in category {help_category} are as follows:')
                                pipe_print(flag_output_string[:-1])
                                flag_input += input(f'If you see any flags you would like to activate, '
                                                    f'enter them separated by spaces and then press enter '
                                                    f'to view the next {str(set_length)} flags.\n>') + ' '
                                os.system('cls' if os.name == 'nt' else 'clear')
                                flag_output_string = ''
                                index = 0
                    if flag_output_string:
                        pipe_print(f'\nValid flags in category {help_category} are as follows:')
                        pipe_print(flag_output_string)
                        flag_input += input('If you see any flags you would like to activate, '
                                            'enter them separated by spaces and then press enter '
                                            'to continue back to flag selection.\n>')
                    os.system('cls' if os.name == 'nt' else 'clear')
                    flag_input = flag_input.strip()
                else:
                    input('The supplied category did not exist. Press enter to try again.')
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
            except ValueError:
                input('No category was supplied. Press enter to try again.')
                os.system('cls' if os.name == 'nt' else 'clear')
                continue

        if len(flag_input) > 0:
            if len(flag_input) == 1 and re.match('[0-9]', flag_input):
                flag_input = config.get('Speeddial', flag_input, fallback=None)
                if flag_input is None:
                    input('The number input was not a valid speed dial. Press enter to try again.')
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                active_flags = []
            if '|' in flag_input:
                try:
                    seed = flag_input.split('|')[3]
                except IndexError:
                    pass
                flag_input = flag_input.split('|')[2]
                active_flags = []
            if flag_input.lower() in SUPPORTED_PRESETS.keys():
                flag_input = SUPPORTED_PRESETS[flag_input.lower()]
                active_flags = []
            input_flag_list = flag_input.split(' ')
            for input_flag in input_flag_list:
                input_flag_found = False
                if ':' in input_flag:
                    flag_value = input_flag.split(':')[1].strip()
                    input_flag = input_flag.split(':')[0].strip()
                else:
                    flag_value = None
                for flag in ALL_FLAGS:
                    if flag.name == input_flag:
                        input_flag_found = True
                        while True:
                            if flag.input_type.lower() == 'combobox':
                                if not flag_value:
                                    flag_value = input(f'Choose a value for {input_flag}. '
                                                       f'Valid values are the following: '
                                                       f'{flag.choices}\n').lower()
                                if flag_value.lower() not in [str(choice).lower() for choice in flag.choices]:
                                    input(f'The flag value for {flag.name} was not valid. Press enter to try again.')
                                    os.system('cls' if os.name == 'nt' else 'clear')
                                    flag_value = None
                                elif flag_value.lower() == str(flag.default_value.lower()):
                                    try:
                                        active_flags.remove(flag)
                                    except ValueError:
                                        pass
                                    break
                                else:
                                    flag.value = flag_value
                                    if flag not in active_flags:
                                        active_flags.append(flag)
                                        os.system('cls' if os.name == 'nt' else 'clear')
                                    break
                            elif flag.input_type.lower() == 'integer':
                                if not flag_value:
                                    flag_value = input(f'Choose a value for {input_flag}. '
                                                       f'Valid values are numbers '
                                                       f'between {str(flag.minimum_value)} and '
                                                       f'{str(flag.maximum_value)}\n').lower()
                                try:
                                    if not (flag.minimum_value <=
                                            int(flag_value.lower()) <=
                                            flag.maximum_value):
                                        input(f'The flag value for {flag.name} was not valid. '
                                              f'Press enter to try again.')
                                        os.system('cls' if os.name == 'nt' else 'clear')
                                        flag_value = None
                                    elif int(flag_value) == flag.default_value:
                                        try:
                                            active_flags.remove(flag)
                                        except ValueError:
                                            pass
                                        break
                                    else:
                                        flag.value = flag_value
                                        if flag not in active_flags:
                                            active_flags.append(flag)
                                            os.system('cls' if os.name == 'nt' else 'clear')
                                        break
                                except ValueError:
                                    input('That flag value must be a whole number. Press enter to try again.')
                                    os.system('cls' if os.name == 'nt' else 'clear')
                                    flag_value = None
                            elif flag.input_type.lower() == 'float2':
                                if not flag_value:
                                    flag_value = input(f'Choose a value for {input_flag}. '
                                                       f'Valid values are numbers '
                                                       f'between {str(flag.minimum_value)} and '
                                                       f'{str(flag.maximum_value)}\n').lower()
                                try:
                                    if not (flag.minimum_value <=
                                            float(flag_value.lower()) <=
                                            flag.maximum_value):
                                        input(f'The flag value for {flag.name} was not within the acceptable range of '
                                              f'{flag.minimum_value}. '
                                              f'Press enter to try again.')
                                        os.system('cls' if os.name == 'nt' else 'clear')
                                        flag_value = None
                                    elif format(float(flag_value), '.2f') == flag.default_value:
                                        try:
                                            active_flags.remove(flag)
                                        except ValueError:
                                            pass
                                        break
                                    else:
                                        flag.value = flag_value
                                        if flag not in active_flags:
                                            active_flags.append(flag)
                                            os.system('cls' if os.name == 'nt' else 'clear')
                                        break
                                except ValueError:
                                    input('That flag value must be a whole number. Press enter to try again.')
                                    os.system('cls' if os.name == 'nt' else 'clear')
                                    flag_value = None
                            elif flag.input_type.lower() == 'boolean':
                                flag_value = True
                                if flag in active_flags:
                                    try:
                                        active_flags.remove(flag)
                                    except ValueError:
                                        pass
                                    break
                                else:
                                    flag.value = True
                                    if flag not in active_flags:
                                        active_flags.append(flag)
                                        os.system('cls' if os.name == 'nt' else 'clear')
                                    break
                if not input_flag_found:
                    input(f'Error: The following flag was not a valid flag: {input_flag}. Press enter to try again.')
                    os.system('cls' if os.name == 'nt' else 'clear')
        elif not skip_error and len(flag_input) == 0 and not flag_string:
            input('You must select at least one flag to continue. Press enter to try again.')
            os.system('cls' if os.name == 'nt' else 'clear')

    os.system('cls' if os.name == 'nt' else 'clear')

    flag_string = ''
    for flag in ALL_FLAGS:
        for active_flag in active_flags:
            if active_flag == flag:
                flag_string += f'{active_flag.name}:{active_flag.value} ' if not active_flag.input_type == 'boolean' \
                    else f'{active_flag.name} '

    # Speed dial save
    while True:
        save_speed_dial = input('If you would like to save these flags to a speeddial, enter a single-digit integer. '
                                'Otherwise, leave blank to skip:\n').strip()
        if not save_speed_dial:
            break
        elif len(save_speed_dial) == 1 and re.match('[0-9]', save_speed_dial):
            set_config_value('Speeddial', save_speed_dial, flag_string)
            break
        else:
            input('An invalid value was supplied. Please leave the prompt blank to skip or enter a single-digit '
                  'integer to save the flags to a speeddial. Press enter to try again.')

    os.system('cls' if os.name == 'nt' else 'clear')

    if 'bingoboingo' in flag_string:
        pipe_print('Welcome to Beyond Chaos Bingo!')
        while not bingo_type:
            pipe_print('What type of squares would you like to appear on your bingo card? (blank for all)')
            pipe_print('  •a   Abilities\n'
                       '  •i   Items\n'
                       '  •m   Monsters\n'
                       '  •s   Spells')
            pipe_print('Example: Type "am" or "ma" for Abilities and Monsters.')
            bingo_type = input('>')
            if not bingo_type:
                bingo_type = 'aims'
            unknown_characters = [character for character in bingo_type if character not in ['a', 'i', 'm', 's']]
            if unknown_characters:
                input('The following options were not recognized: ' +
                      str(unknown_characters).replace('[', '').replace(']', '') +
                      '. Press enter to try again.'
                      )
                bingo_type = ''
            os.system('cls' if os.name == 'nt' else 'clear')

        while not bingo_size:
            try:
                bingo_size = input('What size bingo grid would you like to create? Leave blank for a default '
                                   '5x5 grid.\n>')
                if not bingo_size:
                    bingo_size = 5
                else:
                    bingo_size = int(bingo_size)
                if bingo_size < 1:
                    input('The size of the bingo card must be greater than 0. '
                          'Press enter to try again')
                    bingo_size = None
            except ValueError:
                input('The supplied input was not a number. '
                      'You must supply a positive whole number greater than zero. '
                      'Press enter to try again')
                bingo_size = None
            os.system('cls' if os.name == 'nt' else 'clear')

        while not bingo_difficulty:
            bingo_difficulty = input('What difficulty level? Easy, Normal, or Hard? (e/n/h)\n>').lower()
            if not bingo_difficulty.lower() in ['easy', 'normal', 'hard', 'e', 'n', 'h']:
                input('Please enter "E" for easy, "N" for normal, or "H" for hard. Press enter to try again.')
                bingo_difficulty = ''
            else:
                bingo_difficulty = bingo_difficulty[0]
            os.system('cls' if os.name == 'nt' else 'clear')

        while not bingo_cards:
            try:
                bingo_cards = input('How many bingo cards would you like to generate? Leave blank for 1.\n>')
                if not bingo_cards:
                    bingo_cards = 1
                else:
                    bingo_cards = int(bingo_cards)
                if bingo_cards < 1:
                    input('The number of bingo cards must be greater than 0. '
                          'Press enter to try again')
                    bingo_cards = None
            except ValueError:
                input('The supplied input was not a number. '
                      'You must supply a positive whole number greater than zero. '
                      'Press enter to try again')
                bingo_cards = None
            os.system('cls' if os.name == 'nt' else 'clear')

    # Seed
    while not seed:
        seed = input('Enter a seed number or leave blank to generate a random seed:\n>').strip()
        if not seed:
            from time import time
            seed = int(time())
        else:
            try:
                seed = int(seed)
            except ValueError:
                input('The supplied seed was not a number. Press enter to try again.')
                seed = None

    os.system('cls' if os.name == 'nt' else 'clear')

    # Batch
    while batch == 0:
        batch = input('Enter a batch number or leave blank to generate 1 rom file:\n>').strip()
        if not batch:
            batch = 1
        else:
            try:
                batch = int(batch)
            except ValueError:
                input('The supplied value was not a number. Press enter to try again.')
                batch = 0

    for index in range(batch):
        os.system('cls' if os.name == 'nt' else 'clear')
        pipe_print(f'Performing generation {str(index + 1)} of {str(batch)}.')
        kwargs = {
            'infile_rom_path': infile_rom_path,
            'outfile_rom_path': outfile_rom_path,
            'seed': str(VERSION) + '|' + selected_mode.name + '|' + flag_string + '|' + str(seed + index),
            'bingo_type': bingo_type,
            'bingo_size': bingo_size,
            'bingo_difficulty': bingo_difficulty,
            'bingo_cards': bingo_cards,
            'application': 'console'
        }
        parent_connection, child_connection = Pipe()
        randomize_process = Process(
            target=randomize,
            args=(child_connection,),
            kwargs=kwargs
        )
        randomize_process.start()
        while True:
            if not randomize_process.is_alive():
                raise RuntimeError('Unexpected error: The process performing randomization died.')
            if parent_connection.poll(timeout=5):
                child_output = parent_connection.recv()
            else:
                child_output = None
            if child_output:
                try:
                    if isinstance(child_output, str):
                        pipe_print(child_output)
                    elif isinstance(child_output, Exception):
                        raise child_output
                    elif isinstance(child_output, bool):
                        break
                except EOFError:
                    break


if __name__ == '__main__':
    args = list(sys.argv)
    if len(args) == 1:
        run_console()
        input('Press enter to exit.')
    elif len(args) > 1 and args[1] == 'update':
        # Continue the updating process after updating the core files.
        if os.path.isfile(os.path.join(os.getcwd(), 'beyondchaos.old.exe')):
            os.remove(os.path.join(os.getcwd(), 'beyondchaos.old.exe'))
        if os.path.isfile(os.path.join(os.getcwd(), 'beyondchaos_console.old.exe')):
            os.remove(os.path.join(os.getcwd(), 'beyondchaos_console.old.exe'))
        run_updates(calling_program='console')
        run_console()
    elif len(args) > 1 and args[1] == '?':
        pipe_print(
            '\tBeyond Chaos Randomizer Community Edition, version ' +
            VERSION +
            '\n'
            '\t\tOptional Keyword Arguments:\n'
            '\t\tsource=<file path to your vanilla Final Fantasy 3 v1.0 ROM file>\n'
            '\t\tdestination=<directory path where you want the randomized ROM and spoiler log created>\n'
            '\t\tseed=<flag and seed information in the format version.mode.flags.seed>\n'
            '\t\tbingo_type=<The desired bingo options, if you are using the bingoboingo flag>\n'
            '\t\tbingo_size=<The desired positive integer for the size of bingo card, '
            'if you are using the bingoboingo flag>\n'
            '\t\tbingo_difficulty=<The desired bingo difficulty selection, if you are using the bingoboingo flag>\n'
            '\t\tbingo_cards=<The desired positive integer for number of bingo cards to generate, '
            'if you are using the bingoboingo flag>\n'
        )
        sys.exit()
    else:
        try:
            source_arg = None
            seed_arg = None
            destination_arg = None
            bingo_type_arg = 'aims'
            bingo_size_arg = 5
            bingo_difficulty_arg = 'n'
            bingo_cards_arg = 1
            for argument in args[1:]:
                if 'source=' in argument:
                    source_arg = argument[argument.index('=') + 1:]
                elif 'seed=' in argument:
                    seed_arg = argument[argument.index('=') + 1:]
                elif 'destination=' in argument:
                    destination_arg = argument[argument.index('=') + 1:]
                elif 'bingo_type=' in argument:
                    bingo_type_arg = argument[argument.index('=') + 1:]
                elif 'bingo_size=' in argument:
                    bingo_size_arg = int(argument[argument.index('=') + 1:])
                elif 'bingo_difficulty=' in argument:
                    bingo_difficulty_arg = argument[argument.index('=') + 1:]
                elif 'bingo_cards=' in argument:
                    bingo_cards_arg = int(argument[argument.index('=') + 1:])
                else:
                    pipe_print('Keyword unrecognized or missing: ' + str(
                        argument) + '.\nUse "python randomizer.py ?" to view a list of valid keyword arguments.')

            randomize(
                infile_rom_path=source_arg,
                seed=seed_arg,
                outfile_rom_path=destination_arg,
                bingotype=bingo_type_arg,
                bingosize=bingo_size_arg,
                bingodifficulty=bingo_difficulty_arg,
                bingocards=bingo_cards_arg,
                application='console'
            )
            input('Press enter to close this program.')
        except Exception as exc:
            pipe_print('ERROR: ' + str(exc) + '\nTo view valid keyword arguments, use "python randomizer.py ?"')
            import traceback

            traceback.print_exc()
            input('Press enter to quit.')
