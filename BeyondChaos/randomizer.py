#!/usr/bin/env python3
from hashlib import md5
import os
import re
from io import BytesIO
from time import time, sleep, gmtime
from typing import Callable, Dict, List, Set, Tuple
from multiprocessing import Pipe, Process


import locationrandomizer
import options
from monsterrandomizer import MonsterBlock, early_bosses, solo_bosses
from randomizers.characterstats import CharacterStats
from ancient import manage_ancient
from appearance import manage_character_appearance, manage_coral
from character import get_characters, get_character, equip_offsets, character_list, load_characters
from bcg_junction import JunctionManager
from chestrandomizer import mutate_event_items, get_event_items
from config import (get_config_items, set_config_value, VERSION, VERSION_ROMAN, BETA, config, MD5HASHTEXTLESS2,
                    MD5HASHTEXTLESS, MD5HASHNORMAL)
from decompress import Decompressor
from dialoguemanager import (manage_dialogue_patches, get_dialogue,
                             set_dialogue, read_dialogue,
                             read_location_names, write_location_names)
from esperrandomizer import (get_espers, allocate_espers, randomize_magicite)
from formationrandomizer import (REPLACE_FORMATIONS, KEFKA_EXTRA_FORMATION,
                                 NOREPLACE_FORMATIONS, get_formations,
                                 get_fsets, get_formation, Formation,
                                 FormationSet)
from itemrandomizer import (reset_equippable, get_ranked_items, get_item,
                            reset_special_relics, reset_rage_blizzard,
                            reset_cursed_shield, unhardcode_tintinabar,
                            ItemBlock)
from locationrandomizer import (get_locations, get_location, get_zones,
                                get_npcs, randomize_forest, NPCBlock)
from monsterrandomizer import (REPLACE_ENEMIES, MonsterGraphicBlock, get_monsters,
                               get_metamorphs, get_ranked_monsters,
                               shuffle_monsters, get_monster, read_ai_table,
                               change_enemy_name, randomize_enemy_name,
                               get_collapsing_house_help_skill)
from myselfpatches import myself_patches
from musicinterface import randomize_music, manage_opera, get_music_spoiler, music_init, get_opera_log
from options import ALL_MODES, NORMAL_FLAGS, Options_
from patches import (
    allergic_dog, banon_life3, evade_mblock, death_abuse, no_kutan_skip,
    show_coliseum_rewards, cycle_statuses, no_dance_stumbles, fewer_flashes,
    change_swdtech_speed, change_cursed_shield_battles, sprint_shoes_break,
    apply_namingway, improved_party_gear, patch_doom_gaze,
    nicer_poison, fix_xzone, imp_skimp, fix_flyaway, hidden_relic, y_equip_relics,
    fix_gogo_portrait, vanish_doom, stacking_immunities, mp_color_digits,
    can_always_access_esper_menu, alphabetized_lores, description_disruption,
    informative_miss, improved_equipment_menus, verify_randomtools_patches, slow_background_scrolling,
    shadow_stays, level_cap, mp_refills, item_return_buffer_fix, mastered_espers)
from shoprandomizer import (get_shops, buy_owned_breakable_tools)
from sillyclowns import randomize_passwords, randomize_poem
from skillrandomizer import (SpellBlock, CommandBlock, SpellSub, ComboSpellSub,
                             RandomSpellSub, MultipleSpellSub, ChainSpellSub,
                             get_ranked_spells, get_spell)
from towerrandomizer import randomize_tower
from utils import (COMMAND_TABLE, LOCATION_TABLE, LOCATION_PALETTE_TABLE,
                   FINAL_BOSS_AI_TABLE, SKIP_EVENTS_TABLE, DANCE_NAMES_TABLE,
                   DIVERGENT_TABLE,
                   get_long_battle_text_pointer,
                   Substitution, shorttexttable, name_to_bytes,
                   hex2int, int2bytes, read_multi, write_multi,
                   generate_swapfunc, shift_middle, get_palette_transformer,
                   battlebg_palettes, set_randomness_multiplier,
                   mutate_index, utilrandom as random, open_mei_fallback,
                   AutoLearnRageSub, pipe_print, set_parent_pipe)
from wor import manage_wor_recruitment, manage_wor_skip
from random import Random
from patch_title import title_gfx
from remonsterate.remonsterate import remonsterate


NEVER_REPLACE = ['fight', 'item', 'magic', 'row', 'def', 'magitek', 'lore',
                 'jump', 'mimic', 'xmagic', 'summon', 'morph', 'revert']
RESTRICTED_REPLACE = ['throw', 'steal']
ALWAYS_REPLACE = ['leap', 'possess', 'health', 'shock']
FORBIDDEN_COMMANDS = ['leap', 'possess']
TEK_SKILLS = (  # [0x18, 0x6E, 0x70, 0x7D, 0x7E] +
        list(range(0x86, 0x8B)) + [0xA7, 0xB1] +
        list(range(0xB4, 0xBA)) +
        [0xBF, 0xCD, 0xD1, 0xD4, 0xD7, 0xDD, 0xE3])
JUNCTION_MANAGER_PARAMETERS = {
    'morpher-index': 0x0,
    'berserker-index': 0xd,
    'monster-equip-steal-enabled': 0,
    'monster-equip-drop-enabled': 0,
    'esper-allocations-address': 0x3f858,
}


seed_counter = 1
# seed = None
flags = None
# infile_rom_path = None
# outfile_rom_path = None
# infile_rom_buffer = None
# outfile_rom_buffer = None
# gui_connection = None
name_location_dict = {}
changed_commands = set([])
randomizer_log = {}


def log(text: str, section: str | None):
    """
    Helps build the randomizer_log dict by appending text to the randomizer_log[section] key.
    """
    global randomizer_log
    if section not in randomizer_log:
        randomizer_log[section] = []
    if '\n' in text:
        text = text.split('\n')
        text = '\n'.join([line.rstrip() for line in text])
    text = text.strip()
    randomizer_log[section].append(text)


def get_log_string(ordering: List = None) -> str:
    global randomizer_log
    log_string = ''
    if ordering is None:
        ordering = sorted([order for order in randomizer_log if order is not None])
    ordering = [order for order in ordering if order is not None]

    for data in randomizer_log[None]:
        log_string += data + '\n'

    log_string += '\n'
    sections_with_content = []
    for section in ordering:
        if section in randomizer_log:
            sections_with_content.append(section)
            log_string += '-{0:02d}- {1}\n'.format(len(sections_with_content),
                                                   ' '.join(
                                                       [word.capitalize() for word in str(section).split()]))
    for section_num, section in enumerate(sections_with_content):
        datas = sorted(randomizer_log[section])
        log_string += '\n' + '=' * 60 + '\n'
        log_string += '-{0:02d}- {1}\n'.format(section_num + 1, section.upper())
        log_string += '-' * 60 + '\n'
        newlines = False
        if any('\n' in data for data in datas):
            log_string += '\n'
            newlines = True
        for data in datas:
            log_string += data.strip() + '\n'
            if newlines:
                log_string += '\n'
    return log_string.strip()


def log_chests():
    """
    Appends the Treasure Chests section to the spoiler log.
    """
    area_chests = {}
    event_items = get_event_items()
    for location in get_locations():
        if not location.chests:
            continue
        if location.area_name not in area_chests:
            area_chests[location.area_name] = ''
        area_chests[location.area_name] += location.chest_contents + '\n'
    for area_name in event_items:
        if area_name not in area_chests:
            area_chests[area_name] = ''
        area_chests[area_name] += '\n'.join([event.description for event in event_items[area_name]])
    for area_name in sorted(area_chests):
        chests = area_chests[area_name]
        chests = '\n'.join(sorted(chests.strip().split('\n')))
        chests = area_name.upper() + '\n' + chests.strip()
        log(chests, section='treasure chests')


def log_item_mutations():
    """
    Appends the Item Magic section to the spoiler log.
    """
    items = sorted(get_ranked_items(), key=lambda item: item.name)
    breakable = [item for item in items if not item.is_consumable and item.itemtype & 0x20]
    log_string = 'BREAKABLE ITEMS\n---------------------------\n'
    for item in breakable:
        spell = get_spell(item.features['breakeffect'])
        indestructible = not item.features['otherproperties'] & 0x08
        log_string += '{0:15}{1}'.format(item.name + ':', spell.name)
        if indestructible:
            log_string += ' (indestructible)'
        log_string += '\n'
    log(log_string, 'item magic')

    log_string = 'SPELL-TEACHING ITEMS\n---------------------------\n'
    learnable = [item for item in items if item.features['learnrate'] > 0]
    for item in learnable:
        spell = get_spell(item.features['learnspell'])
        rate = item.features['learnrate']
        log_string += '{0:15}{1} x{2}\n'.format(item.name + ':', spell.name, rate)
    log(log_string, 'item magic')

    log_string = 'ITEM PROCS\n---------------------------\n'
    proc_items = [item for item in items if item.is_weapon and item.features['otherproperties'] & 0x04]
    for item in proc_items:
        spell = get_spell(item.features['breakeffect'])
        log_string += '{0:15}{1}\n'.format(item.name + ':', spell.name)
    log(log_string, 'item magic')

    '''
    Appends the Item Effects section to the spoiler log.
    '''
    log_string = 'SPECIAL FEATURES\n---------------------------\n'
    feature_types = ['fieldeffect', 'statusprotect1', 'statusprotect2', 'statusacquire3',
                     'statboost1', 'special1', 'statboost2', 'special2', 'special3',
                     'statusacquire2']
    # Currently Special Features can only be gained, not lost, so there's no reason to specify
    #   whether a feature was gained or lost. The commented portion of the below code should support
    #   losing special features, if that is implemented in the future.
    for item in items:
        gains = []
        # losses = []
        if item.is_weapon or item.is_armor or item.is_relic:
            for feature_type in feature_types:
                if item.vanilla_data.features[feature_type] == item.features[feature_type]:
                    continue

                for index, bits in enumerate(zip(bin(item.features[feature_type])[2:].zfill(8),
                                                 bin(item.vanilla_data.features[feature_type])[2:].zfill(8))):
                    if int(bits[0]) and not int(bits[1]):
                        # Feature was added - get the new feature from the mutated features
                        feature_name = item.get_feature(feature_type, int(bits[0]) << 7 - index)
                        if feature_name and not feature_name == 'Command Changer':
                            gains.append(feature_name.capitalize())
                    # elif not int(bits[0]) and int(bits[1]):
                    #     # Feature was removed - get the original feature from the vanilla features
                    #     feature_name = item.get_feature(feature_type, int(bits[1]) << 7 - index)
                    #     if feature_name and not feature_name == 'Command Changer':
                    #         losses.append(feature_name.capitalize())

        if gains:
            # log_string += '\tGained Special Feature(s): ' + ', '.join(gains) + '\n'
            log_string += '{0:15}{1}\n'.format(item.name + ':', ', '.join(gains))

        # if losses:
        #     log_string += '\tLost Special Feature(s): ' + ', '.join(losses) + '\n'

        # log_string += '\n'
    log(log_string, 'item effects')

    log_string = 'SPECIAL ACTIONS\n---------------------------\n'
    # Currently Special Actions can only be gained, and only by items that do not already have a special
    #   action. The commented code below should support the loss of special actions, if that is ever implemented.
    for item in items:
        if not item.vanilla_data.features['specialaction'] == item.features['specialaction']:
            # old_special_action = int(item.vanilla_data.features['specialaction']) >> 4
            new_special_action = int(item.features['specialaction']) >> 4

            if new_special_action:
                # log_string += '\tGained Special Action: ' +
                #               item.get_specialaction(new_special_action) + '\n'
                log_string += '{0:15}{1}\n'.format(item.name + ':', item.get_specialaction(new_special_action))

            # if old_special_action:
            #     log_string += '\tLost Special Action: ' +
            #                  item.get_specialaction(old_special_action) + '\n'
    log(log_string, 'item effects')

    log_string = 'ELEMENTAL PROPERTIES\n---------------------------\n'
    elemental_properties = {
        'elements': 'Elemental Dmg/Res',
        'elemabsorbs': 'Elemental Absorption',
        'elemnulls': 'Elemental Nullification',
        'elemweaks': 'Elemental Weakness'
    }

    for item in items:
        new_item = True
        for property_name, friendly_property_name in elemental_properties.items():
            if item.vanilla_data.features[property_name] == item.features[property_name]:
                continue

            gains = []
            losses = []

            for index, bits in enumerate(zip(bin(item.features[property_name])[2:].zfill(8),
                                             bin(item.vanilla_data.features[property_name])[2:].zfill(8))):
                if int(bits[0]) and not int(bits[1]):
                    # Element was added - get the new element from the mutated features
                    element_name = item.get_element(int(bits[0]) << 7 - index)
                    gains.append(element_name.capitalize())
                elif not int(bits[0]) and int(bits[1]):
                    # Element was removed - get the original element from the vanilla features
                    element_name = item.get_element(int(bits[1]) << 7 - index)
                    losses.append(element_name.capitalize())

                if property_name == 'elements':
                    if item.is_weapon:
                        friendly_property_name = 'Elemental Damage'
                    else:
                        friendly_property_name = 'Elemental Half-Damage'

                if new_item and (gains or losses):
                    log_string += item.name + ':'
                    new_item = False

                if gains:
                    # log_string += '\n\tGained ' + friendly_property_name + ': ' + ', '.join(gains)
                    log_string += '\n{0:8}{1}{2}'.format('', 'Gained ' +
                                                         friendly_property_name + ': ', ', '.join(gains))
                    gains = []

                if losses:
                    # log_string += '\n\tLost ' + friendly_property_name + ': ' + ', '.join(losses)
                    log_string += '\n{0:8}{1}{2}'.format('', 'Lost ' +
                                                         friendly_property_name + ': ', ', '.join(losses))
                    losses = []
        if not new_item:
            log_string = log_string + '\n'
    log(log_string, 'item effects')


def rng_state() -> int:
    state = sum(random.getstate()[1])
    return state


def reset():
    global seed_counter
    seed_counter = 0


def reseed():
    global seed_counter
    global seed
    random.seed(seed + seed_counter)
    seed_counter += (seed_counter * 2) + 1


def rewrite_title(text: str):
    """
    Rewrites text in opening credits.
    """
    while len(text) < 20:
        text += ' '
    text = text[:20]
    outfile_rom_buffer.seek(0xFFC0)
    outfile_rom_buffer.write(bytes(text, encoding='ascii'))
    outfile_rom_buffer.seek(0xFFDB)
    # Regex gets the first number in the VERSION - the major version number
    outfile_rom_buffer.write(bytes([int(re.search(r'\d', VERSION).group())]))


def rewrite_checksum():
    # This assumes the file is 32, 40, 48, or 64 Mbit.
    megabit = 0x20000
    outfile_rom_buffer.seek(0, 2)
    file_megabits = outfile_rom_buffer.tell() // megabit
    outfile_rom_buffer.seek(0)
    sub_sums = [sum(outfile_rom_buffer.read(megabit)) for _ in range(file_megabits)]
    while len(sub_sums) % 32:
        sub_sums.extend(sub_sums[32:file_megabits])
        if len(sub_sums) > 64:
            sub_sums = sub_sums[:64]
    checksum = sum(sub_sums) & 0xFFFF
    outfile_rom_buffer.seek(0xFFDE)
    write_multi(outfile_rom_buffer, checksum, length=2)
    outfile_rom_buffer.seek(0xFFDC)
    write_multi(outfile_rom_buffer, checksum ^ 0xFFFF, length=2)
    if file_megabits > 32:
        outfile_rom_buffer.seek(0x40FFDE)
        write_multi(outfile_rom_buffer, checksum, length=2)
        outfile_rom_buffer.seek(0x40FFDC)
        write_multi(outfile_rom_buffer, checksum ^ 0xFFFF, length=2)


class AutoRecruitGauSub(Substitution):
    @property
    def bytestring(self) -> bytes:
        return bytes([0x50, 0xBC, 0x59, 0x10, 0x3F,
                      0x0B, 0x01, 0xD4, 0xFB, 0xB8, 0x49, 0xFE])

    def write(self, stays_in_wor: bool):
        sub_addr = self.location - 0xa0000
        call_recruit_sub = Substitution()
        call_recruit_sub.bytestring = bytes([0xB2]) + int2bytes(sub_addr, length=3)
        call_recruit_sub.set_location(0xBC19C)
        call_recruit_sub.write(outfile_rom_buffer)

        if stays_in_wor:
            gau_stays_wor_sub = Substitution()
            gau_stays_wor_sub.bytestring = bytes([0xD4, 0xFB])
            gau_stays_wor_sub.set_location(0xA5324)
            gau_stays_wor_sub.write(outfile_rom_buffer)

        if Options_.is_flag_active('shuffle_commands') or Options_.is_flag_active('replace_commands'):
            REPLACE_ENEMIES.append(0x172)
        super(AutoRecruitGauSub, self).write(outfile_rom_buffer, noverify=True)


class FreeBlock:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    @property
    def size(self) -> int:
        return self.end - self.start

    def unfree(self, start: int, length: int) -> List:
        end = start + length
        if start < self.start:
            raise Exception('Used space out of bounds (left)')
        if end > self.end:
            raise Exception('Used space out of bounds (right)')
        newfree = []
        if self.start != start:
            newfree.append(FreeBlock(self.start, start))
        if end != self.end:
            newfree.append(FreeBlock(end, self.end))
        self.start, self.end = None, None
        return newfree


def get_appropriate_free_space(free_spaces: List[FreeBlock],
                               size: int,
                               minimum_address: int = None) -> FreeBlock:
    if minimum_address:
        candidates = [free_space for free_space in free_spaces if
                      free_space.size >= size and
                      free_space.start >= minimum_address]
    else:
        candidates = [free_space for free_space in free_spaces if free_space.size >= size]

    if not candidates:
        raise MemoryError('Not enough free space')

    candidates = sorted(candidates, key=lambda free_space: free_space.size)
    return candidates[0]


def determine_new_free_spaces(free_spaces: List[FreeBlock],
                              myfs: FreeBlock, size: int) -> List:
    free_spaces.remove(myfs)
    fss = myfs.unfree(myfs.start, size)
    free_spaces.extend(fss)
    return free_spaces


# Based on a document called Ending_Cinematic_Relocation_Notes
def relocate_ending_cinematic_data(data_blk_dst):
    cinematic_data_addr, cinematic_data_length = 0x28A70, 7145
    # All the LDAs
    relocate_locations = [
        0x3C703, 0x3C716, 0x3C72A, 0x3C73D, 0x3C751, 0x3C75C, 0x3C767, 0x3C772,
        0x3C77D, 0x3C788, 0x3C7B1, 0x3C80F, 0x3C833, 0x3C874, 0x3C8C5, 0x3C8F3,
        0x3CA10, 0x3CA30, 0x3CA57, 0x3CA80, 0x3CC65, 0x3CD59, 0x3CD6E, 0x3CEC9,
        0x3CF7C, 0x3CFB5, 0x3CFCA, 0x3D018, 0x3D023, 0x3D045, 0x3D050, 0x3D173,
        0x3D17E, 0x3D189, 0x3D194, 0x3D19F, 0x3D1AA, 0x3D970, 0x3D97B, 0x3D986,
        0x3D991, 0x3D99C, 0x3D9A7, 0x3D9B2, 0x3D9BD, 0x3D9C8, 0x3D9D3, 0x3D9DE,
        0x3D9E9, 0x3DA09, 0x3DA14, 0x3DA1F, 0x3DA2A, 0x3DA35, 0x3DA40, 0x3DA4B,
        0x3DA56, 0x3DA61, 0x3DA6C, 0x3DA77, 0x3DA82, 0x3DA8D, 0x3DA98, 0x3DAA3,
        0x3DAAE, 0x3DAB9, 0x3DAC4, 0x3DACF, 0x3DADA, 0x3DAE5, 0x3DAF0, 0x3DAFB,
        0x3DB06, 0x3DB11, 0x3DB1C, 0x3DB27, 0x3DB32, 0x3DB3D, 0x3DB48, 0x3DB53,
        0x3DB5E, 0x3DB69, 0x3DB74, 0x3DB7F, 0x3DB8A, 0x3DB95, 0x3DBA0, 0x3DD33,
        0x3E05D, 0x3E07C, 0x3E192, 0x3E1A5, 0x3E1B8, 0x3E1CB, 0x3E1DF, 0x3E1F2,
        0x3E22D, 0x3E28A, 0x3E468, 0x3E4BF, 0x3E773, 0x3E8B1, 0x3E98D, 0x3E9C1,
        0x3ED8D, 0x3EDA2, 0x3EDB7, 0x3EE6A, 0x3D286,
        # Be careful here, you want to change only the C2 part of each of these
        # five loads to the new bank (the last byte of the command).
        0x3D4A1, 0x3E032, 0x3E03A, 0x3E042, 0x3E04A,
    ]

    # Currently this is only a bank move, if we move it to a different offset
    # there are probably other instructions we have to change
    assert data_blk_dst & 0xFFFF == 0x8A70, 'Can only change bank, not offset, of cinematic data'
    new_dst_bnk = data_blk_dst >> 16

    # copy data block
    outfile_rom_buffer.seek(cinematic_data_addr)
    copy_sub = Substitution()
    copy_sub.bytestring = bytes(outfile_rom_buffer.read(cinematic_data_length))
    copy_sub.set_location(data_blk_dst - 0xC00000)
    copy_sub.write(outfile_rom_buffer)

    # Blank the data in the newly free'd block
    copy_sub.set_location(cinematic_data_addr)
    copy_sub.bytestring = b'\x00' * cinematic_data_length
    copy_sub.write(outfile_rom_buffer)

    # Change load instructions to use new bank
    # LDA #$C2 -> LDA #$xx
    for addr in relocate_locations[:-5]:
        copy_sub.set_location(addr + 1)
        copy_sub.bytestring = bytes([new_dst_bnk])
        copy_sub.write(outfile_rom_buffer)

    # LDA $C2____,X -> LDA $xx____,X
    for addr in relocate_locations[-5:]:
        copy_sub.set_location(addr + 3)
        copy_sub.bytestring = bytes([new_dst_bnk])
        copy_sub.write(outfile_rom_buffer)

    return FreeBlock(cinematic_data_addr,
                     cinematic_data_addr + cinematic_data_length)


class WindowBlock:
    def __init__(self, window_id: int):
        self.pointer = 0x2d1c00 + (window_id * 0x20)
        self.palette = [(0, 0, 0)] * 8
        self.negation_bit = 0

    def read_data(self):
        infile_rom_buffer.seek(self.pointer)
        self.palette = []
        if Options_.is_flag_active('christmas'):
            self.palette = [(0x1c, 0x02, 0x04)] * 2 + [(0x19, 0x00, 0x06)] * 2 + [(0x03, 0x0d, 0x07)] * 2 + [
                (0x18, 0x18, 0x18)] + [(0x04, 0x13, 0x0a)]
        elif Options_.is_flag_active('halloween'):
            self.palette = [(0x04, 0x0d, 0x15)] * 2 + [(0x00, 0x00, 0x00)] + [(0x0b, 0x1d, 0x15)] + [
                (0x00, 0x11, 0x00)] + [(0x1e, 0x00, 0x00)] + [(0x1d, 0x1c, 0x00)] + [(0x1c, 0x1f, 0x1b)]
        else:
            for _ in range(0x8):
                color = read_multi(infile_rom_buffer, length=2)
                blue = (color & 0x7c00) >> 10
                green = (color & 0x03e0) >> 5
                red = color & 0x001f
                self.negation_bit = color & 0x8000
                self.palette.append((red, green, blue))

    def write_data(self):
        outfile_rom_buffer.seek(self.pointer)
        for (red, green, blue) in self.palette:
            color = (blue << 10) | (green << 5) | red
            write_multi(outfile_rom_buffer, color, length=2)

    def mutate(self):
        if Options_.is_flag_active('halloween'):
            return

        def cluster_colors(colors: List) -> List:
            def distance(cluster_d: List, value: tuple) -> int:
                average = sum([sum(cluster_d) for (index_d, cluster_d) in cluster_d]) / len(cluster_d)
                return int(abs(sum(value) - average))

            clusters_cc = [{colors[0]}]
            colors = colors[1:]

            if random.randint(1, 3) != 3:
                index_cc = random.randint(1, len(colors) - 3)
                clusters_cc.append({colors[index_cc]})
                colors.remove(colors[index_cc])

            clusters_cc.append({colors[-1]})
            colors = colors[:-1]

            for index_cc2, color in colors:
                ideal = min(clusters_cc, key=lambda clusters_cc2: distance(clusters_cc2, color))
                ideal.add((index_cc2, color))

            return clusters_cc

        ordered_palette = list(zip(list(range(8)), self.palette))
        ordered_palette = sorted(ordered_palette, key=lambda i_c1: sum(i_c1[1]))
        new_palette = [None] * 8
        clusters = cluster_colors(ordered_palette)
        previous_darken = random.uniform(0.3, 0.9)
        for cluster in clusters:
            degree = random.randint(-75, 75)
            darken = random.uniform(previous_darken, min(previous_darken * 1.1, 1.0))

            def darkener(cluster_d):
                return int(round(cluster_d * darken))

            if Options_.is_flag_active('christmas'):
                def hue_swap(value):
                    return value
            else:
                hue_swap = generate_swapfunc()
            for index_m, clusters in sorted(cluster, key=lambda i_c: sum(i_c[1])):
                new_clusters = shift_middle(clusters, degree, ungray=True)
                new_clusters = list(map(darkener, new_clusters))
                new_clusters = hue_swap(new_clusters)
                new_palette[index_m] = tuple(new_clusters)
            previous_darken = darken

        self.palette = new_palette


def commands_from_table(tablefile: str) -> List:
    commands = []
    for index, line in enumerate(open(tablefile)):
        line = line.strip()
        if line[0] == '#':
            continue

        while '  ' in line:
            line = line.replace('  ', ' ')
        command = CommandBlock(*line.split(','))
        command.set_id(index)
        commands.append(command)
    return commands


def randomize_colosseum(pointer: int) -> List:
    item_objs = get_ranked_items(infile_rom_buffer)
    monster_objs = get_ranked_monsters(infile_rom_buffer, bosses=False)
    items = [item.itemid for item in item_objs]
    monsters = [monster.id for monster in monster_objs]
    results = []
    for index1 in range(0xFF):
        try:
            index2 = items.index(index1)
        except ValueError:
            continue
        trade = index2
        while index2 == trade:
            trade = index2
            while random.randint(1, 3) < 3:
                trade += random.randint(-3, 3)
                trade = max(0, min(trade, len(items) - 1))

        opponent = trade
        opponent = max(0, min(opponent, len(monsters) - 1))
        while random.randint(1, 3) < 3:
            opponent += random.randint(-1, 1)
            opponent = max(0, min(opponent, len(monsters) - 1))
        trade = items[trade]
        opponent = monsters[opponent]
        wager_obj = [item for item in item_objs if item.itemid == index1][0]
        opponent_obj = [monster for monster in monster_objs if monster.id == opponent][0]
        win_obj = [item for item in item_objs if item.itemid == trade][0]
        outfile_rom_buffer.seek(pointer + (index1 * 4))
        outfile_rom_buffer.write(bytes([opponent]))
        outfile_rom_buffer.seek(pointer + (index1 * 4) + 2)
        outfile_rom_buffer.write(bytes([trade]))

        if abs(wager_obj.rank() - win_obj.rank()) >= 5000 and random.randint(1, 2) == 2:
            hidden = True
            outfile_rom_buffer.write(b'\xFF')
        else:
            hidden = False
            outfile_rom_buffer.write(b'\x00')
        results.append((wager_obj, opponent_obj, win_obj, hidden))

    results = sorted(results, key=lambda a_b_c_d: a_b_c_d[0].name)

    if Options_.is_flag_active('fightclub'):
        coliseum_run_sub = Substitution()
        coliseum_run_sub.bytestring = [0xEA] * 2
        coliseum_run_sub.set_location(0x25BEF)
        coliseum_run_sub.write(outfile_rom_buffer)

    return results


def randomize_slots(pointer: int):
    spells = get_ranked_spells(infile_rom_buffer)
    spells = [spell for spell in spells if spell.spellid >= 0x36]
    attackspells = [spell for spell in spells if spell.target_enemy_default]
    quarter = len(attackspells) // 4
    eighth = quarter // 2
    jokerdoom = ((eighth * 6) +
                 random.randint(0, eighth) +
                 random.randint(0, eighth))
    jokerdoom += random.randint(0, len(attackspells) - (8 * eighth) - 1)
    jokerdoom = attackspells[jokerdoom]

    def get_slots_spell(index_gss: int) -> SpellBlock | None:
        index2 = None
        if index_gss in [0, 1]:
            return jokerdoom
        elif index_gss == 3:
            return None
        if index_gss in [4, 5, 6]:
            half = len(spells) // 2
            index2 = random.randint(0, half) + random.randint(0, half)
        elif index_gss == 2:
            third = len(spells) // 3
            index2 = random.randint(third, len(spells) - 1)
        elif index_gss == 7:
            twentieth = len(spells) // 20
            index2 = random.randint(0, twentieth)
            while random.randint(1, 3) == 3:
                index2 += random.randint(0, twentieth)
            index2 = min(index2, len(spells) - 1)

        spell = spells[index2]
        return spell

    slot_names = ['JokerDoom', 'JokerDoom', 'Dragons', 'Bars',
                  'Airships', 'Chocobos', 'Gems', 'Fail']
    used = []
    for index in range(1, 8):
        while True:
            spell = get_slots_spell(index)
            if spell is None or spell.spellid not in used:
                break
        if spell:
            from skillrandomizer import spellnames
            slot_string = '%s: %s' % (slot_names[index], spellnames[spell.spellid])
            log(slot_string, 'slots')
            used.append(spell.spellid)
            outfile_rom_buffer.seek(pointer + index)
            outfile_rom_buffer.write(bytes([spell.spellid]))


def auto_recruit_gau(stays_in_wor: bool):
    arg_sub = AutoRecruitGauSub()
    arg_sub.set_location(0xcfe1a)
    arg_sub.write(stays_in_wor)

    recruit_gau_sub = Substitution()
    recruit_gau_sub.bytestring = bytes([0x89, 0xFF])
    recruit_gau_sub.set_location(0x24856)
    recruit_gau_sub.write(outfile_rom_buffer)


def auto_learn_rage():
    alr_sub = AutoLearnRageSub(require_gau=False)
    alr_sub.set_location(0x23b73)
    alr_sub.write(outfile_rom_buffer)


def manage_commands(commands: Dict[str, CommandBlock]):
    """
    Takes in a dict of commands and randomizes them.

    Parameters
    ----------
    commands: a dictionary with the 30 default commands as
    string keys and CommandBlock values, e.g.:
    {'fight': <skillrandomizer.CommandBlock object at 0x0000020D06918760>,
     'item': <skillrandomizer.CommandBlock object at 0x0000020D06918640>,
     'magic': <skillrandomizer.CommandBlock object at 0x0000020D069188B0>,
     'morph': <skillrandomizer.CommandBlock object at 0x0000020D069188E0>,
     ...
     'possess': <skillrandomizer.CommandBlock object at 0x0000020D06918D60>,
     'magitek': <skillrandomizer.CommandBlock object at 0x0000020D06918D90>}
    """
    characters = get_characters()

    learn_lore_sub = Substitution()
    learn_lore_sub.bytestring = bytes([0xEA, 0xEA, 0xF4, 0x00, 0x00, 0xF4, 0x00, 0x00])
    learn_lore_sub.set_location(0x236E4)
    learn_lore_sub.write(outfile_rom_buffer)

    learn_dance_sub = Substitution()
    learn_dance_sub.bytestring = bytes([0xEA] * 2)
    learn_dance_sub.set_location(0x25EE8)
    learn_dance_sub.write(outfile_rom_buffer)

    learn_swdtech_sub = Substitution()
    learn_swdtech_sub.bytestring = bytes([0xEB,  # XBA
                                          0x48,  # PHA
                                          0xEB,  # XBA
                                          0xEA])
    learn_swdtech_sub.set_location(0x261C7)
    learn_swdtech_sub.write(outfile_rom_buffer)
    learn_swdtech_sub.bytestring = bytes([0x4C, 0xDA, 0xA1, 0x60])
    learn_swdtech_sub.set_location(0xA18A)
    learn_swdtech_sub.write(outfile_rom_buffer)

    learn_blitz_sub = Substitution()
    learn_blitz_sub.bytestring = bytes([0xF0, 0x09])
    learn_blitz_sub.set_location(0x261CE)
    learn_blitz_sub.write(outfile_rom_buffer)
    learn_blitz_sub.bytestring = bytes([0xD0, 0x04])
    learn_blitz_sub.set_location(0x261D3)
    learn_blitz_sub.write(outfile_rom_buffer)
    learn_blitz_sub.bytestring = bytes([0x68,  # PLA
                                        0xEB,  # XBA
                                        0xEA, 0xEA, 0xEA, 0xEA, 0xEA])
    learn_blitz_sub.set_location(0x261D9)
    learn_blitz_sub.write(outfile_rom_buffer)
    learn_blitz_sub.bytestring = bytes([0xEA] * 4)
    learn_blitz_sub.set_location(0x261E3)
    learn_blitz_sub.write(outfile_rom_buffer)
    learn_blitz_sub.bytestring = bytes([0xEA])
    learn_blitz_sub.set_location(0xA200)
    learn_blitz_sub.write(outfile_rom_buffer)

    learn_multiple_sub = Substitution()
    learn_multiple_sub.set_location(0xA1B4)
    reljump = 0xFE - (learn_multiple_sub.location - 0xA186)
    learn_multiple_sub.bytestring = bytes([0xF0, reljump])
    learn_multiple_sub.write(outfile_rom_buffer)

    learn_multiple_sub.set_location(0xA1D6)
    reljump = 0xFE - (learn_multiple_sub.location - 0xA18A)
    learn_multiple_sub.bytestring = bytes([0xF0, reljump])
    learn_multiple_sub.write(outfile_rom_buffer)

    learn_multiple_sub.set_location(0x261DD)
    learn_multiple_sub.bytestring = bytes([0xEA] * 3)
    learn_multiple_sub.write(outfile_rom_buffer)

    rage_blank_sub = Substitution()
    rage_blank_sub.bytestring = bytes([0x01] + ([0x00] * 31))
    rage_blank_sub.set_location(0x47AA0)
    rage_blank_sub.write(outfile_rom_buffer)

    # Let x-magic user use magic menu. Commented out as it's duplicated in Myself's patches
    #enable_xmagic_menu_sub = Substitution()
    #enable_xmagic_menu_sub.bytestring = bytes([0xDF, 0x78, 0x4D, 0xC3,  # CMP $C34D78,X
    #                                           0xF0, 0x07,  # BEQ
    #                                           0xE0, 0x01, 0x00,  # CPX #$0001
    #                                           0xD0, 0x02,  # BNE
    #                                           0xC9, 0x17,  # CMP #$17
    #                                           0x6b  # RTL
    #                                           ])
    #enable_xmagic_menu_sub.set_location(0x3F091)
    #enable_xmagic_menu_sub.write(outfile_rom_buffer)

    #enable_xmagic_menu_sub.bytestring = bytes([0x22, 0x91, 0xF0, 0xC3])
    #enable_xmagic_menu_sub.set_location(0x34d56)
    #enable_xmagic_menu_sub.write(outfile_rom_buffer)

    # Prevent Runic, SwdTech, and Capture from being disabled/altered
    protect_battle_commands_sub = Substitution()
    protect_battle_commands_sub.bytestring = bytes([0x03, 0xFF, 0xFF, 0x0C, 0x17, 0x02, 0xFF, 0x00])
    protect_battle_commands_sub.set_location(0x252E9)
    protect_battle_commands_sub.write(outfile_rom_buffer)

    enable_morph_sub = Substitution()
    enable_morph_sub.bytestring = bytes([0xEA] * 2)
    enable_morph_sub.set_location(0x25410)
    enable_morph_sub.write(outfile_rom_buffer)

    enable_mpoint_sub = Substitution()
    enable_mpoint_sub.bytestring = bytes([0xEA] * 2)
    enable_mpoint_sub.set_location(0x25E38)
    enable_mpoint_sub.write(outfile_rom_buffer)

    ungray_statscreen_sub = Substitution()
    ungray_statscreen_sub.bytestring = bytes([0x20, 0x6F, 0x61, 0x30, 0x26, 0xEA, 0xEA, 0xEA])
    ungray_statscreen_sub.set_location(0x35EE1)
    ungray_statscreen_sub.write(outfile_rom_buffer)

    fanatics_fix_sub = Substitution()
    if Options_.is_flag_active('metronome'):
        fanatics_fix_sub.bytestring = bytes([0xA9, 0x1D])
    else:
        fanatics_fix_sub.bytestring = bytes([0xA9, 0x15])
    fanatics_fix_sub.set_location(0x2537E)
    fanatics_fix_sub.write(outfile_rom_buffer)

    invalid_commands = ['fight', 'item', 'magic', 'xmagic',
                        'def', 'row', 'summon', 'revert']
    if random.randint(1, 5) != 5:
        invalid_commands.append('magitek')

    if not Options_.is_flag_active('replace_commands'):
        invalid_commands.extend(FORBIDDEN_COMMANDS)

    invalid_commands = {command for command in commands.values() if command.name in invalid_commands}

    def populate_unused():
        unused_commands = set(commands.values())
        unused_commands = unused_commands - invalid_commands
        return sorted(unused_commands, key=lambda command: command.name)

    unused = populate_unused()
    xmagic_taken = False
    random.shuffle(characters)
    for character in characters:
        if Options_.is_flag_active('shuffle_commands') or Options_.is_flag_active('replace_commands'):
            if character.id == 11:
                # Fixing Gau
                character.set_battle_command(0, commands['fight'])

        if Options_.is_flag_active('metronome'):
            character.set_battle_command(0, command_id=0)
            character.set_battle_command(1, command_id=0x1D)
            character.set_battle_command(2, command_id=2)
            character.set_battle_command(3, command_id=1)
            character.write_battle_commands(outfile_rom_buffer)
            continue

        if Options_.is_flag_active('collateraldamage'):
            character.set_battle_command(1, command_id=0xFF)
            character.set_battle_command(2, command_id=0xFF)
            character.set_battle_command(3, command_id=1)
            character.write_battle_commands(outfile_rom_buffer)
            continue

        if character.id <= 11:
            using = []
            while not using:
                if random.randint(0, 1):
                    using.append(commands['item'])
                if random.randint(0, 1):
                    if not xmagic_taken:
                        using.append(commands['xmagic'])
                        xmagic_taken = True
                    else:
                        using.append(commands['magic'])
            while len(using) < 3:
                if not unused:
                    unused = populate_unused()
                com = random.choice(unused)
                unused.remove(com)
                if com not in using:
                    using.append(com)
                    if com.name == 'morph':
                        invalid_commands.add(com)
                        morph_char_sub = Substitution()
                        morph_char_sub.bytestring = bytes([0xC9, character.id])
                        morph_char_sub.set_location(0x25E32)
                        morph_char_sub.write(outfile_rom_buffer, noverify=True)
                        JUNCTION_MANAGER_PARAMETERS['morpher-index'] = character.id
            for index, command in enumerate(reversed(using)):
                character.set_battle_command(index + 1, command=command)
        else:
            character.set_battle_command(1, command_id=0xFF)
            character.set_battle_command(2, command_id=0xFF)
        character.write_battle_commands(outfile_rom_buffer)

    magitek_skills = [SpellBlock(index, infile_rom_buffer) for index in range(0x83, 0x8B)]
    for ms in magitek_skills:
        ms.fix_reflect(outfile_rom_buffer)

    return commands


