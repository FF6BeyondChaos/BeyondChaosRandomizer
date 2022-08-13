import random
import re
import sys
from hashlib import md5
import os
import pathlib
import configparser
from shutil import copyfile
import time

from .options import ALL_MODES, ALL_FLAGS, Options_, generate_help
from .config import (get_input_path, get_output_path, save_input_path, save_output_path, get_items,
                     set_value)
from ._testing import _modify_args_for_testing

# to testing?
_KNOWN_HASHES = {
    "MD5HASHNORMAL": "e986575b98300f721ce27c180264d890",
    "MD5HASHTEXTLESS": "f08bf13a6819c421eee33ee29e640a1d",
    "MD5HASHTEXTLESS2": "e0984abc9e5dd99e4bc54e8f9e0ff8d0",
}

def _find_valid_rom():
    for filename in sorted(os.listdir('.')):
        if os.path.isdir(filename):
            continue
        if os.stat(filename).st_size in (0x300000, 0x300200):
            continue

        with open(filename, 'rb') as f:
            if md5(f.read()[-0x300000:]).hexdigest() in _KNOWN_HASHES.values():
                return filename
    return None

def _process_sourcefile(sourcefile, previous_rom_path=''):
    if not sourcefile:
        previous_input = f" (blank for default: {previous_rom_path})" if previous_rom_path else ""
        sourcefile = input(f"Please input the file name of your copy of "
                           f"the FF3 US 1.0 rom{previous_input}:\n> ").strip()
        print()

    sourcefile = pathlib.Path(sourcefile or previous_rom_path).resolve()
    if not sourcefile.is_file():
        response = input("File not found. Would you like to search the current directory \n"
                         "for a valid FF3 1.0 rom? (y/n) ") or 'y'
        if response[0].lower() == 'y':
            sourcefile = _find_valid_rom()

        if sourcefile is None:
            raise ValueError("Invalid ROM path supplied, and could not find valid ROM in current directory.")

    print(f"Success! Using valid rom file: {sourcefile}\n")
    return pathlib.Path(sourcefile)

def _process_output_dir(output_directory, previous_output_directory=''):
    if not output_directory:
        while True:
            # Input loop to make sure we get a valid directory
            previous_output = f" (blank for default: {previous_output_directory})"
            output_directory = input(
                f"Please input the directory to place the randomized ROM file. {previous_output}:\n> ").strip()
            print()

            output_directory = pathlib.Path(output_directory or previous_output_directory)
            if output_directory.is_dir():
                # Valid directory received. Break out of the loop.
                break
            else:
                print("That output directory does not exist. Please try again.")

    return output_directory

def _parse_seed(fullseed):
    try:
        version, mode_str, flags, seed = tuple(fullseed.split('|'))
    except ValueError:
        raise ValueError('Seed should be in the format <version>|<mode>|<flags>|<seed>')

    seed = seed.strip()
    seed = int(seed if seed else time.time())
    seed %= 10 ** 10

    return version, _parse_mode(mode_str), flags, seed

def _parse_mode(mode_str):
    try:
        mode_num = int(mode_str) - 1
    except ValueError:
        named_mode = [i for i, m in enumerate(ALL_MODES) if m.name == mode_str]
        mode_num = named_mode[0] if len(named_mode) == 1 else None
    return mode_num

def _process_seed(fullseed):
    if fullseed:
        return str(fullseed).strip()

    flaghelptext = '''!   Recommended new player flags
    -   Use all flags EXCEPT the ones listed'''

    fullseed = input("Please input a seed value (blank for a random "
                     "seed):\n> ").strip()
    print()

    if '.' not in fullseed:
        speeddials = get_items("Speeddial").items()
        mode_num = None
        while mode_num not in range(len(ALL_MODES)):
            print("Available modes (default is 'normal'):\n")
            for i, mode in enumerate(ALL_MODES):
                print("{}. {} - {}".format(i + 1, mode.name, mode.description))
            mode_str = input("\nEnter desired mode number or name:\n").strip() or "1"
            mode_num = _parse_mode(mode_str)

        mode = ALL_MODES[mode_num]
        allowed_flags = [f for f in ALL_FLAGS if f.name not in mode.prohibited_flags]

        print()
        for flag in sorted(allowed_flags):
            print(flag.name, flag.description)
        print(flaghelptext + "\n")
        print("Save frequently used flag sets by adding 0: through 9: before the flags.")
        for speeddial_number, speeddial_flags in speeddials:
            print("\t" + speeddial_number + ": " + speeddial_flags)
        print()
        while True:
            print("For a description of a given code, "
                  "input 'help <code>', e.g. 'help suplexwrecks gpboost'. "
                  "Input only 'help' for a list of available codes.")
            flags = input("Please input your desired flags (blank for "
                          "all of them):\n> ").strip()
            if flags == "!":
                flags = '-dfklu partyparty makeover johnnydmad'
            elif flags.strip().lower().startswith("help"):
                codes = [f.strip().lower() for f in flags.split(" ")] or None
                print(generate_help(codes=codes))
                continue
            break

        is_speeddialing = re.search("^[0-9]$", flags)
        if is_speeddialing:
            for speeddial_number, speeddial_flags in speeddials:
                if speeddial_number == flags[:1]:
                    flags = speeddial_flags.strip()
                    break

        saving_speeddial = re.search("^[0-9]:", flags)
        if saving_speeddial:
            set_value("Speeddial", flags[:1], flags[3:].strip())
            print("Flags saved under speeddial number " + str(flags[:1]))
            flags = flags[3:]

        fullseed = "|%i|%s|%s" % (mode_num + 1, flags, fullseed)

    return fullseed, allowed_flags

