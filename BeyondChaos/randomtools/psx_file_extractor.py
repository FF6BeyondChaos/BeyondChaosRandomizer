from math import ceil
from os import makedirs, path, stat, environ
from string import printable
from sys import argv
from .utils import cached_property
from .cdrom_ecc import get_edc_ecc


SYNC_PATTERN = bytes([0] + ([0xFF]*10) + [0])
fun = lambda x: int(x, 0x10)
DIRECTORY_PATTERN = bytes(map(fun,
    "00 00 00 00 8D 55 58 41 00 00 00 00 00 00".split()))
SANDBOX_PATH = '_temp'

DEBUG = environ.get('DEBUG')
DELTA_FILE = environ.get('DELTA')
IGNORE_BAD_DATA_TYPE = True
SEEN_BAD_DATA_TYPE = False


def file_from_sectors(imgname, initial_sector, tempname=None):
    if not path.exists(SANDBOX_PATH):
        makedirs(SANDBOX_PATH)
    if tempname is None:
        tempname = path.join(SANDBOX_PATH, '_temp.bin')

    f = open(imgname, "rb")
    g = open(tempname, "w+")
    g.close()
    g = open(tempname, "r+b")
    g.truncate()

    sector_index = initial_sector
    while True:
        pointer = sector_index * 0x930
        f.seek(pointer+0x12)
        submode = ord(f.read(1))
        f.seek(pointer+0x16)
        assert submode == ord(f.read(1))
        eof = submode & 0x80
        rt = submode & 0x40
        form = submode & 0x20
        trigger = submode & 0x10
        data = submode & 0x08
        audio = submode & 0x04
        video = submode & 0x02
        eor = submode & 0x01
        #assert not rt
        assert not trigger
        try:
            if not form:
                assert data and not (audio or video)
            else:
                assert (audio or video) and not data
        except AssertionError:
            global SEEN_BAD_DATA_TYPE
            if not IGNORE_BAD_DATA_TYPE:
                raise Exception(
                    'Bad submode data type at sector {0}.'.format(
                        sector_index))
            elif not SEEN_BAD_DATA_TYPE:
                print('WARNING: Bad submode data type at sector {0}.'.format(
                    sector_index))
                SEEN_BAD_DATA_TYPE = True
        f.seek(pointer+0x18)
        block = f.read(0x800)
        g.write(block)
        if eof and eor:
            break
        assert not (eof or eor)
        sector_index += 1

    f.close()
    return g


def write_data_to_sectors(imgname, initial_sector, datafile=None,
                          force_recalc=False):
    if datafile is None:
        datafile = path.join(SANDBOX_PATH, '_temp.bin')

    f = open(imgname, "r+b")
    g = open(datafile, "r+b")
    filesize = stat(datafile).st_size

    delta = None
    if DELTA_FILE is not None:
        delta = open(DELTA_FILE, 'a+')
    if not hasattr(write_data_to_sectors, '_done_delta'):
        write_data_to_sectors._done_delta = set()

    sector_index = initial_sector
    while True:
        pointer = sector_index * 0x930
        f.seek(pointer)
        block = g.read(0x800)
        if len(block) < 0x800:
            block += bytes(0x800-len(block))
        assert len(block) == 0x800

        if g.tell() >= filesize:
            assert g.tell() == filesize
            eof = 0x80
            eor = 0x01
        else:
            eof = 0
            eor = 0
        rt = 0
        form = 0
        trigger = 0
        data = 0x08
        audio = 0
        video = 0
        submode = (eof | rt | form | trigger | data | audio | video | eor)
        f.seek(pointer+0x12)
        old_submode = ord(f.read(1))
        if DEBUG and submode & 0x7E != old_submode & 0x7E:
            print("WARNING! Submode differs on sector %s: %x -> %x" % (
                sector_index, old_submode, submode))

        f.seek(pointer+0x18)
        old_block = f.read(0x800)
        if force_recalc or old_block != block:
            if DEBUG:
                print('Writing: {0} {1:0>8x}'.format(datafile, pointer))
            f.seek(pointer+0x12)
            f.write(bytes([submode]))
            f.seek(pointer+0x16)
            f.write(bytes([submode]))
            f.seek(pointer+0x18)
            f.write(block)
            f.seek(pointer)
            sector_data = f.read(0x818)
            edc, ecc = get_edc_ecc(sector_data)
            assert len(edc + ecc) == 0x118
            f.seek(pointer+0x818)
            f.write(edc + ecc)
            if delta is not None and ((pointer, pointer+0x930) not in
                                       write_data_to_sectors._done_delta):
                write_data_to_sectors._done_delta.add((pointer, pointer+0x930))
                delta.write('{0:0>8x} {1:0>8x}\n'.format(pointer,
                                                         pointer+0x930))

        if eof and eor:
            break
        sector_index += 1

    f.close()
    g.close()

    if delta is not None:
        delta.close()