def manage_tempchar_commands():
    if Options_.is_flag_active('metronome'):
        return
    characters = get_characters()
    char_dict = {character_mtc.id: character_mtc for character_mtc in characters}
    basic_pool = set(range(3, 0x1E)) - changed_commands - {0x4, 0x11, 0x14, 0x15, 0x19}
    moogle_pool, banon_pool, ghost_pool, leo_pool = list(map(set, [basic_pool] * 4))
    for key in [0, 1, 0xA]:
        character_mtc = char_dict[key]
        moogle_pool |= set(character_mtc.battle_commands)
    for key in [4, 5]:
        character_mtc = char_dict[key]
        banon_pool |= set(character_mtc.battle_commands)
    ghost_pool = banon_pool | set(char_dict[3].battle_commands)
    for key in char_dict:
        character_mtc = char_dict[key]
        leo_pool |= set(character_mtc.battle_commands)
    pools = [banon_pool, leo_pool] + ([ghost_pool] * 2) + ([moogle_pool] * 10)
    banned = {0x0, 0x1, 0x2, 0x17, 0xFF}
    # Guest characters with Lore command will have an empty list, so make sure
    # they don't have it.
    if 0xC not in changed_commands:
        banned.add(0xC)
    for index, pool in zip(range(0xE, 0x1C), pools):
        pool = sorted([command for command in pool if command and command not in banned])
        sample1, sample2 = tuple(random.sample(pool, 2))
        char_dict[index].set_battle_command(1, command_id=sample1)
        char_dict[index].set_battle_command(2, command_id=sample2)
        char_dict[index].set_battle_command(3, command_id=0x1)
        char_dict[index].write_battle_commands(outfile_rom_buffer)

    for index in range(0xE, 0x1C):
        character_mtc = char_dict[index]
        if character_mtc.battle_commands[1] == 0xFF and character_mtc.battle_commands[2] != 0xFF:
            character_mtc.set_battle_command(1, command_id=character_mtc.battle_commands[2])
        if character_mtc.battle_commands[1] == character_mtc.battle_commands[2]:
            character_mtc.set_battle_command(2, command_id=0xFF)
        character_mtc.write_battle_commands(outfile_rom_buffer)


def manage_commands_new(commands: Dict[str, CommandBlock]):
    """
    Takes in a dict of commands and randomizes them.

    Parameters
    ----------
    commands: a dictionary with the 30 default commands as
    string keys and CommandBlock values, e.g.:
    {'fight': <skillrandomizer.CommandBlock object at 0x0000020D06918760>,
     'item': <skillrandomizer.CommandBlock object at 0x0000020D06918640>,
     'magic': <skillrandomizer.CommandBlock object at 0x0000020D069188B0>,
     'morph': <skillrandomizer.CommandBlock object at 0x0000020D069188E0>,
     ...
     'possess': <skillrandomizer.CommandBlock object at 0x0000020D06918D60>,
     'magitek': <skillrandomizer.CommandBlock object at 0x0000020D06918D90>}
    """
    # note: x-magic targets random party member
    # replacing lore screws up enemy skills
    # replacing jump makes the character never come back down
    # replacing mimic screws up enemy skills too
    get_characters()
    free_spaces = [FreeBlock(0x2A65A, 0x2A800),
                   FreeBlock(0x2FAAC, 0x2FC6D),
                   FreeBlock(0x28A70, 0x2A659)]
    # NOTE: This depends on using `relocate_cinematic_data`
    # once this is settled on, we can just prepend this to
    # the first free block above

    allow_ultima = not Options_.is_flag_active('penultima')
    multibanned_list = [0x63, 0x58, 0x5B]

    def multibanned(spells: List[SpellBlock]) -> List[SpellBlock] | bool:
        if isinstance(spells, int):
            return spells in multibanned_list
        spells = [spell_m for spell_m in spells if spell_m.spellid not in multibanned_list]
        return spells

    # valid = set(list(commands))
    # valid = sorted(valid - {'row', 'def'})
    used = []
    all_spells = get_ranked_spells(infile_rom_path)
    random_skill_names = set([])
    limit_counter = 0
    for command in commands.values():
        if command.name in NEVER_REPLACE:
            continue

        if not Options_.is_flag_active('replaceeverything'):
            if command.name in RESTRICTED_REPLACE and random.choice([True, False]):
                continue

            if command.name not in ALWAYS_REPLACE:
                if random.randint(1, 100) > 50:
                    continue

        changed_commands.add(command.id)
        rng_value = random.randint(1, 3)

        if Options_.is_flag_active('nocombos'):
            rng_value = random.randint(1, 2)

        if rng_value <= 1:
            random_skill = False
            combo_skill = False
        elif rng_value <= 2:
            random_skill = True
            combo_skill = False
        else:
            random_skill = False
            combo_skill = True

        if Options_.is_flag_active('allcombos'):
            random_skill = False
            combo_skill = True

        # force first skill to limit break
        if limit_counter != 1 and Options_.is_flag_active('desperation'):
            if Options_.is_flag_active('allcombos'):
                random_skill = False
                combo_skill = True
            else:
                random_skill = True
                combo_skill = False

        power_level = 130
        skill_count = 1
        while random.randint(1, 5) == 5:
            skill_count += 1
        skill_count = min(skill_count, 9)
        if Options_.is_flag_active('endless9'):
            skill_count = 9

        def get_random_power() -> int:
            base_power = power_level // 2
            new_power = base_power + random.randint(0, base_power)
            while True:
                new_power += random.randint(0, base_power)
                if random.choice([True, False]):
                    break
            return new_power

        spell = None
        new_name = ''
        while True:
            command.read_properties(infile_rom_buffer)
            if not (random_skill or combo_skill):
                power = get_random_power()

                def spell_is_valid(skill_siv) -> bool:
                    if not skill_siv.valid:
                        return False
                    if skill_siv.spellid in used:
                        return False
                    if skill_siv.name == 'Ultima' and not allow_ultima:
                        return False
                    return skill_siv.rank() <= power

                valid_spells = list(filter(spell_is_valid, all_spells))

                if Options_.is_flag_active('desperation'):
                    desperations = {
                        'Sabre Soul', 'Star Prism', 'Mirager', 'TigerBreak',
                        'Back Blade', 'Riot Blade', 'RoyalShock', 'Spin Edge',
                        'X-Meteo', 'Red Card', 'MoogleRush'
                    }
                    for spell in all_spells:
                        if spell.name in desperations and spell not in valid_spells:
                            valid_spells.append(spell)
                        elif spell.name == 'ShadowFang':
                            valid_spells.append(spell)

                if not valid_spells:
                    continue

                sb = random.choice(valid_spells)
                used.append(sb.spellid)
                command.targeting = sb.targeting
                command.targeting = command.targeting & (0xFF ^ 0x10)  # never autotarget
                if not command.targeting & 0x20 and random.randint(1, 15) == 15:
                    command.targeting = 0xC0  # target random individual (both sides)
                if not command.targeting & 0x20 and random.randint(1, 10) == 10:
                    command.targeting |= 0x28  # target random individual
                    command.targeting &= 0xFE
                if command.targeting & 0x08 and not command.targeting & 0x02 and random.randint(1, 5) == 5:
                    command.targeting = 0x04  # target everyone
                if not command.targeting & 0x64 and sb.spellid not in [0x30, 0x31] and random.randint(1, 5) == 5:
                    command.targeting = 2  # only target self
                if sb.spellid in [0xAB]:  # megazerk
                    command.targeting = random.choice([0x29, 0x6E, 0x6C, 0x27, 0x4])
                if sb.spellid in [0x2B]:  # quick
                    command.targeting = random.choice([0x2, 0x2A, 0xC0, 0x1])

                if command.targeting & 3 == 3:
                    command.targeting ^= 2  # allow targeting either side

                command.properties = 3
                if sb.spellid in [0x23, 0xA3]:
                    command.properties |= 0x4  # enable while imped
                command.unset_retarget(outfile_rom_buffer)
                command.write_properties(outfile_rom_buffer)

                if skill_count == 1 or multibanned(sb.spellid):
                    spell = SpellSub(spellid=sb.spellid)
                else:
                    if skill_count >= 4 or random.choice([True, False]):
                        spell = MultipleSpellSub()
                        spell.set_spells(sb.spellid, outfile_rom_buffer=outfile_rom_buffer)
                        spell.set_count(skill_count)
                    else:
                        spell = ChainSpellSub()
                        spell.set_spells(sb.spellid, outfile_rom_buffer=outfile_rom_buffer)

                new_name = sb.name
            elif random_skill:
                power = 10000
                command.properties = 3
                command.set_retarget(outfile_rom_buffer)
                valid_spells = [spell for spell in all_spells if
                                spell.spellid <= 0xED and spell.valid]
                if not allow_ultima:
                    valid_spells = [spell for spell in valid_spells if spell.name != 'Ultima']

                if Options_.is_flag_active('desperation'):
                    for spell in [spell for spell in all_spells if spell not in valid_spells and spell.is_desperation]:
                        valid_spells.append(spell)
                if skill_count == 1:
                    spell = RandomSpellSub()
                else:
                    valid_spells = multibanned(valid_spells)
                    if skill_count >= 4 or random.choice([True, False]):
                        spell = MultipleSpellSub()
                        spell.set_count(skill_count)
                    else:
                        spell = ChainSpellSub()

                try:
                    if limit_counter != 1 and Options_.is_flag_active('desperation'):
                        spell.set_spells(valid_spells, 'Limit', None, outfile_rom_buffer=outfile_rom_buffer)
                        limit_counter = limit_counter + 1
                    else:
                        limit_bad = True
                        spell.set_spells(valid_spells, outfile_rom_buffer=outfile_rom_buffer)
                        if spell.name == 'Dance':
                            spell.set_spells(all_spells, 'Dance', None, outfile_rom_buffer=outfile_rom_buffer)
                        while limit_bad:
                            if spell.name == 'Limit' and not Options_.is_flag_active('desperation'):
                                spell.set_spells(valid_spells, outfile_rom_buffer=outfile_rom_buffer)
                            else:
                                limit_bad = False
                except ValueError:
                    continue

                if spell.name != 'Limit':
                    if spell.name in random_skill_names:
                        continue
                random_skill_names.add(spell.name)
                command.targeting = 0x2
                if not spell.spells:
                    command.targeting = 0x4
                elif len({spell2.targeting for spell2 in spell.spells}) == 1:
                    command.targeting = spell.spells[0].targeting
                elif any([spell.target_everyone and not spell.target_one_side_only
                          for spell in spell.spells]):
                    command.targeting = 0x4
                else:
                    if not any([spell.target_enemy_default or (spell.target_everyone and not spell.target_one_side_only)
                                for spell in spell.spells]):
                        command.targeting = 0x2e
                    if all([spell.target_enemy_default for spell in spell.spells]):
                        command.targeting = 0x6e

                command.write_properties(outfile_rom_buffer)
                new_name = spell.name

            elif combo_skill:
                always_first = []
                always_last = ['Palidor', 'Quadra Slam', 'Quadra Slice', 'Spiraler',
                               'Pep Up', 'Exploder', 'Quick']
                weighted_first = ['Life', 'Life 2', ]
                weighted_last = ['ChokeSmoke', ]
                for mylist in [always_first, always_last,
                               weighted_first, weighted_last]:
                    assert (len([spell for spell in all_spells if spell.name in mylist]) == len(mylist))

                def spell_is_valid(spell_siv, power_siv) -> bool:
                    if not spell_siv.valid:
                        return False
                    if spell_siv.name == 'Ultima' and not allow_ultima:
                        return False
                    # if multibanned(s.spellid):
                    #    return False
                    return spell_siv.rank() <= power_siv

                my_spells = []
                targeting_conflict = None
                while len(my_spells) < 2:
                    power = get_random_power()
                    valid_spells = [spell for spell in all_spells
                                    if spell_is_valid(spell, power) and spell not in my_spells]

                    if Options_.is_flag_active('desperation'):
                        for spell in [spell for spell in all_spells if
                                      spell not in valid_spells and spell.is_desperation]:
                            valid_spells.append(spell)

                    if not valid_spells:
                        continue
                    my_spells.append(random.choice(valid_spells))
                    targeting_conflict = (len({spell.targeting & 0x40
                                               for spell in my_spells}) > 1)
                    names = {spell.name for spell in my_spells}
                    if len(names & set(always_first)) == 2 or len(names & set(always_last)) == 2:
                        my_spells = []
                    if targeting_conflict and all([spell.targeting & 0x10
                                                   for spell in my_spells]):
                        my_spells = []

                command.unset_retarget(outfile_rom_buffer)
                # if random.choice([True, False]):
                #    nopowers = [s for s in myspells if not s.power]
                #    powers = [s for s in myspells if s.power]
                #    myspells = nopowers + powers
                for spell in my_spells:
                    if spell.name in weighted_first and random.choice([True, False]):
                        my_spells.remove(spell)
                        my_spells.insert(0, spell)
                    if ((spell.name in weighted_last or
                         spell.target_auto or
                         spell.randomize_target or
                         spell.retargetdead or not
                         spell.target_group) and
                            random.choice([True, False])):
                        my_spells.remove(spell)
                        my_spells.append(spell)

                autotarget = [spell for spell in my_spells if spell.target_auto]
                noauto = [spell for spell in my_spells if not spell.target_auto]
                autotarget_warning = (0 < len(autotarget) < len(my_spells))
                if targeting_conflict:
                    my_spells = noauto + autotarget
                for spell in my_spells:
                    if spell.name in always_first:
                        my_spells.remove(spell)
                        my_spells.insert(0, spell)
                    if spell.name in always_last:
                        my_spells.remove(spell)
                        my_spells.append(spell)
                css = ComboSpellSub(my_spells)

                command.properties = 3
                command.targeting = 0
                for mask in [0x01, 0x40]:
                    for spell in css.spells:
                        if spell.targeting & mask:
                            command.targeting |= mask
                            break

                # If the first spell is single-target only, but the combo
                # allows
                # targeting multiple, it'll randomly pick one target and do
                # both
                # spells on that one.
                # So, only allow select multiple targets if the first one does.
                command.targeting |= css.spells[0].targeting & 0x20

                if css.spells[0].targeting & 0x40 == command.targeting & 0x40:
                    command.targeting |= (css.spells[0].targeting & 0x4)

                if all(spell.targeting & 0x08 for spell in css.spells) or command.targeting & 0x24 == 0x24:
                    command.targeting |= 0x08

                if all(spell.targeting & 0x02 for spell in css.spells) and not targeting_conflict:
                    command.targeting |= 0x02

                if targeting_conflict and command.targeting & 0x20:
                    command.targeting |= 1

                if targeting_conflict and random.randint(1, 10) == 10:
                    command.targeting = 0x04

                if command.targeting & 1 and not command.targeting & 8 and random.randint(1, 30) == 30:
                    command.targeting = 0xC0

                if command.targeting & 3 == 3:
                    command.targeting ^= 2  # allow targeting either side

                command.targeting = command.targeting & (0xFF ^ 0x10)  # never autotarget
                command.write_properties(outfile_rom_buffer)

                skill_count = max(1, skill_count - 1)
                if autotarget_warning and targeting_conflict:
                    skill_count = 1
                css.name = ''
                if skill_count >= 2:
                    if skill_count >= 4 or random.choice([True, False]):
                        new_s = MultipleSpellSub()
                        new_s.set_spells(css, outfile_rom_buffer=outfile_rom_buffer)
                        new_s.set_count(skill_count)
                    else:
                        new_s = ChainSpellSub()
                        new_s.set_spells(css, outfile_rom_buffer=outfile_rom_buffer)
                    if len(css.spells) == len(multibanned(css.spells)):
                        css = new_s

                if isinstance(css, (MultipleSpellSub, ChainSpellSub)):
                    namelengths = [3, 2]
                else:
                    namelengths = [4, 3]
                random.shuffle(namelengths)
                names = [spell.name for spell in css.spells]
                names = [name.replace('-', '') for name in names]
                names = [name.replace('.', '') for name in names]
                names = [name.replace(' ', '') for name in names]
                for index in range(2):
                    if len(names[index]) < namelengths[index]:
                        namelengths = list(reversed(namelengths))
                new_name = names[0][:namelengths[0]]
                new_name += names[1][:namelengths[1]]

                spell = css
            else:
                assert False
            break

        myfs = get_appropriate_free_space(free_spaces, spell.size)
        spell.set_location(myfs.start)
        if not hasattr(spell, 'bytestring') or not spell.bytestring:
            spell.generate_bytestring()
        spell.write(outfile_rom_buffer)
        command.setpointer(spell.location, outfile_rom_buffer)
        free_spaces = determine_new_free_spaces(free_spaces, myfs, spell.size)

        if len(new_name) > 7:
            new_name = new_name.replace('-', '')
            new_name = new_name.replace('.', '')

        if isinstance(spell, SpellSub):
            pass
        elif isinstance(spell, RandomSpellSub):
            new_name = 'R-%s' % new_name
        elif isinstance(spell, MultipleSpellSub):
            if spell.count == 2:
                new_name = 'W-%s' % new_name
            else:
                new_name = '%sx%s' % (spell.count, new_name)
        elif isinstance(spell, ChainSpellSub):
            new_name = '?-%s' % new_name

        # Disable menu screens for replaced commands.
        for index, name in enumerate(['swdtech', 'blitz', 'lore', 'rage', 'dance']):
            if command.name == name:
                outfile_rom_buffer.seek(0x34D7A + index)
                outfile_rom_buffer.write(b'\xEE')

        command.newname(new_name, outfile_rom_buffer)
        command.unsetmenu(outfile_rom_buffer)
        command.allow_while_confused(outfile_rom_buffer)
        if Options_.is_flag_active('playsitself'):
            command.allow_while_berserk(outfile_rom_buffer)
        else:
            command.disallow_while_berserk(outfile_rom_buffer)

        command_descr = '{0}\n-------\n{1}'.format(command.name, str(spell))
        log(command_descr, 'commands')

    if Options_.is_flag_active('metronome'):
        magitek = [command for command in commands.values() if command.name == 'magitek'][0]
        magitek.read_properties(infile_rom_buffer)
        magitek.targeting = 0x04
        magitek.set_retarget(outfile_rom_buffer)
        if Options_.is_flag_active('endless9'):
            spell = MultipleSpellSub()
            spell.set_count(9)
            magitek.newname('9xChaos', outfile_rom_buffer)
            spell.set_spells([], outfile_rom_buffer=outfile_rom_buffer)
        else:
            spell = RandomSpellSub()
            magitek.newname('R-Chaos', outfile_rom_buffer)
            spell.set_spells([], 'Chaos', [], outfile_rom_buffer=outfile_rom_buffer)
        magitek.write_properties(outfile_rom_buffer)
        magitek.unsetmenu(outfile_rom_buffer)
        magitek.allow_while_confused(outfile_rom_buffer)
        magitek.allow_while_berserk(outfile_rom_buffer)

        myfs = get_appropriate_free_space(free_spaces, spell.size)
        spell.set_location(myfs.start)
        if not hasattr(spell, 'bytestring') or not spell.bytestring:
            spell.generate_bytestring()
        spell.write(outfile_rom_buffer)
        magitek.setpointer(spell.location, outfile_rom_buffer)
        free_spaces = determine_new_free_spaces(free_spaces, myfs, spell.size)

    gogo_enable_all_sub = Substitution()
    gogo_enable_all_sub.bytestring = bytes([0xEA] * 2)
    gogo_enable_all_sub.set_location(0x35E58)
    gogo_enable_all_sub.write(outfile_rom_buffer)

    cyan_ai_sub = Substitution()
    cyan_ai_sub.bytestring = bytes([0xF0, 0xEE, 0xEE, 0xEE, 0xFF])
    cyan_ai_sub.set_location(0xFBE85)
    cyan_ai_sub.write(outfile_rom_buffer)

    return commands, free_spaces


def manage_suplex(commands: Dict[str, CommandBlock], monsters: List[MonsterBlock]):
    characters = get_characters()
    free_spaces = [FreeBlock(0x2A65A, 0x2A800), FreeBlock(0x2FAAC, 0x2FC6D)]
    suplex_command = [command for command in commands.values() if command.id == 5][0]
    chosen_free_space = free_spaces.pop()
    spell = SpellSub(spellid=0x5F)
    sb = SpellBlock(0x5F, infile_rom_buffer)
    spell.set_location(chosen_free_space.start)
    spell.write(outfile_rom_buffer)
    suplex_command.targeting = sb.targeting
    suplex_command.setpointer(spell.location, outfile_rom_buffer)
    suplex_command.newname(sb.name, outfile_rom_buffer)
    suplex_command.unsetmenu(outfile_rom_buffer)
    fss = chosen_free_space.unfree(spell.location, spell.size)
    free_spaces.extend(fss)
    for character_ms in characters:
        character_ms.set_battle_command(0, command_id=0)
        character_ms.set_battle_command(1, command_id=5)
        character_ms.set_battle_command(2, command_id=0xA)
        character_ms.set_battle_command(3, command_id=1)
        character_ms.write_battle_commands(outfile_rom_buffer)

    for monster in monsters:
        monster.misc2 &= 0xFB
        monster.write_stats(outfile_rom_buffer)

    learn_blitz_sub = Substitution()
    learn_blitz_sub.bytestring = [0xEA] * 2
    learn_blitz_sub.set_location(0x261E5)
    learn_blitz_sub.write(outfile_rom_buffer)
    learn_blitz_sub.bytestring = [0xEA] * 4
    learn_blitz_sub.set_location(0xA18E)
    learn_blitz_sub.write(outfile_rom_buffer)


def manage_natural_magic(natural_magic_table):
    characters = get_characters()

    if not (Options_.is_flag_active("shuffle_commands") or (Options_.is_flag_active("replace_commands"))):
        for character_mnm in characters:
            if character_mnm.id <12:
                character_mnm.set_battle_command(2, command_id=2)
                character_mnm.write_battle_commands(outfile_rom_buffer)

    candidates = [character_mnm for character_mnm in characters if
                  character_mnm.id < 12 and
                  (0x02 in character_mnm.battle_commands or 0x17 in character_mnm.battle_commands)]

    num_natural_mages = 1
    if Options_.is_flag_active('supernatural'):
        num_natural_mages = len(candidates)
    else:
        if random.randint(0, 9) != 9:
            num_natural_mages = 2
            while num_natural_mages < len(candidates) and random.choice([True, False]):
                num_natural_mages += 1

    try:
        candidates = random.sample(candidates, num_natural_mages)
    except ValueError:
        return

    #Ensure Celes does not learn her vanilla natural magic
    natmag_learn_sub = Substitution()
    natmag_learn_sub.set_location(0xa186)
    natmag_learn_sub.bytestring = bytes([0xEA] * 4)
    natmag_learn_sub.write(outfile_rom_buffer)

    # natmag_learn_sub.set_location(NATURAL_MAGIC_TABLE)
    # natmag_learn_sub.bytestring = bytes(
    #    [0xC9, 0x0C, 0xB0, 0x23, 0x48, 0xDA, 0x5A, 0x0B, 0xF4, 0x00, 0x15, 0x2B, 0x85, 0x08, 0xEB, 0x48, 0x85, 0x0B,
    #     0xAE, 0xF4, 0x00, 0x86, 0x09, 0x7B, 0xEB, 0xA9, 0x80, 0x85, 0x0C, 0x22, 0xAB, 0x08, 0xF0, 0x68, 0xEB, 0x2B,
    #     0x7A, 0xFA, 0x68, 0x6B, 0xC9, 0x0C, 0xB0, 0xFB, 0x48, 0xDA, 0x5A, 0x0B, 0xF4, 0x00, 0x15, 0x2B, 0x85, 0x08,
    #     0x8D, 0x02, 0x42, 0xA9, 0x36, 0x8D, 0x03, 0x42, 0xB9, 0x08, 0x16, 0x85, 0x0B, 0xC2, 0x20, 0xAD, 0x16, 0x42,
    #     0x18, 0x69, 0x6E, 0x1A, 0x85, 0x09, 0xA9, 0x00, 0x00, 0xE2, 0x20, 0xA9, 0xFF, 0x85, 0x0C, 0x22, 0xAB, 0x08,
    #     0xF0, 0x2B, 0x7A, 0xFA, 0x68, 0x6B, 0xA0, 0x10, 0x00, 0xA5, 0x08, 0xC2, 0x20, 0x29, 0xFF, 0x00, 0xEB, 0x4A,
    #     0x4A, 0x4A, 0xAA, 0xA9, 0x00, 0x00, 0xE2, 0x20, 0xBF, 0xE1, 0x08, 0xF0, 0xC5, 0x0B, 0xF0, 0x02, 0xB0, 0x11,
    #     0x5A, 0xBF, 0xE0, 0x08, 0xF0, 0xA8, 0xB1, 0x09, 0xC9, 0xFF, 0xF0, 0x04, 0xA5, 0x0C, 0x91, 0x09, 0x7A, 0xE8,
    #     0xE8, 0x88, 0xD0, 0xE0, 0x6B] + [0xFF] * 2 * 16 * 12)
    # natmag_learn_sub.write(outfile_rom_buffer)

    spells = get_ranked_spells(infile_rom_buffer, magic_only=True)
    spell_ids = [spell.spellid for spell in spells]
    address = 0x2CE3C0

    def mutate_spell(pointer_ms: int, used: List) -> Tuple[SpellBlock, int]:
        outfile_rom_buffer.seek(pointer_ms)
        spell, level_ms = tuple(outfile_rom_buffer.read(2))

        while True:
            index_ms = spell_ids.index(spell)
            level_dex = int((level_ms / 99.0) * len(spell_ids))
            lowest_level, highest_level = min(index_ms, level_dex), max(index_ms, level_dex)
            index_ms = random.randint(lowest_level, highest_level)
            index_ms = mutate_index(index_ms, len(spells), [False, True],
                                    (-10, 10), (-5, 5))

            level_ms = mutate_index(level_ms, 99, [False, True],
                                    (-4, 4), (-2, 2))
            level_ms = max(level_ms, 1)

            new_spell_ms = spell_ids[index_ms]
            if Options_.is_flag_active('penultima') and get_spell(new_spell_ms).name == 'Ultima':
                continue
            if new_spell_ms in used:
                continue
            break

        used.append(new_spell_ms)
        return get_spell(new_spell_ms), level_ms

    used_spells = []
    for candidate in candidates:
        candidate.natural_magic = []
        for index in range(16):
            pointer = address + random.choice([0, 32]) + (2 * index)
            new_spell, level = mutate_spell(pointer, used_spells)
            candidate.natural_magic.append((level, new_spell))
        candidate.natural_magic = sorted(candidate.natural_magic, key=lambda spell: (spell[0], spell[1].spellid))
        for index, (level, new_spell) in enumerate(candidate.natural_magic):
            pointer = natural_magic_table + candidate.id * 32 + (2 * index)
            outfile_rom_buffer.seek(pointer)
            outfile_rom_buffer.write(bytes([new_spell.spellid]))
            outfile_rom_buffer.write(bytes([level]))
        used_spells = random.sample(used_spells, 12)

    lores = get_ranked_spells(infile_rom_buffer, magic_only=False)
    lores = [lore for lore in lores if 0x8B <= lore.spellid <= 0xA2]
    lore_ids = [lore.spellid for lore in lores]
    lores_in_order = sorted(lore_ids)
    address = 0x26F564
    outfile_rom_buffer.seek(address)
    known_lores = read_multi(outfile_rom_buffer, length=3)
    known_lore_ids = []
    for index in range(24):
        if (1 << index) & known_lores:
            known_lore_ids.append(lores_in_order[index])

    new_known_lores = 0
    random.shuffle(known_lore_ids)
    for lore_id in known_lore_ids:
        if new_known_lores and random.choice([True, False]):
            continue

        index = lore_ids.index(lore_id)
        index += random.randint(-4, 2)
        index = max(0, min(index, len(lores) - 1))
        while random.choice([True, False]):
            index += random.randint(-2, 1)
            index = max(0, min(index, len(lores) - 1))
        new_lore = lores[index]
        order = lores_in_order.index(new_lore.spellid)
        new_known_lores |= (1 << order)

    outfile_rom_buffer.seek(address)
    write_multi(outfile_rom_buffer, new_known_lores, length=3)


def manage_equip_umaro(freespaces: list):
    # ship unequip - cc3510
    equip_umaro_sub = Substitution()
    equip_umaro_sub.bytestring = [0xC9, 0x0E]
    equip_umaro_sub.set_location(0x31E6E)
    equip_umaro_sub.write(outfile_rom_buffer)
    equip_umaro_sub.bytestring = [0xEA] * 2
    equip_umaro_sub.set_location(0x39EF6)
    equip_umaro_sub.write(outfile_rom_buffer)

    infile_rom_buffer.seek(0xC359D)
    old_unequipper = infile_rom_buffer.read(218)

    header = old_unequipper[:7]
    footer = old_unequipper[-3:]

    def generate_unequipper(base_pointer: int, not_current_party: bool = False):
        unequipper = bytearray([])
        pointer_gu = base_pointer + len(header)
        lo_str, med_str, hi_str = 'LO', 'MED', 'HI'
        for index in range(14):
            segment = []
            segment += [0xE1]
            segment += [0xC0, 0xA0 | index, 0x01, lo_str, med_str, hi_str]
            if not_current_party:
                segment += [0xDE]
                segment += [0xC0, 0xA0 | index, 0x81, lo_str, med_str, hi_str]
            segment += [0x8D, index]
            pointer_gu += len(segment)
            hi, med, lo = pointer_gu >> 16, (pointer_gu >> 8) & 0xFF, pointer_gu & 0xFF
            hi = hi - 0xA
            segment = [hi if byte == hi_str else
                       med if byte == med_str else
                       lo if byte == lo_str else byte for byte in segment]
            unequipper += bytes(segment)
        unequipper = header + unequipper + footer
        return unequipper

    unequip_umaro_sub = Substitution()
    unequip_umaro_sub.bytestring = generate_unequipper(0xC351E)
    unequip_umaro_sub.set_location(0xC351E)
    unequip_umaro_sub.write(outfile_rom_buffer)

    myfs = get_appropriate_free_space(freespaces, 234)
    pointer = myfs.start
    unequip_umaro_sub.bytestring = generate_unequipper(pointer, not_current_party=True)
    freespaces = determine_new_free_spaces(freespaces, myfs, unequip_umaro_sub.size)
    unequip_umaro_sub.set_location(pointer)
    unequip_umaro_sub.write(outfile_rom_buffer)
    unequip_umaro_sub.bytestring = [pointer & 0xFF, (pointer >> 8) & 0xFF, (pointer >> 16) - 0xA]
    unequip_umaro_sub.set_location(0xC3514)
    unequip_umaro_sub.write(outfile_rom_buffer)

    return freespaces


