import random
import struct
from collections import OrderedDict, defaultdict
from hashlib import md5
from math import ceil
from os import path

MODULE_FILEPATH, _ = path.split(__file__)


utilrandom = random.Random()
utran = utilrandom
random = utilrandom


def cached_property(fn):
    @property
    def cacher(self):
        if not hasattr(self, '_property_cache'):
            self._property_cache = {}

        if fn.__name__ not in self._property_cache:
            self._property_cache[fn.__name__] = fn(self)

        return self._property_cache[fn.__name__]

    return cacher


class classproperty(property):
    def __get__(self, inst, cls):
        return self.fget(cls)


def clached_property(fn):
    @classproperty
    def cacher(self):
        if not hasattr(self, '_class_property_cache'):
            self._class_property_cache = {}

        if fn.__name__ not in self._class_property_cache:
            self._class_property_cache[fn.__name__] = fn(self)

        return self._class_property_cache[fn.__name__]

    return cacher


def checksum_calc_sum(data, length):
    return sum(map(int, data[:length]))


def checksum_mirror_sum(data, length, actual_size, mask=0x80000000):
    # this is basically an exact copy of the algorithm in snes9x's source
    while not (actual_size & mask) and mask:
        mask >>= 1
    part1 = checksum_calc_sum(data, mask)
    part2 = 0
    next_length = actual_size - mask
    if next_length:
        part2 = checksum_mirror_sum(data[mask:], next_length, mask >> 1)
        while (next_length < mask):
            next_length += next_length
            part2 += part2
    return part1 + part2


generator = {}
def generate_name(size=None, maxsize=10, namegen_table=None):
    if namegen_table is not None or not generator:
        lookback = None
        for line in open(namegen_table):
            key, values = tuple(line.strip().split())
            generator[key] = values
            if not lookback:
                lookback = len(key)
        return

    lookback = len(generator.keys()[0])

    if not size:
        halfmax = maxsize / 2
        size = random.randint(1, halfmax) + random.randint(1, halfmax)
        if size < 4:
            size += random.randint(0, halfmax)

    def has_vowel(text):
        for c in text:
            if c.lower() in "aeiouy":
                return True
        return False

    while True:
        starts = sorted([s for s in generator if s[0].isupper()])
        name = random.choice(starts)
        name = name[:size]
        while len(name) < size:
            key = name[-lookback:]
            if key not in generator and size - len(name) < len(key):
                name = random.choice(starts)
                continue
            if key not in generator or (random.randint(1, 15) == 15
                                        and has_vowel(name[-2:])):
                if len(name) <= size - lookback:
                    if len(name) + len(key) < maxsize:
                        name += " "
                    name += random.choice(starts)
                    continue
                else:
                    name = random.choice(starts)
                    continue

            c = random.choice(generator[key])
            name = name + c

        if len(name) >= size:
            return name


