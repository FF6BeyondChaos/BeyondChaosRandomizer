from collections import OrderedDict, defaultdict
from copy import deepcopy
from io import SEEK_END, BytesIO
from sys import argv

from .utils import cached_property
from .utils import fake_yaml as yaml
from .utils import mask_compress, mask_decompress, reverse_byte_order, warn

VERIFY_PARSING = False


def hexify(s):
    result = []
    while s:
        w = s[:4]
        s = s[4:]
        w = ' '.join('{0:0>2x}'.format(c) for c in w)
        result.append(w)
    return ' '.join(result)


def mask_shift_left(value, mask):
    assert mask
    count = 0
    while not mask & 1:
        mask >>= 1
        count += 1
    return value << count


assert mask_decompress(0x2b4, 0xeff) == 0x4b4


class TrackedPointer:
    def __init__(self, pointer, virtual_address, parser):
        self.virtual_address = virtual_address
        self.pointer = pointer
        self.old_pointer = pointer
        self.parser = parser
        assert self.pointer - self.virtual_address >= 0

    def __repr__(self):
        return f'{self}'

    def __format__(self, format_spec):
        return self.parser.format_pointer(self, format_spec)

    def __eq__(self, other):
        if self.parser is not other.parser:
            return False
        return self is other

    def __lt__(self, other):
        return self.pointer < other.pointer

    def __hash__(self):
        return self.old_pointer

    @property
    def converted(self):
        return self.parser.convert_pointer(self)

    @property
    def converted_repointer(self):
        return self.parser.convert_pointer(self, repointed=True)

    @property
    def converted_smart(self):
        if hasattr(self, 'repointer') and self.repointer is not None:
            return self.converted_repointer
        else:
            return self.converted