def manage_umaro(commands: Dict[str, CommandBlock]):
    characters = get_characters()
    candidates = [character_mu for character_mu in characters if
                  character_mu.id <= 13 and
                  character_mu.id != 12 and
                  2 not in character_mu.battle_commands and
                  0xC not in character_mu.battle_commands and
                  0x17 not in character_mu.battle_commands]

    if not candidates:
        candidates = [character_mu for character_mu in characters if character_mu.id <= 13 and character_mu.id != 12]
    umaro_risk = random.choice(candidates)
    # character stats have a special case for the berserker, so set this case now until the berserker handler
    # is refactored.
    if umaro_risk and options.Use_new_randomizer:
        for char in character_list:
            if char.id == umaro_risk.id:
                char.berserk = True
    if 0xFF in umaro_risk.battle_commands:
        battle_commands = [0]
        if not Options_.is_flag_active('collateraldamage'):
            battle_commands.extend(random.sample([3, 5, 6, 7, 8, 9, 0xA, 0xB,
                                                  0xC, 0xD, 0xE, 0xF, 0x10,
                                                  0x12, 0x13, 0x16, 0x18, 0x1A,
                                                  0x1B, 0x1C, 0x1D], 2))
        battle_commands.append(1)
        umaro_risk.battle_commands = battle_commands

    umaro = [character for character in characters if character.id == 13][0]
    umaro.battle_commands = list(umaro_risk.battle_commands)
    candidates = [0x00, 0x05, 0x06, 0x07, 0x09, 0x0A, 0x0B, 0x10,
                  0x12, 0x13, 0x16, 0x18]
    candidates = [command for command in candidates if command not in changed_commands]
    base_command = random.choice(candidates)
    commands = list(commands.values())
    base_command = [command for command in commands if command.id == base_command][0]
    base_command.allow_while_berserk(outfile_rom_buffer)
    umaro_risk.battle_commands = [base_command.id, 0xFF, 0xFF, 0xFF]

    umaro.berserk = False
    umaro_risk.berserk = True

    if Options_.is_flag_active('metronome'):
        umaro_risk.battle_commands = [0x1D, 0xFF, 0xFF, 0xFF]

    umaro_risk.write_battle_commands(outfile_rom_buffer)
    umaro.write_battle_commands(outfile_rom_buffer)

    umaro_exchange_sub = Substitution()
    umaro_exchange_sub.bytestring = [0xC9, umaro_risk.id]
    umaro_exchange_sub.set_location(0x21617)
    umaro_exchange_sub.write(outfile_rom_buffer)
    umaro_exchange_sub.set_location(0x20926)
    umaro_exchange_sub.write(outfile_rom_buffer, noverify=True)
    JUNCTION_MANAGER_PARAMETERS['berserker-index'] = umaro_risk.id

    spells = get_ranked_spells(infile_rom_buffer)
    spells = [spell for spell in spells if spell.target_enemy_default]
    spells = [spell for spell in spells if spell.valid]
    spells = [spell for spell in spells if spell.rank() < 1000]
    spell_ids = [spell.spellid for spell in spells]
    index = spell_ids.index(0x54)  # storm
    index += random.randint(0, 10)
    while random.choice([True, False]):
        index += random.randint(-10, 10)
    index = max(0, min(index, len(spell_ids) - 1))
    spell_id = spell_ids[index]
    storm_sub = Substitution()
    storm_sub.bytestring = bytes([0xA9, spell_id])
    storm_sub.set_location(0x21710)
    storm_sub.write(outfile_rom_buffer)

    return umaro_risk


def manage_sprint():
    auto_sprint = Substitution()
    auto_sprint.set_location(0x4E2D)
    auto_sprint.bytestring = bytes([0x80, 0x00])
    auto_sprint.write(outfile_rom_buffer)


def name_swd_techs():
    swd_tech_sub = Substitution()
    swd_tech_sub.set_location(0x26F7E1)
    swd_tech_sub.bytestring = bytes(
        [0x83, 0xa2, 0xac, 0xa9, 0x9a, 0xad, 0x9c,
         0xa1, 0xff, 0xff, 0x91, 0x9e, 0xad, 0xa8,
         0xab, 0xad, 0xff, 0xff, 0xff, 0xff, 0x92,
         0xa5, 0x9a, 0xac, 0xa1, 0xff, 0xff, 0xff,
         0xff, 0xff, 0x90, 0xae, 0x9a, 0x9d, 0xab,
         0x9a, 0x92, 0xa5, 0x9a, 0xa6, 0x84, 0xa6,
         0xa9, 0xa8, 0xb0, 0x9e, 0xab, 0x9e, 0xab,
         0xff, 0x92, 0xad, 0xae, 0xa7, 0xa7, 0x9e,
         0xab, 0xff, 0xff, 0xff, 0x90, 0xae, 0x9a,
         0x9d, 0xfe, 0x92, 0xa5, 0xa2, 0x9c, 0x9e,
         0x82, 0xa5, 0x9e, 0x9a, 0xaf, 0x9e, 0xff,
         0xff, 0xff, 0xff, ])
    swd_tech_sub.write(outfile_rom_buffer)

    repoint_jokerdoom_sub = Substitution()
    repoint_jokerdoom_sub.set_location(0x0236B9)
    repoint_jokerdoom_sub.bytestring = bytes([0x94])
    repoint_jokerdoom_sub.write(outfile_rom_buffer)


def manage_skips():
    # To identify if this cutscene skip is active in a ROM, look for the
    # bytestring:
    # 41 6E 64 53 68 65 61 74 68 57 61 73 54 68 65 72 65 54 6F 6F
    # at 0xCAA9F
    characters = get_characters()

    def write_to_address(address: str, event: List[str]):  # event is a list of hex strings
        event_skip_sub = Substitution()
        event_skip_sub.bytestring = bytearray([])
        for byte in event:
            event_skip_sub.bytestring.append(int(byte, 16))
        event_skip_sub.set_location(int(address, 16))
        event_skip_sub.write(outfile_rom_buffer, noverify=True)

    def handle_normal():  # Replace events that should always be replaced
        write_to_address(split_line[0], split_line[1:])

    def handle_gau():  # Replace events that should be replaced if we are auto-recruiting Gau
        if Options_.is_flag_active('shuffle_commands') or \
                Options_.is_flag_active('replace_commands') or \
                Options_.is_flag_active('random_treasure'):
            write_to_address(split_line[0], split_line[1:])

    # Replace events if we ARE auto-recruiting Gau in TheScenarioNotTaken
    def handle_gau_divergent():

        if not (Options_.is_flag_active('thescenarionottaken')):
            return
        if (Options_.is_flag_active('shuffle_commands') or
                Options_.is_flag_active('replace_commands') or
                Options_.is_flag_active('random_treasure')):
            write_to_address(split_line[0], split_line[1:])

    # Replace events if we are NOT auto-recruiting Gau in TheScenarioNotTaken
    def handle_no_gau_divergent():
        if not (Options_.is_flag_active('thescenarionottaken')):
            return
        if not (Options_.is_flag_active('shuffle_commands') or
                Options_.is_flag_active('replace_commands') or
                Options_.is_flag_active('random_treasure')):
            write_to_address(split_line[0], split_line[1:])

    # Replace events if we are NOT auto-recruiting Gau in a regular seed
    def handle_no_gau_convergent():
        if Options_.is_flag_active('thescenarionottaken'):
            return
        if not (Options_.is_flag_active('shuffle_commands') or
                Options_.is_flag_active('replace_commands') or
                Options_.is_flag_active('random_treasure')):
            write_to_address(split_line[0], split_line[1:])

    # Replace events if we ARE auto-recruiting Gau in a regular seed
    def handle_gau_convergent():

        if Options_.is_flag_active('thescenarionottaken'):
            return
        if (Options_.is_flag_active('shuffle_commands') or
                Options_.is_flag_active('replace_commands') or
                Options_.is_flag_active('random_treasure')):
            write_to_address(split_line[0], split_line[1:])

    # Fix palettes so that they are randomized
    def handle_palette():
        for character_hp in characters:
            if character_hp.id == int(split_line[1], 16):
                palette_correct_sub = Substitution()
                palette_correct_sub.bytestring = bytes([character_hp.palette])
                palette_correct_sub.set_location(int(split_line[0], 16))
                palette_correct_sub.write(outfile_rom_buffer)

    def handle_convergent_palette():
        if Options_.is_flag_active('thescenarionottaken'):
            return
        handle_palette()

    def handle_divergent_palette():
        if not Options_.is_flag_active('thescenarionottaken'):
            return
        handle_palette()

    # Replace events that should be modified if we start with the airship
    def handle_airship():
        if not Options_.is_flag_active('airship'):
            write_to_address(split_line[0], split_line[1:])
        else:
            write_to_address(split_line[0],
                             split_line[1:-1] +  # remove FE from the end
                             ['D2', 'BA'] +  # enter airship from below decks
                             ['D2', 'B9'] +  # airship appears on world map
                             ['D0', '70'] +  # party appears on airship
                             ['6B', '00', '04', '54', '22', '00'] +  # load map, place party
                             ['C7', '54', '23'] +  # place airship
                             ['FF'] +  # end map script
                             ['FE']  # end subroutine
                             )

    # Replace events that should be modified if the scenarios are changed
    def handle_convergent():
        if Options_.is_flag_active('thescenarionottaken'):
            return
        handle_normal()

    # Replace events that should be modified if the scenarios are changed
    def handle_divergent():
        if not Options_.is_flag_active('thescenarionottaken'):
            return
        handle_normal()

    # Replace extra events that must be trimmed from Strange Journey
    def handle_strange():
        if not Options_.is_flag_active('strangejourney'):
            return
        handle_normal()

    for line in open(SKIP_EVENTS_TABLE):
        # If 'Foo' precedes a line in skipEvents.txt, call 'handleFoo'
        line = line.split('#')[0].strip()  # Ignore everything after '#'
        if not line:
            continue
        split_line = line.strip().split(' ')
        handler = 'handle_' + split_line[0].lower()
        split_line = split_line[1:]
        locals()[handler]()

    # flashback_skip_sub = Substitution()
    # flashback_skip_sub.bytestring = bytes([0xB2, 0xB8, 0xA5, 0x00, 0xFE])
    # flashback_skip_sub.set_location(0xAC582)
    # flashback_skip_sub.write(outfile_rom_buffer)

    # boat_skip_sub = Substitution()
    # boat_skip_sub.bytestring = (
    #     bytes([0x97, 0x5C] +  # Fade to black, wait for fade
    #           [0xD0,
    #            0x87] +  # Set event bit 0x87, Saw the scene with Locke and Celes at night in Albrook
    #           [0xD0, 0x83] +  # Set event bit 0x83, Boarded the ship in Albrook
    #           [0xD0,
    #            0x86] +  # Set event bit 0x86, Saw the scene with Terra and Leo at night on the ship
    #           # to Thamasa
    #           [0x3D, 0x03, 0x3F, 0x03, 0x01,
    #            0x45] +  # Create Shadow, add Shadow to party 1, refresh objects
    #           [0xD4, 0xE3, 0x77, 0x03, 0xD4,
    #            0xF3] +  # Shadow in shop and item menus, level average Shadow, Shadow is available
    #           [0x88, 0x03, 0x00, 0x40, 0x8B, 0x03, 0x7F, 0x8C, 0x03,
    #            0x7F] +  # Cure status ailments of Shadow, set HP and MP to max
    #           [0xB2, 0xBD, 0xCF,
    #            0x00] +  # Subroutine that cures status ailments and set hp and mp to max.
    #           # clear NPC bits
    #           [0xDB, 0x06, 0xDB, 0x07, 0xDB, 0x08, 0xDB, 0x11, 0xDB, 0x13, 0xDB, 0x22, 0xDB,
    #            0x42, 0xDB, 0x65] + [0xB8, 0x4B] +  # Shadow won't run
    #           [0x6B, 0x00, 0x04, 0xE8, 0x96, 0x40, 0xFF]
    #           # Load world map with party near Thamasa, return
    #           ))
    # boat_skip_sub.set_location(0xC615A)
    # boat_skip_sub.write(outfile_rom_buffer)

    leo_skip_sub = Substitution()
    leo_skip_sub.bytestring = (
        bytes([0x97, 0x5C] +  # Fade to black, wait for fade
              [0xD0, 0x99, 0xDB,
               0x1B] +  # Set event bit 0x99, Found the Espers at Gathering Place of the Espers, hide
              # Esper NPCs in cave
              [0xB2, 0x2B, 0x2E, 0x01, 0x3F, 0x01, 0x00, 0x3F, 0x00, 0x00, 0x45, 0x3E, 0x01, 0x3E,
               0x00, 0x45, 0x40, 0x0E, 0x0F, 0x3D, 0x0E, 0x3F, 0x0E, 0x01, 0x37, 0x0E, 0x10, 0x43,
               0x0E, get_character(0x0F).palette, 0x7F, 0x0E, 0x0F, 0x45, 0x3F, 0x08, 0x00, 0x3F,
               0x07, 0x00, 0x45, 0x3E, 0x08, 0x3E, 0x07, 0x45, 0xB2, 0xBD, 0xCF, 0x00,
               0x47] +  # Setup party with Leo
              [0x6B, 0x55, 0x21, 0x16, 0x16, 0xC0, 0x39] +  # Load Map
              [0x3D, 0x1D, 0x3D, 0x1E, 0x3D, 0x1F, 0x3D, 0x20, 0x3D, 0x11, 0x3D, 0x19, 0x3D, 0x1A,
               0x3D, 0x16, 0x3D, 0x17, 0x3D, 0x18, 0x3D, 0x21, 0x45, 0x41, 0x1D, 0x41, 0x1E, 0x41,
               0x1F, 0x41, 0x20, 0x41, 0x11, 0x41, 0x19, 0x41, 0x1A, 0x41, 0x16, 0x41, 0x17, 0x41,
               0x18, 0x41, 0x21, 0x42, 0x15, 0x3E, 0x15, 0x42, 0x14, 0x3E, 0x14,
               0x45] +  # Create necessary NPCs for Thamasa Attack scene
              [0x31, 0x05, 0xD5, 0x16, 0x16, 0x28, 0xFF, 0x45, 0x36, 0x1C, 0x36, 0x1B, 0x59, 0x04,
               0x92, 0xB2, 0x37, 0x6A, 0x01, 0xB2, 0x09, 0x6A, 0x01] +  # Leo wakes up
              [0xB2, 0xA6, 0xFF, 0X01, 0xFE]
              # call Thamasa entrance event CB/FFA6 to place NPCs, end.
              ))
    leo_skip_sub.set_location(0xBF2BB)
    leo_skip_sub.write(outfile_rom_buffer)

    kefka_wins_skip_sub = Substitution()
    kefka_wins_skip_sub.bytestring = bytes(
        [0x40, 0x0F, 0x2C, 0x3D, 0x0F, 0x45, 0x7F, 0x0F, 0x2C, 0x37, 0x0F, 0x15, 0x43, 0x0F,
         get_character(0x15).palette,
         0x88, 0x0F, 0x00, 0x00, 0x8B, 0x0F, 0x7F, 0x8C, 0x0F, 0x7F] +  # Put Kefka in party
        [0x4D, 0x7C, 0x3F] +  # Fight
        [0xB2, 0xA9, 0x5E, 0x00] +  # Game over if you lost
        [0x42, 0x1D, 0x42, 0x1E, 0x42, 0x1F, 0x42, 0x20, 0x42, 0x11, 0x42, 0x19, 0x42, 0x1A, 0x42, 0x16, 0x42, 0x17,
         0x42,
         0x18, 0x42, 0x21, 0x3E, 0x1D, 0x3E, 0x1E, 0x3E, 0x1F, 0x3E, 0x20, 0x3E, 0x11, 0x3E, 0x19, 0x3E, 0x1A, 0x3E,
         0x16,
         0x3E, 0x17, 0x3E, 0x18, 0x3E, 0x21, 0x45] +  # Delete the Kefka Attacks Thamasa objects

        [0xD0, 0x9B] +  # Set event bit 0x9B, Fought Kefka at Thamasa
        [0xD0, 0x9C] +  # Set event bit 0x9C, Leo is buried in Thamasa
        [0x3D, 0x01, 0x3D, 0x00, 0x45, 0x3F, 0x01, 0x01, 0x3F, 0x00, 0x01, 0x45, 0x3F, 0x0E, 0x00, 0x3E, 0x0E, 0x3D,
         0x08, 0x3D,
         0x07, 0x45, 0x3F, 0x08, 0x01, 0x3F, 0x07, 0x01, 0x45, 0x3C, 0x00, 0x01, 0x07, 0x08,
         0x45] +  # Set up party as Terra, Locke, Strago, Relm
        # Clear event bits for party members available
        [0xDB, 0xF7, 0xD5, 0xF2, 0xD5, 0xF3, 0xD5, 0xF4, 0xD5, 0xF5, 0xD5, 0xF9, 0xD5, 0xFB, 0xD5,
         0xF6] +  # perform level averaging
        [0x77, 0x02, 0x77, 0x03, 0x77, 0x04, 0x77, 0x05, 0x77, 0x09, 0x77, 0x0B, 0x77,
         0x06] +  # Set event bits for party members available
        [0xD4, 0xF2, 0xD4, 0xF4, 0xD4, 0xF5, 0xD4, 0xF9, 0xD4, 0xFB, 0xD4, 0xF6] +
        [0xB2, 0x35, 0x09, 0x02] +  # Subroutine to do level averaging for Mog if you have him
        [0xD3, 0xCC] +  # Clear temp song override
        [0xD0, 0x9D] +  # set event bit 0x9D Completed the mandatory Thamasa scenario
        [0xD2, 0xBA] +  # Airship is anchored
        [0xDA, 0x5A, 0xDA, 0x59, 0xDB, 0x20, 0xDA, 0x68] +  # NPC event bits
        [0xD2, 0xB3, 0xD2, 0xB4] +  # Facing left and pressing A?
        [0xD0, 0x7A] +  # Set event bit 0x7A, The Espers attacked the Blackjack
        # always occurs 2 (always remains clear)
        [0xD2, 0x6F] +  # Set event bit 0x16F, Learned how to operate the airship
        [0x6B, 0x00, 0x04, 0xF9, 0x80, 0x00] +  # load map, place party
        [0xC7, 0xF9, 0x7F, 0xFF]  # place airship, end
    )
    kefka_wins_skip_sub.set_location(0xBFFF4)
    kefka_wins_skip_sub.write(outfile_rom_buffer)

    tintinabar_sub = Substitution()
    tintinabar_sub.set_location(0xC67CF)
    tintinabar_sub.bytestring = bytes(
        [0xC1, 0x7F, 0x02, 0x88, 0x82, 0x74, 0x68, 0x02, 0x4B, 0xFF, 0x02, 0xB6, 0xE2, 0x67, 0x02, 0xB3, 0x5E, 0x00,
         0xFE, 0x85, 0xC4, 0x09, 0xC0, 0xBE, 0x81, 0xFF, 0x69, 0x01, 0xD4, 0x88])
    tintinabar_sub.write(outfile_rom_buffer)

    set_dialogue(0x2ff,
                 'For 2500 GP you can send 2 letters, a record, a Tonic, and a book.<line><choice> (Send them)  '
                 '<choice> (Forget it)')

    # skip the flashbacks of Daryl
    # daryl_cutscene_sub = Substitution()
    # daryl_cutscene_sub.set_location(0xA4365)
    # daryl_cutscene_sub.bytestring = (
    #     bytes([0xF0, 0x4C,  # play song 'Searching for Friends'
    #           0x6B, 0x01, 0x04, 0x9E, 0x33, 0x01,
    #           # load map World of Ruin, continue playing song, party at (158,51) facing up,
    #           # in airship
    #           0xC0, 0x20,  # allow ship to propel without changing facing
    #           0xC2, 0x64, 0x00,  # set bearing 100
    #           0xFA,  # show airship emerging from the ocean
    #           0xD2, 0x11, 0x34, 0x10, 0x08, 0x40,  # load map Falcon upper deck
    #           0xD7, 0xF3,  # hide Daryl on the Falcon
    #           0xB2, 0x3F, 0x48, 0x00,
    #           # jump to part where it sets a bunch of bits then flys to Maranda
    #           0xFE]))
    # daryl_cutscene_sub.write(outfile_rom_buffer)

    # We overwrote some of the event items, so write them again
    if Options_.is_flag_active('random_treasure'):
        for items in get_event_items().values():
            for item in items:
                item.write_data(outfile_rom_buffer, cutscene_skip=True)


def activate_airship_mode(free_spaces: list):
    set_airship_sub = Substitution()
    set_airship_sub.bytestring = bytes([0x3A, 0xD2, 0xCC] +  # moving code
                                       [0xD2, 0xBA] +  # enter airship from below decks
                                       [0xD2, 0xB9] +  # airship appears on world map
                                       [0xD0, 0x70] +  # party appears on airship
                                       [0x6B, 0x00, 0x04, 0x54, 0x22, 0x00] +  # load map, place party
                                       [0xC7, 0x54, 0x23] +  # place airship
                                       [0xFF] +  # end map script
                                       [0xFE]  # end subroutine
                                       )
    myfs = get_appropriate_free_space(free_spaces, set_airship_sub.size)
    pointer = myfs.start
    free_spaces = determine_new_free_spaces(free_spaces, myfs, set_airship_sub.size)

    set_airship_sub.set_location(pointer)
    set_airship_sub.write(outfile_rom_buffer)

    set_airship_sub.bytestring = bytes([0xD2, 0xB9])  # airship appears in WoR
    set_airship_sub.set_location(0xA532A)
    set_airship_sub.write(outfile_rom_buffer)

    set_airship_sub.bytestring = bytes([0x6B, 0x01, 0x04, 0x4A, 0x16, 0x01] +  # load WoR, place party
                                       [0xDD] +  # hide minimap
                                       [0xC5, 0x00, 0x7E, 0xC2, 0x1E, 0x00] +  # set height and direction
                                       [0xC6, 0x96, 0x00, 0xE0, 0xFF] +  # propel vehicle, wait 255 units
                                       [0xC7, 0x4E, 0xf0] +  # place airship
                                       [0xD2, 0x8E, 0x25, 0x07, 0x07, 0x40])  # load beach with fish
    set_airship_sub.set_location(0xA51E9)
    set_airship_sub.write(outfile_rom_buffer)

    # point to airship-placing script
    set_airship_sub.bytestring = bytes([0xB2, pointer & 0xFF, (pointer >> 8) & 0xFF,
                                        (pointer >> 16) - 0xA, 0xFE])
    set_airship_sub.set_location(0xCB046)
    set_airship_sub.write(outfile_rom_buffer)

    # always access floating continent
    set_airship_sub.bytestring = bytes([0xC0, 0x27, 0x01, 0x79, 0xF5, 0x00])
    set_airship_sub.set_location(0xAF53A)  # need first branch for button press
    # ...  except in the World of Ruin
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.bytestring = bytes([0xC0, 0xA4, 0x80, 0x6E, 0xF5, 0x00])
    set_airship_sub.set_location(0xAF579)  # need first branch for button press
    set_airship_sub.write(outfile_rom_buffer)

    # always exit airship
    set_airship_sub.bytestring = bytes([0xFD] * 6)
    set_airship_sub.set_location(0xAF4B1)
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.bytestring = bytes([0xFD] * 8)
    set_airship_sub.set_location(0xAF4E3)
    set_airship_sub.write(outfile_rom_buffer)

    # chocobo stables are airship stables now
    set_airship_sub.bytestring = bytes([0xB6, 0x8D, 0xF5, 0x00, 0xB3, 0x5E, 0x00])
    set_airship_sub.set_location(0xA7A39)
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.set_location(0xA8FB7)
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.set_location(0xB44D0)
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.set_location(0xC3335)
    set_airship_sub.write(outfile_rom_buffer)

    # don't force Locke and Celes at party select
    set_airship_sub.bytestring = bytes([0x99, 0x01, 0x00, 0x00])
    set_airship_sub.set_location(0xAAB67)
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.set_location(0xAF60F)
    set_airship_sub.write(outfile_rom_buffer)
    set_airship_sub.set_location(0xCC2F3)
    set_airship_sub.write(outfile_rom_buffer)

    # Daryl is not such an airship hog
    set_airship_sub.bytestring = bytes([0x6E, 0xF5])
    set_airship_sub.set_location(0x41F41)
    set_airship_sub.write(outfile_rom_buffer)

    return free_spaces


def set_lete_river_encounters():
    # make lete river encounters consistent within a seed for katn racing
    manage_lete_river_sub = Substitution()
    # force pseudo random jump to have a battle (4 bytes)
    manage_lete_river_sub.bytestring = bytes([0xFD] * 4)
    manage_lete_river_sub.set_location(0xB0486)
    manage_lete_river_sub.write(outfile_rom_buffer)
    # force pseudo random jump to have a battle (4 bytes)
    manage_lete_river_sub.bytestring = bytes([0xFD] * 4)
    manage_lete_river_sub.set_location(0xB048F)
    manage_lete_river_sub.write(outfile_rom_buffer)
    # call subroutine CB0498 (4 bytes)
    if Options_.is_flag_active('thescenarionottaken'):
        battle_calls = [0xB066B,
                        0xB0690,
                        0xB06A4,
                        0xB06B4,
                        0xB06D0,
                        0xB06E1,
                        0xB0704,
                        0xB071B,
                        0xB0734,
                        0xB0744,
                        0xB076A,
                        0xB077C,
                        0xB07A0,
                        0xB07B6,
                        0xB07DD,
                        0xB0809,
                        0xB081E,
                        0xB082D,
                        0xB084E,
                        0xB0873,
                        0xB08A8, ]
    else:
        battle_calls = [0xB066B,
                        0xB0690,
                        0xB06A4,
                        0xB06B4,
                        0xB06D0,
                        0xB06E1,
                        0xB0704,
                        0xB071B,
                        0xB0734,
                        0xB0744,
                        0xB076A,
                        0xB077C,
                        0xB07A0,
                        0xB07B6,
                        0xB07DD,
                        0xB0809,
                        0xB081E,
                        0xB082D,
                        0xB084E,
                        0xB0873,
                        0xB08A8,
                        0xB09E0,
                        0xB09FC]

    for addr in battle_calls:
        # call subroutine `addr` (4 bytes)
        if random.randint(0, 1) == 0:
            manage_lete_river_sub.bytestring = bytes([0xFD] * 4)
            manage_lete_river_sub.set_location(addr)
            manage_lete_river_sub.write(outfile_rom_buffer)

    if not Options_.is_flag_active('thescenarionottaken'):
        if random.randint(0, 1) == 0:
            manage_lete_river_sub.bytestring = bytes([0xFD] * 8)
            manage_lete_river_sub.set_location(0xB09C8)
            manage_lete_river_sub.write(outfile_rom_buffer)


def manage_rng():
    outfile_rom_buffer.seek(0xFD00)
    if Options_.is_flag_active('norng'):
        numbers = [0 for _ in range(0x100)]
    else:
        numbers = list(range(0x100))
    random.shuffle(numbers)
    outfile_rom_buffer.write(bytes(numbers))

def manage_balance(newslots: bool = True):
    manage_rng()
    if newslots:
        randomize_slots(0x24E4A)

    get_monsters(infile_rom_buffer)
    get_monster(0x174)

    vanish_doom(outfile_rom_buffer)
    evade_mblock(outfile_rom_buffer)
    fix_xzone(outfile_rom_buffer)
    imp_skimp(outfile_rom_buffer)
    allergic_dog(outfile_rom_buffer)
    fix_flyaway(outfile_rom_buffer)
    death_abuse(outfile_rom_buffer)
    fix_gogo_portrait(outfile_rom_buffer)
    item_return_buffer_fix(outfile_rom_buffer)

def manage_magitek():
    magitek_log = ''
    spells = get_ranked_spells()
    # exploder = [s for s in spells if s.spellid == 0xA2][0]
    shockwave = [spell for spell in spells if spell.spellid == 0xE3][0]
    tek_skills = [spell for spell in spells if spell.spellid in TEK_SKILLS and spell.spellid != 0xE3]
    targets = sorted({spell.targeting for spell in spells})
    terra_used, others_used = [], []
    target_pointer = 0x19104
    terra_pointer = 0x1910C
    others_pointer = 0x19114
    terra_cand = None
    others_cand = None
    for index in reversed(range(3, 8)):
        while True:
            if index == 5:
                targeting = 0x43
            else:
                targeting = random.choice(targets)
            candidates = [spell for spell in tek_skills if spell.targeting == targeting]
            if not candidates:
                continue

            terra_cand = random.choice(candidates)
            if index > 5:
                others_cand = None
            elif index == 5:
                others_cand = shockwave
            else:
                others_cand = random.choice(candidates)
            if terra_cand not in terra_used:
                if index >= 5 or others_cand not in others_used:
                    break

        terra_used.append(terra_cand)
        others_used.append(others_cand)

    magitek_log += 'Terra Magitek skills:\n\n'
    for spell in terra_used:
        if spell is not None:
            magitek_log += str(spell.name) + ' \n'
    magitek_log += '\nOther Actor Magitek skills: \n\n'
    for spell in others_used:
        if spell is not None:
            if spell.name != 'Shock Wave':
                magitek_log += str(spell.name) + ' \n'
    log(magitek_log, section='magitek')

    terra_used.reverse()
    others_used.reverse()
    outfile_rom_buffer.seek(target_pointer + 3)
    for spell in terra_used:
        outfile_rom_buffer.write(bytes([spell.targeting]))
    outfile_rom_buffer.seek(terra_pointer + 3)
    for spell in terra_used:
        outfile_rom_buffer.write(bytes([spell.spellid - 0x83]))
    outfile_rom_buffer.seek(others_pointer + 3)
    for spell in others_used:
        if spell is None:
            break
        outfile_rom_buffer.write(bytes([spell.spellid - 0x83]))


def manage_final_boss(freespaces: list):
    kefka1 = get_monster(0x12a)
    kefka2 = get_monster(0x11a)  # dummied kefka
    for kefka in [kefka1, kefka2]:
        pointer = kefka.ai + 0xF8700
        freespaces.append(FreeBlock(pointer, pointer + kefka.aiscriptsize))
    aiscripts = read_ai_table(FINAL_BOSS_AI_TABLE)

    aiscript = aiscripts['KEFKA 1']
    kefka1.aiscript = aiscript

    kefka2.copy_all(kefka1, everything=True)
    aiscript = aiscripts['KEFKA 2']
    kefka2.aiscript = aiscript

    def has_graphics(monster: MonsterBlock) -> bool:
        if monster.graphics.graphics == 0:
            return False
        if not monster.name.strip('_'):
            return False
        if monster.id in list(range(0x157, 0x160)) + [0x11a, 0x12a]:
            return False
        return True

    kefka2.graphics.copy_data(kefka1.graphics)
    monsters = get_monsters()
    monsters = [monster for monster in monsters if has_graphics(monster)]
    kefka = random.choice(monsters)
    kefka1.graphics.copy_data(kefka.graphics)
    change_enemy_name(outfile_rom_buffer, kefka1.id, kefka.name.strip('_'))

    k1formation = get_formation(0x202)
    k2formation = get_formation(KEFKA_EXTRA_FORMATION)
    k2formation.copy_data(k1formation)
    assert k1formation.enemy_ids[0] == (0x12a & 0xFF)
    assert k2formation.enemy_ids[0] == (0x12a & 0xFF)
    k2formation.enemy_ids[0] = kefka2.id & 0xFF
    assert k1formation.enemy_ids[0] == (0x12a & 0xFF)
    assert k2formation.enemy_ids[0] == (0x11a & 0xFF)
    k2formation.lookup_enemies()

    for kefka in [kefka1, kefka2]:
        myfs = get_appropriate_free_space(freespaces, kefka.aiscriptsize)
        pointer = myfs.start
        kefka.set_relative_ai(pointer)
        freespaces = determine_new_free_spaces(freespaces, myfs, kefka.aiscriptsize)

    kefka1.write_stats(outfile_rom_buffer)
    kefka2.write_stats(outfile_rom_buffer)
    return freespaces


def manage_monsters(web_custom_moves=None) -> List[MonsterBlock]:
    monsters = get_monsters(infile_rom_buffer)
    safe_solo_terra = not Options_.is_flag_active('ancientcave')
    darkworld = Options_.is_flag_active('darkworld')
    change_skillset = None
    katn = Options_.mode.name == 'katn'
    final_bosses = (list(range(0x157, 0x160)) + list(range(0x127, 0x12b)) + [0x112, 0x11a, 0x17d])
    for monster in monsters:
        if 'zone eater' in monster.name.lower():
            if Options_.is_flag_active('norng'):
                monster.aiscript = [script.replace(b'\x10', b'\xD5') for script in monster.aiscript]
            continue
        if not monster.name.strip('_') and not monster.display_name.strip('_'):
            continue
        if monster.id in final_bosses:
            if 0x157 <= monster.id < 0x160 or monster.id == 0x17d:
                # deep randomize three tiers, Atma
                monster.randomize_boost_level()
                if darkworld:
                    monster.increase_enemy_difficulty()
                monster.mutate(Options_=Options_,
                               change_skillset=True,
                               safe_solo_terra=False,
                               katn=katn)
            else:
                monster.mutate(Options_=Options_,
                               change_skillset=change_skillset,
                               safe_solo_terra=False,
                               katn=katn)
            if 0x127 <= monster.id < 0x12a or monster.id == 0x17d or monster.id == 0x11a:
                # boost statues, Atma, final kefka a second time
                monster.randomize_boost_level()
                if darkworld:
                    monster.increase_enemy_difficulty()
                monster.mutate(Options_=Options_,
                               change_skillset=change_skillset,
                               safe_solo_terra=False)
            monster.misc1 &= (0xFF ^ 0x4)  # always show name
        else:
            if darkworld:
                monster.increase_enemy_difficulty()
            monster.mutate(Options_=Options_,
                           change_skillset=change_skillset,
                           safe_solo_terra=safe_solo_terra,
                           katn=katn)

        monster.tweak_fanatics()
        monster.relevel_specifics()

    change_enemy_name(outfile_rom_buffer, 0x166, 'L.255Magic')

    shuffle_monsters(monsters, safe_solo_terra=safe_solo_terra)
    for monster in monsters:
        monster.randomize_special_effect(
            outfile_rom_buffer,
            halloween=Options_.is_flag_active('halloween'),
            web_custom_moves=web_custom_moves
        )
        monster.write_stats(outfile_rom_buffer)

    return monsters


