from .psx_file_extractor import FileManager, SANDBOX_PATH
from .utils import (read_multi, write_multi, classproperty,
                    random, md5hash, cached_property, clached_property,
                    ips_patch, map_to_snes, read_lines_nocomment)
from _io import BytesIO, BufferedRandom
from functools import total_ordering
from os import path
from hashlib import md5
import re
from sys import stdout
import string
from copy import copy
from collections import Counter


try:
    from sys import _MEIPASS
    tblpath = path.join(_MEIPASS, "tables")
except ImportError:
    tblpath = "tables"
head = __file__.rsplit('randomtools', 1)[0]
tblpath = path.join(head, tblpath)

addresses = lambda: None
names = lambda: None

MASTER_FILENAME = "master.txt"
TABLE_SPECS = {}
GLOBAL_OUTPUT = None
GLOBAL_TABLE = None
GLOBAL_LABEL = None
GRAND_OBJECT_DICT = {}
PATCH_FILENAMES = []
ALREADY_PATCHED = set()
OPTION_FILENAMES = []
NOVERIFY_PATCHES = []
CMP_PATCH_FILENAMES = []
RANDOM_DEGREE = 0.25
DIFFICULTY = 1.0
SEED = None
PSX_FILE_MANAGER = None
OPEN_FILES = {}
ALL_FILES = set()
REMOVED_FILES = set()
MAX_OPEN_FILE_COUNT = 100
ADDRESSING_MODE = None
MAPPINGS = {}
PATCH_PARAMETERS = {}
FULL_PATCH_CHANGELIST = {}


def get_open_file(filepath, sandbox=False):
    if isinstance(filepath, BytesIO) or isinstance(filepath, BufferedRandom):
        if filepath.closed:
            filepath = open(filepath.name, 'r+b')
        return filepath
    filepath = filepath.replace('/', path.sep)
    filepath = filepath.replace('\\', path.sep)
    assert filepath not in REMOVED_FILES
    if sandbox and not filepath.startswith(SANDBOX_PATH):
        filepath = path.join(SANDBOX_PATH, filepath)
    if filepath in OPEN_FILES:
        f = OPEN_FILES[filepath]
        if not f.closed:
            return OPEN_FILES[filepath]

    if len(OPEN_FILES) >= MAX_OPEN_FILE_COUNT:
        for openfp in list(OPEN_FILES):
            close_file(openfp)

    if (filepath.startswith(SANDBOX_PATH) and path.sep in filepath
            and filepath not in ALL_FILES):
        name = filepath[len(SANDBOX_PATH):].lstrip(path.sep)
        PSX_FILE_MANAGER.export_file(name, filepath)

    f = open(filepath, "r+b")
    OPEN_FILES[filepath] = f
    ALL_FILES.add(filepath)
    return get_open_file(filepath)


def close_file(filepath):
    if filepath in OPEN_FILES:
        OPEN_FILES[filepath].close()
        del(OPEN_FILES[filepath])


def remove_unused_file(filepath):
    close_file(filepath)
    REMOVED_FILES.add(filepath)
    if filepath in ALL_FILES:
        ALL_FILES.remove(filepath)


def create_psx_file_manager(outfile):
    global PSX_FILE_MANAGER
    PSX_FILE_MANAGER = FileManager(outfile, SANDBOX_PATH)


def get_psx_file_manager():
    global PSX_FILE_MANAGER
    assert PSX_FILE_MANAGER is not None
    return PSX_FILE_MANAGER


def reimport_psx_files():
    if not SANDBOX_PATH:
        return
    if not PSX_FILE_MANAGER:
        return
    last_import = -1
    for (n, filepath) in enumerate(sorted(ALL_FILES)):
        if filepath.startswith(SANDBOX_PATH):
            count = int(round(9 * n / len(ALL_FILES)))
            if count > last_import:
                if count == 0:
                    print('Re-importing files...')
                last_import = count
                stdout.write('%s ' % (10-count))
                stdout.flush()
            name = filepath[len(SANDBOX_PATH):].lstrip(path.sep)
            close_file(filepath)  # do before importing to flush the file
            PSX_FILE_MANAGER.import_file(name, filepath)
    stdout.write('\n')
    PSX_FILE_MANAGER.finish()


def set_global_label(label):
    global GLOBAL_LABEL
    GLOBAL_LABEL = label

def get_global_label():
    global GLOBAL_LABEL
    return GLOBAL_LABEL


def set_global_output_filename(filename):
    global GLOBAL_OUTPUT
    GLOBAL_OUTPUT = filename


def set_global_table_filename(filename):
    global GLOBAL_TABLE
    GLOBAL_TABLE = filename


def get_seed():
    global SEED
    return SEED


def set_seed(seed):
    global SEED
    SEED = seed


def set_addressing_mode(mode):
    global ADDRESSING_MODE
    ADDRESSING_MODE = mode


def get_addressing_mode():
    global ADDRESSING_MODE
    return ADDRESSING_MODE


def determine_global_table(outfile, interactive=True, allow_conversions=True):
    global GLOBAL_LABEL
    if GLOBAL_LABEL is not None:
        return GLOBAL_LABEL

    force_conversion = False
    tablefiles, labelfiles, conversions = {}, {}, {}
    for line in open(path.join(tblpath, MASTER_FILENAME)):
        line = line.strip()
        if not line or line[0] == "#":
            continue
        while "  " in line:
            line = line.replace("  ", " ")
        try:
            label, h2, tablefile = line.split()
            tablefiles[h2] = (label, tablefile)
            labelfiles[label] = tablefile
        except ValueError:
            conversion, ips_filename = line.split(' ')
            assert '->' in conversion
            convert_from, convert_to = conversion.split('->')
            if convert_from.startswith('!'):
                convert_from = convert_from.lstrip('!')
                force_conversion = True
            conversions[convert_from] = (convert_to, ips_filename)

    h = md5hash(outfile)
    if h in tablefiles:
        label, filename = tablefiles[h]
    elif interactive:
        print("Unrecognized rom file: %s" % h)
        for i, label in enumerate(sorted(labelfiles)):
            print("%s. %s" % ((i+1), label))
        if len(labelfiles) > 1:
            selection = int(input("Choose 1-%s: " % len(labelfiles)))
            label = sorted(labelfiles.keys())[selection-1]
            filename = labelfiles[label]
        else:
            input("Using this rom information. Okay? ")
            label = sorted(labelfiles.keys())[0]
            filename = labelfiles[label]
    else:
        return None

    if allow_conversions and label in conversions:
        convert_to, ips_filename = conversions[label]
        convert = True
        if interactive and not force_conversion:
            x = input("Automatically convert from {0} to {1}? (y/n) ")
            if x and x[0].lower() == 'n':
                convert = False
        if convert:
            ips_patch(outfile, path.join(tblpath, ips_filename))
            label = convert_to
            h = md5hash(outfile)
            assert h in tablefiles and tablefiles[h][0] == label
            filename = labelfiles[label]

    set_global_label(label)
    set_global_table_filename(filename)
    return GLOBAL_LABEL