class FileManager(object):
    def __init__(self, imgname, dirname=None, minute=0, second=2, sector=22):
        if dirname is None:
            dirname, _ = imgname.rsplit('.', 1)
            dirname = "%s.root" % dirname
        self.imgname = imgname
        self.dirname = dirname
        self.minute = minute
        self.second = second
        self.sector = sector
        self.files = read_directory(
            imgname, dirname, minute=minute, second=second, sector=sector)

    @property
    def flat_files(self):
        if hasattr(self, '_flat_files'):
            return self._flat_files

        files = list(self.files)
        while True:
            for f in list(files):
                if f.is_directory:
                    files.remove(f)
                    new_files = f.files
                    if new_files is not None:
                        files.extend(new_files)
                    break
            else:
                break

        self._flat_files = files
        return self.flat_files

    @property
    def flat_directories(self):
        files = list(self.files)
        directories = []
        while files:
            f = files.pop(0)
            if f.is_directory:
                new_files = f.files
                directories.append(f)
                if new_files is not None:
                    files.extend(new_files)
        return directories

    @property
    def report(self):
        s = ''
        for f in sorted(self.flat_files, key=lambda f2: (f2.initial_sector,
                                                         f2.pointer)):
            assert str(f).startswith(self.dirname)
            filepath = str(f)[len(self.dirname):]
            if filepath.endswith(';1'):
                filepath = filepath[:-2]
            s += '{0:0>8x} {1:0>4x} {2:0>7x} {3}\n'.format(f.target_sector * 0x930, f.pointer, f.size, filepath)
        return s.strip()

    def write_all(self):
        for f in self.flat_files:
            f.write_data()

    def get_file(self, name):
        if not hasattr(self, '_name_cache'):
            self._name_cache = {}

        if not name.endswith(';1'):
            name = name + ';1'

        if name.startswith(SANDBOX_PATH):
            name = name[len(SANDBOX_PATH):].lstrip(path.sep)

        if name in self._name_cache:
            return self._name_cache[name]

        filepath = path.join(self.dirname, name)
        for f in self.flat_files:
            if f.path == filepath:
                self._name_cache[name] = f
                return self.get_file(name)

    def export_file(self, name, filepath=None):
        if not name.endswith(';1'):
            name = name + ';1'
        if filepath is None:
            filepath = path.join(self.dirname, name)
        dirname = path.split(filepath)[0]
        if dirname and not path.exists(dirname):
            makedirs(dirname)
        f = self.get_file(name)
        if f is None:
            return None
        f.write_data(filepath)
        return filepath

    def calculate_free(self):
        max_size = stat(self.imgname).st_size
        max_sectors = max_size // 0x930

        used_sectors = set()
        for f in self.flat_files:
            num_sectors = ceil(f.num_sectors)
            num_sectors = max(num_sectors, 1)
            used_sectors |= set(range(f.target_sector,
                                      f.target_sector+num_sectors))

        last_sector = max_size // 0x930
        unused_sectors = set(range(max_sectors)) - used_sectors

        final_unused_sectors = []
        with open(self.imgname, 'rb') as f:
            previous_unused = -999
            for sector in sorted(unused_sectors):
                pointer = (sector * 0x930) + 0x18
                f.seek(pointer)
                block = f.read(0x800)
                if set(block) in ({0}, {0xff}):
                    if sector == previous_unused + 1:
                        final_unused_sectors[-1].append(sector)
                    else:
                        final_unused_sectors.append([sector])
                    previous_unused = sector

        self._free_sectors = final_unused_sectors

    def get_free(self, num_sectors):
        if not hasattr(self, '_free_sectors'):
            self.calculate_free()

        candidates = [
            sectors for sectors in sorted(self._free_sectors,
                                          key=lambda s: (len(s), s[0]))
            if len(sectors) >= num_sectors]
        chosen = candidates[0]
        self._free_sectors.remove(chosen)
        new_target_sector = chosen[0]
        used, unused = chosen[:num_sectors], chosen[num_sectors:]
        assert len(used) == num_sectors
        if unused:
            self._free_sectors.append(unused)

        return new_target_sector

    def realign_entry_pointers(self):
        if hasattr(self, 'SKIP_REALIGNMENT') and self.SKIP_REALIGNMENT:
            return

        all_files = self.flat_directories + self.flat_files
        initial_sectors = {f.initial_sector for f in all_files}
        for initial_sector in sorted(initial_sectors):
            files = [f for f in all_files
                     if f.initial_sector == initial_sector]
            files = sorted(files, key=lambda f: f.pointer
                                                if f.pointer is not None
                                                else 0xffffffff)
            pointer = 0
            highest_old_pointer = 0
            highest_pointer = 0
            for f in files:
                old_sector = pointer // 0x800
                new_sector = (pointer + f.size) // 0x800
                if new_sector == old_sector + 1:
                    pointer = new_sector * 0x800
                else:
                    assert new_sector == old_sector

                if f.pointer is not None:
                    highest_old_pointer = max(highest_old_pointer, f.pointer)

                f.pointer = pointer
                highest_pointer = max(highest_pointer, f.pointer)
                pointer += f.size
                f.update_file_entry()

            assert highest_old_pointer // 0x800 == highest_pointer // 0x800

    def create_new_file(self, name, template):
        template.initial_sector
        template.target_sector
        new_file = FileEntry(template.imgname, None, template.dirname,
                             template.initial_sector)
        new_file.clone_entry(template)
        head, tail = path.split(name)
        new_file.name = tail
        new_file._size = new_file.size
        self._flat_files.append(new_file)
        self.realign_entry_pointers()
        return new_file

    def import_file(self, name, filepath=None, new_target_sector=None,
                    force_recalc=False, verify=False, template=None):
        if not name.endswith(';1'):
            name = name + ';1'
        if filepath is None:
            filepath = path.join(self.dirname, name)
        if filepath.endswith(';1'):
            filepath = filepath[:-2]

        new_size = ceil(stat(filepath).st_size / 0x800)
        new_size = max(new_size, 1)
        old_file = self.get_file(name)

        if old_file is not None:
            to_import = old_file
            if new_target_sector is None:
                old_size = ceil(old_file.filesize / 0x800)
                if new_size <= old_size:
                    new_target_sector = old_file.target_sector
            else:
                verify = True
        else:
            assert template
            to_import = self.create_new_file(name, template=template)

        if new_target_sector is None:
            new_target_sector = self.get_free(new_size)
            verify = True
            force_recalc = True

        assert new_target_sector is not None
        verify = verify or DEBUG

        if verify:
            end_sector = new_target_sector + new_size

            self_path = path.join(self.dirname, name)
            for f in self.flat_files:
                if f.path == self_path:
                    continue
                try:
                    if f.start_sector <= new_target_sector:
                        assert f.end_sector <= new_target_sector
                    if f.start_sector >= new_target_sector:
                        assert end_sector <= f.start_sector
                except AssertionError:
                    raise Exception("Conflict with %s" % f)

        to_import.target_sector = new_target_sector
        to_import.filesize = new_size * 0x800
        if to_import.pointer is None:
            assert hasattr(self, 'SKIP_REALIGNMENT')
            assert self.SKIP_REALIGNMENT
        else:
            to_import.update_file_entry()
        write_data_to_sectors(
            to_import.imgname, to_import.target_sector, datafile=filepath,
            force_recalc=force_recalc)

        return to_import

    def finish(self):
        FileEntry.write_cached_files()


