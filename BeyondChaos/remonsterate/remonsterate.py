import os
import traceback
from .tools.tablereader import (
    set_global_label, set_global_table_filename, determine_global_table,
    set_table_specs, set_global_output_file_buffer, sort_good_order,
    get_open_file, TableObject, addresses, write_patches)
from .tools.utils import cached_property, get_transparency, utilrandom as random
from .tools.interface import get_outfile, set_seed, get_seed
from hashlib import md5
from PIL import Image, ImageOps
from math import ceil
from time import time
from multiprocessing import Pipe
from io import BytesIO

VERSION = '5.3'
randomize_connection = None
ALL_OBJECTS = None
file_paths = os.path.join(os.getcwd(), "remonsterate")
sprite_paths = os.path.join(os.getcwd(), "remonsterate", "sprites")
monster_list = None
outfile_rom_buffer = None
seed = None


def sig_func(c):
    s = '%s%s' % (c.filename, get_seed())
    return md5(s.encode()).hexdigest(), c.filename


def reseed(s):
    s = '%s%s' % (get_seed(), s)
    value = int(md5(s.encode('ascii')).hexdigest(), 0x10)
    random.seed(value)


class MouldObject(TableObject):
    # Moulds are templates for what enemy sizes are allowed
    # in an enemy formation. Enemies are generally 4, 8, 12, or 16
    # tiles in a given length/width. Note also that only 256 tiles
    # is the maximum for any mould.

    def read_data(self, outfile_rom_buffer: BytesIO = None, pointer=None):
        super().read_data(outfile_rom_buffer, pointer)

    @property
    def successor(self):
        try:
            return MouldObject.get(self.index + 1)
        except KeyError:
            return None

    def read_dimensions(self):
        if self.successor is None:
            end_pointer = addresses.moulds_end | 0x20000
        else:
            end_pointer = self.successor.mould_pointer | 0x20000

        pointer = self.mould_pointer | 0x20000
        f = get_open_file(self.filename)
        dimensions = []
        while pointer < end_pointer:
            f.seek(pointer)
            data = f.read(4)
            dimensions.append((int(data[2]), int(data[3])))
            pointer += 4
        return dimensions


class FormationObject(TableObject):
    pass


