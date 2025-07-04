from io import BytesIO
from character import get_characters, get_character
from esperrandomizer import get_espers
from formationrandomizer import (REPLACE_FORMATIONS, NOREPLACE_FORMATIONS, get_formations, get_fsets,
                                 get_formation, get_fset)
from itemrandomizer import get_item
from locationrandomizer import get_locations, get_location, get_npcs
from monsterrandomizer import REPLACE_ENEMIES, get_monsters
from shoprandomizer import get_shops
from towerrandomizer import randomize_tower
from utils import name_to_bytes, read_multi, Substitution, utilrandom as random, write_multi, AutoLearnRageSub


def get_npc_palettes():
    palettes = {}
    for n in get_npcs():
        g = n.graphics
        if g not in palettes:
            palettes[g] = set([])
        palettes[g].add(n.palette)
    for k, v in list(palettes.items()):
        palettes[k] = sorted(v)
    return palettes


def manage_map_names(outfile_rom_buffer: BytesIO):
    outfile_rom_buffer.seek(0xEF101)
    text = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789")
    text = dict([(c, i + 0x20) for (i, c) in enumerate(text)])
    text[" "] = 0x7F
    pointers = {}
    for i in range(1, 101):
        pointers[i] = outfile_rom_buffer.tell()
        room_name = "Room %s" % i
        room_name = bytes([text[c] for c in room_name]) + b'\x00'
        outfile_rom_buffer.write(room_name)
        #fout.write(chr(0))

    for i in range(1, 101):
        outfile_rom_buffer.seek(0x268400 + (2 * i))
        pointer = pointers[i] - 0xEF100
        write_multi(outfile_rom_buffer, pointer, length=2)