class FileEntryReadException(Exception):
    pass


class FileEntry:
    STRUCT = [
        ('_size', 1),
        ('num_ear', 1),
        ('target_sector', 4),
        ('target_sector_reverse', 4),
        ('filesize', 4),
        ('filesize_reverse', 4),
        ('year', 1),
        ('month', 1),
        ('day', 1),
        ('hour', 1),
        ('minute', 1),
        ('second', 1),
        ('tz_offset', 1),
        ('flags', 1),
        ('interleaved_unit_size', 1),
        ('interleaved_gap_size', 1),
        ('one', 2),
        ('unk3', 2),
        ('name_length', 1),
        ('name', None),
        ('pattern', 14),
        ]

    def __init__(self, imgname, pointer, dirname, initial_sector):
        self.imgname = imgname
        self.pointer = pointer
        self.dirname = dirname
        self.initial_sector = initial_sector

    def __repr__(self):
        return self.path

    @property
    def printable_name(self):
        #return any([c in printable for c in self.name])
        #print(printable, self.name)
        return all([c in printable for c in self.name])

    @property
    def start_sector(self):
        return self.target_sector

    @property
    def end_sector(self):
        return self.start_sector + self.num_sectors

    @property
    def num_sectors(self):
        num_sectors = self.filesize / 0x800
        if self.filesize > num_sectors * 0x800:
            num_sectors += 1
        return max(num_sectors, 1)

    @property
    def hidden(self):
        return self.flags & 1

    @property
    def is_directory(self):
        return self.flags & 0x2

    @cached_property
    def path(self):
        return path.join(self.dirname, self.name)

    @classmethod
    def get_cached_file_from_sectors(self, imgname, initial_sector):
        if not hasattr(FileEntry, '_file_cache'):
            FileEntry._file_cache = {}

        key = (imgname, initial_sector)
        if key in FileEntry._file_cache:
            return FileEntry._file_cache[key]

        tempname = '_temp.{0:x}.bin'.format(initial_sector)
        tempname = path.join(SANDBOX_PATH, tempname)
        f = file_from_sectors(imgname, initial_sector, tempname)
        FileEntry._file_cache[key] = f

        return FileEntry.get_cached_file_from_sectors(imgname, initial_sector)

    @classmethod
    def write_cached_files(self):
        if not hasattr(FileEntry, '_file_cache'):
            return

        for (imgname, initial_sector), f in sorted(
                FileEntry._file_cache.items()):
            fname = f.name
            f.close()
            write_data_to_sectors(imgname, initial_sector, datafile=fname)

    @property
    def size(self):
        size = 0
        for (attr, length) in self.STRUCT:
            if length is not None:
                size += length
            else:
                assert attr == 'name'
                size += len(self.name)
                if not len(self.name) % 2:
                    size += 1
        return size

    def validate(self):
        assert self.num_ear == 0
        assert not self.size % 2
        assert not self.flags & 0xFC
        assert not self.interleaved_unit_size or self.interleaved_gap_size
        assert self.one == 1
        if self.is_directory:
            assert self.pattern == DIRECTORY_PATTERN
        else:
            assert self.name[-2:] == ";1"
        if hasattr(self, '_size'):
            assert self.size == self._size

    def clone_entry(self, other):
        for attr, length in self.STRUCT:
            setattr(self, attr, getattr(other, attr))

    def update_file_entry(self):
        self.validate()

        self._size = self.size

        f = self.get_cached_file_from_sectors(self.imgname,
                                              self.initial_sector)

        f.seek(self.pointer)
        for (attr, length) in self.STRUCT:
            if attr == 'target_sector_reverse':
                f.write(self.target_sector.to_bytes(length=4, byteorder='big'))
            elif attr == 'filesize_reverse':
                f.write(self.filesize.to_bytes(length=4, byteorder='big'))
            elif attr == 'name_length':
                name_length = len(self.name)
                f.write(bytes([name_length]))
                self.name_length = name_length
            elif attr == 'name':
                f.write(self.name.encode('ascii'))
                if not self.name_length % 2:
                    f.write(b'\x00')
            elif attr == 'pattern':
                f.write(self.pattern)
            else:
                value = getattr(self, attr)
                f.write(value.to_bytes(length=length, byteorder='little'))

        assert f.tell() == self.pointer + self.size

    def read_file_entry(self):
        self.old_data = {}

        f = self.get_cached_file_from_sectors(self.imgname,
                                              self.initial_sector)

        f.seek(self.pointer)
        for (attr, length) in self.STRUCT:
            if length == None and attr == 'name':
                length = self.name_length
                self.name = f.read(length).decode('ascii')
                if not self.name_length % 2:
                    p = f.read(1)
                    assert p == b'\x00'

            elif attr == 'pattern':
                self.pattern = f.read(length)

            elif attr == '_size':
                peek = f.read(1)
                if len(peek) == 0:
                    raise EOFError
                self._size = ord(peek)
                if self._size == 0:
                    raise FileEntryReadException

            else:
                value = int.from_bytes(f.read(length), byteorder='little')
                setattr(self, attr, value)

            self.old_data[attr] = getattr(self, attr)

        self.validate()
        assert f.tell() == self.pointer + self.size

    def write_data(self, filepath=None):
        if self.is_directory or not self.printable_name or not self.filesize:
            return
        if filepath is None:
            filepath = path.join(self.dirname, self.name)
            assert filepath.endswith(';1')
            filepath = filepath[:-2]
            if not path.exists(self.dirname):
                makedirs(self.dirname)

        f = file_from_sectors(self.imgname, self.target_sector, filepath)
        f.close()

        written_size = stat(filepath).st_size
        assert not written_size % 0x800
        start_byte = self.target_sector * 0x800
        interval = (start_byte, start_byte + written_size)
        start, finish = interval
        if not hasattr(FileEntry, 'WRITTEN_INTERVALS'):
            FileEntry.WRITTEN_INTERVALS = {}

        assert filepath not in self.WRITTEN_INTERVALS
        errmsg = 'WARNING: {0} overlaps {1} at {2:x}. Truncating {1}.'
        for donepath in sorted(self.WRITTEN_INTERVALS):
            donestart, donefinish = self.WRITTEN_INTERVALS[donepath]
            if start <= donestart < finish:
                # truncate this file
                newfinish = donestart
                newsize = newfinish - start
                print(errmsg.format(donepath, filepath, newsize))
                with open(filepath, 'r+b') as f:
                    f.truncate(newsize)
                finish = newfinish
            if start < donefinish <= finish:
                # truncate the other file
                newfinish = start
                newsize = newfinish - donestart
                print(errmsg.format(filepath, donepath, newsize))
                with open(donepath, 'r+b') as f:
                    f.truncate(newsize)
                assert newfinish >= donestart
                self.WRITTEN_INTERVALS[donepath] = (donestart, newfinish)
        assert finish >= start
        self.WRITTEN_INTERVALS[filepath] = (start, finish)


