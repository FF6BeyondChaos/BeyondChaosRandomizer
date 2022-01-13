from math import ceil
from os import makedirs, path, stat, environ
from string import printable
from sys import argv
from .utils import read_multi, write_multi
from .cdrom_ecc import get_edc_ecc


SYNC_PATTERN = bytes([0] + ([0xFF]*10) + [0])
fun = lambda x: int(x, 0x10)
DIRECTORY_PATTERN = bytes(map(fun,
    "00 00 00 00 8D 55 58 41 00 00 00 00 00 00".split()))
SANDBOX_PATH = '_temp'

DEBUG = environ.get('DEBUG')
DELTA_FILE = environ.get('DELTA')


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
        if not form:
            assert data and not (audio or video)
        else:
            assert (audio or video) and not data
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
        if submode & 0x7E != old_submode & 0x7E:
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
                if new_files is not None:
                    directories.append(f)
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
            s += '{0:0>8x} {1:0>4x} {2}\n'.format(f.target_sector * 0x930, f.pointer, filepath)
        return s.strip()

    def write_all(self):
        for f in self.flat_files:
            f.write_data()

    def get_file(self, name):
        filepath = path.join(self.dirname, name)
        for f in self.flat_files:
            if f.__repr__() == filepath:
                return f

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

    def import_file(self, name, filepath=None, new_target_sector=None,
                    force_recalc=False, verify=False):
        if not name.endswith(';1'):
            name = name + ';1'
        if filepath is None:
            filepath = path.join(self.dirname, name)
        old_file = self.get_file(name)

        size_bytes = stat(filepath).st_size

        verify = verify or DEBUG
        if (new_target_sector is not None
                or ceil(size_bytes / 0x800) > ceil(old_file.filesize / 0x800)):
            verify = True

        if new_target_sector is None:
            new_target_sector = old_file.target_sector

        if verify:
            size_sectors = size_bytes / 0x800
            if size_bytes > size_sectors * 0x800:
                size_sectors += 1
            size_sectors = max(size_sectors, 1)
            end_sector = new_target_sector + size_sectors

            self_path = path.join(self.dirname, name)
            for f in self.flat_files:
                if f.__repr__() == self_path:
                    continue
                try:
                    if f.start_sector <= new_target_sector:
                        assert f.end_sector <= new_target_sector
                    if f.start_sector >= new_target_sector:
                        assert end_sector <= f.start_sector
                except AssertionError:
                    raise Exception("Conflict with %s" % f)

        old_file.target_sector = new_target_sector
        old_file.filesize = size_bytes
        old_file.update_file_entry()
        write_data_to_sectors(
            old_file.imgname, old_file.target_sector, datafile=filepath,
            force_recalc=force_recalc)

    def finish(self):
        FileEntry.write_cached_files()


class FileEntryReadException(Exception):
    pass


class FileEntry:
    def __init__(self, imgname, pointer, dirname, initial_sector):
        self.imgname = imgname
        self.pointer = pointer
        self.dirname = dirname
        self.initial_sector = initial_sector
        self.read_data()

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

    def update_file_entry(self):
        f = self.get_cached_file_from_sectors(self.imgname,
                                              self.initial_sector)

        f.seek(self.pointer+2)
        write_multi(f, self.target_sector, length=4)
        f.seek(self.pointer+6)
        write_multi(f, self.target_sector, length=4, reverse=False)
        f.seek(self.pointer+10)
        write_multi(f, self.filesize, length=4)
        f.seek(self.pointer+14)
        write_multi(f, self.filesize, length=4, reverse=False)

    def read_data(self):
        f = self.get_cached_file_from_sectors(self.imgname,
                                              self.initial_sector)
        f.seek(self.pointer)
        peek = f.read(1)
        if not peek:
            raise EOFError
        self.size = ord(peek)
        if self.size == 0:
            raise FileEntryReadException
        self.num_ear = ord(f.read(1))
        assert self.num_ear == 0
        assert not self.size % 2
        self.target_sector = read_multi(f, length=4)
        f.seek(4, 1)
        self.filesize = read_multi(f, length=4)
        f.seek(4, 1)
        self.year = ord(f.read(1)) + 1900
        self.month = ord(f.read(1))
        self.day = ord(f.read(1))
        self.hour = ord(f.read(1))
        self.minute = ord(f.read(1))
        self.second = ord(f.read(1))
        self.tz_offset = ord(f.read(1)) / 4.0
        self.flags = ord(f.read(1))
        assert not self.flags & 0xFC
        self.hidden = self.flags & 1
        self.is_directory = self.flags & 0x2
        self.interleaved_unit_size = ord(f.read(1))
        self.interleaved_gap_size = ord(f.read(1))
        assert not self.interleaved_unit_size or self.interleaved_gap_size
        self.one = read_multi(f, length=2)
        assert self.one == 1
        f.seek(2, 1)
        self.name_length = ord(f.read(1))
        self.name = f.read(self.name_length).decode('ascii')
        self.path = path.join(self.dirname, self.name)
        if not self.name_length % 2:
            p = ord(f.read(1))
            assert p == 0
        self.pattern = f.read(14)
        if self.is_directory:
            assert self.pattern == DIRECTORY_PATTERN
        else:
            assert self.name[-2:] == ";1"
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

        try:
            f = file_from_sectors(self.imgname, self.target_sector, filepath)
            f.close()
        except AssertionError:
            print("EXCEPTION: %s" % filepath)
            return


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
            pointer = fe.pointer + fe.size
            fes.append(fe)
        except FileEntryReadException:
            pointer = ((pointer // 0x800) + 1) * 0x800
        except EOFError:
            break

    for fe in fes:
        fe.files = None
        if not fe.printable_name:
            continue
        if fe.is_directory and fe.name and sector_index != fe.target_sector:
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
