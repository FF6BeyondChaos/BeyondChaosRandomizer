from ctypes import BigEndianStructure
import itertools
import os
import string
import options
import pathlib
import colorsys

from character import get_characters
from utils import (CHARACTER_PALETTE_TABLE, EVENT_PALETTE_TABLE, FEMALE_NAMES_TABLE, MALE_NAMES_TABLE,
                   MOOGLE_NAMES_TABLE, RIDING_SPRITE_TABLE, SPRITE_REPLACEMENT_TABLE, CORAL_TABLE,
                   generate_character_palette, get_palette_transformer, hex2int, name_to_bytes,
                   open_mei_fallback, read_multi, shuffle_char_hues, custom_path,
                   Substitution, utilrandom as random, write_multi, int2bytes_array)
from io import BytesIO

SPRITE_REPLACEMENT_PATH = os.path.join(custom_path, "sprites")
sprite_replacement_list = None
makeover_groups = None


class SpriteReplacement:
    def __init__(self, file, name, gender, riding=None, fallback_portrait_id=0xE, portrait_filename=None,
                 uniqueids=None, groups=None):
        self.file = file.strip()
        self.name = name.strip()
        self.gender = gender.strip().lower()
        self.size = 0x16A0 if riding is not None and riding.lower() == "true" else 0x1560
        self.uniqueids = [s.strip() for s in uniqueids.split('|')] if uniqueids else []
        self.groups = [s.strip() for s in groups.split('|')] if groups else []
        if self.gender == "female" and "girls" not in self.groups:
            self.groups.append("girls")
        if self.gender == "male" and "boys" not in self.groups:
            self.groups.append("boys")
        self.weight = 1.0

        if fallback_portrait_id == '':
            fallback_portrait_id = 0xE
        self.fallback_portrait_id = int(fallback_portrait_id)
        self.portrait_filename = portrait_filename
        if self.portrait_filename is not None:
            self.portrait_filename = self.portrait_filename.strip()
            if self.portrait_filename:
                self.portrait_palette_filename = portrait_filename.strip()
                if self.portrait_palette_filename and self.portrait_palette_filename:
                    if self.portrait_palette_filename[-4:] == ".bin":
                        self.portrait_palette_filename = self.portrait_palette_filename[:-4]
                    self.portrait_palette_filename = self.portrait_palette_filename + ".pal"
            else:
                self.portrait_filename = None

        self.field_palette_filename = None
        if self.file is not None and self.file[-4:] == ".bin":
            self.field_palette_filename = self.file[:-4] + ".pal"
            
    def has_custom_portrait(self):
        return self.portrait_filename is not None and self.portrait_palette_filename is not None

    def has_field_palette(self):
        return self.field_palette_filename is not None

    def is_on(self, checklist):
        for g in self.uniqueids:
            if g in checklist:
                return True
        return False


def get_sprite_replacements(web_custom_sprite_replacements=None):
    if web_custom_sprite_replacements:
        return [SpriteReplacement(*line.strip().split(',')) for
                                   line in web_custom_sprite_replacements.split("\n")]

    global sprite_replacement_list
    if sprite_replacement_list:
        return sprite_replacement_list

    f = open_mei_fallback(SPRITE_REPLACEMENT_TABLE)
    sprite_replacement_list = [SpriteReplacement(*line.strip().split(',')) for line in f.readlines()]
    f.close()
    return sprite_replacement_list


def recolor_character_palette(outfile_rom_buffer: BytesIO, pointer, palette=None, flesh=False, middle=True,
                              santa=False, skintones=None, char_hues=None, trance=False, skip_index_zero=False):
    outfile_rom_buffer.seek(pointer)
    if palette is None:
        palette = [read_multi(outfile_rom_buffer, length=2) for _ in range(16)]
        outline, eyes, hair, skintone, outfit1, outfit2, NPC = (
            palette[:2], palette[2:4], palette[4:6], palette[6:8],
            palette[8:10], palette[10:12], palette[12:])

        def components_to_color(xxx_todo_changeme):
            (red, green, blue) = xxx_todo_changeme
            return red | (green << 5) | (blue << 10)

        new_style_palette = None
        if skintones and char_hues:
            new_style_palette = generate_character_palette(skintones, char_hues, trance=trance)
            # aliens, available in palette 5 only
            if flesh and random.randint(1, 20) == 1:
                transformer = get_palette_transformer(middle=middle)
                new_style_palette = transformer(new_style_palette)
        elif trance:
            new_style_palette = generate_character_palette(trance=True)

        new_palette = new_style_palette if new_style_palette else []
        if not flesh:
            pieces = (outline, eyes, hair, skintone, outfit1, outfit2, NPC) if not new_style_palette else [NPC]
            for piece in pieces:
                transformer = get_palette_transformer(middle=middle)
                piece = list(piece)
                piece = transformer(piece)
                new_palette += piece

            if not new_style_palette:
                new_palette[6:8] = skintone
            if options.Options_.is_flag_active('christmas'):
                if santa:
                    # color kefka's palette to make him look santa-ish
                    new_palette = palette
                    new_palette[8] = components_to_color((0x18, 0x18, 0x16))
                    new_palette[9] = components_to_color((0x16, 0x15, 0x0F))
                    new_palette[10] = components_to_color((0x1C, 0x08, 0x03))
                    new_palette[11] = components_to_color((0x18, 0x02, 0x05))
                else:
                    # give them red & green outfits
                    red = [components_to_color((0x19, 0x00, 0x05)), components_to_color((0x1c, 0x02, 0x04))]
                    green = [components_to_color((0x07, 0x12, 0x0b)), components_to_color((0x03, 0x0d, 0x07))]

                    random.shuffle(red)
                    random.shuffle(green)
                    outfit = [red, green]
                    random.shuffle(outfit)
                    new_palette[8:10] = outfit[0]
                    new_palette[10:12] = outfit[1]

        else:
            transformer = get_palette_transformer(middle=middle)
            new_palette = transformer(palette)
            if new_style_palette:
                new_palette = new_style_palette[0:12] + new_palette[12:]

        palette = new_palette

    palette_rtn = palette
    if skip_index_zero:
        pointer += 2
        palette = palette[1:]
    outfile_rom_buffer.seek(pointer)
    data: bytes = int2bytes_array(palette)
    outfile_rom_buffer.write(data)

    return palette_rtn


def make_palette_repair(outfile_rom_buffer: BytesIO, main_palette_changes):
    repair_sub = Substitution()
    bytestring = []
    for c in sorted(main_palette_changes):
        _, after = main_palette_changes[c]
        bytestring.extend([0x43, c, after])
    repair_sub.bytestring = bytestring + [0xFE]
    repair_sub.set_location(0xCB154)  # Narshe secret entrance
    repair_sub.write(outfile_rom_buffer, patch_name='make_palette_repair')


NAME_ID_DICT = {
    0: "Terra",
    1: "Locke",
    2: "Cyan",
    3: "Shadow",
    4: "Edgar",
    5: "Sabin",
    6: "Celes",
    7: "Strago",
    8: "Relm",
    9: "Setzer",
    0xa: "Mog",
    0xb: "Gau",
    0xc: "Gogo",
    0xd: "Umaro",
    0xe: "Trooper",
    0xf: "Imp",
    0x10: "Leo",
    0x11: "Banon",
    0x12: "Esper Terra",
    0x13: "Merchant",
    0x14: "Ghost",
    0x15: "Kefka"}


