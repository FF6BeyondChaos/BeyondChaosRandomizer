import traceback
import options

from io import BytesIO
from utils import (hex2int, write_multi, read_multi, ITEM_TABLE,
                   CUSTOM_ITEMS_TABLE, mutate_index,
                   name_to_bytes, utilrandom as random,
                   Substitution)
from skillrandomizer import get_ranked_spells
from copy import deepcopy

# future blocks: chests, morphs, shops

ITEM_STATS = ["learnrate", "learnspell", "fieldeffect",
              "statusprotect1", "statusprotect2", "statusacquire3",
              "statboost1", "special1", "statboost2", "special2",
              "special3", "targeting", "elements", "speedvigor",
              "magstam", "breakeffect", "otherproperties", "power",
              "hitmdef", "elemabsorbs", "elemnulls", "elemweaks",
              "statusacquire2", "mblockevade", "specialaction"]

STATPROTECT = {"fieldeffect": 0xdc,
               "statusprotect1": 0x00,
               "statusprotect2": 0x00,
               "statusacquire3": 0x00,
               "statboost1": 0x00,
               "special1": 0x00,
               "statboost2": 0x02,
               "special2": 0x28,
               "special3": 0x60,
               "otherproperties": 0xdf,
               "statusacquire2": 0x00}

all_spells = None
effects_used = []
itemdict = {}
customs = {}
changed_commands = []

break_unused_dict = {0x09: list(range(0xA3, 0xAB)),
                     0x08: list(range(0xAB, 0xB0)) + list(range(0x41, 0x44))}


def set_item_changed_commands(commands):
    global changed_commands
    changed_commands = set(commands)


def get_custom_items():
    if customs:
        return customs

    customname, customdict = None, None
    for line in open(CUSTOM_ITEMS_TABLE):
        while '  ' in line:
            line = line.replace('  ', ' ')
        line = line.strip()
        if not line or line[0] == '#':
            continue

        if line[0] == '!':
            if customname is not None:
                customs[customname] = customdict
            customdict = {}
            customname = line[1:].strip()
            continue

        key, value = tuple(line.split(' ', 1))
        customdict[key] = value

    customs[customname] = customdict
    return get_custom_items()


def bit_mutate(byte, op="on", nochange=0x00):
    if op == "on":
        bit = 1 << random.randint(0, 7)
        if bit & nochange:
            return byte
        byte = byte | bit
    elif op == "off":
        bit = 1 << random.randint(0, 7)
        if bit & nochange:
            return byte
        bit = 0xff ^ bit
        byte = byte & bit
    elif op == "invert":
        bit = 1 << random.randint(0, 7)
        if bit & nochange:
            return byte
        byte = byte ^ bit
    return byte


def extend_item_breaks(fout):
    break_sub = Substitution()
    break_sub.set_location(0x22735)
    break_sub.bytestring = bytes([0x22, 0x13, 0x30, 0xF0])
    break_sub.write(fout)

    break_sub.set_location(0x22743)
    break_sub.bytestring = bytes([0x30, 0x05])
    break_sub.write(fout)

    break_sub.set_location(0x2274A)
    break_sub.bytestring = bytes([0xAD, 0x10, 0x34])
    break_sub.write(fout)

    break_sub.set_location(0x229ED)
    break_sub.bytestring = bytes([0x22, 0x00, 0x30, 0xF0, 0xEA, 0xEA])
    break_sub.write(fout)

    break_sub.set_location(0x23658)
    break_sub.bytestring = bytes([0xAD, 0x7E, 0x3A])
    break_sub.write(fout)

    break_sub.set_location(0x303000)
    break_sub.bytestring = bytes(
        [0xBD, 0xA4, 0x3B, 0x29, 0x0C, 0x0A, 0x0A, 0x0A, 0x0A, 0x8D, 0x89, 0x3A, 0xBD, 0x34, 0x3D, 0x8D, 0x7E, 0x3A,
         0x6B, 0x08, 0xBF, 0x12, 0x50, 0xD8, 0x8D, 0x10, 0x34, 0xBF, 0x13, 0x50, 0xD8, 0x0A, 0x0A, 0x0A, 0x0A, 0x28,
         0x29, 0xC0, 0x6B])
    break_sub.write(fout)


