#!/usr/bin/env python3

# Dialogue manager:
# Stores words defined in other parts of the Randomizer,
# then patches and re-inserts dialogue scripts with
# designated words changed to the new, randomized words.

# NOTE: FF3usME indexes are 1 lower than the actual ROM indexes used here

import os
import re
from utils import dialoguetexttable, bytes_to_dialogue, utilrandom as random, open_mei_fallback as open, read_multi, write_multi

try:
    from sys import _MEIPASS
    MEI = True
except ImportError:
    MEI = False

SCRIPT_DEBUG = False
SCRIPT_DEBUG_VERBOSE = False

textdialoguetable = {v:k for k, v in dialoguetexttable.items()}
for i in range(0xFF):
    if f"{i:02X}" not in textdialoguetable:
        textdialoguetable[f"{i:02X}"] = f"${i:02X}"
textdialoguetable["63"] = "'"

dialoguebytetable = {}
for k, v in dialoguetexttable.items():
    dialoguebytetable[k] = v
for i in range(0xFF):
    dialoguebytetable[f"${i:02X}"] = f"{i:02X}"
dialoguebytetable["'"] = dialoguebytetable["’"]

dialogue_vars = {}
dialogue_flags = set()
dialogue_vals = {}
dialogue_patches = {}
dialogue_patches_battle = {}
script_ptrs = {}
script = {}
script_bin = bytes()
script_edited = False

location_name_ptrs = {}
location_names = {}
location_name_bin = bytes()

def safepath(vpath):
    # NEW
    # this prepends the absolute file path of the parent/calling script
    #   to the virtual path passed as a param - GreenKnight5
    vpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), vpath)

    if not MEI:
        return vpath
    return [vpath, os.path.join(_MEIPASS, vpath)]

def dprint(text, *args, **kwargs):
    if SCRIPT_DEBUG:
        print(text, *args, **kwargs)

def vprint(text, *args, **kwargs):
    if SCRIPT_DEBUG_VERBOSE:
        print(text, *args, **kwargs)
        
#need to use a different table here, so redefined
def dialogue_to_bytes(text, null_terminate=True):
    bs = []
    i = 0
    while i < len(text):
        if text[i] == " ":
            spaces = re.match(" +", text[i:]).group(0)
            count = len(spaces)
            j = i + count
            hexstr = dialoguebytetable.get(text[i:j], "")
            if not hexstr:
                hexstr = dialoguebytetable.get(text[i])
                j = i + 1
            i = j
        elif text[i] == "<":
            j = text.find(">", i) + 1
            hexstr = dialoguebytetable.get(text[i:j], "")
            i = j
        elif i < len(text) - 1 and text[i:i+2] in dialoguebytetable:
            hexstr = dialoguebytetable[text[i:i+2]]
            i += 2
        elif text[i] == "$":
            hexstr = text[i+1:i+3]
            i += 3
        else:
            hexstr = dialoguebytetable[text[i]]
            i += 1

        if hexstr != "":
            bs.extend(bytes.fromhex(hexstr))

    if not bs:
        return bytes([0x0])

    if null_terminate and bs[-1] != 0x0:
        bs.append(0x0)

    return bytes(bs)

ID_NAMES = ['terra','locke','cyan','shadow','edgar','sabin','celes','strago','relm','setzer','mog','gau','gogo','umaro','trooper','kappa','leo','banon','trance','merchant','ghost','kefka']
VANILLA_GENDER = ["female", "male", "male", "male", "male", "male", "female", "male", "female", "male", "male", "male", "neutral", "male", "male", "object", "male", "male", "female", "male", "neutral", "male"]

# Dialogue variables - a placeholder is replaced by text set elsewhere in the randomizer
#                      The function call defines the actual text written to ROM output.
# Dialogue flags - allows script placeholders that check a TRUE or FALSE value
#                  The function call defines only the boolean value;
#                  output text options are defined in the script file.
# Dialogue values - allows script placeholders that check a numeric value (index)
#                   The function call defines only the numeric value;
#                   output text options are defined in the script file.