def sanitize_names(names):
    delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum() and c not in "!?/:\"'-.")
    table = str.maketrans(dict.fromkeys(delchars))
    names = [name.translate(table) for name in names]
    return [name[:6] for name in names if name != ""]


def sanitize_coral(names):
    delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum() and c not in "!?/:\"'-.")
    table = str.maketrans(dict.fromkeys(delchars))
    names = [name.translate(table) for name in names]
    return [name[:12] for name in names if name != ""]


def manage_coral(outfile_rom_buffer: BytesIO, web_custom_coral_names=None):
    from dialoguemanager import set_dialogue_var, load_patch_file
    if not web_custom_coral_names:
        coral_file = open_mei_fallback(CORAL_TABLE)
        coralnames = sorted(set(sanitize_coral([line.strip() for line in coral_file.readlines()])))
        coral_file.close()
    else:
        coralnames = sorted(set(sanitize_coral([line.strip() for line in web_custom_coral_names.split("\n")])))

    sprite_log = ""

    newcoralname = random.choice(coralnames)
    sprite_log += str("Coral: ").ljust(17) + string.capwords(str(newcoralname)) + "\n"
    coraldescription1 = "Piece of " + newcoralname.lower() + ","
    coraldescription2 = "found near Ebot's Rock."

    load_patch_file("coral")
    set_dialogue_var("coralsub", newcoralname)

    newcoralnamebytes = name_to_bytes(newcoralname, 12)
    coraldescription1 = name_to_bytes(coraldescription1, 24)
    coraldescription2 = name_to_bytes(coraldescription2, 26)

    coraldescription = coraldescription1 + bytes([0x01]) + coraldescription2

    coral_sub = Substitution()
    coral_sub.set_location(0xEFC08) ##change the name when opening a chest
    coral_sub.bytestring = newcoralnamebytes
    coral_sub.write(outfile_rom_buffer, patch_name='manage_coral')

    coral_sub.set_location(0xEFD7F) ##Change the name in the description
    coral_sub.bytestring = coraldescription
    coral_sub.write(outfile_rom_buffer, patch_name='manage_coral')

    return sprite_log


def manage_character_names(outfile_rom_buffer: BytesIO, change_to, male,
                           moogle_names=None, male_names=None, female_names=None):
    characters = get_characters()
    wild = options.Options_.is_flag_active('partyparty')
    sabin_mode = options.Options_.is_flag_active('suplexwrecks')
    tina_mode = options.Options_.is_flag_active('bravenudeworld')
    soldier_mode = options.Options_.is_flag_active('quikdraw')
    moogle_mode = options.Options_.is_flag_active('kupokupo')
    ghost_mode = options.Options_.is_flag_active('halloween')

    names = []
    if tina_mode:
        names = ["Tina"] * 30 + ["MADUIN"] + ["Tina"] * 3
    elif sabin_mode:
        names = ["Teabin", "Loabin", "Cyabin", "Shabin", "Edabin", "Sabin",
                 "Ceabin", "Stabin", "Reabin", "Seabin", "Moabin", "Gaubin",
                 "Goabin", "Umabin", "Baabin", "Leabin", "??abin", "??abin",
                 "Kuabin", "Kuabin", "Kuabin", "Kuabin", "Kuabin", "Kuabin",
                 "Kuabin", "Kuabin", "Kuabin", "Kaabin", "Moabin", "??abin",
                 "MADUIN", "??abin", "Viabin", "Weabin"]
    elif moogle_mode:
        names = ["Kumop", "Kupo", "Kupek", "Kupop", "Kumama", "Kuku",
                 "Kutan", "Kupan", "Kushu", "Kurin", "Mog", "Kuru",
                 "Kamog", "Kumaro", "Banon", "Leo", "?????", "?????",
                 "Cyan", "Shadow", "Edgar", "Sabin", "Celes", "Strago",
                 "Relm", "Setzer", "Gau", "Gogo"]

        gba_moogle_names = ["Moglin", "Mogret", "Moggie", "Molulu", "Moghan",
                            "Moguel", "Mogsy", "Mogwin", "Mog", "Mugmug", "Cosmog"]

        random_name_ids = []

        # Terra, Locke, and Umaro get a specific name, or a random moogle name from another ff game
        for moogle_id in [0, 1, 13]:
            if random.choice([True, True, False]):
                random_name_ids.append(moogle_id)
        # Other party members get either the name of their counterpart from snes or gba, or moogle name from another ff game
        for moogle_id in itertools.chain(range(2, 10), range(11, 13)):
            chance = random.randint(1, 4)
            if chance == 2:
                names[moogle_id] = gba_moogle_names[moogle_id - 2]
            elif chance != 1:
                random_name_ids.append(moogle_id)

        if not moogle_names:
            f = open_mei_fallback(MOOGLE_NAMES_TABLE)
            mooglenames = sorted(set(sanitize_names([line.strip() for line in f.readlines()])))
            f.close()
        else:
            mooglenames = sorted(set(sanitize_names([name.strip() for name in moogle_names.split("\n")])))

        random_moogle_names = random.sample(mooglenames, len(random_name_ids))
        for index, moogle_id in enumerate(random_name_ids):
            names[moogle_id] = random_moogle_names[index]

        # Human Mog gets a human name, maybe
        if random.choice([True, True, False]):
            if not male_names:
                f = open_mei_fallback(MALE_NAMES_TABLE)
                malenames = sorted(set(sanitize_names([line.strip() for line in f.readlines()])))
                f.close()
            else:
                malenames = sorted(set(sanitize_names([name.strip() for name in male_names.split("\n")])))

            names[10] = random.choice(malenames)
    else:
        if not male_names:
            f = open_mei_fallback(MALE_NAMES_TABLE)
            malenames = sorted(set(sanitize_names([line.strip() for line in f.readlines()])))
            f.close()
        else:
            malenames = sorted(set(sanitize_names([name.strip() for name in male_names.split("\n")])))
        if not female_names:
            f = open_mei_fallback(FEMALE_NAMES_TABLE)
            femalenames = sorted(set(sanitize_names([line.strip() for line in f.readlines()])))
            f.close()
        else:
            femalenames = sorted(set(sanitize_names([name.strip() for name in female_names.split("\n")])))
        for c in range(14):
            choose_male = False
            if wild or soldier_mode or ghost_mode:
                choose_male = random.choice([True, False])
            elif change_to[c] in male:
                choose_male = True

            if choose_male:
                try:
                    name = random.choice(malenames)
                except IndexError:
                    raise IndexError("There were not enough male names supplied. The game requires up to 14 names.")
            else:
                try:
                    name = random.choice(femalenames)
                except IndexError:
                    raise IndexError("There were not enough female names supplied. The game requires up to 14 names.")

            if name in malenames:
                malenames.remove(name)
            if name in femalenames:
                femalenames.remove(name)

            names.append(name)

    umaro_name = names[13]
    for umaro_id in [0x10f, 0x110]:
        from monsterrandomizer import change_enemy_name
        change_enemy_name(outfile_rom_buffer, umaro_id, umaro_name)

    if not options.Options_.is_flag_active('capslockoff'):
        names = [name.upper() for name in names]

    for c in characters:
        if c.id < 14:
            c.newname = names[c.id]
            c.original_appearance = NAME_ID_DICT[c.id]

    for c, name in enumerate(names):
        name = name_to_bytes(name, 6)
        assert len(name) == 6
        outfile_rom_buffer.seek(0x478C0 + (6 * c))
        outfile_rom_buffer.write(name)