class ItemBlock:
    def __init__(self, itemid, pointer, name):
        self.itemid = hex2int(itemid)
        self.pointer = hex2int(pointer)
        self.name = name
        self.degree = None
        self.banned = False
        self.itemtype = 0

        self.price = 0
        self._rank = None
        self.dataname = bytes()
        self.heavy = False

        self.vanilla_data = None

    @property
    def is_tool(self):
        return self.itemtype & 0x0f == 0x00

    @property
    def is_weapon(self):
        return self.itemtype & 0x0f == 0x01

    @property
    def is_armor(self):
        return self.is_body_armor or self.is_shield or self.is_helm

    @property
    def is_body_armor(self):
        return self.itemtype & 0x0f == 0x02

    @property
    def is_shield(self):
        return self.itemtype & 0x0f == 0x03

    @property
    def is_helm(self):
        return self.itemtype & 0x0f == 0x04

    @property
    def is_relic(self):
        return self.itemtype & 0x0f == 0x05

    @property
    def is_consumable(self):
        return self.itemtype & 0x0f == 0x06

    def set_degree(self, value):
        self.degree = value

    def read_stats(self, rom_file_buffer: BytesIO=False):
        global all_spells

        rom_file_buffer.seek(self.pointer)
        self.itemtype = ord(rom_file_buffer.read(1))

        # throwable = self.itemtype & 0x10
        # usable_battle = self.itemtype & 0x20
        # usable_field = self.itemtype & 0x40

        self.equippable = read_multi(rom_file_buffer, length=2)
        self.heavy = bool(self.equippable & 0x8000)

        stats = list(rom_file_buffer.read(len(ITEM_STATS)))
        self.features = dict(list(zip(ITEM_STATS, stats)))

        # move flags for "randomly cast" and "destroy if used"
        # so breakeffect can use the full range of spells
        if not self.is_consumable:
            break_flags = self.features["breakeffect"] & 0xC0
            self.features["otherproperties"] |= break_flags >> 4
            self.features["breakeffect"] &= ~0xC0

        self.price = read_multi(rom_file_buffer, length=2)

        if all_spells is None:
            all_spells = get_ranked_spells(rom_file_buffer)
            all_spells = [s for s in all_spells if s.valid]

        rom_file_buffer.seek(0x2CE408 + (8 * self.itemid))
        self.weapon_animation = list(rom_file_buffer.read(8))

        rom_file_buffer.seek(0x12B300 + (13 * self.itemid))
        self.dataname = list(rom_file_buffer.read(13))

        # unhardcoded tintinabar patch moves the tintinabar flag
        if self.features["fieldeffect"] & 0x80:
            self.features["fieldeffect"] &= ~0x80
            self.features["special2"] |= 0x80

    def ban(self):
        self.banned = True

    def become_another(self, customdict=None, tier=None, halloween=False):
        customs = get_custom_items()
        if customdict is None:
            if halloween:
                candidates = [customs[key] for key in sorted(customs) if customs[key]["name_text"] == "SORD....."]
            else:
                if tier is None:
                    candidates = [customs[key] for key in sorted(customs)]
                else:
                    candidates = [customs[key] for key in sorted(customs) if customs[key]["tier"] == tier]
            customdict = random.choice(candidates)
        s = customdict["name_text"]
        for key in self.features:
            self.features[key] = 0

        def convert_value(v):
            v = v.split()

            def intify(value):
                subintify = lambda x: int(x, 0x10)
                if ',' in value:
                    return random.choice(list(map(subintify, value.split(','))))
                return subintify(value)

            if len(v) == 1:
                return intify(v[0])
            return list(map(intify, v))

        name = bytes()
        for key, value in customdict.items():
            if key == "name_text":
                name = name + name_to_bytes(value, 12)
            elif key == "description":
                pass
            elif key == "tier":
                pass
            else:
                value = convert_value(value)
                if key == "name_icon":
                    name = bytes([value]) + name
                elif hasattr(self, key):
                    setattr(self, key, value)
                elif key in self.features:
                    self.features[key] = value

        self.dataname = name
        self.ban()

        return s

    def write_stats(self, fout):
        fout.seek(self.pointer)
        fout.write(bytes([self.itemtype]))

        self.confirm_heavy()
        write_multi(fout, self.equippable, length=2)

        s = bytes([self.features[key] for key in ITEM_STATS])
        fout.write(s)

        write_multi(fout, self.price, length=2)

        if self.is_weapon or (self.itemtype & 0x0f) == 0x01:
            if self.itemid < 93:
                fout.seek(0x2CE408 + (8 * self.itemid))
            else:
                fout.seek(0x303100 + (8 * (self.itemid - 93)))
            fout.write(bytes(self.weapon_animation))

        fout.seek(0x12B300 + (13 * self.itemid))
        fout.write(bytes(self.dataname))

    def confirm_heavy(self):
        if self.heavy and self.equippable:
            self.equippable |= 0x8000
        else:
            self.equippable &= 0x7FFF

    def equippable_by(self, charid):
        return self.equippable & (1 << charid)

    def unrestrict(self):
        if self.is_weapon:
            self.itemtype |= 0x10
            self.features['otherproperties'] |= 0x82

    @property
    def has_disabling_status(self):
        if self.features['statusacquire2'] & 0xf9:
            return True
        if self.features['statusacquire3'] & 0x14:
            return True
        if (self.features['specialaction'] & 0xf0) in {0x50, 0x60, 0xC0}:
            return True
        return False

    @property
    def imp_only(self):
        return self.equippable & 0x4000

    @property
    def prevent_encounters(self):
        return bool(self.features['fieldeffect'] & 0x02)

    @property
    def evade(self):
        mblockevade = self.features['mblockevade']
        evade = mblockevade & 0x0f
        return evade

    @property
    def mblock(self):
        mblockevade = self.features['mblockevade']
        mblock = (mblockevade & 0xf0) >> 4
        return mblock

    def pick_a_spell(self, magic_only=False, custom=None):
        if magic_only:
            spells = [s for s in all_spells if s.spellid in range(0, 36)]
        else:
            spells = all_spells

        if custom:
            spells = list(filter(custom, spells))

        spells = sorted(spells, key=lambda s: s.rank())
        items = get_ranked_items()
        index = items.index(self)
        index = int((index / float(len(items))) * len(spells))
        index = mutate_index(index, len(spells), [False, True, True],
                             (-5, 4), (-3, 3))
        spell = spells[index]

        return spell, index / float(len(spells))

    def get_feature(self, feature, feature_byte):
        features = {
            "statboost1": {1 << i: e for i, e in
                           enumerate(["Bat. Pwr +1/4", "Mag. Pwr +1/4", "+1/4 HP",
                                      "+1/2 HP", "+1/8 HP", "+1/4 MP", "+1/2 MP", "+1/8 MP"])},
            "statboost2": {1 << i: e for i, e in
                           enumerate(["Better Steal", "",
                                      "Better Sketch", "Better Control", "100% Hit Rate",
                                      "1/2 MP Cost", "MP cost = 1", "Vigor +50%"])},
            "special1": {1 << i: e for i, e in
                         enumerate(["Initiative", "Vigilance", "Command Changer",
                                    "Command Changer", "Command Changer", "Command Changer",
                                    "Command Changer", "Super Jump"])},
            "special2": {1 << i: e for i, e in
                         enumerate(["Fight -> X-Fight", "Can counter",
                                    "Random Evade", "Use weapon 2-handed",
                                    "Can equip 2 weapons", "Can equip anything",
                                    "Cover", "Step regen"])},
            "special3": {1 << i: e for i, e in
                         enumerate(["Low HP Shell", "Low HP Safe", "Low HP Reflect",
                                    "Double EXP", "Double GP",
                                    "", "", "Reverses Cures"])},
            "statusprotect1": {1 << i: e for i, e in
                               enumerate(["No dark", "No zombie", "No poison",
                                          "No magitek", "No clear", "No imp",
                                          "No petrify", "Death protection"])},
            "statusprotect2": {1 << i: e for i, e in
                               enumerate(["No condemned", "Near fatal always",
                                          "No image", "No mute", "No berserk", "No muddle",
                                          "No seizure", "No sleep"])},
            "statusacquire2": {1 << i: e for i, e in
                               enumerate(["Condemned", "Near fatal", "Image", "Mute",
                                          "Berserk", "Muddle", "Seizure", "Sleep"])},
            "statusacquire3": {1 << i: e for i, e in
                               enumerate(["Auto float", "Auto regen", "Auto slow",
                                          "Auto haste", "Auto stop", "Auto shell",
                                          "Auto safe", "Auto reflect"])},
            "fieldeffect": {1 << i: e for i, e in
                            enumerate(["1/2 enc.", "No enc.", "", "", "",
                                       "Sprint", "", ""])},
            "otherproperties": {1 << i: e for i, e in
                                enumerate(["", "", "Procs", "Breaks", "", "", "", ""])}
        }
        return features[feature][feature_byte]

    def get_new_feature(self, feature, feature_byte, nochange):
        features = {
            "statboost1": {e: 1 << i for i, e in
                      enumerate(["Bat. Pwr +1/4", "Mag. Pwr +1/4", "+1/4 HP",
                      "+1/2 HP", "+1/8 HP", "+1/4 MP", "+1/2 MP", "+1/8 MP"])},
            "statboost2": {e: 1 << i for i, e in
                      enumerate(["Better Steal", "",
                      "Better Sketch","Better Control", "100% Hit Rate",
                      "1/2 MP Cost", "MP cost = 1", "Vigor +50%"])},
            "special1": {e: 1 << i for i, e in
                      enumerate(["Initiative", "Vigilance", "Command Changer",
                      "Command Changer", "Command Changer", "Command Changer",
                      "Command Changer", "Super Jump"])},
            "special2": {e: 1 << i for i, e in
                      enumerate(["Fight -> X-Fight", "Can counter",
                      "Random Evade", "Use weapon 2-handed",
                      "Can equip 2 weapons", "Can equip anything",
                      "Cover", "Step regen"])},
            "special3": {e: 1 << i for i, e in
                      enumerate(["Low HP Shell", "Low HP Safe", "Low HP Reflect",
                      "Double EXP", "Double GP",
                      "", "", "Reverses Cures"])},
            "statusprotect1": {e: 1 << i for i, e in
                      enumerate(["No dark", "No zombie", "No poison",
                      "No magitek", "No clear", "No imp",
                      "No petrify", "Death protection"])},
            "statusprotect2": {e: 1 << i for i, e in
                      enumerate(["No condemned", "Near fatal always",
                      "No image", "No mute", "No berserk", "No muddle",
                      "No seizure", "No sleep"])},
            "statusacquire2": {e: 1 << i for i, e in
                      enumerate(["Condemned", "Near fatal", "Image", "Mute",
                      "Berserk", "Muddle", "Seizure", "Sleep"])},
            "statusacquire3": {e: 1 << i for i, e in
                      enumerate(["Auto float", "Auto regen", "Auto slow",
                      "Auto haste", "Auto stop", "Auto shell",
                      "Auto safe", "Auto reflect"])},
            "fieldeffect": {e: 1 << i for i, e in
                      enumerate(["1/2 enc.", "No enc.", "", "", "",
                      "Sprint", "", ""])},
            "otherproperties": {e: 1 << i for i, e in
                      enumerate(["", "", "Procs", "Breaks", "", "", "", ""])}
        }

        try:
            FEATURE_FLAGS = features[feature]
        except KeyError:
            FEATURE_FLAGS = None

        # Comparing (v & feature_byte) to (v & nochange) appears to detect if the feature is a vanilla feature.
        # TODO: Adjust the string composition below so that procs and breaks can be handled differently.
        #  Procs and breaks need to check the spell used to determine if they are different than vanilla,
        #  otherwise items that break and proc in vanilla will not show up in the log even if they proc/break
        #  a different spell than in vanilla.
        if FEATURE_FLAGS:
            s = ", ".join([e for e, v in FEATURE_FLAGS.items()
                           if v & feature_byte == v and v & feature_byte != v & nochange])

        # Note that this doesn't catch an error if s is not defined.
        return s

    def mutate_feature(self, feature=None):
        if self.is_consumable or self.is_tool:
            return

        if feature is None:
            feature = random.choice(list(STATPROTECT.keys()))

        nochange = STATPROTECT[feature]
        if feature == 'special2':
            # Allow rare merit award bit on relics
            if self.is_relic:
                if random.randint(1, 10) == 10:
                    nochange &= ~0x20
            # Reduce chance of Genji Glove bit on non-relics
            elif random.randint(1, 4) != 4:
                nochange |= 0x10
        self.features[feature] = bit_mutate(self.features[feature], op="on",
                                            nochange=nochange)

        if not self.vanilla_data.features[feature] == self.features[feature]:
            self.mutate_name()

    def mutate_break_effect(self, always_break=False, wild_breaks=False, no_breaks=False, unbreakable=False):
        global effects_used
        if self.is_consumable:
            return

        if no_breaks:
            self.itemtype &= ~0x20
            return

        if unbreakable:
            self.features['otherproperties'] &= ~0x08
            return

        if always_break:
            effects_used = []

        success = False
        max_spellid = 0xFE if wild_breaks else 0x50
        for _ in range(100):
            spell, _ = self.pick_a_spell(custom=lambda x: x.spellid <= max_spellid)
            if spell.spellid not in effects_used:
                effects_used.append(spell.spellid)
                success = True
                break

        if not success:
            return

        # swdtechs, blitzes, superball, and slots don't seem to work
        # correctly with procs, but they work with breaks.
        # (Mostly they just play the wrong animation, but a couple
        # softlock.)
        no_proc_ids = list(range(0x55, 0x66)) + list(range(0x7D, 0x82))
        self.features['breakeffect'] = spell.spellid
        if not self.is_weapon or random.randint(1, 2) == 2 or always_break or spell.spellid in no_proc_ids:
            # always make armors usable in battle; weapons, only sometimes
            self.itemtype = self.itemtype | 0x20

        # flag to break when used as an item
        if random.randint(1, 20) == 20:
            self.features['otherproperties'] &= 0xF7
        else:
            self.features['otherproperties'] |= 0x08

        # flag to set chance to proc a spell
        if self.is_weapon and spell.spellid not in no_proc_ids and (
                not self.itemtype & 0x20 or random.randint(1, 2) == 2):
            self.features['otherproperties'] |= 0x04
        else:
            self.features['otherproperties'] &= 0xFB

        self.features['targeting'] = spell.targeting & 0xef
        self.mutate_name()

    def get_element(self, elem_byte, as_array=False):
        ELEM_FLAGS = {e: 1 << i for i, e in
                      enumerate(["fire", "ice", "lightning", "poison", "wind", "pearl", "earth", "water"])}
        s = [e for e, v in ELEM_FLAGS.items() if v & elem_byte == v]
        if as_array:
            return s
        else:
            return ", ".join(s)

    def mutate_elements(self):
        if self.is_consumable or self.is_tool:
            return

        def elemshuffle(elements):
            elemcount = bin(elements).count('1')
            while random.randint(1, 5) == 5:
                elemcount += random.choice([-1, 1])
            elemcount = max(0, min(elemcount, 8))
            elements = 0
            while elemcount > 0:
                elements = elements | (1 << random.randint(0, 7))
                elemcount += -1
            return elements

        # Attempt to shuffle weapon elemental damage and armor elemental half-damage
        self.features['elements'] = elemshuffle(self.features['elements'])

        # If the item is a weapon, it cannot have elemental weaknesses, nulls, or absorptions
        if not self.is_weapon:
            # Attempt to shuffle armor elemental absorption
            self.features['elemabsorbs'] = elemshuffle(self.features['elemabsorbs'])

            # Attempt to shuffle armor elemental nulls
            self.features['elemnulls'] = elemshuffle(self.features['elemnulls'])

            # Attempt to shuffle armor elemental weaknesses
            self.features['elemweaks'] = elemshuffle(self.features['elemweaks'])

        # If any changes occurred, mutate the item's name
        if not self.features['elements'] == self.vanilla_data.features['elements'] or \
           not self.features['elemabsorbs'] == self.vanilla_data.features['elemabsorbs'] or \
           not self.features['elemnulls'] == self.vanilla_data.features['elemnulls'] or \
           not self.features['elemweaks'] == self.vanilla_data.features['elemweaks']:
            self.mutate_name()

    def mutate_learning(self):
        if not self.is_armor and not self.is_relic:
            return

        spell, rank = self.pick_a_spell(magic_only=True)
        if self.degree:
            learnrate = self.degree
        else:
            learnrate = 0.25

        try:
            learnrate = int(learnrate / rank) + 1
            learnrate = min(learnrate, 5)
        except ZeroDivisionError:
            learnrate = 5

        self.features['learnrate'] = learnrate
        self.features['learnspell'] = spell.spellid
        if not self.vanilla_data.features['learnrate'] == self.features['learnrate'] or \
           not self.vanilla_data.features['learnspell'] == self.features['learnspell']:
            self.mutate_name()

    def get_specialaction(self, new_action):

        special_descriptions = ["Can steal", "Atma", "X-kill", "Man eater", "Drain HP", "Drain MP", "Uses some MP", "Random throw",
                                "Dice", "Valiant", "Wind Attack", "Heals Target", "Slice Kill", "Fragile wpn", "Uses more MP", ]
        s = special_descriptions[new_action-1]

        return s

    def mutate_special_action(self):
        if self.features['specialaction'] & 0xf0 != 0 or not self.is_weapon:
            return

        new_action = random.randint(1, 0xf)
        if new_action == 0xA:  # make random valiant knife effect rare
            new_action = random.randint(1, 0xf)

        if new_action == 9:  # no random dice effect
            return

        self.features['specialaction'] = (new_action << 4) | (self.features['specialaction'] & 0x0f)
        self.mutate_name()

    def mutate_stats(self):
        if self.is_consumable:
            return

        def mutate_power_hitmdef():
            diff = min(self.features['power'], 0xFF - self.features['power'])
            diff = diff // 3
            self.features['power'] = self.features['power'] - diff
            self.features['power'] = self.features['power'] + random.randint(0, diff) + random.randint(0, diff)
            self.features['power'] = int(min(0xFF, max(0, self.features['power'])))

            if "Dice" in self.name:
                return

            diff = min(self.features['hitmdef'], 0xFF - self.features['hitmdef'])
            diff = diff // 3
            self.features['hitmdef'] = self.features['hitmdef'] - diff
            self.features['hitmdef'] = self.features['hitmdef'] + random.randint(0, diff) + random.randint(0, diff)
            self.features['hitmdef'] = int(min(0xFF, max(0, self.features['hitmdef'])))

        mutate_power_hitmdef()
        while random.randint(0, 10) == 10:
            mutate_power_hitmdef()

        def mutate_nibble(byte, left=False, limit=7):
            if left:
                nibble = (byte & 0xf0) >> 4
                byte = byte & 0x0f
            else:
                nibble = byte & 0x0f
                byte = byte & 0xf0

            value = nibble & 0x7
            if nibble & 0x8:
                value = value * -1

            while random.randint(1, 6) == 6:
                value += random.choice([1, -1])

            value = max(-limit, min(value, limit))
            nibble = abs(value)
            if value < 0:
                nibble = nibble | 0x8

            if left:
                return byte | (nibble << 4)
            return byte | nibble

        self.features['speedvigor'] = mutate_nibble(self.features['speedvigor'])
        self.features['speedvigor'] = mutate_nibble(self.features['speedvigor'], left=True)
        self.features['magstam'] = mutate_nibble(self.features['magstam'])
        self.features['magstam'] = mutate_nibble(self.features['magstam'], left=True)

        evade, mblock = self.evade, self.mblock

        def evade_is_screwed_up(value):
            while random.randint(1, 8) == 8:
                if value == 0:
                    choices = [1, 6]
                elif value in [5, 0xA]:
                    choices = [-1]
                elif value == 6:
                    choices = [1, -6]
                else:
                    choices = [1, -1]
                value += random.choice(choices)
            return value

        evade = evade_is_screwed_up(evade)
        mblock = evade_is_screwed_up(mblock)
        self.features['mblockevade'] = evade | (mblock << 4)

    def mutate_price(self, undo_priceless=False, crazy_prices=False):
        if crazy_prices:
            if self.itemid == 250:
                self.price = random.randint(250, 500)
            else:
                self.price = random.randint(20, 500)
            return
        if self.price <= 2:
            if undo_priceless:
                self.price = self.rank()
            else:
                return

        normal = self.price // 2
        self.price += random.randint(0, normal) + random.randint(0, normal)
        while random.randint(1, 10) == 10:
            self.price += random.randint(0, normal) + random.randint(0, normal)

        zerocount = 0
        while self.price > 100:
            self.price = self.price // 10
            zerocount += 1

        while zerocount > 0:
            self.price = self.price * 10
            zerocount += -1

        self.price = min(self.price, 65000)

    def mutate(self, always_break=False, crazy_prices=False, extra_effects=False, wild_breaks=False, no_breaks=False, unbreakable=False):
        global changed_commands
        self.mutate_stats()
        self.mutate_price(crazy_prices=crazy_prices)
        broken, learned = False, False
        if always_break:
            self.mutate_break_effect(always_break=True, wild_breaks=wild_breaks)
            broken = True
        for command, itemids in list(break_unused_dict.items()):
            if command in changed_commands and self.itemid in itemids:
                self.mutate_break_effect(wild_breaks=wild_breaks)
                broken = True
        if self.itemid == 0xE6:
            self.mutate_learning()
            learned = True
        while random.randint(1, 5) == 5:
            x = random.randint(0, 99)
            if x < 10:
                self.mutate_special_action()
            if 10 <= x < 20 and not learned:
                self.mutate_learning()
            if 20 <= x < 50 and not broken:
                self.mutate_break_effect(wild_breaks=wild_breaks)
                broken = True
            if 50 <= x < 80:
                self.mutate_elements()
            if x >= 80:
                self.mutate_feature()
        if not self.heavy and random.randint(1, 20) == 20:
            self.heavy = True

        if extra_effects:
            if random.randint(1, 3) == 3:
                self.mutate_special_action()

            if random.randint(1, 2) == 2:
                self.mutate_feature()
            while random.randint(1, 3) == 3:
                self.mutate_feature()
        if no_breaks:
            self.mutate_break_effect(no_breaks=no_breaks)
        if unbreakable:
            self.mutate_break_effect(unbreakable=unbreakable)

    def mutate_name(self, vanilla=False):
        if vanilla:
            self.name = self.vanilla_data.name
            self.dataname[1:] = name_to_bytes(self.name, len(self.name))
        elif options.Options_.is_flag_active("questionablecontent") and not self.is_consumable and '?' not in self.name:
            self.name = self.name[:11] + '?'
            # Index on self.dataname is [1:] because the first character determines the
            #   equipment symbol (helmet/shield/etc).
            self.dataname[1:] = name_to_bytes(self.name, len(self.name))

    def rank(self):
        if self._rank:
            return self._rank

        if self.price > 10:
            return self.price

        bl = 0
        if self.is_consumable:
            baseline = 5000
            if self.features['otherproperties'] & 0x08:
                bl += 25
            if self.features['otherproperties'] & 0x10:
                bl += 75
            if self.features['otherproperties'] & 0x80:
                bl *= (self.features['power'] / 16.0) * 2
            if self.features['targeting'] & 0x20:
                bl *= 2
            if bl == 0 and self.features['specialaction']:
                bl += 50
        else:
            if self.imp_only:
                baseline = 0
            else:
                baseline = 25000 + random.randint(-5, 5)

            if not self.is_tool and not self.is_relic:
                power = self.features['power']
                if power < 2:
                    power = 250
                bl += power

                if self.evade in range(2, 6):
                    bl += (self.evade ** 2) * 25

                if self.mblock in range(2, 6):
                    bl += (self.mblock ** 2) * 25

                if self.evade == self.mblock == 1:
                    bl += 100

                if (self.is_armor and (self.features['elemabsorbs'] or
                                       self.features['elemnulls'] or
                                       self.features['elements'])):
                    void = (self.features['elemabsorbs'] |
                            self.features['elemnulls'])
                    bl += (100 * bin(void).count('1'))
                    bl += (25 * bin(self.features['elements']).count('1'))

            if self.features['statboost1'] & 0x4b:
                bl += 50

            if self.features['statboost2'] & 0x40:
                # Economizer
                bl += 1001

            if self.features['special1'] & 0x80:
                bl += 100

            if self.features['special1'] & 0x08:
                bl += 500

            if self.features['special2'] & 0x10:
                bl += 100

            if self.features['special2'] & 0x21:
                # Merit Award and Offering
                bl += 1000

            if self.features['specialaction'] & 0xf0 == 0xa0:
                # Valiant Knife
                bl += 1000

            if self.features['special3'] & 0x08:
                bl += 300

            if self.features['fieldeffect'] & 0x02:
                bl += 300

            if self.features['statusacquire3'] & 0xeb:
                bl += 100 * bin(self.features['statusacquire3']).count('1')

            if self.features['statusacquire2'] & 0xf9:
                bl += -50 * bin(self.features['statusacquire2']).count('1')

            if self.itemid == 0x66:
                # cursed shield
                bl += 666

            if self.itemid == 0x52:
                bl += 277

        baseline += (bl * 100)
        self._rank = int(baseline)
        return self.rank()


