# Beyond Chaos - functions to interface with johnnydmad module
#                (music randomizer)

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "music"))
sys.path.append(os.path.join(os.path.dirname(__file__), "music", "mfvitools"))

from musicrandomizer import process_music, process_formation_music_by_table, process_map_music, get_music_spoiler as get_spoiler
from johnnydmad import add_music_player

BC_MUSIC_FREESPACE = ["53C5F-9FDFF", "310000-37FFFF", "410000-5FFFFF"]

def randomize_music(fout, options_, opera=None, form_music_overrides={}):
    events = ""
    if options_.is_code_active('christmas'):
        events += "W"
    if options_.is_code_active('halloween'):
        events += "H"
    f_chaos = options_.is_code_active('johnnyachaotic')
    
    fout.seek(0)
    data = fout.read()
    metadata = {}
    ## For anyone who wants to add UI for playlist selection:
    ## If a playlist is selected, pass it as process_music(playlist_filename=...)
    data = process_music(data, metadata, f_chaos=f_chaos, eventmodes=events, basepath="music", freespace=BC_MUSIC_FREESPACE)
    if not options_.is_any_code_active(['ancientcave', 'speedcave', 'racecave']):
        data = process_map_music(data)
    data = process_formation_music_by_table(data, form_music_overrides=form_music_overrides)
    
    data = add_music_player(data, metadata)
    
    fout.seek(0)
    fout.write(data)
    
def get_music_spoiler(*a, **kw):
    return get_spoiler(*a, **kw)
    
####### OPERA #######

