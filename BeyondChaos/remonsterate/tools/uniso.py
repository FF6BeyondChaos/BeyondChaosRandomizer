from cdrom_ecc import get_edc_ecc


def remove_sector_metadata(sourcefile, outfile):
    # playstation discs are CD-ROM XA mode 2 (form 1 for data)
    # form 2 sectors also exist on many discs, so this is a huge hack,
    # but I am treating every sector as form 1 for now.
    print("REMOVING SECTOR METADATA")
    g = open(outfile, "w+")
    g.close()
    f = open(sourcefile, 'r+b')
    g = open(outfile, 'r+b')
    g.truncate()
    while True:
        header = f.read(0x18)
        data = f.read(0x800)
        if len(data) < 0x800:
            break
        #g.write(header)
        g.write(data)
        #g.write("".join([chr(0) for _ in xrange(0x118)]))
        checkdata = f.read(4)
        '''
        checksum = crc32(data)
        if checksum < 0:
            checksum += (1 << 32)
        '''
        f.seek(0x114, 1)
    f.close()
    g.close()


def inject_logical_sectors(sourcefile, outfile, debug=False):
    print("REINJECTING LOGICAL SECTORS TO ORIGINAL ISO")
    f = open(sourcefile, 'r+b')
    g = open(outfile, 'r+b')
    minpointer, maxpointer = None, None
    num_changed_sectors = 0
    while True:
        pointer_source = f.tell()
        pointer_dest = g.tell()
        if debug:
            assert not pointer_source % 0x800
            assert not pointer_dest % 0x930
        data_source = f.read(0x800)
        header = g.read(0x10)
        subheader = g.read(0x8)
        data_dest = g.read(0x800)
        error_detect = g.read(4)
        error_correct = g.read(0x114)
        if (len(data_source) == len(header) == len(data_dest)
                == len(error_detect) == len(error_correct) == 0):
            break
        if not all([len(data_source) == 0x800,
                    len(header) == 0x10,
                    len(subheader) == 0x8,
                    len(data_dest) == 0x800,
                    len(error_detect) == 0x4,
                    len(error_correct) == 0x114,
                    ]):
            raise Exception("Data alignment mismatch.")
        if data_source == data_dest:
            continue
        else:
            is_form2 = ord(subheader[2]) & 0x20
            if is_form2:
                print("WARNING: "
                      "A form 2 sector was modified. This software does not "
                      "accurately read from and write to form 2 sectors, "
                      "which are typically used for audio and video data.")
            if debug:
                edc, ecc = get_edc_ecc(header + subheader + data_dest)
                assert edc == error_detect
                assert ecc == error_correct
            if minpointer is None:
                minpointer = pointer_dest
            maxpointer = max(pointer_dest + 0x800, maxpointer)
            num_changed_sectors += 1
            # gotta do this dumb file seeking thing for windows
            g.seek(pointer_dest)
            g.write(header+subheader)
            g.seek(pointer_dest + len(header+subheader))
            g.write(data_source)
            g.seek(pointer_dest + len(header+subheader) + len(data_source))
            edc, ecc = get_edc_ecc(header + subheader + data_source)
            assert len(edc + ecc) == 0x118
            g.write(edc + ecc)
            g.seek(pointer_dest + len(header+subheader) +
                   len(data_source) + len(edc + ecc))

    if minpointer is not None and maxpointer is not None:
        print("%s SECTORS CHANGED IN RANGE %x-%x" % (
            num_changed_sectors, minpointer, maxpointer))
    else:
        print("NO CHANGES MADE TO ISO")


if __name__ == "__main__":
    from sys import argv
    SOURCE = argv[1]
    TEMPFILE = "unheadered.img"
    remove_sector_metadata(SOURCE, TEMPFILE)
    #inject_logical_sectors(TEMPFILE, SOURCE)
    #remove(TEMPFILE)