NUM_CHARS = 14
CHAR_MASK = 0x3fff
IMP_MASK = 0x4000
UMARO_ID = 13


def reset_equippable(items, characters, numchars=NUM_CHARS):
    global changed_commands
    prevents = [i for i in items if i.prevent_encounters]
    for item in prevents:
        while True:
            test = 1 << random.randint(0, numchars - 1)
            if item.itemid == 0xDE or not (CHAR_MASK & item.equippable):
                item.equippable = test
                break

            if test & item.equippable:
                test |= IMP_MASK
                item.equippable &= test
                break

    items = [i for i in items if not (i.is_consumable or i.is_tool or i.prevent_encounters)]
    new_weaps = list(range(numchars))
    random.shuffle(new_weaps)
    new_weaps = dict(list(zip(list(range(numchars)), new_weaps)))

    for item in items:
        if numchars == 14 and random.randint(1, 10) == 10:
            # for umaro's benefit
            item.equippable |= 0x2000

        if item.is_weapon:
            equippable = item.equippable
            item.equippable &= IMP_MASK
            for i in range(numchars):
                if equippable & (1 << i):
                    item.equippable |= (1 << new_weaps[i])
        elif item.is_relic:
            if random.randint(1, 15) == 15:
                item.equippable = 1 << (random.randint(0, numchars - 1))
                while random.randint(1, 3) == 3:
                    item.equippable |= (1 << (random.randint(0, numchars - 1)))
            else:
                item.equippable = CHAR_MASK

    charequips = []
    valid_items = [i for i in items
                   if (not i.is_weapon and not i.is_relic and not i.equippable & 0x4000)]
    for c in range(numchars):
        myequips = []
        for i in valid_items:
            if i.equippable & (1 << c):
                myequips.append(True)
            else:
                myequips.append(False)
        random.shuffle(myequips)
        charequips.append(myequips)

    for item in valid_items:
        item.equippable &= 0xc000

    random.shuffle(charequips)
    for c in range(numchars):
        assert len(valid_items) == len(charequips[c])
        for equippable, item in zip(charequips[c], valid_items):
            if equippable:
                item.equippable |= (1 << c)

    if random.randint(1, 3) == 3:
        weaponstoo = True
    else:
        weaponstoo = False

    for item in items:
        if item.equippable == 0:
            if not weaponstoo:
                continue
            item.equippable |= (1 << random.randint(0, numchars - 1))

    paladin_equippable = None
    for item in items:
        if item.itemid in [0x66, 0x67]:
            if paladin_equippable is not None:
                item.equippable = paladin_equippable
            else:
                paladin_equippable = item.equippable

    if 0x10 not in changed_commands:
        for item in items:
            if item.itemid == 0x1C:
                rage_chars = [c for c in characters if
                              0x10 in c.battle_commands]
                rage_mask = 0
                for c in rage_chars:
                    rage_mask |= (1 << c.id)
                rage_mask |= (1 << 12)  # gogo
                if item.equippable & rage_mask:
                    invert_rage_mask = 0xFFFF ^ rage_mask
                    item.equippable &= invert_rage_mask
                assert not item.equippable & rage_mask

    return items