def get_snes_palette_transformer(use_luma=False, always=None, middle=True,
                                 basepalette=None):
    def generate_swapfunc(swapcode=None):
        if swapcode is None:
            swapcode = utran.randint(0, 7)

        f = lambda w: w
        g = lambda w: w
        h = lambda w: w
        if swapcode & 1:
            f = lambda x, y, z: (y, x, z)
        if swapcode & 2:
            g = lambda x, y, z: (z, y, x)
        if swapcode & 4:
            h = lambda x, y, z: (x, z, y)
        swapfunc = lambda w: f(*g(*h(*w)))

        return swapfunc

    def shift_middle(triple, degree, ungray=False):
        low, medium, high = tuple(sorted(triple))
        triple = list(triple)
        mediumdex = triple.index(medium)
        if ungray:
            lowdex, highdex = triple.index(low), triple.index(high)
            while utran.choice([True, False]):
                low -= 1
                high += 1

            low = max(0, low)
            high = min(31, high)

            triple[lowdex] = low
            triple[highdex] = high

        if degree < 0:
            value = low
        else:
            value = high
        degree = abs(degree)
        a = (1 - (degree/90.0)) * medium
        b = (degree/90.0) * value
        medium = a + b
        medium = int(round(medium))
        triple[mediumdex] = medium
        return tuple(triple)

    def get_ratio(a, b):
        if a > 0 and b > 0:
            return max(a, b) / float(min(a, b))
        elif abs(a-b) <= 1:
            return 1.0
        else:
            return 9999

    def color_to_components(color):
        blue = (color & 0x7c00) >> 10
        green = (color & 0x03e0) >> 5
        red = color & 0x001f
        return (red, green, blue)

    def components_to_color(components):
        red, green, blue = components
        return red | (green << 5) | (blue << 10)

    if always is not None and basepalette is not None:
        raise Exception("'always' argument incompatible with 'basepalette'")

    swapmap = {}
    if basepalette is not None and not use_luma:
        threshold = 1.2

        def color_to_index(color):
            red, green, blue = color_to_components(color)
            a = red >= green
            b = red >= blue
            c = green >= blue
            d = get_ratio(red, green) >= threshold
            e = get_ratio(red, blue) >= threshold
            f = get_ratio(green, blue) >= threshold

            index = (d << 2) | (e << 1) | f
            index |= ((a and not d) << 5)
            index |= ((b and not e) << 4)
            index |= ((c and not f) << 3)

            return index

        colordict = defaultdict(set)
        for color in basepalette:
            index = color_to_index(color)
            colordict[index].add(color)

        saturated = dict((k, v) for (k, v) in colordict.items() if k & 0x7)
        satlist = sorted(saturated)
        random.shuffle(satlist)
        grouporder = sorted(satlist, key=lambda k: len(saturated[k]),
                            reverse=True)
        if grouporder:
            dominant = grouporder[0]
            domhue, domsat = dominant >> 3, dominant & 0x7
            for key in grouporder[1:]:
                colhue, colsat = key >> 3, key & 0x7
                if (domhue ^ colhue) & (domsat | colsat) == 0:
                    continue
                secondary = key
                break
            else:
                secondary = dominant
            sechue, secsat = secondary >> 3, secondary & 0x7
        else:
            dominant, domhue, domsat = 0, 0, 0
            secondary, sechue, secsat = 0, 0, 0

        while True:
            domswap = random.randint(0, 7)
            secswap = random.randint(0, 7)
            tertswap = random.randint(0, 7)
            if domswap == secswap:
                continue
            break

        for key in colordict:
            colhue, colsat = key >> 3, key & 0x7
            if ((domhue ^ colhue) & (domsat | colsat)) == 0:
                if ((sechue ^ colhue) & (secsat | colsat)) == 0:
                    swapmap[key] = random.choice([domswap, secswap])
                else:
                    swapmap[key] = domswap
            elif ((sechue ^ colhue) & (secsat | colsat)) == 0:
                swapmap[key] = secswap
            elif ((domhue ^ colhue) & domsat) == 0:
                if ((sechue ^ colhue) & secsat) == 0:
                    swapmap[key] = random.choice([domswap, secswap])
                else:
                    swapmap[key] = domswap
            elif ((sechue ^ colhue) & secsat) == 0:
                swapmap[key] = secswap
            elif ((domhue ^ colhue) & colsat) == 0:
                if ((sechue ^ colhue) & colsat) == 0:
                    swapmap[key] = random.choice([domswap, secswap])
                else:
                    swapmap[key] = domswap
            elif ((sechue ^ colhue) & colsat) == 0:
                swapmap[key] = secswap
            else:
                swapmap[key] = tertswap

    elif basepalette is not None and use_luma:
        def color_to_index(color):
            red, green, blue = color_to_components(color)
            index = red + green + blue
            return index

        values = []
        for color in basepalette:
            index = color_to_index(color)
            values.append(index)
        values = sorted(values)
        low, high = min(values), max(values)
        median = values[len(values)/2]
        clusters = [set([low]), set([high])]
        done = set([low, high])
        if median not in done and random.choice([True, False]):
            clusters.append(set([median]))
            done.add(median)

        to_cluster = sorted(basepalette)
        random.shuffle(to_cluster)
        for color in to_cluster:
            index = color_to_index(color)
            if index in done:
                continue
            done.add(index)

            def cluster_distance(cluster):
                distances = [abs(index-i) for i in cluster]
                return sum(distances) / len(distances)
                nearest = min(cluster, key=lambda x: abs(x-index))
                return abs(nearest-index)

            chosen = min(clusters, key=cluster_distance)
            chosen.add(index)

        swapmap = {}
        for cluster in clusters:
            swapcode = random.randint(0, 7)
            for index in cluster:
                assert index not in swapmap
                swapmap[index] = swapcode

        remaining = [i for i in range(94) if i not in swapmap.keys()]
        random.shuffle(remaining)

        def get_nearest_swapcode(index):
            nearest = min(swapmap, key=lambda x: abs(x-index))
            return nearest

        for i in remaining:
            nearest = get_nearest_swapcode(i)
            swapmap[i] = swapmap[nearest]

    else:
        def color_to_index(color):
            return 0

        if always:
            swapmap[0] = random.randint(1, 7)
        else:
            swapmap[0] = random.randint(0, 7)

    for key in swapmap:
        swapmap[key] = generate_swapfunc(swapmap[key])

    if middle:
        degree = utran.randint(-75, 75)

    def palette_transformer(raw_palette, single_bytes=False):
        if single_bytes:
            raw_palette = zip(raw_palette, raw_palette[1:])
            raw_palette = [p for (i, p) in enumerate(raw_palette) if not i % 2]
            raw_palette = [(b << 8) | a for (a, b) in raw_palette]
        transformed = []
        for color in raw_palette:
            index = color_to_index(color)
            swapfunc = swapmap[index]
            red, green, blue = color_to_components(color)
            red, green, blue = swapfunc((red, green, blue))
            if middle:
                red, green, blue = shift_middle((red, green, blue), degree)
            color = components_to_color((red, green, blue))
            transformed.append(color)
        if single_bytes:
            major = [p >> 8 for p in transformed]
            minor = [p & 0xFF for p in transformed]
            transformed = []
            for a, b in zip(minor, major):
                transformed.append(a)
                transformed.append(b)
        return transformed

    return palette_transformer