def patch_filename_to_bytecode(patchfilename, mapping=None, parameters=None):
    def clean_parameter(value):
        if isinstance(value, str):
            try:
                value = int(value, 0x10)
            except ValueError:
                pass
        return value

    def hexify(value):
        s = ''
        while True:
            s = ' '.join([s, '{0:0>2x}'.format(value & 0xff)]).strip()
            value >>= 8
            if not value:
                break
        return s.strip()

    if parameters is not None:
        for parameter_name, value in parameters.items():
            value = clean_parameter(value)
            if parameter_name in PATCH_PARAMETERS:
                assert PATCH_PARAMETERS[parameter_name] == value
            PATCH_PARAMETERS[parameter_name] = value

    if patchfilename in MAPPINGS and mapping is None:
        mapping = MAPPINGS[patchfilename]
    if mapping is not None:
        MAPPINGS[patchfilename] = mapping
        temp = {}
        for line in read_lines_nocomment(mapping):
            start, finish, offset = line.strip().split()
            start = int(start, 0x10)
            finish = int(finish, 0x10)
            offset = int(offset, 0x10)
            key = (start, finish)
            assert key not in temp
            temp[key] = offset
        mapping = temp

    def map_address(address):
        if mapping is None:
            return address
        for start, finish in sorted(mapping.keys()):
            if start <= address <= finish:
                return address + mapping[start, finish]
        raise Exception('No valid mapping for {0:0>6x} in {1}.'.format(
            address, patchfilename))

    patch = {}
    validation = {}
    definitions = {}
    code_addresses = {}
    labels = {}
    next_address = None
    filename = None
    read_into = patch
    valparmatcher = re.compile('({{([^:]*)=([^}]*)}})')
    defparmatcher = re.compile('({{([^:]*):([^}]*)}})')
    f = open(patchfilename)
    for line in f:
        line = line.strip()
        if '#' in line:
            line = line.split('#')[0].strip()

        if not line:
            continue

        while "  " in line:
            line = line.replace("  ", " ")

        valparmatches = valparmatcher.findall(line)
        for to_replace, name, value in valparmatches:
            if parameters is not None:
                try:
                    assert name in parameters
                    assert parameters[name] == value
                except:
                    raise Exception('Parameter %s does not equal %s.'
                                    % (name, value))
            line = line.replace(to_replace, value)
        defparmatches = defparmatcher.findall(line)
        for to_replace, name, value in defparmatches:
            value = clean_parameter(value)
            if isinstance(value, int):
                if (':' in line and
                        line.index(':') < line.index(to_replace)):
                    value = hexify(value)
                else:
                    value = '%x' % value

            if name not in PATCH_PARAMETERS:
                line = line.replace(to_replace, value)
            else:
                line = line.replace(to_replace, '{{%s}}' % name)

        if '{{' in line:
            for name in sorted(PATCH_PARAMETERS, key=lambda n: (-len(n), n)):
                if name not in line:
                    continue
                to_replace = '{{%s}}' % name
                if to_replace in line:
                    value = PATCH_PARAMETERS[name]
                    if isinstance(value, int):
                        if (':' in line and
                                line.index(':') < line.index(to_replace)):
                            value = hexify(value)
                        else:
                            value = '%x' % value
                    line = line.replace(to_replace, value)

        if line.startswith(".def"):
            _, name, value = line.split(' ', 2)
            definitions[name] = value
            continue

        if line.startswith(".addr"):
            try:
                _, name, value, length = line.split(' ', 3)
            except ValueError:
                _, name, value = line.split(' ', 2)
                length = 3
            name = name.lstrip('$')
            address = int(value, 0x10)
            code_addresses[name] = (address, int(length))
            continue

        if line.startswith(".label"):
            try:
                _, name, address = line.split(' ')
                labels[name] = (address, filename)
            except ValueError:
                _, name = line.split(' ')
                address = None
                labels[name] = None
                for i in range(1, 4):
                    name_with_length = '%s,%s' % (name, i)
                    labels[name_with_length] = None
            continue

        for name in sorted(code_addresses, key=lambda a: (-len(a), a)):
            to_replace = '${0}'.format(name)
            if to_replace in line:
                if ':' not in line:
                    line = line + ':'
                address, length = code_addresses[name]
                replacement = '{0:x}'.format(address)
                colon_index = line.index(':')
                replace_index = line.index(to_replace)
                if colon_index < replace_index:
                    address = map_address(address)
                    replacement = '{0:x}'.format(address)
                    if ADDRESSING_MODE is not None:
                        lorom = ADDRESSING_MODE == 'lorom'
                        address = map_to_snes(address, lorom=lorom)
                    bytestr = address.to_bytes(
                        length=length, byteorder='little')
                    replacement = ' '.join(['{0:0>2x}'.format(c)
                                            for c in bytestr])
                    for i in range(1, length+1):
                        length_replace = '%s,%s' % (to_replace, i)
                        length_replacement = ' '.join([
                            '{0:0>2x}'.format(c) for c in bytestr[:i]])
                        line = line.replace(length_replace, length_replacement)
                line = line.replace(to_replace, replacement)

        for name in sorted(definitions, key=lambda d: (-len(d), d)):
            if name in line and not line.strip().startswith('.'):
                line = line.replace(name, definitions[name])

        if line.upper() == 'VALIDATION':
            read_into = validation
            continue

        if ':' not in line:
            line = ':' + line

        address, code = line.split(':')
        address = address.strip()
        if not address:
            address = next_address
        else:
            if '@' in address:
                address, filename = address.split('@')
                filename = filename.replace('/', path.sep)
                filename = filename.replace('\\', path.sep)
            address = map_address(int(address, 0x10))
        code = code.strip()
        while '  ' in code:
            code = code.replace('  ', ' ')

        if (address, filename) in read_into:
            raise Exception("Multiple %x patches used." % address)
        if code:
            read_into[(address, filename)] = code
        for name in labels:
            if labels[name] is None:
                labels[name] = (address, filename)

        next_address = address
        for word in code.split():
            if ',' in word:
                _, length = word.split(',')
                length = int(length)
                next_address += length
            else:
                next_address += 1

    for defname in sorted(definitions):
        for aname in sorted(code_addresses):
            if defname in aname.lower():
                raise Exception('Address "%s" cannot contain '
                                'definition "%s".' % (aname, defname))
        for lname in sorted(labels):
            if defname in lname.lower():
                raise Exception('Label "%s" cannot contain '
                                'definition "%s".' % (lname, defname))

    for read_into in (patch, validation):
        for (address, filename) in sorted(read_into):
            code = read_into[address, filename]
            for name in sorted(labels, key=lambda l: (-len(l), l)):
                if name in code:
                    direct = '@%s' % name
                    if direct in code:
                        code = code.replace(direct, name)
                        direct = True
                    else:
                        direct = False

                    if ',' in name:
                        name, length = name.split(',')
                        length = int(length)
                    else:
                        length = 1
                    target_address, target_filename = labels[name]
                    assert target_filename == filename
                    if direct and ADDRESSING_MODE is not None:
                        assert target_address < 0x800000
                        lorom = ADDRESSING_MODE == 'lorom'
                        target_address = map_to_snes(target_address,
                                                     lorom=lorom)
                    if direct:
                        jump = target_address & ((0x100**length)-1)
                    elif length == 1:
                        jump = target_address - (address + 2)
                    else:
                        assert length == 2
                        opcode = int(code.split()[0], 0x10)
                        assert opcode in (0x62, 0x82)
                        if opcode in (0x62,):
                            jump = target_address - (address + 4)
                        elif opcode in (0x82,):
                            jump = target_address - (address + 3)
                        else:
                            raise Exception(
                                'Label not compatible with opcode '
                                '{0:0>2X}.'.format(opcode))

                    if not direct:
                        assert abs(jump) < ((0x100**length) >> 1)
                        if jump < 0:
                            jump = (0x100**length) + jump
                            assert jump >= (0x100**length) >> 1
                        if not 0 <= jump < (0x100**length):
                            raise Exception("Label out of range %x - %s" %
                                            (address, code))
                    replacement = jump.to_bytes(length=length,
                                                byteorder='little')
                    replacement = ' '.join(['{0:0>2x}'.format(c)
                                            for c in replacement])
                    code = code.replace('%s,%s' % (name, length), replacement)
                    code = code.replace(name, replacement)

            code = bytearray(map(lambda s: int(s, 0x10), code.split()))
            read_into[address, filename] = code

    f.close()
    return patch, validation


def select_patches():
    if not OPTION_FILENAMES:
        return

    print("\nThe following optional patches are available.")
    for i, patchfilename in enumerate(OPTION_FILENAMES):
        print("%s: %s" % (i+1, patchfilename.split('.')[0]))
    print()
    s = input("Select which patches to use, separated by a space."
              "\n(0 for none, blank for all): ")
    print()
    s = s.strip()
    if not s:
        return
    while '  ' in s:
        s = s.replace('  ', ' ')
    numbers = map(int, s.split())
    options = [o for (i, o) in enumerate(OPTION_FILENAMES) if i+1 in numbers]
    not_chosen = set(OPTION_FILENAMES) - set(options)
    for pfn in not_chosen:
        PATCH_FILENAMES.remove(pfn)


def write_patch_line(outfile, address, code):
    key = (outfile, address)
    if key in FULL_PATCH_CHANGELIST:
        assert FULL_PATCH_CHANGELIST[key].startswith(code)
    else:
        FULL_PATCH_CHANGELIST[key] = code
    outfile.seek(address)
    outfile.write(code)


def write_patch(outfile, patchfilename, parameters=None, mapping=None,
                noverify=None, validate=None, force=False):
    if patchfilename in ALREADY_PATCHED and not force:
        return
    if validate is None:
        validate = not noverify
    if noverify and patchfilename not in NOVERIFY_PATCHES:
        NOVERIFY_PATCHES.append(patchfilename)
    elif noverify is None and patchfilename in NOVERIFY_PATCHES:
        noverify = True

    patchpath = path.join(tblpath, patchfilename)
    pf = open(patchpath, 'r+b')
    magic_word = pf.read(5)
    pf.close()
    f = get_open_file(outfile)
    if magic_word == b"\xff\xbcCMP":
        CMP_PATCH_FILENAMES.append(patchfilename)
        return write_cmp_patch(f, patchpath)

    patch, validation = patch_filename_to_bytecode(patchpath, mapping=mapping,
                                                   parameters=parameters)
    for (address, filename), code in sorted(patch.items()):
        if filename is None:
            f = get_open_file(outfile)
        else:
            if PSX_FILE_MANAGER is None:
                create_psx_file_manager(outfile)
            f = get_open_file(filename, sandbox=True)
        f.seek(address)
        validation_str = f.read(len(code))
        if validation_str != code[:len(validation)]:
            break
    else:
        # this patch has already been applied
        if patchfilename not in PATCH_FILENAMES:
            PATCH_FILENAMES.append(patchfilename)
        ALREADY_PATCHED.add(patchfilename)
        return

    for patchdict in (validation, patch):
        for (address, filename), code in sorted(patchdict.items()):
            if filename is None:
                f = get_open_file(outfile)
            else:
                if PSX_FILE_MANAGER is None:
                    create_psx_file_manager(outfile)
                f = get_open_file(filename, sandbox=True)
            f.seek(address)

            if patchdict is validation:
                validation_str = f.read(len(code))
                if validation_str != code[:len(validation_str)]:
                    error = ('Patch %s-%x did not pass validation.'
                             % (patchfilename, address))
                    if not validate:
                        print('WARNING: %s' % error)
                    else:
                        raise Exception(error)
            else:
                assert patchdict is patch
                write_patch_line(f, address, code)

    if patchfilename not in PATCH_FILENAMES:
        PATCH_FILENAMES.append(patchfilename)
    ALREADY_PATCHED.add(patchfilename)