sperelic = {0x04: (0x25456, 0x2545B),
            0x08: (0x25455, 0x2545A),
            0x10: (0x25454, 0x25459),
            0x20: (0x25453, 0x25458),
            0x40: (0x25452, 0x25457)}

sperelic2 = {0x04: (0x3619C, 0x361A1),
             0x08: (0x3619B, 0x361A0),
             0x10: (0x3619A, 0x3619F),
             0x20: (0x36199, 0x3619E),
             0x40: (0x36198, 0x3619D)}

invalid_commands = [0x00, 0x04, 0x14, 0x15, 0x19, 0xFF]


def reset_cursed_shield(fout):
    cursed = get_item(0x66)
    cursed.equippable = cursed.equippable & 0x0FFF
    cursed.write_stats(fout)


def reset_special_relics(items, characters, fout):
    global changed_commands
    characters = [c for c in characters if c.id < 14]
    changedict = {}
    loglist = []

    hidden_commands = set(range(0, 0x1E)) - set(invalid_commands)
    for c in characters:
        hidden_commands = hidden_commands - set(c.battle_commands)
    if 0x1D in hidden_commands and random.randint(1, 3) != 3:
        hidden_commands.remove(0x1D)

    flags = [0x04, 0x08, 0x10, 0x20, 0x40]
    random.shuffle(flags)
    for flag in flags:
        if changedict:
            donebefore, doneafter = tuple(zip(*list(changedict.values())))
            donebefore, doneafter = set(donebefore), set(doneafter)
        else:
            donebefore, doneafter = set([]), set([])
        while True:
            if flag == 0x08:
                candidates = set([0x0, 0x1, 0x2, 0x12])
            else:
                candidates = list(range(0, 0x1E))
                candidates = set(candidates) - set([0x04, 0x14, 0x15, 0x19])

            if random.randint(1, 5) != 5:
                candidates = candidates - donebefore

            candidates = sorted(candidates)
            before = random.choice(candidates)

            if before == 0:
                tempchars = [c for c in characters]
            else:
                tempchars = [c for c in characters if before in c.battle_commands]

            if not tempchars:
                continue

            unused = set(range(0, 0x1E)) - set(invalid_commands)
            if len(tempchars) <= 4:
                for t in tempchars:
                    unused = unused - set(t.battle_commands)

            if flag == 0x08:
                unused = unused - changed_commands

            if set(hidden_commands) & set(unused):
                unused = set(hidden_commands) & set(unused)

            if before in unused:
                unused.remove(before)

            if random.randint(1, 5) != 5:
                unused = unused - doneafter

            # Umaro can't get magic/x-magic.
            for t in tempchars:
                if t.id == UMARO_ID:
                    unused = unused - {0x02, 0x17}
                    break

            if not unused:
                continue

            after = random.choice(sorted(unused))
            if after in hidden_commands:
                hidden_commands.remove(after)

            for ptrdict in [sperelic, sperelic2]:
                beforeptr, afterptr = ptrdict[flag]
                fout.seek(beforeptr)
                fout.write(bytes([before]))
                fout.seek(afterptr)
                fout.write(bytes([after]))
            break
        changedict[flag] = (before, after)

    for item in items:
        if (item.is_consumable or item.is_tool or
                not item.features['special1'] & 0x7C):
            continue

        if item.itemid == 0x67:
            continue

        item.equippable &= IMP_MASK
        item.equippable |= 1 << 12  # gogo
        for flag in [0x04, 0x08, 0x10, 0x20, 0x40]:
            if flag & item.features['special1']:
                before, after = changedict[flag]
                tempchars = [c for c in characters
                             if before in c.battle_commands]
                for t in tempchars:
                    item.equippable |= (1 << t.id)

                item.write_stats(fout)
                loglist.append((item.name, before, after))

    return loglist