class Instruction:
    def __init__(self, script=None, opcode=None, parameters=None, parser=None,
                 start_address=None, end_address=None):
        self.start_address, self.end_address = start_address, end_address
        self.script = None
        self.context = None
        self.parameters = None
        self.text_parameters = None
        if script is not None:
            self.set_script(script)
        if self.script is not None:
            self._parser = self.script.parser
        elif parser is not None:
            self._parser = parser
        self.context = self.script.context
        if opcode is None and parameters is None:
            self.read_from_data()
        if opcode is not None and parameters is not None:
            self.opcode = opcode
            self.set_parameters(**parameters)
        else:
            self.set_parameters()
        if 'context' in self.manifest:
            self.script.context = self.manifest['context']
        if VERIFY_PARSING and hasattr(self, 'old_data'):
            verification = self.parser.instruction_to_bytecode(
                    self, convert_pointers=False)
            if verification != self.old_data:
                warn(f'Destructive parsing of byte sequence: '
                     f'{hexify(self.old_data)}',
                     repeat_key=f'INST {self.opcode:x}')

    def __repr__(self):
        if not hasattr(self.parser, 'format_length'):
            self.parser.update_format_length()
        format_length = self.parser.format_length
        formatted = self.format
        if '\n' not in formatted and len(formatted) <= format_length:
            s = ('{0:%s}   # {1}' % format_length).format(formatted,
                                                          self.comment)
        else:
            if '\n' not in formatted:
                formatted = self.format_multiline
            topline, body = formatted.split('\n', 1)
            topline = ('{0:%s}   # {1}' % format_length).format(topline,
                                                                self.comment)
            s = f'{topline}\n{body}'

        if self.text_parameters:
            for parameter_name, text in self.text_parameters.items():
                s = f'{s}\n{self.parser.format_text(parameter_name, text)}'
        s = s.replace('\n', '\n  ')
        return s

    @property
    def config(self):
        return self.parser.config

    @property
    def signature(self):
        return (self.opcode, self.context,
                frozenset(self.parameters.items()),
                frozenset(self.text_parameters.items()))

    def set_script(self, script):
        if self.script is not None and self in self.script.instructions:
            return
        self.script = script
        if self.start_address is None:
            if self.script.instructions:
                self.start_address = max(i.start_address
                                         for i in self.script.instructions) + 1
            else:
                self.start_address = 1
        self.script.instructions.append(self)
        if self.context is None:
            self.context = self.script.context

    def read_from_data(self):
        self.start_address = self.parser.data.tell()
        header_size = self.parser.config['opcode_size']
        data = self.parser.data.read(header_size)

        opcode_key = (self.context, data)
        if opcode_key not in self.parser.valid_opcode_cache:
            header_size = len(data)
            header = int.from_bytes(data, byteorder='big')
            instructions = self.parser.get_instructions(context=self.context)
            originals = \
                    self.parser.config['contexts'][self.context]['_original']
            valid_opcodes, inherited_opcodes = set(), set()
            for opcode in instructions:
                opcode_size = instructions[opcode]['opcode_size']
                if header_size < opcode_size:
                    continue
                mask = instructions[opcode]['mask']
                tempcode = header >> ((header_size - opcode_size) * 8)
                if tempcode & mask == opcode & mask:
                    if 'range' in instructions[opcode] and \
                            instructions[opcode]['range'] is not None:
                        lower, upper = instructions[opcode]['range']
                        if not lower <= tempcode <= upper:
                            continue
                    if opcode in originals:
                        valid_opcodes.add(opcode)
                    else:
                        inherited_opcodes.add(opcode)
            if not valid_opcodes:
                valid_opcodes = inherited_opcodes
            if len(valid_opcodes) != 1:
                def short_dump():
                    for i in self.script.instructions:
                        try:
                            print(f'{i.start_address:x} {i.opcode:0>2x} '
                                  f'{i.context}')
                        except:
                            print(f'{i.start_address:x} -- {i.context}')
                if len(valid_opcodes) == 0:
                    msg = (f'Undefined opcode at @{self.start_address:x}: '
                           f'{header:x} (context {self.context})')
                    short_dump()
                    print(msg)
                    raise Exception(msg)
                if len(valid_opcodes) >= 2:
                    msg = (f'Multiple opcode at @{self.start_address:x}: '
                           f'{header:x} (context {self.context})')
                    short_dump()
                    print(msg)
                    raise Exception(msg)
            self.parser.valid_opcode_cache[opcode_key] = valid_opcodes.pop()

        self.opcode = self.parser.valid_opcode_cache[opcode_key]

        parameters = OrderedDict()
        parameter_order = self.manifest['parameter_order']
        length = self.manifest['length']
        self.end_address = self.start_address + length
        temp = len(data)
        if temp > length:
            data = data[:length]
            self.parser.data.seek(self.end_address)
        elif temp < length:
            self.parser.data.seek(self.start_address)
            data = self.parser.data.read(length)
        if VERIFY_PARSING:
            self.old_data = data

        data = int.from_bytes(data, byteorder='big')
        for parameter_name in parameter_order:
            field = self.manifest['fields'][parameter_name]
            assert field is not None
            if field['mask'] == 'variable':
                continue
            value = data & field['mask']
            tempmask = field['mask']
            if field['compress_mask']:
                oldvalue = value
                value, tempmask = mask_compress(value, tempmask)
            while not tempmask & 1:
                tempmask >>= 1
                value >>= 1
            if field['byteorder'] == 'little':
                old = value
                value = reverse_byte_order(value, mask=tempmask)
            if field['is_pointer']:
                #self.parser.script_pointers.add(value)
                if isinstance(field['propagate_context'], str):
                    context = field['propagate_context']
                else:
                    context = self.context
                value = self.parser.get_tracked_pointer(
                        value, field['virtual_address'], script=True,
                        context=context)
            parameters[parameter_name] = value

        self.parameters = parameters

        if 'is_variable_length' in self.manifest \
                and self.manifest['is_variable_length']:
            self.parser.seek(end_address)
            self.parser.read_variable_length(self)
            self.end_address = self.parser.data.tell()

        self.parser.log_read_data(self.start_address, self.end_address)

    def set_parameters(self, **kwargs):
        if not hasattr(self, 'parameters') or self.parameters is None:
            self.parameters = {}
        if not hasattr(self, 'text_parameters') or \
                self.text_parameters is None:
            self.text_parameters = {}
        for parameter_name, value in kwargs.items():
            assert value is not None
            pmani = self.manifest['fields'][parameter_name]
            is_text = 'is_text' in pmani and pmani['is_text']
            if is_text and isinstance(value, str):
                self.text_parameters[parameter_name] = value
                continue
            if not is_text:
                if 'is_pointer' in pmani and pmani['is_pointer']:
                    assert isinstance(value, self.parser.TrackedPointer)
                else:
                    assert not isinstance(value, self.parser.TrackedPointer)
            self.parameters[parameter_name] = value
            if is_text and parameter_name not in self.text_parameters:
                self.text_parameters[parameter_name] = None

    def update_text(self, text, parameter_name=None):
        if parameter_name in self.text_parameters:
            text = '\n'.join([self.text_parameters[parameter_name], text])
        self.text_parameters[parameter_name] = text
        return True

    def prettify_parameter(self, parameter_name):
        value = self.parameters[parameter_name]
        try:
            pmani = self.manifest['fields'][parameter_name]
            return pmani['prettify'][value]
        except KeyError:
            pass
        if parameter_name in self.config['prettify']:
            pretty = self.config['prettify'][parameter_name]
            while isinstance(pretty, str):
                assert pretty != self.config['prettify'][pretty]
                pretty = self.config['prettify'][pretty]
            assert isinstance(pretty, dict)
            try:
                return pretty[value]
            except KeyError:
                pass
        return None

    @property
    def format(self):
        if 'expand_multiline' in self.config \
                and len(self.parameters) >= self.config['expand_multiline']:
            return self.format_multiline
        parameters = []
        for parameter_name in self.parameters:
            parameters.append(
                    self.parser.format_parameter(self, parameter_name))
        parameters = ','.join(parameters)
        opcode = self.parser.format_opcode(self.opcode)
        return f'{opcode}:{parameters}'

    @property
    def format_multiline(self):
        s = self.parser.format_opcode(self.opcode) + ':\n'
        maxlength = -1
        parameters = []
        for parameter_name in self.parameters:
            value = self.parser.format_parameter(self, parameter_name)
            if ',' in value:
                value = value.replace(',', ', ')
            while '  ' in value:
                value = value.replace('  ', ' ')
            parameters.append((parameter_name, value))
            maxlength = max(maxlength, len(parameter_name))
        lineformat = '{0:%s} = {1}' % maxlength
        lines = []
        maxlength = -1
        for parameter_name, value in parameters:
            line = lineformat.format(parameter_name, value)
            maxlength = max(maxlength, len(line))
            comment = self.prettify_parameter(parameter_name)
            lines.append((line, comment))
        for line, comment in lines:
            if comment is not None:
                s += ('{0:%s}  # {1}\n' % maxlength).format(line, comment)
            else:
                s += line + '\n'
        return s.strip()

    @property
    def comment(self):
        parameters = dict(self.parameters)
        for parameter_name in set(parameters.keys()):
            if parameter_name not in self.manifest['fields']:
                continue
            pmani = self.manifest['fields'][parameter_name]
            prettified = None
            prettified = self.prettify_parameter(parameter_name)
            if prettified is None:
                prettified = self.parser.format_parameter(self, parameter_name)
            parameters[f'_pretty_{parameter_name}'] = prettified
        if 'comment' not in self.manifest:
            return f'Unknown {self.opcode:0>2x}'
        return self.manifest['comment'].format(**parameters)

    @property
    def parser(self):
        if hasattr(self, '_parser'):
            if self.script is not None:
                assert self.script.parser is self._parser
            return self._parser
        return self.script.parser

    @cached_property
    def manifest(self):
        instructions = self.parser.get_instructions(context=self.context)
        manifest = instructions[self.opcode]
        assert 'inherit' not in manifest
        return manifest

    @property
    def references(self):
        return [v for (k, v) in self.parameters.items()
                if isinstance(v, self.parser.TrackedPointer)]

    @property
    def referenced_scripts(self):
        return [self.parser.scripts[r.pointer] for r in self.references
                if r.pointer in self.parser.scripts]

    @property
    def is_terminator(self):
        return self.manifest['is_terminator']

    @property
    def bytecode(self):
        bytecode = self.parser.instruction_to_bytecode(self)
        length = self.manifest['length']
        if not self.manifest['is_variable_length']:
            assert len(bytecode) == length
        else:
            assert len(bytecode) >= length
        return bytecode

    @property
    def bytecode_length(self):
        if self.manifest['is_variable_length']:
            return len(self.bytecode)
        length = self.manifest['length']
        return length


