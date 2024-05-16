from sys import argv
from os import stat, listdir, path
import string
from time import time
from shutil import copyfile
from collections import defaultdict

from .tablereader import (
    determine_global_table, sort_good_order, set_table_specs,
    set_global_output_filename, select_patches, write_patches, verify_patches,
    get_random_degree, set_random_degree, get_difficulty, set_difficulty,
    set_seed, get_seed, close_file, get_addressing_mode, set_addressing_mode,
    reimport_psx_files)
from .utils import (
    utilrandom as random, rewrite_snes_title, rewrite_snes_checksum,
    md5hash)
from .psx_file_extractor import DELTA_FILE

sourcefile = None
outfile = None
flags = None
user_input_flags = None
activated_codes = None
all_objects = None


def get_all_objects():
    global all_objects
    return all_objects


def get_sourcefile():
    global sourcefile
    return sourcefile


def get_outfile():
    global outfile
    return outfile


def get_flags():
    global flags
    return flags


def get_user_input_flags():
    global user_input_flags
    return user_input_flags


def get_activated_codes():
    global activated_codes
    return sorted(activated_codes)


def activate_code(code):
    global activated_codes
    activated_codes.add(code)


def rewrite_snes_meta(title, version, lorom=None):
    addressing_mode = get_addressing_mode()
    if lorom is None:
        lorom = addressing_mode == 'lorom'

    close_file(outfile)

    for o in get_all_objects():
        if o.random_degree != get_random_degree():
            random_degree = "??"
            break
    else:
        random_degree = int(round((get_random_degree()**0.5) * 100))
        if random_degree >= 100:
            random_degree = "!!"
        else:
            random_degree = "{0:0>2}".format(random_degree)

    rewrite_snes_title("%s %s %s" % (title, random_degree, get_seed()),
                       outfile, version, lorom=lorom)
    rewrite_snes_checksum(outfile, lorom=lorom)


def snescopy(sourcefile, outfile):
    size = stat(sourcefile).st_size
    if size % 0x400 == 0:
        copyfile(sourcefile, outfile)
    elif size % 0x200 == 0:
        print("SNES header detected. Removing header from output file.")
        f = open(sourcefile, 'r+b')
        data = f.read()
        f.close()
        data = data[0x200:]
        open(outfile, 'w+').close()
        f = open(outfile, 'r+b')
        f.write(data)
        f.close()
    else:
        raise Exception("Inappropriate file size for SNES rom file.")


def n64copy(sourcefile, outfile):
    simple_copy = False
    with open(outfile, 'w+') as g:
        pass
    with open(sourcefile, 'r+b') as f:
        with open(outfile, 'r+b') as g:
            first_word = f.read(4)
            f.seek(0)
            if first_word == b'\x80\x37\x12\x40':
                # big-endian
                simple_copy = True
            elif first_word == b'\x37\x80\x40\x12':
                # byte swapped
                print('Byte-swapped ROM detected. Converting to big-endian.')
                while True:
                    data = f.read(2)
                    if not data:
                        break
                    g.write(data[::-1])
            elif first_word == b'\x40\x12\x37\x80':
                # little-endian
                print('Little-endian ROM detected. Converting to big-endian.')
                while True:
                    data = f.read(4)
                    if not data:
                        break
                    g.write(data[::-1])
            else:
                raise Exception('Unknown N64 ROM format.')
    if simple_copy:
        copyfile(sourcefile, outfile)


def write_cue_file():
    filename = get_outfile()
    cue_filename = '.'.join(filename.split('.')[:-1] + ['cue'])
    head, tail = path.split(filename)
    f = open(cue_filename, 'w+')
    f.write('FILE "{0}" BINARY\n\n'
            'TRACK 01 MODE2/2352\n\n'
            'INDEX 01 00:00:00\n'.format(tail))
    f.close()