def get_free_portrait_ids(swap_to, change_to, char_ids, char_portraits):
    # get unused portraits so we can overwrite them if needed
    sprite_swap_mode = options.Options_.is_flag_active('makeover')
    wild = options.Options_.is_flag_active('partyparty')
    if not sprite_swap_mode:
        return [], False

    def reserve_portrait_id(used_portrait_ids, new, swap, portrait):
        if swap is None:
            if portrait == 0 and wild and new != 0:
                used_portrait_ids.add(0xE)
            else:
                used_portrait_ids.add(new)
        elif not swap.has_custom_portrait():
            used_portrait_ids.add(swap.fallback_portrait_id)
        else:
            return 1
        return 0

    needed = 0
    used_portrait_ids = set()
    for c in char_ids:
        # skip characters who don't have their own portraits
        if (char_portraits[c] == 0 and c != 0) or c == 0x13:
            continue
        new = change_to[c]
        portrait = char_portraits[new]
        swap = swap_to[c] if c in swap_to else None
        needed += reserve_portrait_id(used_portrait_ids, new, swap, portrait)

    if not wild:
        for i in range(0xE, 0x13):
            used_portrait_ids.add(i)

    # Merchant normally uses the same portrait as soldier.
    # If we have a free slot because some others happen to be sharing, use the portrait for the merchant sprite.
    # If not, we have to use the same one as the soldier.
    merchant = False
    if wild and needed < 19 - len(used_portrait_ids):
        c = 0x13
        new = change_to[c]
        portrait = char_portraits[new]
        swap = swap_to[c] if c in swap_to else None
        merchant = reserve_portrait_id(used_portrait_ids, new, swap, portrait)

    free_portrait_ids = list(set(range(19)) - used_portrait_ids)
    return free_portrait_ids, merchant


def get_sprite_swaps(char_ids, male, female, vswaps, web_custom_sprite_replacements=None):
    sprite_swap_mode = options.Options_.is_flag_active('makeover')
    wild = options.Options_.is_flag_active('partyparty')
    clone_mode = options.Options_.is_flag_active('cloneparty')
    replace_all = options.Options_.is_flag_active('novanilla') or options.Options_.is_flag_active('frenchvanilla')
    external_vanillas = False if options.Options_.is_flag_active('novanilla') else (
                options.Options_.is_flag_active('frenchvanilla') or clone_mode)
    if not sprite_swap_mode:
        return []

    known_replacements = get_sprite_replacements(web_custom_sprite_replacements)

    # uniqueids for sprites pulled from rom
    vuids = {0: "terra", 1: "locke", 2: "cyan", 3: "shadow", 4: "edgar", 5: "sabin", 6: "celes", 7: "strago", 8: "relm",
             9: "setzer", 10: "moogle", 11: "gau", 12: "gogo6", 13: "umaro", 16: "leo", 17: "banon", 18: "terra",
             21: "kefka"}

    # determine which character ids are makeover'd
    blacklist = set()
    if replace_all:
        num_to_replace = len(char_ids)
        is_replaced = [True] * num_to_replace
    else:
        replace_min = 8 if not wild else 16
        replace_max = 12 if not wild else 20
        num_to_replace = min(len(known_replacements), random.randint(replace_min, replace_max))
        is_replaced = [True] * num_to_replace + [False] * (len(char_ids) - num_to_replace)
        random.shuffle(is_replaced)
        for i, t in enumerate(is_replaced):
            if i in vuids and not t:
                blacklist.update([s.strip() for s in vuids[i].split('|')])

    if external_vanillas:
        # include vanilla characters, but using the same system/chances as all others
        og_replacements = [
            SpriteReplacement("ogterra.bin", "Terra", "female", "true", 0, None, "terra"),
            SpriteReplacement("oglocke.bin", "Locke", "male", "true", 1, None, "locke"),
            SpriteReplacement("ogcyan.bin", "Cyan", "male", "true", 2, None, "cyan"),
            SpriteReplacement("ogshadow.bin", "Shadow", "male", "true", 3, None, "shadow"),
            SpriteReplacement("ogedgar.bin", "Edgar", "male", "true", 4, None, "edgar"),
            SpriteReplacement("ogsabin.bin", "Sabin", "male", "true", 5, None, "sabin"),
            SpriteReplacement("ogceles.bin", "Celes", "female", "true", 6, None, "celes"),
            SpriteReplacement("ogstrago.bin", "Strago", "male", "true", 7, None, "strago"),
            SpriteReplacement("ogrelm.bin", "Relm", "female", "true", 8, None, "relm", "kids"),
            SpriteReplacement("ogsetzer.bin", "Setzer", "male", "true", 9, None, "setzer"),
            SpriteReplacement("ogmog.bin", "Mog", "neutral", "true", 10, None, "moogle"),
            SpriteReplacement("oggau.bin", "Gau", "male", "true", 11, None, "gau", "kids"),
            SpriteReplacement("oggogo.bin", "Gogo", "neutral", "true", 12, None, "gogo6"),
            SpriteReplacement("ogumaro.bin", "Umaro", "neutral", "true", 13, None, "umaro")]
        if wild:
            og_replacements.extend([
                SpriteReplacement("ogtrooper.bin", "Trooper", "neutral", "true", 14),
                SpriteReplacement("ogimp.bin", "Imp", "neutral", "true", 15),
                SpriteReplacement("ogleo.bin", "Leo", "male", "true", 16, None, "leo"),
                SpriteReplacement("ogbanon.bin", "Banon", "male", "true", 17, None, "banon"),
                SpriteReplacement("ogesperterra.bin", "Esper Terra", "female", "true", 0, "esperterra-p.bin", "terra"),
                SpriteReplacement("ogmerchant.bin", "Merchant", "male", "true", 1, "merchant-p.bin", "merchant"),
                SpriteReplacement("ogghost.bin", "Ghost", "neutral", "true", 18),
                SpriteReplacement("ogkefka.bin", "Kefka", "male", "true", 17, "kefka-p.bin", "kefka")])
        if clone_mode:
            used_vanilla = [NAME_ID_DICT[vswaps[n]] for i, n in enumerate(char_ids) if not is_replaced[i]]
            og_replacements = [r for r in og_replacements if r.name not in used_vanilla]
        known_replacements.extend(og_replacements)

    # weight selection based on no*/hate*/like*/only* codes
    whitelist = [flag.name.lower() for flag in options.Options_.active_flags if flag.value == "only"]
    replace_candidates = []
    for r in known_replacements:
        whitelisted = False
        for group in [group.lower() for group in r.groups]:
            if not r.weight:
                break
            if group in whitelist:
                whitelisted = True
            if options.Options_.get_flag_value(group) == "no":
                r.weight = 0
            elif options.Options_.get_flag_value(group) == "hate":
                r.weight /= 3
            elif options.Options_.get_flag_value(group) == "like":
                r.weight *= 2
        if whitelist and not whitelisted:
            r.weight = 0
        if r.weight:
            replace_candidates.append(r)

    # select sprite replacements
    if not wild or sprite_swap_mode:
        female_candidates = [c for c in replace_candidates if c.gender == "female"]
        male_candidates = [c for c in replace_candidates if c.gender == "male"]
        neutral_candidates = [c for c in replace_candidates if c.gender != "male" and c.gender != "female"]
        
    swap_to = {}
    for char_id in random.sample(char_ids, len(char_ids)):
        if not is_replaced[char_id]:
            continue
        if wild:
            candidates = replace_candidates[:]
        else:
            if female and char_id in female:
                candidates = female_candidates
            elif male and char_id in male:
                candidates = male_candidates
            else:
                candidates = neutral_candidates
            if random.randint(0, len(neutral_candidates) + 2 * len(candidates)) <= len(neutral_candidates):
                candidates = neutral_candidates
        if clone_mode:
            reverse_blacklist = [c for c in candidates if c.is_on(blacklist)]
            if reverse_blacklist:
                weights = [c.weight for c in reverse_blacklist]
                swap_to[char_id] = random.choices(reverse_blacklist, weights)[0]
                blacklist.update(swap_to[char_id].uniqueids)
                candidates.remove(swap_to[char_id])
                continue
        final_candidates = [c for c in candidates if not c.is_on(blacklist)]
        if final_candidates:
            weights = [c.weight for c in final_candidates]
            swap_to[char_id] = random.choices(final_candidates, weights)[0]
            blacklist.update(swap_to[char_id].uniqueids)
            candidates.remove(swap_to[char_id])
        else:
            print(f"custom sprite pool for {char_id} empty, using a vanilla sprite")

    return swap_to


