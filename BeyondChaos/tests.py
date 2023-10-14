from randomizer import VERSION

SOURCE_FILE = ''
OUTPUT_PATH = ''
TEST_SEED = ('CE-5.1.1|normal|c f h i m n o p q r s t u y z makeover partyparty capslockoff nicerpoison notawaiter '
             'removeflashing:all cursepower:1 dancingmaduin:chaos expboost:2.0 gpboost:1.5 madworld masseffect:random '
             'mpboost:1.5 rushforpower mimetime nomiabs questionablecontent randomboost:0 relicmyhat mementomori:14 '
             'naturalmagic supernatural thescenarionottaken treaffect frenchvanilla girls:only|1695090942')
SKIP_FLAGS = ['remonsterate', 'bingoboingo']
INCLUDE_FLAGS = ['cursedencounters']


# Test a single generation, just like using TEST = True previously in randomizer.py
def test_generation(iterations: int = 1, generate_output_rom=True):
    from randomizer import randomize
    from multiprocessing import Pipe, Process
    for i in range(iterations):
        test_bundle = TEST_SEED.split('|')
        test_seed = test_bundle[len(test_bundle) - 1]
        test_seed = str(int(test_seed) + i)
        test_bundle[len(test_bundle) - 1] = test_seed
        kwargs = {
            'infile_rom_path': SOURCE_FILE,
            'outfile_rom_path': OUTPUT_PATH,
            'seed': '|'.join(test_bundle),
            'application': 'tester',
            'generate_output_rom': generate_output_rom
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
                raise RuntimeError('Unexpected error: The randomize child process died.')
            if parent_connection.poll(timeout=5):
                child_output = parent_connection.recv()
            else:
                child_output = None
            if child_output:
                try:
                    if isinstance(child_output, str):
                        print(child_output)
                    elif isinstance(child_output, Exception):
                        raise child_output
                    elif isinstance(child_output, bool):
                        break
                except EOFError:
                    break


# Test multiple generations. Choose a number of seeds to generate and a number of random flags those seeds should have.
# The selected mode is random too.
# Note that this method does not write any of the generated roms to disk.
def test_random_generation(iterations: int, num_flags: int, generate_output_rom=False, halt_on_exception=False):
    from options import ALL_FLAGS
    from options import ALL_MODES
    from randomizer import randomize
    from random import Random
    from time import time
    from multiprocessing import Pipe, Process

    random = Random()
    for index in range(iterations):
        try:
            all_testing_flags = [flag for flag in ALL_FLAGS if flag.name not in SKIP_FLAGS]
            current_flagstring = '' if not INCLUDE_FLAGS else ', '.join(INCLUDE_FLAGS) + ' '
            new_flags = random.sample(all_testing_flags, num_flags)
            for flag in new_flags:
                try:
                    if flag.inputtype == "integer":
                        # Choose a random value from within the allowed values
                        flag.value = random.randint(flag.minimum_value, flag.maximum_value)
                        if flag.value == flag.default_value:
                            continue
                        current_flagstring += str(flag.name) + ":" + str(flag.value)
                    elif flag.inputtype == "float2":
                        # Choose a random value from within the allowed values
                        flag.value = round(random.uniform(flag.minimum_value, flag.maximum_value), 2)
                        if flag.value == flag.default_value:
                            continue
                        current_flagstring += str(flag.name) + ":" + str(flag.value)
                    elif flag.inputtype == "combobox":
                        # Choose a random value from within the allowed values
                        flag.value = random.choice(flag.choices)
                        while flag.value == flag.default_value:
                            # Except do not allow the default_value, because that represents the flag being off
                            flag.value = random.choice(flag.choices)
                        current_flagstring += str(flag.name) + ":" + str(flag.value)
                    else:
                        current_flagstring += str(flag.name)
                    current_flagstring += " "
                except Exception:
                    print("Error setting and applying flag value for flag " + str(flag.name) + " on iteration " +
                          str(index) + ".")
            current_seed = str(VERSION) + "|" + \
                           str(random.choice(ALL_MODES).name) + "|" + \
                           str(current_flagstring) + "|" + \
                           str(int(time()))
            print(f"Running generation {index} with seed {str(current_seed)}")
            kwargs = {
                "infile_rom_path": SOURCE_FILE,
                "outfile_rom_path": OUTPUT_PATH,
                "seed": current_seed,
                "application": "tester",
                "generate_output_rom": generate_output_rom
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
                    raise RuntimeError("Unexpected error: The randomize child process died.")
                if parent_connection.poll(timeout=5):
                    item = parent_connection.recv()
                else:
                    item = None
                if item:
                    try:
                        if isinstance(item, str):
                            print(item)
                        elif isinstance(item, Exception):
                            raise item
                        elif isinstance(item, bool):
                            break
                    except EOFError:
                        break
            print("\n")
        except Exception as e:
            if halt_on_exception:
                raise e


def thorough_test(starting_combination=5):
    from options import ALL_FLAGS
    from options import ALL_MODES
    from itertools import combinations
    from multiprocessing import Pipe, Process
    from time import time
    from randomizer import randomize
    from random import choice, randint

    for num_flags in range(starting_combination, len(ALL_FLAGS) + 1):
        every_flag_combination = combinations(ALL_FLAGS, num_flags)
        for mode in ALL_MODES:
            for combination in every_flag_combination:
                flag_string = '' if not INCLUDE_FLAGS else ', '.join(INCLUDE_FLAGS)
                for flag in combination:
                    if flag.name in SKIP_FLAGS or (len(flag.name) > 1 and flag.name in flag_string):
                        continue
                    if flag.inputtype == 'combobox':
                        flag_string += flag.name + ':' + choice(flag.choices) + ' '
                    elif flag.inputtype == 'integer':
                        flag_string += flag.name + ':' + str(randint(flag.minimum_value, flag.maximum_value)) + ' '
                    elif flag.inputtype == 'float2':
                        flag_string += flag.name + ':' + str(randint(flag.minimum_value, flag.maximum_value)) + ' '
                    else:
                        flag_string += flag.name + ' '
                kwargs = {
                    'infile_rom_path': SOURCE_FILE,
                    'outfile_rom_path': OUTPUT_PATH,
                    'seed': '|'.join([VERSION, mode.name, flag_string, str(int(time()))]),
                    'application': 'tester',
                    'generate_output_rom': False
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
                        raise RuntimeError('An unexpected error preventing the randomize process from completing.')
                    if parent_connection.poll(timeout=5):
                        child_output = parent_connection.recv()
                    else:
                        child_output = None
                    if child_output:
                        try:
                            if isinstance(child_output, str):
                                print(child_output)
                            elif isinstance(child_output, Exception):
                                raise child_output
                            elif isinstance(child_output, bool):
                                break
                        except EOFError:
                            break


def test_esper_allocation():
    from esperrandomizer import get_espers
    from character import get_characters
    from random import Random
    from io import BytesIO

    random = Random()
    char_ids = list(range(12)) + [13]
    espers = get_espers(BytesIO(open(SOURCE_FILE, 'rb').read()))
    characters = [c for c in get_characters() if c.id in char_ids]
    preassigned_espers = random.sample(espers, len(characters))
    preassignments = {e: c for (e, c) in zip(preassigned_espers, characters)}

    test_range = 1000
    crusader_id = 15
    ragnarok_id = 16

    average_users_per_tier = {}
    average_users_per_esper = {}
    esperless_users = 0
    unique_users = set()
    for index in range(test_range):
        espers_per_tier = {}
        users_per_tier = {}
        users_per_esper = {}
        for e in espers:
            num_users = 1
            if e.id not in [crusader_id, ragnarok_id] and 20 - (4 * e.rank) >= random.random() * 100:
                num_users += 1
                while num_users < len(char_ids) and random.choice([True] + [False] * (e.rank + 2)):
                    num_users += 1
            users = random.sample(characters, num_users)
            if e in preassignments:
                c = preassignments[e]
                if c not in users:
                    users[0] = c
                    assert c in users
            for user in users:
                unique_users.add(user)
            # chars_requiring_espers = [c for c in chars_requiring_espers if c not in [u.id for u in users]]
            espers_per_tier[e.rank] = espers_per_tier.get(e.rank, 0) + 1
            users_per_tier[e.rank] = users_per_tier.get(e.rank, 0) + num_users
            users_per_esper[e.name] = users_per_esper.get(e.name, 0) + num_users
        assert len(unique_users) == len(char_ids)

        for key, value in users_per_tier.items():
            # Average the number of users per tier by dividing by the number of users by the number of espers in that tier
            users_per_tier[key] = value / espers_per_tier[key]
            average_users_per_tier[key] = average_users_per_tier.get(key, 0) + users_per_tier.get(key, 0)

        # Average the number of users per tier by dividing by the number of users by the number of espers in that tier
        for key, value in users_per_esper.items():
            average_users_per_esper[key] = average_users_per_esper.get(key, 0) + users_per_esper.get(key, 0)

    for key, value in average_users_per_tier.items():
        average_users_per_tier[key] = average_users_per_tier.get(key, 0) / test_range

    for key, value in average_users_per_esper.items():
        average_users_per_esper[key] = average_users_per_esper.get(key, 0) / test_range

    print('Average esperless characters: ' + str(esperless_users / test_range))
    print('Average users by esper tier (Original): ' + str(average_users_per_tier))
    print('Average users by esper (Original): ' + str(average_users_per_esper))

    print('\n')
    average_users_per_tier = {}
    average_users_per_esper = {}
    from math import pow

    for index in range(test_range):
        espers_per_tier = {}
        users_per_tier = {}
        users_per_esper = {}
        for e in espers:
            num_users = 1
            if e.id not in [crusader_id, ragnarok_id]:
                while num_users < len(char_ids) and 90 - (18 * e.rank + pow(1.25, num_users)) >= random.random() * 100:
                    num_users += 1
            espers_per_tier[e.rank] = espers_per_tier.get(e.rank, 0) + 1
            users_per_tier[e.rank] = users_per_tier.get(e.rank, 0) + num_users
            users_per_esper[e.name] = users_per_esper.get(e.name, 0) + num_users
        for key, value in users_per_tier.items():
            users_per_tier[key] = value / espers_per_tier[key]
            average_users_per_tier[key] = average_users_per_tier.get(key, 0) + users_per_tier.get(key, 0)
        for key, value in users_per_esper.items():
            average_users_per_esper[key] = average_users_per_esper.get(key, 0) + users_per_esper.get(key, 0)

    for key, value in average_users_per_tier.items():
        average_users_per_tier[key] = average_users_per_tier.get(key, 0) / test_range

    for key, value in average_users_per_esper.items():
        average_users_per_esper[key] = average_users_per_esper.get(key, 0) / test_range

    print('Average users by esper tier (Modified): ' + str(average_users_per_tier))
    print('Average users by esper (Modified): ' + str(average_users_per_esper))


if __name__ == "__main__":
    # test_generation(iterations=1, generate_output_rom=False)
    test_random_generation(iterations=100, num_flags=10, generate_output_rom=False, halt_on_exception=True)
    # thorough_test()
