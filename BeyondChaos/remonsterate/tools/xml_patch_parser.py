from collections import defaultdict
from difflib import SequenceMatcher
from os import path
from sys import argv
from xml.etree import ElementTree

from .tablereader import tblpath, get_open_file

alt_filenames = {}

try:
    for line in open(path.join(tblpath, "xml_name_mapping.txt")):
        line = line.strip()
        if not line or line[0] == '#':
            continue
        while '  ' in line:
            line = line.replace('  ', ' ')

        filename, alt_filename = line.split()
        alt_filenames[filename] = alt_filename
except FileNotFoundError:
    pass


def text_to_bytecode(text):
    text = ''.join(text.strip().split())
    assert not (len(text) % 2)
    pairs = [a + b for (a, b) in zip(text[::2], text[1::2])]
    assert len(pairs) == len(text) / 2.0
    return b''.join([int(p, 0x10).to_bytes(1, byteorder='little')
                     for p in pairs])


def get_patchdicts(filename):
    tree = ElementTree.parse(filename)
    assert tree.getroot().tag == 'Patches'
    patches = [n for n in tree.getroot()]
    patchdicts = []
    for patch in patches:
        is_asm_patch = False
        patchdict = {}
        patchdict['filename'] = filename
        patchdict['locations'] = []
        patchdict['variables'] = []
        for key, value in patch.items():
            assert key == 'name'
            patchdict['name'] = value
        assert patch.tag == 'Patch'
        for node in patch:
            if node.tag == 'Location':
                locdict = {}
                for key, value in node.items():
                    assert key in {'file', 'offset', 'mode',
                                   'offsetMode', 'inputFile'}
                    assert key not in locdict
                    if key == 'file' and value in alt_filenames:
                        value = alt_filenames[value]
                    locdict[key] = value
                locdict['offset'] = int(locdict['offset'], 0x10)
                if 'mode' not in locdict:
                    locdict['mode'] = 'DATA'
                assert locdict['mode'] in {'DATA', 'ASM'}
                if locdict['mode'] == 'DATA':
                    locdict['data'] = text_to_bytecode(node.text)
                if locdict['mode'] == 'ASM' or 'offsetMode' in locdict:
                    is_asm_patch = True
                patchdict['locations'].append(locdict)
            elif node.tag == 'Description':
                assert 'description' not in patchdict
                patchdict['description'] = node.text.strip()
            elif node.tag == 'Variable':
                assert node.text is None
                vardict = {}
                for key, value in node.items():
                    assert key in {'name', 'file', 'offset', 'default',
                                   'bytes'}
                    assert key not in vardict
                    if key == 'file' and value in alt_filenames:
                        vardict[key] = alt_filenames[value]
                    elif key in {'offset', 'default'}:
                        vardict[key] = int(value, 0x10)
                    elif key in {'bytes'}:
                        vardict[key] = int(value)
                    else:
                        vardict[key] = value
                if 'bytes' not in vardict:
                    vardict['bytes'] = 1
                patchdict['variables'].append(vardict)
            else:
                assert False
        if not is_asm_patch:
            patchdicts.append(patchdict)
    patchdicts = sorted(patchdicts, key=lambda p: p['name'])
    assert len(patchdicts) == len(set([p['name'] for p in patchdicts]))
    return patchdicts


def get_patches(directory, config_file):
    patch_filepath = path.join(directory, config_file)
    try:
        f = open(patch_filepath)
    except FileNotFoundError:
        print("WARNING: File not found - %s" % patch_filepath)
        return []

    xmlfilenames = defaultdict(set)
    varvals = defaultdict(set)
    xmlfilename, patchname = None, None
    for line in f:
        line = line.rstrip()
        if line and line[0] != '#':
            while '  ' in line:
                line = line.replace('  ', ' ')
            if line[0] == ' ':
                variable, value = line.strip().rsplit(' ', 1)
                value = int(value)
                varvals[xmlfilename, patchname] = variable, value
                continue
            xmlfilename, patchname = line.split(' ', 1)
            xmlfilenames[xmlfilename].add(patchname)

    patches = []
    for xmlfilename in sorted(xmlfilenames):
        try:
            my_patches = get_patchdicts(path.join(directory, xmlfilename))
        except IOError:
            raise Exception("ERROR: file %s not in xml patch directory."
                            % xmlfilename)
        for name in sorted(xmlfilenames[xmlfilename]):
            for p in my_patches:
                if p['name'] == name:
                    if (xmlfilename, name) in varvals:
                        variable, value = varvals[xmlfilename, name]
                        if 'varvals' not in p:
                            p['varvals'] = {}
                        p['varvals'][variable] = value
                    patches.append(p)
                    break
            else:
                raise Exception("ERROR: unknown patch %s %s"
                                % (xmlfilename, name))

    return patches


def patch_patch(directory, patchdict, verify=False):
    if 'varvals' not in patchdict:
        varvals = {}
    else:
        varvals = patchdict['varvals']

    if not verify:
        print("Applying patch: %s" % patchdict['name'])
    elif verify:
        print("Verifying patch: %s" % patchdict['name'])

    for location in patchdict['locations'] + patchdict['variables']:
        offset = location['offset']

        length = (location['bytes'] if 'bytes' in location
                  else len(location['data']))

        if 'bytes' in location:
            length = location['bytes']
            if location['name'] in varvals:
                value = varvals[location['name']]
            elif 'default' in location:
                value = location['default']
            else:
                raise Exception("No value given for variable: %s %s" %
                                (patchdict['name'], location['name']))
            if not verify:
                print('-- Variable:', location['name'], value)
            to_write = value.to_bytes(length, byteorder='little')
            assert len(to_write) == length
        else:
            to_write = location['data']
            length = len(to_write)

        filename = path.join(directory, location['file'])
        to_patch = get_open_file(filename)
        to_patch.seek(offset)

        if verify:
            patched_data = to_patch.read(length)
            if patched_data != to_write:
                to_write_var = to_write
                for varloc in patchdict['variables']:
                    varoffset = varloc['offset']
                    varlength = varloc['bytes']
                    varname = varloc['name']
                    if offset <= varoffset < offset + length:
                        middle = varoffset - offset
                        if varname in varvals:
                            varval = varvals[varname]
                        else:
                            varval = varloc['default']
                        data = varval.to_bytes(varlength, byteorder='little')
                        to_write_var = (to_write_var[:middle] + data +
                                        to_write_var[middle+varlength:])
                if patched_data != to_write_var:
                    raise Exception("Verification failed: %s %s"
                                    % (patchdict['name'], location['offset']))

        if not verify:
            to_patch.write(to_write)