def manage_character_appearance(outfile_rom_buffer: BytesIO, preserve_graphics=False,
                                web_custom_moogle_names=None, web_custom_male_names=None,
                                web_custom_female_names=None, web_custom_sprite_replacements=None):
    characters = get_characters()
    wild = options.Options_.is_flag_active('partyparty')
    sabin_mode = options.Options_.is_flag_active('suplexwrecks')
    tina_mode = options.Options_.is_flag_active('bravenudeworld')
    soldier_mode = options.Options_.is_flag_active('quikdraw')
    moogle_mode = options.Options_.is_flag_active('kupokupo')
    ghost_mode = options.Options_.is_flag_active('halloween')
    christmas_mode = options.Options_.is_flag_active('christmas')
    sprite_swap_mode = options.Options_.is_flag_active('makeover') and not (sabin_mode or tina_mode or soldier_mode or
                                                                            moogle_mode or ghost_mode)
    new_palette_mode = not options.Options_.is_flag_active('sometimeszombies')

    sprite_log = ""

    if new_palette_mode:
        # import recolors for incompatible base sprites
        recolors = [("cyan", 0x152D40, 0x16A0), ("mog", 0x15E240, 0x16A0),
                    ("umaro", 0x162620, 0x16A0), ("dancer", 0x1731C0, 0x5C0),
                    ("lady", 0x1748C0, 0x5C0)]
        for rc in recolors:
            filename = os.path.join(pathlib.Path(__file__).parent.absolute(),
                                    "data",
                                    "sprites",
                                    "RC" + rc[0] + ".bin")
            try:
                with open_mei_fallback(filename, "rb") as f:
                    sprite = f.read()
            except OSError:
                continue
            if len(sprite) >= rc[2]:
                sprite = sprite[:rc[2]]
            outfile_rom_buffer.seek(rc[1])
            outfile_rom_buffer.write(sprite)

    if wild or tina_mode or sabin_mode or christmas_mode:
        if christmas_mode:
            char_ids = list(range(0, 0x15)) # don't replace kefka
        else:
            char_ids = list(range(0, 0x16))
    else:
        char_ids = list(range(0, 0x0E))

    male = None
    female = None
    if tina_mode:
        change_to = dict(list(zip(char_ids, [0x12] * 100)))
    elif sabin_mode:
        change_to = dict(list(zip(char_ids, [0x05] * 100)))
    elif soldier_mode:
        change_to = dict(list(zip(char_ids, [0x0e] * 100)))
    elif ghost_mode:
        change_to = dict(list(zip(char_ids, [0x14] * 100)))
    elif moogle_mode:
        # all characters are moogles except Mog, Imp, and Esper Terra
        if wild:
            # make mog human
            mog = random.choice(list(range(0, 0x0A)) + list(range(0x0B, 0x0F)) + [0x10, 0x11, 0x13, 0x15])
            # esper terra and imp neither human nor moogle
            esper_terra, imp = random.sample([0x0F, 0x12, 0x14], 2)
        else:
            mog = random.choice(list(range(0, 0x0A)) + list(range(0x0B, 0x0E)))
            esper_terra = 0x12
            imp = 0x0F
        change_to = dict(list(zip(char_ids, [0x0A] * 100)))
        change_to[0x0A] = mog
        change_to[0x12] = esper_terra
        change_to[0x0F] = imp
    else:
        female = [0, 0x06, 0x08]
        female += [c for c in [0x03, 0x0A, 0x0C, 0x0D, 0x0E, 0x0F, 0x14] if
                   random.choice([True, False])]
        female = [c for c in char_ids if c in female]
        male = [c for c in char_ids if c not in female]
        if preserve_graphics:
            change_to = dict(list(zip(char_ids, char_ids)))
        elif wild:
            change_to = list(char_ids)
            random.shuffle(change_to)
            change_to = dict(list(zip(char_ids, change_to)))
        else:
            random.shuffle(female)
            random.shuffle(male)
            change_to = dict(list(zip(sorted(male), male)) +
                             list(zip(sorted(female), female)))

    manage_character_names(outfile_rom_buffer, change_to, male, web_custom_moogle_names,
                           web_custom_male_names, web_custom_female_names)

    swap_to = get_sprite_swaps(char_ids, male, female, change_to, web_custom_sprite_replacements)

    for c in characters:
        if c.id < 14:
            if sprite_swap_mode and c.id in swap_to:
                c.new_appearance = swap_to[c.id].name
            elif not preserve_graphics:
                c.new_appearance = NAME_ID_DICT[change_to[c.id]]
            else:
                c.new_appearance = c.original_appearance

    lookup = {c.id: c for c in characters}

    for index, name in NAME_ID_DICT.items():
        if index in swap_to:
            sprite_log += str(str(name) + ": ").ljust(17) + string.capwords(str(swap_to[index].name)) + "\n"
        elif lookup[index].new_appearance is not None:
            sprite_log += str(str(name) + ": ").ljust(17) + string.capwords(str(lookup[index].new_appearance)) + "\n"
        else:
            sprite_log += str(str(name) + ": ").ljust(17) + string.capwords(str(name)) + "\n"

    sprite_ids = list(range(0x16))

    ssizes = ([0x16A0] * 0x10) + ([0x1560] * 6)
    spointers = dict([(c, sum(ssizes[:c]) + 0x150000) for c in sprite_ids])
    ssizes = dict(list(zip(sprite_ids, ssizes)))

    char_portraits = {}
    char_portrait_palettes = {}
    sprites = {}

    riding_sprites = {}
    try:
        f = open(RIDING_SPRITE_TABLE, "r")
    except IOError:
        pass
    else:
        for line in f.readlines():
            char_id, filename = line.strip().split(',', 1)
            try:
                g = open_mei_fallback(os.path.join(SPRITE_REPLACEMENT_PATH, "rb"))
            except IOError:
                continue

            riding_sprites[int(char_id)] = g.read(0x140)
            g.close()
        f.close()

    for c in sprite_ids:
        outfile_rom_buffer.seek(0x36F1B + (2 * c))
        portrait = read_multi(outfile_rom_buffer, length=2)
        char_portraits[c] = portrait
        outfile_rom_buffer.seek(0x36F00 + c)
        portrait_palette = outfile_rom_buffer.read(1)
        char_portrait_palettes[c] = portrait_palette
        outfile_rom_buffer.seek(spointers[c])
        sprite = outfile_rom_buffer.read(ssizes[c])

        if c in riding_sprites:
            sprite = sprite[:0x1560] + riding_sprites[c]
        sprites[c] = sprite

    if tina_mode:
        char_portraits[0x12] = char_portraits[0]
        char_portrait_palettes[0x12] = char_portrait_palettes[0]

    portrait_data = []
    portrait_palette_data = []

    outfile_rom_buffer.seek(0x2D1D00)

    for _ in range(19):
        portrait_data.append(outfile_rom_buffer.read(0x320))

    outfile_rom_buffer.seek(0x2D5860)
    for _ in range(19):
        portrait_palette_data.append(outfile_rom_buffer.read(0x20))

    free_portrait_ids, merchant = get_free_portrait_ids(swap_to, change_to, char_ids, char_portraits)

    for c in char_ids:
        new = change_to[c]
        portrait = char_portraits[new]
        portrait_palette = char_portrait_palettes[new]

        if c == 0x13 and sprite_swap_mode and not merchant:
            new_soldier = change_to[0xE]
            portrait = char_portraits[new_soldier]
            portrait_palette = char_portrait_palettes[new_soldier]
        elif char_portraits[c] == 0 and c != 0:
            portrait = char_portraits[0xE]
            portrait_palette = char_portrait_palettes[0xE]
        elif sprite_swap_mode and c in swap_to:
            use_fallback = True
            fallback_portrait_id = swap_to[c].fallback_portrait_id
            if fallback_portrait_id < 0 or fallback_portrait_id > 18:
                fallback_portrait_id = 0xE

            portrait = fallback_portrait_id * 0x320
            portrait_palette = bytes([fallback_portrait_id])
            new_portrait_data = portrait_data[fallback_portrait_id]
            new_portrait_palette_data = portrait_palette_data[fallback_portrait_id]

            if swap_to[c].has_custom_portrait():
                use_fallback = False

                try:
                    g = open_mei_fallback(os.path.join(SPRITE_REPLACEMENT_PATH, swap_to[c].portrait_filename), "rb")
                    h = open_mei_fallback(os.path.join(SPRITE_REPLACEMENT_PATH, swap_to[c].portrait_palette_filename), "rb")
                except IOError:
                    use_fallback = True
                    print("failed to load portrait %s for %s, using fallback" % (
                          swap_to[c].portrait_filename, swap_to[c].name))
                else:
                    new_portrait_data = g.read(0x320)
                    new_portrait_palette_data = h.read(0x20)
                    h.close()
                    g.close()

            if not use_fallback or fallback_portrait_id in free_portrait_ids:
                portrait_id = free_portrait_ids[0]
                portrait = portrait_id * 0x320
                portrait_palette = bytes([portrait_id])
                free_portrait_ids.remove(free_portrait_ids[0])
                outfile_rom_buffer.seek(0x2D1D00 + portrait)
                outfile_rom_buffer.write(new_portrait_data)
                outfile_rom_buffer.seek(0x2D5860 + portrait_id * 0x20)
                outfile_rom_buffer.write(new_portrait_palette_data)

        elif portrait == 0 and wild and change_to[c] != 0:
            portrait = char_portraits[0xE]
            portrait_palette = char_portrait_palettes[0xE]
        outfile_rom_buffer.seek(0x36F1B + (2 * c))
        write_multi(outfile_rom_buffer, portrait, length=2)
        outfile_rom_buffer.seek(0x36F00 + c)
        outfile_rom_buffer.write(portrait_palette)

        if wild:
            outfile_rom_buffer.seek(spointers[c])
            outfile_rom_buffer.write(sprites[0xE][:ssizes[c]])
        outfile_rom_buffer.seek(spointers[c])

        if sprite_swap_mode and c in swap_to:
            try:
                g = open_mei_fallback(os.path.join(SPRITE_REPLACEMENT_PATH, swap_to[c].file), "rb")
            except IOError:
                newsprite = sprites[change_to[c]]
                for ch in characters:
                    if ch.id == c:
                        ch.new_appearance = NAME_ID_DICT[change_to[c]]
            else:
                newsprite = g.read(min(ssizes[c], swap_to[c].size))
                # if it doesn't have riding sprites, it probably doesn't have a death sprite either
                if swap_to[c].size < 0x16A0:
                    newsprite = newsprite[:0xAE0] + sprites[0xE][0xAE0:0xBA0] + newsprite[0xBA0:]
                g.close()
        else:
            newsprite = sprites[change_to[c]]
        newsprite = newsprite[:ssizes[c]]
        outfile_rom_buffer.write(newsprite)

    # celes in chains
    outfile_rom_buffer.seek(0x159500)
    chains = outfile_rom_buffer.read(192)
    outfile_rom_buffer.seek(0x17D660)
    outfile_rom_buffer.write(chains)

    if options.Options_.is_flag_active('hdmapalette'):
        hdma_palette(outfile_rom_buffer, swap_to)
    else:
        manage_palettes(outfile_rom_buffer, change_to, char_ids)

    return sprite_log