def manage_opera(fout, affect_music):
    fout.seek(0)
    data = fout.read()
    
    #2088 blocks available for all 3 voices in Waltz 3
    SAMPLE_MAX_SIZE = 0x4968 
    
    #Determine opera cast
    
    class OperaSinger:
        def __init__(self, name, title, sprite, gender, file, sample, octave, volume, init):
            self.name = name
            self.title = title
            self.sprite = sprite
            self.gender = gender
            self.file = file
            self.sample = int(sample,16)
            self.octave = octave
            self.volume = volume
            self.init = init
    
    #voice range notes
    # Overture (Draco) ranges from B(o-1) to B(o)
    # Aria (Maria) ranges from D(o) to D(o+1)
    # Duel 1 (Draco) ranges from B(o-1) to E(o)
    # Duel 2 (Maria) ranges from A(o) to F(o+1)
    # Duel 3 (Ralse) ranges from E(o) to C(o+1)
    # Duel 4 (Draco) ranges from B(o-1) to F(o)
    # Duel 5 (Ralse) ranges from E(o) to B(o)
    
    singer_Options = []
    try:
        with open(os.path.join('custom','opera.txt')) as f:
            for line in f.readlines():
                singer_Options.append([l.strip() for l in line.split('|')])
    except IOError:
        print("WARNING: failed to load opera config")
        return
        
    singer_Options = [OperaSinger(*s) for s in singer_Options]
    
    #categorize by voice sample
    voices = {}
    for s in singer_Options:
        if s.sample in voices:
            voices[s.sample].append(s)
        else:
            voices[s.sample] = [s]
    
    #find a set of voices that doesn't overflow SPC RAM
    sample_sizes = {}
    while True:
        vchoices = random.sample(list(voices.values()), 3)
        for c in vchoices:
            smp = c[0].sample
            if smp not in sample_sizes:
                sample_sizes[smp] = find_sample_size(data, smp)
        sample_total_size = sum([sample_sizes[c[0].sample] for c in vchoices])
        if sample_total_size <= SAMPLE_MAX_SIZE:
            break

    #select characters
    charpool = []
    char = {}
    #by voice, for singers
    for v in vchoices:
        charpool.append(random.choice(v))
    random.shuffle(charpool)
    for c in ["Maria", "Draco", "Ralse"]:
        char[c] = charpool.pop()
    #by sprite/name, for impresario
    charpool = [c for c in singer_Options if c not in char.values()]
    char["Impresario"] = random.choice(charpool)
    
    #reassign sprites in npc data
    locations = get_locations()
    #first, free up space for a unique Ralse
    #choose which other NPCs get merged:
    # 0. id for new scholar, 1. offset for new scholar, 2. id for merged sprite, 3. offset for merged sprite, 4. spritesheet filename, 5. extra pose type
    merge_Options = [
        (32, 0x172C00, 33, 0x1731C0, "dancer.bin", "flirt"), #fancy gau -> dancer
        (32, 0x172C00, 35, 0x173D40, "gau-fancy.bin", "sideeye"), #clyde -> fancy gau
        (60, 0x17C4C0, 35, 0x173D40, "daryl.bin", "sideeye"), #clyde -> daryl
        (42, 0x176580, 35, 0x173D40, "katarin.bin", "sideeye"), #clyde -> katarin
        (60, 0x17C4C0, 42, 0x176580, "daryl.bin", "sideeye"), #katarin -> daryl
        (60, 0x17C4C0, 42, 0x176580, "katarin.bin", "sideeye"), #daryl -> katarin
        (60, 0x17C4C0, 41, 0x175FC0, "daryl.bin", "sleeping"), #rachel -> daryl
        (60, 0x17C4C0, 41, 0x175FC0, "rachel.bin", "sleeping"), #daryl -> rachel
        (60, 0x17C4C0, 30, 0x172080, "returner.bin", "prone"), #daryl -> returner
        (53, 0x17A1C0, 59, 0x17BFC0, "figaroguard.bin", None), #conductor -> figaro guard
        (45, 0x1776C0, 48, 0x178800, "maduin.bin", "prone"), #yura -> maduin
        ]
    merge = random.choice(merge_Options)
    
    #merge sacrifice into new slot
    replace_npc(locations, (merge[0], None), merge[2])
    #move scholar into sacrifice slot
    for i in [0,1,3,4,5]:
        replace_npc(locations, (27, i), (merge[0], i))
    
    #randomize palettes of shuffled characters
    for i in [0x1A, 0x1B, 0x1C, 0x2B]:
        palette = random.randint(0,5)
        for l in locations:
            for npc in l.npcs:
                if npc.graphics == i:
                    #npc.palette = palette
                    pass
    
    #debug info
    # for l in locations:
        # for npc in l.npcs:
            # if npc.graphics in [118,138]:
                # print()
                # print(f"graphics {npc.graphics} found at ${npc.pointer:X}, in location 0x{l.locid:X}")
                # print(f"palette {npc.palette}, facing byte {npc.facing:X}")
                # print(f"facing {npc.facing & 3:X}, change {npc.facing>>2 & 1:X}")
                # print(f"bglayer {npc.facing>>3 & 3:X}, unknown1 {npc.facing>>5 & 1:X}")
                # print(f"mirror {npc.facing>>6 & 2:X}, unknown2 {npc.facing>>7 & 1:X}")
                
    #randomize item thrown off balcony
    balcony = get_location(0xEC)
    for npc in balcony.npcs:
        if npc.graphics == 88:
            item = random.choice([
                #(84, 0x24, "chest"), #treasure box (palette broken)
                (87, 0x44, "statue"),
                (88, 0x54, "flowers"), #bouquet
                (89, 0x54, "letter"), #letter
                (91, 0x54, "magicite"), #magicite
                (92, 0x44, "book"), #book
                ##DO NOT THROW THE BABY
                (96, 0x44, "crown"), #slave crown
                (97, 0x54, "weight"), #4ton weight
                (100, 0x54, "bandana"), #locke's bandana
                ##(124, 0x02, "helmet") #a shiny thing (didn't work)
                ])
            npc.graphics = item[0]
            npc.palette = random.choice(range(6))
            npc.facing = item[1]
            set_dialogue_var("OperaItem", item[2])
            #print(f"opera item is {npc.graphics}, palette {npc.palette} ({item[2]})")
            #print(f"at address {npc.pointer:X}")
    #4 ton weight
    for npc in get_location(0xEB).npcs:
        if npc.graphics == 97:
            item = random.choice([
                (58, 0x11), #fish (????)
                (87, 0x44), #mini statue
                (93, 0x54), #ultros is allowed to try to throw the baby (STOP HIM)
                (97, 0x54), #4ton weight
                (112, 0x43), #fire
                ###(118, 0x10), #rock (didn't work)
                ###(138, 0x12) #leo's sword (didn't work)
                ])
            npc.graphics = item[0]
            npc.palette = random.choice(range(6))
            npc.facing = item[1]
            #print(f"ultros item is {npc.graphics}, palette {npc.palette}")
            #print(f"at address {npc.pointer:X}")

    #set up some spritesheet locations
    pose = {
        'singing': [0x66, 0x67, 0x68, 0x69, 0x64, 0x65, 0x60, 0x61, 0x62, 0x63],
        'ready': list(range(0x3E, 0x44)),
        'prone': list(range(0x51, 0x57)),
        'angry': list(range(0x76, 0x7C)),
        'flirt': [0xA3, 0xA4, 0x9C, 0x99, 0x9A, 0x9B],
        'sideeye': [0x92, 0x93, 0x94, 0x95, 0x08, 0x09],
        'sleeping': [0x86, 0x87, 0x88, 0x89, 0x08, 0x09]
            }
    
    opath = os.path.join("custom","opera")
    #load scholar graphics
    try:
        with open(os.path.join(opath, "ralse.bin"),"rb") as f:
            sprite = f.read()
    except IOError:
        print(f"failed to open custom/opera/ralse.bin")
        sprite = None
    if sprite:
        new_sprite = create_sprite(sprite)
        data = byte_insert(data, merge[1], new_sprite)
        
    #load new graphics into merged slot
    try:
        with open(os.path.join(opath, f"{merge[4]}"),"rb") as f:
            sprite = f.read()
    except IOError:
        try:
            with open(os.path.join("custom","sprites", f"{merge[4]}"),"rb") as f:
                sprite = f.read()
        except:
            print(f"failed to open custom/opera/{merge[4]} or custom/sprites/{merge[4]}")
            sprite = None
    if sprite:
        #print(f"merge {merge}, pose {pose}")
        new_sprite = create_sprite(sprite, pose[merge[5]] if merge[5] is not None else [])
        data = byte_insert(data, merge[3], new_sprite)
    
    
    #load new graphics into opera characters
    char_offsets = {
        "Maria": (0x1705C0, pose['ready'] + pose['singing']),
        "Draco": (0x1713C0, pose['prone'] + pose['singing']),
        "Ralse": (0x170CC0, pose['prone'] + pose['singing']),
        "Impresario": (0x176B40, pose['angry'])}
    for cname, c in char.items():
        #print(f"{cname} -> {c.name}")
        try:
            with open(os.path.join(opath, f"{c.sprite}.bin"),"rb") as f:
                sprite = f.read()
        except IOError:
            try:
                with open(os.path.join("custom","sprites", f"{c.sprite}.bin"),"rb") as f:
                    sprite = f.read()
            except:
                print(f"failed to open custom/opera/{c.sprite}.bin or custom/sprites/{c.sprite}.bin")
                continue
        offset, extra_tiles = char_offsets[cname]
        #tiles = list(range(0x28)) + extra_tiles
        #new_sprite = bytearray()
        #for t in tiles:
        #    loc = t*32
        #    new_sprite.extend(sprite[loc:loc+32])
        #data = byte_insert(data, offset, new_sprite)
        new_sprite = create_sprite(sprite, extra_tiles)
        data = byte_insert(data, offset, new_sprite)
        
    ### adjust script
    
    load_patch_file("opera")
    factions = [
        ("the East", "the West"),
        ("the North", "the South"),
        ("the Rebels", "the Empire"),
        ("the Alliance", "the Horde"),
        ("the Sharks", "the Jets"),
        ("the Fire Nation", "the Air Nation"),
        ("the Sith", "the Jedi"),
        ("the X-Men", "the Sentinels"),
        ("the X-Men", "the Inhumans"),
        ("the Kree", "the Skrulls"),
        ("the jocks", "the nerds"),
        ("Palamecia", "the Wild Rose"),
        ("Baron", "Mysidia"),
        ("Baron", "Damcyan"),
        ("Baron", "Fabul"),
        ("AVALANCHE", "Shinra"),
        ("Shinra", "Wutai"),
        ("Balamb", "Galbadia"),
        ("Galbadia", "Esthar"),
        ("Alexandria", "Burmecia"),
        ("Alexandria", "Lindblum"),
        ("Zanarkand", "Bevelle"),
        ("the Aurochs", "the Goers"),
        ("Yevon", "the Al Bhed"),
        ("the Gullwings", "the Syndicate"),
        ("New Yevon", "the Youth League"),
        ("Dalmasca", "Archadia"),
        ("Dalmasca", "Rozarria"),
        ("Cocoon", "Pulse"),
        ("Lucis", "Niflheim"),
        ("Altena", "Forcena"),
        ("Nevarre", "Rolante"),
        ("Wendel", "Ferolia"),
        ("the Lannisters", "the Starks"),
        ("the Hatfields", "the McCoys"),
        ("the Aliens", "the Predators"),
        ("cats", "dogs"),
        ("YoRHa", "the machines"),
        ("Shevat", "Solaris"),
        ("U-TIC", "Kukai"),
        ("the Bionis", "the Mechonis"),
        ("Samaar", "the Ghosts"),
        ("Mor Ardain", "Uraya"),
        ("Marvel", "Capcom"),
        ("Nintendo", "Sega"),
        ("Subs", "Dubs"),
        ("vampires", "werewolves"),
        ("Guardia", "the Mystics"),
        ("the Ascians", "the Scions"),
        ("Garlemald", "Eorzea"),
        ("Garlemald", "Ala Mhigo"),
        ("Garlemald", "Doma"),
        ("Ul'dah", "Sil'dih"),
        ("Amdapor", "Mhach"),
        ("Amdapor", "Nym"),
        ("Nym", "Mhach"),
        ("Ishgard", "Dravania"),
        ("the Oronir", "the Dotharl"),
        ("Allag", "Meracydia")
        ]
    factions = random.choice(factions)
    if random.choice([False, True]):
        factions = (factions[1], factions[0])
    set_dialogue_var("OperaEast", factions[0])
    set_dialogue_var("OperaWest", factions[1])
        
    set_dialogue_var("maria", char['Maria'].name)
    set_dialogue_var("draco", char['Draco'].name)
    set_dialogue_var("ralse", char['Ralse'].name)
    set_dialogue_var("impresario", char['Impresario'].name)
    set_dialogue_var("mariatitle", char['Maria'].title)
    set_dialogue_var("dracotitle", char['Draco'].title)
    set_dialogue_var("ralsetitle", char['Ralse'].title)
    set_dialogue_var("impresariotitle", char['Impresario'].title)
    char['Maria'].gender = set_pronoun('Maria', char['Maria'].gender)
    char['Draco'].gender = set_pronoun('Draco', char['Draco'].gender)
    char['Ralse'].gender = set_pronoun('Ralse', char['Ralse'].gender)
    char['Impresario'].gender = set_pronoun('Impresario', char['Impresario'].gender)
    
    #due to the variance in power relations connoted by "make X my queen" and "make X my king", this line will be altered in all variations so that it means roughly the same thing no matter the Maria replacement's gender
    
    if char['Maria'].gender == "female":
        set_dialogue_var("MariaTheGirl", "the girl")
        set_dialogue_var("MariaQueenBad", "mine")
        set_dialogue_var("MariaQueen", "queen")
        set_dialogue_var("MariaWife", "wife")
    elif char['Maria'].gender == "male":
        set_dialogue_var("MariaTheGirl", "the guy")
        set_dialogue_var("MariaQueenBad", "mine")
        set_dialogue_var("MariaQueen", "king")
        set_dialogue_var("MariaWife", "husband")
    elif char['Maria'].gender == "object":
        set_dialogue_var("MariaTheGirl", char['Maria'].title + " " + char['Maria'].name)
        set_dialogue_var("MariaQueenBad", "mine")
        set_dialogue_var("MariaQueen", "prize")
        set_dialogue_var("MariaWife", "collection")
    else:
        set_dialogue_var("MariaTheGirl", "the girl")
        set_dialogue_var("MariaQueenBad", "mine")
        set_dialogue_var("MariaQueen", "consort")
        set_dialogue_var("MariaWife", "partner")
    
    if char['Impresario'].gender == "male":
        set_dialogue_var("ImpresarioMan", "man") # from "music man"
    elif char['Impresario'].gender == "female":
        set_dialogue_var("ImpresarioMan", "madam")
    elif char['Impresario'].gender == "object":
        set_dialogue_var("ImpresarioMan", "machine")
    else:
        set_dialogue_var("ImpresarioMan", "maker")
        
    ### adjust music
    opera = {}
    try:
        overture = read_opera_mml('overture')
        overture += f"\n#WAVE 0x2B 0x{char['Draco'].sample:02X}\n"
        overture += f"\n#def draco= |B o{char['Draco'].octave[0]} v{char['Draco'].volume} {char['Draco'].init}\n"
        seg = read_opera_mml(f"{char['Draco'].file}_overture")
        overture += seg
        
        aria = read_opera_mml('aria')
        aria += f"\n#WAVE 0x2A 0x{char['Maria'].sample:02X}\n"
        aria += f"\n#def maria= |A o{char['Maria'].octave[1]} v{char['Maria'].volume} {char['Maria'].init}\n"
        seg = read_opera_mml(f"{char['Maria'].file}_aria")
        aria += seg
        
        duel = read_opera_mml('duel')
        duel += f"\n#WAVE 0x2A 0x{char['Maria'].sample:02X}\n"
        duel += f"\n#def maria= |A o{char['Maria'].octave[3]} v{char['Maria'].volume} {char['Maria'].init}\n"
        duel += f"\n#WAVE 0x2B 0x{char['Draco'].sample:02X}\n"
        duel += f"\n#def draco= |B o{char['Draco'].octave[2]} v{char['Draco'].volume} {char['Draco'].init}\n"
        duel += f"\n#def draco2= |B o{char['Draco'].octave[5]} v{char['Draco'].volume} {char['Draco'].init}\n"
        duel += f"\n#WAVE 0x2C 0x{char['Ralse'].sample:02X}\n"
        duel += f"\n#def ralse= |C o{char['Ralse'].octave[4]} v{char['Ralse'].volume} {char['Ralse'].init}\n"
        duel += f"\n#def ralse2= |C o{char['Ralse'].octave[6]} v{char['Ralse'].volume} {char['Ralse'].init}\n"
        duelists = ["Draco", "Maria", "Ralse", "Draco", "Ralse"]
        for i in range(5):
            seg = read_opera_mml(f"{char[duelists[i]].file}_duel{i+1}")
            duel += seg
        
        #print(overture)
        #print("########")
        #print(duel)
        #print("########")
        #print(aria)
        
        opera['overture'] = mml_to_akao(overture)['_default_']
        opera['duel'] = mml_to_akao(duel)['_default_']
        opera['aria'] = mml_to_akao(aria)['_default_']
        
    except IOError:
        print("opera music generation failed, reverting to default")
        affect_music = False
    
    fout.seek(0)
    fout.write(data)
    
    return opera if affect_music else None
    