def manage_monster_appearance(monsters: List[MonsterBlock], preserve_graphics: bool = False) -> (
        List)[MonsterGraphicBlock]:
    monster_graphic_blocks = [monster.graphics for monster in monsters]
    esperptr = 0x127000 + (5 * 384)
    espers = []
    for index_mma in range(32):
        monster_graphics = MonsterGraphicBlock(pointer=esperptr + (5 * index_mma), name='')
        monster_graphics.read_data(infile_rom_buffer)
        espers.append(monster_graphics)
        monster_graphic_blocks.append(monster_graphics)

    for monster in monsters:
        graphic = monster.graphics
        palette_pointer = graphic.palette_pointer
        others = [monster_graphic_block for monster_graphic_block in monster_graphic_blocks if
                  monster_graphic_block.palette_pointer == palette_pointer + 0x10]
        if others:
            graphic.palette_data = graphic.palette_data[:0x10]

    nonbosses = [monster for monster in monsters if not monster.is_boss and not monster.boss_death]
    bosses = [monster for monster in monsters if monster.is_boss or monster.boss_death]
    assert not set(bosses) & set(nonbosses)
    # nonboss_graphics = [monster.graphics.graphics for monster in nonbosses]
    # bosses = [monster for monster in bosses if monster.graphics.graphics not in nonboss_graphics]

    for index, monster in enumerate(nonbosses):
        if 'Chupon' in monster.name:
            monster.update_pos(6, 6)
            monster.update_size(8, 16)
        if 'Siegfried' in monster.name:
            monster.update_pos(8, 8)
            monster.update_size(8, 8)
        candidates = nonbosses[index:]
        monster.mutate_graphics_swap(candidates)
        name = randomize_enemy_name(outfile_rom_buffer, monster.id)
        monster.changed_name = name

    done = {}
    free_pointer = 0x127820
    for monster in monsters:
        monster_graphics = monster.graphics
        if monster.id == 0x12a and not preserve_graphics:
            id_pair = 'KEFKA 1'
        if monster.id in REPLACE_ENEMIES + [0x172]:
            monster_graphics.set_palette_pointer(free_pointer)
            free_pointer += 0x40
            continue
        else:
            id_pair = (monster.name, monster_graphics.palette_pointer)

        if id_pair not in done:
            monster_graphics.mutate_palette()
            done[id_pair] = free_pointer
            free_pointer += len(monster_graphics.palette_data)
            monster_graphics.write_data(outfile_rom_buffer, palette_pointer=done[id_pair])
        else:
            monster_graphics.write_data(outfile_rom_buffer, palette_pointer=done[id_pair],
                                        no_palette=True)

    for monster_graphics in espers:
        monster_graphics.mutate_palette()
        monster_graphics.write_data(outfile_rom_buffer, palette_pointer=free_pointer)
        free_pointer += len(monster_graphics.palette_data)

    return monster_graphic_blocks


def manage_colorize_animations():
    palettes = []
    for index in range(240):
        pointer = 0x126000 + (index * 16)
        outfile_rom_buffer.seek(pointer)
        palette = [read_multi(outfile_rom_buffer, length=2) for _ in range(8)]
        palettes.append(palette)

    for index, palette in enumerate(palettes):
        transformer = get_palette_transformer(basepalette=palette)
        palette = transformer(palette)
        pointer = 0x126000 + (index * 16)
        outfile_rom_buffer.seek(pointer)
        for color in palette:
            write_multi(outfile_rom_buffer, color, length=2)


def manage_items(items: List[ItemBlock], changed_commands_mi: Set[int] = None) -> List[ItemBlock]:
    from itemrandomizer import (set_item_changed_commands, extend_item_breaks)
    always_break = Options_.is_flag_active('collateraldamage')
    crazy_prices = Options_.is_flag_active('madworld')
    extra_effects = Options_.get_flag_value('masseffect')
    wild_breaks = Options_.is_flag_active('electricboogaloo')
    no_breaks = Options_.is_flag_active('nobreaks')
    unbreakable = Options_.is_flag_active('unbreakable')
    allow_ultima = not Options_.is_flag_active('penultima')

    set_item_changed_commands(changed_commands_mi)
    unhardcode_tintinabar(outfile_rom_buffer)
    sprint_shoes_break(outfile_rom_buffer)
    extend_item_breaks(outfile_rom_buffer)

    auto_equip_relics = []

    for item in items:
        item.mutate(always_break=always_break, crazy_prices=crazy_prices, extra_effects=extra_effects,
                    wild_breaks=wild_breaks, no_breaks=no_breaks, unbreakable=unbreakable, allow_ultima=allow_ultima)
        item.unrestrict()
        item.write_stats(outfile_rom_buffer)
        if item.features['special2'] & 0x38 and item.is_relic:
            auto_equip_relics.append(item.itemid)

    assert auto_equip_relics

    auto_equip_sub = Substitution()
    auto_equip_sub.set_location(0x39EF9)
    auto_equip_sub.bytestring = bytes([0xA0, 0xF1, ])
    auto_equip_sub.write(outfile_rom_buffer)

    auto_equip_sub.set_location(0x3F1A0)
    auto_equip_sub.bytestring = bytes([0x20, 0xF2, 0x93,
                                       0xB9, 0x23, 0x00,
                                       0xC5, 0xB0,
                                       0xD0, 0x09,
                                       0xB9, 0x24, 0x00,
                                       0xC5, 0xB1,
                                       0xD0, 0x02,
                                       0x80, 0x4C,
                                       0x64, 0x99,
                                       0xA5, 0xB0,
                                       0x20, 0x21, 0x83,
                                       0xAE, 0x34, 0x21,
                                       0xBF, 0x0C, 0x50, 0xD8,
                                       0x29, 0x38,
                                       0x85, 0xFE,
                                       0xA5, 0xB1,
                                       0x20, 0x21, 0x83,
                                       0xAE, 0x34, 0x21,
                                       0xBF, 0x0C, 0x50, 0xD8,
                                       0x29, 0x38,
                                       0x04, 0xFE,
                                       0xB9, 0x23, 0x00,
                                       0x20, 0x21, 0x83,
                                       0xAE, 0x34, 0x21,
                                       0xBF, 0x0C, 0x50, 0xD8,
                                       0x29, 0x38,
                                       0x85, 0xFF,
                                       0xB9, 0x24, 0x00,
                                       0x20, 0x21, 0x83,
                                       0xAE, 0x34, 0x21,
                                       0xBF, 0x0C, 0x50, 0xD8,
                                       0x29, 0x38,
                                       0x04, 0xFF,
                                       0xA5, 0xFE,
                                       0xC5, 0xFF,
                                       0xF0, 0x02,
                                       0xE6, 0x99,
                                       0x60])
    auto_equip_sub.write(outfile_rom_buffer)

    return items


def manage_equipment(items: List[ItemBlock]) -> List[ItemBlock]:
    characters = get_characters()
    reset_equippable(items, characters=characters, equip_anything=Options_.is_flag_active('equipanything'))

    equippable_dict = {'weapon': lambda item: item.is_weapon,
                       'shield': lambda item: item.is_shield,
                       'helm': lambda item: item.is_helm,
                       'armor': lambda item: item.is_body_armor,
                       'relic': lambda item: item.is_relic}

    tempchars = [14, 15, 16, 17, 32, 33] + list(range(18, 28))
    if Options_.is_flag_active('ancientcave'):
        tempchars += [41, 42, 43]
    for character_me in characters:
        if character_me.id >= 14 and character_me.id not in tempchars:
            continue
        if character_me.id in tempchars:
            left_handed = random.randint(1, 10) == 10
            for equip_type in ['weapon', 'shield', 'helm', 'armor',
                               'relic1', 'relic2']:
                outfile_rom_buffer.seek(character_me.address + equip_offsets[equip_type])
                ord(outfile_rom_buffer.read(1))
                outfile_rom_buffer.seek(character_me.address + equip_offsets[equip_type])
                if left_handed and equip_type == 'weapon':
                    equip_type = 'shield'
                elif left_handed and equip_type == 'shield':
                    equip_type = 'weapon'
                if equip_type == 'shield' and random.randint(1, 7) == 7:
                    equip_type = 'weapon'
                equip_type = equip_type.strip('1').strip('2')
                func = equippable_dict[equip_type]
                equippable_items = list(filter(func, items))
                while True:
                    equip_item = equippable_items.pop(random.randint(0, len(equippable_items) - 1))
                    equip_id = equip_item.itemid
                    if equip_item.has_disabling_status and (0xE <= character_me.id <= 0xF or character_me.id > 0x1B):
                        equip_id = 0xFF
                    elif (Options_.is_flag_active('dearestmolulu') and
                          equip_item.prevent_encounters and
                          character_me.id in [14, 16, 17]):
                        # don't give moogle charm to Banon, or Guest Ghosts during dearestmolulu
                        equip_id = 0xFF
                    else:
                        if equip_type not in ['weapon', 'shield'] and random.randint(1, 100) == 100:
                            equip_id = random.randint(0, 0xFF)
                    if equip_id != 0xFF or len(equippable_items) == 0:
                        break
                outfile_rom_buffer.write(bytes([equip_id]))
            continue

        equippable_items = [item for item in items if item.equippable & (1 << character_me.id)]
        equippable_items = [item for item in equippable_items if not item.has_disabling_status]
        equippable_items = [item for item in equippable_items if not item.banned]
        if random.randint(1, 4) < 4:
            equippable_items = [item for item in equippable_items if not item.imp_only]
        for equip_type, func in equippable_dict.items():
            if equip_type == 'relic':
                continue
            equippable = list(filter(func, equippable_items))
            weakest = 0xFF
            if equippable:
                weakest = min(equippable, key=lambda item: item.rank()).itemid
            character_me.write_default_equipment(outfile_rom_buffer, weakest, equip_type)
    for item in items:
        item.write_stats(outfile_rom_buffer)
    return items


def manage_reorder_rages(rage_order_table):
    pointer = rage_order_table

    monsters = get_monsters()
    monsters = [monster for monster in monsters if monster.id <= 0xFE]
    monsters = sorted(monsters, key=lambda monster: monster.display_name)
    assert len(monsters) == 255
    monster_order = [monster.id for monster in monsters]

    reordered_rages_sub = Substitution()
    reordered_rages_sub.bytestring = monster_order
    reordered_rages_sub.set_location(pointer)
    reordered_rages_sub.write(outfile_rom_buffer)
    ((pointer >> 16) & 0x3F) + 0xC0, (pointer >> 8) & 0xFF, pointer & 0xFF
    return


def manage_esper_boosts(free_spaces: List[FreeBlock]) -> List[FreeBlock]:
    boost_subs = []
    esper_boost_sub = Substitution()
    # experience: $1611,X - $1613,X
    # experience from battle: $0011,X - $0013,X
    # experience needed for levelup: $ED8220,X
    # available registers: FC, FD, X
    # Y contains offset to char block and should not be changed
    esper_boost_sub.bytestring = [0xE2, 0x20,  # SEP #$20
                                  0xB9, 0x08, 0x16,  # LDA $1608,Y (load level)
                                  0xC9, 0x63,  # Are we level 99?
                                  0xD0, 0x01,  # Branch if not.
                                  0x60,  # RTS
                                  0x0A, 0xAA,  # ASL, TAX
                                  0xC2, 0x20,  # REP #$20 IMPORTANT
                                  0xBF, 0x1E, 0x82, 0xED,  # LDA $ED821E,X (load needed exp)
                                  0x0A, 0x0A,  # ASL, ASL
                                  0x79, 0x11, 0x16,  # ADC $1611,Y (low bytes exp)
                                  0x99, 0x11, 0x16,  # STA $1611,Y
                                  0xE2, 0x20,  # SEP #$20
                                  0x90, 0x07,  # BCC +7 (skip seven bytes)
                                  0xB9, 0x13, 0x16,  # LDA $1613,Y
                                  0x1A,  # INC
                                  0x99, 0x13, 0x16,  # STA $1613,Y
                                  0x60,  # RTS
                                  ]
    boost_subs.append(esper_boost_sub)

    esper_boost_sub = Substitution()
    esper_boost_sub.bytestring = [0xE2, 0x20,  # SEP #$20
                                  0xB9, 0x08, 0x16,  # LDA $1608,Y (load level)
                                  0xC9, 0x02,  # CMP Are we level 2?
                                  0xD0, 0x01,  # BNE Branch if not.
                                  0x60,  # RTS
                                  0x3A, 0x3A,  # DEC, DEC (decrease two levels)
                                  0x99, 0x08, 0x16,  # STA $1608,Y
                                  0xC2, 0x20,  # REP #$20
                                  0xA9, 0x00, 0x00,  # LDA #$0000
                                  0x99, 0x12, 0x16,  # STA $1612,Y (clear 1613)
                                  0xA2, 0x00, 0x00,  # LDX #$0000
                                  0x99, 0x11, 0x16,  # STA $1611,Y
                                  # ENTER LOOP
                                  0xE8, 0xE8,  # INX, INX
                                  0xB9, 0x11, 0x16,  # LDA $1611,Y
                                  0x18,  # CLC
                                  0x7F, 0x1C, 0x82, 0xED,  # ADC $ED821E,X (add needed exp)
                                  0x90, 0x06,  # BCC +6 (skip six bytes)
                                  0xDA, 0xBB,  # PHX, TYX
                                  0xFE, 0x13, 0x16,  # INC $1613
                                  0xFA,  # PLX
                                  0x99, 0x11, 0x16,  # STA $1611,Y
                                  0x8A,  # TXA
                                  0x4A,  # LSR
                                  0xE2, 0x20,  # SEP #$20
                                  0xD9, 0x08, 0x16,  # CMP $1608,Y
                                  0xC2, 0x20,  # REP #$20
                                  0xD0, 0xE0,  # BNE ???  bytes backwards
                                  # EXIT LOOP
                                  0xE2, 0x20,  # SEP #$20
                                  0xB9, 0x13, 0x16,  # LDA $1613,Y
                                  0x0A, 0x0A, 0x0A,  # ASL, ASL, ASL
                                  0x99, 0x13, 0x16,  # STA $1613,Y
                                  0xB9, 0x12, 0x16,  # LDA $1612,Y
                                  0x4A, 0x4A, 0x4A, 0x4A, 0x4A,  # LSR x5
                                  0x19, 0x13, 0x16,  # ORA $1613,Y
                                  0x99, 0x13, 0x16,  # STA $1613,Y
                                  0xB9, 0x12, 0x16,  # LDA $1612,Y
                                  0x0A, 0x0A, 0x0A,  # ASL, ASL, ASL
                                  0x99, 0x12, 0x16,  # STA $1612,Y
                                  0xB9, 0x11, 0x16,  # LDA $1611,Y
                                  0x4A, 0x4A, 0x4A, 0x4A, 0x4A,  # LSR x5
                                  0x19, 0x12, 0x16,  # ORA $1612,Y
                                  0x99, 0x12, 0x16,  # STA $1612,Y
                                  0xB9, 0x11, 0x16,  # LDA $1611,Y
                                  0x0A, 0x0A, 0x0A,  # ASL, ASL, ASL
                                  0x99, 0x11, 0x16,  # STA $1611,Y
                                  0x20, None, None,  # JSR to below subroutine
                                  0x20, None, None,  # JSR
                                  0x60,  # RTS

                                  # RANDOMLY LOWER ONE STAT
                                  0xBB,  # TYX
                                  0x20, 0x5A, 0x4B,  # JSR get random number
                                  0x29, 0x03,  # AND limit to 0-3
                                  0xC9, 0x00,  # CMP is it zero?
                                  0xF0, 0x04,  # BEQ skip 4 bytes
                                  0xE8, 0x3A,  # INX, DEC
                                  0x80, 0xF8,  # BRA to beginning of loop
                                  0xBD, 0x1A, 0x16,  # LDA $161A,X (random stat)
                                  0x3A,  # DEC decrease stat by 1
                                  0xC9, 0x00,  # CMP is it zero?
                                  0xD0, 0x01,  # BNE skip 1 byte
                                  0x1A,  # INC stat
                                  0x9D, 0x1A, 0x16,  # STA $161A,X
                                  0x60,  # RTS
                                  ]
    assert esper_boost_sub.bytestring.count(0x60) == 3
    boost_subs.append(esper_boost_sub)
    for boost_sub in boost_subs:
        myfs = get_appropriate_free_space(free_spaces, boost_sub.size)
        pointer = myfs.start
        free_spaces = determine_new_free_spaces(free_spaces, myfs, boost_sub.size)
        boost_sub.set_location(pointer)

        if None in boost_sub.bytestring:
            indices = [index for (index, byte_string) in enumerate(esper_boost_sub.bytestring)
                       if byte_string == 0x60]
            subpointer = indices[1] + 1
            subpointer = pointer + subpointer
            pointer1, pointer2 = subpointer & 0xFF, (subpointer >> 8) & 0xFF
            while None in esper_boost_sub.bytestring:
                index = esper_boost_sub.bytestring.index(None)
                esper_boost_sub.bytestring[index:index + 2] = [pointer1, pointer2]
            assert None not in esper_boost_sub.bytestring

        boost_sub.write(outfile_rom_buffer)

    esper_boost_sub = Substitution()
    esper_boost_sub.set_location(0x2615C)
    pointer1, pointer2 = (boost_subs[0].location, boost_subs[1].location)
    esper_boost_sub.bytestring = [pointer2 & 0xFF, (pointer2 >> 8) & 0xFF,
                                  pointer1 & 0xFF, (pointer1 >> 8) & 0xFF, ]
    esper_boost_sub.write(outfile_rom_buffer)

    esper_boost_sub.set_location(0xFFEED)
    desc = [hex2int(shorttexttable[char]) for char in 'LV - 1   ']
    esper_boost_sub.bytestring = desc
    esper_boost_sub.write(outfile_rom_buffer)
    esper_boost_sub.set_location(0xFFEF6)
    desc = [hex2int(shorttexttable[char]) for char in 'LV + 50% ']
    esper_boost_sub.bytestring = desc
    esper_boost_sub.write(outfile_rom_buffer)

    death_abuse(outfile_rom_buffer)

    return free_spaces


def manage_espers(free_spaces: List[FreeBlock], replacements: dict = None) -> List[FreeBlock]:
    espers = get_espers(infile_rom_buffer)
    random.shuffle(espers)
    for esper in espers:
        esper.generate_spells(tierless=Options_.is_flag_active('madworld'),
                              allow_ultima=not Options_.is_flag_active('penultima'))
        esper.generate_bonus()

    if replacements:
        bonus_espers = [replacements[index] for index in [15, 16]]
    else:
        bonus_espers = [esper for esper in espers if esper.id in [15, 16]]
    random.shuffle(bonus_espers)
    bonus_espers[0].bonus = 7
    bonus_espers[1].add_spell(0x2B, 1)
    for esper in sorted(espers, key=lambda esper_me: esper_me.name):
        esper.write_data(outfile_rom_buffer)

    ragnarok_id = replacements[16].id if replacements else 16
    ragnarok_id += 0x36  # offset by spell ids
    ragnarok_sub = Substitution()
    ragnarok_sub.set_location(0xC0B37)
    ragnarok_sub.bytestring = bytes([0xB2, 0x58, 0x0B, 0x02, 0xFE])
    ragnarok_sub.write(outfile_rom_buffer)
    pointer = ragnarok_sub.location + len(ragnarok_sub.bytestring) + 1

    pointer1, pointer2 = pointer & 0xFF, (pointer >> 8) & 0xFF
    c = 2
    ragnarok_sub.set_location(0xC557B)
    ragnarok_sub.bytestring = bytes([0xD4, 0xDB,
                                     0xDD, 0x99,
                                     0x6B, 0x6C, 0x21, 0x08, 0x08, 0x80,
                                     0xB2, pointer1, pointer2, c])
    ragnarok_sub.write(outfile_rom_buffer)
    ragnarok_sub.set_location(pointer)
    # CA5EA9
    ragnarok_sub.bytestring = bytes([0xB2, 0xA9, 0x5E, 0x00,  # event stuff
                                     0x5C,
                                     0xF4, 0x67,  # SFX
                                     0xB2, 0xD5, 0x9A, 0x02,  # GFX
                                     0x4B, 0x6A, 0x85,
                                     0xB2, 0xD5, 0x9A, 0x02,  # GFX
                                     0xF4, 0x8D,  # SFX
                                     0x86, ragnarok_id,  # receive esper
                                     0xFE, ])
    ragnarok_sub.write(outfile_rom_buffer)

    free_spaces = manage_esper_boosts(free_spaces)

    for esper in espers:
        log(str(esper), section='espers')

    return free_spaces


