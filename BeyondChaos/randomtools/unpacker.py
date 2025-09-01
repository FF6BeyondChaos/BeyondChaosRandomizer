import json
from collections import OrderedDict, defaultdict
from copy import copy
from io import BytesIO
from os import SEEK_END
from sys import argv

from randomtools.utils import MaskStruct
from randomtools.utils import fake_yaml as yaml
from randomtools.utils import search_nested_key


def hexify(s):
    if isinstance(s, int):
        return f'{s:0>2x}'
    return ' '.join([f'{w:0>2x}' for w in s])


class BytesEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return hexify(o)
        else:
            return super().default(o)


class BasicPointer:
    def __init__(self, index, pointer, pointer_length, byteorder):
        self.index = index
        if isinstance(pointer, bytes):
            pointer = int.from_bytes(pointer, byteorder=byteorder)
        self.pointer = pointer
        self.pointer_length = pointer_length
        self.byteorder = byteorder

    def __repr__(self):
        return f'{self.index:0>3}:@{self.pointer:x}'

    def __hash__(self):
        return self._sort_key.__hash__()

    def __int__(self):
        return self.pointer

    def __format__(self, format_spec):
        return format(self.pointer, format_spec)

    def __add__(self, other):
        if isinstance(other, int):
            return self.pointer + other
        if hasattr(other, 'pointer'):
            return self.pointer + other.pointer
        raise TypeError

    def __sub__(self, other):
        if isinstance(other, int):
            return self.pointer - other
        if hasattr(other, 'pointer'):
            return self.pointer - other.pointer
        raise TypeError

    def __eq__(self, other):
        if not isinstance(other, BasicPointer):
            return False
        return self._sort_key == other._sort_key

    def __lt__(self, other):
        return self._sort_key < other._sort_key

    @property
    def _sort_key(self):
        return (self.pointer, self.index)

    @property
    def packed(self):
        return self.pointer.to_bytes(length=self.pointer_length,
                                     byteorder=self.byteorder)


class MaskStructPointer(BasicPointer):
    def __init__(self, index, original):
        self.index = index
        self.original = original
        self.pointer_length = len(original.packed)
        self.byteorder = None
        for attr in self.original._original_values:
            assert not hasattr(self, attr)
            setattr(self, attr, getattr(self.original, attr))

    def update(self):
        for attr in self.original._original_values:
            setattr(self.original, attr, getattr(self, attr))

    @property
    def packed(self):
        self.update()
        return self.original.packed