def set_dialogue_var(k, v):
    dialogue_vars[k.lower()] = v

def set_dialogue_flag(f, v=True):
    if v:
        dialogue_flags.add(f.lower())
    elif f in dialogue_flags:
        dialogue_flags.remove(f)

def set_dialogue_value(k, v):
    dialogue_vals[k.lower()] = v
    
def initialize_pronouns():
    for i, gender in enumerate(VANILLA_GENDER):
        set_pronoun(ID_NAMES[i], gender)
        
        
def set_pronoun(character, gender, force=True):
    # Allow using either char.id or name string
    if character in range(0,len(ID_NAMES)):
        name = ID_NAMES[character]
    else:
        name = character
                
    gender = gender.lower()
    name = name.lower().capitalize()

    dprint(f"{name} is {gender}")
    
    if "random" in gender:
        force = True
        opts = ["male"]*19+["female"]*19+["neutral"]*2 if "truerandom" not in gender else ["male", "female", "neutral"]
        if gender == "orandom":
            opts += ["object"]*40
        gender = random.choice(opts)

    if not force:
        if gender == "neutral":
            gender = random.choice(["male"]*19 + ["female"]*19 + ["neutral"]*2)
        elif gender != "object":
            gender = random.choice([gender]*19 + ["neutral"])

    if gender == "male":
        pset = ("he", "him", "his", "his", "he's")
        set_dialogue_flag(name + "Plu", False)
        set_dialogue_value(name + "Gen", 0)
    elif gender == "female":
        pset = ("she", "her", "her", "hers", "she's")
        set_dialogue_flag(name + "Plu", False)
        set_dialogue_value(name + "Gen", 1)
    elif gender == "object":
        pset = ("it", "it", "its", "its", "it's")
        set_dialogue_flag(name + "Plu", False)
        set_dialogue_value(name + "Gen", 3)
    else:
        pset = ("they", "them", "their", "theirs", "they're")
        set_dialogue_flag(name + "Plu")
        set_dialogue_value(name + "Gen", 2)
        gender = "neutral"

    pmap = ("Ey", "Em", "Eir", "Eirs", "EyIs")
    for i in range(5):
        set_dialogue_var(name + pmap[i], pset[i])

    return gender

def patch_dialogue(id, from_text, to_text, index=None, battle=False):
    patches = dialogue_patches_battle if battle else dialogue_patches
    if id not in patches:
        patches[id] = {}
    patches[id][(from_text.lower(), index)] = to_text

def get_dialogue(idx):
    return script[idx]

def set_dialogue(idx, text):
    global script_edited
    script[idx] = text
    script_edited = True

def set_location_name(idx, text):
    location_names[idx] = text

def load_patch_file(fn):
    filepath = os.path.join('data', 'script', fn + ".txt")

    # NEW
    # this prepends the absolute file path of the parent/calling script
    #   to filepath created above - GreenKnight5
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filepath)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except IOError:
        print(f"failed to open data/script/{fn}.txt")
        return
    for i, line in enumerate(lines):
        s = line.split(':', 1)
        try:
            script_idx = int(s[0].strip())
        except ValueError:
            print(f"{fn}.txt: line {i} - {s[0]} is not a valid caption index")
            continue
        changes = s[1].rstrip('\n').split('|')
        for c in changes:
            if '->' not in c:
                continue
            chgfrom, chgto = c.split('->', 1)
            if '@' in chgfrom:
                chgfrom, match_idx = chgfrom.split('@', 1)
                try:
                    match_idx = int(match_idx)
                except ValueError:
                    print(f"{fn}.txt: line {i} - {match_idx} is not a valid match index")
                    match_idx = 0
            else:
                match_idx = None
            if chgto == "*":
                chgto = None
            patch_dialogue(script_idx, chgfrom, chgto, index=match_idx)