class MonsterSpriteObject(TableObject):
    SUPER_PROTECTED_INDEXES = [0x106]
    PROTECTED_INDEXES = list(range(0x180, 0x1a0)) + [0x12a]
    DONE_IMAGES = []

    def __repr__(self):
        if hasattr(self, 'image') and hasattr(self.image, 'filename'):
            return '{0:0>3X} {1}'.format(self.index, self.image.filename)
        else:
            return '{0:0>3X} ---'.format(self.index)

    def get_index(self):
        return self.index

    @property
    def is_8color(self):
        return bool(self.misc_sprite_pointer & 0x8000)

    @property
    def sprite_pointer(self):
        base_address = addresses.monster_graphics
        return (self.misc_sprite_pointer & 0x7FFF) * 8 + base_address

    @property
    def palette_index(self):
        return ((self.misc_palette_index & 0x3) << 8) | self.low_palette_index

    @property
    def is_big(self):
        return bool(self.misc_palette_index & 0x80)

    @property
    def is_actually_big(self):
        return self.width_tiles > 8 or self.height_tiles > 8

    @property
    def palette(self):
        if hasattr(self, '_palette'):
            return self._palette
        mpo = MonsterPaletteObject.get(self.palette_index)
        self._palette = [v for vs in mpo.rgb_palette for v in vs]
        return self.palette

    @property
    def stencil(self):
        if hasattr(self, '_stencil'):
            return self._stencil
        monster_comp = MonsterComp16Object if self.is_big else MonsterComp8Object
        self._stencil = list(monster_comp.get(self.stencil_index).stencil)
        return self.stencil

    @property
    def num_tiles(self):
        return sum([bin(v).count('1') for v in self.stencil])

    @property
    def is_unseen(self):
        if self.index <= 0xff:
            return False
        if self.old_data['misc_sprite_pointer'] & 0x7fff == 0:
            return True
        brachiosaur = MonsterSpriteObject.get(0x26)
        k = 'misc_sprite_pointer'
        if (self.old_data[k] == brachiosaur.old_data[k]
                and 0x157 <= self.index <= 0x15f):
            return True
        return False

    @cached_property
    def pair_protected(self):
        for index in self.SUPER_PROTECTED_INDEXES:
            if index == self.index:
                continue
            other = MonsterSpriteObject.get(index)
            k1, k2 = 'stencil_index', 'misc_sprite_pointer'
            if (self.old_data[k1] == other.old_data[k1]
                    and self.old_data[k2] == other.old_data[k2]):
                return MonsterSpriteObject.get(index)
        return None

    @property
    def is_super_protected(self):
        return self.index in self.SUPER_PROTECTED_INDEXES

    @property
    def is_protected(self):
        if self.index in self.PROTECTED_INDEXES + self.SUPER_PROTECTED_INDEXES:
            return True
        if self.is_unseen:
            return True
        return False

    def deinterleave_tile(self, tile):
        rows = []
        old_bit_count = sum([bin(v).count('1') for v in tile])
        for i in range(8):
            if self.is_8color:
                interleaved = (tile[i * 2], tile[(i * 2) + 1],
                               tile[i + 16])
            else:
                interleaved = (tile[i * 2], tile[(i * 2) + 1],
                               tile[(i * 2) + 16], tile[(i * 2) + 17])
            row = []
            for j in range(7, -1, -1):
                pixel = 0
                mask = 1 << j
                for k, v in enumerate(interleaved):
                    pixel |= bool(v & mask) << k

                if self.is_8color:
                    assert 0 <= pixel <= 7
                else:
                    assert 0 <= pixel <= 0xf
                row.append(pixel)

            assert len(row) == 8
            rows.append(row)

        assert len(rows) == 8
        # assert self.interleave_tile(rows) == tile
        new_bit_count = sum([bin(v).count('1') for vs in rows for v in vs])
        assert old_bit_count == new_bit_count
        return rows

    def interleave_tile(self, old_tile):
        if self.is_8color:
            new_tile = [0] * 24
        else:
            new_tile = [0] * 32

        old_bit_count = sum([bin(v).count('1') for vs in old_tile for v in vs])
        assert len(old_tile) == 8
        for (j, old_row) in enumerate(old_tile):
            assert len(old_row) == 8
            for (i, pixel) in enumerate(old_row):
                i = 7 - i
                a = bool(pixel & 1)
                b = bool(pixel & 2)
                c = bool(pixel & 4)
                d = bool(pixel & 8)

                new_tile[(j * 2)] |= (a << i)
                new_tile[(j * 2) + 1] |= (b << i)
                if self.is_8color:
                    new_tile[j + 16] |= (c << i)
                else:
                    new_tile[(j * 2) + 16] |= (c << i)
                    new_tile[(j * 2) + 17] |= (d << i)

        new_bit_count = sum([bin(v).count('1') for v in new_tile])

        assert old_bit_count == new_bit_count
        assert self.deinterleave_tile(new_tile) == old_tile
        return bytes(new_tile)

    @property
    def tiles(self):
        if hasattr(self, '_tiles'):
            return self._tiles

        if self.is_8color:
            num_bytes = 24
        else:
            num_bytes = 32

        tiles = []
        for i in range(self.num_tiles):
            outfile_rom_buffer.seek(self.sprite_pointer + (num_bytes * i))
            tiles.append(self.deinterleave_tile(outfile_rom_buffer.read(num_bytes)))

        self._tiles = tiles
        return self.tiles

    @property
    def all_pixels(self):
        tiles = list(self.tiles)
        if self.is_big:
            width = 16
        else:
            width = 8

        blank_tile = [[0] * 8] * 8

        height = width
        rows = []
        for y in range(height):
            row = []
            for x in range(width):
                stencil_value = self.stencil[y]
                if self.is_big:
                    stencil_value = ((stencil_value >> 8) |
                                     ((stencil_value & 0xff) << 8))
                to_tile = stencil_value & (1 << (width - (x + 1)))
                if to_tile:
                    row.append(tiles.pop(0))
                else:
                    row.append(blank_tile)
            rows.append(row)

        all_pixels = []
        for row in rows:
            for i in range(8):
                for tile in row:
                    tile_row = tile[i]
                    all_pixels.extend(tile_row)

        return all_pixels

    @property
    def palette_indexes(self):
        return set(self.all_pixels)

    @property
    def image(self):
        if hasattr(self, '_image'):
            return self._image

        if self.is_big:
            width = 16 * 8
        else:
            width = 8 * 8
        height = width
        data = bytes(self.all_pixels)
        im = Image.frombytes(mode='P', size=(width, height), data=data)
        im.putpalette(self.palette)

        self._image = im
        return self.image

    @property
    def width_tiles(self):
        if self.is_big:
            def measure(s):
                return bin((s >> 8) | ((s & 0xff) << 8))[2:].rfind('1')

            width = max([measure(s) for s in self.stencil])
        else:
            width = max([bin(s)[2:].rfind('1') for s in self.stencil])
        return width + 1

    @property
    def height_tiles(self):
        height = 0
        for i, s in enumerate(self.stencil):
            if s:
                height = i
        return height + 1

    @cached_property
    def max_width_tiles(self):
        n = 4
        while True:
            if n >= self.width_tiles:
                return max(n, 4)
            n += 4

    @cached_property
    def max_height_tiles(self):
        n = 4
        while True:
            if n >= self.height_tiles:
                return max(n, 4)
            n += 4

    def get_size_compatibility(self, image):
        if not hasattr(self, '_image_scores'):
            self._image_scores = {}

        if image.filename in self._image_scores:
            return self._image_scores[image.filename]

        if isinstance(image, str):
            image = Image.open(image)

        width = ceil(image.width / 8)
        height = ceil(image.height / 8)
        # image.close()

        if width > self.max_width_tiles or height > self.max_height_tiles:
            return None

        a, b = max(width, self.width_tiles), min(width, self.width_tiles)
        width_score = b / a
        a, b = max(height, self.height_tiles), min(height, self.height_tiles)
        height_score = b / a

        score = width_score * height_score
        self._image_scores[image.filename] = score

        return self.get_size_compatibility(image)

    def select_image(self, images=None, list_of_monsters=None):
        monster_original_name = None
        if self.get_index() < len(list_of_monsters):
            monster_original_name = list_of_monsters[self.get_index()].name.strip("_")
        if self.is_protected:
            if monster_original_name:
                randomize_connection.send("Remonsterate: " + monster_original_name +
                                          " is protected and did not receive a randomized sprite.")
            self.load_image(self.image)
            return True

        if images is None:
            images = MonsterSpriteObject.import_images
            if len(images) == len(self.DONE_IMAGES):
                return False

        candidates = [i for i in images if
                      i.filename not in self.DONE_IMAGES and
                      self.get_size_compatibility(i) is not None
                      ]

        if self.is_actually_big and random.random() > 0.1:
            temp = [c for c in candidates if c.width > 64 or c.height > 64]
            candidates = temp or candidates

        if hasattr(self, 'whitelist') and self.whitelist:
            candidates = [c for c in candidates
                          if hasattr(c, 'tags') and c.tags >= self.whitelist]
            if not candidates:
                # There were no eligible sprites matching the whitelistd tags
                if monster_original_name:
                    randomize_connection.send("Remonsterate: " + monster_original_name +
                                           " was not sprite randomized: "
                                           "No eligible sprites matching the whitelist tags '" +
                                        str(self.whitelist) + "' were found.")
                self.load_image(self.image)
                return True

        if hasattr(self, 'blacklist') and self.blacklist:
            candidates = [c for c in candidates if not
            (hasattr(c, 'tags') and c.tags & self.blacklist)]
            if not candidates:
                if monster_original_name:
                    randomize_connection.send("Remonsterate: " + monster_original_name +
                                           " was not sprite randomized: "
                                           "No eligible sprites were left after processing blacklisted tags '" +
                                        str(self.blacklist) + "'.")
                self.load_image(self.image)
                return True

        if not candidates:
            self.load_image(self.image)
            if monster_original_name:
                randomize_connection.send("Remonsterate: " + monster_original_name +
                                       " was not sprite randomized: No suitable sprite was found.")
            return True

        def sort_func(c):
            return self.get_size_compatibility(c), sig_func(c)

        candidates = sorted(candidates, key=sort_func)
        max_index = len(candidates) - 1
        index = random.randint(
            random.randint(random.randint(0, max_index), max_index), max_index)

        chosen = candidates[index]

        self.DONE_IMAGES.append(chosen.filename)

        result = self.load_image(chosen)
        if not result:
            self.select_image(candidates)
        return True

    def remap_palette(self, data, rgb_palette):
        zipped = zip(rgb_palette[0::3],
                     rgb_palette[1::3],
                     rgb_palette[2::3])
        pal = enumerate(zipped)
        pal = sorted(pal, key=lambda x: (x[1], x[0]))
        old_vals = set(data)
        assert all([0 <= v <= 0xf for v in old_vals])
        new_palette = []
        for new, (old, components) in enumerate(pal):
            if new == 0:
                assert new == old
                assert components == (0, 0, 0)
            data = data.replace(bytes([old]), bytes([new | 0x80]))
            new_palette.append(components)
        for value in set(data):
            data = data.replace(bytes([value]), bytes([value & 0x7f]))
        new_palette = [v for vs in new_palette for v in vs]
        new_vals = set(data)
        assert len(old_vals) == len(new_vals)
        assert all([0 <= v <= 0xf for v in new_vals])
        assert set(rgb_palette) == set(new_palette)
        return data, new_palette

    def load_image(self, image, transparency=None,
                   preserve_palette_order=False):
        if self.is_super_protected:
            return
        if isinstance(image, str):
            image = Image.open(image)
        # if hasattr(image, 'filename') and image.fp is None:
        #    image = Image.open(image.filename)
        if image.mode != 'P':
            filename = image.filename
            image = image.convert(mode='P')
            image.filename = filename

        width, height = image.size
        assert width <= 128
        assert height <= 128
        is_big = width > 64 or height > 64
        if is_big:
            self.misc_palette_index |= 0x80
        else:
            self.misc_palette_index &= 0x7f
        assert self.is_big == is_big

        palette_indexes = set(image.tobytes())
        if max(palette_indexes) > 0xf:
            # This should no longer happen after prepare_image()
            randomize_connection.send('Remonsterate: %s had too many colors and was excluded from use.'
                                      % image.filename)
            return False

        is_8color = max(palette_indexes) <= 7
        if is_8color:
            self.misc_sprite_pointer |= 0x8000
        else:
            self.misc_sprite_pointer &= 0x7fff
        assert self.is_8color == is_8color

        self._image = image
        assert self.image == image

        transparency = get_transparency(self.image)

        palette = self.image.getpalette()
        if transparency != 0:
            data = self.image.tobytes()
            data = data.replace(b'\x00', b'\xff')
            data = data.replace(bytes([transparency]), b'\x00')
            data = data.replace(b'\xff', bytes([transparency]))
            self.image.frombytes(data)
            index = 3 * transparency
            temp = palette[index:index + 3]
            assert len(temp) == 3
            palette[index:index + 3] = palette[0:3]
            palette[0:3] = temp
        palette[0:3] = [0, 0, 0]
        num_colors = 8 if self.is_8color else 16
        self.image.putpalette(palette)
        self._palette = palette[:3 * num_colors]
        assert self.palette == palette[:3 * num_colors]

        done_flag = False
        while hasattr(self.image, 'filename'):
            if done_flag:
                break
            for j in range(7, -1, -1):
                if done_flag:
                    break
                for i in range(width):
                    pixel = self.image.getpixel((i, j))
                    if pixel:
                        done_flag = True
                        break
            else:
                if not done_flag:
                    height = self.image.height
                    if height <= 8:
                        raise Exception('Fully transparent image not allowed.')
                    image = self.image.crop(
                        (0, 8, self.image.width, self.image.height))
                    image.filename = self.image.filename
                    self._image = image
                    new_height = self.image.height
                    assert height == new_height + 8

        blank_tile = [[0] * 8] * 8
        new_tiles = []
        stencil = []
        if self.is_big:
            num_tiles_width = 16
        else:
            num_tiles_width = 8

        data = self.image.tobytes()
        remapped = self.remap_palette(data, self.palette)
        if not preserve_palette_order:
            data, self._palette = remapped

        for jj in range(num_tiles_width):
            stencil_value = 0
            for ii in range(num_tiles_width):
                tile = []
                for j in range(8):
                    row = []
                    y = (jj * 8) + j
                    for i in range(8):
                        x = (ii * 8) + i
                        if x >= self.image.width:
                            row.append(0)
                            continue
                        try:
                            row.append(int(data[(y * self.image.width) + x]))
                        except IndexError:
                            row.append(0)
                    tile.append(row)
                if tile == blank_tile:
                    pass
                else:
                    new_tiles.append(tile)
                    stencil_value |= (1 << (num_tiles_width - (ii + 1)))
            if self.is_big:
                stencil_value = ((stencil_value >> 8) |
                                 ((stencil_value & 0xff) << 8))
            stencil.append(stencil_value)

        self._tiles = new_tiles
        self._stencil = stencil

        return True

    def write_data(self, pointer=None, syncing=False):
        global outfile_rom_buffer

        self.image

        chosen_palette = MonsterPaletteObject.get_free()
        chosen_palette.set_from_rgb(self.palette, is_8color=self.is_8color)

        self.misc_palette_index &= 0xFC
        self.misc_palette_index |= (chosen_palette.index >> 8)
        self.low_palette_index = chosen_palette.index & 0xff
        assert self.palette_index == chosen_palette.index

        for mso in MonsterSpriteObject.every:
            if self.pair_protected:
                break
            if (hasattr(mso, 'written') and mso.written
                    and mso.stencil == self.stencil):
                self.stencil_index = mso.stencil_index
                break
        else:
            assert self.pair_protected is None
            if self.is_big:
                mco = MonsterComp16Object.create_new()
            else:
                mco = MonsterComp8Object.create_new()
            mco.stencil = self.stencil
            self.stencil_index = mco.new_index
        if not self.stencil_index <= 0xff:
            raise OverflowError()
        #assert self.stencil_index <= 0xff

        if not hasattr(MonsterSpriteObject, 'free_space'):
            MonsterSpriteObject.free_space = addresses.new_monster_graphics

        for mso in MonsterSpriteObject.every:
            if self.pair_protected:
                break
            if (hasattr(mso, 'written') and mso.written
                    and mso.stencil == self.stencil
                    and mso.tiles == self.tiles):
                self.misc_sprite_pointer = mso.misc_sprite_pointer
                break
        else:
            assert self.pair_protected is None
            DIVISION_FACTOR = 16
            remainder = MonsterSpriteObject.free_space % DIVISION_FACTOR
            if remainder:
                MonsterSpriteObject.free_space += (DIVISION_FACTOR - remainder)
            assert not MonsterSpriteObject.free_space % DIVISION_FACTOR

            pointer = (MonsterSpriteObject.free_space -
                       addresses.new_monster_graphics)
            pointer //= DIVISION_FACTOR
            assert 0 <= pointer <= 0x7fff

            self.misc_sprite_pointer &= 0x8000
            self.misc_sprite_pointer |= pointer
            check = (((self.misc_sprite_pointer & 0x7FFF) * DIVISION_FACTOR)
                     + addresses.new_monster_graphics)
            assert check == MonsterSpriteObject.free_space
            remainder = MonsterSpriteObject.free_space % DIVISION_FACTOR
            if remainder:
                MonsterSpriteObject.free_space += (DIVISION_FACTOR - remainder)

            outfile_rom_buffer.seek(MonsterSpriteObject.free_space)
            data = bytes([v for tile in self.tiles
                          for v in self.interleave_tile(tile)])
            outfile_rom_buffer.write(data)

            if self.is_8color:
                MonsterSpriteObject.free_space += (len(self.tiles) * 24)
            else:
                MonsterSpriteObject.free_space += (len(self.tiles) * 32)

            assert outfile_rom_buffer.tell() == MonsterSpriteObject.free_space
            assert MonsterSpriteObject.free_space < addresses.new_comp8_pointer

        if self.pair_protected is not None:
            assert self.pair_protected.written
            for attr in ['misc_sprite_pointer', 'stencil_index',
                         'misc_palette_index', 'low_palette_index']:
                setattr(self, attr, getattr(self.pair_protected, attr))

        super().write_data()
        self.written = True