class Script:
    def __init__(self, pointer, parser):
        self.pointer = pointer
        self.parser = parser
        self.joined_before, self.joined_after = None, None
        self.truncate()

    def __repr__(self):
        header = self.parser.format_pointer(self.pointer)
        if self.instructions and (self.instructions[0].context !=
                                  self.parser.config['default_context']):
            context = self.instructions[0].context
            header = f'{header} ({context})'

        comment = self.comment
        if comment is not None:
            header = f'{header}  # {comment}'
        elif self.pointer in self.parser.original_pointers:
            header = f'{header}  # origin'

        lines = [header]

        start_addresses = [f'{i.start_address:x}' for i in self.instructions]
        address_length = 0
        if start_addresses:
            address_length = max(len(addr) for addr in start_addresses)

        for instruction in self.instructions:
            line = '{0:0>%sx}. {1}' % address_length
            lines.append(line.format(
                instruction.start_address,
                self.parser.format_instruction(instruction)))
        if self.joined_after:
            after = self.joined_after
            line = f'{after.pointer.pointer:x}. {after.pointer}'
            lines.append(line)
        s = '\n'.join(lines)
        s = s.replace('\n', '\n  ')
        return s.strip()

    def __eq__(self, other):
        if self.parser is not other.parser:
            return False
        return self is other

    def __lt__(self, other):
        return self.pointer < other.pointer

    def __hash__(self):
        if not hasattr(self, '_hash'):
            self._hash = (self.parser.__hash__(),
                          self.pointer.__hash__()).__hash__()
        return self._hash

    @property
    def comment(self):
        return None

    @property
    def references(self):
        return {r for i in self.instructions for r in i.references}

    @property
    def referenced_scripts(self):
        references = {r.pointer for r in self.references}
        references.add(self.pointer.pointer)
        scripts = {v for (k, v) in self.parser.scripts.items()
                   if k in references}
        return scripts

    @property
    def bytecode(self):
        bytecode = self.parser.script_to_bytecode(self)
        assert len(bytecode) == self.bytecode_length
        return bytecode

    @property
    def bytecode_length(self):
        bytecode_length = sum([i.bytecode_length for i in self.instructions])
        return bytecode_length

    @property
    def start_address(self):
        if not self.instructions:
            return None
        return self.instructions[0].start_address

    @property
    def end_address(self):
        if not self.instructions:
            return None
        return self.instructions[-1].end_address

    @property
    def joined_start(self):
        before = self
        while before.joined_before:
            before = before.joined_before
        return before

    @property
    def joined_bytecode(self):
        after = self.joined_start
        bytecode = after.bytcode
        while after.joined_after:
            after = after.joined_after
            bytecode += after.bytecode
        return bytecode

    @property
    def joined_bytecode_length(self):
        after = self.joined_start
        bytecode_length = after.bytecode_length
        while after.joined_after is not None:
            after = after.joined_after
            bytecode_length += after.bytecode_length
        return bytecode_length

    @property
    def joined_references(self):
        after = self.joined_start
        references = set(after.references)
        chain = {self.pointer}
        while after.joined_after is not None:
            after = after.joined_after
            chain.add(after.pointer)
            references |= after.references
        return references - chain

    @property
    def joined_referenced_scripts(self):
        references = {r.pointer for r in self.joined_references}
        references.add(self.joined_start.pointer.pointer)
        scripts = {v for (k, v) in self.parser.scripts.items()
                   if k in references}
        return scripts

    def insert_instruction(self, index, text):
        instruction = self.parser.interpret_instruction(text, self)
        instruction.start_address = 0
        self.instructions.insert(index, instruction)

    def append_instruction(self, text):
        self.insert_instruction(len(self.instructions), text)

    def prepend_instruction(self, text):
        self.insert_instruction(0, text)

    def split(self, pointer):
        ever_after = self.joined_after
        new_script = self.parser.Script(pointer=pointer,
                                        parser=self.parser)
        after_instructions = [i for i in self.instructions
                              if pointer.converted <= i.start_address]
        self.instructions = [i for i in self.instructions
                             if i not in after_instructions]
        new_script.instructions = after_instructions
        if ever_after is not None:
            assert ever_after.joined_before is self
            self.joined_after = None
            ever_after.joined_before = new_script
            new_script.joined_after = ever_after
        self.join(new_script)
        return self, new_script

    def join(self, script):
        if self.joined_after:
            assert self.joined_after is script
        if script.joined_before:
            assert script.joined_before is self
        self.joined_after = script
        script.joined_before = self
        assert self.joined_after.joined_before is self
        assert script.joined_before.joined_after is script

    def truncate(self):
        self.instructions = []
        self.parser.set_context(self)
        if self.joined_after:
            self.joined_after.joined_before = None
        self.joined_after = None