def hexify(s):
    if isinstance(s, int):
        num_bytes = ceil(len(f'{s:x}')/2)
        s = s.to_bytes(length=num_bytes, byteorder='little')
    return ' '.join([f'{w:0>2x}' for w in s])


def hexstring(value):
    if type(value) is str:
        value = "".join(["{0:0>2}".format("%x" % ord(c)) for c in value])
    elif type(value) is int:
        value = "{0:0>2}".format("%x" % value)
    elif type(value) is list:
        value = " ".join([hexstring(v) for v in value])
    return value


def ips_patch(outfile, ips_filename):
    patchlist = []
    with open(ips_filename, 'r+b') as f:
        magic_str = f.read(5)
        assert magic_str == b'PATCH'
        while True:
            offset = f.read(3)
            blocksize = f.read(2)
            if len(offset) < 3 or len(blocksize) < 2:
                assert offset == b'EOF'
                break
            offset = int.from_bytes(offset, byteorder='big')
            blocksize = int.from_bytes(blocksize, byteorder='big')
            if blocksize == 0:
                # RLE encoding
                blocksize = f.read(2)
                assert len(blocksize) == 2
                blocksize = int.from_bytes(blocksize, byteorder='big')
                repeat_byte = f.read(1)
                assert len(repeat_byte) == 1
                block = repeat_byte * blocksize
            else:
                block = f.read(blocksize)
            assert len(block) == blocksize
            patchlist.append((offset, block))

    with open(outfile, 'r+b') as f:
        for offset, block in patchlist:
            f.seek(offset)
            f.write(block)


def line_wrap(things, width=16):
    newthings = []
    while things:
        newthings.append(things[:width])
        things = things[width:]
    return newthings


def map_from_lorom(lorom_address):
    lorom_address &= 0x7FFFFF
    base = (lorom_address >> 1) & 0xFFFF8000
    address = base | (lorom_address & 0x7FFF)
    #assert lorom_address == map_to_lorom(address)
    return address


def map_from_snes(address, lorom=False):
    if lorom:
        return map_from_lorom(address)
    if address & 0xC00000 == 0xC00000:
        return address & 0x3FFFFF
    if 0x400000 <= address < 0x7E0000:
        return address
    if address & 0x8000 and (address >> 16) in (0x3E, 0x3F):
        raise NotImplementedError
    raise ValueError('%X cannot be mapped to ROM.' % address)


def map_to_lorom(address):
    if address > 0x3fffff:
        raise Exception('LOROM address out of range.')
    base = ((address << 1) & 0xFFFF0000)
    lorom_address = base | 0x8000 | (address & 0x7FFF)
    assert (map_from_lorom(lorom_address & 0x7fffff) ==
            map_from_lorom(lorom_address | 0x800000))
    return lorom_address | 0x800000


