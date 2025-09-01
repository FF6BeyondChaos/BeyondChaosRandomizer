from .cdrom_ecc_tables import EDC_crctable, L2sq

# unused CRC polynomials
#POLYNOMIAL = 0x04C11DB7  # standard
#POLYNOMIAL = 0x8001801b  # cd-rom xa mode 2??


def crc32(data):
    result = 0
    for value in data:
        result = EDC_crctable[(result ^ value) & 0xFF] ^ (result >> 8)
    return result


L2_RAW = 0x800
L2_P = 43*2*2
L2_Q = 26*2*2


def encode_L2_P(data):
    base_index = 0
    P_index = 4 + L2_RAW + 4 + 8
    target_size = P_index + L2_P
    data = list(data) + ([None] * (target_size-len(data)))
    assert len(data) == target_size
    for j in range(43):
        a, b = 0, 0
        index = base_index
        for i in range(19, 43):
            assert index < P_index-1
            a ^= L2sq[i][data[index]]
            b ^= L2sq[i][data[index+1]]
            index += (2*43)

        data[P_index] = a >> 8
        data[P_index + (43*2)] = a & 0xFF
        data[P_index + 1] = b >> 8
        data[P_index + (43*2) + 1] = b & 0xFF
        base_index += 2
        P_index += 2
    assert None not in data
    return data


def encode_L2_Q(data):
    base_index = 0
    Q_index = 4 + L2_RAW + 4 + 8 + L2_P
    MOD_INDEX = Q_index
    target_size = Q_index + L2_Q
    data = data + ([None] * (target_size-len(data)))
    assert len(data) == target_size
    counter = 0
    for j in range(26):
        a, b = 0, 0
        index = base_index
        for i in range(43):
            a ^= L2sq[i][data[index]]
            b ^= L2sq[i][data[index+1]]
            index += (2*44)
            index = index % MOD_INDEX
        data[Q_index] = a >> 8
        data[Q_index + (26*2)] = a & 0xFF
        data[Q_index + 1] = b >> 8
        data[Q_index + (26*2) + 1] = b & 0xFF
        base_index += (2*43)
        Q_index += 2
        counter += 1
    assert None not in data
    return data


EDC_ECC_CACHE = {}


def get_edc_ecc_cache_key(data):
    length = len(data)
    if length > 0x808:
        index = min(0x10, length - 0x808)
        return data[index:index+0x808]
    return data


def cache_edc_ecc(data, edc_ecc=None):
    key = get_edc_ecc_cache_key(data)
    if edc_ecc is None:
        assert len(data) == 0x930
        edc_ecc = data[0x10+len(key):]
        assert len(edc_ecc) == 0x118
    if isinstance(edc_ecc, bytes):
        edc = edc_ecc[:4]
        ecc = edc_ecc[4:]
    else:
        edc, ecc = edc_ecc
    assert len(edc) == 4
    assert len(ecc) == 0x114
    if key in EDC_ECC_CACHE and EDC_ECC_CACHE[key] != (edc, ecc):
        assert len(data) >= 0x818
        edc, ecc = get_edc_ecc(data[:0x818], use_cache=False)
    EDC_ECC_CACHE[key] = (edc, ecc)


def get_edc_ecc(data, use_cache=True):
    if use_cache:
        key = get_edc_ecc_cache_key(data)
        if key in EDC_ECC_CACHE:
            return EDC_ECC_CACHE[key]
        original_data = data
    assert len(data) == 0x818
    edc = crc32(data[0x10:0x818])
    for _ in range(4):
        data += bytes([edc & 0xFF])
        edc >>= 8
    assert len(data) == 0x81c
    assert len(data)-12 == 0x810
    temp = encode_L2_P(bytes([0, 0, 0, 0]) + data[0x10:])
    temp = encode_L2_Q(temp)
    data += bytes(temp[-0x114:])
    assert len(data) == 0x930
    edc, ecc = data[0x818:0x81c], data[0x81c:]
    if not use_cache:
        return edc, ecc
    EDC_ECC_CACHE[key] = (edc, ecc)
    return get_edc_ecc(original_data, use_cache=True)


def get_edc_form2(data):
    assert len(data) == 0x91C
    edc = crc32(data)
    for _ in range(4):
        data += bytes([edc & 0xFF])
        edc >>= 8
    assert len(data) == 0x920
    return data[-4:]