def reset_rage_blizzard(items, umaro_risk, fout):
    for item in items:
        if item.itemid not in [0xC5, 0xC6]:
            continue

        item.equippable = 1 << (umaro_risk.id)
        item.write_stats(fout)


def items_from_table(tablefile):
    items = []
    for line in open(tablefile):
        line = line.strip()
        if line[0] == '#':
            continue

        while '  ' in line:
            line = line.replace('  ', ' ')
        c = ItemBlock(*line.split(','))
        items.append(c)
    return items


def get_items(rom_file_buffer: BytesIO = None, allow_banned=False):
    global itemdict
    if itemdict:
        to_return = [i for i in list(itemdict.values()) if i]
        if not allow_banned:
            to_return = [i for i in to_return if not i.banned]
        return to_return

    items = items_from_table(ITEM_TABLE)
    for i in items:
        i.read_stats(rom_file_buffer)
        i.vanilla_data = deepcopy(i)

    for n, i in enumerate(items):
        i.set_degree(n / float(len(items)))
        itemdict[i.itemid] = i
    itemdict[0xFF] = None

    return get_items()


def get_item(itemid, allow_banned=False):
    global itemdict
    item = itemdict[itemid]
    if item and item.banned:
        if allow_banned:
            return item
        return None
    return item


def unbanItems():
    global itemdict
    try:
        for x in range(0, len(itemdict)):
            item = itemdict[x]
            if item != None:
                item.banned = False
    except Exception as e:
        traceback.print_exc()