class Parser:
    Script = Script
    Instruction = Instruction
    TrackedPointer = TrackedPointer

    USE_BYTECODE_CACHE = True
    INSTRUCTION_BYTECODE_CACHE = {}

    def __init__(self, config, data, pointers, log_reads=False,
                 reserved_contexts=None):
        if isinstance(config, dict):
            self.config = config
        else:
            with open(config, encoding='utf8') as f:
                self.config = yaml.safe_load(f.read())
        self.clean_config()
        if not isinstance(data, bytes):
            assert isinstance(data, str)
            with open(data, 'r+b') as f:
                data = f.read()
        self.data = BytesIO(data)
        self.original_data = self.data.read()
        self.max_address = self.data.tell()
        self.data.seek(0)
        self.log_reads = log_reads
        self.readlog = None
        if self.log_reads:
            self.readlog = BytesIO(bytes(len(self.original_data)))
        self.scripts = None
        self.pointers = {}
        self.script_pointers = set()
        self.original_pointers = set()
        for p in pointers:
            p2 = self.add_pointer(p, script=True)
            self.original_pointers.add(p2)
        self.get_text_decode_table()
        self.reserved_contexts = {}
        if reserved_contexts is not None:
            for pointer, context in sorted(reserved_contexts.items()):
                pointer = self.get_tracked_pointer(pointer)
                self.reserve_context(pointer, context)
        self.valid_opcode_cache = {}
        if hasattr(self, 'VALID_OPCODE_CACHE'):
            self.valid_opcode_cache = self.VALID_OPCODE_CACHE
        self.read_scripts()

    def clean_config(self):
        defaults = {
            'prettify': {},
            }
        for key in defaults:
            if key not in self.config:
                self.config[key] = defaults[key]

        for conname, context in self.config['contexts'].items():
            instructions = context['instructions']
            if '_original' not in context:
                context['_original'] = deepcopy(instructions)
            if 'inherit' in context:
                incontexts = context['inherit']
                incontexts = incontexts.split(',')
                for incontext in incontexts:
                    inconin = self.config['contexts'][incontext]
                    for opcode, v in inconin['instructions'].items():
                        if opcode not in instructions:
                            instructions[opcode] = v
                del(context['inherit'])

            for opcode, inconf in instructions.items():
                while 'inherit' in inconf:
                    incode = inconf['inherit']
                    del(inconf['inherit'])
                    for key in instructions[incode]:
                        if key == 'parameter_order':
                            if inconf['fields'].keys() != \
                                    instructions[incode]['fields'].keys():
                                continue
                        if key not in inconf:
                            inconf[key] = deepcopy(instructions[incode][key])

                assert 'parameters' not in inconf
                if 'mask' not in inconf:
                    if opcode == 0:
                        mask = 0xff
                    else:
                        mask = 0
                        while True:
                            mask <<= 8
                            mask |= 0xff
                            if mask & opcode == opcode:
                                break
                    inconf['mask'] = mask
                else:
                    mask = inconf['mask']
                maskmask = 0
                opcode_size = 0
                while True:
                    opcode_size += 1
                    maskmask <<= 8
                    maskmask |= 0xff
                    if mask & maskmask == mask:
                        break
                inconf['opcode_size'] = opcode_size

                if 'length' not in inconf:
                    inconf['length'] = opcode_size

                length = inconf['length']
                if isinstance(length, str):
                    assert length.endswith('+')
                    inconf['length'] = int(length[:-1])
                    if 'is_variable_length' in inconf:
                        assert inconf['is_variable_length'] is True
                    inconf['is_variable_length'] = True

                assert isinstance(inconf['length'], int)

                if 'fields' not in inconf:
                    length = inconf['length']
                    fieldmask = (1 << (length * 8)) - 1
                    fieldmask ^= inconf['mask'] << ((length-opcode_size)*8)
                    if fieldmask:
                        fields = {'_unknown': {'mask': fieldmask,
                                               'is_pointer': False}}
                    else:
                        fields = {}
                    inconf['fields'] = fields

                defaults = {
                    'is_terminator': False,
                    'is_variable_length': False,
                    }
                for attr in defaults:
                    if attr not in inconf:
                        inconf[attr] = defaults[attr]

                defaults = {
                    'byteorder': 'big',
                    'compress_mask': False,
                    'is_pointer': False,
                    'is_list': False,
                    'is_bytes': False,
                    'is_text': False,
                    'propagate_context': False,
                    'virtual_address': 0,
                    }
                if 'virtual_address' in self.config:
                    defaults['virtual_address'] = \
                            self.config['virtual_address']
                for attr in defaults:
                    if attr in self.config:
                        default = self.config[attr]
                    else:
                        default = defaults[attr]
                    for fieldname, field in inconf['fields'].items():
                        if field is None:
                            continue
                        if attr not in field:
                            field[attr] = default

                if 'parameter_order' not in inconf:
                    inconf['parameter_order'] = [k for k in inconf['fields']]

                for parameter_name in list(inconf['parameter_order']):
                    if inconf['fields'][parameter_name] is None:
                        inconf['parameter_order'].remove(parameter_name)

    def log_read_data(self, start, finish):
        if not self.log_reads:
            return
        assert start <= finish
        self.readlog.seek(start)
        self.readlog.write(b'\xff' * (finish-start))
        assert self.readlog.tell() == finish
        self.readlog.seek(0)

    def get_unread_data(self):
        self.readlog.seek(0)
        data = BytesIO(self.original_data)
        data.seek(0)
        unread_data = {}
        current_segment = b''
        current_pointer = 0
        while True:
            peek = self.readlog.read(1)
            if len(peek) == 0:
                break
            if peek == b'\x00':
                if not current_segment:
                    current_pointer = self.readlog.tell() - 1
                data.seek(self.readlog.tell() - 1)
                current_segment += data.read(1)
            elif peek == b'\xff':
                if current_segment:
                    unread_data[current_pointer] = current_segment
                    current_segment = b''
        if current_segment:
            unread_data[current_pointer] = current_segment
            current_segment = b''
        return unread_data

    def set_context(self, script):
        if script.pointer in self.reserved_contexts:
            script.context = self.reserved_contexts[script.pointer]
        else:
            script.context = self.config['default_context']

    def reserve_context(self, pointer, context):
        assert isinstance(pointer, TrackedPointer)
        if pointer in self.reserved_contexts:
            assert self.reserved_contexts[pointer] == context
        else:
            self.reserved_contexts[pointer] = context
        if self.scripts and pointer.converted in self.scripts:
            script = self.scripts[pointer.converted]
            if script.instructions:
                assert script.instructions[0].context == context
            else:
                script.context = context

    def get_instructions(self, context=None):
        return self.config['contexts'][context]['instructions']

    def get_tracked_pointer(self, pointer, virtual_address=None,
                            script=False, context=None):
        if pointer in self.pointers:
            return self.pointers[pointer]
        if virtual_address is None:
            virtual_address = self.config['virtual_address']
        tracked_pointer = self.TrackedPointer(pointer, virtual_address, self)
        self.pointers[pointer] = tracked_pointer
        if script:
            self.script_pointers.add(tracked_pointer)
        if context is not None:
            assert script
            self.reserve_context(tracked_pointer, context)
        return tracked_pointer

    add_pointer = get_tracked_pointer

    def convert_pointer(self, pointer, repointed=False):
        if repointed:
            return pointer.repointer - pointer.virtual_address
        else:
            return pointer.pointer - pointer.virtual_address

    def get_text_decode_table(self):
        self.text_decode_table = {}
        self.text_encode_table = {}
        if 'text_decode_table' not in self.config:
            return
        for codepoint, value in self.config['text_decode_table'].items():
            if isinstance(value, str):
                value = value.replace(r'\n', '\n')
                assert codepoint not in self.text_decode_table
                self.text_decode_table[codepoint] = value
                self.text_encode_table[value] = codepoint
                continue

            expansion = value['expansion']
            increment = value['increment']
            for i, character in enumerate(expansion):
                excodepoint = codepoint + (i*increment)
                assert excodepoint not in self.text_decode_table
                self.text_decode_table[excodepoint] = character
                self.text_encode_table[character] = excodepoint

    def decode(self, pointer, data=None):
        if data is None:
            data = self.data
        if isinstance(data, bytes):
            data = BytesIO(data)
        address = data.tell()
        data.seek(pointer)
        decoded = ''
        char_size = self.config['text_char_size']
        while True:
            value = data.read(char_size)
            if len(value) < char_size:
                decoded += '{EOF}'
                break
            value = int.from_bytes(value, byteorder=self.config['byteorder'])
            if value in self.text_decode_table:
                decoded += self.text_decode_table[value]
            else:
                word = ('{0:0>%sx}' % (char_size*2)).format(value)
                decoded += '{%s}' % word
            if value in self.config['text_terminators']:
                break
        self.log_read_data(pointer, data.tell())
        data.seek(address)
        return decoded

    def encode(self, text):
        original_text = text
        bytecode = b''
        char_size = self.config['text_char_size']
        byteorder = self.config['byteorder']
        encode_order = sorted(self.text_encode_table,
                              key=lambda w: (-len(w), w))
        while True:
            if not text:
                break
            value = None
            if text.startswith('{'):
                index = text.index('}')
                word = text[0:index+1]
                if word == '{EOF}':
                    break
                elif word in self.text_encode_table:
                    value = self.text_encode_table[word]
                else:
                    value = int(word[1:-1], 0x10)
                text = text[index+1:]
            else:
                for word in encode_order:
                    if '{' in word:
                        continue
                    if text.startswith(word):
                        value = self.text_encode_table[word]
                        text = text[len(word):]
                        break
            if value is None:
                raise Exception(f'Unable to encode "{text}".')
            bytecode += value.to_bytes(length=char_size,
                                       byteorder=byteorder)
        if value not in self.config['text_terminators']:
            print(f'WARNING: "{original_text}" not terminated properly.')
        return bytecode

    def get_text(self, value, instruction):
        raise NotImplementedError

    def read_variable_length(self, instruction):
        raise NotImplementedError

    def get_next_instruction(self, script, start_address=None):
        if start_address is None and script.instructions:
            end_address = script.end_address
            if end_address == self.data.tell():
                start_address = end_address
        if start_address == self.max_address:
            return None
        instruction = self.Instruction(script=script,
                                       start_address=start_address)
        return instruction

    def read_script(self, pointer):
        if self.scripts:
            #nearest = max({s for s in self.scripts.values()
            #               if s.pointer < pointer or s.pointer == pointer})
            nearest = max(s for s in self.scripts if s <= pointer.old_pointer)
            nearest = self.scripts[nearest]
            assert nearest.pointer != pointer
            for i in nearest.instructions:
                if i.start_address == pointer.converted:
                    a, b = nearest.split(pointer)
                    assert b.pointer == pointer
                    return b
        script = self.Script(pointer=pointer, parser=self)
        self.data.seek(pointer.converted)
        while True:
            instruction = self.get_next_instruction(script=script)
            if instruction is None or instruction.is_terminator:
                break
            if instruction.end_address in self.pointers:
                assert instruction.end_address not in self.future_joins
                pointer = self.pointers[instruction.end_address]
                self.future_joins[instruction.end_address] = script
                self.reserve_context(pointer, script.context)
                break
        return script

    def read_scripts(self):
        if self.scripts is None:
            self.scripts = {}
        self.future_joins = {}

        def join_futures(p):
            before = self.future_joins[p]
            after = self.scripts[p]
            while before.joined_after:
                if before.joined_after is after:
                    break
                before = before.joined_after
            #while after.joined_before:
            #    if after.joined_before is before:
            #        break
            #    after = after.joined_before
            if not (before.joined_after or after.joined_before):
                before.join(after)
            assert before.joined_after is after
            assert after.joined_before is before
            assert before.pointer < after.pointer

        while True:
            old_pointers = frozenset(self.pointers)
            updated = False
            for p, pointer in sorted(self.pointers.items()):
                if p in self.scripts:
                    continue
                if pointer not in self.script_pointers:
                    continue
                updated = True
                self.scripts[p] = self.read_script(pointer)
                if p in self.future_joins:
                    join_futures(p)
                if self.pointers != old_pointers:
                    break
            if not updated:
                break
        for p in self.future_joins:
            join_futures(p)

    def format_instruction(self, instruction):
        return str(instruction)

    def format_opcode(self, opcode):
        length = self.config['opcode_size'] * 2
        opcode = f'{opcode:x}'
        while len(opcode) % 2:
            opcode = f'0{opcode}'
        assert len(opcode) <= length
        return ('{0:<%s}' % length).format(opcode)

    def format_parameter(self, instruction, parameter_name):
        value = instruction.parameters[parameter_name]
        if isinstance(value, int):
            mask = instruction.manifest['fields'][parameter_name]['mask']
            while not mask & 1:
                mask >>= 1
            length = len(f'{mask:x}')
            if length < 2:
                length += 1
            parameter = ('{0:0>%sx}' % length).format(value)
        elif isinstance(value, bytes):
            if parameter_name in instruction.text_parameters:
                parameter = parameter_name
            else:
                parameter = ''.join(f'{c:0>2x}' for c in value)
        elif isinstance(value, tuple):
            parameter = '-'.join(f'{c:0>2x}' for c in value)
        elif isinstance(value, list):
            if not value:
                raise NotImplementedError
            parameter_list = []
            for v in value:
                if isinstance(v, int):
                    parameter_list.append(f'{v:x}')
                elif isinstance(v, bytes):
                    parameter_list.append(''.join(f'{c:0>2x}' for c in v))
                elif isinstance(v, tuple):
                    s = '-'.join(f'{c:0>2x}' for c in v)
                    parameter_list.append(s)
                else:
                    parameter_list.append(str(v))
            parameter = '&'.join(parameter_list)
        else:
            parameter = str(value)
        return parameter

    def format_pointer(self, pointer, format_spec=None):
        if not format_spec:
            format_spec = 'x'
        return ('@{0:%s}' % format_spec).format(pointer.pointer)

    def format_text(self, parameter_name, text):
        lines = text.split('\n')
        lines = [f'|{line}|' for line in lines]
        if parameter_name is not None:
            name_length = len(parameter_name)
            first_line = f'{parameter_name}: {lines[0]}'
        else:
            name_length = 0
            first_line = f'  {lines[0]}'
        other_lines = [('{0:%s}  {1}' % name_length).format('', line)
                       for line in lines[1:]]
        return '\n'.join([first_line] + other_lines)

    def update_format_length(self, instruction=None):
        lengths = []
        if instruction is not None:
            new_length = len(instruction.format)
            if not hasattr(self, 'format_length'):
                self.format_length = new_length
            if new_length <= self.format_length:
                return
            lengths.append(new_length)
        for script in self.scripts.values():
            for i in script.instructions:
                lengths.append(len(i.format))
        if not lengths:
            lengths = [0]
        mean = sum(lengths) / len(lengths)
        median = sorted(lengths)[len(lengths) >> 1]
        deviation = sum((l-median)**2 for l in lengths) / len(lengths)
        threshold = median + (2 * deviation)
        self.format_length = max(l for l in lengths if l <= threshold)

    def interpret_opcode(self, opcode, context):
        if context is None:
            context = self.config['default_context']
        opcode = int(opcode, 0x10)
        instructions = self.config['contexts'][context]['instructions']
        if opcode in instructions:
            return opcode
        return None

    def interpret_parameter(self, parameter,
                            opcode=None, parameter_name=None, manifest=None,
                            is_list=None, is_bytes=None):
        if manifest and is_list is None:
            is_list = manifest['fields'][parameter_name]['is_list']
        if manifest and is_bytes is None:
            is_bytes = manifest['fields'][parameter_name]['is_bytes']

        if is_bytes:
            parameter = parameter.replace(' ', '')
            assert len(parameter) % 2 == 0
            result = []
            while parameter:
                result.append(int(parameter[:2], 0x10))
                parameter = parameter[2:]
            return bytes(result)
        elif is_list:
            parameter = parameter.replace(',', '&')
            while ' &' in parameter or '& ' in parameter:
                parameter = parameter.replace(' &', '&')
                parameter = parameter.replace('& ', '&')
            parameter = parameter.split('&')
            return [self.interpret_parameter(
                p, opcode=opcode, parameter_name=parameter_name,
                manifest=manifest, is_list=False) for p in parameter]
        elif parameter.startswith('@'):
            return self.interpret_pointer(parameter)
        elif '-' in parameter[1:]:
            return tuple(
                    self.interpret_parameter(p, opcode=opcode,
                                             parameter_name=parameter_name,
                                             manifest=manifest, is_list=False)
                    for p in parameter.split('-'))
        else:
            try:
                return int(parameter, 0x10)
            except ValueError:
                return None

    def interpret_pointer(self, pointer):
        pointer = pointer.split('#')[0].strip()
        if pointer.startswith('@'):
            try:
                pointer = int(pointer[1:], 0x10)
                return self.get_tracked_pointer(pointer)
            except ValueError:
                return None

    def interpret_instruction(self, line, script=None, append=False):
        if script is not None:
            context = script.context
        else:
            context = self.config['default_context']
        line = line.split('#')[0].strip()
        if line.count(':') > 1:
            return None
        line_number = None
        if '.' in line:
            line_number, line = line.split('.')
            line_number = int(line_number.strip(), 0x10)
            line = line.strip()
        if line.count(':') == 0:
            assert line.startswith('@')
            script_pointer = int(line[1:], 0x10)
            joined_script = self.get_or_create_script(script_pointer)
            if script.joined_after is None:
                script.join(joined_script)
            assert script.joined_after == joined_script
            return True
        opcode, parameters = line.split(':')
        assert opcode.count('.') <= 1
        opcode = self.interpret_opcode(opcode.strip(), context)
        if opcode is None:
            return None
        manifest = self.config['contexts'][context]['instructions'][opcode]
        parameters = parameters.replace(' ', '').strip()
        if parameters:
            parameters = parameters.split(',')
        else:
            parameters = []

        if 'parameter_order' in manifest:
            parameter_order = list(manifest['parameter_order'])
        else:
            parameter_order = []
        while len(parameter_order) < len(parameters):
            parameter_order.append(None)
        assert len(parameter_order) == len(parameters)
        done_parameters = set()
        interpreted = {}
        for parameter_name, parameter in zip(parameter_order, parameters):
            if '=' in parameter:
                parameter_name, parameter = parameter.split('=', 1)
            if parameter_name is None:
                raise Exception(f'Unknown parameter: {line}')
            if parameter_name in interpreted:
                raise Exception(f'Parameter "{parameter_name}" out of order: '
                                f'{line}')
            interpreted[parameter_name] = self.interpret_parameter(
                    parameter, opcode, parameter_name, manifest)
            if interpreted[parameter_name] is None:
                raise Exception(f'Unable to interpret "{parameter_name}": '
                                f'{line}')
        parameters = interpreted

        i = self.Instruction(script=script, opcode=opcode,
                             parameters=parameters)
        if script and append is False and \
                script.instructions and script.instructions[-1] is i:
            script.instructions.pop()
            assert i not in script.instructions
        if line_number is not None:
            i.start_address = line_number
        return i

    def interpret_text(self, text, instruction):
        text = text.strip()
        for parameter_name in instruction.text_parameters:
            if text.startswith(f'{parameter_name}:'):
                text = text.split(':', 1)[1].strip()
                break
        else:
            parameter_name = None
        if not (text.startswith('|') and text.endswith('|')):
            return None
        text = text[1:-1]
        return instruction.update_text(text, parameter_name=parameter_name)

    def script_text_to_lines(self, script_text):
        lines = []
        for line in script_text.split('\n'):
            try:
                line = line.strip()
                if line.startswith('#'):
                    continue
                is_text = line.startswith('|') or line.endswith('|')
                if is_text:
                    previous = lines[-1]
                    if line.startswith('|') and previous.endswith('|'):
                        assert line.endswith('|')
                        new = f'{previous}{line}'.replace('||', '\n')
                        lines[-1] = new
                    else:
                        lines.append(line)
                    continue
                if '#' in line:
                    line = line.split('#')[0].strip()
                if not line:
                    continue
                line = line.replace(' ', '')
                if line.startswith('@'):
                    lines.append(line)
                    continue
                if '.' in line:
                    addr, inst = line.split('.')
                    addr = int(addr.strip(), 0x10)
                    lines.append(line)
                    continue
                previous = lines[-1]
                if '=' in previous and '=' in line:
                    new = f'{previous},{line}'
                    while ',,' in new:
                        new = new.replace(',,', ',')
                else:
                    new = f'{previous}{line}'
                lines[-1] = new
            except:
                raise Exception(f'Unable to interpret "{line}"')
        lines = [line.rstrip(',') for line in lines]
        return lines

    def get_or_create_script(self, pointer):
        if pointer in self.scripts:
            script = self.scripts[pointer]
        else:
            script = self.Script(pointer=self.get_tracked_pointer(pointer),
                                 parser=self)
            self.scripts[pointer] = script
        return script

    def import_script(self, script_text):
        current_script = None
        lines = self.script_text_to_lines(script_text)
        dialogue_text = []
        for line in lines:
            result = None
            if line.startswith('@'):
                assert ' ' not in line
                context = self.config['default_context']
                if '(' in line:
                    address, context = line.split('(')
                    assert context.endswith(')')
                    context = context[:-1]
                else:
                    address = line
                result = self.interpret_pointer(address)
                if result:
                    self.reserve_context(result, context)
            if line.startswith('|'):
                assert line.endswith('|')
                dialogue_text.append(line[1:-1])
                continue
            if dialogue_text:
                prev_instruction = current_script.instructions[-1]
                prev_instruction.update_text('\n'.join(dialogue_text))
                dialogue_text = []
            if result:
                current_script = self.get_or_create_script(result.pointer)
                current_script.truncate()
                assert current_script is self.scripts[result.pointer]
                continue
            if current_script:
                result = self.interpret_instruction(line, current_script,
                                                    append=True)
                if result is True:
                    # script is joined to next script
                    assert current_script.joined_after is not None
                    current_script = None
                    continue
                if isinstance(result, self.Instruction):
                    assert result.script is current_script
                    continue
            raise Exception(f'Unable to interpret "{line}"')

    def text_to_parameter_bytecode(self, parameter_name, instruction):
        raise NotImplementedError

    def variable_instruction_to_bytecode(self, instruction, header=b''):
        raise NotImplementedError

    def instruction_to_bytecode(self, instruction, convert_pointers=True):
        length = instruction.manifest['length']
        variable_length = False
        if isinstance(length, str) or \
                instruction.manifest['is_variable_length']:
            variable_length = True

        tracked = any(isinstance(p, TrackedPointer)
                      for p in instruction.parameters.values())
        if self.USE_BYTECODE_CACHE \
                and variable_length is False and not tracked:
            signature = instruction.signature
            assert signature is not None
            if signature in self.INSTRUCTION_BYTECODE_CACHE:
                return self.INSTRUCTION_BYTECODE_CACHE[signature]
        else:
            signature = None

        difference = (instruction.manifest['length'] -
                      instruction.manifest['opcode_size'])
        assert difference >= 0
        opcode = instruction.opcode << (difference * 8)
        opcode_mask = instruction.manifest['mask'] << (difference * 8)
        value = opcode & opcode_mask
        for verify in [False, True]:
            for parameter_name in instruction.manifest['parameter_order']:
                parameter = instruction.parameters[parameter_name]
                if isinstance(parameter, self.TrackedPointer):
                    if convert_pointers:
                        parameter = parameter.converted_smart
                    else:
                        parameter = self.convert_pointer(
                                parameter, repointed=False)
                field = instruction.manifest['fields'][parameter_name]
                mask = field['mask']
                if not isinstance(mask, int):
                    variable_length = True
                    continue
                if field['is_text']:
                    raise NotImplementedError
                if field['byteorder'] != 'big':
                    parameter = reverse_byte_order(parameter, mask=mask)
                parameter = mask_shift_left(parameter, mask)
                if field['compress_mask']:
                    parameter = mask_decompress(parameter, mask)
                if not verify:
                    value |= parameter
                else:
                    assert value & mask == parameter
        assert value & opcode_mask == opcode & opcode_mask
        bytecode = value.to_bytes(length=length, byteorder='big')
        if variable_length:
            return self.variable_instruction_to_bytecode(instruction, bytecode)

        if signature is not None:
            self.INSTRUCTION_BYTECODE_CACHE[signature] = bytecode
        return bytecode

    def script_to_bytecode(self, script):
        return b''.join(i.bytecode for i in script.instructions)

    def dump_all_scripts(self, header=None):
        if header is None:
            header = b''
        bytecode = BytesIO(header)

        done_scripts = set()
        warned = False
        for s in self.scripts.values():
            if hasattr(s.pointer, 'repointer'):
                comment = s.comment
                if comment is None:
                    comment = ''
                else:
                    comment = f'# {comment}'
                msg = f'Double dump: @{s.pointer.old_pointer:x}  {comment}'
                if not warned:
                    warn(msg.strip())
                    warned = True
                delattr(s.pointer, 'repointer')

        assert not any(hasattr(s.pointer, 'repointer')
                       for s in self.scripts.values())
        no_joined_before = {s for s in self.scripts.values()
                            if s.joined_before is None}
        chosen = None
        while True:
            if chosen is None:
                if not no_joined_before:
                    break
                chosen = min(no_joined_before, key=lambda s: s.pointer.pointer)
            assert chosen is not None
            assert chosen not in done_scripts
            assert chosen is self.scripts[chosen.pointer.old_pointer]
            bytecode.seek(0, SEEK_END)
            repointer = bytecode.tell() | chosen.pointer.virtual_address
            assert not hasattr(chosen.pointer, 'repointer')
            assert chosen is self.scripts[chosen.pointer.pointer]
            chosen.pointer.repointer = repointer
            if chosen.joined_before:
                before_pointer = chosen.joined_before.pointer.repointer
                before_length = chosen.joined_before.bytecode_length
                assert repointer-before_pointer == before_length
            assert bytecode.tell() == chosen.pointer.converted_repointer
            bytecode.write(chosen.bytecode)
            done_scripts.add(chosen)
            no_joined_before.discard(chosen)
            chosen = chosen.joined_after

        def dump_write_all():
            for s in self.scripts.values():
                bytecode.seek(s.pointer.converted_repointer)
                bytecode.write(s.bytecode)

        dump_write_all()
        for s in self.scripts.values():
            bytecode.seek(s.pointer.converted_repointer)
            script_bytecode = bytecode.read(s.bytecode_length)
            assert s.bytecode == script_bytecode

        bytecode.seek(0)
        result = bytecode.read()
        return result

    def to_bytecode(self):
        raise NotImplementedError


if __name__ == '__main__':
    config_filename, data_filename = argv[1:]
    p = Parser(config_filename)
