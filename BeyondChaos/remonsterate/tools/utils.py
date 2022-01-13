import random
from collections import defaultdict
from hashlib import md5


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


def read_lines_nocomment(filename):
    lines = []
    with open(filename) as f:
        for line in f:
            if '#' in line:
                line, _ = line.split('#', 1)
            line = line.strip()
            if not line:
                continue
            lines.append(line)
    return lines


def md5hash(filename, blocksize=65536):
    m = md5()
    with open(filename, 'rb') as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def int2bytes(value, length=2, reverse=True):
    # reverse=True means high-order byte first
    bs = []
    while value:
        bs.append(value & 255)
        value = value >> 8

    while len(bs) < length:
        bs.append(0)

    if not reverse:
        bs = reversed(bs)

    return bs[:length]


def read_multi(f, length=2, reverse=True):
    vals = list(map(int, f.read(length)))
    if reverse:
        vals = list(reversed(vals))
    value = 0
    for val in vals:
        value = value << 8
        value = value | val
    return value


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


utilrandom = random.Random()
utran = utilrandom
random = utilrandom


def line_wrap(things, width=16):
    newthings = []
    while things:
        newthings.append(things[:width])
        things = things[width:]
    return newthings


def hexstring(value):
    if type(value) is str:
        value = "".join(["{0:0>2}".format("%x" % ord(c)) for c in value])
    elif type(value) is int:
        value = "{0:0>2}".format("%x" % value)
    elif type(value) is list:
        value = " ".join([hexstring(v) for v in value])
    return value


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


def rewrite_snes_title(text, filename, version, lorom=False):
    f = open(filename, 'r+b')
    while len(text) < 20:
        text += ' '
    if len(text) > 20:
        text = text[:19] + "?"
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