def map_to_snes(address, lorom=False):
    if lorom:
        return map_to_lorom(address)
    assert 0 <= address <= 0x7FFFFF
    if address < 0x400000:
        return address | 0xC00000
    elif address < 0x7E0000:
        return address
    elif 0x7E0000 <= address <= 0x7FFFFF and not address & 0x8000:
        return address
    else:
        # NOTE: Normally 7E and 7F can be accessed with banks 3E and 3F
        # But we cannot use 3E:0000-3E:7FFF or 3F:0000-3F:7FFF
        # Only 3E:8000-3E:FFFF and 3F:8000-3F:FFFF can be used
        # In all, ExHiROM can address 63.5 MBits of ROM
        # But that last 0.5 MBits seems like a pain so let's just ignore it
        raise NotImplementedError


def mask_compress(value, mask=None):
    if mask is None:
        mask = value
    i, j = 0, 0
    result_value, result_mask = 0, 0
    while True:
        if not mask >> i:
            assert not value >> i
            break
        ibit = (1 << i)
        if (mask & ibit):
            jbit = (1 << j)
            result_mask |= jbit
            if value & ibit:
                result_value |= jbit
            j += 1
        else:
            assert not (value & ibit)
        i += 1
    assert bin(result_mask).count('0') == 1
    return result_value, result_mask


def mask_decompress(value, mask):
    decompressed = 0
    counter = 0
    while True:
        bitmask = 1 << counter
        if bitmask > mask:
            break
        if bitmask & mask:
            if value & 1:
                decompressed |= bitmask
            value >>= 1
        counter += 1
    if value:
        raise Exception('Value overflowed mask.')
    assert not value
    return decompressed


def md5hash(filename, blocksize=65536):
    m = md5()
    with open(filename, 'rb') as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def read_multi(f, length=2, reverse=True):
    vals = list(map(int, f.read(length)))
    if reverse:
        vals = list(reversed(vals))
    value = 0
    for val in vals:
        value = value << 8
        value = value | val
    return value


def read_lines_nocomment(filename):
    lines = []
    with open(filename, encoding='utf8') as f:
        for line in f:
            if '#' in line:
                line, _ = line.split('#', 1)
            line = line.rstrip()
            if not line:
                continue
            lines.append(line)
    return lines


def reverse_byte_order(value, length=None, mask=None):
    if mask is None:
        mask = (2**(length*8)) - 1
    assert mask
    while not mask & 1:
        mask >>= 1

    reverse_value = 0
    assert mask & 1
    while True:
        reverse_value <<= 8
        reverse_value |= value & 0xff
        value >>= 8
        mask >>= 8
        if not mask:
            break
    return reverse_value


def rewrite_snes_checksum(filename, lorom=False):
    f = open(filename, 'r+b')
    f.seek(0, 2)
    actual_size = f.tell()
    if actual_size & (0x1FFFF):
        print("WARNING: The rom is a strange size.")

    if lorom:
        rommask = 0x7FFF
    else:
        rommask = 0xFFFF
    expected_header_size = 0x9
    while actual_size > (1024 << expected_header_size):
        expected_header_size += 1
    f.seek(0xFFD7 & rommask)
    previous_header_size = ord(f.read(1))
    if previous_header_size != expected_header_size:
        print("WARNING: Game rom reports incorrect size. Fixing.")
        f.seek(0xFFD7 & rommask)
        f.write(expected_header_size.to_bytes(1, byteorder='little'))

    f.seek(0, 0)
    data = f.read()
    checksum = checksum_mirror_sum(data, actual_size, actual_size)

    checksum &= 0xFFFF
    f.seek(0xFFDE & rommask)
    write_multi(f, checksum, length=2)
    f.seek(0xFFDC & rommask)
    write_multi(f, checksum ^ 0xFFFF, length=2)
    f.close()


def rewrite_snes_title(text, filename, version, lorom=False):
    f = open(filename, 'r+b')
    while len(text) < 21:
        text += ' '
    if len(text) > 21:
        text = text[:20] + "?"
    if lorom:
        mask = 0x7FFF
    else:
        mask = 0xFFFF
    f.seek(0xFFC0 & mask)
    f.write(bytes(text.encode('ascii')))
    f.seek(0xFFDB & mask)
    if isinstance(version, str) and '.' in version:
        version = version.split('.')[0]
    f.write(bytes([int(version)]))
    f.close()


NESTED_FAIL = object()
def search_nested_key(nested, key, root=True):
    if key in nested:
        return nested[key]
    candidates = [search_nested_key(v, key, root=False)
                  for v in nested.values() if isinstance(v, dict)]
    candidates = [c for c in candidates if c is not NESTED_FAIL]
    if len(candidates) == 1:
        return candidates[0]
    if root:
        if not candidates:
            raise Exception(f'Nested key not found: {key}')
        raise Exception(f'Nested key not unique: {key}')
    return NESTED_FAIL