class MonsterPaletteObject(TableObject):
    after_order = [MonsterSpriteObject]
    new_palettes = []

    @property
    def successor(self):
        return MonsterPaletteObject.get(self.index + 1)

    @cached_property
    def rgb_palette(self):
        multiplier = 0xff / 0x1f
        rgbs = []
        for c in self.colors + self.successor.colors:
            r = c & 0x1f
            g = (c >> 5) & 0x1f
            b = (c >> 10) & 0x1f
            a = (c >> 15)
            assert not a
            if a:
                r, g, b = 0, 0, 0
            r = int(round(multiplier * r))
            g = int(round(multiplier * g))
            b = int(round(multiplier * b))
            rgbs.append((r, g, b))
        return rgbs

    def compare_palette(self, palette, is_8color):
        if is_8color:
            max_index = 23
        else:
            max_index = 47

        index = 0
        for vs in self.rgb_palette:
            for v in vs:
                if v != palette[index]:
                    return False
                if index >= max_index:
                    return True
                index += 1

    def set_from_rgb(self, rgb_palette, is_8color):
        if 'rgb_palette' in self._property_cache:
            del (self._property_cache['rgb_palette'])

        multiplier = 0x1f / 0xff
        rgb_palette = rgb_palette[:48]
        zipped = zip(rgb_palette[0::3],
                     rgb_palette[1::3],
                     rgb_palette[2::3])
        palette = []
        for (r, g, b) in zipped:
            r = int(round(multiplier * r))
            g = int(round(multiplier * g))
            b = int(round(multiplier * b))
            assert 0 <= r <= 0x1f
            assert 0 <= g <= 0x1f
            assert 0 <= b <= 0x1f
            c = r | (g << 5) | (b << 10)
            palette.append(c)

        assert len(palette) >= 8
        self.colors = palette[:8]
        if not is_8color:
            if not len(palette) == 16:
                # Pad the palette with 0s
                palette += [0] * (16 - len(palette))
            assert self.successor not in MonsterPaletteObject.new_palettes
            self.successor.colors = palette[8:]
            MonsterPaletteObject.new_palettes.append(self.successor)

    @classmethod
    def get_free(cls):
        if not hasattr(MonsterPaletteObject, 'last_index'):
            MonsterPaletteObject.last_index = -1
        index = MonsterPaletteObject.last_index
        while True:
            index += 1
            mpo = MonsterPaletteObject.get(index)
            if mpo not in MonsterPaletteObject.new_palettes:
                MonsterPaletteObject.last_index = mpo.index
                MonsterPaletteObject.new_palettes.append(mpo)
                return mpo

    def write_data(self, pointer=None, syncing=False):
        if (self.index < addresses.previous_max_palettes
                or self in self.new_palettes):
            new_pointer = (addresses.new_palette_pointer
                           + (self.index * len(self.colors) * 2))
            assert (new_pointer + (len(self.colors) * 2)
                    < addresses.new_code_pointer)
            super().write_data(pointer=new_pointer)