def write_cmp_patch(outfile, patchfilename, verify=False):
    from randomtools.interface import get_sourcefile

    sourcefile = open(get_sourcefile(), 'r+b')
    patchfile = open(patchfilename, 'r+b')
    magic_word = patchfile.read(5)
    if magic_word != b"\xFF\xBCCMP":
        raise Exception("Not a CMP patch.")
    version = ord(patchfile.read(1))
    pointer_length = ord(patchfile.read(1))

    while True:
        command = patchfile.read(1)
        if not command:
            break
        if command == b'\x00':
            address = read_multi(patchfile, length=pointer_length)
            outfile.seek(address)
        elif command == b'\x01':
            chunksize = read_multi(patchfile, length=2)
            address = read_multi(patchfile, length=pointer_length)
            sourcefile.seek(address)
            s = sourcefile.read(chunksize)
            if not verify:
                write_patch_line(outfile, outfile.tell(), s)
            elif verify:
                s2 = outfile.read(len(s))
                if s != s2:
                    raise Exception("Patch write conflict %s %x" % (
                        patchfilename, outfile.tell()-len(s2)))
        elif command == b'\x02':
            chunksize = read_multi(patchfile, length=2)
            s = patchfile.read(chunksize)
            if not verify:
                write_patch_line(outfile, outfile.tell(), s)
            elif verify:
                s2 = outfile.read(len(s))
                if s != s2:
                    raise Exception("Patch write conflict %s %x" % (
                        patchfilename, outfile.tell()-len(s2)))
        else:
            raise Exception("Unexpected EOF")

    sourcefile.close()
    patchfile.close()


def write_patches(outfile):
    if not PATCH_FILENAMES:
        return

    print("Writing patches...")
    for patchfilename in PATCH_FILENAMES:
        write_patch(outfile, patchfilename)


def verify_patchlist(outfile, patchlist):
    f = get_open_file(outfile)
    for patchfilename in patchlist:
        if patchfilename in NOVERIFY_PATCHES:
            continue
        patchpath = path.join(tblpath, patchfilename)
        if patchfilename in CMP_PATCH_FILENAMES:
            write_cmp_patch(f, patchpath, verify=True)
            continue
        patch, validation = patch_filename_to_bytecode(patchpath)
        for (address, filename), code in sorted(patch.items()):
            if filename is None:
                f = get_open_file(outfile)
            else:
                f = get_open_file(filename, sandbox=True)
            f.seek(address)
            written = f.read(len(code))
            if code != written:
                raise Exception(
                    "Patch %x conflicts with modified data." % address)


def verify_patch_changes():
    def sort_key(k):
        if hasattr(k[0], 'name'):
            return (k[0].name, k[1], k)
        else:
            return (None, k[1], k)
    keys = sorted(FULL_PATCH_CHANGELIST, key=sort_key)
    for outfile, address in keys:
        code = FULL_PATCH_CHANGELIST[outfile, address]
        outfile.seek(address)
        test = outfile.read(len(code))
        if code != test:
            raise Exception(
                    "Patch %x conflicts with modified data." % address)


def verify_patches(outfile, strict=False):
    if not (PATCH_FILENAMES or FULL_PATCH_CHANGELIST):
        return

    print("Verifying patches...")
    if strict:
        verify_patch_changes()
    else:
        verify_patchlist(outfile, PATCH_FILENAMES)


def get_activated_patches():
    return list(PATCH_FILENAMES)


def sort_good_order(objects):
    objects = sorted(objects, key=lambda o: o.__name__)
    objects = [o for o in objects if o.__name__ in TABLE_SPECS]
    while True:
        changed = False
        for o in list(objects):
            if hasattr(o, "after_order"):
                index = objects.index(o)
                for o2 in o.after_order:
                    index2 = objects.index(o2)
                    if index2 > index:
                        objects.remove(o)
                        objects.insert(index2, o)
                        changed = True
        if not changed:
            break
    return objects


def set_random_degree(value):
    global RANDOM_DEGREE
    RANDOM_DEGREE = value


def get_random_degree():
    global RANDOM_DEGREE
    return RANDOM_DEGREE


def set_difficulty(value):
    global DIFFICULTY
    DIFFICULTY = value


def get_difficulty():
    global DIFFICULTY
    return DIFFICULTY


def gen_random_normal(random_degree=None):
    if random_degree is None:
        random_degree = get_random_degree()
    value_a = (random.random() + random.random() + random.random()) / 3.0
    value_b = random.random()
    value_c = 0.5
    if random_degree > 0.5:
        factor = (random_degree * 2) - 1
        return (value_a * (1-factor)) + (value_b * factor)
    else:
        factor = random_degree * 2
        return (value_c * (1-factor)) + (value_a * factor)


def mutate_normal(base, minimum, maximum, random_degree=None,
                  return_float=False, wide=False):
    assert minimum <= base <= maximum
    if minimum == maximum:
        return base
    if random_degree is None:
        random_degree = get_random_degree()
    baseval = base-minimum
    width = maximum-minimum
    factor = gen_random_normal(random_degree=random_degree)
    maxwidth = max(baseval, width-baseval)
    minwidth = min(baseval, width-baseval)
    if wide:
        subwidth = maxwidth
    else:
        width_factor = 1.0
        for _ in range(7):
            width_factor *= random.uniform(random_degree, width_factor)
        subwidth = (minwidth * (1-width_factor)) + (maxwidth * width_factor)
    if factor > 0.5:
        subfactor = (factor-0.5) * 2
        modifier = subwidth * subfactor
        value = baseval + modifier
    else:
        subfactor = 1 - (factor * 2)
        modifier = subwidth * subfactor
        value = baseval - modifier
    value += minimum
    if not return_float:
        value = int(round(value))
    if value < minimum or value > maximum:
        return mutate_normal(base, minimum, maximum,
                             random_degree=random_degree,
                             return_float=return_float, wide=wide)
    return value


def shuffle_normal(candidates, random_degree=None, wide=False):
    if random_degree is None:
        classes = list(set([c.__class__ for c in candidates]))
        if len(classes) == 1 and hasattr(classes[0], "random_degree"):
            random_degree = classes[0].random_degree
        else:
            random_degree = get_random_degree()
    max_index = len(candidates)-1
    new_indexes = {}
    for i, c in enumerate(candidates):
        new_index = mutate_normal(i, 0, max_index, return_float=True,
                                  random_degree=random_degree, wide=wide)
        #new_index = (i * (1-random_degree)) + (new_index * random_degree)
        new_indexes[c] = new_index
    if candidates and hasattr(candidates[0], "signature"):
        shuffled = sorted(candidates,
                          key=lambda c: (new_indexes[c], c.signature))
    else:
        shuffled = sorted(candidates,
                          key=lambda c: (new_indexes[c], random.random(), c))
    return shuffled


def shuffle_simple(candidates, random_degree=None):
    assert 0 <= random_degree <= 1
    if random_degree is None:
        classes = list(set([c.__class__ for c in candidates]))
        if len(classes) == 1 and hasattr(classes[0], "random_degree"):
            random_degree = classes[0].random_degree
        else:
            random_degree = get_random_degree()

    max_index = len(candidates)-1
    indexes = list(range(len(candidates)))
    pure_shuffled = list(indexes)
    random.shuffle(pure_shuffled)
    new_indexes = list(indexes)

    for _ in range(len(indexes)):
        for i, v in enumerate(new_indexes):
            v += random.choice([1, -1])
            new_indexes[i] = v

    if random_degree == 0.5:
        final_indexes = new_indexes
    elif random_degree < 0.5:
        factor = random_degree * 2
        final_indexes = [((1-factor)*a) + (factor*b)
                         for (a, b) in zip(indexes, new_indexes)]
    elif random_degree > 0.5:
        factor = (random_degree-0.5) * 2
        final_indexes = [((1-factor)*a) + (factor*b)
                         for (a, b) in zip(new_indexes, pure_shuffled)]

    assert len(candidates) == len(indexes) == len(final_indexes)
    shuffled = [candidates[i]
                for (f, i) in sorted(zip(final_indexes, indexes))]

    return shuffled