def summarize_state():
    a, b, c = utilrandom.getstate()
    b = hash(b)
    return a, b, c


done_warnings = set()
def warn(msg, repeat=False, repeat_key=None):
    if repeat_key is None:
        repeat_key = msg
    if repeat is False and repeat_key in done_warnings:
        return
    print(f'WARNING: {msg}')
    if repeat_key is not None:
        done_warnings.add(repeat_key)


def write_multi(f, value, length=2, reverse=True):
    vals = []
    while value:
        vals.append(value & 0xFF)
        value = value >> 8
    if len(vals) > length:
        raise Exception("Value length mismatch.")

    while len(vals) < length:
        vals.append(0x00)

    if not reverse:
        vals = reversed(vals)

    f.write(bytes(vals))


class fake_yaml:
    SafeLoader = None

    def verify_result(text, data):
        import yaml
        assert yaml.safe_load(text) == data

    def load(text, Loader=None, testing=False):
        try:
            if testing:
                raise ImportError
            import yaml
            if Loader is not None:
                return yaml.load(text, Loader=Loader)
            return yaml.safe_load(text)
        except ImportError:
            pass

        import json

        def format_key(key):
            if key.startswith('0x') or key.startswith('-0x'):
                try:
                    return int(key, 0x10)
                except ValueError:
                    pass
            try:
                return int(key)
            except ValueError:
                if key.startswith('"') and key.endswith('"'):
                    key = key[1:-1]
                if key.startswith("'") and key.endswith("'"):
                    key = key[1:-1]
            return key

        def format_value(value):
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1]
            if value.startswith("'") and value.endswith("'"):
                return value[1:-1]
            value = format_key(value)
            if isinstance(value, int):
                return value
            try:
                return float(value)
            except ValueError:
                pass
            if value.startswith('[') and value.endswith(']'):
                values = value[1:-1].split(',')
                values = [v.strip() for v in values]
                return [format_value(v) for v in values]
            if value.lower() in ('yes', 'true'):
                return True
            if value.lower() in ('no', 'false'):
                return False
            return value

        data = OrderedDict()
        nested = [(-1, data)]
        lines = text.splitlines()
        temp = []
        for line in lines:
            if '#' in line:
                line, _ = line.split('#', 1)
            line = line.rstrip()
            if not line:
                continue
            if ':' in line:
                temp.append(line)
            else:
                temp[-1] = ' '.join((temp[-1], line))
        lines = temp
        for line in lines:
            test = line.lstrip()
            indentation = len(line) - len(test)
            assert ':' in line
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            while True:
                (a, b) = nested[-1]
                if a >= indentation:
                    nested = nested[:-1]
                else:
                    break

            _, subnested = nested[-1]
            if value:
                subnested[format_key(key)] = format_value(value)
            else:
                next_nested = OrderedDict()
                subnested[format_key(key)] = next_nested
                nested.append((indentation, next_nested))

        _, data = nested[0]
        if testing:
            fake_yaml.verify_result(text, data)
        return data

    def safe_load(text, testing=False):
        return fake_yaml.load(text, testing=testing)