def manage_treasure(monsters: List[MonsterBlock], shops=True, no_charm_drops=False, katn_flag=False,
                    guarantee_hidon_drop=False):
    for treasure_metamorph in get_metamorphs():
        treasure_metamorph.mutate_items()
        treasure_metamorph.write_data(outfile_rom_buffer)

    for monster in monsters:
        monster.mutate_items(katn_flag, guarantee_hidon_drop)
        if no_charm_drops:
            charms = [222, 223]
            while any(charm in monster.items for charm in charms):
                monster.mutate_items()
        monster.mutate_metamorph()
        monster.write_stats(outfile_rom_buffer)

    if shops:
        buyables = manage_shops()

    if Options_.is_flag_active('ancientcave') or Options_.mode.name == 'katn':
        return

    pointer = 0x1fb600
    results = randomize_colosseum(pointer)
    wagers = {wager.itemid: win_reward for (wager, opponent, win_reward, hidden) in results}

    def ensure_striker():
        candidates = []
        for buyable in buyables:
            if buyable == 0xFF or buyable not in wagers:
                continue
            intermediate = wagers[buyable]
            if intermediate.itemid == 0x29:
                return get_item(buyable), get_item(buyable)
            if intermediate in candidates:
                continue
            if intermediate.itemid not in buyables:
                candidates.append(intermediate)

        candidates = sorted(candidates, key=lambda candidate: candidate.rank())
        candidates = candidates[len(candidates) // 2:]
        wager = random.choice(candidates)
        buy_check = [get_item(buyable).itemid for buyable in buyables
                     if buyable in wagers and wagers[buyable] == wager]
        if not buy_check:
            raise Exception('Striker pickup not ensured.')
        outfile_rom_buffer.seek(pointer + (wager.itemid * 4) + 2)
        outfile_rom_buffer.write(b'\x29')
        return get_item(buy_check[0]), wager

    chain_start_item, striker_wager = ensure_striker()

    # We now ensure that the item that starts the Striker colosseum chain is available in WoR
    chain_start_item_found = False
    all_wor_shops = [shop for shop in get_shops(infile_rom_buffer) if 81 >= shop.shopid >= 48 or shop.shopid == 84]
    for shop in all_wor_shops:
        for item in shop.items:
            # shop.items is an 8-length list of bytes
            if item == chain_start_item.itemid:
                chain_start_item_found = True
                break
    if not chain_start_item_found:
        # Get a list of shops that are relevant to the item type of the chain start item
        if chain_start_item.is_weapon:
            filtered_shops = [shop for shop in all_wor_shops if shop.shoptype_pretty in ['weapons', 'misc']]
        elif chain_start_item.is_armor:
            filtered_shops = [shop for shop in all_wor_shops if shop.shoptype_pretty in ['armor', 'misc']]
        elif chain_start_item.is_relic:
            filtered_shops = [shop for shop in all_wor_shops if shop.shoptype_pretty in ['relics', 'misc']]
        else:
            filtered_shops = [shop for shop in all_wor_shops if shop.shoptype_pretty in ['items', 'misc']]
        # Replace a random lower-tier shop item with striker_wager
        chosen_shop = random.choice(filtered_shops)
        itemblocks_in_chosen_shop = []
        for itemid in chosen_shop.items:
            item = get_item(itemid)
            # Double check that the items is not None. None will be returned for itemid 255
            if item:
                itemblocks_in_chosen_shop.append(item)
        chosen_item = random.choice(
            # Sort the shop's items by rank, then get a random item from the lowest ranked half
            sorted(itemblocks_in_chosen_shop, key=lambda item_mt: item_mt.rank())[len(itemblocks_in_chosen_shop) // 2:]
        )
        # Build a new item list because shop.items is immutable
        new_items = []
        for item in chosen_shop.items:
            if item == chosen_item.itemid:
                new_items.append(chain_start_item.itemid)
            else:
                new_items.append(item)
        chosen_shop.items = new_items
        chosen_shop.write_data(outfile_rom_buffer)
        # Look in spoiler log and find the shop that was changed and update spoiler log
        for index, shop in enumerate(randomizer_log['shops']):
            if not shop.split('\n')[0] == str(chosen_shop).split('\n')[0]:
                continue
            randomizer_log['shops'][index] = str(chosen_shop)

    for wager_obj, opponent_obj, win_obj, hidden in results:
        if wager_obj == striker_wager:
            win_name = get_item(0x29).name
        # if hidden:
        #    winname = '????????????'
        else:
            win_name = win_obj.name
        log_string = '{0:12} -> {1:12}  :  LV {2:02d} {3}'.format(wager_obj.name,
                                                                  win_name,
                                                                  opponent_obj.stats['level'],
                                                                  opponent_obj.display_name)
        log(log_string, section='colosseum')


def manage_doom_gaze():
    # patch is actually 98 bytes, but just in case
    patch_doom_gaze(outfile_rom_buffer)
    set_dialogue(0x60, '<choice> (Lift-off)<line><choice> (Find Doom Gaze)<line><choice> (Not just yet)')


def manage_chests():
    crazy_prices = Options_.is_flag_active('madworld')
    no_monsters = Options_.is_flag_active('nomiabs')
    uncapped_monsters = Options_.is_flag_active('bsiab')
    locations = get_locations(infile_rom_buffer)
    locations = sorted(locations, key=lambda location_mc: location_mc.rank())
    for location in locations:
        # if the Zozo clock is randomized, upgrade the chest from chain saw to
        # pearl lance before mutating
        if Options_.is_flag_active('random_clock'):
            if location.locid in [221, 225, 226]:
                for chest in location.chests:
                    if chest.content_type == 0x40 and chest.contents == 166:
                        chest.contents = 33

        location.mutate_chests(crazy_prices=crazy_prices, no_monsters=no_monsters, uncapped_monsters=uncapped_monsters)
    sorted(locations, key=lambda location_mc: location_mc.locid)

    for monster in get_monsters():
        monster.write_stats(outfile_rom_buffer)


def write_all_locations_misc():
    write_all_chests()
    write_all_npcs()
    write_all_events()
    write_all_entrances()


def write_all_chests():
    locations = get_locations()
    locations = sorted(locations, key=lambda location_wac: location_wac.locid)

    next_pointer = 0x2d8634
    for location in locations:
        next_pointer = location.write_chests(outfile_rom_buffer, nextpointer=next_pointer)


def write_all_npcs():
    locations = get_locations()
    locations = sorted(locations, key=lambda location_wan: location_wan.locid)

    next_pointer = 0x41d52
    for location in locations:
        if hasattr(location, 'restrank'):
            next_pointer = location.write_npcs(outfile_rom_buffer, nextpointer=next_pointer,
                                               ignore_order=True)
        else:
            next_pointer = location.write_npcs(outfile_rom_buffer, nextpointer=next_pointer)


def write_all_events():
    locations = get_locations()
    locations = sorted(locations, key=lambda location_wae: location_wae.locid)

    next_pointer = 0x40342
    for location in locations:
        next_pointer = location.write_events(outfile_rom_buffer, nextpointer=next_pointer)


def write_all_entrances():
    entrance_sets = [location.entrance_set for location in get_locations()]
    entrance_sets = entrance_sets[:0x19F]
    next_pointer = 0x1FBB00 + (len(entrance_sets) * 2) + 2
    long_next_pointer = 0x2DF480 + (len(entrance_sets) * 2) + 2
    total = 0
    for entrance_set in entrance_sets:
        total += len(entrance_set.entrances)
        next_pointer, long_next_pointer = entrance_set.write_data(outfile_rom_buffer, next_pointer,
                                                                  long_next_pointer)
        outfile_rom_buffer.seek(entrance_set.pointer + 2)
        write_multi(outfile_rom_buffer, (next_pointer - 0x1fbb00), length=2)
        outfile_rom_buffer.seek(entrance_set.longpointer + 2)
        write_multi(outfile_rom_buffer, (long_next_pointer - 0x2df480), length=2)


def manage_blitz():
    blitz_spec_pointer = 0x47a40
    # 3: X
    # 4: Y
    # 5: L
    # 6: R
    display_inputs = {0x3: 'X', 0x4: 'Y', 0x5: 'L', 0x6: 'R',
                      0x7: 'down-left', 0x8: 'down',
                      0x9: 'down-right', 0xA: 'right',
                      0xB: 'up-right', 0xC: 'up',
                      0xD: 'up-left', 0xE: 'left'}
    adjacency = {0x7: [0xE, 0x8],  # down-left
                 0x8: [0x7, 0x9],  # down
                 0x9: [0x8, 0xA],  # down-right
                 0xA: [0x9, 0xB],  # right
                 0xB: [0xA, 0xC],  # up-right
                 0xC: [0xB, 0xD],  # up
                 0xD: [0xC, 0xE],  # up-left
                 0xE: [0xD, 0x7]}  # left
    perpendicular = {0x8: [0xA, 0xE],
                     0xA: [0x8, 0xC],
                     0xC: [0xA, 0xE],
                     0xE: [0x8, 0xC]}
    diagonals = [0x7, 0x9, 0xB, 0xD]
    cardinals = [0x8, 0xA, 0xC, 0xE]
    letters = list(range(3, 7))
    log('1. left, right, left', section='blitz inputs')
    used_cmds = [[0xE, 0xA, 0xE]]
    for index in range(1, 8):
        # skip pummel
        current = blitz_spec_pointer + (index * 12)
        outfile_rom_buffer.seek(current + 11)
        length = ord(outfile_rom_buffer.read(1)) // 2
        half_length = max(length // 2, 2)
        new_length = (half_length + random.randint(0, half_length) + random.randint(1, half_length))
        new_length = min(new_length, 10)

        new_cmd = []
        while True:
            prev = new_cmd[-1] if new_cmd else None
            prev_prev = new_cmd[-2] if len(new_cmd) > 1 else None
            # dir_continue = prev and prev in adjacency
            if prev and prev in diagonals:
                dir_continue = True
            elif prev and prev in adjacency and new_length - len(new_cmd) > 1:
                dir_continue = random.choice([True, False])
            else:
                dir_continue = False

            if dir_continue:
                next_in = random.choice(adjacency[prev])
                if next_in == prev_prev and (prev in diagonals or random.randint(1, 3) != 3):
                    next_in = [previous for previous in adjacency[prev] if previous != next_in][0]
                new_cmd.append(next_in)
            else:
                if random.choice([True, False, prev in cardinals]):
                    if prev and prev not in letters:
                        candidates = [cardinal for cardinal in cardinals
                                      if cardinal not in perpendicular[prev]]
                        if prev_prev in diagonals:
                            candidates = [candidate for candidate in candidates if candidate != prev]
                    else:
                        candidates = cardinals
                    new_cmd.append(random.choice(candidates))
                else:
                    new_cmd.append(random.choice(letters))

            if len(new_cmd) == new_length:
                new_cmd_str = ''.join(map(chr, new_cmd))
                if new_cmd_str in used_cmds:
                    new_cmd = []
                else:
                    used_cmds.append(new_cmd_str)
                    break

        new_cmd += [0x01]
        while len(new_cmd) < 11:
            new_cmd += [0x00]
        blitz_string = [display_inputs[cmd_input] for cmd_input in new_cmd if cmd_input in display_inputs]
        blitz_string = ', '.join(blitz_string)
        blitz_string = '%s. %s' % (index + 1, blitz_string)
        log(blitz_string, section='blitz inputs')
        new_cmd += [(new_length + 1) * 2]
        outfile_rom_buffer.seek(current)
        outfile_rom_buffer.write(bytes(new_cmd))


def manage_dragons():
    dragon_pointers = [0xab6df, 0xc18f3, 0xc1920, 0xc2048,
                       0xc205b, 0xc36df, 0xc43cd, 0xc558b]
    dragons = list(range(0x84, 0x8c))
    assert len(dragon_pointers) == len(dragons) == 8
    random.shuffle(dragons)
    for pointer, dragon in zip(dragon_pointers, dragons):
        outfile_rom_buffer.seek(pointer)
        assert ord(outfile_rom_buffer.read(1)) == 0x4D
        outfile_rom_buffer.seek(pointer + 1)
        outfile_rom_buffer.write(bytes([dragon]))


def manage_formations(formations: List[Formation], formation_sets: List[FormationSet]) -> (
                                                                                                  List)[
                                                                                              Formation] | tuple:
    for formation_set in formation_sets:
        if len(formation_set.formations) == 4:
            for formation in formation_set.formations:
                formation.set_music(6)
                formation.set_continuous_music()
                formation.write_data(outfile_rom_buffer)

    for formation in formations:
        if formation.get_music() != 6:
            # print formation
            if formation.formid in [0xb2, 0xb3, 0xb6]:
                # additional floating continent formations
                formation.set_music(6)
                formation.set_continuous_music()
                formation.write_data(outfile_rom_buffer)

    ranked_formation_sets = sorted(formation_sets, key=lambda fs: fs.rank())
    ranked_formation_sets = [formation_set for formation_set in ranked_formation_sets if not formation_set.has_boss]
    valid_formation_sets = [formation_set for formation_set in ranked_formation_sets
                            if len(formation_set.formations) == 4]

    outdoors = list(range(0, 0x39)) + [0x57, 0x58, 0x6e, 0x6f, 0x78, 0x7c]

    # don't swap with Narshe Mines formations
    valid_formation_sets = [formation_set for formation_set in valid_formation_sets if
                            formation_set.setid not in [0x39, 0x3A] and
                            formation_set.setid not in [0xB6, 0xB8] and
                            not formation_set.sixteen_pack and
                            {formation.formid for formation in formation_set.formations} != {0}]

    outdoor_formation_sets = [formation_set for formation_set in valid_formation_sets if
                              formation_set.setid in outdoors]
    indoor_formation_set = [formation_set for formation_set in valid_formation_sets if
                            formation_set.setid not in outdoors]

    def mutate_ordering(formation_set_list: List[FormationSet]) -> List[FormationSet]:
        for index in range(len(formation_set_list) - 1):
            if random.choice([True, False, False]):
                formation_set_list[index], formation_set_list[index + 1] = (
                    formation_set_list[index + 1], formation_set_list[index])
        return formation_set_list

    for formation_set_list2 in [outdoor_formation_sets, indoor_formation_set]:
        formation_set_list2 = [formation_set for formation_set in formation_set_list2 if formation_set.swappable]
        formation_set_list2 = mutate_ordering(formation_set_list2)
        formation_set_list2 = sorted(formation_set_list2, key=lambda formation_set_mf: formation_set_mf.rank())
        for formation_set1, formation_set2 in zip(formation_set_list2, formation_set_list2[1:]):
            formation_set1.swap_formations(formation_set2)

    # just shuffle the rest of the formations within a formation set
    valid_formation_sets = [formation_set for formation_set in ranked_formation_sets if
                            formation_set not in valid_formation_sets]
    for formation_set in valid_formation_sets:
        formation_set.shuffle_formations()

    indoor_formations = {formation for formation_set in indoor_formation_set for formation in formation_set.formations}
    # include floating continent formations, which are weird
    indoor_formations |= {formation for formation in formations
                          if 0xB1 <= formation.formid <= 0xBC}
    # fanatics tower too
    indoor_formations |= {formation for formation in formations if formation.formid in
                          [0xAB, 0xAC, 0xAD,
                           0x16A, 0x16B, 0x16C, 0x16D,
                           0x18A, 0x1D2, 0x1D8, 0x1DE,
                           0x1E0, 0x1E6]}

    for formation in formations:
        formation.mutate(mp=False, mp_boost_value=Options_.get_flag_value('mpboost'))
        if formation.formid == 0x1e2:
            formation.set_music(2)  # change music for Atma fight
        if formation.formid == 0x162:
            formation.mp = 255  # Magimaster
        if formation.formid in [0x1d4, 0x1d5, 0x1d6, 0x1e2]:
            formation.mp = 100  # Triad
        formation.write_data(outfile_rom_buffer)

    return formations, formation_sets


def manage_formations_hidden(formations: List[Formation],
                             free_spaces: List[FreeBlock],
                             form_music_overrides: dict = None,
                             no_special_events=True):
    if not form_music_overrides:
        form_music_overrides = {}
    for rare_formation in formations:
        rare_formation.mutate(mp=True, mp_boost_value=Options_.get_flag_value('mpboost'))

    unused_enemies = [monster for monster in get_monsters() if monster.id in REPLACE_ENEMIES]

    def unused_validator(formation: Formation) -> bool:
        if formation.formid in NOREPLACE_FORMATIONS:
            return False
        if formation.formid in REPLACE_FORMATIONS:
            return True
        if not set(formation.present_enemies) & set(unused_enemies):
            return False
        return True

    unused_formations = list(filter(unused_validator, formations))

    def single_enemy_validator(formation: Formation) -> bool:
        if formation in unused_formations:
            return False
        if len(formation.present_enemies) != 1:
            return False
        if formation.formid in REPLACE_FORMATIONS + NOREPLACE_FORMATIONS:
            return False
        return True

    single_enemy_formations = list(filter(single_enemy_validator, formations))

    def single_boss_validator(formation: Formation) -> bool:
        if formation.formid == 0x1b5:
            # disallow GhostTrain
            return False
        if not (any([monster.boss_death for monster in formation.present_enemies]) or formation.mould in range(2, 8)):
            return False
        return True

    single_boss_formations = list(filter(single_boss_validator,
                                         single_enemy_formations))

    def safe_boss_validator(formation: Formation) -> bool:
        if formation in unused_formations:
            return False
        if formation.formid in REPLACE_FORMATIONS + NOREPLACE_FORMATIONS:
            return False
        if not any([monster.boss_death for monster in formation.present_enemies]):
            return False
        if formation.battle_event:
            return False
        if any('Phunbaba' in monster.name for monster in formation.present_enemies):
            return False
        if formation.get_music() == 0:
            return False
        return True

    safe_boss_formations = list(filter(safe_boss_validator, formations))
    sorted_bosses = sorted([monster for monster in get_monsters() if monster.boss_death],
                           key=lambda monster: monster.stats['level'])

    repurposed_formations = []
    used_graphics = []
    mutated_ues = []
    for unused_enemy, unused_formation in zip(unused_enemies, unused_formations):
        while True:
            vbf = random.choice(single_boss_formations)
            vboss = [enemy for enemy in vbf.enemies if enemy][0]

            if not vboss.graphics.graphics:
                continue

            if vboss.graphics.graphics not in used_graphics:
                used_graphics.append(vboss.graphics.graphics)
                break

        unused_enemy.graphics.copy_data(vboss.graphics)
        unused_formation.copy_data(vbf)
        unused_formation.lookup_enemies()
        eids = []
        if vbf.formid == 575:
            eids = [unused_enemy.id] + ([0xFF] * 5)
        else:
            for eid in unused_formation.enemy_ids:
                if eid & 0xFF == vboss.id & 0xFF:
                    eids.append(unused_enemy.id)
                else:
                    eids.append(eid)
        unused_formation.set_big_enemy_ids(eids)
        unused_formation.lookup_enemies()
        if no_special_events:
            unused_formation.set_event(False)

        for _ in range(100):
            while True:
                bf = random.choice(safe_boss_formations)
                boss_choices = [enemy for enemy in bf.present_enemies if enemy.boss_death]
                boss_choices = [enemy for enemy in boss_choices if enemy in sorted_bosses]
                if boss_choices:
                    break

            boss = random.choice(boss_choices)
            unused_enemy.copy_all(boss, everything=True)
            index = sorted_bosses.index(boss)
            index = mutate_index(index, len(sorted_bosses), [False, True],
                                 (-2, 2), (-1, 1))
            boss2 = sorted_bosses[index]
            unused_enemy.copy_all(boss2, everything=False)
            unused_enemy.stats['level'] = (boss.stats['level'] + boss2.stats['level']) // 2

            if unused_enemy.id in mutated_ues:
                raise OverflowError('Double mutation detected.')

            try:
                myfs = get_appropriate_free_space(free_spaces, unused_enemy.aiscriptsize)
            except MemoryError:
                continue

            break
        else:
            continue

        pointer = myfs.start
        unused_enemy.set_relative_ai(pointer)
        free_spaces = determine_new_free_spaces(free_spaces, myfs, unused_enemy.aiscriptsize)

        katn = Options_.mode.name == 'katn'
        unused_enemy.auxloc = 'Missing (Boss)'
        unused_enemy.mutate_ai(change_skillset=True, Options_=Options_)
        unused_enemy.mutate_ai(change_skillset=True, Options_=Options_)

        unused_enemy.mutate(change_skillset=True, Options_=Options_, katn=katn)
        if random.choice([True, False]):
            unused_enemy.mutate(change_skillset=True, Options_=Options_, katn=katn)
        unused_enemy.treasure_boost()
        unused_enemy.graphics.mutate_palette()
        name = randomize_enemy_name(outfile_rom_buffer, unused_enemy.id)
        unused_enemy.changed_name = name
        unused_enemy.misc1 &= (0xFF ^ 0x4)  # always show name
        unused_enemy.write_stats(outfile_rom_buffer)
        outfile_rom_buffer.flush()
        unused_enemy.read_ai(outfile_rom_buffer)
        mutated_ues.append(unused_enemy.id)
        for monster in get_monsters():
            if monster.id != unused_enemy.id:
                assert monster.aiptr != unused_enemy.aiptr

        unused_formation.set_music_appropriate()
        form_music_overrides[unused_formation.formid] = unused_formation.get_music()
        appearances = list(range(1, 14))
        if unused_enemy.stats['level'] > 50:
            appearances += [15]
        unused_formation.set_appearing(random.choice(appearances))
        unused_formation.get_special_mp()
        unused_formation.mouldbyte = 0x60
        unused_enemy.graphics.write_data(outfile_rom_buffer)
        unused_formation.misc1 &= 0xCF  # allow front and back attacks
        unused_formation.write_data(outfile_rom_buffer)
        repurposed_formations.append(unused_formation)

    lobo_formation = get_formation(0)
    for unused_formation in unused_formations:
        if unused_formation not in repurposed_formations:
            unused_formation.copy_data(lobo_formation)

    boss_candidates = list(safe_boss_formations)
    boss_candidates = random.sample(boss_candidates,
                                    random.randint(0, len(boss_candidates) // 2))
    rare_candidates = list(repurposed_formations + boss_candidates)

    zones = get_zones()
    formation_sets = []
    for zone in zones:
        for index in range(4):
            area_name = zone.get_area_name(index)
            if area_name.lower() != 'unknown':
                try:
                    formation_set = zone.fsets[index]
                except IndexError:
                    break
                if formation_set.setid != 0 and formation_set not in formation_sets:
                    formation_sets.append(formation_set)
    random.shuffle(formation_sets)

    done_fss = []

    def good_match(formation_set_gm: FormationSet, formation: Formation, multiplier: float = 1.5) -> bool:
        if formation_set_gm in done_fss:
            return False
        low = max(fo.rank() for fo in formation_set_gm.formations) * multiplier
        high = low * multiplier
        while random.randint(1, 4) == 4:
            high = high * 1.25
        if low <= formation.rank() <= high:
            return formation_set_gm.remove_redundant_formation(fsets=formation_sets,
                                                               check_only=True)
        return False

    rare_candidates = sorted(set(rare_candidates), key=lambda rare_id: rare_id.formid)
    for rare_formation in rare_candidates:
        mult = 1.2
        while True:
            formation_set_candidates = [fs for fs in formation_sets if good_match(fs, rare_formation, mult)]
            if not formation_set_candidates:
                if mult >= 50:
                    break
                else:
                    mult *= 1.25
                    continue
            # formation_set = None
            while True:
                formation_set = random.choice(formation_set_candidates)
                formation_set_candidates.remove(formation_set)
                done_fss.append(formation_set)
                result = formation_set.remove_redundant_formation(fsets=formation_sets,
                                                                  replacement=rare_formation)
                if not result:
                    continue
                formation_set.write_data(outfile_rom_buffer)
                if not formation_set_candidates:
                    break
                if random.randint(1, 5) != 5:
                    break
            break


def assign_unused_enemy_formations():
    from chestrandomizer import add_orphaned_formation, get_orphaned_formations
    get_orphaned_formations()
    siegfried = get_monster(0x37)
    chupon = get_monster(0x40)

    behemoth_formation = get_formation(0xb1)
    replace_formations = REPLACE_FORMATIONS[:]
    for enemy, music in zip([siegfried, chupon], [3, 4]):
        formation_id = replace_formations.pop()
        if formation_id not in NOREPLACE_FORMATIONS:
            NOREPLACE_FORMATIONS.append(formation_id)
        unused_formation = get_formation(formation_id)
        unused_formation.copy_data(behemoth_formation)
        unused_formation.enemy_ids = [enemy.id] + ([0xFF] * 5)
        unused_formation.lookup_enemies()
        unused_formation.set_music(music)
        unused_formation.set_appearing(random.randint(1, 13))
        add_orphaned_formation(unused_formation)


def manage_shops() -> Set[int]:
    buyables = set([])
    descriptions = []
    crazy_shops = Options_.is_flag_active('madworld')

    for shop in get_shops(infile_rom_buffer):
        shop.mutate_items(outfile_rom_buffer, crazy_shops)
        shop.mutate_misc()
        shop.write_data(outfile_rom_buffer)
        buyables |= set(shop.items)
        descriptions.append(str(shop))

    if not Options_.is_flag_active('ancientcave'):  # only logs vanilla shops anyways
        for shop_description in sorted(descriptions):
            log(shop_description, section='shops')

    return buyables


def get_namelocdict():
    if name_location_dict:
        return name_location_dict

    for line in open(LOCATION_TABLE):
        line = line.strip().split(',')
        name, encounters = line[0], line[1:]
        encounters = list(map(hex2int, encounters))
        name_location_dict[name] = encounters
        for encounter in encounters:
            assert encounter not in name_location_dict
            name_location_dict[encounter] = name

    return name_location_dict


def manage_colorize_dungeons(locations=None):
    locations = locations or get_locations()
    get_namelocdict()
    pal_dict = {}
    for location in locations:
        if location.setid in name_location_dict:
            name = name_location_dict[location.setid]
            if location.name and name != location.name:
                raise Exception('Location name mismatch.')
            if location.name is None:
                location.name = name_location_dict[location.setid]
        if location.field_palette not in pal_dict:
            pal_dict[location.field_palette] = set([])
        if location.attacks:
            formation = [formation_set for formation_set in get_fsets() if formation_set.setid == location.setid][0]
            if set(formation.formids) != {0}:
                pal_dict[location.field_palette].add(location)
        location.write_data(outfile_rom_buffer)

    from itertools import product

    done = []
    for line in open(LOCATION_PALETTE_TABLE):
        line = line.strip()
        if line[0] == '#':
            continue
        line = line.split(':')
        if len(line) == 2:
            names, palettes = tuple(line)
            names = names.split(',')
            palettes = palettes.split(',')
            backgrounds = []
        elif len(line) == 3:
            names, palettes, backgrounds = tuple(line)
            names = names.split(',')
            palettes = palettes.split(',')
            backgrounds = backgrounds.split(',')
        elif len(line) == 1:
            names, palettes = [], []
            backgrounds = line[0].split(',')
        else:
            raise Exception('Bad formatting for location palette data.')

        palettes = [int(palette, 0x10) for palette in palettes]
        backgrounds = [int(background, 0x10) for background in backgrounds]
        candidates = set()
        for index, (name, palette) in enumerate(product(names, palettes)):
            if name.endswith('*'):
                names[index] = name.strip('*')
                break
            candidates |= {location for location in locations if location.name == name and
                           location.field_palette == palette and location.attacks}

        if not candidates and not backgrounds:
            palettes, battle_backgrounds = [], []

        battle_backgrounds = {location.battlebg for location in candidates if location.attacks}
        battle_backgrounds |= set(backgrounds)

        transformer = None
        battle_backgrounds = sorted(battle_backgrounds)
        random.shuffle(battle_backgrounds)
        for background in battle_backgrounds:
            palette_number = battlebg_palettes[background]
            pointer = 0x270150 + (palette_number * 0x60)
            outfile_rom_buffer.seek(pointer)
            if pointer in done:
                # raise Exception('Already recolored palette %x' % pointer)
                continue
            raw_palette = []
            for index in range(0x30):
                raw_palette.append(read_multi(outfile_rom_buffer, length=2))
            if transformer is None:
                if background in [0x33, 0x34, 0x35, 0x36]:
                    transformer = get_palette_transformer(always=True)
                else:
                    transformer = get_palette_transformer(basepalette=raw_palette, use_luma=True)
            new_palette = transformer(raw_palette)

            outfile_rom_buffer.seek(pointer)
            for color in new_palette:
                write_multi(outfile_rom_buffer, color, length=2)
            done.append(pointer)

        for palette in palettes:
            if palette in done:
                raise Exception('Already recolored palette %x' % palette)
            outfile_rom_buffer.seek(palette)
            raw_palette = []
            for index in range(0x80):
                raw_palette.append(read_multi(outfile_rom_buffer, length=2))
            new_palette = transformer(raw_palette)
            outfile_rom_buffer.seek(palette)
            for color in new_palette:
                write_multi(outfile_rom_buffer, color, length=2)
            done.append(palette)

    if Options_.is_flag_active('random_animation_palettes') or \
            Options_.is_flag_active('swap_sprites') or \
            Options_.is_flag_active('partyparty'):
        manage_colorize_wor()
        manage_colorize_esper_world()


def manage_colorize_wor():
    transformer = get_palette_transformer(always=True)
    outfile_rom_buffer.seek(0x12ed00)
    raw_palette = []
    for index in range(0x80):
        raw_palette.append(read_multi(outfile_rom_buffer, length=2))
    new_palette = transformer(raw_palette)
    outfile_rom_buffer.seek(0x12ed00)
    for color in new_palette:
        write_multi(outfile_rom_buffer, color, length=2)

    outfile_rom_buffer.seek(0x12ef40)
    raw_palette = []
    for index in range(0x60):
        raw_palette.append(read_multi(outfile_rom_buffer, length=2))
    new_palette = transformer(raw_palette)
    outfile_rom_buffer.seek(0x12ef40)
    for color in new_palette:
        write_multi(outfile_rom_buffer, color, length=2)

    outfile_rom_buffer.seek(0x12ef00)
    raw_palette = []
    for index in range(0x12):
        raw_palette.append(read_multi(outfile_rom_buffer, length=2))
    airship_transformer = get_palette_transformer(basepalette=raw_palette)
    new_palette = airship_transformer(raw_palette)
    outfile_rom_buffer.seek(0x12ef00)
    for color in new_palette:
        write_multi(outfile_rom_buffer, color, length=2)

    for battlebg in [1, 5, 0x29, 0x2F]:
        palettenum = battlebg_palettes[battlebg]
        pointer = 0x270150 + (palettenum * 0x60)
        outfile_rom_buffer.seek(pointer)
        raw_palette = []
        for index in range(0x30):
            raw_palette.append(read_multi(outfile_rom_buffer, length=2))
        new_palette = transformer(raw_palette)
        outfile_rom_buffer.seek(pointer)
        for color in new_palette:
            write_multi(outfile_rom_buffer, color, length=2)

    for palette_index in [0x16, 0x2c, 0x2d, 0x29]:
        field_palette = 0x2dc480 + (256 * palette_index)
        outfile_rom_buffer.seek(field_palette)
        raw_palette = []
        for index in range(0x80):
            raw_palette.append(read_multi(outfile_rom_buffer, length=2))
        new_palette = transformer(raw_palette)
        outfile_rom_buffer.seek(field_palette)
        for color in new_palette:
            write_multi(outfile_rom_buffer, color, length=2)


def manage_colorize_esper_world():
    location = get_location(217)
    chosen = random.choice([1, 22, 25, 28, 34, 38, 43])
    location.palette_index = (location.palette_index & 0xFFFFC0) | chosen
    location.write_data(outfile_rom_buffer)


def manage_encounter_rate() -> None:
    # There's a series of encounter incrementors at C0/C92F (for the overworld) and C0/C2BF (for dungeons).
    #   These get added to a counter that has been running since the last encounter.
    #   If the carry is clear after this addition, no encounter occurs.
    #   Molulu sets the values to FFFF so that the carry gets added every step when the charm is on,
    #   and sets the other values to 0100 so that it takes 255 'checks' before an encounter triggers otherwise.
    #  The game generates a random number every step, and if that number is below the threat meter >> 8,
    #   then it triggers an encounter.
    if Options_.is_flag_active('dearestmolulu'):
        overworld_rates = bytes([1, 0, 1, 0, 1, 0, 0, 0,
                                 0xC0, 0, 0x60, 0, 0x80, 1, 0, 0,
                                 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                                 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        dungeon_rates = bytes([0, 0, 0, 0, 0, 0, 0, 0,
                               0xC0, 0, 0x60, 0, 0x80, 1, 0, 0,
                               0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                               0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        assert len(overworld_rates) == 32
        assert len(dungeon_rates) == 32
        encrate_sub = Substitution()
        encrate_sub.set_location(0xC29F)
        encrate_sub.bytestring = overworld_rates
        encrate_sub.write(outfile_rom_buffer)
        encrate_sub.set_location(0xC2BF)
        encrate_sub.bytestring = dungeon_rates
        encrate_sub.write(outfile_rom_buffer)
        return

    get_namelocdict()
    encrates = {}
    change_dungeons = ['floating continent', 'veldt cave', 'fanatics tower',
                       'ancient castle', 'mt zozo', "yeti's cave",
                       "gogo's domain", 'phoenix cave', "cyan's dream",
                       "ebot's rock"]

    for name in change_dungeons:
        if name == 'fanatics tower':
            encrates[name] = random.randint(2, 3)
        elif random.randint(1, 3) == 3:
            encrates[name] = random.randint(1, 3)
        else:
            encrates[name] = 0

    for name in name_location_dict:
        if not isinstance(name, str):
            continue

        for shortname in change_dungeons:
            if shortname in name:
                encrates[name] = encrates[shortname]

    zones = get_zones()
    for zone in zones:
        if zone.zoneid >= 0x40:
            zone.rates = 0
        if zone.zoneid >= 0x80:
            for setid in zone.setids:
                if setid in name_location_dict:
                    name = name_location_dict[setid]
                    zone.names[setid] = name
                    if name not in zone.names:
                        zone.names[name] = set([])
                    zone.names[name].add(setid)
            for set_id in zone.setids:
                if set_id == 0x7b:
                    continue
                if set_id in zone.names and zone.names[set_id] in encrates:
                    rate = encrates[zone.names[set_id]]
                    zone.set_formation_rate(set_id, rate)
        zone.write_data(outfile_rom_buffer)

    def rates_cleaner(rates: List[float]) -> List[int]:
        rates = [max(int(round(rate_rc)), 1) for rate_rc in rates]
        rates = [int2bytes(rate_rc, length=2) for rate_rc in rates]
        rates = [item for sublist in rates for item in sublist]
        return rates

    # 4x4 table of threat rates. One dimension is for up to four different encounter rates.
    #   The other dimension is for the normal rate, charm bangle rate, moogle charm rate,
    #   and charm bangle + moogle charm rate.
    base4 = [b_t[0] * b_t[1] for b_t in zip([0xC0] * 4, [1, 0.5, 2, 1])]
    bangle = 0.5
    moogle = 0.01
    overworld_rates = (base4 + [base * bangle for base in base4] +
                       [base * moogle for base in base4] +
                       [base * bangle * moogle for base in base4])
    overworld_rates = rates_cleaner(overworld_rates)
    encrate_sub = Substitution()
    encrate_sub.set_location(0xC29F)
    encrate_sub.bytestring = bytes(overworld_rates)
    encrate_sub.write(outfile_rom_buffer)

    # dungeon encounters: normal, strongly affected by charms,
    # weakly affected by charms, and unaffected by charms
    base = 0x70
    bangle = 0.5
    moogle = 0.01
    normal = [base, base * bangle, base * moogle, base * bangle * moogle]

    half = base // 2
    quarter = base // 4
    unaffected = [base, half + quarter + (quarter * bangle),
                  half + quarter + (quarter * moogle),
                  half + (quarter * bangle) + (quarter * moogle)]

    sbase = base * 2.5
    strong = [sbase, sbase * bangle / 2, sbase * moogle / 2, sbase * bangle * moogle / 4]

    wbase = base * 1.5
    half = wbase / 2
    weak = [wbase, half + (half * bangle), half + (half * moogle),
            (half * bangle) + (half * moogle)]

    dungeon_rates = list(zip(normal, strong, weak, unaffected))
    dungeon_rates = [item for sublist in dungeon_rates for item in sublist]
    dungeon_rates = rates_cleaner(dungeon_rates)
    encrate_sub = Substitution()
    encrate_sub.set_location(0xC2BF)
    encrate_sub.bytestring = bytes(dungeon_rates)
    encrate_sub.write(outfile_rom_buffer)


def manage_tower():
    locations = get_locations()
    randomize_tower(morefanatical=Options_.is_flag_active('morefanatical'))
    for location in locations:
        if location.locid in [0x154, 0x155] + list(range(104, 108)):
            # leo's thamasa, etc
            # TODO: figure out consequences of 0x154
            location.entrance_set.entrances = []
            if location.locid == 0x154:
                thamasa_map_sub = Substitution()
                for address in [0xBD330, 0xBD357, 0xBD309, 0xBD37E, 0xBD3A5,
                                0xBD3CC, 0xBD3ED, 0xBD414]:
                    thamasa_map_sub.set_location(address)
                    thamasa_map_sub.bytestring = bytes([0x57])
                    thamasa_map_sub.write(outfile_rom_buffer)
        location.write_data(outfile_rom_buffer)

    # Moving NPCs in the World of Ruin in the Beginner's House to prevent soft locks

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x233AA][0]
    npc.x = 108
    npc.facing = 2

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x23403][0]
    npc.x = 99
    npc.facing = 2

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x2369E][0]
    npc.x = 93
    npc.facing = 2

    # Make the guy guarding the Beginner's House to give a full heal

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x233B8][0]  # Narshe School Guard
    npc.event_addr = 0x12240  # Airship guy event address
    npc.graphics = 30
    npc.palette = 4  # School guard becomes a helpful Returner

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x2D223][0]  # Warehouse Guy
    npc.event_addr = 0x2707F  # Barking dog event address
    npc.x = 5
    npc.y = 35
    npc.graphics = 25  # In sacrifice to the byte gods, this old man becomes a dog

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x2D1FB][0]  # Follow the Elder Guy
    npc.event_addr = 0x2D223  # Warehouse Guy event address

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x2D1FF][0]  # Magic DOES exist Guy
    npc.event_addr = 0x2D1FB  # Follow the Elder Guy event address


# def manage_strange_events():
#     shadow_recruit_sub = Substitution()
#     shadow_recruit_sub.set_location(0xB0A9F)
#     shadow_recruit_sub.bytestring = bytes([0x42, 0x31])  # hide party member in slot 0
#
#     shadow_recruit_sub.write(outfile_rom_buffer)
#     shadow_recruit_sub.set_location(0xB0A9E)
#     shadow_recruit_sub.bytestring = bytes([0x41, 0x31,  # show party member in slot 0
#                                            0x41, 0x11,  # show object 11
#                                            0x31  # begin queue for party member in slot 0
#                                            ])
#     shadow_recruit_sub.write(outfile_rom_buffer)
#
#     shadow_recruit_sub.set_location(0xB0AD4)
#     shadow_recruit_sub.bytestring = bytes([0xB2, 0x29, 0xFB, 0x05, 0x45])  # Call subroutine $CFFB29, refresh objects
#     shadow_recruit_sub.write(outfile_rom_buffer)
#
#     shadow_recruit_sub.set_location(0xFFB29)
#     shadow_recruit_sub.bytestring = bytes(
#         [0xB2, 0xC1, 0xC5, 0x00,  # Call subroutine $CAC5C1 (set CaseWord bit corresponding to number of
#          # characters in party)
#          0xC0, 0xA3, 0x81, 0x38, 0xFB, 0x05,  # If ($1E80($1A3) [$1EB4, bit 3] is set), branch to $CFFB38
#          0x3D, 0x03,  # Create object $03
#          0x3F, 0x03, 0x01,  # Assign character $03 (Actor in stot 3) to party 1
#          0xFE  # return
#          ])
#     shadow_recruit_sub.write(outfile_rom_buffer)
#
#     # Always remove the boxes in Mobliz basement
#     mobliz_box_sub = Substitution()
#     mobliz_box_sub.set_location(0xC50EE)
#     mobliz_box_sub.bytestring = bytes([0xC0, 0x27, 0x81, 0xB3, 0x5E, 0x00])
#     mobliz_box_sub.write(outfile_rom_buffer)
#
#     # Always show the door in Fanatics Tower level 1,
#     # and don't change commands.
#     fanatics_sub = Substitution()
#     fanatics_sub.set_location(0xC5173)
#     fanatics_sub.bytestring = bytes([0x45, 0x45, 0xC0, 0x27, 0x81, 0xB3, 0x5E, 0x00])
#     fanatics_sub.write(outfile_rom_buffer)


def create_dimensional_vortex():
    entrance_sets = [location.entrance_set for location in get_locations()]
    entrances = []
    for entrance_set in entrance_sets:
        entrance_set.read_data(infile_rom_buffer)
        entrances.extend(entrance_set.entrances)

    entrances = sorted(set(entrances), key=lambda x: (
        x.location.locid, x.entid if (hasattr(x, 'entid') and x.entid is not None) else -1))

    # Don't randomize certain entrances
    def should_be_vanilla(entrance: locationrandomizer.Entrance) -> bool:
        """Example input looks like <0 0: 30 6>"""
        if (
                # leave Arvis's house
                (entrance.location.locid == 0x1E and entrance.entid == 1)
                # return to Arvis's house or go to the mines
                or (entrance.location.locid == 0x14 and (
                        entrance.entid == 10 or entrance.entid == 14))
                # backtrack out of the mines
                or (entrance.location.locid == 0x32 and entrance.entid == 3)
                # backtrack out of the room with Terrato while you have Vicks and Wedge
                or (entrance.location.locid == 0x2A)
                # esper world
                or (0xD7 < entrance.location.locid < 0xDC)
                # collapsing house
                or (entrance.location.locid == 0x137 or entrance.dest & 0x1FF == 0x137)
                # weird out-of-bounds entrance in the sealed gate cave
                or (entrance.location.locid == 0x180 and entrance.entid == 0)
                # Figaro interior to throne room
                or (entrance.location.locid == 0x3B and entrance.dest & 0x1FF == 0x3A)
                or (entrance.location.locid == 0x19A and entrance.dest & 0x1FF == 0x19A)
                # World of Ruin Towns
                or (entrance.location.locid == 0x1 or entrance.dest & 0x1FF == 0x1)
                # World of Balance Towns
                or (entrance.location.locid == 0x0 or entrance.dest & 0x1FF == 0x0)):
            # Kefka's Tower factory room (bottom level) conveyor/pipe
            return True
        return False

    entrances = [entrance for entrance in entrances if not should_be_vanilla(entrance)]

    # Make two entrances next to each other (like in the phantom train)
    # that go to the same place still go to the same place.
    # Also make matching entrances from different versions of maps
    # (like Vector pre/post esper attack) go to the same place
    duplicate_entrance_dict = {}
    equivalent_map_dict = {0x154: 0x157, 0x155: 0x157, 0xFD: 0xF2}

    for index, entrance in enumerate(entrances):
        for next_entrance in entrances[index + 1:]:
            c_locid = entrance.location.locid & 0x1FF
            d_locid = next_entrance.location.locid & 0x1FF
            if ((c_locid == d_locid or
                 (d_locid in equivalent_map_dict and equivalent_map_dict[d_locid] == c_locid) or
                 (c_locid in equivalent_map_dict and equivalent_map_dict[c_locid] == d_locid)) and
                    (entrance.dest & 0x1FF) == (next_entrance.dest & 0x1FF) and
                    entrance.destx == next_entrance.destx and entrance.desty == next_entrance.desty and
                    (abs(entrance.x - next_entrance.x) + abs(entrance.y - next_entrance.y)) <= 3):
                if c_locid in equivalent_map_dict:
                    duplicate_entrance_dict[entrance] = next_entrance
                else:
                    if entrance in duplicate_entrance_dict:
                        duplicate_entrance_dict[next_entrance] = duplicate_entrance_dict[entrance]
                    else:
                        duplicate_entrance_dict[next_entrance] = entrance

    entrances = [entrance for entrance in entrances if entrance not in equivalent_map_dict]

    entrances2 = list(entrances)
    random.shuffle(entrances2)
    for entrance1, entrance2 in zip(entrances, entrances2):
        entrance_string = ''
        for entrance in entrances:
            if entrance == entrance2 or (entrance.location.locid & 0x1FF) != (entrance2.dest & 0x1FF):
                continue
            value = abs(entrance.x - entrance2.destx) + abs(entrance.y - entrance2.desty)
            if value <= 3:
                break
            else:
                entrance_string += '%s ' % value
        else:
            continue
        if (entrance2.dest & 0x1FF) == (entrance1.location.locid & 0x1FF):
            continue
        entrance1.dest, entrance1.destx, entrance1.desty = entrance2.dest, entrance2.destx, entrance2.desty

    for duplicate_entrance in duplicate_entrance_dict:
        entrance = duplicate_entrance_dict[duplicate_entrance]
        duplicate_entrance.dest, duplicate_entrance.destx, duplicate_entrance.desty = (
            entrance.dest, entrance.destx, entrance.desty)

    entrance_sets = entrance_sets[:0x19F]
    next_pointer = 0x1FBB00 + (len(entrance_sets) * 2)
    long_next_pointer = 0x2DF480 + (len(entrance_sets) * 2) + 2
    total = 0

    locations = get_locations()
    for location in locations:
        for entrance in location.entrances:
            if location.locid in [0, 1]:
                entrance.dest = entrance.dest | 0x200
                # turn on bit
            else:
                entrance.dest = entrance.dest & 0x1FF
                # turn off bit

    for entrance_set in entrance_sets:
        total += len(entrance_set.entrances)
        next_pointer, long_next_pointer = entrance_set.write_data(outfile_rom_buffer, next_pointer,
                                                                  long_next_pointer)
        outfile_rom_buffer.seek(entrance_set.pointer + 2)
        write_multi(outfile_rom_buffer, (next_pointer - 0x1fbb00), length=2)
        outfile_rom_buffer.seek(entrance_set.longpointer + 2)
        write_multi(outfile_rom_buffer, (long_next_pointer - 0x2df480), length=2)


def randomize_final_party_order():
    code = bytes([0x20, 0x99, 0xAA,  # JSR $AA99
                  0xA9, 0x00,  # LDA #00
                  0xA8,  # TAY
                  0xAD, 0x1E, 0x02,  # LDA $021E (frame counter)
                  0x6D, 0xA3, 0x1F,  # ADC $1FA3 (encounter seed addition)
                  0x8D, 0x6D, 0x1F,  # STA $1F6D
                  # 21 bytes
                  0xEE, 0x6D, 0x1F,  # INC $1F6D
                  0xAD, 0x6D, 0x1F,  # LDA $1F6D
                  0x6D, 0xA3, 0x1F,  # ADC $1FA3 (encounter seed addition)
                  0xAA,  # TAX
                  0xBF, 0x00, 0xFD, 0xC0,  # LDA $C0FD00,X
                  0x29, 0x0F,  # AND $0F, Get bottom 4 bits
                  0xC9, 0x0B,  # CMP $0B
                  0xB0, 0xEC,  # BCS 20 bytes back
                  0xAA,  # TAX

                  # 14 bytes
                  0xB9, 0x05, 0x02,  # LDA $0205,Y
                  0x48,  # PHA
                  0xBD, 0x05, 0x02,  # LDA $0205,X
                  0x99, 0x05, 0x02,  # STA $0205,Y
                  0x68,  # PLA
                  0x9D, 0x05, 0x02,  # STA $0205,X

                  # 6 bytes
                  0xC8,  # INY
                  0x98,  # TYA
                  0xC9, 0x0C,  # CMP $0C
                  0x90, 0xD7,  # BCC 41 bytes back

                  0x60,  # RTS
                  ])
    outfile_rom_buffer.seek(0x3AA25)
    outfile_rom_buffer.write(code)


def dummy_item(item: ItemBlock) -> bool:
    dummied = False
    for monster in get_monsters():
        dummied = monster.dummy_item(item) or dummied

    for metamorph in get_metamorphs(infile_rom_buffer):
        dummied = metamorph.dummy_item(item) or dummied

    for location in get_locations():
        dummied = location.dummy_item(item) or dummied

    return dummied


def manage_equip_anything():
    equip_anything_sub = Substitution()
    equip_anything_sub.set_location(0x39b8b)
    equip_anything_sub.bytestring = bytes([0x80, 0x04])
    equip_anything_sub.write(outfile_rom_buffer)
    equip_anything_sub.set_location(0x39b99)
    equip_anything_sub.bytestring = bytes([0xEA, 0xEA])
    equip_anything_sub.write(outfile_rom_buffer)


def manage_full_umaro():
    full_umaro_sub = Substitution()
    full_umaro_sub.bytestring = bytes([0x80])
    full_umaro_sub.set_location(0x20928)
    full_umaro_sub.write(outfile_rom_buffer)
    if Options_.is_flag_active('random_zerker'):
        full_umaro_sub.set_location(0x21619)
        full_umaro_sub.write(outfile_rom_buffer)


def manage_opening():
    decompressor = Decompressor(0x2686C, fakeaddress=0x5000, maxaddress=0x28A60)
    decompressor.read_data(infile_rom_buffer)

    # removing white logo screen
    decompressor.writeover(0x501A, [0xEA] * 3)
    decompressor.writeover(0x50F7, [0] * 62)
    decompressor.writeover(0x5135, [0] * 0x20)
    decompressor.writeover(0x7445, [0] * 0x20)
    decompressor.writeover(0x5155, [0] * 80)

    # removing notices/symbols
    bg_color = decompressor.get_bytestring(0x7BA5, 2)
    decompressor.writeover(0x7BA7, bg_color)
    decompressor.writeover(0x52F7, [0xEA] * 3)
    decompressor.writeover(0x5306, [0] * 57)

    def mutate_palette_set(addresses: List[int], transformer: Callable = None):
        if transformer is None:
            transformer = get_palette_transformer(always=True)
        for address_mps in addresses:
            palette_mps = decompressor.get_bytestring(address_mps, 0x20)
            palette_mps = transformer(palette_mps, single_bytes=True)
            decompressor.writeover(address_mps, palette_mps)

    # clouds
    tf = get_palette_transformer(always=True)
    mutate_palette_set([0x7B63, 0x7BE3, 0x7C03, 0x7C43, 0x56D9, 0x6498], tf)

    # lightning
    mutate_palette_set([0x7B43, 0x7C23, 0x5659, 0x5679, 0x5699, 0x56B9], tf)

    # fire
    mutate_palette_set([0x7B83, 0x7BA3, 0x7BC3], tf)

    # end of the world
    mutate_palette_set([0x717D, 0x719D, 0x71BD, 0x71DD])

    # magitek
    palette = decompressor.get_bytestring(0x6470, 0x20)
    tf = get_palette_transformer(use_luma=True, basepalette=palette)
    palette = tf(palette, single_bytes=True)
    decompressor.writeover(0x6470, palette)

    table = ('! ' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' + '.' + 'abcdefghijklmnopqrstuvwxyz')
    table = dict((char, index) for (index, char) in enumerate(table))

    def replace_credits_text(address_rct: int, text_rct: str, split=False):
        original = decompressor.get_bytestring(address_rct, 0x40)
        length = original.index(0)
        original = original[:length]
        if 0xFE in original and not split:
            linebreak = original.index(0xFE)
            length = linebreak
        if len(text_rct) > length:
            raise Exception('Text too long to replace.')
        if not split:
            remaining = length - len(text_rct)
            text_rct = (' ' * (remaining // 2)) + text_rct
            while len(text_rct) < len(original):
                text_rct += ' '
        else:
            mid_text = len(text_rct) // 2
            mid_length = length // 2
            first_half, second_half = text_rct[:mid_text].strip(), text_rct[mid_text:].strip()
            text_rct = ''
            for half in (first_half, second_half):
                margin = (mid_length - len(half)) // 2
                half = (' ' * margin) + half
                while len(half) < mid_length:
                    half += ' '
                text_rct += half
                text_rct = text_rct[:-1] + chr(0xFE)
            text_rct = text_rct[:-1]
        text_rct = [table[char] if char in table else ord(char) for char in text_rct]
        text_rct.append(0)
        decompressor.writeover(address_rct, bytes(text_rct))

    from string import ascii_letters as alpha
    consonants = ''.join([letter for letter in alpha if letter not in 'aeiouy'])
    flag_names = [flag.name for flag in Options_.active_flags if len(flag.name) == 1]
    display_flags = sorted([char for char in alpha if char in flag_names])
    text = ''.join([consonants[int(index)] for index in str(seed)])
    flag_status = 'FLAGS ON' if Options_.active_flags else 'FLAGS OFF'
    display_flags = ''.join(display_flags).upper()
    replace_credits_text(0x659C, 'ffvi')
    replace_credits_text(0x65A9, 'BEYOND CHAOS CE')
    replace_credits_text(0x65C0, 'by')
    replace_credits_text(0x65CD, 'DarkSlash88')
    replace_credits_text(0x65F1, 'Based on')
    replace_credits_text(0x6605, 'Beyond Chaos by Abyssonym', split=True)
    replace_credits_text(0x6625, '')
    replace_credits_text(0x663A, 'and Beyond Chaos EX by', split=True)
    replace_credits_text(0x6661, 'SubtractionSoup        ', split=True)
    replace_credits_text(0x6682, '')
    replace_credits_text(0x668C, '')
    replace_credits_text(0x669E, '')
    replace_credits_text(0x66B1, '')
    replace_credits_text(0x66C5, 'flags')
    replace_credits_text(0x66D8, display_flags, split=True)
    replace_credits_text(0x66FB, '')
    replace_credits_text(0x670D, '')
    replace_credits_text(0x6732, flag_status)
    replace_credits_text(0x6758, 'seed')
    replace_credits_text(0x676A, text.upper())
    replace_credits_text(0x6791, 'ver.')
    replace_credits_text(0x67A7, VERSION_ROMAN)
    replace_credits_text(0x67C8, '')
    replace_credits_text(0x67DE, '')
    replace_credits_text(0x67F4, '')
    replace_credits_text(0x6809, '')
    replace_credits_text(0x6819, '')

    for address in [0x6835, 0x684A, 0x6865, 0x6898, 0x68CE,
                    0x68F9, 0x6916, 0x6929, 0x6945, 0x6959, 0x696C, 0x697E,
                    0x6991, 0x69A9, 0x69B8]:
        replace_credits_text(address, '')

    decompressor.compress_and_write(outfile_rom_buffer)


def manage_ending():
    ending_sync_sub = Substitution()
    ending_sync_sub.bytestring = bytes([0xC0, 0x07])
    ending_sync_sub.set_location(0x3CF93)
    ending_sync_sub.write(outfile_rom_buffer)


def manage_auction_house():
    new_format = {
        0x4ea4: [0x5312],  # Entry Point
        0x4ecc: [0x55b0, 0x501d],  # Cherub Down (2x)
        0x501d: [0x5460],  # Chocobo
        0x5197: [0x58fa, 0x58fa],  # Golem (2x)
        0x5312: [0x5197, 0x5197],  # Zoneseek (2x)
        0x5460: [],  # Cure Ring (terminal)
        0x55b0: [0x5b85, 0x5b85],  # Hero Ring (2x)
        0x570c: [0x5cad],  # 1/1200 Airship
        0x58fa: [0x5a39, 0x5a39],  # Golem WoR (2x)
        0x5a39: [0x4ecc, 0x4ecc],  # Zoneseek WoR (2x)
        0x5b85: [0x570c, 0x570c],  # Zephyr Cape (2x)
        0x5cad: [],  # Imp Robot (terminal)
    }
    destinations = [destination for (key, value) in new_format.items()
                    for destination in value if value is not None]
    for key in new_format:
        if key == 0x4ea4:
            continue
        assert key in destinations
    for key in new_format:
        pointer = 0xb0000 | key
        for dest in new_format[key]:
            outfile_rom_buffer.seek(pointer)
            value = ord(outfile_rom_buffer.read(1))
            if value in [0xb2, 0xbd]:
                pointer += 1
            elif value == 0xc0:
                pointer += 3
            elif value == 0xc1:
                pointer += 5
            else:
                raise Exception('Unknown auction house byte %x %x' % (pointer, value))
            outfile_rom_buffer.seek(pointer)
            oldaddr = read_multi(outfile_rom_buffer, 2)
            assert oldaddr in new_format
            assert dest in new_format
            outfile_rom_buffer.seek(pointer)
            write_multi(outfile_rom_buffer, dest, 2)
            pointer += 3

    if not Options_.is_flag_active('random_treasure'):
        return

    auction_items = [(0xbc, 0xB4EF1, 0xB5012, 0x0A45, 500),  # Cherub Down
                     (0xbd, 0xB547B, 0xB55A4, 0x0A47, 1500),  # Cure Ring
                     (0xc9, 0xB55D5, 0xB56FF, 0x0A49, 3000),  # Hero Ring
                     (0xc0, 0xB5BAD, 0xB5C9F, 0x0A4B, 3000),  # Zephyr Cape
                     ]
    items = get_ranked_items()
    itemids = [item.itemid for item in items]
    for index, auction_item in enumerate(auction_items):
        try:
            index = itemids.index(auction_item[0])
        except ValueError:
            index = 0
        index = mutate_index(index, len(items), [False, True],
                             (-3, 3), (-2, 2))
        item = items[index]
        auction_sub = Substitution()
        auction_sub.set_location(auction_item[2])
        auction_sub.bytestring = bytes([0x6d, item.itemid, 0x45, 0x45, 0x45])
        auction_sub.write(outfile_rom_buffer)

        addr = 0x303F00 + index * 6
        auction_sub.set_location(addr)
        auction_sub.bytestring = bytes([0x66, auction_item[3] & 0xff, (auction_item[3] & 0xff00) >> 8, item.itemid,
                                        # Show text auction_item[3] with item item.itemid
                                        0x94,  # Pause 60 frames
                                        0xFE])  # return
        auction_sub.write(outfile_rom_buffer)

        addr -= 0xA0000
        addr_lo = addr & 0xff
        addr_mid = (addr & 0xff00) >> 8
        addr_hi = (addr & 0xff0000) >> 16
        auction_sub.set_location(auction_item[1])
        auction_sub.bytestring = bytes([0xB2, addr_lo, addr_mid, addr_hi])
        auction_sub.write(outfile_rom_buffer)

        opening_bid = str(auction_item[4])

        set_dialogue(auction_item[3], f'<line>        “<item>”!<page><line>Do I hear {opening_bid} GP?!')


def manage_bingo(bingo_flags, size=5, difficulty='', num_cards=1, target_score=200.0):
    skills = get_ranked_spells()
    spells = [spell for spell in skills if spell.spellid <= 0x35]
    abilities = [spell for spell in skills if 0x54 <= spell.spellid <= 0xED]
    monsters = get_ranked_monsters()
    items = get_ranked_items()
    monsters = [monster for monster in monsters if
                monster.display_location and
                'missing' not in monster.display_location.lower() and
                'unknown' not in monster.display_location.lower() and
                monster.display_name.strip('_')]
    monster_skills = set([])
    for monster in monsters:
        ids = set(monster.get_skillset(ids_only=True))
        monster_skills |= ids
    abilities = [spell for spell in abilities if spell.spellid in monster_skills]
    if difficulty == 'e':
        left, right = lambda x_mb: 0, lambda x_mb: len(x_mb) // 2
    elif difficulty == 'h':
        left, right = lambda x_mb: len(x_mb) // 2, len
    else:
        left, right = lambda x_mb: 0, len

    abilities = abilities[left(abilities):right(abilities)]
    items = items[left(items):right(items)]
    monsters = monsters[left(monsters):right(monsters)]
    spells = spells[left(spells):right(spells)]

    difficulty = {'e': 'Easy',
                  'n': 'Normal',
                  'h': 'Hard'}[difficulty]
    flag_names = {'a': 'Ability',
                  'i': 'Item',
                  'm': 'Enemy',
                  's': 'Spell'}

    def generate_card(grid_gc: List[list]) -> str:
        """
        Creates a matrix for bingo!

        Inputs:
            square types (abilities, items, monsters, spells)
            size grid (default: 5)
            difficulty level (easy, normal, hard)
            number of cards to generate (default: 1)

        Example card generated:
        +------------+------------+------------+------------+------------+
        |   ENEMY    |  ABILITY   |   SPELL    |    ITEM    |  ABILITY   |
        |  Badmant   |   Plasma   |   X-Zone   | Force Shld | Bio Blast  |
        | 500 Points | 900 Points |2200 Points |2000 Points |1400 Points |
        +------------+------------+------------+------------+------------+
        |   SPELL    |    ITEM    |  ABILITY   |   SPELL    |    ITEM    |
        |    Bolt    |Czarina Gown|  Dischord  |   Haste    |Green Beret |
        | 200 Points | 500 Points | 500 Points | 400 Points | 100 Points |
        +------------+------------+------------+------------+------------+
        |   ENEMY    |   SPELL    |   ENEMY    |    ITEM    |   ENEMY    |
        | Fizerneanu |    Doom    | Blaki Carm | Wall Ring  |   Aphae    |
        | 500 Points |1000 Points |1100 Points | 200 Points | 700 Points |
        +------------+------------+------------+------------+------------+
        |  ABILITY   |    ITEM    |   SPELL    |   ENEMY    |  ABILITY   |
        |   Slide    |  Ragnarok  |   Cure 3   |    Aqui    | Magnitude8 |
        |1000 Points |1400 Points | 700 Points |1900 Points | 900 Points |
        +------------+------------+------------+------------+------------+
        |    ITEM    |   ENEMY    |    ITEM    |  ABILITY   |   SPELL    |
        |   Tiara    |  Osierry   | Aura Lance |  Sun Bath  |   Ice 2    |
        | 100 Points | 200 Points | 700 Points | 300 Points | 500 Points |
        +------------+------------+------------+------------+------------+
        """
        mid_border = '+' + '+'.join(['-' * 12] * len(grid)) + '+'
        bingo_string_gc = mid_border + '\n'
        for row in grid_gc:
            flags_gc = ['{0:^12}'.format(item.bingo_flag.upper()) for item in row]
            names = ['{0:^12}'.format(item.bingo_name) for item in row]
            scores = ['{0:^12}'.format('%s Points' % item.bingo_score)
                      for item in row]
            flags_gc = '|'.join(flags_gc)
            names = '|'.join(names)
            scores = '|'.join(scores)
            row_str = '|' + '|\n|'.join([flags_gc, names, scores]) + '|'
            bingo_string_gc += row_str + '\n'
            bingo_string_gc += mid_border + '\n'
        return bingo_string_gc.strip()

    for index in range(num_cards):
        flag_lists = {'a': list(abilities),
                      'i': list(items),
                      'm': list(monsters),
                      's': list(spells)}
        score_lists = {x: dict({}) for x in 'aims'}
        random.seed(seed + (index ** 2))
        grid, flag_grid, display_grid = [], [], []
        filename = 'bingo.%s.%s.txt' % (seed, index)
        bingo_string = 'Beyond Chaos Bingo Card %s-%s\n' % (index, difficulty)
        bingo_string += 'Seed: %s\n' % seed
        for index2 in range(size):
            for all_grids in [grid, flag_grid, display_grid]:
                all_grids.append([])
            for index3 in range(size):
                flag_options = set(bingo_flags)
                if index2 > 0 and flag_grid[index2 - 1][index3] in flag_options:
                    flag_options.remove(flag_grid[index2 - 1][index3])
                if index3 > 0 and flag_grid[index2][index3 - 1] in flag_options:
                    flag_options.remove(flag_grid[index2][index3 - 1])
                if not flag_options:
                    flag_options = set(bingo_flags)
                chosen_flag = random.choice(sorted(flag_options))
                flag_grid[index2].append(chosen_flag)
                chosen = random.choice(flag_lists[chosen_flag])
                flag_lists[chosen_flag].remove(chosen)
                score_lists[chosen_flag][chosen] = (index3, index2)
                grid[index2].append(chosen)
        for flag in bingo_flags:
            score_dict = score_lists[flag]
            chosen_flags = list(score_dict.keys())
            score_sum = sum([c.rank() for c in chosen_flags])
            multiplier = target_score / score_sum
            for chosen in chosen_flags:
                chosen.bingo_score = int(round(chosen.rank() * multiplier, -2))
                chosen.bingo_flag = flag_names[flag]
                chosen.bingo_name = (chosen.display_name if hasattr(chosen, 'display_name')
                                     else chosen.name)

        assert len(grid) == size
        assert len(grid[0]) == size
        s2 = generate_card(grid)
        bingo_string += '\n' + s2
        with open(filename, 'w+') as bingo_file:
            bingo_file.write(bingo_string)


def fix_norng_npcs():
    # move npcs who block you with norng
    npc = [npc for npc in get_npcs() if npc.event_addr == 0x8F8E][0]  # Nikeah Kid
    npc.x = 8

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x18251][0]  # Zone Eater Bouncers (All 3)
    npc.x = 38
    npc.y = 32

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x18251][1]  # Zone Eater Bouncers (All 3)
    npc.x = 46
    npc.y = 30

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x18251][2]  # Zone Eater Bouncers (All 3)
    npc.x = 33
    npc.y = 32

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x25AD5][0]  # Frantic Tzen Codger
    npc.x = 20

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x25AD9][0]  # Frantic Tzen Crone
    npc.x = 20

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x25BF9][0]  # Albrook Inn Lady
    npc.x = 55

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x145F3][0]  # Jidoor Item Scholar
    npc.x = 28

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x8077][0]  # South Figaro Codger
    npc.x = 23

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x8085][0]  # South Figaro Bandit
    npc.x = 29

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x25DDD][0]  # Seraphim Thief
    npc.y = 5

    npc = [npc for npc in get_npcs() if npc.event_addr == 0x26A0E][0]  # Kohlingen WoB Lady
    npc.x = 2
    npc.y = 17