def read_directory(imgname, dirname, sector_index=None,
                   minute=None, second=None, sector=None):
    f = open(imgname, 'r+b')
    if sector_index is None:
        sector_index = (minute * 60 * 75) + ((second-2) * 75) + sector
    pointer = sector_index * 0x930
    f.seek(pointer)
    temp = f.read(12)
    #print(hex(pointer), temp, SYNC_PATTERN)
    assert temp == SYNC_PATTERN
    f.seek(pointer+15)
    mode = ord(f.read(1))
    assert mode == 2

    f.close()

    pointer = 0
    fes = []
    while True:
        try:
            fe = FileEntry(imgname, pointer, dirname, sector_index)
            fe.read_file_entry()
            pointer = fe.pointer + fe.size
            fes.append(fe)
        except FileEntryReadException:
            pointer = ((pointer // 0x800) + 1) * 0x800
        except EOFError:
            break

    for fe in fes:
        fe.files = None
        if (fe.is_directory and fe.printable_name
                and sector_index != fe.target_sector):
            subfes = read_directory(
                imgname, path.join(dirname, fe.name),
                sector_index=fe.target_sector)
            fe.files = subfes

    return fes


if __name__ == "__main__":
    from subprocess import call

    filename = argv[1]
    if len(argv) > 2:
        sector_address = argv[2]
        minute, second, sector = sector_address.split(",")
    else:
        minute, second, sector = 0, 2, 22
    minute, second, sector = map(int, (minute, second, sector))
    dirname, _ = filename.rsplit('.', 1)
    dirname = "%s.root" % dirname

    outfile = "modified.%s" % filename
    call(["cp", "-n", filename, outfile])
    filename = None

    f = FileManager(outfile, dirname, minute, second, sector)
    print(f.report)
    #f.write_all()