class MaskStruct:
    WARNED = False

    def __init__(self, data, masks, length=None, data_types=None,
                 byteorders=None, collapsible=None):
        assert isinstance(data, bytes)
        self._original_packed = data
        self._masks = masks
        self._byteorders = byteorders or {}
        self._collapsible = collapsible or {}
        self._data_types = data_types or {}
        self._list_bit_lengths = {}
        self._list_endianness = {}

        if length is None:
            length = 0
            biggest = max(self._masks.values())
            while biggest:
                length += 1
                biggest >>= 8
            if length != len(data) and not MaskStruct.WARNED:
                print('WARNING: Length/data mismatch.')
                MaskStruct.WARNED = True
        self._length = length

        bigend_data = int.from_bytes(data, byteorder='big')
        litend_data = int.from_bytes(data, byteorder='little')

        for attr in self._masks:
            if attr not in self._data_types:
                self._data_types[attr] = 'int'

            bigend_mask = self._masks[attr]
            litend_mask = reverse_byte_order(bigend_mask,
                                             length=self._length)
            bigend_is_split = '0' in f'{bigend_mask:b}'.rstrip('0')
            litend_is_split = '0' in f'{litend_mask:b}'.rstrip('0')
            if attr not in self._collapsible:
                if self._data_types[attr] == 'int':
                    if attr in self._byteorders and \
                            self._byteorders[attr] == 'big' and \
                            not bigend_is_split:
                        self._collapsible[attr] = False
                    elif not litend_is_split:
                        self._collapsible[attr] = False
                    else:
                        self._collapsible[attr] = True
                else:
                    self._collapsible[attr] = False

            data_type = self._data_types[attr]
            if data_type.startswith('list'):
                _, num_items, endianness = data_type.split(',')
                num_items = int(num_items)
                num_bits = f'{bigend_mask:b}'.count('1')
                if num_bits % num_items:
                    raise Exception(f'{num_items} does not divide '
                                    f'evenly the {attr} field.')
                self._list_bit_lengths[attr] = num_bits // num_items
                self._list_endianness[attr] = endianness

            if attr not in self._byteorders:
                if data_type == 'str':
                    self._byteorders[attr] = 'big'
                elif data_type.startswith('lis') and \
                        not bigend_is_split and \
                        num_bits == num_items * 8:
                    self._byteorders[attr] = 'big'
                elif litend_is_split and not bigend_is_split:
                    self._byteorders[attr] = 'big'
                else:
                    self._byteorders[attr] = 'little'

            if data_type == 'str':
                self._list_bit_lengths[attr] = 8
                self._list_endianness[attr] = self._byteorders[attr]

        for attr, data_type in self._data_types.items():
            assert data_type.startswith('list') or data_type in ('int', 'str')

        self._original_values = self._unpack(data)
        for attr, value in sorted(self._original_values.items()):
            assert not hasattr(self, attr)
            setattr(self, attr, value)

    def __repr__(self):
        fieldstrs = []
        for field, value in self.unpacked.items():
            if isinstance(value, int):
                value = f'{value:0>2x}'
            if isinstance(value, list):
                value = ','.join([f'{v:0>2x}' for v in value])
            if isinstance(value, bytes):
                value = hexify(value).replace(' ', '')
            fieldstrs.append(f'{field}={value}')
        return '<%s>' % ';'.join(fieldstrs).strip()

    def _unpack(self, data):
        original_data = data
        result = {}
        bigend_data = int.from_bytes(data, byteorder='big')
        litend_data = int.from_bytes(data, byteorder='little')
        for attr, mask in sorted(self._masks.items()):
            data = bigend_data
            data_type = self._data_types[attr]
            if self._byteorders[attr] == 'little':
                data = litend_data
                mask = reverse_byte_order(mask, length=self._length)
            while mask & 1 == 0:
                mask >>= 1
                data >>= 1
            value = data & mask
            if self._collapsible[attr]:
                value, _ = mask_compress(value, mask)
            if data_type[:3] in ('str', 'lis'):
                bit_length = self._list_bit_lengths[attr]
                endianness = self._list_endianness[attr]
                mini_mask = (2**bit_length)-1
                sequence = []
                while mask:
                    v = value & mask & mini_mask
                    if endianness == 'big':
                        sequence.insert(0, v)
                    elif endianness == 'little':
                        sequence.append(v)
                    mask >>= bit_length
                    value >>= bit_length
                if data_type == 'str':
                    value = bytes(sequence)
                else:
                    value = sequence
            result[attr] = value
        return result

    def _repack(self, unpacked):
        bigend_data = 0
        for attr, mask in sorted(self._masks.items()):
            if self._byteorders[attr] == 'little':
                mask = reverse_byte_order(mask, length=self._length)
            value = unpacked[attr]
            if isinstance(value, bytes):
                value = [c for c in value]
            if isinstance(value, list):
                bit_length = self._list_bit_lengths[attr]
                endianness = self._list_endianness[attr]
                temp = 0
                value = list(value)
                if endianness == 'little':
                    value = list(reversed(value))
                while value:
                    temp <<= bit_length
                    v = value.pop(0)
                    assert len(f'{v:b}') <= bit_length
                    temp |= v
                value = temp
            if self._collapsible[attr]:
                value = mask_decompress(value, mask)
            else:
                while mask & 1 == 0:
                    mask >>= 1
                    value <<= 1
            if self._byteorders[attr] == 'little':
                value = reverse_byte_order(value, length=self._length)
            bigend_data |= value
        return bigend_data.to_bytes(length=self._length, byteorder='big')

    @property
    def unpacked(self):
        return {attr: getattr(self, attr) for attr in self._masks}

    @property
    def packed(self):
        unpacked = self.unpacked
        packed = self._repack(unpacked)
        test = self._unpack(packed)
        for attr in unpacked:
            if unpacked[attr] != test[attr]:
                raise Exception(f'Mask conflict: {attr}')
        return packed