class TableSpecs:
    def __init__(self, specfile, pointer=None, count=None,
                 grouped=False, pointed=False, delimit=False,
                 pointerfilename=None):
        self.attributes = []
        self.bitnames = {}
        self.total_size = 0
        self.pointer = pointer
        self.count = count
        self.grouped = grouped
        self.pointed = pointed
        self.pointedpoint1 = False
        self.delimit = delimit
        self.pointerfilename = pointerfilename
        for line in open(specfile):
            line = line.strip()
            if not line or line[0] == "#":
                continue
            line = line.strip().split(',')
            if len(line) == 2:
                name, size, other = line[0], line[1], None
            elif len(line) == 3:
                name, size, other = tuple(line)

            if size[:3] == "bit":
                size, bitnames = tuple(size.split(':'))
                bitnames = bitnames.split(" ")
                assert len(bitnames) % 8 == 0
                size = len(bitnames) // 8
                assert all([bn.strip() for bn in bitnames])
                assert len(bitnames) == len(set(bitnames)) == size * 8
                self.bitnames[name] = bitnames
            elif size == '?':
                size = 0

            try:
                size = int(size)
                self.total_size += size
            except ValueError:
                a, b = size.split('x')
                self.total_size += (int(a)*int(b))
            self.attributes.append((name, size, other))