def get_secret_item():
    item = get_item(0, allow_banned=True)
    if not item.banned:
        item = get_item(0xEF)
    return item


def get_ranked_items(rom_file_buffer: BytesIO = None, allow_banned=False):
    items = get_items(rom_file_buffer, allow_banned)
    return sorted(items, key=lambda i: i.rank())


def unhardcode_tintinabar(fout):
    # Apply Lenophis's unhardcoded tintinabar patch (solo version)
    tintinabar_sub = Substitution()
    tintinabar_sub.set_location(0x4A57)
    tintinabar_sub.bytestring = bytes(
        [0x89, 0x40, 0xF0, 0x5C, 0x29, 0x07, 0xCD, 0x6D, 0x1A, 0xD0, 0x55, 0x20, 0xE8, 0xAE, 0xB9, 0x14, 0x16, 0x89,
         0xC2, 0xD0, 0x4B, 0x20, 0x0D, 0xDF, 0xF0, 0x19, 0xB9, 0x1C, 0x16, 0x4A, 0x4A, 0xC2, 0x21, 0x29, 0xFF, 0x00,
         0x79, 0x09, 0x16, 0xC5, 0x1E, 0x90, 0x02, 0xA5, 0x1E, 0x99, 0x09, 0x16, 0x7B, 0xE2, 0x20, 0xB9, 0x14, 0x16,
         0x29, 0x04, 0xF0, 0x26, 0x7B, 0xA9, 0x0F, 0x8D, 0xF0, 0x11, 0xC2, 0x20, 0xEB, 0x8D, 0x96, 0x07, 0xC2, 0x20,
         0xA5, 0x1E, 0x4A, 0x4A, 0x4A, 0x4A, 0x4A, 0x85, 0x1E, 0xB9, 0x09, 0x16, 0x38, 0xE5, 0x1E, 0xF0, 0x02, 0xB0,
         0x02, 0x7B, 0x1A, 0x99, 0x09, 0x16, 0xC2, 0x21, 0x98, 0x69, 0x25, 0x00, 0xA8, 0x7B, 0xE2, 0x20, 0xE8, 0xE0,
         0x10, 0x00, 0xD0, 0x8D, 0xFA, 0x86, 0x24, 0xFA, 0x86, 0x22, 0xFA, 0x86, 0x20, 0xFA, 0x86, 0x1E, 0x28, 0x6B])
    tintinabar_sub.write(fout)

    tintinabar_sub.set_location(0x6CF8)
    tintinabar_sub.bytestring = bytes(
        [0x8C, 0x48, 0x14, 0x64, 0x1B, 0xB9, 0x67, 0x08, 0x0A, 0x10, 0x11, 0x4A, 0x29, 0x07, 0xCD, 0x6D, 0x1A, 0xD0,
         0x09, 0xA5, 0x1B, 0x22, 0x77, 0x0E, 0xC2, 0x20, 0xF6, 0xDE, 0xC2, 0x21, 0x98, 0x69, 0x29, 0x00, 0xA8, 0xE2,
         0x20, 0xE6, 0x1B, 0xC0, 0x90, 0x02, 0xD0, 0xD9, 0x7B, 0x60])
    tintinabar_sub.write(fout)

    tintinabar_sub.set_location(0xDEF6)
    tintinabar_sub.bytestring = bytes(
        [0xAD, 0xD8, 0x11, 0x10, 0x11, 0xA5, 0x1B, 0x5A, 0x1A, 0xA8, 0xC2, 0x20, 0x38, 0x7B, 0x2A, 0x88, 0xD0, 0xFC,
         0x0C, 0x48, 0x14, 0x7A, 0x60, 0x8C, 0x04, 0x42, 0xA9, 0x25, 0x8D, 0x06, 0x42, 0x22, 0xD4, 0x4A, 0xC0, 0x7B,
         0xAD, 0x14, 0x42, 0xDA, 0x1A, 0xAA, 0xC2, 0x20, 0x38, 0x7B, 0x2A, 0xCA, 0xD0, 0xFC, 0xFA, 0x2C, 0x48, 0x14,
         0xE2, 0x20, 0x60])
    tintinabar_sub.write(fout)

    tintinabar_sub.set_location(0x31DA9)
    tintinabar_sub.bytestring = bytes(
        [0x10, 0x03, 0x4C, 0x62, 0x2E, 0xA5, 0x09, 0x89, 0x02, 0xF0, 0x03, 0x4C, 0xC6, 0x2E, 0x10, 0x0F, 0x9C, 0x05,
         0x02, 0x20, 0xA9, 0x0E, 0x20, 0xC9, 0x1D, 0x7B, 0x3A, 0x85, 0x27, 0x64, 0x26, 0x60, 0x9C, 0xDF, 0x11, 0x9C,
         0x48, 0x14, 0x9C, 0x49, 0x14, 0xA2, 0x03, 0x00, 0xB5, 0x69, 0x30, 0x07, 0x22, 0x77, 0x0E, 0xC2, 0x20, 0x6C,
         0xF1, 0xCA, 0x10, 0xF2, 0x60, 0x00, 0xD0, 0xF0, 0x60])
    tintinabar_sub.write(fout)

    tintinabar_sub.set_location(0x3F16C)
    tintinabar_sub.bytestring = bytes(
        [0xAD, 0xD8, 0x11, 0x10, 0x12, 0x7B, 0xB5, 0x69, 0x1A, 0xA8, 0x38, 0x7B, 0xC2, 0x20, 0x2A, 0x88, 0xD0, 0xFC,
         0x0C, 0x48, 0x14, 0xE2, 0x20, 0x60])
    tintinabar_sub.write(fout)