def namingway():
    apply_namingway(outfile_rom_buffer)

    set_dialogue(0x4E, 'Rename lead character?<line><choice> (Yes)<line><choice> (No)')

    if not Options_.is_flag_active('ancientcave'):

        wor_airship = get_location(0xC)
        wor_namer = NPCBlock(pointer=None, locid=wor_airship.locid)
        attributes = {
            'graphics': 0x24, 'palette': 0, 'x': 14, 'y': 45,
            'show_on_vehicle': False, 'speed': 0,
            'event_addr': 0x209AB, 'facing': 2,
            'no_turn_when_speaking': False, 'layer_priority': 0,
            'special_anim': 0,
            'memaddr': 0, 'membit': 0, 'bg2_scroll': 0,
            'move_type': 0, 'sprite_priority': 0, 'vehicle': 0, 'npcid': 15}
        for key, value in attributes.items():
            setattr(wor_namer, key, value)
        wor_airship.npcs.append(wor_namer)

        wob_airship = get_location(0x7)
        wob_namer = NPCBlock(pointer=None, locid=wob_airship.locid)
        attributes = {
            'graphics': 0x24, 'palette': 0, 'x': 39, 'y': 12,
            'show_on_vehicle': False, 'speed': 0,
            'event_addr': 0x209AB, 'facing': 2,
            'no_turn_when_speaking': False, 'layer_priority': 0,
            'special_anim': 0,
            'memaddr': 0, 'membit': 0, 'bg2_scroll': 0,
            'move_type': 0, 'sprite_priority': 0, 'vehicle': 0, 'npcid': 22}
        for key, value in attributes.items():
            setattr(wob_namer, key, value)
        wob_airship.npcs.append(wob_namer)


def chocobo_merchant():
    baren_falls = get_location(0x9B)
    chocobo_merchant_block = NPCBlock(pointer=None, locid=baren_falls.locid)
    attributes = {
        'graphics': 0xE, 'palette': 0, 'x': 9, 'y': 6,
        'show_on_vehicle': True, 'speed': 0,
        'event_addr': 0x10B7E, 'facing': 1,
        'no_turn_when_speaking': True, 'layer_priority': 0,
        'special_anim': 0,
        'memaddr': 0, 'membit': 0, 'bg2_scroll': 0,
        'move_type': 0, 'sprite_priority': 0, 'vehicle': 1, 'npcid': 0}
    for key, value in attributes.items():
        setattr(chocobo_merchant_block, key, value)
    baren_falls.npcs.append(chocobo_merchant_block)


def manage_clock():
    hour = random.randint(0, 5)
    minute = random.randint(0, 4)
    second = random.randint(0, 4)

    # Change correct Options
    hour_sub = Substitution()
    hour_sub.bytestring = bytearray([0xE4, 0x96, 0x00] * 6)
    hour_sub.bytestring[hour * 3] = 0xE2
    hour_sub.set_location(0xA96CF)
    hour_sub.write(outfile_rom_buffer)

    minute_sub = Substitution()
    minute_sub.bytestring = bytearray([0xFA, 0x96, 0x00] * 5)
    minute_sub.bytestring[minute * 3] = 0xF8
    minute_sub.set_location(0xA96E8)
    minute_sub.write(outfile_rom_buffer)

    second_sub = Substitution()
    second_sub.bytestring = bytearray([0x16, 0x97, 0x00] * 5)
    second_sub.bytestring[second * 3] = 0x0E
    second_sub.set_location(0xA96FE)
    second_sub.write(outfile_rom_buffer)

    hour = (hour + 1) * 2
    minute = (minute + 1) * 10
    second = (second + 1) * 10
    clock_string = f'{hour}:{minute:02}:{second:02}'
    log(clock_string, section='zozo clock')

    # Change text of hints
    wrong_hours = [2, 4, 6, 8, 10, 12]
    wrong_hours.remove(hour)
    random.shuffle(wrong_hours)

    for index in range(0, 5):
        text = get_dialogue(0x416 + index)
        text = re.sub(r'\d+(?=:00)', str(wrong_hours[index]), text)
        set_dialogue(0x416 + index, text)

    # Change text that says 'Hand's pointin' at the two.'
    clock_number_text = {10: 'two', 20: 'four', 30: 'six', 40: 'eight', 50: 'ten'}

    if minute != 10:
        text = get_dialogue(0x42A)
        text = re.sub(r'two', clock_number_text[minute], text)

        set_dialogue(0x42A, text)

    wrong_seconds = [10, 20, 30, 40, 50]
    wrong_seconds.remove(second)
    random.shuffle(wrong_seconds)

    double_clue = sorted(wrong_seconds[:2])
    wrong_seconds = wrong_seconds[2:]

    text = ''
    if double_clue == [10, 20]:
        text = 'The seconds? They’re less than 30!'
    elif double_clue == [10, 30]:
        text = 'The seconds? They’re a factor of 30!'
    elif double_clue == [10, 40]:
        text = 'The seconds? They’re a square times 10.'
    elif double_clue == [10, 50]:
        text = 'The second hand’s in the clock’s top half.'
    elif double_clue == [20, 30]:
        text = 'The seconds? They’re around 25!'
    elif double_clue == [20, 40]:
        pass
        # Leave the clue as 'The seconds?  They’re divisible by 20!'.
    elif double_clue == [20, 50]:
        text = 'The seconds have four proper factors.'
    elif double_clue == [30, 40]:
        text = 'The seconds? They’re around 35!'
    elif double_clue == [30, 50]:
        text = 'The seconds are an odd prime times 10!'
    elif double_clue == [40, 50]:
        text = 'The seconds? They’re greater than 30!'

    if double_clue != [20, 40]:
        set_dialogue(0x423, text)

    text = f'Clock’s second hand’s pointin’ at {wrong_seconds[0]}.'
    set_dialogue(0x421, text)

    # In the original game, this clue says 'four' and is redundant.  It should
    # say 'two'.
    text = get_dialogue(0x425)
    text = re.sub(r'four', clock_number_text[wrong_seconds[1]], text)
    set_dialogue(0x425, text)


def manage_santa():
    for index in [0x72, 0x75, 0x7c, 0x8e, 0x17e, 0x1e1, 0x1e7, 0x1eb, 0x20f, 0x35c, 0x36d, 0x36e, 0x36f, 0x372, 0x3a9,
                  0x53a, 0x53f, 0x53f, 0x57c, 0x580, 0x5e9, 0x5ec, 0x5ee, 0x67e, 0x684, 0x686, 0x6aa, 0x6b3, 0x6b7,
                  0x6ba, 0x6ef, 0xa40, 0x717, 0x721, 0x723, 0x726, 0x775, 0x777, 0x813, 0x814, 0x818, 0x823, 0x851,
                  0x869, 0x86b, 0x86c, 0x89a, 0x89b, 0x89d, 0x8a3, 0x8a5, 0x8b1, 0x8b6, 0x8b8, 0x8c6, 0x8ca, 0x8cb,
                  0x8d2, 0x8d4, 0x913, 0x934, 0x959, 0x95d, 0x960, 0x979, 0x990, 0x9ae, 0x9e7, 0x9ef, 0xa07, 0xa35,
                  0xb76, 0xba0, 0xbc2, 0xbc9]:
        text = get_dialogue(index)
        text = re.sub(r'Kefka', 'Santa', text)
        set_dialogue(index, text)

    santa_sub = Substitution()
    santa_sub.bytestring = bytes([0x32, 0x20, 0x2D, 0x33, 0x20])
    for index in [0x24, 0x72, 0x76, 0x77, 0x78, 0x7a, 0x7c, 0x7d, 0x7f, 0x80, 0x90, 0x90, 0x94, 0x97, 0x9e, 0x9f, 0x1eb,
                  0x1eb, 0x203, 0x204, 0x205, 0x206, 0x207, 0x207, 0x207, 0x209, 0x20a, 0x20b, 0x20c, 0x20e, 0x210,
                  0x35b, 0x35c, 0x35c, 0x35d, 0x36b, 0x36c, 0x377, 0x55c, 0x55d, 0x55e, 0x56d, 0x56f, 0x570, 0x573,
                  0x575, 0x576, 0x585, 0x587, 0x66d, 0x674, 0x6b4, 0x6b5, 0x6b6, 0x80f, 0x813, 0x815, 0x819, 0x81a,
                  0x81b, 0x81c, 0x81d, 0x81e, 0x81f, 0x820, 0x821, 0x85d, 0x85e, 0x861, 0x862, 0x863, 0x866, 0x867,
                  0x868, 0x869, 0x86d, 0x86e, 0x871, 0xbab, 0xbac, 0xbad, 0xbaf, 0xbb2, 0xbc0, 0xbc1, 0xbc3, 0xbc4,
                  0xbc6, 0xbc8, 0xbca, 0xc0b]:
        text = get_dialogue(index)
        text = re.sub(r'KEFKA', 'SANTA', text)
        set_dialogue(index, text)

    battle_santa_sub = Substitution()
    battle_santa_sub.bytestring = bytes([0x92, 0x9A, 0xA7, 0xAD, 0x9A])
    for location in [0xFCB54, 0xFCBF4, 0xFCD34]:
        battle_santa_sub.set_location(location)
        battle_santa_sub.write(outfile_rom_buffer)
    for index, offset in [(0x30, 0x4), (0x5F, 0x4), (0x64, 0x1A), (0x66, 0x5), (0x86, 0x14), (0x93, 0xE), (0xCE, 0x59),
                          (0xD9, 0x9), (0xE3, 0xC), (0xE8, 0xD)]:
        battle_santa_sub.set_location(get_long_battle_text_pointer(infile_rom_buffer, index) + offset)
        battle_santa_sub.write(outfile_rom_buffer)

    battle_santa_sub = Substitution()
    battle_santa_sub.bytestring = bytes([0x92, 0x80, 0x8D, 0x93, 0x80])
    for location in [0x479B6, 0x479BC, 0x479C2, 0x479C8, 0x479CE, 0x479D4, 0x479DA]:
        battle_santa_sub.set_location(location)
        battle_santa_sub.write(outfile_rom_buffer)
    for index, offset in [(0x1F, 0x0), (0x2F, 0x0), (0x31, 0x0), (0x57, 0x0), (0x58, 0x0), (0x5A, 0x0), (0x5C, 0x0),
                          (0x5D, 0x0), (0x60, 0x0), (0x62, 0x0), (0x63, 0x0), (0x65, 0x0), (0x85, 0x0), (0x87, 0x0),
                          (0x8d, 0x0), (0x91, 0x0), (0x94, 0x0), (0x95, 0x0), (0xCD, 0x0), (0xCE, 0x0), (0xCF, 0x0),
                          (0xDA, 0x0), (0xE5, 0x0), (0xE7, 0x0), (0xE9, 0x0), (0xEA, 0x0), (0xEB, 0x0), (0xEC, 0x0),
                          (0xED, 0x0), (0xEE, 0x0), (0xEF, 0x0), (0xF5, 0x0)]:
        battle_santa_sub.set_location(get_long_battle_text_pointer(infile_rom_buffer, index) + offset)
        battle_santa_sub.write(outfile_rom_buffer)


def manage_spookiness():
    n_o_e_s_c_a_p_e_sub = Substitution()
    n_o_e_s_c_a_p_e_sub.bytestring = bytes([0x4B, 0xAE, 0x42])
    locations = [0xCA1C8, 0xCA296, 0xB198B]
    if not Options_.is_flag_active('notawaiter'):
        locations.extend([0xA89BF, 0xB1963])
    for location in locations:
        n_o_e_s_c_a_p_e_sub.set_location(location)
        n_o_e_s_c_a_p_e_sub.write(outfile_rom_buffer)

    n_o_e_s_c_a_p_e_bottom_sub = Substitution()
    n_o_e_s_c_a_p_e_bottom_sub.bytestring = bytes([0x4B, 0xAE, 0xC2])
    for location in [0xA6325]:
        n_o_e_s_c_a_p_e_bottom_sub.set_location(location)
        n_o_e_s_c_a_p_e_bottom_sub.write(outfile_rom_buffer)

    nowhere_to_run_sub = Substitution()
    nowhere_to_run_sub.bytestring = bytes([0x4B, 0xB3, 0x42])
    locations = [0xCA215, 0xCA270, 0xC8293]
    if not Options_.is_flag_active('notawaiter'):
        locations.extend([0xB19B5, 0xB19F0])
    for location in locations:
        nowhere_to_run_sub.set_location(location)
        nowhere_to_run_sub.write(outfile_rom_buffer)

    nowhere_to_run_bottom_sub = Substitution()
    nowhere_to_run_bottom_sub.bytestring = bytes([0x4B, 0xB3, 0xC2])
    locations = [0xCA7EE]
    if not Options_.is_flag_active('notawaiter'):
        locations.append(0xCA2F0)
    for location in locations:
        nowhere_to_run_bottom_sub.set_location(location)
        nowhere_to_run_bottom_sub.write(outfile_rom_buffer)


def manage_dances(dance_names=None):
    if Options_.is_flag_active('madworld'):
        spells = get_ranked_spells(infile_rom_buffer)
        dances = random.sample(spells, 32)
        dances = [spell.spellid for spell in dances]
    else:
        infile_rom_buffer.seek(0x0FFE80)
        dances = bytes(infile_rom_buffer.read(32))

        # Shuffle the geos, plus Fire Dance, Pearl Wind, Lullaby, Acid Rain,
        # and Absolute 0 because why not
        geo = ([dances[index * 4] for index in range(8)] + [dances[index * 4 + 1] for index in range(8)] +
               [0x60, 0x93, 0xA8, 0xA9, 0xBB])
        random.shuffle(geo)

        # Shuffle 1/16 beasts, plus chocobop, takedown, and wild fang, since
        # they seem on theme
        beasts = [dances[index * 4 + 3] for index in range(8)] + [0x7F, 0xFC, 0xFD]
        random.shuffle(beasts)

        # Replace 2/16 moves that are duplicated from other dances
        spells = get_ranked_spells(infile_rom_buffer)
        spells = [spell for spell in spells if spell.valid and
                  spell.spellid >= 0x36 and
                  spell.spellid not in geo and
                  spell.spellid not in beasts]
        half = len(spells) // 2

        other = []
        for index in range(8):
            while True:
                index = random.randint(0, half) + random.randint(0, half - 1)
                spellid = spells[index].spellid
                if spellid not in other:
                    break
            other.append(spellid)

        dances = geo[:16] + other[:8] + beasts[:8]
        random.shuffle(dances)

    dance_sub = Substitution()
    dance_sub.bytestring = bytes(dances)
    dance_sub.set_location(0x0FFE80)
    dance_sub.write(outfile_rom_buffer)

    # Randomize names
    bases = []
    prefixes = []
    for index in range(0, 8):
        prefixes.append([])
    index = -1

    if not dance_names:
        with open_mei_fallback(DANCE_NAMES_TABLE) as dance_file:
            dance_names = dance_file.read()
    dance_names = dance_names.split('\n')

    for line in dance_names:
        line = line.strip()
        if line[0] == '*':
            index += 1
            continue
        if index < 0:
            bases.append(line)
        elif index < 8:
            prefixes[index].append(line)

    used_bases = random.sample(bases, 8)
    used_prefixes = [''] * 8
    for index, terrain_prefixes in enumerate(prefixes):
        max_len = 11 - len(used_bases[index])
        candidates = [prefix for prefix in terrain_prefixes if len(prefix) <= max_len]
        if not candidates:
            candidates = terrain_prefixes
            used_bases[index] = None
        prefix = random.choice(candidates)
        used_prefixes[index] = prefix
        if not used_bases[index]:
            max_len = 11 - len(prefix)
            candidates = [base for base in bases if len(base) <= max_len]
            used_bases[index] = random.choice(candidates)

    dance_names = [' '.join(prefix) for prefix in zip(used_prefixes, used_bases)]
    for index, name in enumerate(dance_names):
        name = name_to_bytes(name, 12)
        outfile_rom_buffer.seek(0x26FF9D + index * 12)
        outfile_rom_buffer.write(name)

    for index, dance in enumerate(dance_names):
        from skillrandomizer import spellnames
        dance_names = [spellnames[dances[index * 4 + index2]] for index2 in range(4)]
        dancestr = '%s:\n  ' % dance
        frequencies = [7, 6, 2, 1]
        for frequency, dance_name in zip(frequencies, dance_names):
            dancestr += '{0}/16 {1:<12} '.format(frequency, dance_name)
        dancestr = dancestr.rstrip()
        log(dancestr, 'dances')

    # Randomize dance backgrounds
    backgrounds = [[0x00, 0x05, 0x06, 0x36],  # Wind Song
                   [0x01, 0x03],  # Forest Suite
                   [0x02, 0x0E, 0x2F],  # Desert Aria
                   [0x04, 0x08, 0x10, 0x13, 0x14, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C,
                    0x1D, 0x1E, 0x20, 0x24, 0x2B, 0x2D, 0x2E, 0x37],  # Love Sonata
                   [0x0B, 0x15, 0x16],  # Earth Blues
                   [0x0D, 0x23],  # Water Rondo
                   [0x09, 0x0A, 0x0C, 0x11, 0x22, 0x26, 0x28, 0x2A],  # Dusk Requiem
                   [0x12]]  # Snowman Jazz
    outfile_rom_buffer.seek(0x11F9AB)
    for index, terrain in enumerate(backgrounds):
        outfile_rom_buffer.write(bytes([random.choice(terrain)]))

    # Change some semi-unused dance associations to make more sense
    # 1C (Colosseum) from Wind Song to Love Sonata
    # 1E (Thamasa) from Wind Song to Love Sonata
    outfile_rom_buffer.seek(0x2D8E77)
    outfile_rom_buffer.write(bytes([3]))
    outfile_rom_buffer.seek(0x2D8E79)
    outfile_rom_buffer.write(bytes([3]))


def manage_cursed_encounters(formations: List[Formation], formation_sets: List[FormationSet]):
    # event formation sets that can be shuffled with cursedencounters
    good_event_formation_sets = [263, 264, 275, 276, 277, 278, 279,
                                 281, 282, 283, 285, 286, 287,
                                 297, 303, 400, 382, 402, 403,
                                 404]
    # Narshe Cave, Magitek Factory Escape, Collapsing House, South Figaro Cave WoR, Castle Figaro Basement
    bad_event_fsets = [57, 58, 108, 128, 138, 139, 140]
    event_formations = set()
    salt_formations = set()

    # Don't do: Commando, Sp Forces, Zone Eater, Naughty, L.X Magic, Phunbaba, Guardian,
    #   Merchant, Officer, Mega Armor, Master Pug, KatanaSoul, Warring Triad, Atma, Inferno,
    #   Guardian, Tier 1, 2, 3, Final Kefka, Ifrit, Shiva, Tritoch, Nerapa,
    bad_enemy_ids = {
        184, 199, 258, 264, 265,
        268, 273, 274, 276, 277,
        280, 282, 292, 293, 295,
        296, 297, 298, 299, 304,
        306, 307, 312, 313, 314,
        315, 321, 322, 323, 343,
        344, 345, 346, 347, 348,
        349, 350, 351, 355, 356,
        358, 361, 362, 363, 364,
        365, 369, 373, 381,
    }

    #Don't do: Pugs, Dummy Dullahan, Dummy Umaro, Dummy Colossus, Dummy Czar Dragon, Dummy Guardian Fight

    bad_formations = {235, 252, 443, 526, 560, 561}

    for formation in formations:
        if (formation.has_event or
                (bad_enemy_ids & set(formation.enemy_ids + formation.big_enemy_ids)) or
                formation.formid in bad_formations):
            event_formations.add(formation.formid)
            salt_formations.add((formation.formid - 1))
            salt_formations.add((formation.formid - 2))
            salt_formations.add((formation.formid - 3))
            salt_formations.add((formation.formid - 4))

    salt_formations = [formation_id for formation_id in salt_formations if formation_id not in event_formations]

    for formation_set in formation_sets:
        # code that applies FC flag to allow 16 encounters in all zones
        #   only do regular enemies, don't do sets that can risk Zone Eater or get event encounters
        if formation_set.setid < 252 or formation_set.setid in good_event_formation_sets:
            if formation_set.setid not in bad_event_fsets:
                if not [value for value in formation_set.formids if
                        value in event_formations or value in salt_formations]:
                    formation_set.sixteen_pack = True
                for index, big_enemy_id in enumerate(formation_set.formids):
                    if formation_set.formids[index] in salt_formations:
                        # any encounter that could turn into an event encounter,
                        #   keep reducing until it's not a salt or event formation
                        while (formation_set.formids[index] in event_formations or
                               formation_set.formids[index] in salt_formations):
                            formation_set.formids[index] -= 1
                        formation_set.sixteen_pack = True