def find_sample_size(data, sidx):
    table = 0x53C5F
    offset = bytes_to_int(data[table+sidx*3:table+sidx*3+3]) - 0xC00000 + 2
    loc = 0
    
    #scan BRR block headers until one has END bit set
    while not (data[offset+loc*9] & 1):
        loc += 1
    
    return (loc+1)*9
    
def replace_npc(locations, old, new):
    if old[1] is not None: #if a palette is specified,
        for l in locations:
            for n in l.npcs:
                if n.graphics == old[0] and n.palette == old[1]:
                    n.graphics = new[0]
                    n.palette = new[1]
    else:
        for l in locations:
            for n in l.npcs:
                if n.graphics == old[0]:
                    try:
                        n.graphics = new[0]
                    except TypeError:
                        n.graphics = new
    
def create_sprite(sprite, extra_tiles=None):
    tiles = list(range(0x28)) + (extra_tiles if extra_tiles else [])
    new_sprite = bytearray()
    for t in tiles:
        loc = t*32
        new_sprite.extend(sprite[loc:loc+32])
    return new_sprite
    
def read_opera_mml(file):
    try:
        file = os.path.join('custom','opera',f'{file}.mml')
        with open(file, "r") as f:
            mml = f.read()
        return mml
    except IOError:
        print(f"Failed to read {file}")
        raise
    