class MonsterCompMixin(TableObject):
    @property
    def new_index(self):
        return self.index - self.specs.count


class MonsterComp8Object(MonsterCompMixin):
    after_order = [MonsterSpriteObject]

    def write_data(self, pointer=None, syncing=False):
        global outfile_rom_buffer
        if self.new_index >= 0:
            assert self.pointer is None
            self.pointer = addresses.new_comp8_pointer + 4 + (
                    self.new_index * len(self.stencil))
            assert (addresses.new_comp8_pointer + 4 <= self.pointer
                    < addresses.new_palette_pointer - len(self.stencil))
        super().write_data()
        self.written = True


class MonsterComp16Object(MonsterCompMixin):
    after_order = [MonsterComp8Object]

    def write_data(self, pointer=None, syncing=False):
        global outfile_rom_buffer
        if not hasattr(MonsterComp16Object, 'new_base_address'):
            for mc8 in MonsterComp8Object.every:
                assert mc8.written
            MonsterComp16Object.new_base_address = max(
                [mc8.pointer for mc8 in MonsterComp8Object.every]) + 8

            outfile_rom_buffer.seek(addresses.new_comp8_pointer)
            pointer = MonsterComp8Object.get(0).pointer & 0xffff
            outfile_rom_buffer.write(pointer.to_bytes(2, byteorder='little'))
            outfile_rom_buffer.seek(addresses.new_comp16_pointer)
            pointer = MonsterComp16Object.new_base_address & 0xffff
            outfile_rom_buffer.write(pointer.to_bytes(2, byteorder='little'))

        if self.new_index >= 0:
            self.pointer = MonsterComp16Object.new_base_address + (
                    self.new_index * len(self.stencil) * 2)
            assert (MonsterComp16Object.new_base_address <= self.pointer
                    < addresses.new_palette_pointer - len(self.stencil))

        super().write_data()