def nerf_paladin_shield():
    paladin_shield = get_item(0x67)
    paladin_shield.mutate_learning(not Options_.is_flag_active('penultima'))
    paladin_shield.write_stats(outfile_rom_buffer)


def fix_flash_and_bioblaster():
    # Function to make Flash and Bio Blaster have correct names and animations when used outside of Tools
    # Because of FF6 jank, need to modify Schiller animation and share with Flash, and then modify Bomblet to share
    # with X-Kill. Not a perfect fix, but better than it was

    fix_flash_sub = Substitution()

    fix_flash_sub.set_location(0x103803)  # Change Schiller animation to a single Flash
    fix_flash_sub.bytestring = (
        [0x00, 0x20, 0xD1, 0x01, 0xC9, 0x00, 0x85, 0xB0, 0xFF, 0xBA, 0xC0, 0x89, 0x10, 0xBB, 0xC2, 0x00, 0x8A, 0x89,
         0x20,
         0xB5, 0xF1, 0xBB, 0xD2, 0x00, 0x8A, 0xD1, 0x00, 0x81, 0x00, 0x00, 0xFF])
    fix_flash_sub.write(outfile_rom_buffer)

    fix_flash_sub.set_location(0x108696)  # Make Flash have Schiller animation when used outside of Tools
    fix_flash_sub.bytestring = ([0x24, 0x81, 0xFF, 0xFF, 0xFF, 0xFF, 0x51, 0x00, 0x00, 0x9F, 0x10, 0x76, 0x81, 0x10])
    fix_flash_sub.write(outfile_rom_buffer)

    fix_flash_sub.set_location(0x1088D4)  # Change Schiller animation data to look better with one flash
    fix_flash_sub.bytestring = [0x24, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xE3, 0x00, 0x00, 0x6D, 0x10, 0x76, 0x81, 0x10]
    fix_flash_sub.write(outfile_rom_buffer)

    fix_flash_sub.set_location(0x023D45)  # Tell X-Kill to point to Bomblet for animation, instead of Flash
    fix_flash_sub.bytestring = ([0xD8])
    fix_flash_sub.write(outfile_rom_buffer)

    fix_flash_sub.set_location(0x108B82)  # Make Bomblet have X-Kill animation instead of nothing
    fix_flash_sub.bytestring = ([0xFF, 0xFF, 0x7F, 0x02, 0xFF, 0xFF, 0x35, 0x35, 0x00, 0xCC, 0x1B, 0xFF, 0xFF, 0x10])
    fix_flash_sub.write(outfile_rom_buffer)

    fix_bio_blaster_sub = Substitution()  # Make Bio Blaster have correct animation when used outside of Tools
    fix_bio_blaster_sub.set_location(0x108688)
    fix_bio_blaster_sub.bytestring = (
        [0x7E, 0x02, 0xFF, 0xFF, 0x4A, 0x00, 0x00, 0x00, 0xEE, 0x63, 0x03, 0xFF, 0xFF, 0x10])
    fix_bio_blaster_sub.write(outfile_rom_buffer)

    fix_bio_blaster_sub.set_location(
        0x02402D)  # Change Super Ball Item Animatino to point to 0xFFFF (No spell) animation
    fix_bio_blaster_sub.bytestring = ([0xFF])
    fix_bio_blaster_sub.write(outfile_rom_buffer)

    fix_bio_blaster_sub.set_location(0x108DA4)  # Tell 0xFFFF (No spell) to have Super Ball animation
    fix_bio_blaster_sub.bytestring = (
        [0x0E, 0x02, 0xFF, 0xFF, 0xFF, 0xFF, 0xD1, 0x00, 0x00, 0xCA, 0x10, 0x85, 0x02, 0x03])
    fix_bio_blaster_sub.write(outfile_rom_buffer)

    fix_bio_blaster_name_sub = Substitution()  # Change Spell Name to BioBlaster
    fix_bio_blaster_name_sub.set_location(0x26F971)
    fix_bio_blaster_name_sub.bytestring = ([0x81, 0xa2, 0xa8, 0x81, 0xa5, 0x9a, 0xac, 0xad, 0x9e, 0xab])
    fix_bio_blaster_name_sub.write(outfile_rom_buffer)


def sprint_shoes_hint():
    sprint_shoes = get_item(0xE6)
    spell_id = sprint_shoes.features['learnspell']
    spell_name = get_spell(spell_id).name
    hint = f'Equip relics to gain a variety of abilities!<page>These teach me {spell_name}!'

    set_dialogue(0xb8, hint)

    # disable fade to black relics tutorial
    sprint_sub = Substitution()
    sprint_sub.set_location(0xA790E)
    sprint_sub.bytestring = b'\xFE'
    sprint_sub.write(outfile_rom_buffer)


def sabin_hint(commands: Dict[str, CommandBlock]):
    sabin = get_character(0x05)
    command_id = sabin.battle_commands[1]
    if not command_id or command_id == 0xFF:
        command_id = sabin.battle_commands[0]

    command = [command for command in commands.values() if command.id == command_id][0]
    hint = 'My husband, Duncan, is a world-famous martial artist!<page>He is a master of the art of {}.'.format(
        command.name)

    set_dialogue(0xb9, hint)


def house_hint():
    skill = get_collapsing_house_help_skill()

    hint = f'There are monsters inside! They keep {skill}ing everyone who goes in to help. You using suitable Relics?'
    set_dialogue(0x8A4, hint)


def start_with_random_espers():
    outfile_rom_buffer.seek(0xC9ab6)
    outfile_rom_buffer.write(bytes([0xB2, 0x00, 0x50, 0xF0 - 0xCA]))

    espers = sorted(get_espers(infile_rom_buffer), key=lambda esper: esper.rank)

    num_espers = 4 + random.randint(0, 2) + random.randint(0, 1)
    outfile_rom_buffer.seek(0x305000)
    bytestring = bytes([0x78, 0x0e, 0x78, 0x0f])
    for _ in range(num_espers):
        rank = espers[0].rank
        while rank < 5 and random.randint(1, 3) == 3:
            rank += 1
        candidates = [esper for esper in espers if esper.rank == rank]
        while not candidates:
            candidates = [esper for esper in espers if esper.rank <= rank]
            rank += 1

        esper = random.choice(candidates)
        espers.remove(esper)
        bytestring += bytes([0x86, 0x36 + esper.id])
    bytestring += bytes([0xFE])
    outfile_rom_buffer.write(bytestring)


def the_end_comes_beyond_katn():
    outfile_rom_buffer.seek(0x25f821)
    outfile_rom_buffer.write(bytes([0xEA] * 5))

    outfile_rom_buffer.seek(0x25f852)
    outfile_rom_buffer.write(bytes([0xEA] * 5))

    outfile_rom_buffer.seek(0xcbfa3)
    outfile_rom_buffer.write(bytes([0xf6, 0xf1, 0x00, 0x00, 0xbb, 0xfe]))


def the_end_comes_beyond_crusader():
    outfile_rom_buffer.seek(0x25f821)
    outfile_rom_buffer.write(bytes([0xEA] * 5))

    outfile_rom_buffer.seek(0x25f852)
    outfile_rom_buffer.write(bytes([0xEA] * 5))

    outfile_rom_buffer.seek(0xc203f)
    outfile_rom_buffer.write(bytes([0x97, 0xf6, 0xf1, 0x00, 0x00, 0x5c, 0xbb, 0xfe]))


def expand_rom():
    outfile_rom_buffer.seek(0, 2)
    if outfile_rom_buffer.tell() < 0x400000:
        expand_sub = Substitution()
        expand_sub.set_location(0x3fffff)
        expand_sub.bytestring = b'\x00'
        expand_sub.write(outfile_rom_buffer)


def validate_rom_expansion():
    # Some randomizer functions may expand the ROM past 32mbit. (ExHIROM)
    # Per abyssonym's testing, this needs bank 00 to be mirrored in bank 40.
    # While the modules that may use this extra space already handle this,
    # BC may make further changes to bank 00 afterward, so we need to mirror
    # the final version.
    outfile_rom_buffer.seek(0, 2)
    romsize = outfile_rom_buffer.tell()
    if romsize > 0x400000:
        # Standardize on 48mbit for ExHIROM, for now
        if romsize < 0x600000:
            expand_sub = Substitution()
            expand_sub.set_location(0x5fffff)
            expand_sub.bytestring = b'\x00'
            expand_sub.write(outfile_rom_buffer)

        outfile_rom_buffer.seek(0)
        bank = outfile_rom_buffer.read(0x10000)
        outfile_rom_buffer.seek(0x400000)
        outfile_rom_buffer.write(bank)


def diverge():
    for line in open(DIVERGENT_TABLE):
        line = line.strip().split('#')[0]  # Ignore everything after '#'
        if not line:
            continue
        split_line_d = line.strip().split(' ')
        address = int(split_line_d[0], 16)
        data = bytes([int(byte, 16) for byte in split_line_d[1:]])
        outfile_rom_buffer.seek(address)
        outfile_rom_buffer.write(data)


def initialize_esper_allocation_table():
    num_espers = 27
    data = b'\xff' * num_espers * 2
    outfile_rom_buffer.seek(
        JUNCTION_MANAGER_PARAMETERS['esper-allocations-address'])
    outfile_rom_buffer.write(data)


def junction_everything(jm: JunctionManager,
                        commands: Dict[str, CommandBlock]):
    jm.set_seed(seed)

    monsters = get_monsters()
    for monster in monsters:
        if hasattr(monster, 'changed_name'):
            # monster_index = monster.id
            old_length = len(monster.name.rstrip('_'))
            old_suffix = jm.monster_names[monster.id][old_length:]
            jm.monster_names[monster.id] = monster.changed_name + old_suffix

    for k, v in sorted(jm.junction_short_names.items()):
        if commands["gprain"].name != "gprain" and v.lower() == "sos gp rain":
            jm.junction_short_names[k] = "SOS " + commands["gprain"].name
        if commands["runic"].name != "runic" and v.lower() == "sos runic":
            jm.junction_short_names[k] = "SOS " + commands["runic"].name
        if commands["dance"].name != "dance" and v.lower() == "sos dance":
            jm.junction_short_names[k] = "SOS " + commands["dance"].name

    if Options_.is_flag_active('espercutegf'):
        jm.add_junction(None, 'esper_magic', 'whitelist')
        jm.add_junction(None, 'esper_counter', 'whitelist')
        jm.add_junction(None, 'esper_attack', 'whitelist')
        jm.add_junction(None, 'esper_defense', 'whitelist')
        jm.add_junction(None, 'caller', 'whitelist')
        jm.activated = True

    if Options_.is_flag_active('espffect'):
        espers = sorted(jm.esper_tags.keys())
        jm.randomize_generous(espers, 'esper', True)
        jm.activated = True

    if (Options_.is_flag_active('effectmas')
            or Options_.is_flag_active('effectory')):
        banned_equips = set()
        characters = get_characters()
        for character in characters:
            if character.id >= 14:
                continue
            for equip_type in ['weapon', 'shield', 'helm', 'armor',
                               'relic1', 'relic2']:
                outfile_rom_buffer.seek(character.address + equip_offsets[equip_type])
                equip_id = ord(outfile_rom_buffer.read(1))
                banned_equips.add(equip_id)

        items = get_ranked_items()
        valid_equips = [item for item in items if item.equippable & 0x3fff
                        and 1 <= item.itemtype & 0xf <= 5
                        and item.itemid in jm.equip_tags
                        and item.itemid not in banned_equips]

        equips = []
        if Options_.is_flag_active('effectmas'):
            equips += [item.itemid for item in valid_equips
                       if 1 <= item.itemtype & 0xf <= 4]

        if Options_.is_flag_active('effectory'):
            equips += [item.itemid for item in valid_equips
                       if item.itemtype & 0xf == 5]

        jm.randomize_sparing(equips, 'equip', True)
        if options.Options_.is_flag_active('questionablecontent'):
            chosen_items = [item for item in items if item.itemid in jm.equip_whitelist]
            for item in chosen_items:
                if jm.equip_whitelist[item.itemid]:
                    item.mutate_name(character='!')
                    item.write_stats(outfile_rom_buffer)
        jm.activated = True

        shields = [item.itemid for item in items if item.equiptype == 'shield']
        for equip_type in ['weapon', 'shield', 'helm', 'armor',
                           'relic1', 'relic2']:
            pool = [item for item in items if item.equippable
                    and equip_type.startswith(item.equiptype)]
            if equip_type == 'shield':
                pool += [item for item in items if item.equippable
                         and item.equiptype == 'weapon']
            fallback = [
                item for item in pool if not (item.has_disabling_status or
                                              jm.equip_whitelist[item.itemid])]
            pool = [item.itemid for item in pool]
            fallback = [item.itemid for item in fallback]
            pool.insert(0, 0xff)
            fallback.insert(0, 0xff)
            for character in characters:
                if character.id != 15 and character.id < 29:
                    continue
                equip_address = character.address + equip_offsets[equip_type]
                outfile_rom_buffer.seek(equip_address)
                equip_id = ord(outfile_rom_buffer.read(1))
                junctions = jm.equip_whitelist[equip_id]
                if junctions:
                    if equip_id in pool:
                        old_rank = pool.index(equip_id) / (len(pool) - 1)
                    elif equip_type == 'weapon' and equip_id in shields:
                        old_rank = shields.index(equip_id) / (len(shields) - 1)
                    else:
                        old_rank = random.random()
                    index = int(round(old_rank * (len(fallback) - 1)))
                    new_equip = fallback[index]
                    # old_item = [i for i in items if i.itemid == equip_id][0]
                    # new_item = [i for i in items if i.itemid == new_equip][0]
                    outfile_rom_buffer.seek(equip_address)
                    outfile_rom_buffer.write(bytes([new_equip]))

    banned_bosses = set(early_bosses + solo_bosses)
    if Options_.is_flag_active('effectster'):
        monsters = get_monsters()
        jm.reseed('premonster')
        valid_monsters = []
        for monster in monsters:
            if monster.id in banned_bosses:
                continue
            if monster.id not in jm.monster_tags:
                continue
            if (monster.oldlevel / 99) > (jm.random.random() ** 3):
                valid_monsters.append(monster.id)

        jm.randomize_sparing(valid_monsters, 'monster', True)
        statuses = {'morph', 'imp', 'zombie', 'dance'}
        statuses = {jm.get_category_index('status', name) for name in statuses}
        jm.randomize_generous(statuses, 'status', True)
        jm.activated = True

    if Options_.is_flag_active('treaffect'):
        monsters = get_monsters()
        for monster in monsters:
            if monster.id not in banned_bosses:
                continue
            for item in monster.steals + monster.drops:
                if item is None:
                    continue
                index = item.itemid
                for effect_index in jm.equip_whitelist[index]:
                    jm.add_junction(monster.id, effect_index, 'blacklist',
                                    force_category='monster')
        JUNCTION_MANAGER_PARAMETERS['monster-equip-steal-enabled'] = 1
        JUNCTION_MANAGER_PARAMETERS['monster-equip-drop-enabled'] = 1

    if Options_.is_flag_active('jejentojori'):
        #Ensure merchants die to mp in case of Astral being innate on Locke
        for monster in monsters:
            if 'merchant' in monster.name.lower():
                monster.misc1 |= 0x01
                monster.write_stats(outfile_rom_buffer)

        for character in get_characters():
            if character.id >= 0x10:
                continue
            if not hasattr(character, 'relic_selection'):
                continue
            junctions = jm.equip_whitelist[character.relic_selection]
            for junction in junctions:
                jm.add_junction(character.id, junction, 'whitelist',
                                force_category='character')

    if jm.activated:
        jm.match_esper_monster_junctions()

    jm.set_parameters(JUNCTION_MANAGER_PARAMETERS)