def manage_ancient(Options_, outfile_rom_buffer: BytesIO, infile_rom_buffer: BytesIO,
                   form_music_overrides=None, randlog=None, shadowstays=False, noenc=False):
    if not form_music_overrides:
        form_music_overrides = {}

    change_battle_commands = [41, 42, 43]
    if not Options_.is_flag_active("shuffle_commands"):
        alrs = AutoLearnRageSub(require_gau=True)
        alrs.set_location(0x23b73)
        alrs.write(outfile_rom_buffer)

        enable_morph_sub = Substitution()
        enable_morph_sub.bytestring = bytes([0xEA] * 2)
        enable_morph_sub.set_location(0x25410)
        enable_morph_sub.write(outfile_rom_buffer, patch_name='enable_morph')

        enable_mpoint_sub = Substitution()
        enable_mpoint_sub.bytestring = bytes([0xEA] * 2)
        enable_mpoint_sub.set_location(0x25E38)
        enable_mpoint_sub.write(outfile_rom_buffer, patch_name='enable_mpoint')

        change_battle_commands += list(range(18, 28))

    moogle_commands = [0x03, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b,
                       0x0d, 0x0e, 0x0f, 0x10, 0x12, 0x13, 0x16, 0x18,
                       0x1a, 0x1b, 0x1d]
    for i in change_battle_commands:
        commands = random.sample(moogle_commands, 2)
        c = get_character(i)
        c.battle_commands = [0x00, commands[0], commands[1], 0x01]
        c.write_battle_commands(outfile_rom_buffer)

    for i in [32, 33]:
        c = get_character(i)
        c.battle_commands = [0x00, 0x1D, 0xFF, 0x01]
        c.write_battle_commands(outfile_rom_buffer)

    characters = get_characters()
    gau = [c for c in characters if c.id == 11][0]
    if not Options_.is_flag_active("replace_commands") and gau.battle_commands[1] in [0x11, None]:
        gau.battle_commands[1] = 0xFF
        gau.write_battle_commands(outfile_rom_buffer)

    to_dummy = [get_item(0xF6), get_item(0xF7)]
    dummy_names = ["Pebble", "Tissue"]
    for dummy_name, item in zip(dummy_names, to_dummy):
        name = bytes([0xFF]) + name_to_bytes(dummy_name, 12)
        item.dataname = name
        item.price = 4
        item.itemtype = 6
        item.write_stats(outfile_rom_buffer)
    blank_sub = Substitution()
    blank_sub.set_location(0x2D76C1)
    blank_sub.bytestring = bytearray([0xFF] * (0x2D76F5 - blank_sub.location))
    blank_sub.bytestring[blank_sub.size//2] = 0
    blank_sub.write(outfile_rom_buffer, patch_name='blank_items')

    goddess_save_sub = Substitution()
    goddess_save_sub.bytestring = bytes([0xFD, 0xFD])
    goddess_save_sub.set_location(0xC170A)
    goddess_save_sub.write(outfile_rom_buffer, patch_name='goddess_save')
    goddess_save_sub.set_location(0xC1743)
    goddess_save_sub.write(outfile_rom_buffer, patch_name='goddess_save')
    goddess_save_sub.set_location(0xC1866)
    goddess_save_sub.write(outfile_rom_buffer, patch_name='goddess_save')

    # decrease exp needed for level up
    if Options_.is_flag_active('racecave'):
        maxlevel = 49
        divisor = 12.0
    elif Options_.is_flag_active('speedcave'):
        maxlevel = 49
        divisor = 8.0
    else:
        maxlevel = 49
        divisor = 2.0

    for level in range(maxlevel):
        ratio = (float(level) / maxlevel)**2
        ratio = min(ratio, 1.0)
        xptr = 0x2d8220 + (level*2)
        outfile_rom_buffer.seek(xptr)
        exp = read_multi(outfile_rom_buffer, length=2)
        newexp = (exp / divisor)
        remaining = exp - newexp
        newexp = int(round(newexp + (ratio*remaining)))
        newexp = max(newexp, 1)
        outfile_rom_buffer.seek(xptr)
        write_multi(outfile_rom_buffer, newexp, length=2)

    startsub = Substitution()
    startsub.bytestring = bytearray([
        0xD7, 0xF3,  # remove Daryl
        0xD5, 0xF0,  # remove Terra from party
        0xD5, 0xE0,  # remove Terra from party
        0xDC, 0x7E,  # fix ending? $1F4F bit 6
        0xB8, 0x43,  # show magic points after battle
        0x3F, 0x0E, 0x00,
        0x3F, 0x0F, 0x00,
    ])
    if Options_.is_flag_active('racecave'):
        num_starting = 9 + random.randint(0, 2) + random.randint(0, 1)
    elif Options_.is_flag_active('speedcave'):
        num_starting = 4 + random.randint(0, 3) + random.randint(0, 2)
    else:
        num_starting = 4 + random.randint(0, 1) + random.randint(0, 1)
    starting = random.sample(list(range(14)), num_starting)
    for c in starting:
        startsub.bytestring += bytearray([0xD4, 0xF0 | c])
        startsub.bytestring += bytearray([0xD4, 0xE0 | c])

    for c in characters:
        i = c.id
        cptr = 0x2d7ca0 + 0x15 + (i*22)
        outfile_rom_buffer.flush()
        outfile_rom_buffer.seek(cptr)
        level = ord(outfile_rom_buffer.read(1))
        level &= 0xF3
        if i >= 14 or Options_.is_flag_active("speedcave") and i not in starting:
            level |= 0b1000
        outfile_rom_buffer.seek(cptr)
        outfile_rom_buffer.write(bytes([level]))
    outfile_rom_buffer.seek(0xa5e74)
    outfile_rom_buffer.write(b'\x00')  # remove Terra's magitek

    tempcands = [14, 15, random.choice(list(range(18, 28))), random.choice([32, 33])]
    if Options_.is_flag_active('speedcave'):
        tempcands.append(random.choice([16, 17]))
        tempcands.append(random.choice([41, 42, 43]))
    charcands = list(range(14)) + random.sample(tempcands, 2)
    chargraphics = {14: 0x11, 15: 0x10, 16: 0x14, 17: 0x14, 32: 0xE, 33: 0xE,
                    41: 0x15, 42: 0x15, 43: 0x15}
    for c in range(14):
        chargraphics[c] = c
    for c in range(18, 28):
        chargraphics[c] = 0xA
    for npc, i in enumerate(charcands):
        c = [x for x in characters if x.id == i][0]
        if i in chargraphics:
            g = chargraphics[i]
        else:
            g = i
        startsub.bytestring.extend([0x7F, npc, i,
                                    0x37, npc, g,
                                    0x43, npc, c.palette,
                                    0x40, npc, i])
        c.slotid = npc

    runaway = random.choice([c for c in characters if hasattr(c, "slotid")
                             and c.id == c.slotid]).slotid

    if not shadowstays:

        if runaway in starting:
            byte, bit = runaway // 8, runaway % 8
            mem_addr = ((0x1b+byte) << 3) | bit
            startsub.bytestring += bytearray([0xD7, mem_addr])
        shadow_leaving_sub = Substitution()
        shadow_leaving_sub.set_location(0x248A6)
        shadow_leaving_sub.bytestring = bytearray([
            0x1C, 0xDE + (runaway//8), 0x1E,     # TRB $1ede
            0x20, 0xE3, 0x47,
            0xAD, 0xFB + (runaway//8), 0x1E,     # LDA $1efb
            0x09, 1 << (runaway % 8),           # ORA #$08
            0x8D, 0xFB + (runaway//8), 0x1E,     # STA $1efb
            0xAD, 0xDE + (runaway//8), 0x1E,     # LDA $1ede
            0x29, 0xFF ^ (1 << (runaway % 8)),  # AND #$F7
            0x8D, 0xDE + (runaway//8), 0x1E,     # STA $1ede
            ])
        while len(shadow_leaving_sub.bytestring) < 23:
            shadow_leaving_sub.bytestring.append(0xEA)
        shadow_leaving_sub.bytestring += bytearray([0xA9, 0xFE,
                                                    0x20, 0x92, 0x07])
        shadow_leaving_sub.write(outfile_rom_buffer, patch_name='ancient_shadow_leaving')
        shadow_leaving_sub.set_location(0x24861)
        shadow_leaving_sub.bytestring = bytearray([
            0xAE, runaway, 0x30,
            0x30, 0x26,
            0x20, 0x5A, 0x4B,
            0xC9, random.choice([0x20, 0x10, 0x8, 0x4, 0x2, 0x1]),
            0xB0, 0x1F,
            0xAD, 0x1F, 0x20,
            0xD0, 0x1A,
            0xAD, 0x76, 0x3A,
            0xC9, 0x02,
            0x90, 0x13,
            0xBD, 0xE4, 0x3E,
            0x89, 0xC2,
            0xD0, 0x0C,
            0xA9, 1 << (runaway % 8),
            0x2C, 0xBD + (runaway//8), 0x3E,
            0xD0, 0x05,
            0x2C, 0xDE + (runaway//8), 0x1E,
            ])
        shadow_leaving_sub.write(outfile_rom_buffer, patch_name='ancient_shadow_leaving')
        shadow_leaving_sub.set_location(0x10A851)
        shadow_leaving_sub.bytestring = bytearray([
            0x0E, 0x03, runaway, 0x6A, 0xA8, 0x0F,
            0x11,
            0x01, 0xFB,
            0x0E, 0x03, runaway, 0x7E, 0xA8, 0x0F,
            0x01, 0xFC,
            0x0E, 0x03, runaway, 0x92, 0xA8, 0x0F,
            0x10, 0xFF,
            ])
        shadow_leaving_sub.write(outfile_rom_buffer, patch_name='ancient_shadow_leaving')
        shadow_leaving_sub.bytestring = bytearray([runaway])
        shadow_leaving_sub.set_location(0x10FC2F)
        shadow_leaving_sub.write(outfile_rom_buffer, patch_name='ancient_shadow_leaving')
        shadow_leaving_sub.set_location(0x10FC5D)
        shadow_leaving_sub.write(outfile_rom_buffer, patch_name='ancient_shadow_leaving')

    esperevents = [
        "Ramuh", "Ifrit", "Shiva", "Siren", "Terrato", "Shoat", "Maduin",
        "Bismark", "Stray", "Palidor", "Tritoch", "Odin", "Raiden", "Bahamut",
        "Alexandr", "Crusader", "Ragnarok", "Kirin", "ZoneSeek", "Carbunkl",
        "Phantom", "Sraphim", "Golem", "Unicorn", "Fenrir", "Starlet",
        "Phoenix"]
    esperevents = dict([(npc, i) for (i, npc) in enumerate(esperevents)])
    espers = list(get_espers(infile_rom_buffer))
    num_espers = 3
    for i in range(num_espers):
        if Options_.is_flag_active("speedcave"):
            esperrank = 999
        else:
            esperrank = 0
            while random.randint(1, 3) == 3:
                esperrank += 1
        candidates = [e for e in espers if e.rank <= esperrank]
        esper = random.choice(candidates)
        espers.remove(esper)
        event_value = esperevents[esper.name] + 0x36
        startsub.bytestring += bytearray([0x86, event_value])
    for i in range(27):  # espers
        byte, bit = i // 8, i % 8
        mem_addr = ((0x17+byte) << 3) | bit
        startsub.bytestring += bytearray([0xD6, mem_addr])
    for i in range(16):  # characters
        if i in starting:
            continue
        byte, bit = i // 8, i % 8
        mem_addr = ((0x1b+byte) << 3) | bit
        startsub.bytestring += bytearray([0xD6, mem_addr])
    startsub.bytestring += bytearray([0xB2, 0x09, 0x21, 0x02,  # start on airship
                                     ])
    startsub.bytestring.append(0xFE)
    startsub.set_location(0xADD1E)
    startsub.write(outfile_rom_buffer, patch_name='ancient_start_location')

    startsub0 = Substitution()
    startsub0.bytestring = bytearray([0xB2, 0x1E, 0xDD, 0x00, 0xFE])
    startsub0.set_location(0xC9A4F)
    startsub0.write(outfile_rom_buffer, patch_name='ancient_start_location')

    set_airship_sub = Substitution()
    set_airship_sub.bytestring = bytearray([0xB2, 0xD6, 0x02, 0x00,
                                            0xFE])
    set_airship_sub.set_location(0xAF53A)  # need first branch for button press
    set_airship_sub.write(outfile_rom_buffer, patch_name='ancient_start_location')

    tower_msg_sub = Substitution()
    tower_msg_sub.bytestring = bytearray([0xD6, 0xE6, 0xD6, 0xE7])  # reset temp chars
    while len(tower_msg_sub.bytestring) < 12:
        tower_msg_sub.bytestring.append(0xFD)
    tower_msg_sub.set_location(0xA03A7)
    tower_msg_sub.write(outfile_rom_buffer, patch_name='ancient_tower_message')

    from locationrandomizer import NPCBlock, EventBlock
    falcon = get_location(0xb)
    save_point = NPCBlock(pointer=None, locid=falcon.locid)
    attributes = {
        "graphics": 0x6f, "palette": 6, "x": 20, "y": 8,
        "show_on_vehicle": False, "speed":  0,
        "event_addr": 0x5eb3, "facing": 3,
        "no_turn_when_speaking": False, "layer_priority": 0,
        "special_anim": 2,
        "memaddr": 0, "membit": 0, "bg2_scroll": 0,
        "move_type": 0, "sprite_priority": 1, "vehicle": 0}
    for key, value in attributes.items():
        setattr(save_point, key, value)
    save_point.set_id(len(falcon.npcs))
    falcon.npcs.append(save_point)
    save_event = EventBlock(pointer=None, locid=falcon.locid)
    attributes = {"event_addr": 0x29aeb, "x": 20, "y": 8}
    for key, value in attributes.items():
        setattr(save_event, key, value)
    falcon.events.append(save_event)
    partyswitch = NPCBlock(pointer=None, locid=falcon.locid)
    attributes = {
        "graphics": 0x17, "palette": 0, "x": 16, "y": 6,
        "show_on_vehicle": False, "speed":  0,
        "event_addr": 0x047d, "facing": 2,
        "no_turn_when_speaking": False, "layer_priority": 0,
        "special_anim": 0,
        "memaddr": 0, "membit": 0, "bg2_scroll": 0,
        "move_type": 0, "sprite_priority": 0, "vehicle": 0, "npcid": 2}
    for key, value in attributes.items():
        setattr(partyswitch, key, value)
    falcon.npcs.append(partyswitch)

    pilot = random.choice([s for s in starting if s < 12])
    pilot_sub = Substitution()
    pilot_sub.bytestring = bytearray([
        0x3D, pilot, 0x45,
        0x3F, pilot, 0x01])
    for i in range(14):
        if i == pilot:
            continue
        pilot_sub.bytestring += bytearray([0x3F, i, 0x00])
    pilot_sub.set_location(0xC2110)
    pilot_sub.write(outfile_rom_buffer, patch_name='ancient_pilot_sub')

    if Options_.is_flag_active("racecave"):
        randomize_tower(ancient=True, nummaps=50)
    elif Options_.is_flag_active("speedcave"):
        randomize_tower(ancient=True, nummaps=85)
    else:
        randomize_tower(ancient=True, nummaps=300)
    manage_map_names(outfile_rom_buffer)

    # remove event pointers so Ancient Cave doesn't overwrite and create some softlock exits

    fix_cave_sub = Substitution()
    fix_cave_sub.set_location(0x11FC73)  # Owzer's Mansion change to no event
    fix_cave_sub.bytestring = bytes([0xB3, 0x5E, 0x00])
    fix_cave_sub.write(outfile_rom_buffer, patch_name='ancient_fix_cave')

    fix_cave_sub = Substitution()
    fix_cave_sub.set_location(0x11FB89)  # Gau's Father change to no event
    fix_cave_sub.bytestring = bytes([0xB3, 0x5E, 0x00])
    fix_cave_sub.write(outfile_rom_buffer, patch_name='ancient_fix_cave')

    unused_enemies = [u for u in get_monsters() if u.id in REPLACE_ENEMIES]

    def safe_boss_validator(formation):
        if formation.is_fanatics:
            return False
        if set(formation.present_enemies) & set(unused_enemies):
            return False
        if formation.formid in NOREPLACE_FORMATIONS:
            return False
        if not (any([m.boss_death for m in formation.present_enemies]) or
                formation.get_music() in [1, 2, 5]):
            return False
        if formation.get_music() == 0:
            return False
        if formation.formid in [0x1b0, 0x1b3, 0x1d9, 0x1db, 0x1d7]:
            return False
        if formation.formid in [0x1a4, 0x1d4, 0x1d5, 0x1d6, 0x1e4,
                                0x1e2, 0x1ff, 0x1bd, 0x1be]:
            return False
        if (Options_.is_flag_active("racecave")
                and formation.formid in [0x162, 0x1c8, 0x1d3]):
            return False
        return True

    def challenge_battle_validator(formation):
        if not formation.present_enemies:
            return False
        if set(formation.present_enemies) & set(unused_enemies):
            return False
        if formation.formid in NOREPLACE_FORMATIONS:
            return False
        if formation.battle_event:
            return False
        if formation.formid in [0x1a4, 0x1ff, 0x1bd, 0x1d7, 0x200, 0x201,
                                0x23f]:
            return False
        if formation.get_music() == 0:
            if any([f for f in formations if f.formid != formation.formid
                    and set(f.enemy_ids) == set(formation.enemy_ids)
                    and f.get_music() != 0]):
                return False
        best_drop = formation.get_best_drop()
        if best_drop and (best_drop.price <= 2 or best_drop.price >= 30000 or Options_.is_flag_active("madworld")):
            return True
        return False

    formations = sorted(get_formations(), key=lambda f: f.rank())
    enemy_formations = [
        f for f in formations if f.is_fanatics or
        (f.present_enemies and not f.has_event and not f.has_boss)]
    enemy_formations = [f for f in enemy_formations if f.formid not in
                        REPLACE_FORMATIONS + NOREPLACE_FORMATIONS]
    boss_formations = [f for f in formations if safe_boss_validator(f)]
    used_formations = []

    challenges = sorted([f for f in formations
                         if challenge_battle_validator(f)],
                        key=lambda f: f.get_best_drop().rank())[-48:]
    challenges = sorted(random.sample(challenges, 24), key=lambda f: f.rank())
    challenges = [f.formid for f in challenges]
    challenges = {1: challenges[:6],
                  2: challenges[6:12],
                  3: challenges[12:18],
                  4: challenges[18:24]}
    ch_bgs = list(range(0x31)) + [0x36, 0x37]
    waters = [0xD, 0x1F, 0x23]
    snows = [0x12]
    ch_bgs = random.sample(ch_bgs, 10) + [random.choice(waters), snows[0]]
    random.shuffle(ch_bgs)

    for location in get_locations():
        if not hasattr(location, "ancient_rank"):
            location.entrance_set.entrances = []
            location.entrance_set.longentrances = []
            location.chests = []
            location.attacks = 0
            location.write_data(outfile_rom_buffer)

    pointer = 0xB4E35
    if Options_.is_flag_active('racecave'):
        candidates = [c for c in starting if c != runaway]
        leaders = random.sample(candidates, 3)
        subptr = pointer - 0xa0000
        leader_sub = Substitution()

        # makes switching impossible and makes row change instant
        # could freeze the game d+pad and A on same frame tho
        leader_sub.set_location(0x324b7)
        leader_sub.bytestring = bytes([0xEA, 0xEA, 0xEA])
        leader_sub.write(outfile_rom_buffer, patch_name='ancient_leader')
        leader_sub.set_location(0x32473)
        leader_sub.bytestring = bytes([0xEA, 0xEA])
        leader_sub.write(outfile_rom_buffer, patch_name='ancient_leader')

        leader_sub.set_location(0xa02da)
        leader_sub.bytestring = bytes([
            0xB2, subptr & 0xFF, (subptr >> 8) & 0xFF, subptr >> 16])
        leader_sub.write(outfile_rom_buffer, patch_name='ancient_leader')
        leader_sub.set_location(pointer)
        leader_sub.bytestring = bytearray([])
        locked = 0
        for i, c in enumerate(leaders):
            leader_sub.bytestring += bytearray([0x3F, c, i+1])
            locked |= (1 << c)
        for c in range(16):
            if c in leaders:
                continue
            leader_sub.bytestring += bytearray([0x3F, c, 0x00])
            leader_sub.bytestring += bytearray([0x3E, c])
        leader_sub.bytestring += bytearray([0x47,
                                            0xE1,
                                            0xB2, 0x0B, 0xC9, 0x00,
                                            0x45])
        for i, c in enumerate(leaders):
            leader_sub.bytestring += bytearray([0x3F, c, 0])
            leader_sub.bytestring += bytearray([0x3F, c, i+1])
        leader_sub.bytestring += bytearray([0x99, 0x03, locked & 0xFF, locked >> 8])
        for i in [14, 15]:
            byte, bit = i // 8, i % 8
            mem_addr = ((0x1b+byte) << 3) | bit
            leader_sub.bytestring += bytearray([0xD6, mem_addr])
        leader_sub.bytestring += bytearray([0x96, 0xFE])
        leader_sub.write(outfile_rom_buffer, patch_name='ancient_leader')
        pswitch_ptr = pointer - 0xa0000
        pointer += len(leader_sub.bytestring)

    espersubs = {}
    for esper, event_value in esperevents.items():
        byte, bit = event_value // 8, event_value % 8
        mem_addr = ((0x17+byte) << 3) | bit
        espersub = Substitution()
        espersub.set_location(pointer)
        espersub.bytestring = [0xF4, 0x8D,
                               0x86, event_value + 0x36,
                               0xD7, mem_addr,
                               0x3E, None, 0xFE]
        espersubs[esper] = espersub
        pointer += espersub.size

    inn_template = [0x4B, None, None,
                    0x4B, 0x11, 0x81,
                    0xB6, None, None, None,
                    None, None, None,
                    0xFE]
    inn_template2 = [0x85, None, None,
                     0xC0, 0xBE, 0x81, 0xFF, 0x69, 0x01,
                     0x31, 0x84, 0xC3, 0x8F, 0x84, 0xFF,
                     0xF4, 0x2C, 0x73, 0x30, 0x0E, 0x01, 0x02, 0x06, 0x16,
                     0x31, 0x86, 0xC3, 0x9C, 0x80, 0x8D, 0xCE, 0xFF,
                     0xB2, 0x67, 0xCF, 0x00,
                     0xF0, 0xB8, 0xFA,
                     0x31, 0x85, 0xD5, 0x36, 0x05, 0xCE, 0xFF,
                     0xB2, 0x96, 0xCF, 0x00,
                     0xFE]

    prices = {1: (500, 0xA6E),
              2: (2000, 0xA71),
              3: (8000, 0xA5F),
              4: (30000, 0xA64)}

    if Options_.is_flag_active("racecave"):
        partyswitch_template = [
            0x4B, None, None,
            0x4B, 0x86, 0x83,
            0xB6, None, None, None,
            None, None, None,
            0xFE]

        partyswitch_template2 = [
            0x85, None, None,
            0xC0, 0xBE, 0x81, 0xFF, 0x69, 0x01,
            0xB2,
            pswitch_ptr & 0xFF, (pswitch_ptr >> 8) & 0xFF, pswitch_ptr >> 16,
            0xFE]

    save_template = [0x4B, None, None,
                     0x4B, 0x24, 0x85,
                     0xB6, None, None, None,
                     None, None, None,
                     0xFE]
    save_template2 = [0x85, None, None,
                      0xC0, 0xBE, 0x81, 0xFF, 0x69, 0x01,
                      0xB2, 0xEB, 0x9A, 0x02,
                      0xFE]

    enemy_template = [0x4B, 0x0B, 0x07,
                      0xB6, None, None, None,
                      None, None, None,
                      0xA0, None, None, 0xB3, 0x5E, 0x70,
                      0x4D, None, None,
                      0xA1, 0x00,
                      0x96, 0x5C,
                      0xFE]

    def make_challenge_event(loc, ptr):
        bg = ch_bgs.pop()
        formids = random.sample(challenges[loc.restrank], 2)
        formations = [get_formation(formid) for formid in formids]
        for formid in formids:
            challenges[loc.restrank].remove(formid)
        setcands = [f for f in get_fsets() if f.setid >= 0x100 and f.unused]
        fset = setcands.pop()
        fset.formids = formids
        fset.write_data(outfile_rom_buffer)
        timer = max([e.stats['hp'] for f in formations
                     for e in f.present_enemies])
        reverse = False
        if timer >= 32768:
            reverse = True
            timer = 65535 - timer
        timer = max(timer, 3600)
        half = None
        while half is None or random.randint(1, 5) == 5:
            half = timer // 2
            timer = half + random.randint(0, half) + random.randint(0, half)
        if reverse:
            timer = 65535 - timer
        timer = int(round(timer / 1800.0))
        timer = max(2, min(timer, 36))
        timer = timer * 1800
        timer = [timer & 0xFF, timer >> 8]
        addr1 = ptr + 10 - 0xa0000
        addr2 = ptr + (len(enemy_template) - 1) - 0xa0000
        addr1 = [addr1 & 0xFF, (addr1 >> 8) & 0xFF, addr1 >> 16]
        addr2 = [addr2 & 0xFF, (addr2 >> 8) & 0xFF, addr2 >> 16]
        bytestring = list(enemy_template)
        bytestring[4:7] = addr1
        bytestring[7:10] = addr2
        bytestring[11:13] = timer
        bytestring[17] = fset.setid & 0xFF
        bytestring[18] = bg
        assert None not in bytestring
        sub = Substitution()
        sub.set_location(ptr)
        sub.bytestring = bytes(bytestring)
        sub.write(outfile_rom_buffer, patch_name='ancient_make_challenge_event')
        return ptr + len(enemy_template)

    shops = get_shops(infile_rom_buffer)
    shopranks = {}
    itemshops = [s for s in shops
                 if s.shoptype_pretty in ["items", "misc"]]
    othershops = [s for s in shops if s not in itemshops]
    othershops = othershops[random.randint(0, len(othershops)//2):]
    itemshops = sorted(random.sample(itemshops, 5), key=lambda p: p.rank())
    othershops = sorted(random.sample(othershops, 7),
                        key=lambda p: p.rank())
    for i in range(1, 5):
        if i > 1:
            shopranks[i] = othershops[:2] + itemshops[:1]
            othershops = othershops[2:]
            itemshops = itemshops[1:]
        else:
            shopranks[i] = othershops[:1] + itemshops[:2]
            othershops = othershops[1:]
            itemshops = itemshops[2:]
        assert len(shopranks[i]) == 3
        random.shuffle(shopranks[i])
    shopranks[random.randint(1, 4)][random.randint(0, 2)] = None

    levelmusic = {}
    dungeonmusics = [23, 24, 33, 35, 55, 71, 40, 41, 75, 77, 78]
    random.shuffle(dungeonmusics)
    for i in range(5):
        levelmusic[i] = dungeonmusics.pop()

    locations = [l for l in get_locations() if hasattr(l, "ancient_rank")]
    locations = sorted(locations, key=lambda l: l.ancient_rank)
    restlocs = [l for l in locations if hasattr(l, "restrank")]
    ban_musics = [0, 36, 56, 57, 58, 73, 74, 75] + list(levelmusic.values())
    restmusics = [m for m in range(1, 85) if m not in ban_musics]
    random.shuffle(restmusics)

    optional_chars = [c for c in characters if hasattr(c, "slotid")]
    optional_chars = [c for c in optional_chars if (c.slotid == runaway and c.id not in starting) or
                      (c.id not in starting and c.id in charcands)]
    if Options_.is_flag_active("speedcave"):
        while len(optional_chars) < 24:
            if random.choice([True, True, False]):
                supplement = [c for c in optional_chars if c.id >= 14 or
                              c.slotid == runaway]
            else:
                supplement = list(optional_chars)
            supplement = sorted(set(supplement), key=lambda c: c.id)
            optional_chars.append(random.choice(supplement))
    random.shuffle(optional_chars)

    ptr = pointer - 0xA0000
    c0, b0, a0 = ptr & 0xFF, (ptr >> 8) & 0xFF, ptr >> 16
    ptr = (pointer + 10) - 0xA0000
    c1, b1, a1 = ptr & 0xFF, (ptr >> 8) & 0xFF, ptr >> 16
    ptr = (pointer + 20) - 0xA0000
    c2, b2, a2 = ptr & 0xFF, (ptr >> 8) & 0xFF, ptr >> 16
    num_in_party_sub = Substitution()
    num_in_party_sub.set_location(0xAC654)
    num_in_party_sub.bytestring = [0xB2, c0, b0, a0]
    num_in_party_sub.write(outfile_rom_buffer, patch_name='ancient_starting_party_size')
    num_in_party_sub.set_location(pointer)
    num_in_party_sub.bytestring = bytes([
        0xC0, 0xAE, 0x01, c1, b1, a1,
        0xB2, 0x80, 0xC6, 0x00,
        0xC0, 0xAF, 0x01, c2, b2, a2,
        0xB2, 0x80, 0xC6, 0x00,
        0xD3, 0xA3,
        0xD3, 0xA2,
        0xFE
    ])
    num_in_party_sub.write(outfile_rom_buffer, patch_name='ancient_starting_party_size')
    pointer += len(num_in_party_sub.bytestring)
    ally_addrs = {}
    for chosen in set(optional_chars):
        byte, bit = chosen.slotid // 8, chosen.slotid % 8
        mem_addr = ((0x1b+byte) << 3) | bit
        allysub = Substitution()
        for party_id in range(1, 4):
            for npc_id in range(4, 6):
                allysub.set_location(pointer)
                allysub.bytestring = [0xB2, 0xC1, 0xC5, 0x00,  # set caseword
                                      0xC0, 0xA3, 0x81, None, None, None]
                allysub.bytestring += [0xD4, 0xF0 | chosen.slotid,
                                       0xD4, 0xE0 | chosen.slotid,
                                       0xD7, mem_addr]
                if chosen.id >= 14 or Options_.is_flag_active("speedcave"):
                    allysub.bytestring += [0x77, chosen.slotid,
                                           0x8b, chosen.slotid, 0x7F,
                                           0x8c, chosen.slotid, 0x7F,
                                           0x88, chosen.slotid, 0x00, 0x00]
                allysub.bytestring += [0x3E, 0x10 | npc_id,
                                       0x3D, chosen.slotid,
                                       0x3F, chosen.slotid, party_id,
                                       0x47,
                                       0x45,
                                       0xF4, 0xD0,
                                       0xFE]
                pointer = pointer + len(allysub.bytestring)
                uptr = (pointer - 1) - 0xa0000
                a, b, c = (uptr >> 16, (uptr >> 8) & 0xFF, uptr & 0xFF)
                allysub.bytestring[7:10] = [c, b, a]
                allysub.write(outfile_rom_buffer, patch_name='ancient_starting_party_members')
                event_addr = (allysub.location - 0xa0000) & 0x3FFFF
                ally_addrs[chosen.id, party_id, npc_id] = event_addr

    npc_palettes = get_npc_palettes()
    for g in npc_palettes:
        npc_palettes[g] = [v for v in npc_palettes[g] if 0 <= v <= 5]
    for g in range(14, 63):
        if g not in npc_palettes or not npc_palettes[g]:
            npc_palettes[g] = list(range(6))

    def make_paysub(template, template2, loc, ptr):
        sub = Substitution()
        sub.set_location(ptr)
        price, message = prices[loc.restrank]
        message |= 0x8000
        sub.bytestring = list(template)
        ptr += len(template)
        price = [price & 0xFF, price >> 8]
        message = [message & 0xFF, message >> 8]
        p = (ptr - 0xA0000) & 0x3FFFF
        p2 = p - 1
        ptrbytes = [p & 0xFF, (p >> 8) & 0xFF, p >> 16]
        ptrbytes2 = [p2 & 0xFF, (p2 >> 8) & 0xFF, p2 >> 16]
        mapid = [loc.locid & 0xFF, loc.locid >> 8]
        mapid[1] |= 0x23
        sub.bytestring[1:3] = message
        sub.bytestring[7:10] = ptrbytes
        sub.bytestring[10:13] = ptrbytes2
        assert None not in sub.bytestring
        assert len(sub.bytestring) == 14
        sub.bytestring += template2
        ptr += len(template2)
        sub.bytestring[15:17] = price
        assert None not in sub.bytestring
        sub.bytestring = bytes(sub.bytestring)
        sub.write(outfile_rom_buffer, patch_name='ancient_make_paysub')
        return sub

    rest_shops = []
    random.shuffle(restlocs)
    for location in restlocs:
        assert location.ancient_rank == 0
        location.music = restmusics.pop()
        location.make_warpable()

        innsub = make_paysub(inn_template, inn_template2, location, pointer)
        pointer += innsub.size
        savesub = make_paysub(save_template, save_template2, location, pointer)
        pointer += savesub.size
        if Options_.is_flag_active('racecave'):
            pswitch_sub = make_paysub(partyswitch_template,
                                      partyswitch_template2, location, pointer)
            pointer += pswitch_sub.size

        event_addr = (innsub.location - 0xa0000) & 0x3FFFF
        innkeeper = NPCBlock(pointer=None, locid=location.locid)
        graphics = random.randint(14, 62)
        palette = random.choice(npc_palettes[graphics])
        attributes = {
            "graphics": graphics, "palette": palette, "x": 52, "y": 16,
            "show_on_vehicle": False, "speed":  0,
            "event_addr": event_addr, "facing": 2,
            "no_turn_when_speaking": False, "layer_priority": 0,
            "special_anim": 0,
            "memaddr": 0, "membit": 0, "bg2_scroll": 0,
            "move_type": 0, "sprite_priority": 0, "vehicle": 0}
        for key, value in attributes.items():
            setattr(innkeeper, key, value)
        location.npcs.append(innkeeper)

        unequipper = NPCBlock(pointer=None, locid=location.locid)
        attributes = {
            "graphics": 0x1e, "palette": 3, "x": 49, "y": 16,
            "show_on_vehicle": False, "speed":  0,
            "event_addr": 0x23510, "facing": 2,
            "no_turn_when_speaking": False, "layer_priority": 0,
            "special_anim": 0,
            "memaddr": 0, "membit": 0, "bg2_scroll": 0,
            "move_type": 0, "sprite_priority": 0, "vehicle": 0}
        for key, value in attributes.items():
            setattr(unequipper, key, value)
        location.npcs.append(unequipper)

        event_addr = (savesub.location - 0xa0000) & 0x3FFFF
        pay_to_save = NPCBlock(pointer=None, locid=location.locid)
        attributes = {
            "graphics": 0x6f, "palette": 6, "x": 47, "y": 4,
            "show_on_vehicle": False, "speed":  0,
            "event_addr": event_addr, "facing": 3,
            "no_turn_when_speaking": False, "layer_priority": 0,
            "special_anim": 2,
            "memaddr": 0, "membit": 0, "bg2_scroll": 0,
            "move_type": 0, "sprite_priority": 0, "vehicle": 0}
        for key, value in attributes.items():
            setattr(pay_to_save, key, value)
        location.npcs.append(pay_to_save)

        if location.restrank == 4:
            final_loc = get_location(412)
            if len(final_loc.npcs) < 2:
                final_save = NPCBlock(pointer=None, locid=location.locid)
                attributes = {
                    "graphics": 0x6f, "palette": 6, "x": 82, "y": 43,
                    "show_on_vehicle": False, "speed":  0,
                    "event_addr": event_addr, "facing": 3,
                    "no_turn_when_speaking": False, "layer_priority": 0,
                    "special_anim": 2,
                    "memaddr": 0, "membit": 0, "bg2_scroll": 0,
                    "move_type": 0, "sprite_priority": 0, "vehicle": 0, "npcid": 1}
                for key, value in attributes.items():
                    setattr(final_save, key, value)
                final_loc.npcs.append(final_save)

        shop = shopranks[location.restrank].pop()
        if shop is not None:
            shop.name = "Rest stop " + str(location.restrank)
            rest_shops.append(shop)
            shopsub = Substitution()
            shopsub.set_location(pointer)
            shopsub.bytestring = bytes([0x9B, shop.shopid, 0xFE])
            shopsub.write(outfile_rom_buffer, patch_name='ancient_shopsub')
            pointer += len(shopsub.bytestring)
            event_addr = (shopsub.location - 0xa0000) & 0x3FFFF
        else:
            event_addr = 0x178cb
            colsub = Substitution()
            colsub.set_location(0xb78ea)
            colsub.bytestring = bytes([0x59, 0x04, 0x5C, 0xFE])
            colsub.write(outfile_rom_buffer, patch_name='ancient_colsub')
        shopkeeper = NPCBlock(pointer=None, locid=location.locid)
        graphics = random.randint(14, 62)
        palette = random.choice(npc_palettes[graphics])
        attributes = {
            "graphics": graphics, "palette": palette, "x": 39, "y": 11,
            "show_on_vehicle": False, "speed":  0,
            "event_addr": event_addr, "facing": 1,
            "no_turn_when_speaking": False, "layer_priority": 0,
            "special_anim": 0,
            "memaddr": 0, "membit": 0, "bg2_scroll": 0,
            "move_type": 0, "sprite_priority": 0, "vehicle": 0}
        for key, value in attributes.items():
            setattr(shopkeeper, key, value)
        location.npcs.append(shopkeeper)

        if optional_chars:
            chosen = optional_chars.pop()
            assert chosen.palette is not None
            if chosen.id >= 14 and False:
                byte, bit = 0, 0
            else:
                byte, bit = (chosen.slotid // 8) + 0x1b, chosen.slotid % 8
            event_addr = ally_addrs[chosen.id, location.party_id, len(location.npcs)]
            ally = NPCBlock(pointer=None, locid=location.locid)
            attributes = {
                "graphics": chargraphics[chosen.id],
                "palette": chosen.palette,
                "x": 54, "y": 18, "show_on_vehicle": False, "speed":  0,
                "event_addr": event_addr,
                "facing": 2, "no_turn_when_speaking": False, "layer_priority": 0,
                "special_anim": 0, "memaddr": byte, "membit": bit,
                "bg2_scroll": 0, "move_type": 0, "sprite_priority": 0, "vehicle": 0}
            for key, value in attributes.items():
                setattr(ally, key, value)
            location.npcs.append(ally)
            if (len(optional_chars) == 12 or (optional_chars and
                                              Options_.is_flag_active('speedcave'))):
                temp = optional_chars.pop()
                if chosen.id != temp.id:
                    chosen = temp
                    if chosen.id >= 14 and False:
                        byte, bit = 0, 0
                    else:
                        byte, bit = (chosen.slotid // 8) + 0x1b, chosen.slotid % 8
                    event_addr = ally_addrs[chosen.id, location.party_id, len(location.npcs)]
                    attributes = {
                        "graphics": chargraphics[chosen.id],
                        "palette": chosen.palette,
                        "x": 53, "y": 18, "show_on_vehicle": False, "speed":  0,
                        "event_addr": event_addr,
                        "facing": 2, "no_turn_when_speaking": False, "layer_priority": 0,
                        "special_anim": 0, "memaddr": byte, "membit": bit,
                        "bg2_scroll": 0, "move_type": 0, "sprite_priority": 0, "vehicle": 0}
                    ally = NPCBlock(pointer=None, locid=location.locid)
                    for key, value in attributes.items():
                        setattr(ally, key, value)
                    location.npcs.append(ally)

        if location.restrank == 1:
            num_espers = 3
        elif location.restrank in [2, 3]:
            num_espers = 2
        elif location.restrank == 4:
            num_espers = 1
        for i in range(num_espers):
            if not espers:
                break
            if Options_.is_flag_active('speedcave'):
                candidates = espers
            else:
                esperrank = location.restrank
                if random.randint(1, 7) == 7:
                    esperrank += 1
                candidates = []
                while not candidates:
                    candidates = [e for e in espers if e.rank == esperrank]
                    if not candidates or random.randint(1, 3) == 3:
                        candidates = [e for e in espers if e.rank <= esperrank]
                    if not candidates:
                        esperrank += 1
            esper = random.choice(candidates)
            espers.remove(esper)
            espersub = espersubs[esper.name]
            index = espersub.bytestring.index(None)
            espersub.bytestring[index] = 0x10 | len(location.npcs)
            espersub.write(outfile_rom_buffer, patch_name='ancient_espersub')
            event_addr = (espersub.location - 0xa0000) & 0x3FFFF
            event_value = esperevents[esper.name]
            byte, bit = event_value // 8, event_value % 8
            magicite = NPCBlock(pointer=None, locid=location.locid)
            attributes = {
                "graphics": 0x5B, "palette": 2, "x": 44+i, "y": 16,
                "show_on_vehicle": False, "speed":  0,
                "event_addr": event_addr, "facing": 0,
                "no_turn_when_speaking": True, "layer_priority": 2,
                "special_anim": 2,
                "memaddr": byte + 0x17, "membit": bit, "bg2_scroll": 0,
                "move_type": 0, "sprite_priority": 0, "vehicle": 0}
            for key, value in attributes.items():
                setattr(magicite, key, value)
            location.npcs.append(magicite)

        event_addr = pointer - 0xa0000
        pointer = make_challenge_event(location, pointer)
        enemy = NPCBlock(pointer=None, locid=location.locid)
        attributes = {
            "graphics": 0x3e, "palette": 2, "x": 42, "y": 6,
            "show_on_vehicle": False, "speed":  0,
            "event_addr": event_addr, "facing": 2,
            "no_turn_when_speaking": False, "layer_priority": 0,
            "special_anim": 0,
            "memaddr": 0, "membit": 0, "bg2_scroll": 0,
            "move_type": 0, "sprite_priority": 0, "vehicle": 0}
        for key, value in attributes.items():
            setattr(enemy, key, value)
        location.npcs.append(enemy)

        if Options_.is_flag_active('racecave'):
            event_addr = (pswitch_sub.location - 0xa0000) & 0x3FFFF
            partyswitch = NPCBlock(pointer=None, locid=location.locid)
            attributes = {
                "graphics": 0x17, "palette": 0, "x": 55, "y": 16,
                "show_on_vehicle": False, "speed":  0,
                "event_addr": event_addr, "facing": 2,
                "no_turn_when_speaking": False, "layer_priority": 0,
                "special_anim": 0,
                "memaddr": 0, "membit": 0, "bg2_scroll": 0,
                "move_type": 0, "sprite_priority": 0, "vehicle": 0}
            for key, value in attributes.items():
                setattr(partyswitch, key, value)
            location.npcs.append(partyswitch)

        renamer = NPCBlock(pointer=None, locid=location.locid)
        attributes = {
            "graphics": 0x24, "palette": 0, "x": 47, "y": 16,
            "show_on_vehicle": False, "speed": 0,
            "event_addr": 0x209AB, "facing": 2,
            "no_turn_when_speaking": False, "layer_priority": 0,
            "special_anim": 0,
            "memaddr": 0, "membit": 0, "bg2_scroll": 0,
            "move_type": 0, "sprite_priority": 0, "vehicle": 0}
        for key, value in attributes.items():
            setattr(renamer, key, value)
        location.npcs.append(renamer)

    for s in sorted(rest_shops, key=lambda s: s.name):
        if "shops"not in randlog:
            randlog["shops"] = []
        randlog["shops"].append(str(s))

    assert not optional_chars

    if pointer >= 0xb6965:
        raise Exception("Cave events out of bounds. %x" % pointer)

    if not noenc:
        # lower encounter rate
        dungeon_rates = [0x38, 0, 0x20, 0, 0xb0, 0, 0x00, 1,
                         0x1c, 0, 0x10, 0, 0x58, 0, 0x80, 0] + ([0]*16)
        assert len(dungeon_rates) == 32
        encrate_sub = Substitution()
        encrate_sub.set_location(0xC2BF)
        encrate_sub.bytestring = bytes(dungeon_rates)
        encrate_sub.write(outfile_rom_buffer, patch_name='ancient_encounter_rate')

    maxrank = max(locations, key=lambda l: l.ancient_rank).ancient_rank
    for location in locations:
        if location not in restlocs and (location.npcs or location.events):
            for npc in location.npcs:
                if npc == final_save:
                    continue
                if npc.graphics == 0x6F:
                    npc.memaddr, npc.membit, npc.event_addr = 0x73, 1, 0x5EB3
                    success = False
                    for event in location.events:
                        if event.x % 128 == npc.x % 128 and event.y % 128 == npc.y % 128:
                            if success:
                                raise Exception("Duplicate events found.")
                            event.event_addr = 0x5EB3
                            success = True
                    if not success:
                        raise Exception("No corresponding event found.")
        for entrance in location.entrances:
            entrance.dest |= 0x800
        rank = location.ancient_rank
        location.name_id = min(rank, 0xFF)

        if not hasattr(location, "restrank"):
            if hasattr(location, "secret_treasure") and location.secret_treasure:
                pass
            elif location.locid == 334 or not hasattr(location, "routerank"):
                location.music = 58
            elif location.routerank in levelmusic:
                location.music = levelmusic[location.routerank]
            else:
                raise Exception

        location.setid = rank
        if rank == 0:
            location.attacks = 0
        elif rank > 0xFF:
            location.setid = random.randint(0xF0, 0xFF)
        else:
            def enrank(r):
                mr = min(maxrank, 0xFF)
                r = max(0, min(r, mr))
                if Options_.is_flag_active('racecave'):
                    half = r//2
                    quarter = half//2
                    r = (half + random.randint(0, quarter) +
                         random.randint(0, quarter))
                if r <= 0:
                    return 0
                elif r >= mr:
                    return 1.0
                ratio = float(r) / mr
                return ratio

            low = enrank(rank-3)
            high = enrank(rank+2)
            high = int(round(high * len(enemy_formations)))
            low = int(round(low * len(enemy_formations)))
            while high - low < 4:
                high = min(high + 1, len(enemy_formations))
                low = max(low - 1, 0)
            candidates = enemy_formations[low:high]
            chosen_enemies = random.sample(candidates, 4)

            chosen_enemies = sorted(chosen_enemies, key=lambda f: f.rank())

            if Options_.is_flag_active('racecave'):
                bossify = False
            elif rank >= maxrank * 0.9:
                bossify = True
            else:
                if Options_.is_flag_active('speedcave'):
                    thresh = 0.5
                else:
                    thresh = 0.1
                bossify = rank >= random.randint(int(maxrank * thresh),
                                                 int(maxrank * 0.9))
                bossify = bossify and random.randint(1, 3) == 3
            if bossify:
                formrank = chosen_enemies[0].rank()
                candidates = [c for c in boss_formations if c.rank() >= formrank]
                if candidates:
                    if rank < maxrank * 0.75:
                        candidates = candidates[:random.randint(2, 4)]
                    chosen_boss = random.choice(candidates)
                    chosen_enemies[3] = chosen_boss

            if Options_.is_flag_active('speedcave'):
                thresh, bossthresh = 2, 1
            else:
                # allow up to three of the same formation
                thresh, bossthresh = 3, 2
            for c in chosen_enemies:
                used_formations.append(c)
                if used_formations.count(c) >= bossthresh:
                    if c in boss_formations:
                        boss_formations.remove(c)
                    if used_formations.count(c) >= thresh:
                        if c in enemy_formations:
                            enemy_formations.remove(c)

            fset = get_fset(rank)
            fset.formids = [f.formid for f in chosen_enemies]
            for formation in fset.formations:
                if formation.get_music() == 0:
                    formation.set_music(6)
                    formation.set_continuous_music()
                    formation.write_data(outfile_rom_buffer)
            fset.write_data(outfile_rom_buffer)

        if not (hasattr(location, "secret_treasure") and location.secret_treasure):
            if Options_.is_flag_active('speedcave') or rank == 0:
                low = random.randint(0, 400)
                high = random.randint(low, low*5)
                high = random.randint(low, high)
            else:
                low = rank * 2
                high = low * 1.5
                while random.choice([True, False, False]):
                    high = high * 1.5
            if rank < maxrank * 0.4:
                monster = False
            else:
                monster = None
            if 0 < rank < maxrank * 0.75:
                enemy_limit = sorted([f.rank() for f in fset.formations])[-2]
                enemy_limit *= 1.5
            else:
                enemy_limit = None
            location.unlock_chests(int(low), int(high), monster=monster,
                            guarantee_miab_treasure=True,
                            enemy_limit=enemy_limit, uncapped_monsters=Options_.is_flag_active('bsiab'))

        location.write_data(outfile_rom_buffer)

    final_cut = Substitution()
    final_cut.set_location(0xA057D)
    final_cut.bytestring = bytearray([0x3F, 0x0E, 0x00,
                                      0x3F, 0x0F, 0x00,
                                     ])
    if not Options_.is_flag_active("racecave"):
        final_cut.bytestring += bytearray([0x9D,
                                           0x4D, 0x65, 0x33,
                                           0xB2, 0xA9, 0x5E, 0x00])
    else:
        for i in range(16):
            final_cut.bytestring += bytearray([0x3F, i, 0x00])
        locked = 0
        protected = random.sample(starting, 4)
        assignments = {0: [], 1: [], 2: [], 3: []}
        for i, c in enumerate(protected):
            if 1 <= i <= 3 and random.choice([True, False]):
                assignments[i].append(c)

        chars = list(range(16))
        random.shuffle(chars)
        for c in chars:
            if c in protected:
                continue
            if c >= 14 and random.choice([True, False]):
                continue
            if random.choice([True, True, False]):
                i = random.randint(0, 3)
                if len(assignments[i]) >= 3:
                    continue
                elif len(assignments[i]) == 2 and random.choice([True, False]):
                    continue
                assignments[i].append(c)

        for key in assignments:
            for c in assignments[key]:
                locked |= (1 << c)
                if key > 0:
                    final_cut.bytestring += bytearray([0x3F, c, key])
        final_cut.bytestring += bytearray([0x99, 0x03, locked & 0xFF, locked >> 8])
        from chestrandomizer import get_2pack
        event_bosses = {
            1: [0xC18A4, 0xC184B],
            2: [0xC16DD, 0xC171D, 0xC1756],
            3: [None, None, None]}
        outfile_rom_buffer.seek(0xA0F6F)
        outfile_rom_buffer.write(bytes([0x36]))
        candidates = sorted(boss_formations, key=lambda b: b.rank())
        candidates = [c for c in candidates if c.inescapable]
        candidates = candidates[random.randint(0, len(candidates)-16):]
        chosens = random.sample(candidates, 8)
        chosens = sorted(chosens, key=lambda b: b.rank())
        for rank in sorted(event_bosses):
            num = len(event_bosses[rank])
            rankchosens, chosens = chosens[:num], chosens[num:]
            assert len(rankchosens) == num
            random.shuffle(rankchosens)
            if rank == 3:
                bgs = random.sample([0x07, 0x0D, 0x17, 0x18, 0x19, 0x1C,
                                     0x1F, 0x21, 0x22, 0x23, 0x29, 0x2C,
                                     0x30, 0x36, 0x37], 3)
            for i, (address, chosen) in enumerate(
                    zip(event_bosses[rank], rankchosens)):
                if rank == 3:
                    chosen.set_music(5)
                elif rank == 2:
                    chosen.set_music(2)
                else:
                    chosen.set_music(4)
                form_music_overrides[chosen.formid] = chosen.get_music()
                chosen.set_appearing([1, 2, 3, 4, 5, 6,
                                      7, 8, 9, 10, 11, 13])
                fset = get_2pack(chosen)
                if address is not None:
                    outfile_rom_buffer.seek(address)
                    outfile_rom_buffer.write(bytes([fset.setid & 0xFF]))
                else:
                    bg = bgs.pop()
                    final_cut.bytestring += bytearray([
                        0x46, i+1,
                        0x4D, fset.setid & 0xFF, bg,
                        0xB2, 0xA9, 0x5E, 0x00])

        assert not chosens

    final_cut.bytestring += bytearray([0xB2, 0x64, 0x13, 0x00])
    final_cut.write(outfile_rom_buffer, patch_name='ancient_final_cut')