def nuke():
    f = get_open_file(get_outfile())
    f.seek(addresses.monster_graphics)
    f.write(b'\x00' * (addresses.end_monster_graphics -
                       addresses.monster_graphics))


def prepare_image(image: Image) -> Image:
    allowed_colors = 0x10
    image_filename = image.filename

    # If the image had transparent rows or columns, crop them out for efficiency
    border_color = get_transparency(image)
    solid_top = True
    solid_left = True
    image_width_in_pixels, image_height_in_pixels = image.size

    while solid_top or solid_left:
        pixel_data = image.convert('RGBA')
        current_color = border_color
        for x in range(image_width_in_pixels):
            # Scan the top and bottom rows of pixels, cropping out the row if it is fully transparent
            if not current_color == pixel_data.getpixel((x, 0))[3]:
                solid_top = False
            if not solid_top:
                break
            if x == image_width_in_pixels - 1 and solid_top:
                # If the top row was fully transparent, crop it out
                image = image.crop((0, 1, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size

        for y in range(image_height_in_pixels):
            # Scan the left and right columns of pixels, cropping out the column if it is fully transparent
            current_color = border_color
            if not current_color == pixel_data.getpixel((0, y))[3]:
                solid_left = False
            if not solid_left:
                break
            if y == image_height_in_pixels - 1 and solid_left:
                # If the left column was fully transparent, crop it out
                image = image.crop((1, 0, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size

    # Tiles are 8x8, so we ensure the image's width and height are divisible by 8
    image_width_in_pixels, image_height_in_pixels = image.size
    if not image_width_in_pixels % 8 == 0:
        border_width = 8 - (image_width_in_pixels % 8)
        image = ImageOps.expand(image, border=(0, 0, border_width, 0), fill=border_color)

    if not image_height_in_pixels % 8 == 0:
        border_width = 8 - (image_height_in_pixels % 8)
        image = ImageOps.expand(image, border=(0, 0, 0, border_width), fill=border_color)

    # If the image has too many colors, convert it into a form with reduced colors
    # if max(palette_indexes) > allowed_colors:
    palette_indexes = set(image.tobytes())
    if max(palette_indexes) != 8 and max(palette_indexes) != 16:
        if image.mode == "P":
            # Images already in P mode cannot be converted to P mode to shrink their allowed colors, so
            #   temporarily convert them back to RGB
            image = image.convert("RGBA")
        image = image.convert("P", palette=Image.ADAPTIVE, colors=int(allowed_colors))

    image.filename = image_filename
    return image


def remonsterate(connection: Pipe, **kwargs):
    try:
        if "outfile_rom_buffer" not in kwargs.keys():
            connection.send(RuntimeError("Remonsterate was not supplied an output file."))

        global outfile_rom_buffer
        global seed
        outfile_rom_buffer = kwargs.get("outfile_rom_buffer")
        seed = kwargs.get("seed", int(time()))
        images_tags_filename = kwargs.get("images_tags_filename", "images_and_tags.txt")
        monsters_tags_filename = kwargs.get("monsters_tags_filename", "monsters_and_tags.txt")
        rom_type = kwargs.get("rom_type", None)
        list_of_monsters = kwargs.get("list_of_monsters", None)

        global randomize_connection
        randomize_connection = connection
        images = []
        try:
            for line in open(os.path.join(file_paths, images_tags_filename)):
                if '#' in line:
                    line, comment = line.split('#', 1)
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    image_filename, tags = line.split(':')
                    tags = tags.split(',')
                    tags = {t for t in tags if t.strip()}
                else:
                    image_filename, tags = line, set([])
                try:
                    image = prepare_image(Image.open(os.path.join(sprite_paths, image_filename)))
                    image.tags = tags
                    # image.close()
                    images.append(image)
                except FileNotFoundError:
                    connection.send("Remonsterate: %s was listed in images_and_tags.txt, "
                                    "but was not found in the sprites directory." % image_filename)
            if len(images) == 0:
                connection.send("Remonsterate: images_and_tags.txt is empty. To use remonsterate, "
                                "place .png images into the sprites folder and document the file paths to those images in "
                                "images_and_tags.txt along with any applicable tags")
                return
        except FileNotFoundError as e:
            connection.send(e)
            return

        begin_remonsterate(rom_type=rom_type)

        try:
            if monsters_tags_filename is not None:
                for line in open(os.path.join(file_paths, monsters_tags_filename)):
                    if '#' in line:
                        line, comment = line.split('#', 1)
                    line = line.strip()
                    if ':' not in line:
                        continue
                    index, tags = line.split(':')
                    index = int(index, 0x10)
                    tags = tags.split(',')
                    tags = {t for t in tags if t.strip()}
                    whitelist = {t for t in tags if not t.startswith('!')}
                    blacklist = {t[1:] for t in tags if t.startswith('!')}
                    MonsterSpriteObject.get(index).whitelist = whitelist
                    MonsterSpriteObject.get(index).blacklist = blacklist
        except FileNotFoundError:
            connection.send("Remonsterate: No monsters_and_tags.txt file was found in the remonsterate directory.")
        MonsterSpriteObject.import_images = sorted(images,
                                                   key=lambda i: i.filename)

        msos = list(MonsterSpriteObject.every)
        random.shuffle(msos)
        for mso in msos:
            if not mso.select_image(list_of_monsters=list_of_monsters):
                connection.send("Remonsterate: All usable images have been exhausted. "
                                "Some monsters may not be randomized.")
                break

        # Wrapped in a try/except/finally block so that even if finish_remonsterate errors, the images are closed
        results = finish_remonsterate(list_of_monsters)
        connection.send((outfile_rom_buffer, results))
    except Exception as exc:
        # connection.send(type(exc)(traceback.format_exc()))
        connection.send(exc)
    finally:
        try:
            if images:
                for image in images:
                    # Remonsterate is finished. Close all the image files.
                    image.close()
        except UnboundLocalError:
            pass


def begin_remonsterate(rom_type=None):
    global ALL_OBJECTS

    if rom_type in ('1.0', '1.1'):
        label = 'FF6_NA_%s' % rom_type
        set_global_label(label)
        tables_list = ('tables_list.txt' if rom_type != '1.1'
                       else 'tables_list_1.1.txt')
        set_global_table_filename(tables_list)
    else:
        determine_global_table(outfile_rom_buffer)  # Calls set_global_table_filenamew

    # TODO: Document what this is writing
    outfile_rom_buffer.seek(0)
    block = outfile_rom_buffer.read(0x10000)
    outfile_rom_buffer.seek(0x400000)
    outfile_rom_buffer.write(block)

    set_seed(seed)
    random.seed(seed)

    set_global_output_file_buffer(outfile_rom_buffer)

    ALL_OBJECTS = [g for g in globals().values() if
                   isinstance(g, type) and issubclass(g, TableObject) and g not in [TableObject]]
    set_table_specs(ALL_OBJECTS)
    ALL_OBJECTS = sort_good_order(ALL_OBJECTS)
    assert ALL_OBJECTS

    for o in ALL_OBJECTS:
        o.every
    for o in ALL_OBJECTS:
        o.ranked

    for index in MonsterSpriteObject.PROTECTED_INDEXES:
        MonsterSpriteObject.get(index).image

    write_patches(randomize_connection)


def finish_remonsterate(list_of_monsters):
    for o in ALL_OBJECTS:
        o.write_all(outfile_rom_buffer)

    outfile_rom_buffer.seek(0)
    block1 = outfile_rom_buffer.read(0x10000)
    outfile_rom_buffer.seek(0x400000)
    block81 = outfile_rom_buffer.read(0x10000)

    assert block1 == block81

    remonsterate_results = []
    for mso in MonsterSpriteObject.every:
        try:
            current_monster = list_of_monsters[mso.get_index()]
            monster_display_name = current_monster.display_name.strip('_')
            monster_original_name = current_monster.name.strip('_')
            if monster_display_name != '' and monster_original_name != '':
                log_string = f"{monster_display_name:10}" + ' (' + f"{monster_original_name:10}" + ')'
                if hasattr(mso.image, 'filename'):
                    remonsterate_results.append(log_string + ' -> ' +
                                                mso.image.filename[mso.image.filename.rindex('sprites') +
                                                                   len('sprites') + 1:] + '.')
                else:
                    remonsterate_results.append(log_string + ' -> original sprite.')
        except IndexError:
            continue
    return remonsterate_results


def generate_tag_file(tag_file):
    # Create the default images_and_tags.txt and monsters_and_tags.txt files
    with open(tag_file, 'w') as text_file:
        text_file.write(
'''# This is a sample image list file.
# This file contains the paths to every sprite that you wish to import randomly.
# The format is: path/to/file.png:tag1,tag2,tag3
# You can also omit the tags.
#
# Examples:
# sprites/dragon.png:reptile,flying,kickass,boss
# sprites/unicorn.png''')


def construct_tag_file_from_dirs(sprite_directory, tag_file):
    # Populate the file name lists. Iterates through directories starting in the
    #   remonsterate directory. Does not traverse directories past
    #   the depth specified by walk_distance.
    walk_distance = 6
    sprite_directory_level = sprite_directory.count(os.path.sep)
    spritelist = ""
    print("Generating images_and_tags.txt using the updated sprite files.")
    for root, dirs, files in os.walk(sprite_directory):
        current_walking_directory = os.path.abspath(root)
        current_directory_level = current_walking_directory.count(os.path.sep)

        if current_directory_level > sprite_directory_level + walk_distance:
            # del dirs[:] empties the list that os.walk uses to determine what
            #   directories to walk through, meaning os.walk will move on to
            #   the next directory. It does NOT delete or modify files on the
            #   hard drive.
            if len(dirs) > 0:
                print("There were additional unexplored directories in " + current_walking_directory + ".")
            del dirs[:]
        else:
            for file_name in files:
                if file_name.lower().endswith(".png"):
                    spritelist += str(os.path.join(root, file_name))[len(sprite_directory) + 1:] + "\n"

    with open(tag_file, 'w') as text_file:
        text_file.write(spritelist)


def generate_sample_monster_list(tag_file):
    with open(tag_file, 'w') as text_file:
        text_file.write(
'''# This is a sample monster list file.
# This list is used to whitelist or blacklist specific tags for each monster.
# It is not necessary to list every monster in the game.
#
# The format is: monster_index:white_tag1,white_tag2,!black_tag1,!black_tag2
#   The monster index is in hexadecimal.
#   An exclamation point (!) denotes a blacklisted flag.
#
# If any tags are whitelisted, that monster can ONLY use sprites with
#   ALL of those tags.
# If a tag is blacklisted, that monster cannot use ANY sprites with that tag.
# These tags only work when using the default randomization functions.
#
# Examples:
# 0:humanoid,!female            # Narshe Guard
# 53:town,large,!boss           # HadesGigas
# 5d:desert                     # Areneid
# 128:humanoid,female,boss      # Goddess

# Guard_____
000:

# Soldier___
001:

# Templar___
002:

# Ninja_____
003:

# Samurai___
004:

# Orog______
005:

# Mag_Roader
006:

# Retainer__
007:

# Hazer_____
008:

# Dahling___
009:

# Rain_Man__
00A:

# Brawler___
00B:

# Apokryphos
00C:

# Dark_Force
00D:

# Whisper___
00E:

# Over_Mind_
00F:

# Osteosaur_
010:

# Commander_
011:

# Rhodox____
012:

# Were_Rat__
013:

# Ursus_____
014:

# Rhinotaur_
015:

# Steroidite
016:

# Leafer____
017:

# Stray_Cat_
018:

# Lobo______
019:

# Doberman__
01A:

# Vomammoth_
01B:

# Fidor_____
01C:

# Baskervor_
01D:

# Suriander_
01E:

# Chimera___
01F:

# Behemoth__
020:

# Mesosaur__
021:

# Pterodon__
022:

# FossilFang
023:

# White_Drgn
024:

# Doom_Drgn_
025:

# Brachosaur
026:

# Tyranosaur
027:

# Dark_Wind_
028:

# Beakor____
029:

# Vulture___
02A:

# Harpy_____
02B:

# HermitCrab
02C:

# Trapper___
02D:

# Hornet____
02E:

# CrassHoppr
02F:

# Delta_Bug_
030:

# Gilomantis
031:

# Trilium___
032:

# Nightshade
033:

# TumbleWeed
034:

# Bloompire_
035:

# Trilobiter
036:

# Siegfried_
037:

# Nautiloid_
038:

# Exocite___
039:

# Anguiform_
03A:

# Reach_Frog
03B:

# Lizard____
03C:

# ChickenLip
03D:

# Hoover____
03E:

# Rider_____
03F:

# Chupon____
040:

# Pipsqueak_
041:

# M_TekArmor
042:

# Sky_Armor_
043:

# Telstar___
044:

# Lethal_Wpn
045:

# Vaporite__
046:

# Flan______
047:

# Ing_______
048:

# Humpty____
049:

# Brainpan__
04A:

# Cruller___
04B:

# Cactrot___
04C:

# Repo_Man__
04D:

# Harvester_
04E:

# Bomb______
04F:

# Still_Life
050:

# Boxed_Set_
051:

# SlamDancer
052:

# HadesGigas
053:

# Pug_______
054:

# Magic_Urn_
055:

# Mover_____
056:

# Figaliz___
057:

# Buffalax__
058:

# Aspik_____
059:

# Ghost_____
05A:

# Crawler___
05B:

# Sand_Ray__
05C:

# Areneid___
05D:

# Actaneon__
05E:

# Sand_Horse
05F:

# Dark_Side_
060:

# Mad_Oscar_
061:

# Crawly____
062:

# Bleary____
063:

# Marshal___
064:

# Trooper___
065:

# General___
066:

# Covert____
067:

# Ogor______
068:

# Warlock___
069:

# Madam_____
06A:

# Joker_____
06B:

# Iron_Fist_
06C:

# Goblin____
06D:

# Apparite__
06E:

# PowerDemon
06F:

# Displayer_
070:

# Vector_Pup
071:

# Peepers___
072:

# Sewer_Rat_
073:

# Slatter___
074:

# Rhinox____
075:

# Rhobite___
076:

# Wild_Cat__
077:

# Red_Fang__
078:

# Bounty_Man
079:

# Tusker____
07A:

# Ralph_____
07B:

# Chitonid__
07C:

# Wart_Puck_
07D:

# Rhyos_____
07E:

# SrBehemoth
07F:

# Vectaur___
080:

# Wyvern____
081:

# Zombone___
082:

# Dragon____
083:

# Brontaur__
084:

# Allosaurus
085:

# Cirpius___
086:

# Sprinter__
087:

# Gobbler___
088:

# Harpiai___
089:

# GloomShell
08A:

# Drop______
08B:

# Mind_Candy
08C:

# WeedFeeder
08D:

# Luridan___
08E:

# Toe_Cutter
08F:

# Over_Grunk
090:

# Exoray____
091:

# Crusher___
092:

# Uroburos__
093:

# Primordite
094:

# Sky_Cap___
095:

# Cephaler__
096:

# Maliga____
097:

# Gigan_Toad
098:

# Geckorex__
099:

# Cluck_____
09A:

# Land_Worm_
09B:

# Test_Rider
09C:

# PlutoArmor
09D:

# Tomb_Thumb
09E:

# HeavyArmor
09F:

# Chaser____
0A0:

# Scullion__
0A1:

# Poplium___
0A2:

# Intangir__
0A3:

# Misfit____
0A4:

# Eland_____
0A5:

# Enuo______
0A6:

# Deep_Eye__
0A7:

# GreaseMonk
0A8:

# NeckHunter
0A9:

# Grenade___
0AA:

# Critic____
0AB:

# Pan_Dora__
0AC:

# SoulDancer
0AD:

# Gigantos__
0AE:

# Mag_Roader
0AF:

# Spek_Tor__
0B0:

# Parasite__
0B1:

# EarthGuard
0B2:

# Coelecite_
0B3:

# Anemone___
0B4:

# Hipocampus
0B5:

# Spectre___
0B6:

# Evil_Oscar
0B7:

# Slurm_____
0B8:

# Latimeria_
0B9:

# StillGoing
0BA:

# Allo_Ver__
0BB:

# Phase_____
0BC:

# Outsider__
0BD:

# Barb_e____
0BE:

# Parasoul__
0BF:

# Pm_Stalker
0C0:

# Hemophyte_
0C1:

# Sp_Forces_
0C2:

# Nohrabbit_
0C3:

# Wizard____
0C4:

# Scrapper__
0C5:

# Ceritops__
0C6:

# Commando__
0C7:

# Opinicus__
0C8:

# Poppers___
0C9:

# Lunaris___
0CA:

# Garm______
0CB:

# Vindr_____
0CC:

# Kiwok_____
0CD:

# Nastidon__
0CE:

# Rinn______
0CF:

# Insecare__
0D0:

# Vermin____
0D1:

# Mantodea__
0D2:

# Bogy______
0D3:

# Prussian__
0D4:

# Black_Drgn
0D5:

# Adamanchyt
0D6:

# Dante_____
0D7:

# Wirey_Drgn
0D8:

# Dueller___
0D9:

# Psychot___
0DA:

# Muus______
0DB:

# Karkass___
0DC:

# Punisher__
0DD:

# Balloon___
0DE:

# Gabbldegak
0DF:

# GtBehemoth
0E0:

# Scorpion__
0E1:

# Chaos_Drgn
0E2:

# Spit_Fire_
0E3:

# Vectagoyle
0E4:

# Lich______
0E5:

# Osprey____
0E6:

# Mag_Roader
0E7:

# Bug_______
0E8:

# Sea_Flower
0E9:

# Fortis____
0EA:

# Abolisher_
0EB:

# Aquila____
0EC:

# Junk______
0ED:

# Mandrake__
0EE:

# 1st_Class_
0EF:

# Tap_Dancer
0F0:

# Necromancr
0F1:

# Borras____
0F2:

# Mag_Roader
0F3:

# Wild_Rat__
0F4:

# Gold_Bear_
0F5:

# Innoc_____
0F6:

# Trixter___
0F7:

# Red_Wolf__
0F8:

# Didalos___
0F9:

# Woolly____
0FA:

# Veteran___
0FB:

# Sky_Base__
0FC:

# IronHitman
0FD:

# Io________
0FE:

# Pugs______
0FF:

# Whelk_____
100:

# Presenter_
101:

# Mega_Armor
102:

# Vargas____
103:

# TunnelArmr
104:

# Prometheus
105:

# GhostTrain
106:

# Dadaluma__
107:

# Shiva_____
108:

# Ifrit_____
109:

# Number_024
10A:

# Number_128
10B:

# Inferno___
10C:

# Crane_____
10D:

# Crane_____
10E:

# Umaro_____
10F:

# Umaro_____
110:

# Guardian__
111:

# Guardian__
112:

# Air_Force_
113:

# Tritoch___
114:

# Tritoch___
115:

# FlameEater
116:

# AtmaWeapon
117:

# Nerapa____
118:

# SrBehemoth
119:

# Kefka_____
11A:

# Tentacle__
11B:

# Dullahan__
11C:

# Doom_Gaze_
11D:

# Chadarnook
11E:

# Curley____
11F:

# Larry_____
120:

# Moe_______
121:

# Wrexsoul__
122:

# Hidon_____
123:

# KatanaSoul
124:

# L_30_Magic
125:

# Hidonite__
126:

# Doom______
127:

# Goddess___
128:

# Poltrgeist
129:

# Kefka_____
12A:false_kefka_do_not_replace

# L_40_Magic
12B:

# Ultros____
12C:

# Ultros____
12D:

# Ultros____
12E:

# Chupon____
12F:

# L_20_Magic
130:

# Siegfried_
131:

# L_10_Magic
132:

# L_50_Magic
133:

# Head______
134:

# Whelk_Head
135:

# Colossus__
136:

# CzarDragon
137:

# Master_Pug
138:

# L_60_Magic
139:

# Merchant__
13A:

# B_Day_Suit
13B:

# Tentacle__
13C:

# Tentacle__
13D:

# Tentacle__
13E:

# RightBlade
13F:

# Left_Blade
140:

# Rough_____
141:

# Striker___
142:

# L_70_Magic
143:

# Tritoch___
144:

# Laser_Gun_
145:

# Speck_____
146:

# MissileBay
147:

# Chadarnook
148:

# Ice_Dragon
149:

# Kefka_____
14A:

# Storm_Drgn
14B:

# Dirt_Drgn_
14C:

# Ipooh_____
14D:

# Leader____
14E:

# Grunt_____
14F:

# Gold_Drgn_
150:

# Skull_Drgn
151:

# Blue_Drgn_
152:

# Red_Dragon
153:

# Piranha___
154:

# Rizopas___
155:

# Specter___
156:

# Short_Arm_
157:

# Long_Arm__
158:

# Face______
159:

# Tiger_____
15A:

# Tools_____
15B:

# Magic_____
15C:

# Hit_______
15D:

# Girl______
15E:

# Sleep_____
15F:

# Hidonite__
160:

# Hidonite__
161:

# Hidonite__
162:

# L_80_Magic
163:

# L_90_Magic
164:

# ProtoArmor
165:

# MagiMaster
166:

# SoulSaver_
167:

# Ultros____
168:

# Naughty___
169:

# Phunbaba__
16A:

# Phunbaba__
16B:

# Phunbaba__
16C:

# Phunbaba__
16D:

# __________
16E:

# __________
16F:

# __________
170:

# Zone_Eater
171:

# __________
172:

# __________
173:

# __________
174:

# Officer___
175:

# Cadet_____
176:

# __________
177:

# __________
178:

# Soldier___
179:

# __________
17A:

# __________
17B:

# __________
17C:

# Atma______
17D:

# __________
17E:

# __________
17F:''')