@total_ordering
class TableObject(object):
    class __metaclass__(type):
        def __iter__(self):
            for obj in self.ranked:
                yield obj

    def __init__(self, filename=None, pointer=None, index=None,
                 groupindex=0, size=None):
        assert hasattr(self, 'specs')
        assert isinstance(self.specs.total_size, int)
        assert index is not None
        if hasattr(self.specs, 'subfile'):
            self.filename = path.join(SANDBOX_PATH, self.specs.subfile)
        else:
            self.filename = filename
        if self.filename != GLOBAL_OUTPUT and PSX_FILE_MANAGER is None:
            create_psx_file_manager(filename)
        self.pointer = pointer
        self.groupindex = groupindex
        self.variable_size = size
        self.index = index
        if filename:
            self.read_data(None, pointer)
        key = (type(self), self.index)
        assert key not in GRAND_OBJECT_DICT
        GRAND_OBJECT_DICT[key] = self

    def __hash__(self):
        return hash(self.signature)

    def __eq__(self, other):
        if type(self) is type(other):
            return self.index == other.index
        return False

    def __lt__(self, other):
        if other is None:
            return False
        assert type(self) is type(other)
        return (self.rank, self.index) < (other.rank, other.index)

    @classmethod
    def create_new(cls, filename=None):
        if filename is None:
            filename = GLOBAL_OUTPUT
        index = max([o.index for o in cls.every]) + 1
        new = cls(filename=filename, index=index)
        #new.old_data = {}
        for name, size, other in new.specs.attributes:
            if other in [None, "int"]:
                setattr(new, name, 0)
            elif other == "str":
                setattr(new, name, "")
            elif other == "list":
                setattr(new, name, [])
            #new.old_data[name] = copy(getattr(new, name))

        cls._every.append(new)
        return new

    @classproperty
    def random_degree(cls):
        if hasattr(cls, "custom_random_degree"):
            return cls.custom_random_degree
        else:
            return get_random_degree()

    @classproperty
    def random_difficulty(cls):
        if hasattr(cls, 'custom_difficulty'):
            return cls.custom_difficulty
        else:
            return get_difficulty()

    @classproperty
    def numgroups(cls):
        return len(cls.groups)

    @classproperty
    def every(cls):
        if hasattr(cls, "_every"):
            return cls._every

        cls._every = list(get_table_objects(cls))
        return cls.every

    @classproperty
    def randomize_order(cls):
        return cls.every

    @property
    def rank(self):
        return 1

    @cached_property
    def ranked_ratio(self):
        if hasattr(self, '_ranked_ratio'):
            return self._ranked_ratio

        for o in self.every:
            o._ranked_ratio = None

        ranked = [o for o in self.ranked if o.rank >= 0]
        for (i, o) in enumerate(ranked):
            ratio = i / float(len(ranked)-1)
            o._ranked_ratio = ratio

        return self.ranked_ratio

    @property
    def mutate_valid(self):
        return True

    @property
    def intershuffle_valid(self):
        return True

    @property
    def intershuffle_group(self):
        return None

    @property
    def magic_mutate_valid(self):
        return True

    @property
    def catalogue_index(self):
        return self.index

    @clached_property
    def ranked(cls):
        return sorted(cls.every,
                      key=lambda c: (c.rank, c.signature))

    def assert_unchanged(self):
        for attr in self.old_data:
            if getattr(self, attr) != self.old_data[attr]:
                raise AssertionError('{0} {1} attribute "{2}" changed.'.format(
                    self.__class__.__name__, ("%x" % self.index), attr))

    def clear_cache(self):
        if hasattr(self, '_property_cache'):
            del(self._property_cache)

    def get_bit_similarity_score(self, other, bitmasks=None):
        if bitmasks is None:
            bitmasks = self.bit_similarity_attributes
        score = 0
        for attribute, mask in sorted(bitmasks.items()):
            a = self.old_data[attribute]
            if isinstance(other, dict):
                b = other[attribute]
            else:
                b = other.old_data[attribute]
            i = 0
            while True:
                bit = (1 << i)
                if bit > mask:
                    break
                i += 1
                if not bit & mask:
                    continue
                if (a & bit) == (b & bit):
                    score += 1

        return score

    def get_similar(self, candidates=None, override_outsider=False,
                    random_degree=None, allow_intershuffle_invalid=False,
                    wide=False, presorted=False):
        if not (self.intershuffle_valid or allow_intershuffle_invalid):
            return self
        if self.rank < 0:
            return self

        if random_degree is None:
            random_degree = self.random_degree

        if candidates is None:
            candidates = [c for c in self.ranked if c.rank >= 0]
        elif not presorted:
            assert all(c.rank >= 0 for c in candidates)

        if not presorted:
            if not allow_intershuffle_invalid:
                candidates = [c for c in candidates if c.intershuffle_valid]

            candidates = sorted(set(candidates),
                                key=lambda c: (c.rank, c.signature))
            if self.intershuffle_group is not None:
                candidates = [
                    c for c in candidates
                    if c.intershuffle_group == self.intershuffle_group]

        if len(candidates) <= 0:
            raise Exception("No candidates for get_similar")

        if self not in candidates:
            if override_outsider:
                index, index2 = 0, 0
                for (i, c) in enumerate(candidates):
                    if c.rank < self.rank:
                        index = i
                    elif c.rank <= self.rank:
                        index2 = i
                    elif c.rank > self.rank:
                        break
                if index2 and index2 > index:
                    index = random.randint(index, index2)
            else:
                raise Exception("Must manually override outsider elements.")
        else:
            override_outsider = False
            index = candidates.index(self)

        if not candidates:
            return self
        elif len(candidates) == 1:
            return candidates[0]

        if override_outsider:
            index = random.choice([index, index-1])
            index = max(0, min(index, len(candidates)-1))
        index = mutate_normal(index, minimum=0, maximum=len(candidates)-1,
                              random_degree=random_degree, wide=wide)
        chosen = candidates[index]
        if override_outsider:
            assert chosen is not self

        return chosen

    @classmethod
    def get_similar_set(cls, current, candidates=None):
        if candidates is None:
            candidates = [c for c in cls.every if c.rank >= 0]
        candidates = sorted(set(candidates),
                            key=lambda c: (c.rank, c.signature))
        random.shuffle(sorted(current, key=lambda c: c.index))
        chosens = []
        for c in current:
            while True:
                chosen = c.get_similar(candidates, override_outsider=True)
                assert chosen not in chosens
                chosens.append(chosen)
                candidates.remove(chosen)
                assert chosen not in candidates
                break
        assert len(chosens) == len(current)
        return chosens

    @classmethod
    def get(cls, index):
        if isinstance(index, int):
            return GRAND_OBJECT_DICT[cls, index]
        elif isinstance(index, str):
            objs = [o for o in cls.every if index in o.name]
            if len(objs) == 1:
                return objs[0]
            elif len(objs) >= 2:
                raise Exception("Too many matching objects.")
            else:
                raise Exception("No matching objects.")
        else:
            raise Exception("Bad index.")

    @classmethod
    def get_by_pointer(cls, pointer):
        objs = [o for o in cls.every if o.pointer == pointer]
        if len(objs) == 1:
            return objs[0]
        elif len(objs) >= 2:
            raise Exception("Too many matching objects.")
        else:
            raise Exception("No matching objects.")

    @classproperty
    def groups(cls):
        returndict = {}
        for obj in cls.every:
            if obj.groupindex not in returndict:
                returndict[obj.groupindex] = []
            returndict[obj.groupindex].append(obj)
        return returndict

    @classmethod
    def getgroup(cls, index):
        return [o for o in cls.every if o.groupindex == index]

    @property
    def group(self):
        return self.getgroup(self.groupindex)

    @classmethod
    def has(cls, index):
        try:
            cls.get(index)
            return True
        except KeyError:
            return False

    def get_bit(self, bitname, old=False):
        for key, value in sorted(self.specs.bitnames.items()):
            if bitname in value:
                index = value.index(bitname)
                if old:
                    byte = self.old_data[key]
                else:
                    byte = getattr(self, key)
                bitvalue = byte & (1 << index)
                return bool(bitvalue)
        raise Exception("No bit registered under that name.")

    def set_bit(self, bitname, bitvalue):
        bitvalue = 1 if bitvalue else 0
        for key, value in self.specs.bitnames.items():
            if bitname in value:
                index = value.index(bitname)
                byte = getattr(self, key)
                if bitvalue:
                    byte = byte | (1 << index)
                else:
                    byte = byte & (0xFF ^ (1 << index))
                setattr(self, key, byte)
                return
        raise Exception("No bit registered under that name.")

    @property
    def display_name(self):
        if not hasattr(self, "name"):
            self.name = "%x" % self.index
        if isinstance(self.name, int):
            return "%x" % self.name
        return "".join([c for c in self.name if c in string.printable])

    @property
    def verification_signature(self):
        return self.get_verification_signature(old_data=False)

    @property
    def old_verification_signature(self):
        return self.get_verification_signature(old_data=True)

    def get_verification_signature(self, old_data=False):
        labels = sorted([a for (a, b, c) in self.specs.attributes
                         if c not in ["str"]])
        if old_data:
            data = str([(label, self.old_data[label]) for label in labels])
        else:
            data = str([(label, getattr(self, label)) for label in labels])

        datahash = md5(data).hexdigest()
        signature = "{0}:{1:0>4}:{2}".format(
            self.__class__.__name__, ("%x" % self.index), datahash)
        return signature

    @property
    def description(self):
        classname = self.__class__.__name__
        pointer = "%x" % self.pointer if self.pointer else "None"
        desc = "{0} {1:02x} {2} {3}".format(
            classname, self.index, pointer, self.display_name)
        return desc

    @property
    def pretty_description(self):
        if hasattr(self, 'name'):
            s = '{0} {1:0>3X} {2}\n'.format(self.__class__.__name__,
                                            self.index, self.name)
        else:
            s = '{0} {1:0>3X}\n'.format(self.__class__.__name__, self.index)
        for (attr, size, other) in self.specs.attributes:
            value = getattr(self, attr)
            if isinstance(value, int):
                s += ('  {0}: {1:0>%sx}\n' % (size*2)).format(attr, value)
            elif isinstance(value, bytes):
                s += '  {0}: {1}\n'.format(attr, value)
            elif isinstance(value, list):
                if isinstance(size, str) and 'x' in size:
                    length, width = map(int, size.split('x'))
                else:
                    width = 1
                value = ' '.join([('{0:0>%sx}' % (width*2)).format(v)
                                  for v in value])
                s += '  {0}: {1}\n'.format(attr, value)
            else:
                s += '  {0}: ???\n'.format(attr)
        return s.strip()

    @property
    def long_description(self):
        s = []
        for attr in sorted(dir(self)):
            if attr.startswith('_'):
                continue

            if attr in ["specs", "catalogue"]:
                continue

            if hasattr(self.__class__, attr):
                class_attr = getattr(self.__class__, attr)
                if (isinstance(class_attr, property)
                        or hasattr(class_attr, "__call__")):
                    continue

            try:
                value = getattr(self, attr)
            except AttributeError:
                continue

            if isinstance(value, dict):
                continue

            if isinstance(value, list):
                if value and not isinstance(value[0], int):
                    continue
                value = " ".join(["%x" % v for v in value])

            if isinstance(value, int):
                value = "%x" % value

            s.append((attr, "%s" % str(value)))

        s = ", ".join(["%s: %s" % (a, b) for (a, b) in s])
        s = "%x - %s" % (self.index, s)
        return s

    @classproperty
    def catalogue(self):
        logs = []
        for obj in sorted(self.every, key=lambda o: o.catalogue_index):
            logs.append(obj.log.strip())

        if any(["\n" in log for log in logs]):
            return "\n\n".join(logs)
        else:
            return "\n".join(logs)

    @property
    def log(self):
        return str(self)

    def __repr__(self):
        return self.description

    def get_variable_specsattrs(self):
        specsattrs = [(name, self.variable_size, other)
                      for (name, size, other)
                      in self.specs.attributes if size == 0]
        if not specsattrs:
            raise ValueError("No valid specs attributes.")
        elif len(specsattrs) >= 2:
            raise ValueError("Too many specs attributes.")
        return specsattrs

    def read_data(self, filename=None, pointer=None):
        if pointer is None:
            pointer = self.pointer
        if filename is None:
            filename = self.filename
        if pointer is None or filename is None:
            return

        if self.variable_size is not None:
            specsattrs = self.get_variable_specsattrs()
        else:
            specsattrs = self.specs.attributes

        self.old_data = {}
        f = get_open_file(filename)
        f.seek(pointer)
        for name, size, other in specsattrs:
            if other in [None, "int"]:
                value = read_multi(f, length=size)
            elif other == "str":
                value = f.read(size)
            elif other == "list":
                if not isinstance(size, int):
                    number, numbytes = size.split('x')
                    number, numbytes = int(number), int(numbytes)
                else:
                    number, numbytes = size, 1
                value = []
                for i in range(number):
                    value.append(read_multi(f, numbytes))
            self.old_data[name] = copy(value)
            setattr(self, name, value)

    def copy_data(self, another):
        for name, _, _ in self.specs.attributes:
            value = getattr(another, name)
            setattr(self, name, value)

    def write_data(self, filename=None, pointer=None, syncing=False):
        if pointer is None:
            pointer = self.pointer
        if filename is None:
            filename = self.filename
        if pointer is None or filename is None:
            return

        if (not syncing and hasattr(self.specs, 'syncpointers')
                and self.specs.syncpointers):
            for p in self.specs.syncpointers:
                offset = p - self.specs.pointer
                new_pointer = self.pointer + offset
                self.write_data(filename=filename, pointer=new_pointer,
                                syncing=True)
            return

        if self.variable_size is not None:
            # doesn't seem to work properly
            raise NotImplementedError
            specsattrs = self.get_variable_specsattrs()
        else:
            specsattrs = self.specs.attributes

        f = get_open_file(filename)
        for name, size, other in specsattrs:
            value = getattr(self, name)
            if other in [None, "int"]:
                assert value >= 0
                f.seek(pointer)
                write_multi(f, value, length=size)
                pointer += size
            elif other == "str":
                assert len(value) == size
                f.seek(pointer)
                f.write(value)
                pointer += size
            elif other == "list":
                if not isinstance(size, int):
                    number, numbytes = size.split('x')
                    number, numbytes = int(number), int(numbytes)
                else:
                    number, numbytes = size, 1
                assert len(value) == number
                for v in value:
                    f.seek(pointer)
                    write_multi(f, v, length=numbytes)
                    pointer += numbytes
        return pointer

    @classmethod
    def write_all(cls, filename):
        if cls.specs.pointedpoint1 or not (
                cls.specs.grouped or cls.specs.pointed or cls.specs.delimit):
            for o in cls.every:
                o.write_data()
        elif cls.specs.grouped:
            pointer = cls.specs.pointer
            f = get_open_file(filename)
            for i in range(cls.numgroups):
                objs = [o for o in cls.every if o.groupindex == i]
                f.seek(pointer)
                if cls.specs.groupednum is None:
                    f.write(chr(len(objs)))
                    pointer += 1
                for o in objs:
                    pointer = o.write_data(None, pointer)
        elif cls.specs.pointed and cls.specs.delimit:
            pointer = cls.specs.pointedpointer
            f = get_open_file(filename)
            for i in range(cls.specs.count):
                objs = [o for o in cls.every if o.groupindex == i]
                if not objs:
                    continue
                f.seek(cls.specs.pointer + (cls.specs.pointedsize * i))
                write_multi(f, pointer-cls.specs.pointedpointer,
                            length=cls.specs.pointedsize)
                f.seek(pointer)
                for o in objs:
                    pointer = o.write_data(None, pointer)
                f.seek(pointer)
                f.write(bytes([cls.specs.delimitval]))
                pointer += 1
            if pointer == cls.specs.pointedpointer:
                raise Exception("No objects in pointdelimit data.")
            nullpointer = pointer-1
            for i in range(cls.specs.count):
                objs = [o for o in cls.every if o.groupindex == i]
                if objs:
                    continue
                f.seek(cls.specs.pointer + (cls.specs.pointedsize * i))
                write_multi(f, nullpointer-cls.specs.pointedpointer,
                            length=cls.specs.pointedsize)
        elif cls.specs.pointed:
            pointer = cls.specs.pointer
            size = cls.specs.pointedsize
            f = get_open_file(filename)
            first_pointer = min(
                [o.pointer for o in cls.every
                 if o is not None and o.pointer is not None])
            pointedpointer = max(
                first_pointer, pointer + (cls.specs.count * size))
            mask = (2 ** (8*size)) - 1
            for i in range(cls.specs.count):
                #masked = pointedpointer & mask
                masked = (pointedpointer-cls.specs.pointedpointer) & mask
                objs = [o for o in cls.every if o.groupindex == i]
                if hasattr(cls, "groupsort"):
                    objs = cls.groupsort(objs)
                for o in objs:
                    pointedpointer = o.write_data(None, pointedpointer)
                f.seek(pointer + (i*size))
                write_multi(f, masked, length=size)
        elif cls.specs.delimit:
            f = get_open_file(filename)
            pointer = cls.specs.pointer
            for i in range(cls.specs.count):
                objs = cls.getgroup(i)
                if hasattr(cls, "groupsort"):
                    objs = cls.groupsort(objs)
                for o in objs:
                    pointer = o.write_data(None, pointer)
                f.seek(pointer)
                f.write(chr(cls.specs.delimitval))
                pointer += 1

    def preprocess(self):
        return

    def preclean(self):
        return

    def cleanup(self):
        return

    @classmethod
    def full_preclean(cls):
        if hasattr(cls, "after_order"):
            for cls2 in cls.after_order:
                if not (hasattr(cls2, "precleaned") and cls2.precleaned):
                    raise Exception("Preclean order violated: %s %s"
                                    % (cls, cls2))
        for o in cls.every:
            o.reseed('preclean')
            o.preclean()
        cls.precleaned = True

    @classmethod
    def full_cleanup(cls):
        if hasattr(cls, "after_order"):
            for cls2 in cls.after_order:
                if not (hasattr(cls2, "cleaned") and cls2.cleaned):
                    raise Exception("Clean order violated: %s %s"
                                    % (cls, cls2))
        for o in cls.every:
            o.reseed('cleanup')
            o.cleanup()
        cls.cleaned = True

    @cached_property
    def signature(self):
        filename = '/'.join(self.filename.split(path.sep))
        identifier = '%s%s' % (filename, self.pointer)
        left = '%s%s%s' % (
            get_seed(), identifier, self.__class__.__name__)
        right = '%s%s' % (self.index, get_seed())
        left = md5(left.encode('ascii')).hexdigest()
        right = md5(right.encode('ascii')).hexdigest()
        return '%s%s%s%x' % (left, identifier, right, self.index)

    def reseed(self, salt=""):
        s = "%s%s%s%s" % (
            get_seed(), self.index, salt, self.__class__.__name__)
        value = int(md5(s.encode('ascii')).hexdigest(), 0x10)
        random.seed(value)

    @classmethod
    def class_reseed(cls, salt=""):
        obj = cls.every[0]
        obj.reseed(salt="cls"+salt)

    @classmethod
    def preprocess_all(cls):
        for o in cls.every:
            o.reseed(salt="preprocess")
            o.preprocess()

    @classmethod
    def full_randomize(cls):
        if hasattr(cls, "after_order"):
            for cls2 in cls.after_order:
                if not (hasattr(cls2, "randomize_step_finished")
                        and cls2.randomize_step_finished):
                    raise Exception("Randomize order violated: %s %s"
                                    % (cls, cls2))

        cls.class_reseed("group")
        cls.groupshuffle()
        cls.class_reseed("inter")
        cls.intershuffle()
        cls.class_reseed("randsel")
        cls.randomselect_all()
        cls.class_reseed("full")
        cls.shuffle_all()
        cls.randomize_all()
        cls.mutate_all()
        cls.randomized = True

    @classmethod
    def mutate_all(cls):
        for o in cls.randomize_order:
            if hasattr(o, "mutated") and o.mutated:
                continue
            o.reseed(salt="mut")
            if o.mutate_valid:
                o.mutate()
            o.mutate_bits()
            if o.magic_mutate_valid:
                o.magic_mutate_bits()
            o.mutated = True

    @classmethod
    def randomize_all(cls):
        for o in cls.randomize_order:
            if hasattr(o, "randomized") and o.randomized:
                continue
            o.reseed(salt="ran")
            o.randomize()
            o.randomized = True

    @classmethod
    def shuffle_all(cls):
        for o in cls.randomize_order:
            if hasattr(o, "shuffled") and o.shuffled:
                continue
            o.reseed(salt="shu")
            o.shuffle()
            o.shuffled = True

    def mutate(self):
        if not hasattr(self, "mutate_attributes"):
            return

        if not self.mutate_valid:
            return

        self.reseed(salt="mut")
        for attribute in sorted(self.mutate_attributes):
            mutatt = getattr(self, attribute)
            if not isinstance(mutatt, list):
                mutatt = [mutatt]
            newatt = []

            if isinstance(self.mutate_attributes[attribute], type):
                tob = self.mutate_attributes[attribute]
                for ma in mutatt:
                    tob = tob.get(ma)
                    tob = tob.get_similar()
                    newatt.append(tob.index)
            else:
                minmax = self.mutate_attributes[attribute]
                if type(minmax) is tuple:
                    minimum, maximum = minmax
                else:
                    values = [o.old_data[attribute] for o in self.every
                              if o.mutate_valid]
                    if isinstance(values[0], list):
                        values = [v2 for v1 in values for v2 in v1]
                    minimum, maximum = min(values), max(values)
                    self.mutate_attributes[attribute] = (minimum, maximum)

                for ma in mutatt:
                    if ma < minimum or ma > maximum:
                        newatt.append(ma)
                        continue
                    ma = mutate_normal(ma, minimum, maximum,
                                       random_degree=self.random_degree)
                    newatt.append(ma)

            if not isinstance(self.old_data[attribute], list):
                assert len(newatt) == 1
                newatt = newatt[0]
            setattr(self, attribute, newatt)

    def mutate_bits(self):
        if not hasattr(self, "mutate_bit_attributes"):
            return

        for attribute in sorted(self.mutate_bit_attributes):
            chance = self.mutate_bit_attributes[attribute]
            if random.random() <= chance:
                value = self.get_bit(attribute)
                self.set_bit(attribute, not value)

    def magic_mutate_bits(self, random_degree=None):
        if (self.rank < 0 or not hasattr(self, "magic_mutate_bit_attributes")
                or not self.magic_mutate_valid):
            return

        if random_degree is None:
            random_degree = self.random_degree

        base_candidates = [o for o in self.every
                           if o.magic_mutate_valid and o.rank >= 0]

        if not hasattr(self.__class__, "_candidates_dict"):
            self.__class__._candidates_dict = {}

        self.reseed(salt="magmutbit")
        for attributes in sorted(self.magic_mutate_bit_attributes):
            masks = self.magic_mutate_bit_attributes[attributes]
            if isinstance(attributes, str):
                del(self.magic_mutate_bit_attributes[attributes])
                attributes = tuple([attributes])
            if masks is None:
                masks = tuple([None for a in attributes])
            if isinstance(masks, int):
                masks = (masks,)
            bitmasks = dict(zip(attributes, masks))
            for attribute, mask in bitmasks.items():
                if mask is None:
                    mask = 0
                    for c in base_candidates:
                        mask |= getattr(c, attribute)
                    bitmasks[attribute] = mask
            masks = tuple([bitmasks[a] for a in attributes])
            self.magic_mutate_bit_attributes[attributes] = masks

            def obj_to_dict(o):
                return dict([(a, getattr(o, a)) for a in attributes])

            wildcard = [random.randint(0, m << 1) & m for m in masks]
            wildcard = []
            for attribute, mask in bitmasks.items():
                value = random.randint(0, mask << 1) & mask
                while True:
                    if not value:
                        break
                    v = random.randint(0, value) & mask
                    if not v & value:
                        if bin(v).count('1') <= bin(value).count('1'):
                            value = v
                        if random.choice([True, False]):
                            break
                    else:
                        value &= v
                value = self.old_data[attribute] ^ value
                wildcard.append((attribute, value))

            if attributes not in self._candidates_dict:
                candidates = []
                for o in base_candidates:
                    candidates.append(tuple(
                        [getattr(o, a) for a in attributes]))
                counted_candidates = Counter(candidates)
                candidates = []
                for values in sorted(counted_candidates):
                    valdict = dict(zip(attributes, values))
                    frequency = counted_candidates[values]
                    frequency = int(
                        round(frequency ** (1-(random_degree**0.5))))
                    candidates.extend([valdict]*frequency)
                self._candidates_dict[attributes] = candidates

            candidates = list(self._candidates_dict[attributes])
            candidates += [dict(wildcard)]
            if obj_to_dict(self) not in candidates:
                candidates += [obj_to_dict(self)]
            candidates = sorted(
                candidates, key=lambda o: (
                    self.get_bit_similarity_score(o, bitmasks=bitmasks),
                    o.signature if hasattr(o, "signature") else -1,
                    o.index if hasattr(o, "index") else -1),
                reverse=True)
            index = candidates.index(obj_to_dict(self))
            max_index = len(candidates)-1
            index = mutate_normal(index, 0, max_index,
                                  random_degree=random_degree, wide=True)
            chosen = candidates[index]
            if chosen is self:
                continue
            if not isinstance(chosen, dict):
                chosen = chosen.old_data
            for attribute, mask in sorted(bitmasks.items()):
                diffmask = (getattr(self, attribute) ^ chosen[attribute])
                diffmask &= mask
                if not diffmask:
                    continue
                i = 0
                while True:
                    bit = (1 << i)
                    i += 1
                    if bit > (diffmask | mask):
                        break

                    if (bit & mask and not bit & diffmask
                            and random.random() < random_degree ** 6):
                        diffmask |= bit

                    if bit & diffmask:
                        if random.random() < ((random_degree**0.5)/2.0):
                            continue
                        else:
                            diffmask ^= bit
                setattr(self, attribute, getattr(self, attribute) ^ diffmask)

    def randomize(self):
        if not hasattr(self, "randomize_attributes"):
            return
        if not self.intershuffle_valid:
            return

        self.reseed(salt="ran")
        candidates = [c for c in self.every
                      if c.rank >= 0 and c.intershuffle_valid]
        if self.intershuffle_group is not None:
            candidates = [c for c in candidates
                          if c.intershuffle_group == self.intershuffle_group]
        for attribute in sorted(self.randomize_attributes):
            chosen = random.choice(candidates)
            setattr(self, attribute, chosen.old_data[attribute])

    def shuffle(self):
        if not hasattr(self, "shuffle_attributes"):
            return

        self.reseed(salt="shu")
        for attributes in sorted(self.shuffle_attributes):
            if len(attributes) == 1:
                attribute = attributes[0]
                value = sorted(getattr(self, attribute))
                random.shuffle(value)
                setattr(self, attribute, value)
                continue
            values = [getattr(self, attribute) for attribute in attributes]
            random.shuffle(values)
            for attribute, value in zip(attributes, values):
                setattr(self, attribute, value)

    def randomselect(self, candidates=None):
        if not hasattr(self, "randomselect_attributes"):
            return

        self.reseed("randsel")
        if candidates is None:
            candidates = [c for c in self.every if c.intershuffle_valid]
        if self.intershuffle_group is not None:
            candidates = [c for c in candidates
                          if c.intershuffle_group == self.intershuffle_group]

        if len(set([o.rank for o in candidates])) <= 1:
            hard_shuffle = True
        else:
            hard_shuffle = False

        for attributes in self.randomselect_attributes:
            if hard_shuffle:
                other = random.choice(candidates)
            else:
                other = self.get_similar(candidates)
            if isinstance(attributes, str):
                attributes = [attributes]
            for attribute in attributes:
                setattr(self, attribute, other.old_data[attribute])
        self.random_selected = True

    @classmethod
    def intershuffle(cls, candidates=None, random_degree=None):
        if not hasattr(cls, "intershuffle_attributes"):
            return

        if random_degree is None:
            random_degree = cls.random_degree

        if candidates is None:
            candidates = list(cls.every)

        candidates = [o for o in candidates
                      if o.rank >= 0 and o.intershuffle_valid]

        cls.class_reseed("inter")
        hard_shuffle = False
        if (len(set([o.rank for o in candidates])) == 1
                or all([o.rank == o.index for o in candidates])):
            hard_shuffle = True

        for attributes in cls.intershuffle_attributes:
            if hard_shuffle:
                shuffled = list(candidates)
                random.shuffle(shuffled)
            else:
                candidates = sorted(
                    candidates, key=lambda c: (c.rank, c.signature))
                shuffled = shuffle_normal(candidates,
                                          random_degree=random_degree)

            if isinstance(attributes, str):
                attributes = [attributes]

            for attribute in attributes:
                swaps = []
                for a, b in zip(candidates, shuffled):
                    aval, bval = getattr(a, attribute), getattr(b, attribute)
                    swaps.append(bval)
                for a, bval in zip(candidates, swaps):
                    setattr(a, attribute, bval)

    @classmethod
    def randomselect_all(cls, candidates=None):
        if candidates is None:
            candidates = list(cls.randomize_order)
        candidates = [o for o in candidates
                      if o.rank >= 0 and o.intershuffle_valid]

        for o in candidates:
            o.randomselect(candidates=candidates)
            o.random_selected = True

    @classmethod
    def groupshuffle(cls):
        if (not hasattr(cls, "groupshuffle_enabled")
                or not cls.groupshuffle_enabled):
            return

        cls.class_reseed("group")
        shuffled = range(cls.numgroups)
        random.shuffle(shuffled)
        swapdict = {}
        for a, b in zip(range(cls.numgroups), shuffled):
            a = cls.getgroup(a)
            b = cls.getgroup(b)
            for a1, b1 in zip(a, b):
                swapdict[a1] = (b1.groupindex, b1.index, b1.pointer)

        for o in cls.every:
            groupindex, index, pointer = swapdict[o]
            o.groupindex = groupindex
            o.index = index
            o.pointer = pointer

    @property
    def full_bitnames(self):
        bitnames = dict(self.specs.bitnames)
        if hasattr(self, 'extra_bitnames'):
            for attr in self.extra_bitnames:
                bitnames[attr] = self.extra_bitnames[attr]
        return bitnames

    def export_data(self):
        import json
        data = {}
        index_length = len('%x' % (len(self.every)-1))
        data['!index'] = ('{0:0>%sx}' % index_length).format(self.index)
        for attribute in dir(self):
            if not hasattr(self.__class__, attribute):
                continue
            if hasattr(TableObject, attribute):
                continue
            if (hasattr(self, 'export_blacklist')
                    and attribute in self.export_blacklist):
                continue
            if isinstance(getattr(self.__class__, attribute), property):
                value = getattr(self, attribute)
                if isinstance(value, int):
                    value = '%x' % value
                if isinstance(value, list) or isinstance(value, set):
                    value = ['%x' % v if isinstance(v, int) else v
                             for v in value]
                try:
                    json.dumps(value)
                    data['#%s' % attribute] = value
                except TypeError:
                    value = str(value)
                    data['#%s' % attribute] = value
        for attribute, length, other in self.specs.attributes:
            value = getattr(self, attribute)
            if attribute in self.full_bitnames:
                bitnames = self.full_bitnames[attribute]
                setbits = []
                for i, bitname in enumerate(bitnames):
                    if value & (1 << i):
                        setbits.append(bitname)
                value = setbits
            if other == 'str':
                if hasattr(self, 'decode_bytes'):
                    value = self.decode_bytes(value)
                else:
                    value = [c for c in value]
            if other == 'list':
                if isinstance(length, str):
                    value_length, value_width = length.split('x')
                    value_length = int(value_length)
                    value_width = int(value_width)
                else:
                    value_length = int(length)
                    value_width = 1
                assert len(value) == value_length
                value = [('{0:0>%sx}' % (value_width*2)).format(v)
                         for v in value]
            if isinstance(value, int):
                value = ('{0:0>%sx}' % (length * 2)).format(value)
            data[attribute] = value
        return data

    def import_data(self, data):
        assert int(data['!index'], 0x10) == self.index
        attributes = [a for (a, _ , _) in self.specs.attributes]

        for key in data:
            if key in attributes:
                continue
            if key.startswith('#') or key.startswith('!'):
                continue
            setattr(self, key, data[key])

        for attribute, length, other in self.specs.attributes:
            if attribute not in data:
                continue
            value = data[attribute]
            if other == 'str':
                if hasattr(self, 'encode_bytes'):
                    value = self.encode_bytes(value)
                else:
                    value = bytes(value)
            elif other == 'list':
                assert type(self.old_data[attribute]) is list
                value = [int(v, 0x10) if isinstance(v, str) else v
                         for v in value]
                if isinstance(length, str):
                    value_length, _ = length.split('x')
                    value_length = int(value_length)
                else:
                    value_length = length
                assert value_length == len(value)
            elif isinstance(value, list):
                assert attribute in self.full_bitnames
                assert type(self.old_data[attribute]) is int
                bitnames = self.full_bitnames[attribute]
                new_value = 0
                for name in value:
                    assert bitnames.count(name) == 1
                    new_value |= 1 << bitnames.index(name)
                value = new_value
            else:
                if isinstance(value, str):
                    value = int(value, 0x10)
            assert type(value) is type(self.old_data[attribute])
            setattr(self, attribute, value)

    @classmethod
    def export_all(cls):
        return [o.export_data() for o in cls.every]

    @classmethod
    def import_all(cls, datas):
        for data in datas:
            index = int(data['!index'], 0x10)
            cls.get(index).import_data(data)