def manage_palettes(outfile_rom_buffer: BytesIO, change_to, char_ids):
    if options.Options_.is_flag_active('hdmapalette'):
        return
    sabin_mode = options.Options_.is_flag_active('suplexwrecks')
    tina_mode = options.Options_.is_flag_active('bravenudeworld')
    christmas_mode = options.Options_.is_flag_active('christmas')
    new_palette_mode = not options.Options_.is_flag_active('sometimeszombies')

    from locationrandomizer import get_npcs
    characters = get_characters()
    npcs = get_npcs()
    charpal_Options = {}
    for line in open(CHARACTER_PALETTE_TABLE):
        if line[0] == '#':
            continue
        charid, palettes = tuple(line.strip().split(':'))
        palettes = list(map(hex2int, palettes.split(',')))
        charid = hex2int(charid)
        charpal_Options[charid] = palettes

    if new_palette_mode:
        twinpal = random.randint(0, 5)
        char_palette_pool = list(range(0, 6)) + list(range(0, 6))
        char_palette_pool.remove(twinpal)
        char_palette_pool.append(random.choice(list(range(0, twinpal)) + list(range(twinpal, 6))))
        while True:
            random.shuffle(char_palette_pool)
            # make sure terra, locke, and edgar are all different
            if twinpal in char_palette_pool[0:2]:
                continue
            if char_palette_pool[0] == char_palette_pool[1]:
                continue
            break
        char_palette_pool = char_palette_pool[:4] + [twinpal, twinpal] + char_palette_pool[4:]

    palette_change_to = {}
    additional_celeses = []
    for npc in npcs:
        if npc.graphics == 0x41:
            additional_celeses.append(npc)
        if npc.graphics not in charpal_Options:
            continue
        # Don't recolor shadowy Sabin on Mt. Kolts
        if npc.locid in [0x60, 0x61]:
            continue
        if npc.graphics in change_to:
            new_graphics = change_to[npc.graphics]
            if (npc.graphics, npc.palette) in palette_change_to:
                new_palette = palette_change_to[(npc.graphics, npc.palette)]
            elif new_palette_mode and npc.graphics < 14:
                new_palette = char_palette_pool[npc.graphics]
                palette_change_to[(npc.graphics, npc.palette)] = new_palette
                npc.palette = new_palette
            else:
                while True:
                    new_palette = random.choice(charpal_Options[new_graphics])
                    if sabin_mode or tina_mode:
                        new_palette = random.randint(0, 5)

                    if (new_palette == 5 and new_graphics not in
                            [3, 0xA, 0xC, 0xD, 0xE, 0xF, 0x12, 0x14] and
                            random.randint(1, 10) != 10):
                        continue
                    break
                palette_change_to[(npc.graphics, npc.palette)] = new_palette
                npc.palette = new_palette
            npc.palette = new_palette
    for npc in additional_celeses:
        if (6, 0) in palette_change_to:
            npc.palette = palette_change_to[(6, 0)]

    main_palette_changes = {}
    for character in characters:
        c = character.id
        if c not in change_to:
            continue
        outfile_rom_buffer.seek(0x2CE2B + c)
        before = ord(outfile_rom_buffer.read(1))
        new_palette = palette_change_to[(c, before)]
        main_palette_changes[c] = (before, new_palette)
        outfile_rom_buffer.seek(0x2CE2B + c)
        outfile_rom_buffer.write(bytes([new_palette]))
        pointers = [0, 4, 9, 13]
        pointers = [ptr + 0x18EA60 + (18 * c) for ptr in pointers]
        if c < 14:
            for ptr in pointers:
                outfile_rom_buffer.seek(ptr)
                byte = ord(outfile_rom_buffer.read(1))
                byte = byte & 0xF1
                byte |= ((new_palette + 2) << 1)
                outfile_rom_buffer.seek(ptr)
                outfile_rom_buffer.write(bytes([byte]))
        character.palette = new_palette

    if options.Options_.is_flag_active('repairpalette'):
        make_palette_repair(outfile_rom_buffer, main_palette_changes)

    if new_palette_mode:
        char_hues = get_char_hues()
        skintones = get_skinstones()
        snowmanvampire = ((29, 29, 30), (25, 25, 27))
        if christmas_mode or random.randint(1, 100) > 66:
            skintones.append(snowmanvampire)
        random.shuffle(skintones)
        # no vampire townsfolk
        if snowmanvampire in skintones[:6] and not christmas_mode:
            skintones.remove(snowmanvampire)
            skintones = skintones[:5] + [snowmanvampire]

    for i in range(6):
        pointer = 0x268000 + (i * 0x20)
        if new_palette_mode:
            palette = recolor_character_palette(outfile_rom_buffer, pointer, palette=None,
                                                flesh=(i == 5), santa=(christmas_mode and i == 3),
                                                skintones=skintones, char_hues=char_hues)
        else:
            palette = recolor_character_palette(outfile_rom_buffer, pointer, palette=None,
                                                flesh=(i == 5), santa=(christmas_mode and i == 3))
        pointer = 0x2D6300 + (i * 0x20)
        recolor_character_palette(outfile_rom_buffer, pointer, palette=palette)

    # esper terra
    pointer = 0x268000 + (8 * 0x20)
    if new_palette_mode:
        palette = recolor_character_palette(outfile_rom_buffer, pointer, palette=None, trance=True)
    else:
        palette = recolor_character_palette(outfile_rom_buffer, pointer, palette=None, flesh=True,
                                            middle=False)
    pointer = 0x2D6300 + (6 * 0x20)
    palette = recolor_character_palette(outfile_rom_buffer, pointer, palette=palette)

    # recolor magitek and chocobos
    transformer = get_palette_transformer(middle=True)

    def recolor_palette(pointer, size):
        outfile_rom_buffer.seek(pointer)
        palette = [read_multi(outfile_rom_buffer, length=2) for _ in range(size)]
        palette = transformer(palette)
        outfile_rom_buffer.seek(pointer)
        for color in palette:
            write_multi(outfile_rom_buffer, color, length=2)

    recolor_palette(0x2cfd4, 23)
    recolor_palette(0x268000 + (7 * 0x20), 16)
    recolor_palette(0x12ee20, 16)
    recolor_palette(0x12ef20, 16)

    for line in open(EVENT_PALETTE_TABLE):
        if line[0] == '#':
            continue
        line = line.split(' ')
        if len(line) > 1:
            if line[1] == 'c' and options.Options_.is_flag_active('thescenarionottaken'):
                return
            if line[1] == 'd' and not options.Options_.is_flag_active('thescenarionottaken'):
                return
        pointer = hex2int(line[0].strip())
        outfile_rom_buffer.seek(pointer)
        data = bytearray(outfile_rom_buffer.read(5))
        char_id, palette = data[1], data[4]
        if char_id not in char_ids:
            continue
        try:
            data[4] = palette_change_to[(char_id, palette)]
        except KeyError:
            continue

        outfile_rom_buffer.seek(pointer)
        outfile_rom_buffer.write(data)