def run_interface(objects, custom_degree=False, custom_difficulty=False,
                  codes=None, snes=False, n64=False, lorom=False, args=None,
                  setup_only=False, override_outfile=None):
    global sourcefile, outfile, flags, user_input_flags
    global activated_codes, all_objects

    all_objects = objects

    if codes is None:
        codes = {}
    activated_codes = set([])

    if args is None:
        args = list(argv)[:6]

    num_args = len(args)
    while len(args) < 6:
        args.append(None)
    (_, sourcefile, flags, seed,
            random_degree, difficulty_multiplier) = tuple(args)
    if random_degree is None and num_args >= 2:
        random_degree = 0.5
    if difficulty_multiplier is None and num_args >= 2:
        difficulty_multiplier = 1.0

    if sourcefile is None:
        print('TIP: Try dragging-and-dropping the rom file '
              'instead of typing the filename manually!')
        sourcefile = input("Rom filename? ")
        if sourcefile.startswith('"') and sourcefile.endswith('"'):
            print('NOTICE: Automatically removing '
                  'extraneous quotation marks.')
            sourcefile = sourcefile.strip('"')

    if seed is None and num_args < 2:
        seed = input("Seed? (blank for random) ").strip()

    if seed is None or seed == "":
        seed = time()
    seed = int(seed)
    seed = seed % (10**10)
    set_seed(seed)
    random.seed(seed)

    flagobjects = [o for o in objects if hasattr(o, "flag")
                   and hasattr(o, "flag_description")]
    flagobjects = sorted(flagobjects, key=lambda o: o.flag)
    for o in objects:
        if hasattr(o, "flag") and not hasattr(o, "flag_description"):
            for fo in flagobjects:
                if fo.flag == o.flag:
                    break
            else:
                raise Exception("%s has no flag description." % o.flag)

    allflags = "".join(sorted([f.flag for f in flagobjects]))
    user_input_flags = flags
    if allflags:
        if flags is None and num_args < 2:
            print("\nPlease input the flags for "
                  "the things you want to randomize.")
            for o in flagobjects:
                print("    %s  Randomize %s." % (o.flag,
                                                 o.flag_description.lower()))
            print()
            flags = input("Flags? (blank for all) ").strip()
            user_input_flags = flags
        elif flags is None:
            flags = allflags

    if flags:
        flags = flags.lower()
        code_keys = sorted(codes.keys(), key=lambda c: (-len(c), c))
        for code in code_keys:
            code_options = codes[code]
            if isinstance(code_options, str):
                code_options = [code_options]
            for co in code_options:
                co = co.lower()
                if co in flags:
                    flags = flags.replace(co, "")
                    activated_codes.add(code)
                    break

    if flags and allflags:
        flags = "".join(sorted([f for f in flags if f in allflags]))
    if not (allflags and flags):
        flags = allflags

    if "." not in sourcefile:
        outfile = [sourcefile, "smc"]
    else:
        outfile = sourcefile.split(".")
    if flags == allflags:
        flagstr = ""
    else:
        flagstr = flags
    outfile = outfile[:-1] + [flagstr, str(seed), outfile[-1]]
    outfile = ".".join(outfile)
    while ".." in outfile:
        outfile = outfile.replace("..", ".")

    if override_outfile is not None:
        outfile = override_outfile

    try:
        print('Making copy of rom file...')
        if snes:
            snescopy(sourcefile, outfile)
            if lorom:
                set_addressing_mode('lorom')
            else:
                set_addressing_mode('hirom')
        elif n64:
            n64copy(sourcefile, outfile)
        else:
            if (DELTA_FILE is not None
                    and DELTA_FILE in listdir() and outfile in listdir()):
                f = open(sourcefile, 'r+b')
                g = open(outfile, 'r+b')
                for line in open(DELTA_FILE):
                    line = line.strip()
                    start, finish = line.split()
                    start = int(start, 0x10)
                    finish = int(finish, 0x10)
                    assert finish > start
                    f.seek(start)
                    g.seek(start)
                    data = f.read(finish-start)
                    g.write(data)
                f.close()
                g.close()
            else:
                copyfile(sourcefile, outfile)
            if DELTA_FILE is not None:
                f = open(DELTA_FILE, 'w+')
                f.close()
                label = determine_global_table(outfile, interactive=False)
                if label is None:
                    print('Delta failed. Copying full rom.')
                    copyfile(sourcefile, outfile)
    except (OSError, IOError) as e:
        if e.strerror == "No such file or directory":
            e.strerror = ('%s; Did you include the filename extension? For '
                          'example, ".smc", ".sfc", or ".img". ' % e.strerror)
        raise e

    set_global_output_filename(outfile)
    determine_global_table(outfile, allow_conversions=not setup_only)
    set_table_specs(objects)

    if setup_only:
        objects = sort_good_order(objects)
        for o in objects:
            o.every
        for o in objects:
            o.ranked
        return

    custom_degree = custom_degree or random_degree is not None
    if custom_degree:
        custom_split = False
        for o in sorted(objects, key=lambda ob: str(ob)):
            if hasattr(o, "custom_random_enable") and o.custom_random_enable:
                custom_split = True
                break

        if random_degree is None:
            if custom_split:
                print("\nIf you would like even more control over the "
                      "randomness, type \"custom\" here.")
            random_degree = input("Randomness? (default: 0.5) ").strip()
            if not random_degree:
                random_degree = 0.5

        if custom_split and (isinstance(random_degree, str) and
                             "custom" in random_degree.strip().lower()):
            custom_dict = defaultdict(set)
            for o in sorted(objects, key=lambda o: str(o)):
                if (hasattr(o, "custom_random_enable")
                        and o.custom_random_enable):
                    if o.custom_random_enable is True:
                        custom_dict[o.flag].add(o)
                    else:
                        custom_dict[o.custom_random_enable].add(o)

            for k in sorted(custom_dict):
                os = sorted(custom_dict[k], key=lambda o: o.__name__)
                onames = ", ".join([o.__name__ for o in os])
                s = input("Randomness for %s? " % onames).strip()
                if not s:
                    continue
                for o in os:
                    crd = float(s)
                    assert isinstance(crd, float)
                    crd = min(1.0, max(0.0, crd))
                    o.custom_random_degree = crd ** 2

            random_degree = input("Randomness for everything"
                                  " unspecified? ").strip()
            if not random_degree:
                random_degree = 0.5

        random_degree = float(random_degree)
        assert isinstance(random_degree, float)
        random_degree = min(1.0, max(0.0, random_degree))
        set_random_degree(random_degree ** 2)

    custom_difficulty = custom_difficulty or difficulty_multiplier is not None
    if custom_difficulty:
        custom_split = False
        for o in sorted(objects, key=lambda ob: str(ob)):
            if (hasattr(o, "custom_difficulty_enable")
                    and o.custom_difficulty_enable):
                custom_split = True
                break

        if difficulty_multiplier is None:
            if custom_split:
                print("\nIf you would like even more control over the "
                      "difficulty, type \"custom\" here.")
            difficulty_multiplier = input(
                "Difficulty? (default: 1.0) ").strip()
            if not difficulty_multiplier:
                difficulty_multiplier = 1.0

        if custom_split and (
                isinstance(difficulty_multiplier, str) and
                "custom" in difficulty_multiplier.strip().lower()):
            custom_dict = defaultdict(set)
            for o in sorted(objects, key=lambda o: str(o)):
                if (hasattr(o, "custom_difficulty_enable")
                        and o.custom_difficulty_enable):
                    if o.custom_difficulty_enable is True:
                        custom_dict[o.flag].add(o)
                    else:
                        custom_dict[o.custom_difficulty_enable].add(o)

            for k in sorted(custom_dict):
                os = sorted(custom_dict[k], key=lambda o: o.__name__)
                onames = ", ".join([o.__name__ for o in os])
                s = input("Difficulty for %s? " % onames).strip()
                if not s:
                    continue
                for o in os:
                    cdiff = float(s)
                    assert isinstance(cdiff, float)
                    o.custom_difficulty = cdiff

            difficulty_multiplier = input("Difficulty for everything"
                                          " unspecified? ").strip()
            if not difficulty_multiplier:
                difficulty_multiplier = 1.0

        difficulty_multiplier = float(difficulty_multiplier)
        assert isinstance(difficulty_multiplier, float)
        set_difficulty(difficulty_multiplier)

    if num_args < 3:
        select_patches()

    print()
    if flags == allflags:
        flags = string.ascii_lowercase
        print("Randomizing %s with all flags using seed %s"
              % (sourcefile, seed), end=' ')
    else:
        flags = flags.lower()
        print("Randomizing %s with flags '%s' using seed %s"
              % (sourcefile, flags, seed), end=' ')
    if custom_degree:
        print("and randomness %s" % random_degree, end=' ')
    if custom_difficulty:
        print("and difficulty %s" % difficulty_multiplier, end=' ')
    print("now.\n")

    if user_input_flags is None:
        user_input_flags = flags

    write_patches(outfile)
    print("Loading and ranking game objects...")
    objects = sort_good_order(objects)
    for o in objects:
        o.every
    for o in objects:
        o.ranked
    for o in objects:
        o.preprocess_all()

    for o in objects:
        if hasattr(o, "flag_description") and o.flag in flags:
            print("Randomizing %s." % o.flag_description.lower())
        if not hasattr(o, "flag") or o.flag in flags:
            o.class_reseed('full_randomize')
            o.full_randomize()
        o.randomize_step_finished = True

    if set(flags) >= set(allflags):
        flags = allflags


def clean_and_write(objects):
    objects = sort_good_order(objects)
    for o in objects:
        o.class_reseed('preclean')
        o.full_preclean()

    for o in objects:
        if hasattr(o, "flag_description") and o.flag in get_flags():
            print("Cleaning %s." % o.flag_description.lower())
        o.class_reseed('cleanup')
        o.full_cleanup()

    print("Saving game objects...")
    for o in objects:
        o.write_all(outfile)

    verify_patches(outfile)
    reimport_psx_files()


def finish_interface():
    close_file(outfile)
    print()
    print("Randomization completed successfully.")
    print("Output filename: %s" % outfile)
    print("MD5 hash: %s" % md5hash(outfile))
    print()
    if len(argv) < 2:
        input("Press Enter to close this program. ")