def load_custom_words():
    filepath = os.path.join('custom', "words.txt")
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filepath)
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except IOError:
        print(f"failed to open data/script/{fn}.txt")
        return
        
    pos = 0
    while pos < len(lines):
        line = lines[pos]
        # Ignore comments
        line = line.split('#')[0]
        
        if line.startswith("define"):
            options = []
            line = line[6:]
            name, fields = line.split(':', 1)
            name = name.strip()
            fields = [f.strip() for f in fields.split()]
            if not fields:
                fields.append("")
                
            while pos < len(lines):
                pos += 1
                line = lines[pos].strip()
                if not line:
                    continue
                if line.lower() == "end":
                    break
                if '|' in line:
                    conditions, words = line.rsplit('|', 1)
                else:
                    conditions = []
                    words = line
                
                if conditions:
                    conditions = conditions.split('|')
                no_conditions_failed = True
                for condition in conditions:
                    passed = False
                    if condition.lower().startswith('not'):
                        reverse = True
                        condition = condition[3:].strip()
                    else:
                        reverse = False
                    if '=' not in condition:
                        if condition.strip().lower() in dialogue_flags:
                            passed = True
                    else:
                        var, test = condition.split('=')
                        var = var.lower()
                        if var in dialogue_vars:
                            if dialogue_vars[var] == test.strip():
                                passed = True
                    if reverse:
                        passed = False if passed else True
                    if not passed:
                        no_conditions_failed = False
                        break
                if no_conditions_failed:
                    words = [w.strip() for w in words.split('\\')]
                    if len(words) == len(fields):
                        options.append(words)
                        dprint(f"added {words} to options for {name}")
                    else:
                        print(f"warning: words.txt: wrong number of words in line {pos} ({len(words)} words for {len(fields)} fields)")
            if not options:
                print(f"warning: words.txt: no valid options for {name}")
            else:
                words = random.choice(options)
                dprint(f"chose option {words} for {name}")
                for i, word in enumerate(words):
                    varname = name + fields[i]
                    while '{' in word:
                        word = patch(word, varname)
                    set_dialogue_var(varname, word) 
        pos += 1
                    
def read_dialogue(fout):
    #load existing script & pointer table
    fout.seek(0xD0000)
    script_bin = fout.read(0x1F0FF)

    #TODO battle script

    fout.seek(0xCE600)
    bankidx = read_multi(fout, 2)
    for idx in range(0xC0C): #C0D through CFF pointers are repurposed
        script_ptrs[idx] = read_multi(fout, 2) + (0x10000 if idx >= bankidx else 0)

    for idx in range(0xC0C): #C0D through CFF pointers are repurposed
        start = script_ptrs[idx]
        end = script_ptrs.get(idx+1, 0)
        if end == 0:
            end = script_bin.find(b'\x00', start)
        script[idx] = bytes_to_dialogue(script_bin[start:end])

def manage_dialogue_patches(fout):
    global script_bin

    #don't do anything unless we need to
    if not dialogue_patches and not dialogue_patches_battle and not script_edited:
        return

    #TODO battle pointers

    #apply changes to dialogue
    for idx, patches in dialogue_patches.items():
        line = split_line(script[idx])

        vprint(f"patching line {idx}")
        vprint(f"  original: {script[idx]}")
        token_counter = {}
        for i, token in enumerate(line):
            if token.lower() not in token_counter:
                token_counter[token.lower()] = 1
            else:
                token_counter[token.lower()] += 1
            if (token.lower(), token_counter[token.lower()]) in patches:
                line[i] = patch(patches[token.lower(), token_counter[token.lower()]], token)
            elif (token.lower(), None) in patches:
                line[i] = patch(patches[token.lower(), None], token)
            #handle removing text along with following space
            if line[i] is None:
                line[i] = ""
                try:
                    if line[i+1][0] == " ":
                        line[i+1] = "" if len(line[i+1]) < 2 else line[i+1][1:]
                except IndexError:
                    pass
        new_text = "".join(line)
        vprint(f"  new: {new_text}")
        script[idx] = new_text

    new_script = b""
    new_ptrs = b""
    offset = 0
    first_high_index = None
    for idx, text in script.items():
    ####TODO!!! rewrite to only re-encode dialogue if it is changed?
        lastlength = len(new_script) - offset
        if first_high_index:
            lastlength -= 0x10000
        offset += lastlength
        if offset > 0xFFFF:
            if offset > 0x1FFFF or first_high_index is not None:
                print(f"script addressing overflow at index {idx}")
                raise IndexError
            offset -= 0x10000
            first_high_index = idx
            dprint(f"first high index at {first_high_index}")
        new_script += dialogue_to_bytes(text)
        new_ptrs += bytes([offset & 0xFF, (offset >> 8) & 0xFF])
    dprint(f"new script: ${len(new_script):X} bytes")

    #write to file
    fout.seek(0xD0000)
    assert len(new_script) <= 0x1F0FF
    fout.write(new_script)

    fout.seek(0xCE600)
    write_multi(fout, first_high_index)
    assert len(new_ptrs) <= 0x19FE
    fout.write(new_ptrs)