def _save_flags(sourcefile, output_directory):
    try:
        save_input_path(sourcefile)
        save_output_path(output_directory)
    except:
        print("Couldn't save flag string\n")

class State:
    def __init__(self, configfile="bcce.cfg"):

        # Filename for the current ROM being written
        self.outfile = None
        # file pointer
        # FIXME: for the source file reading if needed
        #self._reader = None
        self._writer = None

        # Filename for the origin ROM being read
        self.sourcefile = None

        # BC flag set
        self.flags = None
        self.mode_num = None

        # seed number
        self.seed = None
        # for reseeding?
        self.seedcounter = 1

        self.outlog = None
        #  ????
        self.randlog = None

        # some persistent configuration
        self.config = configparser.ConfigParser()
        try:
            self.config.read("bcee.cgf")
        except (IOError, KeyError) as e:
            print(str(e))

        # replacement for RANDOM_MULTIPLIER global var
        self.random_multiplier = 1

    class BufferedWriter:
        def __init__(self, fname):
            self._fname = fname
            self._fout = open(self._fname, "r+b")

        def __del__(self):
            self._fout.close()

    @property
    def fout(self):
        return self._writer._fout

    def _process_args(self, args, interactive=True):
        # Override to test flags
        # FIXME: this needs to be handled differently
        if args["TEST_ON"]:
            args = _modify_args_for_testing(args)

        previous_rom_path = get_input_path()
        previous_output_directory = get_output_path()

        # process the sourcefile args
        args["source_arg"] = self.sourcefile = \
            pathlib.Path(_process_sourcefile(args.pop("source"), previous_rom_path))

        # If no previous directory or an invalid directory was obtained from
        # bcce.cfg, default to the ROM's directory
        if not previous_output_directory or not pathlib.Path(previous_output_directory).is_dir():
            previous_output_directory = os.path.dirname(self.sourcefile)
        # process the output director args
        output_directory = \
            pathlib.Path(_process_output_dir(args.pop("destination"),
                                             previous_output_directory))

        # parse or obtain vital seed information
        if interactive:
            self.fullseed, self.allowed_flags = _process_seed(args["seed"])
        else:
            self.fullseed = args["seed"]

        self.version, self.mode_num, self.flags, self.seed = _parse_seed(self.fullseed)
        self.flags = self.flags.lower()
        self.mode_num = int(self.mode_num)

        if self.mode_num not in range(len(ALL_MODES)):
            raise Exception("Invalid mode specified")

        tempname, ext = self.sourcefile.stem, self.sourcefile.suffix
        self.outfile = output_directory / f"{tempname}.{self.seed}{ext}"
        self.outlog = output_directory / f"{tempname}.{self.seed}.txt"

        # should we save this to the configuration?
        if self.sourcefile != previous_rom_path or output_directory != previous_output_directory:
            _save_flags(self.sourcefile, output_directory)

        return args

    def prepare_outfile(self, from_gui=False):
        assert self.outfile is not None

        with open(self.sourcefile, "rb") as f:
            data = f.read()

        if len(data) % 0x400 == 0x200:
            print("NOTICE: Headered ROM detected. Output file will have no header.")
            data = data[0x200:]
            tempname, ext = self.sourcefile.stem, self.sourcefile.suffix
            self.sourcefile = '.'.join([tempname, "unheadered", suffix])
            with open(sourcefile, 'wb') as f:
                f.write(data)

        if md5(data).hexdigest() not in _KNOWN_HASHES.values() and not from_gui:
            print("WARNING! The md5 hash of this file does not match the known "
                  "hashes of the english FF6 1.0 rom!")
            x = input("Continue? y/n (default no)") or "n"
            if x.lower()[0] != 'y':
                # FIXME: this may not have the same behavior as before
                return

        copyfile(self.sourcefile, self.outfile)
        self._writer = self.BufferedWriter(self.outfile)

    def reset_seed(self):
        self.seedcounter = 0

    def reseed(self):
        random.seed(self.seed + self.seedcounter)
        self.seedcounter += (self.seedcounter * 2) + 1

    def check_christmas_mode(self):
        tm = time.gmtime(self.seed)
        if tm.tm_mon == 12 and (tm.tm_mday == 24 or tm.tm_mday == 25):
            Options_.activate_code('christmas')
            return True
        return False

    def check_halloween_mode(self):
        tm = time.gmtime(self.seed)
        if tm.tm_mon == 10 and tm.tm_mday == 31:
            Options_.activate_code('halloween')
            return True
        return False

    def get_random_boost(self):
        self.random_multiplier = Options_.get_code_value('randomboost')
        while not isinstance(self.random_multiplier, bool):
            try:
                self.random_multiplier = int(input("Please enter a randomness "
                                                   "multiplier value (blank or "
                                                   "<=0 for tierless): "))
            except ValueError:
                print("The supplied value for the randomness multiplier was not valid.")

        return self.random_multiplier