class NamedStruct:
    FIELD_NAMES = None
    FORMAT_STRING = None
    VERIFIED = False

    def __init__(self, *args, **kwargs):
        self._original_values = None
        if not self.VERIFIED:
            self.verify()

        if args and kwargs:
            raise TypeError(f'Specify only one of {args} or {kwargs}')
        elif not (args or kwargs):
            raise TypeError(f'Please specify either a bytestring '
                            f'or keyword arguments.')
        elif args and len(args) > 1:
            raise TypeError(f'NamedStruct takes one non-keyword argument.')

        if args:
            data = args[0]
            if data is None:
                data = b'\x00' * self.expected_length
            self._original_values = self.unpack(data)
        else:
            self._original_values = OrderedDict()
            for field in self.FIELD_NAMES:
                self._original_values[field] = kwargs[field]

        if len(self._original_values) != len(self.FIELD_NAMES):
            difference = set(self.FIELD_NAMES) - self._original_values.keys()
            raise TypeError(f'Missing fields {difference}')

        for field, value in self._original_values.items():
            setattr(self, field, value)

    def __repr__(self):
        s = f'{self.__class__.__name__}: '
        fieldstrs = []
        for field, value in self.unpacked.items():
            if isinstance(value, int):
                value = f'{value:x}'
            if isinstance(value, bytes):
                value = hexify(value).replace(' ', '')
            fieldstrs.append(f'{field}={value}')
        return (s + ','.join(fieldstrs)).strip()

    def __hash__(self):
        return self.packed.__hash__()

    def __eq__(self, other):
        return self.packed == other.packed

    def __lt__(self, other):
        return self.packed < other.packed

    @classmethod
    def verify(self):
        intersection = set(self.FIELD_NAMES) & set(dir(self))
        if intersection:
            raise Exception(f'Cannot use the following '
                            f'field names: {intersection}')
        self.VERIFIED = True

    @property
    def packed(self):
        return self.pack()

    @property
    def unpacked(self):
        return self.unpack()

    @property
    def changed(self):
        return self.unpacked != self._original_values

    @property
    def expected_length(self):
        return struct.calcsize(self.FORMAT_STRING)

    def pack(self):
        return struct.pack(
                self.FORMAT_STRING, *[getattr(self, field) for field
                                      in self.FIELD_NAMES])

    def unpack(self, data=None):
        if data is None:
            result = OrderedDict()
            for field in self.FIELD_NAMES:
                result[field] = getattr(self, field)
            return result

        values = struct.unpack(self.FORMAT_STRING, data)
        if len(values) != len(self.FIELD_NAMES):
            raise Exception(f'Format string {self.FORMAT_STRING} does '
                            f'not map to field names {self.FIELD_NAMES}')
        return OrderedDict(zip(self.FIELD_NAMES, values))

    def set_values(self, values):
        for field, value in values.items():
            setattr(self, field, value)

    def restore(self):
        self.set_values(self._original_values)