def read_script(idx, battle=False):
    loc = script_ptrs[idx]
    dialogue = []
    while loc < len(script_bin):
        if script_bin[loc] == 0:
            break
        dialogue.append(textdialoguetable[f"{script_bin[loc]:02X}"])
        loc += 1
    return "".join(dialogue)

def split_line(line):
    line = line.replace('’', "'")
    split = re.split("(\$..|[A-Za-z']+|[^$A-Za-z']+)", line)
    return [s for s in split if len(s)]

def patch(text, token):
    if text is None:
        return None
    vprint(f'patching "{token}" by {text}', end="")
    while True:
        match = re.search("\{(.+)\}", text)
        if not match:
            break

        # handle conditionals/flags
        if "?" in match[1]:
            flag, opts = match[1].split('?', 1)
            opts = opts.split(':')
            if len(opts) > 2:
                try:
                    opt_idx = dialogue_vals[flag.lower()]
                except KeyError:
                    print(f"warning: dialogue value {flag} not defined")
                    opt_idx = 0
                # Silently use final option if index is too high.
                # This will allow distinguishing Object (3) from Neutral (2)
                # genders while allowing Object to cleanly fall back to
                # Neutral when undefined.
                try:
                    var = opts[opt_idx]
                except IndexError:
                    var = opts[-1]
            else:
                try:
                    textiftrue, textiffalse = opts
                except ValueError:
                    textiftrue = opts
                    textiffalse = ""
                var = textiftrue if flag.lower() in dialogue_flags else textiffalse
        # handle variables
        else:
            if match[1].lower() not in dialogue_vars:
                print(f"warning: dialogue variable {match[1]} not defined")
                var = match[1]
            else:
                var = dialogue_vars[match[1].lower()]

            if match[1].upper() == match[1]:
                var = var.upper()
            elif match[1][0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                try:
                    var = var[0].upper() + var[1:]
                except IndexError:
                    var = var.capitalize()

        text = text[0:match.start()] + var + text[match.end():]

    vprint(f' to "{text}"')
    return text

def read_location_names(f):
    #load existing script & pointer table
    f.seek(0xEF100)
    location_name_bin = f.read(0x4ff)

    f.seek(0x268400)
    for idx in range(0x49):
        location_name_ptrs[idx] = read_multi(f, 2)

    for idx in range(0x49):
        start = location_name_ptrs[idx]
        end = location_name_ptrs.get(idx+1, location_name_bin.find(b'\0', start) + 1)
        location_names[idx] = bytes_to_dialogue(location_name_bin[start:end])

def write_location_names(fout):
    new_location_names = b""
    new_ptrs = b""
    offset = 0
    for idx, text in location_names.items():
        lastlength = len(new_location_names) - offset

        offset += lastlength
        if offset > 0x1FFFF:
            print(f"location name addressing overflow at index {idx}")
            raise IndexError
        new_location_names += dialogue_to_bytes(text)
        new_ptrs += bytes([offset & 0xFF, (offset >> 8) & 0xFF])
    dprint(f"new location names: ${len(new_location_names):X} bytes")

    #write to file
    fout.seek(0xEF100)
    assert len(new_location_names) <= 0x4FF
    fout.write(new_location_names)

    fout.seek(0x268400)
    assert len(new_ptrs) <= 0x375
    fout.write(new_ptrs)