already_gotten = {}


def get_table_objects(objtype, filename=None):
    pointer = objtype.specs.pointer
    number = objtype.specs.count
    grouped = objtype.specs.grouped
    pointed = objtype.specs.pointed
    delimit = objtype.specs.delimit
    pointerfilename = objtype.specs.pointerfilename
    identifier = (objtype, pointer, number)
    if identifier in already_gotten:
        return already_gotten[identifier]

    if filename is None:
        filename = GLOBAL_OUTPUT
    objects = []

    def add_objects(n, groupindex=0, p=None, obj_filename=None):
        if obj_filename is None:
            obj_filename = filename
        if p is None:
            p = pointer
        accumulated_size = 0
        for i in range(n):
            obj = objtype(obj_filename, p, index=len(objects),
                          groupindex=groupindex)
            objects.append(obj)
            p += obj.specs.total_size
            accumulated_size += obj.specs.total_size
        return accumulated_size

    def add_variable_object(p1, p2):
        size = p2 - p1
        obj = objtype(filename, p1, index=len(objects),
                      groupindex=0, size=size)
        objects.append(obj)
        return size

    if pointerfilename is not None:
        for line in open(path.join(tblpath, pointerfilename)):
            line = line.strip()
            if not line or line[0] == '#':
                continue
            line = line.split()[0]
            if '@' in line:
                pointer, obj_filename = line.split('@')
                obj_filename = obj_filename.replace('/', path.sep)
                obj_filename = obj_filename.replace('\\', path.sep)
                obj_filename = path.join(SANDBOX_PATH, obj_filename)
            else:
                pointer = line
                obj_filename = None
            pointer = int(pointer, 0x10)
            add_objects(1, p=pointer, obj_filename=obj_filename)
    elif not grouped and not pointed and not delimit:
        add_objects(number)
    elif grouped:
        counter = 0
        while len(objects) < number:
            if objtype.specs.groupednum is None:
                f = get_open_file(filename)
                f.seek(pointer)
                value = ord(f.read(1))
                pointer += 1
            else:
                value = objtype.specs.groupednum
            pointer += add_objects(value, groupindex=counter)
            counter += 1
    elif pointed and delimit:
        size = objtype.specs.pointedsize
        counter = 0
        f = get_open_file(filename)
        while counter < number:
            f.seek(pointer)
            subpointer = read_multi(f, size) + objtype.specs.pointedpointer
            while True:
                f.seek(subpointer)
                peek = ord(f.read(1))
                if peek == objtype.specs.delimitval:
                    break
                obj = objtype(filename, subpointer, index=len(objects),
                              groupindex=counter, size=None)
                objects.append(obj)
                subpointer += objtype.specs.total_size
            pointer += size
            counter += 1
    elif pointed and objtype.specs.total_size > 0:
        size = objtype.specs.pointedsize
        counter = 0
        f = get_open_file(filename)
        while counter < number:
            f.seek(pointer)
            subpointer = read_multi(f, size) + objtype.specs.pointedpointer
            f.seek(pointer + size)
            subpointer2 = read_multi(f, size) + objtype.specs.pointedpointer
            groupcount = (subpointer2 - subpointer) // objtype.specs.total_size
            if objtype.specs.pointedpoint1:
                groupcount = 1
            add_objects(groupcount, groupindex=counter, p=subpointer)
            pointer += size
            counter += 1
    elif pointed and objtype.specs.total_size == 0:
        size = objtype.specs.pointedsize
        counter = 0
        f = get_open_file(filename)
        while counter < number:
            f.seek(pointer + (size*counter))
            subpointer = read_multi(f, size) + objtype.specs.pointedpointer
            f.seek(pointer + (size*counter) + size)
            subpointer2 = read_multi(f, size) + objtype.specs.pointedpointer
            add_variable_object(subpointer, subpointer2)
            counter += 1
    elif delimit:
        f = get_open_file(filename)
        for counter in range(number):
            while True:
                f.seek(pointer)
                peek = ord(f.read(1))
                if peek == objtype.specs.delimitval:
                    pointer += 1
                    break
                obj = objtype(filename, pointer, index=len(objects),
                              groupindex=counter, size=None)
                objects.append(obj)
                pointer += obj.specs.total_size

    already_gotten[identifier] = objects

    return get_table_objects(objtype, filename=filename)