def get_char_hues():
    char_hues = get_char_hues_base()
    char_hues.append(random.choice([0, 0, 345, random.randint(105, 135)]))
    char_hues = shuffle_char_hues(char_hues)
    return char_hues
def get_char_hues_base():
    return [0, 10, 20, 30, 45, 60, 75, 90, 120, 150, 180, 200, 220, 240, 270, 300, 330]
def get_skinstones():
    skintones = [
        ((31, 24, 17), (25, 13, 7)),
        ((31, 23, 15), (25, 15, 8)),
        ((31, 24, 17), (25, 13, 7)),
        ((31, 25, 15), (25, 19, 10)),
        ((31, 25, 16), (24, 15, 12)),
        ((27, 17, 10), (20, 12, 10)),
        ((25, 20, 14), (19, 12, 4)),
        ((27, 22, 18), (20, 15, 12)),
        ((28, 22, 16), (22, 13, 6)),
        ((28, 23, 15), (22, 16, 7)),
        ((27, 23, 15), (20, 14, 9))]
    return skintones


#  HDMA palette Made by Myself086

# FIELD_PALETTE contains palettes of 16 colors, 32 bytes per palette
# Color index 0 is reserved for PAL and CMD listed below
# Color 12 bit 15 is set when the palette is only 12 colors instead of 16 which is important for the solver's efficiency