class SnesGfxManager:
    @staticmethod
    def deinterleave_tile(tile, is_8color=False):
        rows = []
        old_bitcount = sum([bin(v).count('1') for v in tile])
        for i in range(8):
            if is_8color:
                interleaved = (tile[i*2], tile[(i*2)+1],
                               tile[i+16])
            else:
                interleaved = (tile[i*2], tile[(i*2)+1],
                               tile[(i*2)+16], tile[(i*2)+17])
            row = []
            for j in range(7, -1, -1):
                pixel = 0
                mask = 1 << j
                for k, v in enumerate(interleaved):
                    pixel |= bool(v & mask) << k

                if is_8color:
                    assert 0 <= pixel <= 7
                else:
                    assert 0 <= pixel <= 0xf
                row.append(pixel)

            assert len(row) == 8
            rows.append(row)

        assert len(rows) == 8
        #assert SnesGfxManager.interleave_tile(rows) == tile
        new_bitcount = sum([bin(v).count('1') for vs in rows for v in vs])
        assert old_bitcount == new_bitcount
        return rows

    @staticmethod
    def interleave_tile(old_tile, is_8color=False):
        if is_8color:
            new_tile = [0]*24
        else:
            new_tile = [0]*32

        old_bitcount = sum([bin(v).count('1')
                            for vs in old_tile for v in vs])
        assert len(old_tile) == 8
        for (j, old_row) in enumerate(old_tile):
            assert len(old_row) == 8
            for (i, pixel) in enumerate(old_row):
                i = 7 - i
                a = bool(pixel & 1)
                b = bool(pixel & 2)
                c = bool(pixel & 4)
                d = bool(pixel & 8)

                new_tile[(j*2)] |= (a << i)
                new_tile[(j*2)+1] |= (b << i)
                if is_8color:
                    new_tile[j+16] |= (c << i)
                else:
                    new_tile[(j*2)+16] |= (c << i)
                    new_tile[(j*2)+17] |= (d << i)

        new_bitcount = sum([bin(v).count('1') for v in new_tile])

        assert old_bitcount == new_bitcount
        assert SnesGfxManager.deinterleave_tile(new_tile,
                                                is_8color) == old_tile
        return bytes(new_tile)

    @staticmethod
    def data_to_tiles(old_data):
        data = old_data
        tiles = []
        while data:
            tile, data = data[:0x20], data[0x20:]
            tile = SnesGfxManager.deinterleave_tile(tile)
            tiles.append(tile)
        return tiles

    @staticmethod
    def tiles_to_data(tiles):
        data = b''
        for t in tiles:
            data += SnesGfxManager.interleave_tile(t)
        return data

    @staticmethod
    def tiles_to_pixels(tiles, width=1):
        # Width is in columns of tiles, NOT pixels
        height = len(tiles) // width
        rows = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(tiles.pop(0))
            rows.append(row)

        all_pixels = []
        for row in rows:
            for i in range(8):
                for tile in row:
                    tile_row = tile[i]
                    all_pixels.extend(tile_row)

        return all_pixels

    @staticmethod
    def pixels_to_tiles(pixels, width=8):
        assert len(pixels) % (8*8) == 0
        pixel_width = width * 8
        pixel_height = len(pixels) // pixel_width
        tile_width = width
        tile_height = pixel_height // 8
        num_tiles = len(pixels) // (8*8)

        tiles = []
        for tile_index in range(num_tiles):
            tile_row = tile_index // tile_width
            tile_column = tile_index % tile_width
            pixel_x = tile_column * 8
            pixel_y = tile_row * 8
            tile = []
            base_pixel_index = (pixel_y * pixel_width) + pixel_x
            for pixel_row in range(8):
                pixel_index = base_pixel_index + (pixel_row * pixel_width)
                row = pixels[pixel_index:pixel_index+8]
                assert len(row) == 8
                tile.append(row)
            tiles.append(tile)

        assert all(len(tile) == 8 for tile in tiles)
        return tiles

    @staticmethod
    def snes_palette_to_rgb(colors):
        multiplier = 0xff / 0x1f
        rgbs = []
        for c in colors:
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

    @staticmethod
    def rgb_palette_to_snes(rgbs):
        if isinstance(rgbs[0], int):
            assert len(rgbs) % 3 == 0
            rgbs = zip(rgbs[::3], rgbs[1::3], rgbs[2::3])
        palette = []
        factor = 0x1f / 0xff
        for r, g, b in rgbs:
            r = int(round(r * factor))
            g = int(round(g * factor))
            b = int(round(b * factor))
            assert 0 <= r <= 0x1f
            assert 0 <= g <= 0x1f
            assert 0 <= b <= 0x1f
            c = r | (g << 5) | (b << 10)
            assert 0 <= c <= 0xffff
            palette.append(c)
        return palette

    @staticmethod
    def pixels_to_image(pixels, width, height, palette):
        from PIL import Image
        assert len(pixels) >= width * height
        data = bytes(pixels)
        im = Image.frombytes(mode='P', size=(width, height), data=data)
        if isinstance(palette[0], int):
            palette = SnesGfxManager.snes_palette_to_rgb(palette)
        palette = [c for color in palette for c in color]
        im.putpalette(palette)
        im.info['transparency'] = 0
        return im

    @staticmethod
    def image_to_data(filename):
        from PIL import Image
        image = Image.open(filename)
        tile_width = ceil(image.width / 8)
        tile_height = ceil(image.height / 8)
        tiles = []
        for ty in range(tile_height):
            for tx in range(tile_width):
                tile = []
                for y in range(8):
                    row = []
                    for x in range(8):
                        p = image.getpixel(((tx*8)+x, (ty*8)+y))
                        row.append(p)
                    tile.append(row)
                tiles.append(tile)

        data = b''
        for t in tiles:
            data += SnesGfxManager.interleave_tile(t)
        return data