def set_table_specs(objects, filename=None):
    if filename is None:
        filename = GLOBAL_TABLE
    tablesfile = path.join(tblpath, filename)
    for line in open(tablesfile):
        if '#' in line:
            line = line.split('#')[0]
        line = line.strip()
        if not line:
            continue

        if line[0] == '$':
            attr, value = line.lstrip('$').strip().split(' ', 1)
            attr = attr.strip()
            value = value.strip()
            try:
                value = int(value, 0x10)
                setattr(addresses, attr, value)
            except ValueError:
                namesfilepath = path.join(tblpath, value)
                namelist = []
                with open(namesfilepath) as namesfile:
                    for line in namesfile:
                        if '#' in line:
                            line, _ = line.split('#', 1)
                        line = line.strip()
                        namelist.append(line)
                setattr(names, attr, namelist)

            continue

        if any(line.startswith(s) for s in [".patch", ".option"]):
            _, patchfilename = line.strip().split(' ', 1)
            patchfilename = patchfilename.strip()
            PATCH_FILENAMES.append(patchfilename)
            if line.startswith(".option"):
                OPTION_FILENAMES.append(patchfilename)
            if ".no_verify" in line:
                NOVERIFY_PATCHES.append(patchfilename)
            continue

        while "  " in line:
            line = line.replace("  ", " ")
        line = line.split()
        groupednum = None
        pointerfilename = None
        pointer = None
        subfile = None
        count = None
        syncpointers = False
        if len(line) >= 5:
            (objname, tablefilename, pointer, count,
                organization) = tuple(line[:5])
            args = line[5:]
            if organization.lower() not in ["grouped", "pointed", "point1",
                                            "pointdelimit", "delimit"]:
                raise NotImplementedError
            grouped = True if organization.lower() == "grouped" else False
            pointed = True if organization.lower() == "pointed" else False
            point1 = True if organization.lower() == "point1" else False
            delimit = True if organization.lower() == "delimit" else False
            pointdelimit = (True if organization.lower() == "pointdelimit"
                            else False)
            pointed = pointed or point1 or pointdelimit
            delimit = delimit or pointdelimit
            if pointed:
                pointedpointer = int(args[0], 0x10)
                pointedsize = int(args[1]) if len(args) > 1 else 2
            if grouped and len(args) >= 1:
                groupednum = int(args[0])
            if delimit and not pointdelimit:
                delimitval = int(args[0])
            if pointdelimit:
                pointedpointer = int(args[0], 0x10)
                pointedsize = int(args[1]) if len(args) > 1 else 2
                delimitval = int(args[2])
        else:
            grouped = False
            pointed = False
            point1 = False
            delimit = False
            pointdelimit = False
            if len(line) <= 3:
                objname, tablefilename, pointerfilename = tuple(line)
            else:
                objname, tablefilename, pointer, count = tuple(line)
        if pointer is not None and isinstance(pointer, str):
            if '@' in pointer:
                pointer, subfile = pointer.split('@')
                subfile = subfile.replace('/', path.sep)
                subfile = subfile.replace('\\', path.sep)
            if ',' in pointer:
                pointers = map(lambda p: int(p, 0x10), pointer.split(','))
                pointer = pointers[0]
                syncpointers = True
            else:
                pointer = int(pointer, 0x10)
                syncpointers = False
        if count is not None:
            count = int(count)
        TABLE_SPECS[objname] = TableSpecs(path.join(tblpath, tablefilename),
                                          pointer, count, grouped, pointed,
                                          delimit, pointerfilename)

        objs = [o for o in objects if o.__name__ == objname]
        assert len(objs) == 1
        objs[0].specs = TABLE_SPECS[objname]
        if pointed or point1 or pointdelimit:
            TABLE_SPECS[objname].pointedpointer = pointedpointer
            TABLE_SPECS[objname].pointedsize = pointedsize
            TABLE_SPECS[objname].pointedpoint1 = point1
        if grouped:
            TABLE_SPECS[objname].groupednum = groupednum
        if delimit or pointdelimit:
            TABLE_SPECS[objname].delimitval = delimitval
        if syncpointers:
            TABLE_SPECS[objname].syncpointers = pointers
        if subfile:
            TABLE_SPECS[objname].subfile = subfile