# High byte command (CMD) for FIELD_PALETTE from myselfpatches.py
HDMA_PALETTE__CMD_NEVER_CHANGE = 0x00
HDMA_PALETTE__CMD_ALWAYS_CHANGE = 0x02
HDMA_PALETTE__CMD_IF_PALETTE_0 = 0x04       # If original palette match, change
HDMA_PALETTE__CMD_IF_PALETTE_1 = 0x06
HDMA_PALETTE__CMD_IF_PALETTE_2 = 0x08
HDMA_PALETTE__CMD_IF_PALETTE_3 = 0x0a
HDMA_PALETTE__CMD_IF_PALETTE_4 = 0x0c
HDMA_PALETTE__CMD_IF_PALETTE_5 = 0x0e
HDMA_PALETTE__CMD_IF_PALETTE_6 = 0x10
HDMA_PALETTE__CMD_IF_PALETTE_7 = 0x12
HDMA_PALETTE__CMD_IFNOT_PALETTE_0 = 0x14    # If original palette doesn't match, change
HDMA_PALETTE__CMD_IFNOT_PALETTE_1 = 0x16
HDMA_PALETTE__CMD_IFNOT_PALETTE_2 = 0x18
HDMA_PALETTE__CMD_IFNOT_PALETTE_3 = 0x1a
HDMA_PALETTE__CMD_IFNOT_PALETTE_4 = 0x1c
HDMA_PALETTE__CMD_IFNOT_PALETTE_5 = 0x1e
HDMA_PALETTE__CMD_IFNOT_PALETTE_6 = 0x20
HDMA_PALETTE__CMD_IFNOT_PALETTE_7 = 0x22
HDMA_PALETTE__CMD_USE_ORIGINAL = 0x24       # Force using original palette* (PAL equivalent exists)

# Low byte destination palette (PAL) for FIELD_PALETTE from myselfpatches.py
HDMA_PALETTE__PAL_CUSTOM_COUNT = 0xe0       # Number of palettes located in FIELD_PALETTE
HDMA_PALETTE__PAL_MOD_BOTTOM = 0xe0         # Palettes affected by event color modifiers (do not use in python)
HDMA_PALETTE__PAL_MOD_TOP = 0xef
HDMA_PALETTE__PAL_VANILLA_BOTTOM = 0xf0     # Original palettes**
HDMA_PALETTE__PAL_VANILLA_TOP = 0xf7
HDMA_PALETTE__PAL_VANILLA_X = 0xf8          # Force using original palette* (CMD equivalent exists)
HDMA_PALETTE__PAL_DEFAULT = 0xfe            # Default gray palette (can use in python but may not solve properly)
HDMA_PALETTE__PAL_UNKNOWN = 0xff            # Assumed unknown/unused by the solver (do not use in python)

# * "Force using original palette" will pick a palette between 0xf0 to 0xf7 based on the palette designated to the sprite.
# ** "Original palettes" are the original 8 hardware palettes used by the game during field display.