def randomize(connection: Pipe = None, **kwargs) -> str | None:
    """
    The main function which takes in user arguments and creates a log
    and outfile. Returns a path (as str) to the output file.
    TODO: Document parameters, args, etc.
    """
    try:
        global outfile_rom_path, infile_rom_path, \
            flags, seed, \
            infile_rom_buffer, outfile_rom_buffer, \
            ALWAYS_REPLACE, NEVER_REPLACE, gui_connection

        application = kwargs.get('application', None)

        if not application:
            # The console should supply these kwargs
            infile_rom_path = kwargs.get('infile_rom_path')
            outfile_rom_path = kwargs.get('outfile_rom_path')
        elif application in ['console', 'gui', 'tester']:
            # The gui (beyondchaos.py) should supply these kwargs
            infile_rom_path = kwargs.get('infile_rom_path')
            outfile_rom_path = kwargs.get('outfile_rom_path')
            set_parent_pipe(connection)
        elif application == 'web':
            infile_rom_buffer = kwargs.get('infile_rom_buffer')
            outfile_rom_buffer = kwargs.get('outfile_rom_buffer')
            set_parent_pipe(connection)
        full_seed = kwargs.get('seed')

        sleep(0.5)
        pipe_print(f'You are using Beyond Chaos CE Randomizer version {VERSION}.')
        if BETA:
            pipe_print('WARNING: This version is a beta! Things may not work correctly.')

        config_infile_rom_path = ''
        config_outfile_rom_path = ''

        flag_help_text = ''
        if not application:
            # If an input rom path is supplied, use that. Otherwise, check config.ini to see if a previously used
            #    input path was used. If so, prompt the user if they would like to use the saved input path. Otherwise
            #    prompt the user for the directory of their FF3 rom file.
            # TODO: Refactor this part?
            if not infile_rom_path:
                config_infile_rom_path = config.get('Settings', 'input_path', fallback='')
                config_outfile_rom_path = config.get('Settings', 'output_path', fallback='')
                previous_input = f' (blank for default: {config_infile_rom_path})' if config_infile_rom_path else ''
                infile_rom_path = input(f'Please input the file name of your copy of '
                                        f'the FF3 US 1.0 rom{previous_input}:\n> ').strip()
                pipe_print()

            # If there is a saved rom path and the user input was blank, use the saved rom path
            if config_infile_rom_path and not infile_rom_path:
                infile_rom_path = config_infile_rom_path

            # Correct for Windows paths given with surrounding quotes
            # (e.g. drag & drop onto console when path includes a space)
            if infile_rom_path.startswith("'") and infile_rom_path.endswith("'"):
                infile_rom_path = infile_rom_path.strip("'")
            infile_rom_path = os.path.abspath(infile_rom_path)

            outfile_rom_path = kwargs.get('outfile_rom_path')
            if not outfile_rom_path:
                # If no previous directory or an invalid directory was obtained from bcce.cfg,
                #   default to the ROM's directory
                if not config_outfile_rom_path or not os.path.isdir(os.path.normpath(config_outfile_rom_path)):
                    config_outfile_rom_path = os.path.dirname(infile_rom_path)

                while True:
                    # Input loop to make sure we get a valid directory
                    previous_output = f' (blank for default: {config_outfile_rom_path})'
                    try:
                        outfile_rom_path = input(
                            f'Please input the directory to place the randomized ROM file. '
                            f'{previous_output}:\n> ').strip()
                        pipe_print()
                    except EOFError:
                        raise RuntimeError('The GUI did not supply an output directory for the randomized ROM.')

                    if config_outfile_rom_path and not outfile_rom_path:
                        outfile_rom_path = config_outfile_rom_path
                    if outfile_rom_path.startswith("'") and outfile_rom_path.endswith("'"):
                        outfile_rom_path = outfile_rom_path.strip("'")

                    if os.path.isdir(outfile_rom_path):
                        # Valid directory received. Break out of the loop.
                        break
                    else:
                        pipe_print('That output directory does not exist. Please try again.')

            try:
                with open(infile_rom_path, 'rb') as infile:
                    infile.read()

            except IOError:
                response = input('File not found. Would you like to search the current directory \n'
                                 'for a valid FF3 1.0 rom? (y/n) ')
                if response and response[0].lower() == 'y':
                    for filename in sorted(os.listdir('.')):
                        stats = os.stat(filename)
                        size = stats.st_size
                        if size not in [3145728, 3145728 + 0x200]:
                            continue

                        try:
                            with open(filename, 'r+b') as infile:
                                data = infile.read()
                        except IOError:
                            continue

                        if size == 3145728 + 0x200:
                            data = data[0x200:]
                        file_hash = md5(data).hexdigest()
                        if file_hash in [MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2]:
                            infile_rom_path = filename
                            break
                    else:
                        raise Exception('File not found.')
                else:
                    raise Exception('File not found.')
                pipe_print('Success! Using valid rom file: %s\n' % infile_rom_path)
            del infile

            flag_help_text = '''!   Recommended new player flags
        -   Use all flags EXCEPT the ones listed'''

        if full_seed:
            full_seed = str(full_seed).strip()
        else:
            if application:
                raise Exception('No seed was supplied.')
            full_seed = input('Please input a seed value (blank for a random '
                              'seed):\n> ').strip()
            pipe_print()

            if '.' not in full_seed:
                speeddials = get_config_items('Speeddial').items()
                mode_num = None
                while mode_num not in range(len(ALL_MODES)):
                    pipe_print('Available modes:\n')
                    for index, mode in enumerate(ALL_MODES):
                        pipe_print('{}. {} - {}'.format(index + 1, mode.name, mode.description))
                    mode_str = input('\nEnter desired mode number or name:\n').strip()
                    try:
                        mode_num = int(mode_str) - 1
                    except ValueError:
                        for index, monster in enumerate(ALL_MODES):
                            if monster.name == mode_str:
                                mode_num = index
                                break
                mode = ALL_MODES[mode_num]
                allowed_flags = [flag for flag in NORMAL_FLAGS if
                                 flag.category == 'flags' and
                                 flag.name not in mode.prohibited_flags]
                pipe_print()
                for flag in sorted(allowed_flags, key=lambda flag: flag.name):
                    pipe_print(flag.name + ' - ' + flag.long_description)
                pipe_print(flag_help_text + '\n')
                pipe_print('Save frequently used flag sets by adding 0: through 9: before the flags.')
                for speeddial_number, speeddial_flags in speeddials:
                    pipe_print('\t' + speeddial_number + ': ' + speeddial_flags)
                pipe_print()
                flags = input('Please input your desired flags (blank for '
                              'all of them):\n> ').strip()
                if flags == '!':
                    flags = '-dfklu partyparty makeover johnnydmad'

                is_speeddialing = re.search('^[0-9]$', flags)
                if is_speeddialing:
                    for speeddial_number, speeddial_flags in speeddials:
                        if speeddial_number == flags[:1]:
                            flags = speeddial_flags.strip()
                            break

                saving_speeddial = re.search('^[0-9]:', flags)
                if saving_speeddial:
                    set_config_value('Speeddial', flags[:1], flags[3:].strip())
                    pipe_print('Flags saved under speeddial number ' + str(flags[:1]))
                    flags = flags[3:]

                full_seed = '|%i|%s|%s' % (mode_num + 1, flags, full_seed)
                pipe_print()

        try:
            version, mode_str, flags, seed = tuple(full_seed.split('|'))
        except ValueError:
            raise ValueError('Seed should be in the format <version>|<mode>|<flags>|<seed>')
        mode_str = mode_str.strip()
        mode_num = None
        try:
            mode_num = int(mode_str) - 1
        except ValueError:
            for index, monster in enumerate(ALL_MODES):
                if monster.name == mode_str:
                    mode_num = index
                    break

        if mode_num not in range(len(ALL_MODES)):
            raise Exception('Invalid mode specified')
        Options_.mode = ALL_MODES[mode_num]

        seed = seed.strip()
        if not seed:
            seed = int(time())
        else:
            seed = int(seed)
        seed = seed % (10 ** 10)
        reseed()

        rng = Random(seed)

        outlog = None
        if not application or application != 'web':
            if '.' in infile_rom_path:
                tempname = os.path.basename(infile_rom_path).rsplit('.', 1)
            else:
                tempname = [os.path.basename(infile_rom_path), 'smc']

            outfile_rom_path = os.path.join(outfile_rom_path,
                                            '.'.join([os.path.basename(tempname[0]),
                                                      str(seed), tempname[1]]))
            outlog = os.path.join(os.path.dirname(outfile_rom_path),
                                  '.'.join([os.path.basename(tempname[0]),
                                            str(seed), 'txt']))

            if infile_rom_path != config_infile_rom_path or outfile_rom_path != config_outfile_rom_path:
                set_config_value('Settings', 'input_path', str(infile_rom_path))
                set_config_value('Settings', 'output_path', str(os.path.dirname(outfile_rom_path)))

            infile_rom_buffer = BytesIO(open(infile_rom_path, 'rb').read())
            outfile_rom_buffer = BytesIO(open(infile_rom_path, 'rb').read())

            if len(outfile_rom_buffer.read()) % 0x400 == 0x200:
                pipe_print('NOTICE: Headered ROM detected. Output file will have no header.')
                outfile_rom_buffer = outfile_rom_buffer[0x200:]
                # infile_rom_path = '.'.join([tempname[0], 'unheadered', tempname[1]])
                # with open(infile_rom_path, 'w+b') as f:
                #     f.write(data)

            rom_hash = md5(outfile_rom_buffer.getbuffer()).hexdigest()
            if rom_hash not in [MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2] and \
                    not application:
                pipe_print('WARNING! The md5 hash of this file does not match the known '
                           'hashes of the english FF6 1.0 rom!')
                response = input('Continue? y/n ')
                if not (response and response.lower()[0] == 'y'):
                    return

            # Before randomizing, test to make sure the supplied output directory is writable
            if not os.access(os.path.dirname(outfile_rom_path), os.W_OK):
                if gui_connection:
                    gui_connection.send(PermissionError('The randomizer does not have '
                                                        'write permissions to the given ROM output directory.'))
                    return
                else:
                    raise PermissionError('The randomizer does not have write permissions '
                                          'to the given ROM output directory.')

        flags = flags.lower()
        activation_string = Options_.activate_from_string(flags)

        # Check expboost, gpboost, and mpboost values
        for flag_name in ['expboost', 'gpboost', 'mpboost', 'randomboost']:
            if flag := Options_.is_flag_active(flag_name):
                while True:
                    try:
                        if str(flag.value).lower() == 'random':
                            # TODO: Make better weighting?
                            # Get a random value for these seeds based on standard deviation.
                            flag.value = 0
                            if flag.name == 'randomboost':
                                # Randomboost has a wider range, usually between 1.5 and 4.5,
                                while (flag.value < 0.25):
                                    flag.value = rng.gauss(float(flag.default_value) + 1, .70)
                            else:
                                # Boost flags generally roll between .5x and 1.6x, slightly favoring positive.
                                while (flag.value < 0.25):
                                    flag.value = rng.gauss(float(flag.default_value) + .1, .25)
                            flag.value = round(flag.value, 2)
                            #while flag.value == flag.default_value:
                            #    flag.value = round(random.uniform(flag.minimum_value, flag.maximum_value), 2)
                            break
                        elif flag.maximum_value < float(flag.value):
                            error_message = ('The supplied value for ' +
                                             flag_name +
                                             ' was greater than the maximum '
                                             'allowed value of ' +
                                             str(flag.maximum_value) + '.')
                        elif float(flag.value) < flag.minimum_value:
                            error_message = ('The supplied value for ' +
                                             flag_name +
                                             ' was less than the minimum '
                                             'allowed value of ' +
                                             str(flag.minimum_value) + '.')
                        elif not flag.value or type(flag.value) == bool or str(flag.value).lower() == 'nan':
                            error_message = ('No value was supplied for ' +
                                             flag_name +
                                             '.')
                        else:
                            flag.value = float(flag.value)
                            if flag.input_type == 'integer':
                                flag.value = int(flag.value)
                            break
                    except ValueError:
                        error_message = 'The supplied value for ' + flag_name + ' was not a number.'

                    if not application:
                        # Users in the GUI or web cannot fix the flags after generation begins, so deactivate the flag.
                        pipe_print(error_message + ' Deactivating flag.')
                        Options_.deactivate_flag(flag_name)
                        break
                    flag.value = input(error_message + ' Please enter a multiplier between ' + str(flag.minimum_value) +
                                       ' and ' + str(flag.maximum_value) + ' for ' + flag_name + '.\n>')

        if not application or application != 'web':
            if version and version != VERSION:
                pipe_print('WARNING! Version mismatch! '
                           'This seed will not produce the expected result!')
        log_string = ('Using seed: %s|%s|%s|%s' %
                       (VERSION,
                        Options_.mode.name,
                        ' '.join(
                            [flag.name if isinstance(flag.value, bool) else
                             flag.name + ':' + str(flag.value) for flag in Options_.active_flags]),
                        seed))
        pipe_print(log_string)
        log(log_string, section=None)
        log('This is a game guide generated for the Beyond Chaos CE FF6 Randomizer.',
            section=None)
        log('For more information, visit https://github.com/FF6BeyondChaos/BeyondChaosRandomizer',
            section=None)

        commands = commands_from_table(COMMAND_TABLE)
        commands = {command.name: command for command in commands}

        load_characters(infile_rom_buffer, force_reload=True)
        characters = get_characters()

        tm = gmtime(seed)
        if tm.tm_mon == 12 and (tm.tm_mday == 24 or tm.tm_mday == 25):
            Options_.activate_flag('christmas', True)
            activation_string += 'CHRISTMAS MODE ACTIVATED\n'
        elif tm.tm_mon == 10 and tm.tm_mday == 31:
            Options_.activate_flag('halloween', True)
            activation_string += "ALL HALLOWS' EVE MODE ACTIVATED\n"

        pipe_print(activation_string)

        if Options_.is_flag_active('randomboost'):
            if int(Options_.get_flag_value('randomboost')) == 0 or int(Options_.get_flag_value('randomboost')) == 255:
                set_randomness_multiplier(None)
            else:
                set_randomness_multiplier(int(Options_.get_flag_value('randomboost')))
        if Options_.is_flag_active('madworld'):
            set_randomness_multiplier(None)

        expand_rom()

        pipe_print('\nNow beginning randomization.\n'
                   'The randomization is very thorough, so it may take some time.\n'
                   'Please be patient and wait for "randomization successful" to appear.')

        if Options_.is_flag_active('thescenarionottaken'):
            if Options_.is_flag_active('strangejourney'):
                pipe_print('thescenarionottaken flag is incompatible with strangejourney')
            else:
                diverge()

        read_dialogue(outfile_rom_buffer)  # Uses outfile instead of infile for TheScenarioNotTaken compatibility
        read_location_names(outfile_rom_buffer)  # Uses outfile instead of infile for TheScenarioNotTaken compatibility
        relocate_ending_cinematic_data(0xF08A70)

        if Options_.is_flag_active('shuffle_commands') or \
                Options_.is_flag_active('replace_commands') or \
                Options_.is_flag_active('random_treasure'):
            auto_recruit_gau(stays_in_wor=not Options_.is_flag_active('shuffle_wor') and not
                             Options_.is_flag_active('mimetime'))
            if Options_.is_flag_active('shuffle_commands') or Options_.is_flag_active('replace_commands'):
                auto_learn_rage()

        can_always_access_esper_menu(outfile_rom_buffer)
        if Options_.is_flag_active('shuffle_commands') and not Options_.is_flag_active('suplexwrecks'):
            manage_commands(commands)

        reseed()

        if Options_.is_flag_active('random_dances'):
            if 0x13 not in changed_commands:
                manage_dances(kwargs.get('web_custom_dance_names', None))

        spells = get_ranked_spells(infile_rom_buffer)
        if Options_.is_flag_active('madworld'):
            random.shuffle(spells)
            for index, spell in enumerate(spells):
                spell._rank = index + 1
                spell.valid = True
        if Options_.is_flag_active('replace_commands') and not Options_.is_flag_active('suplexwrecks'):
            if Options_.is_flag_active('quikdraw'):
                ALWAYS_REPLACE += ['rage']
            if Options_.is_flag_active('sketch'):
                NEVER_REPLACE += ['sketch']
            _, freespaces = manage_commands_new(commands)

        if Options_.is_flag_active('lessfanatical'):  # remove the magic only tile when entering fanatic's tower
            fanatics_fix_sub = Substitution()
            fanatics_fix_sub.bytestring = bytes([0x80])
            fanatics_fix_sub.set_location(0x025352)
            fanatics_fix_sub.write(outfile_rom_buffer)

        reseed()

        if Options_.is_flag_active('sprint'):
            manage_sprint()

        if Options_.is_flag_active('fix_exploits'):
            manage_balance(newslots=Options_.is_flag_active('replace_commands'))

        if Options_.is_flag_active('random_final_party'):
            randomize_final_party_order()
        reseed()

        preserve_graphics = (not Options_.is_flag_active('swap_sprites') and not Options_.is_flag_active('partyparty'))

        monsters = get_monsters(infile_rom_buffer)
        formations = get_formations(infile_rom_buffer)
        fsets = get_fsets(infile_rom_buffer)
        get_locations(outfile_rom_buffer)  # Must read from outfile for thescenarionottaken to function
        get_ranked_items(infile_rom_buffer)
        get_zones(infile_rom_buffer)
        get_metamorphs(infile_rom_buffer)

        aispaces = [
            FreeBlock(0xFCF50, 0xFCF50 + 384),
            FreeBlock(0xFFF47, 0xFFF47 + 87),
            FreeBlock(0xFFFBE, 0xFFFBE + 66)
        ]

        if Options_.is_flag_active('random_final_dungeon') or Options_.is_flag_active('ancientcave'):
            # do this before treasure
            if Options_.is_flag_active('random_enemy_stats') \
                    and Options_.is_flag_active('random_treasure') \
                    and Options_.is_flag_active('random_character_stats'):
                dirk = get_item(0)
                if dirk is None:
                    get_ranked_items(infile_rom_buffer)
                    dirk = get_item(0)
                secret_item = dirk.become_another(halloween=Options_.is_flag_active('halloween'))
                dirk.write_stats(outfile_rom_buffer)
                dummy_item(dirk)
                assert not dummy_item(dirk)
                log(secret_item, section='secret items')
        if Options_.is_flag_active('random_enemy_stats') and \
                Options_.is_flag_active('random_treasure') and \
                Options_.is_flag_active('random_character_stats'):
            rename_card = get_item(231)
            if rename_card is not None:

                secret_item = rename_card.become_another(tier='low')
                rename_card.write_stats(outfile_rom_buffer)

                # Make sure the secret item uses the proper weapon animation

                weapon_anim_fix = Substitution()
                weapon_anim_fix.set_location(0x19DB8)
                weapon_anim_fix.bytestring = bytes([0x22, 0xB0, 0x3F, 0xF0])
                weapon_anim_fix.write(outfile_rom_buffer)

                weapon_anim_fix.set_location(0x303FB0)
                weapon_anim_fix.bytestring = bytes(
                    [0xE0, 0xE8, 0x02,          # CPX $02E8
                    0xB0, 0x05,                 # BCS $05
                    0xBF, 0x00, 0xE4, 0xEC,     # LDA $ECE400,X
                    0x6B,                       # RTL
                    0xDA,                       # PHX
                    0xC2, 0x20,                 # REP #$20
                    0x8A,                       # TXA
                    0xE9, 0xF0, 0x02,           # SBC $02F0
                    0xAA,                       # TAX
                    0x29, 0xFF, 0x00,           # AND #$00FF
                    0xE2, 0x20,                 # SEP #$20
                    0xBF, 0x00, 0x31, 0xF0,     # LDA $F03100,X
                    0xFA,                       # PLX
                    0x6B])                      # RTL
                weapon_anim_fix.write(outfile_rom_buffer)

                log(secret_item, section='secret items')
        reseed()

        items = get_ranked_items()
        if Options_.is_flag_active('random_items'):
            manage_items(items, changed_commands_mi=changed_commands)
            buy_owned_breakable_tools(outfile_rom_buffer)

        reseed()

        if Options_.is_flag_active('random_enemy_stats'):
            aispaces = manage_final_boss(aispaces)
            monsters = manage_monsters(
                web_custom_moves=kwargs.get('web_custom_monster_attack_names', None)
            )

        reseed()

        if Options_.is_flag_active('random_enemy_stats') or \
                Options_.is_flag_active('shuffle_commands') or \
                Options_.is_flag_active('replace_commands'):
            for monster in monsters:
                monster.screw_tutorial_bosses(old_vargas_fight=Options_.is_flag_active('rushforpower'))
                monster.write_stats(outfile_rom_buffer)

        if Options_.is_flag_active('mementomori'):
            amount = Options_.get_flag_value('mementomori')
            if type(amount) == bool:
                while True:
                    amount = input('\nHow many character should receive innate relics? '
                                   '(0-14 or random):\n')
                    try:
                        if amount.lower() == 'random' or 0 < int(amount) < 15:
                            break
                        raise ValueError
                    except ValueError:
                        pipe_print('The supplied value was not a valid option. Please try again.')
            feature_exclusion_list = ['Auto stop', 'Muddle', 'Command Changer']
            if Options_.is_flag_active('dearestmolulu'):
                feature_exclusion_list.append('no enc.')
            hidden_relic(outfile_rom_buffer, amount, feature_exclusion_list)

        # This needs to be before manage_monster_appearance or some of the monster
        # palettes will be messed up.
        esper_replacements = {}
        if Options_.is_flag_active('randomize_magicite'):
            esper_replacements = randomize_magicite(outfile_rom_buffer, infile_rom_buffer)
            JUNCTION_MANAGER_PARAMETERS['esper_replacements'] = esper_replacements
        reseed()

        if Options_.is_flag_active('random_palettes_and_names') and \
                Options_.is_flag_active('random_enemy_stats'):
            manage_monster_appearance(monsters, preserve_graphics=preserve_graphics)
        reseed()

        if Options_.is_flag_active('random_palettes_and_names') or \
                Options_.is_flag_active('swap_sprites') or \
                Options_.is_any_flag_active(
                    ['partyparty', 'bravenudeworld', 'suplexwrecks', 'novanilla',
                     'christmas', 'halloween', 'kupokupo', 'quikdraw', 'makeover', 'cloneparty', 'frenchvanilla']):
            sprite_log = manage_character_appearance(
                outfile_rom_buffer,
                preserve_graphics=preserve_graphics,
                web_custom_moogle_names=kwargs.get('web_custom_moogle_names', None),
                web_custom_male_names=kwargs.get('web_custom_male_names', None),
                web_custom_female_names=kwargs.get('web_custom_female_names', None),
                web_custom_sprite_replacements=kwargs.get('web_custom_sprite_replacements', None)
            )
            log(sprite_log, 'aesthetics')
            # show_original_names(outfile_rom_buffer)
        reseed()

        if Options_.is_flag_active('random_character_stats'):
            # do this after items
            manage_equipment(items)
        reseed()

        esperrage_spaces = [FreeBlock(0x26469, 0x26469 + 919)]

        # Even if we don't enable dancingmaduin, we must construct an
        # esper allocation table for other modules that rely on it
        # (i.e. junction effects)
        initialize_esper_allocation_table()
        if Options_.is_flag_active('random_espers'):
            dancingmaduin = Options_.is_flag_active('dancingmaduin')
            if dancingmaduin:
                esper_allocations_address = allocate_espers(
                    Options_.is_flag_active('ancientcave'),
                    get_espers(infile_rom_buffer),
                    get_characters(),
                    dancingmaduin.value,
                    outfile_rom_buffer,
                    esper_replacements
                )
                nerf_paladin_shield()
                verify = JUNCTION_MANAGER_PARAMETERS['esper-allocations-address']
                assert esper_allocations_address == verify
            manage_espers(esperrage_spaces, esper_replacements)
        reseed()
        myself_locations = myself_patches(outfile_rom_buffer)
        myself_name_bank = [(myself_locations['NAME_TABLE'] >> 16) + 0xC0]
        myself_name_address = [myself_locations['NAME_TABLE'] & 0x0000FF,
                               (myself_locations['NAME_TABLE'] >> 8) & 0x00FF]
        manage_reorder_rages(myself_locations['RAGE_ORDER_TABLE'])

        titlesub = Substitution()
        titlesub.bytestring = [0xFD] * 4
        titlesub.set_location(0xA5E8E)
        titlesub.write(outfile_rom_buffer)

        manage_opening()
        manage_ending()
        manage_auction_house()

        savetutorial_sub = Substitution()
        savetutorial_sub.set_location(0xC9AF1)
        savetutorial_sub.bytestring = [0xD2, 0x33, 0xEA, 0xEA, 0xEA, 0xEA]
        savetutorial_sub.write(outfile_rom_buffer)

        savecheck_sub = Substitution()
        savecheck_sub.bytestring = [0xEA, 0xEA]
        savecheck_sub.set_location(0x319f2)
        savecheck_sub.write(outfile_rom_buffer)
        reseed()

        if (Options_.is_flag_active('shuffle_commands') or Options_.is_flag_active(
                'supernatural')) and not Options_.is_flag_active('suplexwrecks'):
            # do this after swapping beserk
            manage_natural_magic(myself_locations['NATURAL_MAGIC_TABLE'])
        reseed()

        if Options_.is_flag_active('random_zerker'):
            umaro_risk = manage_umaro(commands)
            reset_rage_blizzard(items, umaro_risk, outfile_rom_buffer)
        reseed()

        if Options_.is_flag_active('shuffle_commands') and not Options_.is_flag_active('suplexwrecks'):
            # do this after swapping berserk
            manage_tempchar_commands()
        reseed()

        start_in_wor = Options_.is_flag_active('worringtriad')
        if Options_.is_flag_active('random_character_stats'):
            # do this after swapping berserk
            from itemrandomizer import set_item_changed_commands
            set_item_changed_commands(changed_commands)
            loglist = reset_special_relics(items, characters, outfile_rom_buffer)
            log_string = 'COMMAND CHANGERS\n---------------------------\n'
            loglist.sort(key=lambda log_item: log_item[0])
            for name, before, after in loglist:
                before_name = [command for command in commands.values() if command.id == before][0].name
                after_name = [command for command in commands.values() if command.id == after][0].name
                log_string += '{0:15}{1:7} -> {2:7}\n'.format(name + ':', before_name.lower(), after_name.lower())

            log(log_string, section='item effects')
            reset_cursed_shield(outfile_rom_buffer)

            if options.Use_new_randomizer:
                stat_randomizer = CharacterStats(rng, Options_, character_list)
                stat_randomizer.randomize()
                for mutated_character in character_list:
                    substitutions = mutated_character.get_bytes()
                    for substitution_address in substitutions:
                        outfile_rom_buffer.seek(substitution_address)
                        outfile_rom_buffer.write(substitutions[substitution_address])
            else:
                for character in characters:
                    character.mutate_stats(outfile_rom_buffer, start_in_wor)
        else:
            for character in characters:
                character.mutate_stats(outfile_rom_buffer, start_in_wor, read_only=True)
        reseed()

        if Options_.is_flag_active('random_formations') or Options_.is_flag_active('ancientcave'):
            manage_dragons()
        reseed()

        if Options_.is_flag_active('randomize_forest') and not \
                Options_.is_flag_active('ancientcave') and not \
                Options_.is_flag_active('strangejourney'):
            randomize_forest()

            # remove forced healing event tile with randomized forest
            remove_forest_event_sub = Substitution()
            remove_forest_event_sub.set_location(0xBA3D1)
            remove_forest_event_sub.bytestring = bytes([0xFE])
            remove_forest_event_sub.write(outfile_rom_buffer)

        reseed()

        if Options_.is_flag_active('random_final_dungeon') and not Options_.is_flag_active('ancientcave'):
            # do this before treasure
            manage_tower()
        reseed()
        if Options_.is_flag_active('norng'):
            fix_norng_npcs()

        if Options_.is_flag_active('random_formations') or Options_.is_flag_active('random_treasure'):
            assign_unused_enemy_formations()

        form_music = {}
        if Options_.is_flag_active('random_formations'):
            no_special_events = not Options_.is_flag_active('bsiab')
            manage_formations_hidden(formations, free_spaces=aispaces, form_music_overrides=form_music,
                                     no_special_events=no_special_events)
            for monster in get_monsters():
                monster.write_stats(outfile_rom_buffer)
        reseed()

        for formation in get_formations():
            formation.write_data(outfile_rom_buffer)

        if Options_.is_flag_active('random_treasure'):
            wedge_money = 1000 + random.randint(0, 1500)
            vicks_money = 500 + random.randint(0, 750)
            starting_money = wedge_money + vicks_money
            starting_money_sub = Substitution()
            starting_money_sub.set_location(0xC9A93)
            starting_money_sub.bytestring = bytes([0x84, starting_money & 0xFF, (starting_money >> 8) & 0xFF])
            starting_money_sub.write(outfile_rom_buffer)

            # do this after hidden formations
            katn = Options_.mode.name == 'katn'
            guarantee_hidon_drop = Options_.is_flag_active('random_enemy_stats')
            manage_treasure(monsters, shops=True, no_charm_drops=katn, katn_flag=katn,
                            guarantee_hidon_drop=guarantee_hidon_drop)
            if not Options_.is_flag_active('ancientcave'):
                manage_chests()
                mutate_event_items(outfile_rom_buffer, cutscene_skip=Options_.is_flag_active('notawaiter'),
                                   crazy_prices=Options_.is_flag_active('madworld'),
                                   no_monsters=Options_.is_flag_active('nomiabs'),
                                   uncapped_monsters=Options_.is_flag_active('bsiab'))
                for fset in fsets:
                    # write new formation sets for MiaBs
                    fset.write_data(outfile_rom_buffer)
        reseed()

        if Options_.is_flag_active('random_palettes_and_names'):
            # do this before ancient cave
            # could probably do it after if I wasn't lazy
            manage_colorize_dungeons()

        if Options_.is_flag_active('ancientcave'):
            manage_ancient(Options_, outfile_rom_buffer, infile_rom_buffer, form_music_overrides=form_music,
                           randlog=randomizer_log)
        reseed()

        if Options_.is_flag_active('shuffle_commands') or \
                Options_.is_flag_active('replace_commands') or \
                Options_.is_flag_active('random_enemy_stats'):
            manage_magitek()
        reseed()

        if Options_.is_flag_active('random_blitz'):
            if 0x0A not in changed_commands:
                manage_blitz()
        reseed()

        if Options_.is_flag_active('halloween'):
            demon_chocobo_sub = Substitution()
            outfile_rom_buffer.seek(0x2d0000 + 896 * 7)
            demon_chocobo_sub.bytestring = outfile_rom_buffer.read(896)
            for index in range(7):
                demon_chocobo_sub.set_location(0x2d0000 + 896 * index)
                demon_chocobo_sub.write(outfile_rom_buffer)

        if Options_.is_flag_active('random_window') or \
                Options_.is_flag_active('christmas') or \
                Options_.is_flag_active('halloween'):
            for index in range(8):
                window = WindowBlock(index)
                window.read_data()
                window.mutate()
                window.write_data()
        reseed()

        if Options_.is_flag_active('dearestmolulu') or (
                Options_.is_flag_active('random_formations') and
                Options_.is_flag_active('fix_exploits') and not
                Options_.is_flag_active('ancientcave')):
            manage_encounter_rate()
        reseed()
        reseed()

        if Options_.is_flag_active('random_animation_palettes'):
            manage_colorize_animations()
        reseed()

        if Options_.is_flag_active('suplexwrecks'):
            manage_suplex(commands, monsters)
        reseed()

        if Options_.is_flag_active('strangejourney') and not Options_.is_flag_active('ancientcave'):
            create_dimensional_vortex()
            # manage_strange_events()
        reseed()

        if Options_.is_flag_active('notawaiter') and not Options_.is_flag_active('ancientcave'):
            pipe_print('Cutscenes are currently skipped up to Kefka @ Narshe')
            manage_skips()
        reseed()

        if Options_.is_flag_active('shadowstays'):
            shadow_stays(outfile_rom_buffer)

        wor_free_char = 0xB  # gau
        alternate_gogo = Options_.is_flag_active('mimetime')
        if (Options_.is_flag_active('shuffle_wor') or alternate_gogo) and not Options_.is_flag_active('ancientcave'):
            include_gau = Options_.is_flag_active('shuffle_commands') or \
                          Options_.is_flag_active('replace_commands') or \
                          Options_.is_flag_active('random_treasure')
            wor_free_char = manage_wor_recruitment(outfile_rom_buffer,
                                                   shuffle_wor=Options_.is_flag_active('shuffle_wor'),
                                                   random_treasure=Options_.is_flag_active('random_treasure'),
                                                   include_gau=include_gau,
                                                   alternate_gogo=alternate_gogo)
        reseed()

        if Options_.is_flag_active('worringtriad') and not Options_.is_flag_active('ancientcave'):
            manage_wor_skip(outfile_rom_buffer, wor_free_char, airship=Options_.is_flag_active('airship'),
                            dragon=Options_.mode.name == 'dragonhunt',
                            alternate_gogo=Options_.is_flag_active('mimetime'),
                            esper_replacements=esper_replacements)
        reseed()

        if Options_.is_flag_active('random_clock') and not Options_.is_flag_active('ancientcave'):
            manage_clock()
        reseed()

        reseed()

        if Options_.is_flag_active('remonsterate'):
            outfile_backup = BytesIO(outfile_rom_buffer.getbuffer().tobytes())

            attempt_number = 0
            remonsterate_results = None
            randomize_connection, remonsterate_connection = Pipe()

            while True:
                try:
                    remonsterate_kwargs = {
                        'outfile_rom_buffer': outfile_rom_buffer,
                        'seed': (seed + attempt_number),
                        'rom_type': '1.0',
                        'list_of_monsters': get_monsters(outfile_rom_buffer)
                    }
                    remonsterate_process = Process(
                        target=remonsterate,
                        args=(remonsterate_connection, pipe_print),
                        kwargs=remonsterate_kwargs
                    )
                    remonsterate_process.start()
                    while True:
                        try:
                            if not remonsterate_process.is_alive():
                                raise RuntimeError('Unexpected error: The process handling remonsteration died.')
                            if randomize_connection.poll(timeout=5):
                                child_output = randomize_connection.recv()
                            else:
                                child_output = None
                            if child_output:
                                if isinstance(child_output, str):
                                    pipe_print(child_output)
                                elif isinstance(child_output, tuple):
                                    outfile_rom_buffer, remonsterate_results = child_output
                                    break
                                elif isinstance(child_output, Exception):
                                    raise child_output
                        except EOFError:
                            break
                except Exception as remonsterate_exception:
                    if isinstance(remonsterate_exception, OverflowError) or \
                            isinstance(remonsterate_exception, ReferenceError):
                        pipe_print('Remonsterate: An error occurred attempting to remonsterate. Trying again...')
                        # Replace backup file
                        outfile_rom_buffer = outfile_backup
                        attempt_number = attempt_number + 1
                        continue
                    else:
                        raise remonsterate_exception
                break

            # Remonsterate finished
            if remonsterate_results:
                for result in remonsterate_results:
                    log(str(result) + '\n', section='remonsterate')

        if not Options_.is_flag_active('sketch') or Options_.is_flag_active('remonsterate'):
            # Original C2 sketch fix by Assassin, prevents bad pointers

            sketch_fix_sub = Substitution()
            sketch_fix_sub.set_location(0x2F5C6)
            sketch_fix_sub.bytestring = bytes([0x80, 0xCA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0x4C, 0x09, 0xF8,
                                               0xA0, 0x00, 0x28, 0x22, 0x09, 0xB1, 0xC1, 0xA9, 0x01, 0x1C, 0x8D, 0x89,
                                               0xA0,
                                               0x03, 0x00,
                                               0xB1, 0x76, 0x0A, 0xAA, 0xC2, 0x20, 0xBD, 0x01, 0x20, 0x90, 0x02,
                                               0x7B, 0x3A, 0xAA, 0x7B, 0xE2, 0x20, 0x22, 0xD1, 0x24, 0xC1, 0x80,
                                               0xD7, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            sketch_fix_sub.set_location(0x12456)
            sketch_fix_sub.bytestring = bytes([0x20, 0x8F, 0x24, 0xA2, 0x00, 0x18, 0xA0, 0x00, 0x00,
                                               0x86, 0x10, 0xA2, 0x3F, 0xAE, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            # Additional C1 sketch animation fix by Assassin, handles bad draw instruction

            sketch_fix_sub.set_location(0x12456)
            sketch_fix_sub.bytestring = bytes([0x20, 0x8F, 0x24, 0xA2, 0x00, 0x18, 0xA0, 0x00, 0x00,
                                               0x86, 0x10, 0xA2, 0x3F, 0xAE, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            sketch_fix_sub.set_location(0x1246C)
            sketch_fix_sub.bytestring = bytes([0x20, 0x8F, 0x24, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            sketch_fix_sub.set_location(0x12484)
            sketch_fix_sub.bytestring = bytes(
                [0x20, 0x8F, 0x24, 0xA2, 0x00, 0x14, 0xA0, 0x00, 0x24, 0x80, 0xD0, 0xDA, 0x86, 0x10,
                 0x20, 0x20, 0x20, 0x20, 0xF5, 0x24, 0x20, 0xE5, 0x24, 0x20, 0xA5, 0x22, 0xFA, 0x60,
                 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            sketch_fix_sub.set_location(0x124A9)
            sketch_fix_sub.bytestring = bytes([0x20, 0x8F, 0x24, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            sketch_fix_sub.set_location(0x124D1)
            sketch_fix_sub.bytestring = bytes([0x20, 0x8F, 0x24, 0xE0, 0xFF, 0xFF, 0xD0, 0x03,
                                               0x20, 0x20, 0x20, 0xA2, 0x00, 0x20, 0x20, 0x5C, 0x24, 0x6B, 0xEA,
                                               0x6B, ])
            sketch_fix_sub.write(outfile_rom_buffer)

            sketch_fix_sub.set_location(0x124F9)
            sketch_fix_sub.bytestring = bytes(
                [0x1A, 0xF0, 0x01, 0x3A, 0x0A, 0x0A, 0x18, 0x65, 0x10, 0xAA, 0xBF, 0x02, 0x70, 0xD2, 0xEB, 0x29, 0xFF,
                 0x03,
                 0x0A, 0x0A, 0x0A, 0x0A, 0x8D, 0x69, 0x61, 0xBF, 0x00, 0x70, 0xD2, 0x29, 0xFF, 0x7F, 0x8D, 0xA8, 0x81,
                 0x7B, 0xBF, 0x01, 0x70, 0xD2, 0xE2, 0x20, 0x0A, 0xEB, 0x6A, 0x8D, 0xAC, 0x81,
                 0x0A, 0x0A, 0x0A, 0x7B, 0x2A, 0x8D, 0xAB, 0x81, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, ])
            sketch_fix_sub.write(outfile_rom_buffer)

        # Code must be below assign_unused_enemy_formations and above randomize_music
        if Options_.is_flag_active('random_formations'):
            # formations = get_formations()
            # fsets = get_fsets()
            formations, fsets = manage_formations(formations, fsets)
            if Options_.is_flag_active('cursedencounters'):
                manage_cursed_encounters(formations, fsets)
            for fset in fsets:
                fset.write_data(outfile_rom_buffer)

        has_music = Options_.is_any_flag_active(['johnnydmad', 'johnnyachaotic'])
        if has_music:
            music_init()

        if Options_.is_flag_active('alasdraco'):
            opera = manage_opera(outfile_rom_buffer, has_music)
            log(get_opera_log(), section='aesthetics')
        else:
            opera = None
        reseed()

        if has_music:
            from utils import custom_path
            randomize_music(outfile_rom_buffer, Options_, playlist_path=custom_path,
                            playlist_filename='songs.txt',
                            virtual_playlist=kwargs.get('web_custom_playlist', None),
                            opera=opera, form_music_overrides=form_music)
            log(get_music_spoiler(), section='music')
        reseed()

        if Options_.mode.name == 'katn':
            start_with_random_espers()
            set_lete_river_encounters()
        reseed()

        if Options_.is_flag_active('random_enemy_stats') or Options_.is_flag_active('random_formations'):
            if not Options_.is_flag_active('ancientcave') or Options_.mode.name == 'katn':
                house_hint()
        reseed()
        reseed()

        randomize_poem(outfile_rom_buffer)
        randomize_passwords(custom_web_passwords=kwargs.get('web_custom_passwords', None))
        reseed()
        namingway()
        if Options_.is_flag_active('thescenarionottaken'):
            chocobo_merchant()

        jm = JunctionManager(outfile_rom_buffer, 'bcg_junction_manifest.json')
        jm.activated = False
        junction_everything(jm, commands=commands)

        # ----- NO MORE RANDOMNESS PAST THIS LINE -----
        if Options_.is_flag_active('thescenarionottaken'):
            no_kutan_skip(outfile_rom_buffer)

        write_all_locations_misc()
        for fset in fsets:
            fset.write_data(outfile_rom_buffer)

        # This needs to be after write_all_locations_misc()
        # so the changes to Daryl don't get stomped.
        event_freespaces = [FreeBlock(0xCFE2A, 0xCFE2a + 470)]
        if Options_.is_flag_active('airship'):
            event_freespaces = activate_airship_mode(event_freespaces)

        if Options_.is_flag_active('random_zerker') or Options_.is_flag_active('random_character_stats'):
            manage_equip_umaro(event_freespaces)

        # Write easymodo, expboost, and gpboost stat changes to each monster
        if Options_.is_flag_active('easymodo') or Options_.is_flag_active('expboost') or \
                Options_.is_flag_active('gpboost'):
            for monster in monsters:
                if Options_.is_flag_active('easymodo'):
                    monster.stats['hp'] = 1
                if Options_.is_flag_active('expboost'):
                    monster.stats['xp'] = int(
                        min(0xFFFF, float(Options_.get_flag_value('expboost')) * monster.stats['xp']))
                if Options_.is_flag_active('gpboost'):
                    monster.stats['gp'] = int(
                        min(0xFFFF, float(Options_.get_flag_value('gpboost')) * monster.stats['gp']))
                monster.write_stats(outfile_rom_buffer)

        if Options_.is_flag_active('naturalmagic') or Options_.is_flag_active('naturalstats'):
            espers = get_espers(infile_rom_buffer)
            if Options_.is_flag_active('naturalstats'):
                for esper in espers:
                    esper.bonus = 0xFF
            if Options_.is_flag_active('naturalmagic'):
                for esper in espers:
                    esper.spells, esper.learnrates = [], []
                for item in items:
                    item.features['learnrate'] = 0
                    item.features['learnspell'] = 0
                    item.write_stats(outfile_rom_buffer)
            for esper in espers:
                esper.write_data(outfile_rom_buffer)

        if Options_.is_flag_active('canttouchthis'):
            for character in characters:
                if character.id >= 14:
                    continue
                character.become_invincible(outfile_rom_buffer)

        if Options_.is_flag_active('equipanything'):
            manage_equip_anything()

        if Options_.is_flag_active('playsitself'):
            manage_full_umaro()
            for command in commands.values():
                if command.id not in [0x01, 0x08, 0x0E, 0x0F, 0x15, 0x19]:
                    command.allow_while_berserk(outfile_rom_buffer)
            whelkhead = get_monster(0x134)
            whelkhead.stats['hp'] = 1
            whelkhead.write_stats(outfile_rom_buffer)
            whelkshell = get_monster(0x100)
            whelkshell.stats['hp'] = 1
            whelkshell.write_stats(outfile_rom_buffer)

        for item in get_ranked_items(allow_banned=True):
            if item.banned:
                assert not dummy_item(item)

        if Options_.is_flag_active('christmas') and not Options_.is_flag_active('ancientcave'):
            manage_santa()
        elif Options_.is_flag_active('halloween') and not Options_.is_flag_active('ancientcave'):
            manage_spookiness()

        if Options_.is_flag_active('dancelessons'):
            no_dance_stumbles(outfile_rom_buffer)

        title_gfx(outfile_rom_buffer)  # always on
        stacking_immunities(outfile_rom_buffer) # always on
        banon_life3(outfile_rom_buffer) #always on
        improved_party_gear(outfile_rom_buffer, myself_name_address, myself_name_bank)  # always on
        mastered_espers(outfile_rom_buffer, dancingmaduin=Options_.is_flag_active("dancingmaduin")) #always on

        if Options_.is_flag_active('tastetherainbow'):
            cycle_statuses(outfile_rom_buffer)  # QoL Flag

        if Options_.is_flag_active('magicnumbers'):
            mp_color_digits(outfile_rom_buffer)  # QoL Flag

        if Options_.is_flag_active('alphalores'):
            alphabetized_lores(outfile_rom_buffer)  # QoL Flag

        if Options_.is_flag_active('informativemiss'):
            informative_miss(outfile_rom_buffer)  # QoL Flag

        if Options_.is_flag_active('regionofdoom'):
            manage_doom_gaze()  # QoL Flag

        if Options_.is_flag_active('shuffle_commands'):
            name_swd_techs()
            fix_flash_and_bioblaster()

        if Options_.is_flag_active('effectmas'):
            description_disruption(outfile_rom_buffer)  # add to item junctions code

        if Options_.is_flag_active('mpparty'):
            mp_refills(outfile_rom_buffer) # QoL Flag

        if Options_.is_flag_active('relicmyhat'):
            improved_equipment_menus(outfile_rom_buffer)
        else:
            y_equip_relics(outfile_rom_buffer)

        if Options_.is_flag_active('swdtechspeed'):
            swdtech_speed = Options_.get_flag_value('swdtechspeed')
            if isinstance(swdtech_speed, bool):
                if application:
                    pipe_print('ERROR: No value was supplied for swdtechspeed flag. Skipping flag.')
                else:
                    while True:
                        swdtech_speed = input('\nPlease enter a custom speed for Sword Tech '
                                              '(random, vanilla, fast, faster, fastest):\n')
                        try:
                            if swdtech_speed.lower() in ['random', 'vanilla', 'fast', 'faster', 'fastest']:
                                break
                            raise ValueError
                        except ValueError:
                            pipe_print('The supplied speed was not a valid option. Please try again.')
            if not type(swdtech_speed) == bool:
                change_swdtech_speed(outfile_rom_buffer, swdtech_speed)
        if Options_.is_flag_active('cursepower'):
            change_cursed_shield_battles(myself_locations['DECURSE_GOAL'], outfile_rom_buffer, Options_.get_flag_value('cursepower'))

        coral_log = manage_coral(outfile_rom_buffer, kwargs.get('web_custom_coral_names', None))
        log(coral_log, 'aesthetics')

        # TODO Does not work currently - needs fixing to allow Lenophis' esper bonus patch to work correctly
        # add_esper_bonuses(outfile_rom_buffer)

        if Options_.is_flag_active('removeflashing'):
            fewer_flashes(outfile_rom_buffer, Options_.get_flag_value('removeflashing'))

        if Options_.is_flag_active('nicerpoison'):
            nicer_poison(outfile_rom_buffer)

        if Options_.is_flag_active('levelcap'):

            maxlevel = Options_.get_flag_value('levelcap')
            leveltable = myself_locations['LEVEL_CAP']
            max_level_string = bytes()

            if str(maxlevel).lower() == "random":
                maxlevel = rng.randint(1, 99)
                for character in characters:
                    if character.id >= 14:
                        continue
                    character.level_cap = maxlevel
                    max_level_string += bytes([int(maxlevel)])
            elif str(maxlevel).lower() == "chaos":
                for character in characters:
                    if character.id >= 14:
                        continue
                    maxlevel = rng.randint(1, 99)
                    character.level_cap = maxlevel
                    max_level_string += bytes([int(maxlevel)])
            else:  # use whatever numeric value was given
                for character in characters:
                    if character.id >= 14:
                        continue
                    character.level_cap = maxlevel
                    max_level_string += bytes([int(maxlevel)])

            level_cap(outfile_rom_buffer, max_level_string, leveltable)

        if Options_.is_flag_active('slowerbg'):
            slow_background_scrolling(outfile_rom_buffer)

        if not Options_.is_flag_active('fightclub'):
            show_coliseum_rewards(outfile_rom_buffer)

        if Options_.is_flag_active('replace_commands') or Options_.is_flag_active('shuffle_commands'):
            sabin_hint(commands)

        if Options_.is_flag_active('sprint'):
            sprint_shoes_hint()

        if Options_.mode.name == 'katn':
            the_end_comes_beyond_katn()
        elif Options_.mode.name == 'dragonhunt':
            the_end_comes_beyond_crusader()

        manage_dialogue_patches(outfile_rom_buffer)
        write_location_names(outfile_rom_buffer)

        if jm.activated:
            outfile_rom_buffer.seek(0, 2)
            rom_size = outfile_rom_buffer.tell()
            if rom_size < 0x700000:
                expand_sub = Substitution()
                expand_sub.set_location(0x6fffff)
                expand_sub.bytestring = b'\x00'
                expand_sub.write(outfile_rom_buffer)

            if Options_.is_flag_active('playsitself'):
                jm.patch_blacklist.add('patch_junction_focus_umaro.txt')
            jm.execute()
            jm.verify()
            log(jm.report, section='junctions')

        rewrite_title(text='FF6 BCCE %s' % seed)
        validate_rom_expansion()
        rewrite_checksum()
        verify_randomtools_patches(outfile_rom_buffer)
        Substitution.verify_all_writes(outfile_rom_buffer)

        if not application == 'web' and kwargs.get('generate_output_rom', True):
            with open(outfile_rom_path, 'wb+') as rom_file:
                rom_file.write(outfile_rom_buffer.getvalue())
            outfile_rom_buffer.close()

        if kwargs.get('generate_output_rom', True):
            pipe_print('\nWriting log...')

            for log_character in sorted(characters, key=lambda character_r: character_r.id):
                log_character.associate_command_objects(list(commands.values()))
                if log_character.id > 13:
                    continue
                log(str(log_character), section='characters')

            if options.Use_new_randomizer:
                for log_character in sorted(character_list, key=lambda character_r: character_r.id):
                    if log_character.id <= 14:
                        log(str(log_character), section='stats')

            for monster in sorted(get_monsters(), key=lambda log_monster: log_monster.display_name):
                if monster.display_name:
                    log(monster.get_description(changed_commands=changed_commands),
                        section='monsters')

            if not Options_.is_flag_active('ancientcave'):
                log_chests()
            log_item_mutations()

            if not application == 'web':
                try:
                    with open(outlog, 'w+') as log_file:
                        log_file.write(get_log_string(
                            ['characters', 'stats', 'aesthetics', 'commands', 'blitz inputs', 'magitek',
                             'slots', 'dances', 'espers', 'item magic', 'item effects',
                             'command-change relics', 'colosseum', 'monsters', 'music', 'remonsterate',
                             'shops', 'treasure chests', 'junctions', 'zozo clock', 'secret items']))
                except UnicodeEncodeError:
                    # Computer's locale does not support all unicode characters being written. Try again with UTF-8.
                    try:
                        with open(outlog, 'w', encoding='UTF-8') as log_file:
                            log_file.write(get_log_string(
                                ['characters', 'stats', 'aesthetics', 'commands', 'blitz inputs', 'magitek',
                                 'slots', 'dances', 'espers', 'item magic', 'item effects',
                                 'command-change relics', 'colosseum', 'monsters', 'music', 'remonsterate',
                                 'shops', 'treasure chests', 'junctions', 'zozo clock', 'secret items']))
                    except Exception as ex:
                        pipe_print("ERROR: The randomizer encountered an error generating the spoiler log. No "
                                   "spoiler log was generated. Error text: " + str(ex))

        if Options_.is_flag_active('bingoboingo'):
            target_score = 200.0
            bingo_flags = kwargs.get('bingo_type')
            size = kwargs.get('bingo_size')
            difficulty = kwargs.get('bingo_difficulty')
            num_cards = kwargs.get('bingo_cards')

            pipe_print('Generating Bingo cards, please wait.')
            target_score = float(target_score) * (size ** 2)

            manage_bingo(bingo_flags=bingo_flags, size=size, difficulty=difficulty, num_cards=num_cards,
                         target_score=target_score)
            pipe_print('Bingo cards generated.')

        if application == 'tester':
            pipe_print('Randomization successful.')
            pipe_print(True)
        elif application in ['console', 'gui']:
            pipe_print('Randomization successful. Output filename: %s\n' % outfile_rom_path)
            pipe_print(True)
        elif application == 'web':
            pipe_print('Randomization successful.')
            pipe_print({
                # ord = output rom data
                # os = output seed
                # osl = output spoiler log
                'ord': outfile_rom_buffer,
                'os': seed,
                'osl': get_log_string(
                    ['characters', 'stats', 'aesthetics', 'commands', 'blitz inputs', 'magitek', 'slots', 'dances',
                     'espers',
                     'item magic', 'item effects', 'command-change relics', 'colosseum', 'monsters', 'music',
                     'remonsterate', 'shops', 'treasure chests', 'junctions', 'zozo clock', 'secret items'])
            })
        return outfile_rom_path
    except Exception as exc_r:
        # pipe_print(type(exc)(traceback.print_exc()))
        pipe_print(exc_r)
        raise exc_r


if __name__ == '__main__':
    pass