class Unpacker:
    class PointerTable:
        def __init__(self, section):
            self.section = section

        def __len__(self):
            return self.num_pointers * self.pointer_length

        @property
        def config(self):
            return self.section.config

        @property
        def num_pointers(self):
            num_pointers = self.section.get_setting('num_pointers')
            if isinstance(num_pointers, str):
                num_pointers = self.section.evaluate(num_pointers)
            if num_pointers is not None:
                assert isinstance(num_pointers, int)
                return num_pointers
            assert isinstance(self.section.unpacked, list)
            return len(self.section.unpacked)

        @property
        def pointer_length(self):
            return self.section.get_setting('pointer_length')

        def get_pointer_addresses(self):
            pointers = []
            addresses = []
            for x in self.pointers:
                if x is None:
                    pointers.append(None)
                    addresses.append(None)
                    continue
                if isinstance(x, tuple):
                    p, a = x
                else:
                    p = None
                    a = x
                pointers.append(p)
                addresses.append(a)
            return pointers, addresses

        @property
        def bytecode(self):
            bytecode = b''
            byteorder = self.section.get_setting('byteorder')
            relative_to = self.section.get_setting('relative_to')
            pointer_order = self.section.get_setting('pointer_order')
            offset = 0
            if isinstance(relative_to, str):
                assert relative_to.startswith('@')
                label, offset = self.section.split_address_label(relative_to)
                relative_to = self.section.get_address(relative_to)
            if relative_to is None:
                return None
            relative_to += offset

            pointers, addresses = self.get_pointer_addresses()
            previous_value = None
            for pointer, address in zip(pointers, addresses):
                slabel, label, offset = None, None, None
                if isinstance(address, str):
                    assert address.startswith('@')
                    assert '@' not in address[1:]
                    slabel, offset = self.section.split_address_label(address)
                    assert slabel.startswith('@')
                    assert not slabel.startswith('@@')
                    label = slabel[1:]
                    if self.section.tree[label].unpacked is None:
                        value = 0
                    else:
                        value = self.section.get_address(slabel)
                        if value is not None:
                            value = value + offset - relative_to
                        else:
                            return None
                elif address is None:
                    value = 0
                assert value >= 0
                if hasattr(pointer, 'packed'):
                    pointer.pointer = value
                    bytecode += pointer.packed
                else:
                    bytecode += value.to_bytes(length=self.pointer_length,
                                               byteorder=byteorder)
                if pointer_order == 'sorted' and previous_value is not None \
                        and 0 < value < previous_value:
                    raise Exception(f'Pointer out of order: {pointer}')
                if address is not None:
                    previous_value = value
            return bytecode

    INHERITABLE_SETTINGS = {
        'byteorder', 'pointer_length', 'pointer_order',
        }

    def __init__(self, config, label=None, parent=None, superformat=None):
        if label is None:
            assert parent is None
            label = '_root'
        else:
            assert not label.startswith('_')
        assert label is not None
        assert not label.startswith('@')
        self.label = label
        self.config = config
        self._config_values = {}
        self.children = []
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)
            assert superformat is None
        self._superformat = superformat
        self._addresses = None
        self.sections = None
        if self.parent is None:
            self._tree = {}
            self._addresses = defaultdict(set)
            self._address_cache = {}
            self._nulled_addresses = set()
            self._alignments = {}
            self.sections = {}
        elif self.is_recursive:
            self.sections = {}

        if self.label in self.tree:
            raise Exception(f'Duplicate section label: {self.label}')
        self.index = len(self.tree)
        assert self.index not in {s.index for s in self.tree.values()}
        self.tree[self.label] = self

        if 'start' in self.config:
            self.add_address(f'@{label}', self.config['start'])

        if 'finish' in self.config:
            self.add_address(f'@@{label}', self.config['finish'])

        if 'align' in self.config:
            self.set_alignment(f'@{label}', self.config['align'])

        if 'total_length' in self.config:
            total_length = self.config['total_length']
            if isinstance(total_length, int):
                self.add_address(f'@@{label}', f'@{label},{total_length}')

        if self.is_recursive and self.sections is not None:
            for key in self.config:
                if not isinstance(self.config[key], dict):
                    continue
                self.sections[key] = Unpacker(self.config[key], key,
                                              parent=self)
                assert self.children[-1] == self.sections[key]

        if self.is_pointers:
            self.check_pointer_dimensions()

        if self.is_regular_list or self.is_pointed_list:
            self.check_list_dimensions()

        if not self.parent:
            self.preclean()

    @property
    def is_recursive(self):
        if 'data_type' in self.config:
            return self.config['data_type'] == 'recursive'
        return self.parent is None

    @property
    def is_pointers(self):
        return 'data_type' in self.config and \
                self.config['data_type'] == 'pointers'

    @property
    def is_pointed_list(self):
        return 'data_type' in self.config and \
                self.config['data_type'] == 'pointed_list'

    @property
    def is_regular_list(self):
        return 'data_type' in self.config and \
                self.config['data_type'] == 'regular_list'

    @property
    def is_mask_struct(self):
        return 'data_type' in self.config and \
                self.config['data_type'] == 'mask_struct'

    @property
    def root(self):
        if hasattr(self, '_root'):
            return self._root
        if not self.parent:
            self._root = self
            return self.root
        self._root = self.parent.root
        return self.root

    @property
    def tree(self):
        return self.root._tree

    @property
    def superformat(self):
        return self.root._superformat

    @property
    def descendents(self):
        descendents = set(self.children)
        for c in self.children:
            descendents |= c.descendents
        return descendents

    @property
    def addresses(self):
        return self.root._addresses

    @property
    def address_cache(self):
        return self.root._address_cache

    @property
    def nulled_addresses(self):
        return self.root._nulled_addresses

    @property
    def alignments(self):
        return self.root._alignments

    @property
    def start(self):
        return self.get_address(self.slabel)

    @property
    def finish(self):
        return self.get_address(self.flabel)

    @property
    def starts(self):
        addresses = self.addresses[self.slabel]
        if addresses:
            return addresses

    @property
    def finishes(self):
        addresses = self.addresses[self.flabel]
        if addresses:
            return addresses

    @property
    def slabel(self):
        return f'@{self.label}'

    @property
    def flabel(self):
        return f'@@{self.label}'

    def get_setting(self, attribute, caller=None):
        if caller is None:
            caller = self
        if caller is self and attribute in self._config_values:
            return self._config_values[attribute]
        result = None
        if attribute in self.config:
            result = self.config[attribute]
        elif self.parent is not None and \
                attribute in self.INHERITABLE_SETTINGS:
            result = self.parent.get_setting(attribute, caller=caller)
        if isinstance(result, str) and result.startswith('@'):
            label, offset = self.split_address_label(result)
            test = self.get_address(label)
            if test is not None:
                result = test + offset
        return result

    def set_value(self, attribute, value):
        self._config_values[attribute] = value

    def evaluate(self, expression):
        if isinstance(expression, int) or expression is None:
            return expression
        if not expression.startswith('{'):
            raise NotImplementedError
        assert expression.endswith('}')
        expression = expression[1:-1]
        if '.' in expression:
            label, setting = expression.split('.')
        else:
            label = expression
            setting = None

        section = self.tree[label]
        if setting is not None:
            value = section.get_setting(setting)
            return value

        assert section.config['data_type'] == 'blob'
        if hasattr(section, 'packed'):
            section.packed.seek(0)
            blob = section.packed.read()
        elif hasattr(section, 'unpacked'):
            blob = section.unpacked
        else:
            return
        value = int.from_bytes(blob,
                               byteorder=section.get_setting('byteorder'))
        return value

    def split_address_label(self, label):
        try:
            label, offset = label.split(',')
            if offset.startswith('0x'):
                offset = int(offset, 0x10)
            else:
                offset = int(offset)
        except ValueError:
            offset = 0
        return label, offset

    def add_address(self, label, address):
        if address not in self.addresses[label]:
            assert address is not None
            self.addresses[label].add(address)
            if isinstance(address, int):
                if label in self.alignments:
                    m, r = self.alignments[label]
                    assert address % m == r
                assert len({a for a in self.addresses[label]
                            if isinstance(a, int)}) == 1
                self.cache_address(label, address)
                for other in self.addresses[label]:
                    if isinstance(other, int):
                        continue
                    olabel, ooffset = self.split_address_label(other)
                    self.add_address(olabel, address-ooffset)
            else:
                pool = {label, address} | \
                        self.addresses[label] | self.addresses[address]
                numbers = {a for a in pool if isinstance(a, int)}
                pool -= numbers
                assert len(numbers) <= 1
                number = numbers.pop() if numbers else None
                for l in pool:
                    self.addresses[l] |= pool
                    if number is not None:
                        self.cache_address(l, number)
                if ',' in address:
                    alabel, aoffset = self.split_address_label(address)
                    self.add_address(alabel, f'{label},{-aoffset}')
            return True
        return False

    def cache_address(self, label, address):
        assert isinstance(address, int)
        if label in self.address_cache:
            assert self.address_cache[label] == address
        else:
            self.address_cache[label] = address

    def get_address(self, label):
        #assert ',' not in label
        try:
            return self.address_cache[label]
        except KeyError:
            return None

    def set_alignment(self, label, alignment):
        if isinstance(alignment, tuple):
            self.alignments[label] = alignment
        else:
            self.alignments[label] = alignment, 0

    def check_pointer_dimensions(self):
        num_pointers = self.get_setting('num_pointers')
        pointers = self.get_setting('pointers')
        if pointers and num_pointers is None:
            num_pointers = len(pointers)
            self.set_value('num_pointers', num_pointers)
        if pointers and num_pointers is not None:
            assert num_pointers == len(pointers)
        pointer_length = self.get_setting('pointer_length')
        if None not in (num_pointers, pointer_length, self.start):
            key = self.flabel
            finish = self.start + (self.evaluate(num_pointers) *
                                   pointer_length)
            if finish not in self.addresses[key]:
                self.add_address(key, finish)

    def check_list_dimensions(self):
        num_items = self.get_setting('num_items')
        item_size = self.get_setting('item_size')

        if self.start is not None and self.finish is not None and \
                (num_items, item_size).count(None) == 1:
            total_length = self.finish - self.start
            if num_items is None:
                self.set_value('num_items', total_length // item_size)
            if item_size is None:
                self.set_value('item_size', total_length // num_items)
            num_items = self.get_setting('num_items')
            item_size = self.get_setting('item_size')

        num_items = self.evaluate(num_items)
        item_size = self.evaluate(item_size)
        if None not in (num_items, item_size, self.start):
            total_length = num_items * item_size
            key = self.flabel
            finish = self.start + total_length
            if finish not in self.addresses[key]:
                self.add_address(key, finish)

    def guess_total_length(self):
        if 'total_length' not in self.config:
            return

        total_length = self.config['total_length']
        if isinstance(total_length, int):
            return
        assert total_length.endswith('?')
        total_length = int(total_length.rstrip('?'))

        if self.start is self.finish is None:
            return

        if self.start is not None:
            self.add_address(self.flabel, f'{self.slabel},{total_length}')
        if self.finish is not None:
            if self.finish >= total_length:
                self.add_address(self.slabel, f'{self.flabel},-{total_length}')
            else:
                self.add_address(self.slabel, self.flabel)

    def guess_start(self):
        if self.start is not None:
            return

        self.guess_total_length()

        for label in self.addresses[self.slabel]:
            label, offset = self.split_address_label(label)
            address = self.get_address(label)
            if address is not None:
                self.add_address(self.slabel, address + offset)
                return self.guess_start()

        if self.parent is None:
            self.add_address(self.slabel, 0)
            return

        if self.get_setting('start') is self.get_setting('finish') is None \
                and self.parent.start is not None \
                and len(self.parent.children) >= 1 \
                and self.parent.children[0] is self:
            self.add_address(self.slabel, self.parent.start)

    def guess_finish(self, override=False):
        if self.finish is not None:
            return

        self.guess_total_length()

        for label in self.addresses[self.flabel]:
            label, offset = self.split_address_label(label)
            address = self.get_address(label)
            if address is not None:
                self.add_address(self.flabel, address + offset)
                return self.guess_finish()

        if self.parent is None:
            self.add_address(self.flabel, '!eof')

        if '!eof' in self.addresses[self.flabel]:
            length = self.root.get_packed_length()
            if length is not None:
                self.add_address(self.flabel, length)

        if 'finish' in self.config and not override:
            return

        if self.is_regular_list or self.is_pointed_list:
            self.check_list_dimensions()

        if self.is_pointers:
            self.check_pointer_dimensions()

        if self.parent is None:
            return

        # double check
        if self.finish is not None:
            return

        self.parent.guess_finish()
        self.guess_sibling_finish()

    def guess_sibling_finish(self):
        siblings = self.parent.children
        self_index = siblings.index(self)
        if len(siblings) > self_index + 1:
            if self.start is None:
                return
            sibling = siblings[self_index + 1]
            sibling.guess_finish()
            sibling.guess_start()
            self.add_address(self.flabel, sibling.slabel)
        else:
            assert self is self.parent.children[-1]
            address = self.parent.finish
            if address is not None:
                self.add_address(self.flabel, address)

    def check_null_pointer(self, pointer):
        if hasattr(pointer, 'pointer'):
            pointer = pointer.pointer
        if isinstance(pointer, int) and self.get_setting('valid_range'):
            lower, upper = self.get_setting('valid_range')
            return not lower <= pointer <= upper
        if pointer in (None, 0):
            return True
        MAX_POINTER = (1 << (self.get_setting('pointer_length') * 8)) - 1
        NULL_POINTERS = (None, 0, MAX_POINTER)
        return pointer in NULL_POINTERS

    def guess_num_pointers(self):
        assert self.get_setting('num_pointers') is None
        pointers = self.get_setting('pointers')
        if pointers is not None:
            self.set_value('num_pointers', len(pointers))
            return

        byteorder = self.get_setting('byteorder')
        pointer_length = self.get_setting('pointer_length')
        relative_to = self.get_setting('relative_to')
        assert self.start >= self.parent.start
        self.parent.packed.seek(self.start-self.parent.start)
        pointers = []
        non_null = set()
        maximum = None
        if isinstance(self.start, int) and isinstance(self.finish, int):
            maximum = int((self.finish-self.start) / pointer_length)
        while True:
            if maximum is not None and len(pointers) >= maximum:
                assert len(pointers) == maximum
                break

            if non_null and (self.start <= relative_to or relative_to < 0):
                lowest = min(non_null)
                pointer_area = pointer_length * len(pointers)
                if lowest == pointer_area:
                    break
                elif lowest <= pointer_area:
                    pointers = pointers[:-1]
                    break

            pointer = self.parent.packed.read(pointer_length)
            if len(pointer) < pointer_length:
                break
            pointer = int.from_bytes(pointer, byteorder)

            if not self.check_null_pointer(pointer):
                pointer += (relative_to - self.parent.start)
                pointers.append(pointer)
                non_null.add(pointer)
            else:
                pointers.append(None)

        self.set_value('num_pointers', len(pointers))

    def get_pointer_table_size(self):
        if hasattr(self, '_pointer_table_size'):
            assert self.finish == self._pointer_table_size
            return self._pointer_table_size
        num_pointers = self.get_setting('num_pointers')

        if num_pointers is None:
            self.guess_num_pointers()
        elif isinstance(num_pointers, str):
            self.set_value('num_pointers', self.evaluate(num_pointers))
        assert self.get_setting('num_pointers') is not None

        self.check_pointer_dimensions()
        assert self.finish is not None
        self._pointer_table_size = self.finish
        return self.get_pointer_table_size()

    def preclean(self):
        self.guess_start()
        for c in self.children:
            c.preclean()

    def set_packed(self, packed=None):
        if hasattr(self, '_packed_length'):
            del(self._packed_length)

        if packed is not None:
            while hasattr(packed, 'packed'):
                packed = packed.packed
            if not isinstance(packed, BytesIO):
                packed = BytesIO(packed)
            self.packed = packed
            return

        assert self.parent is not None
        if not hasattr(self.parent, 'packed'):
            self.parent.set_packed()
        if self.start is None and self.slabel in self.nulled_addresses:
            self.packed = None
            return

        self.guess_finish()
        finish = self.finish
        if finish is None and self.is_pointers:
            finish = self.get_pointer_table_size()
        if finish is None:
            self.guess_finish(override=True)
            finish = self.finish
        if None in (self.start, finish):
            import pdb; pdb.set_trace()
        assert None not in (self.start, finish)
        assert finish >= self.start
        self.parent.guess_start()
        self.parent.guess_finish()
        assert None not in (self.parent.start, self.parent.finish)
        assert self.parent.start <= self.start <= finish <= self.parent.finish
        self.parent.packed.seek(self.start-self.parent.start)
        data = self.parent.packed.read(finish-self.start)
        assert len(data) == finish-self.start
        self.packed = BytesIO(data)

    def get_packed_length(self):
        if not hasattr(self, 'packed'):
            return None
        if hasattr(self, '_packed_length'):
            return self._packed_length
        self.packed.seek(0)
        self._packed_length = len(self.packed.read())
        return self.get_packed_length()

    def unpack_pointers(self):
        subformat = self.get_setting('subformat')
        pointer_names = self.get_setting('pointers')
        byteorder = self.get_setting('byteorder')
        pointer_length = self.get_setting('pointer_length')
        relative_to = self.get_setting('relative_to')
        if relative_to is None:
            relative_to = self.start
        elif isinstance(relative_to, str):
            relative_to = self.get_address(relative_to)
        pointers = []
        num_pointers = self.get_setting('num_pointers')
        if pointer_names is None:
            if num_pointers is not None:
                pointer_names = [None] * self.evaluate(
                        self.get_setting('num_pointers'))
            else:
                self.packed.seek(0, SEEK_END)
                if self.packed.tell() == 0:
                    pointer_names = []
                else:
                    self.guess_num_pointers()
                    pointer_names = [None] * self.evaluate(
                            self.get_setting('num_pointers'))

        if num_pointers:
            assert len(pointer_names) == self.evaluate(num_pointers)
        self.packed.seek(0)
        lowest = None
        for i, pointer_name in enumerate(pointer_names):
            pointer = self.packed.read(pointer_length)
            if subformat is None:
                pointer = BasicPointer(i, pointer,
                                       pointer_length=pointer_length,
                                       byteorder=byteorder)
            else:
                pointer = MaskStructPointer(i, self.subunpack(subformat,
                                                              pointer))
            if self.check_null_pointer(pointer):
                if isinstance(pointer_name, str):
                    self.nulled_addresses.add(pointer_name)
                    slabel = pointer_name
                    flabel = f'@{slabel}'
                    self.add_address(slabel, flabel)
                    self.add_address(flabel, slabel)
                pointers.append(None)
                continue
            pointers.append(pointer)
            value = pointer.pointer + relative_to
            lowest = value if lowest is None else min(lowest, value)
            if isinstance(pointer_name, str) \
                    and pointer_name.startswith('@'):
                self.add_address(pointer_name, value)
        pointers = [None if self.check_null_pointer(p) else p
                    for p in pointers]

        for section in self.tree.values():
            if pointers and lowest is None:
                break
            if not section.is_pointed_list:
                continue
            if section.config['linked_pointers'] != self.label:
                continue
            if lowest is not None and lowest not in section.starts:
                self.add_address(section.slabel, lowest)
            elif lowest is None and not pointers:
                self.add_address(section.slabel, section.flabel)

        return pointers

    def unpack_pointed_list(self):
        pointsec = self.tree[self.config['linked_pointers']]
        linked_pointers = pointsec.unpack()
        assert isinstance(linked_pointers, list)
        relative_to = pointsec.get_setting('relative_to')

        pointer_offset = relative_to - self.start
        offset_relation = {p: p.pointer for p in linked_pointers
                           if p is not None}
        pointers = [p.pointer + pointer_offset
                    for p in linked_pointers if p is not None]
        pointers = sorted(set(pointers))
        pointers.append(None)
        datas = {}
        for (a, b) in zip(pointers, pointers[1:]):
            assert 0 <= a
            self.packed.seek(a)
            if b is not None:
                assert a < b
                data = self.packed.read(b-a)
            else:
                data = self.packed.read()
            assert a not in datas
            datas[a] = data

        repeat = pointsec.get_setting('repeat')
        if repeat is None:
            repeat = False
        final_datas = {}
        previous_pointer = None
        sorted_pointers = sorted(p for p in linked_pointers if p is not None)
        for p in sorted_pointers:
            final_datas[p] = datas[p.pointer + pointer_offset]
            if repeat and previous_pointer is not None and \
                    previous_pointer.pointer == p.pointer:
                final_datas[previous_pointer] = b''
            previous_pointer = p

        return final_datas

    def unpack_regular_list(self):
        num_items = self.get_setting('num_items')
        item_size = self.get_setting('item_size')

        if None in (num_items, item_size):
            self.check_list_dimensions()
            num_items = self.get_setting('num_items')
            item_size = self.get_setting('item_size')

        item_size = self.evaluate(item_size)
        items = []
        self.packed.seek(0)
        for _ in range(self.evaluate(num_items)):
            item = self.packed.read(item_size)
            assert len(item) == item_size
            items.append(item)

        return items

    def unpack_mask_struct(self):
        masks = self.get_setting('masks')
        byteorders = {attr: masks[attr]['byteorder'] for attr in masks
                      if 'byteorder' in masks[attr]}
        collapsible = {attr: masks[attr]['collapse'] for attr in masks
                       if 'collapse' in masks[attr]}
        assert all(isinstance(v, bool) for v in collapsible.values())
        data_types = {attr: masks[attr]['data_type'] for attr in masks
                      if 'data_type' in masks[attr]}
        masks = {attr: masks[attr]['mask'] for attr in masks}
        numeric_masks = {}
        for attr in masks:
            mask = masks[attr]
            if isinstance(mask, str):
                while '  ' in mask:
                    mask = mask.replace('  ', ' ')
                mask = mask.strip().split()
                mask = bytes([int(c, 0x10) for c in mask])
                mask = int.from_bytes(mask, byteorder='big')
            numeric_masks[attr] = mask
        length = self.get_setting('total_length')
        if length is None:
            length = self.finish - self.start
        self.packed.seek(0)
        data = self.packed.read(length)
        return MaskStruct(data, numeric_masks, length=len(data),
                          data_types=data_types, byteorders=byteorders,
                          collapsible=collapsible)

    def unpack(self):
        if hasattr(self, 'unpacked'):
            return self.unpacked

        if self.slabel in self.nulled_addresses:
            return None

        unpacked = None
        if self.is_recursive and self.sections is not None:
            unpacked = {}
            for key in self.sections:
                assert self.sections[key] in self.children
                unpacked[key] = self.sections[key].unpack()
            self.unpacked = unpacked
            return self.unpack()

        if not hasattr(self, 'packed'):
            self.set_packed()

        if self.packed is None:
            return None

        if 'data_type' not in self.config:
            raise Exception(f'Undefined data type: {self.label}')

        self.guess_start()
        self.guess_finish()
        if self.config['data_type'] in ('blob', 'ignore'):
            assert unpacked is None
            self.packed.seek(0)
            data = self.packed.read()
            unpacked = data

        if self.is_pointers:
            assert unpacked is None
            unpacked = self.unpack_pointers()

        if self.is_pointed_list:
            unpacked = self.unpack_pointed_list()

        if self.is_regular_list:
            unpacked = self.unpack_regular_list()

        if self.is_mask_struct:
            unpacked = self.unpack_mask_struct()

        if unpacked is None:
            raise Exception(f'Unknown data type: {self.label}')

        subformat = self.get_setting('subformat')
        if subformat is not None:
            if isinstance(unpacked, dict):
                for k, v in list(unpacked.items()):
                    unpacked[k] = self.subunpack(subformat, v)
            elif isinstance(unpacked, list):
                unpacked = [self.subunpack(subformat, v) for v in unpacked]
            elif isinstance(unpacked, bytes):
                unpacked = self.subunpack(subformat, unpacked)
            else:
                import pdb; pdb.set_trace()

        if self.is_pointers:
            assert isinstance(unpacked, list)
            test = [p for p in unpacked if p is not None]
            if test and not isinstance(test[0], BasicPointer):
                if isinstance(test[0], MaskStruct):
                    unpacked = [MaskStructPointer(i, p) if p is not None
                                else None for (i, p) in enumerate(unpacked)]
                else:
                    raise Exception('Invalid pointer data type.')

        if 'value' in self.config and None not in (self.start, self.finish) \
                and self.finish > self.start:
            if isinstance(unpacked, bytes):
                value = int.from_bytes(unpacked,
                                       byteorder=self.get_setting('byteorder'))
                evaluated = self.evaluate(self.config['value'])
                if value != evaluated and evaluated != '{%s}' % self.label:
                    raise Exception(f'Validation failure: {self.label}')
            else:
                raise NotImplementedError
        self.unpacked = unpacked
        return self.unpack()

    def set_unpacked(self, unpacked):
        self.unpacked = unpacked
        if unpacked is None:
            for c in self.descendents:
                assert not hasattr(c, 'unpacked')
                c.unpacked = None
            return
        for c in self.children:
            c.set_unpacked(unpacked[c.label])

    def repack_regular_list(self):
        return b''.join(self.unpacked)

    def repack_pointed_list(self):
        SORTED_ORDER = False
        PRESERVE_POINTERS = False
        OPTIMIZE = False
        SEMIOPTIMIZE = False

        pointsec = self.tree[self.config['linked_pointers']]
        pointer_order = pointsec.get_setting('pointer_order')
        repeat = pointsec.get_setting('repeat')
        if repeat is None:
            repeat = False

        if pointer_order == 'optimize':
            OPTIMIZE = True
        elif pointer_order == 'sorted':
            SORTED_ORDER = True
        elif pointer_order == 'preserve':
            PRESERVE_POINTERS = True
        else:
            raise Exception('Unknown pointer order.')

        keys = {k for k in pointsec.unpacked if k is not None}
        assert keys <= set(self.unpacked.keys())
        if keys != set(self.unpacked.keys()):
            print(f'WARNING: Mismatched keys in section {self.label}')

        if not (SORTED_ORDER or PRESERVE_POINTERS or OPTIMIZE):
            raise Exception(f'Undefined order: {self.label}')

        offsets = {}

        if SORTED_ORDER or OPTIMIZE:
            assert not PRESERVE_POINTERS
            if OPTIMIZE:
                keys = sorted(keys, key=lambda k: (-len(self.unpacked[k]), k))
            elif SORTED_ORDER:
                keys = sorted(keys)
            alldata = b''
            previous_offset = None
            previous_data = None
            for key in keys:
                data = self.unpacked[key]
                if SEMIOPTIMIZE and previous_offset is not None:
                    previous_data = alldata[previous_offset:]
                if OPTIMIZE and data in alldata:
                    offset = alldata.index(data)
                elif previous_data and repeat is False and \
                        data in previous_data:
                    offset = previous_data.index(data)
                    offset += previous_offset
                elif repeat is False and previous_offset is not None and \
                        alldata[previous_offset:] == data:
                    offset = previous_offset
                else:
                    offset = len(alldata)
                    alldata += data
                offsets[key] = offset
                previous_offset = offset

        if PRESERVE_POINTERS:
            lowest = 0
            if self.unpacked.keys():
                lowest = min(self.unpacked.keys())
            with BytesIO(b'') as f:
                for verify in (False, True):
                    for key in self.unpacked.keys():
                        f.seek(key-lowest)
                        mydata = self.unpacked[key]
                        if not verify:
                            f.write(mydata)
                            offsets[key] = key-lowest
                        else:
                            vdata = f.read(len(mydata))
                            if vdata != mydata:
                                raise Exception(
                                        f'Unable to verify {self.label} data '
                                        f'at offset {key:x}.')
                f.seek(0)
                alldata = f.read()

        pointsec.linked_offsets = offsets
        pointsec.linked_section = self
        return alldata

    def repack_pointers(self):
        if not hasattr(self, 'table'):
            self.table = Unpacker.PointerTable(self)
        if 'pointers' in self.config:
            assert not hasattr(self, 'linked_section')
            self.table.pointers = list(self.config['pointers'])
        if hasattr(self, 'linked_section'):
            assert 'pointers' not in self.config
            pointers = []
            previous_offset = None
            for key in self.unpacked:
                if key is None:
                    pointers.append(None)
                    continue
                else:
                    offset = self.linked_offsets[key]
                    pointers.append(
                            (key, f'@{self.linked_section.label},{offset}'))
                    previous_offset = offset
            self.table.pointers = pointers
        return self.table

    def repack_mask_struct(self):
        return self.unpacked.packed

    def partial_repack(self):
        if self is self.root and not hasattr(self, '_packed_cache'):
            self._packed_cache = {}
        if self.label in self.root._packed_cache:
            return self.root._packed_cache[self.label]

        subformat = self.get_setting('subformat')
        backup_unpacked = None
        if subformat and self.get_setting('data_type') != 'pointers':
            unpacked = self.unpacked
            backup_unpacked = copy(unpacked)
            if isinstance(unpacked, dict):
                for k, v in list(unpacked.items()):
                    unpacked[k] = self.subrepack(subformat, v)
            elif isinstance(unpacked, list):
                unpacked = [self.subrepack(subformat, v) for v in unpacked]
            elif isinstance(unpacked, bytes):
                unpacked = self.subrepack(subformat, unpacked)
            self.unpacked = unpacked

        packed = None
        if self.children:
            complete = True
            nonpoint_children = [c for c in self.children
                                 if not c.is_pointers]
            point_children = [c for c in self.children if c.is_pointers]
            packed = {}
            for c in nonpoint_children + point_children:
                cpacked = c.partial_repack()
                if cpacked is None:
                    complete = False
                    continue
                packed[c.label] = cpacked
            packed = set(packed.keys())
        elif self.unpacked is None:
            packed = None
        elif self.is_regular_list:
            packed = self.repack_regular_list()
        elif self.is_pointed_list:
            packed = self.repack_pointed_list()
        elif self.is_pointers:
            packed = self.repack_pointers()
        elif self.is_mask_struct:
            packed = self.repack_mask_struct()
        elif self.config['data_type'] in ('blob', 'ignore'):
            assert isinstance(self.unpacked, bytes)
            packed = self.unpacked
        else:
            import pdb; pdb.set_trace()

        self.root._packed_cache[self.label] = packed

        if backup_unpacked is not None:
            self.unpacked = backup_unpacked

        return self.partial_repack()

    def calculate_packed_size(self):
        if hasattr(self, '_packed_size'):
            return self._packed_size

        if not self.children:
            packed = self.root._packed_cache[self.label]
            if packed is None:
                return 0
            assert type(packed) in (bytes, Unpacker.PointerTable)
            self._packed_size = len(packed)
            return self.calculate_packed_size()

        total_size = 0
        for c in self.children:
            total_size += c.calculate_packed_size()

        verify = 0
        for c in self.descendents:
            packed = self.root._packed_cache[c.label]
            if type(packed) in (bytes, Unpacker.PointerTable):
                verify += len(packed)
        assert verify == total_size
        self._packed_size = total_size
        return self.calculate_packed_size()

    def calculate_packed_addresses(self):
        assert self is self.root
        eof = self.calculate_packed_size()
        assert eof is not None
        local_updated = True
        while local_updated:
            local_updated = False
            problems = set()
            for c in self.descendents:
                packed_size = c.calculate_packed_size()
                slabel = f'@{c.label}'
                flabel = f'@{slabel}'
                start = c.get_address(slabel)
                finish = c.get_address(flabel)
                if None not in (start, finish) and \
                        finish - start == packed_size:
                    continue
                if start is not None:
                    finish = start + packed_size
                    if finish not in self.addresses[flabel]:
                        self.add_address(flabel, finish)
                        local_updated = True
                else:
                    problems.add(c)
                if c.finishes and '!eof' in c.finishes \
                        and eof not in c.finishes:
                    local_updated = True
                    self.add_address(flabel, eof)
                finish = c.get_address(flabel)
                if finish is not None:
                    start = finish - packed_size
                    if start not in self.addresses[slabel]:
                        self.add_address(slabel, start)
                        local_updated = True

            if local_updated:
                continue

            problems = {c for c in problems if c.unpacked is not None}
            if not problems:
                break

            problems = sorted(problems, key=lambda c: c.index)
            for c in problems:
                if local_updated:
                    break
                packed_size = c.calculate_packed_size()
                parent = c.parent
                candidates = {c.parent.start}
                blacklisted = {None}
                for c2 in parent.children:
                    blacklisted.add(c2.start)
                    candidates.add(c2.finish)
                candidates = candidates - blacklisted
                align = None
                if 'align' in c.config:
                    align = c.config['align']
                    if isinstance(align, int):
                        align_m, align_r = align, 0
                    else:
                        align_m, align_r = align
                for candidate in sorted(candidates):
                    if align:
                        while candidate % align_m != align_r:
                            candidate += 1
                    upper = candidate + packed_size
                    test = {a for a in blacklisted if a is not None
                            and candidate <= a < upper}
                    if test:
                        continue
                    self.add_address(c.slabel, candidate)
                    local_updated = True
                    break

            if not local_updated:
                raise Exception('Unable to allocate packed data.')

        for c in self.descendents:
            if 'align' in c.config:
                align = c.config['align']
                if c.start % align:
                    raise Exception(
                        f'Section {c.label} misaligned: {c.start:x}')

    def repack(self):
        assert self is self.root
        self.partial_repack()
        self.calculate_packed_addresses()

        if self.is_recursive:
            packed = BytesIO(b'\x00' * self.calculate_packed_size())
            for verify in (False, True):
                for c in self.descendents:
                    cpacked = self._packed_cache[c.label]
                    if cpacked is None:
                        continue
                    assert cpacked is not None
                    if isinstance(cpacked, set):
                        continue
                    if isinstance(cpacked, Unpacker.PointerTable):
                        cpacked = cpacked.bytecode
                    assert isinstance(cpacked, bytes)
                    assert len(cpacked) == c.finish-c.start
                    packed.seek(c.start)
                    if not verify:
                        packed.write(cpacked)
                    else:
                        verification = packed.read(len(cpacked))
                        assert verification == cpacked
                    assert packed.tell() == c.finish
        else:
            assert self is self.root
            assert not self.descendents
            packed = BytesIO(self.root._packed_cache[self.label])

        self.set_packed(packed)
        self.packed.seek(0)
        return self.packed.read()

    def subunpack(self, subformat, packed):
        subun = Unpacker(subformat, superformat=self)
        subun.set_packed(packed)
        return subun.unpack()

    def subrepack(self, subformat, unpacked):
        subun = Unpacker(subformat, superformat=self)
        subun.set_unpacked(unpacked)
        return subun.repack()


if __name__ == '__main__':
    config_filename = argv[1]
    data_filenames = argv[2:]
    with open(config_filename) as f:
        config = yaml.safe_load(f.read(), testing=True)
    assert isinstance(config, OrderedDict)
    for fn in data_filenames:
        print(fn)
        u = Unpacker(config)
        with open(fn, 'r+b') as f:
            data = f.read()
            u.set_packed(data)
        unpacked = u.unpack()

        u2 = Unpacker(config)
        u2.set_unpacked(unpacked)
        verify = u2.repack()

        u3 = Unpacker(config)
        u3.set_packed(verify)
        verify_unpacked = u3.unpack()

        if data != verify:
            with open('_nested.a.txt', 'w+') as f:
                f.write(json.dumps(unpacked, indent=2, cls=BytesEncoder))
            with open('_nested.b.txt', 'w+') as f:
                f.write(json.dumps(verify_unpacked, indent=2,
                                   cls=BytesEncoder))
            print('ERROR')
            import pdb; pdb.set_trace()