def hdma_palette(outfile_rom_buffer: BytesIO, swap_to: dict[int, SpriteReplacement]):
    if not options.Options_.is_flag_active('hdmapalette'):
        return
    random_palette_order = False        # Randomize custom palette order (TODO: Add flag for this)
    random_color_palette = False        # Ignore exact custom palettes and create random palettes based on them (TODO: Add flag for this)

    HUE_THRESHOLD = 48                  # For determining hue groups, hue/360

    _sub = Substitution()

    # Get palette table location
    from myselfpatches import myself_patches
    palette_location = myself_patches(outfile_rom_buffer).get("FIELD_PALETTE")

    # Get/set methods for new palettes
    def bytes_to_rgb(byte_data, mult=0x1f):
        (byte0, byte1) = byte_data[0:2]
        color = byte0 + (byte1 << 8)
        mult = mult / 0x1f
        r = ((color >> 0) & 0x1f) * mult
        g = ((color >> 5) & 0x1f) * mult
        b = ((color >> 10) & 0x1f) * mult
        return (r, g, b)
    def get_cmd(index: int):
        outfile_rom_buffer.seek(palette_location + index * 32 + 0)
        return outfile_rom_buffer.read(2)
    def set_cmd(index: int, pal, cmd):
        _sub.set_location(palette_location + index * 32 + 0)
        _sub.bytestring = bytes([pal, cmd])
        _sub.write(outfile_rom_buffer, noverify=True, patch_name = "hdma_palette_cmd")
    def set_pal_rgb(index: int, rgb_values):
        if len(rgb_values) > 15: rgb_values = rgb_values[:15]
        data = []
        for (r, g, b) in rgb_values:
            # Format: 0bbbbbgggggrrrrr
            data.append(
                ((r & 0x1f) << 0) |
                ((g & 0x1f) << 5) |
                ((b & 0x1f) << 10)
            )
        set_pal_value(index, data)
    def set_pal_value(index: int, values):
        if len(values) > 15: values = values[:15]
        data = []
        for val in values:
            data.append((val >> 0) & 0xff)
            data.append((val >> 8) & 0xff)
        set_pal_data(index, bytes(data))
    def set_pal_data(index: int, data: bytes):
        if len(data) > 30: data = data[:30]
        _sub.set_location(palette_location + index * 32 + 2)
        _sub.bytestring = data
        _sub.write(outfile_rom_buffer, noverify=True, patch_name = "hdma_palette")

    # Method for generating a summary of the custom palettes
    unchanging = None
    hue_groups: dict[int, list[int]] = None
    char_hues_groups: dict[int, list[int]] = None
    skintones = None
    hls_base: list[int] = None
    lightness_ranges = None                 # Unused
    ALL_CHAR_HUES = get_char_hues_base()    # Used as constant
    def gen_palette_summary(palette_data: bytes):
        outer_range = range(0, len(palette_data) & ~0x1f, 0x20)
        inner_range = range(3*2, 16*2, 2)

        # Default summary
        nonlocal unchanging, hue_groups, char_hues_groups, skintones, hls_base, lightness_ranges, ALL_CHAR_HUES
        unchanging = [0, 1, 2]
        hue_groups = {}
        char_hues_groups = {}
        skintones = get_skinstones()
        hls_base = [None] * 16
        #lightness_ranges: list[range | None] = [None] * 16

        # Unchanging colors
        if len(palette_data) >= 0x40:
            for x in inner_range:
                x2 = x>>1
                if x2>>1 != 3:      # Not skin tone
                    main_color = palette_data[x:x+2]
                    same = True
                    if palette_data[x+1] < 0x80:    # Check for unused color
                        for y in outer_range:
                            if main_color != palette_data[y+x:y+x+2]:
                                same = False
                                break
                    if same:
                        unchanging.append(x2)

        # Create groups
        def append_hue_group(index, hue_value):
            if hue_value >= 0:
                # Find most similar hue group
                best_hue = None
                best_diff = 0xffff
                for (key, indices) in hue_groups.items():
                    diff = abs(hue_value - key)
                    if best_diff > diff:
                        best_diff = diff
                        best_hue = key
                # Add to new group or existing group
                if best_diff > HUE_THRESHOLD:
                    # New group
                    hue_groups[int(hue_value)] = [index]
                    char_hues_groups[index] = temp_list = get_char_hues_base()
                    random.shuffle(temp_list)
                else:
                    # Exisitng group
                    hue_groups[best_hue].append(index)
            else:
                # TODO: Gray groups?
                pass
        for x in inner_range:
            x2 = x>>1

            # Get rgb and hls
            (r, g, b) = bytes_to_rgb(palette_data[x:x+2], mult = 1)
            (h, l, s) = [z*360.0 for z in colorsys.rgb_to_hls(r,g,b)]

            # Record base hls
            hls_base[x2] = [h, l, s]

            # Changing?
            if x2 not in unchanging and x2 >> 1 != 3:
                # Add to hue group or gray group
                append_hue_group(x2, h if s > 48 else -1)

        # Remove used hue groups if randomization is necessary
        if not random_color_palette and len(palette_data) < 0x20 * 5:
            for _, group in hue_groups.items():
                x2 = group[0]
                x = x2 << 1

                # Get hues for this group
                hue_group = char_hues_groups[x2]

                for y in outer_range:
                    # Get rgb and hls
                    (r, g, b) = bytes_to_rgb(palette_data[x:x+2], mult = 1)
                    (h, l, s) = [z*360.0 for z in colorsys.rgb_to_hls(r,g,b)]

                    # Find most similar hue group
                    best_hue = None
                    best_diff = 0xffff
                    for key in ALL_CHAR_HUES:
                        diff = abs(h - key)
                        if best_diff > diff:
                            best_diff = diff
                            best_hue = key

                    # Remove most similar hue
                    if best_hue in hue_group:
                        hue_group.remove(best_hue)

        return

    # Find first extra palette
    extra_palette = 0xff
    for x in range(HDMA_PALETTE__PAL_CUSTOM_COUNT):
        (pal, cmd) = get_cmd(x)
        if HDMA_PALETTE__CMD_IF_PALETTE_0 <= cmd <= HDMA_PALETTE__CMD_IFNOT_PALETTE_7 and pal < HDMA_PALETTE__PAL_CUSTOM_COUNT:
            extra_palette = pal
            break

    # Apply palette changes
    for x in range(0, extra_palette):
        swap: SpriteReplacement = swap_to.get(x)
        if swap is None:
            # Use original palette for unchanged sprites
            set_cmd(x, 0, HDMA_PALETTE__CMD_USE_ORIGINAL)
        else:
            # Load custom palette if the file exists
            palette_data = None
            if swap.has_field_palette():
                try:
                    f = open_mei_fallback(os.path.join(SPRITE_REPLACEMENT_PATH, swap.field_palette_filename), "rb")
                except IOError:
                    pass
                else:
                    palette_data = f.read()
                    f.close()

            # TEST ONLY
            if swap.name.lower() == "locke":
                pass

            # Main palette name based on character ID
            pal_name = x

            # .pal file found?
            if palette_data is not None and len(palette_data) >= 0x20:
                # Split palettes from the .pal file
                palettes: list[bytes] = []
                for y in range(0, len(palette_data) & ~0x1f, 0x20):
                    palettes.append(palette_data[y:y+0x20])

                # Apply custom palette either linearly or randomly
                pal_valid_summary = False
                pal_main = palettes[0] if palettes else None
                while True:
                    # Apply one palette to this pal_name
                    pal = None if len(palettes) == 0 else palettes.pop(0 if not random_palette_order else random.randrange(0, len(palettes)))
                    if pal is not None and not random_color_palette:
                        set_pal_data(pal_name, pal[2:])
                    else:
                        # Get palette summary
                        if not pal_valid_summary:
                            gen_palette_summary(palette_data)
                            pal_valid_summary = True

                        # Generate palette based on summary
                        base_hues = {}
                        colors = [0x1f, 0x7c] * 16      # Fill with error color
                        for c in range(16):
                            c2=c*2
                            if c in unchanging:
                                colors[c2:c2+2] = pal_main[c2:c2+2]
                            else:
                                hue_key = None
                                for key, items in hue_groups.items():
                                    if c in items:
                                        hue_key = items[0]
                                        break
                                if c == 6:
                                    (r, g, b) = skintones[0][0]
                                elif c == 7:
                                    (r, g, b) = skintones.pop(0)[1]
                                elif hue_key is not None:
                                    (h, l, s) = hls_base[c]
                                    if hue_key not in base_hues:
                                        h = base_hues[hue_key] = char_hues_groups[hue_key].pop(0)
                                        h = base_hues[hue_key] = char_hues_groups[hue_key].pop(0)
                                        h = base_hues[hue_key] = char_hues_groups[hue_key].pop(0)
                                        h = base_hues[hue_key] = char_hues_groups[hue_key].pop(0)
                                    else:
                                        h = base_hues[hue_key]
                                    (h, l, s) = [z/360.0 for z in [h, l, s]]
                                    (r, g, b) = [z*0x1f for z in colorsys.hls_to_rgb(h, l, s)]
                                else:
                                    (r, g, b) = [31, 0, 31]     # Error color
                                new_data = (
                                    (int(r + 0.5) << 0) |
                                    (int(g + 0.5) << 5) |
                                    (int(b + 0.5) << 10))
                                colors[c2:c2+2] = [new_data & 0xff, new_data >> 8]

                        # Write palette data
                        set_pal_data(pal_name, bytes(colors[2:]))

                    # Get next pal_name if valid alternate
                    (pal, cmd) = get_cmd(pal_name)
                    if HDMA_PALETTE__CMD_IF_PALETTE_0 <= cmd <= HDMA_PALETTE__CMD_IFNOT_PALETTE_7 and pal < HDMA_PALETTE__PAL_CUSTOM_COUNT:
                        pal_name = pal
                    else:
                        break

                # Temp set palette
                #set_pal_data(x, palette_data[2:32])
            else:
                # No .pal file, generate random palette based on the old palette randomizer
                while True:
                    # Write palette
                    recolor_character_palette(
                        outfile_rom_buffer, palette_location + pal_name * 32, palette=None,
                        flesh=False, santa=False,           # flesh and santa not supported here
                        skintones=skintones, char_hues=char_hues,
                        skip_index_zero=True)               # Color index 0 is reserved for scripts

                    # Get next pal_name if valid alternate
                    (pal, cmd) = get_cmd(pal_name)
                    if HDMA_PALETTE__CMD_IF_PALETTE_0 <= cmd <= HDMA_PALETTE__CMD_IFNOT_PALETTE_7 and pal < HDMA_PALETTE__PAL_CUSTOM_COUNT:
                        pal_name = pal
                    else:
                        break

    return

