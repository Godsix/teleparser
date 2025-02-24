# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 08:47:59 2022

@author: 皓
"""
import os
import os.path as osp
import re
import logging
from glob import iglob
from enum import IntEnum
from functools import lru_cache
import autopep8
from javalang.parse import parse
from javalang.tree import (Node, 
                           CompilationUnit, ClassDeclaration,
                           FieldDeclaration, FormalParameter,
                           MethodDeclaration, BlockStatement,
                           Statement, IfStatement, ForStatement,
                           ReturnStatement, SwitchStatement,
                           StatementExpression, TryStatement,
                           LocalVariableDeclaration,
                           MethodInvocation, Assignment,
                           BasicType, ReferenceType, ClassCreator,
                           ForControl, BinaryOperation, TernaryExpression,
                           Cast, This, MemberReference, Literal)
try:
    from .common import STRUCT_CACHE, HEADER
    from .tools import get_struct_content, get_structures_content
    from .utils import name_convert_to_snake, save_code, lazy_property
except ImportError:
    from generater.common import STRUCT_CACHE, HEADER
    from generater.tools import get_struct_content, get_structures_content
    from generater.utils import name_convert_to_snake, save_code, lazy_property


TYPE_INFO = {
    'writeInt32': 'Int32ul',
    'writeInt64': 'Int64ul',
    'writeBool': 'TBool',
    'writeBytes': 'GreedyBytes',
    'writeByte': 'Byte',
    'writeString': 'TString',
    'writeByteArray': 'TBytes',
    'writeFloat': 'Single',
    'writeDouble': 'Double',
    'writeByteBuffer': 'TBytes',
    'readInt32': 'Int32ul',
    'readInt64': 'Int64ul',
    'readBool': 'TBool',
    'readBytes': 'GreedyBytes',
    'readByte': 'Byte',
    'readString': 'TString',
    'readByteArray': 'TBytes',
    'readFloat': 'Single',
    'readDouble': 'Double',
    'readByteBuffer': 'TBytes',
}

VECTOR_TYPE_INFO = {
    'serialize': '',
    'serializeInt': 'Int32ul',
    'serializeLong': 'Int64ul',
    'serializeString': 'TString',
    'deserialize': '',
    'deserializeInt': 'Int32ul',
    'deserializeLong': 'Int64ul',
    'deserializeString': 'TString',
}





PATTERN1 = re.compile(r"@constructor\((\w+), '(\w+)'(.*)\)")
PATTERN2 = re.compile(r"'sname'\s*/\s*Computed\(\s*'(\w+)'\s*\)")


FAIL_STR = '''    @constructor({cid}, '{sname}')
    def struct_{cid}(self):
        # TODO
        return Struct(
            'sname' / Computed('{sname}'),
            'signature' / Hex(Const({cid}, Int32ul)))'''


TODO_STR = '''    @constructor({cid}, '{sname}')
    def struct_{cid}(self):
        # TODO: {todo}
        return Struct(
            'sname' / Computed('{sname}'),
            'signature' / Hex(Const({cid}, Int32ul)))'''


SIMP_STR = '''    @constructor({cid}, '{sname}')
    def struct_{cid}(self):
        return [{content}]'''


FUNCTION_PATTERN = re.compile(r"^ +@.+\n +def (\w+)\(.+\)(?s:.+?)\n\n", re.M)


GDATA = {}

NAME_MAP = {('peer', 'user_id'): 'peer_user_id',
            ('title', 'text'): 'title_text',
            ('color', 'background_emoji_id'): 'background_emoji_id',
            ('question', 'text'): 'question_text',
            ('from_id', 'user_id'): 'from_user_id',
            ('from_id', 'channel_id'): 'from_channel_id',
            ('reply_to', 'reply_to_msg_id'): 'reply_to_msg_id',
            ('fwd_from', 'date'): 'fwd_from_date',
            ('fwd_from.from_id', 'user_id'): 'fwd_from_user_id',
            ('reply_to', 'reply_to_random_id'): 'reply_to_random_id',
            ('owner_id', 'user_id'): 'owner_user_id',
            ('stars', 'amount'): 'stars_amount',
            ('balance', 'amount'): 'balance_amount',
            ('sender_id', 'user_id'): 'sender_user_id',
            ('recipient_id', 'user_id'): 'recipient_user_id'}


class UserWrapper:
    def __init__(self, obj: Node):
        self.object = obj

    def __getattr__(self, name):
        if hasattr(self.object, name):
            return getattr(self.object, name)
        raise AttributeError(f"'ClassParser' object has no attribute '{name}'")

class UserCompilationUnit(UserWrapper):
    def __init__(self, path, encoding: str = "utf-8"):
        with open(path, 'rb') as f:
            c = f.read()
        super().__init__(parse(c))
        self.lines =[x for x in c.decode(encoding).splitlines()]
        self.path = path

    @lazy_property
    def package(self):
        return self.object.package  # pylint: disable=E1101

    @lazy_property
    def imports(self):
        return self.object.imports  # pylint: disable=E1101

    @lazy_property
    def types(self):
        return self.object.types  # pylint: disable=E1101
    
    @lazy_property
    def class_list(self) -> list:
        return [x for x in self.types if isinstance(x, ClassDeclaration)]

    def get_line(self, obj: Node):
        if not (position := obj.position):
            return position
        return self.lines[position.line - 1][position.column - 1:]

class UserClassDeclaration(UserWrapper):
    def __init__(self,
                 declaration: ClassDeclaration,
                 outer: UserWrapper):
        super().__init__(declaration)
        if isinstance(outer, UserCompilationUnit):
            self.c_unit = outer
            self.outer = None
        elif isinstance(outer, UserClassDeclaration):
            self.c_unit = outer.c_unit
            self.outer = outer
        else:
            raise TypeError("'outer' must be a UserCompilationUnit or UserClassDeclaration")
        self.imports = {}
        self.outer_imports = {}
        for item in self.c_unit.imports:
            item_path = item.path
            self.imports[item_path.split('.')[-1]] = item_path
        if self.outer:
            fqn = self.outer.fqn
            for item in self.outer.class_list:
                item_name = item.name
                self.outer_imports[item_name] = f'{fqn}.{item_name}'

    @lazy_property
    def package(self):
        return self.c_unit.package.name

    @lazy_property
    def name(self):
        return self.object.name

    @lazy_property
    def body(self):
        return self.object.body

    @lazy_property
    def fields(self):
        return self.object.fields

    @lazy_property
    def methods(self):
        return self.object.methods
    @lazy_property
    def fqn(self):
        '''类的全限定名(Fully Qualified Name, FQN)'''
        if self.outer:
            return f'{self.outer.fqn}.{self.name}'
        else:
            return f'{self.package}.{self.name}'

    @lazy_property
    def extends(self):
        if not (extends := self.object.extends):
            return None
        if extends.sub_type:
            v = f'{extends.name}.{extends.sub_type.name}'
        else:
            v = extends.name
        return self.get_fqn(v)

    @lazy_property
    def class_list(self) -> list:
        return [x for x in self.body if isinstance(x, ClassDeclaration)]

    @lru_cache()
    def get_fqn(self, value: str):
        if '.' not in value:
            if value in self.outer_imports:
                return self.outer_imports[value]
            if value in self.imports:
                return self.imports[value]
        else:
            c1, c2 = value.split('.')
            if c1 in self.imports:
                return f'{self.imports[c1]}.{c2}'
        return f'{self.package}.{value}'

    @lru_cache()
    def get_value(self, name: str):
        for field in self.fields:
            declarators = field.declarators
            # type_name = field.type.name
            for declarator in declarators:
                if declarator.name == name:
                    value = declarator.initializer.value
                    if value:
                        return eval(value) # pylint: disable=W0123
                    else:
                        return value
    def get_line(self, obj: Node):
        return self.c_unit.get_line(obj)


def rename_struct(content: str, name):
    def sub_func1(match):
        return f"@constructor({match.group(1)}, '{name}'{match.group(3)})"
    content = PATTERN1.subn(sub_func1, content, 1)[0]

    def sub_func2(match):
        return match.group(0).replace(match.group(1), name)
    content = PATTERN2.subn(sub_func2, content, 1)[0]
    return content


def get_stream_type(member, name=''):
    datatype = TYPE_INFO[member]
    if datatype == 'Int32ul' and name.endswith('date'):
        return 'TTimestamp'
    return datatype


class Tag(IntEnum):
    VECTOR_START = 1
    VECTOR_CONTENT = 2
    VECTOR_END = 3
    FLAGS_TAG = 4
    FLAGS_GAP = 5


class MethodType(IntEnum):
    WRITE = 1
    READ = 2
    TLDES = 3

class BaseParser:
    LOG = None

    def __init__(self, level=logging.INFO):
        self.logger = logging.getLogger(self.LOG)
        self.init_logger(self.logger, level)
        self.logger_level = level

    @classmethod
    def init_logger(cls, logger, level):
        if not logger.handlers:
            # logger.handlers.clear()
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.setLevel(level)

    @classmethod
    def is_statement_expression(cls, obj):
        return isinstance(obj, StatementExpression)

    @classmethod
    def is_block_statement(cls, obj):
        return isinstance(obj, BlockStatement)

    @classmethod
    def is_local_variable(cls, obj):
        return isinstance(obj, LocalVariableDeclaration)

    @classmethod
    def is_for_statement(cls, obj):
        return isinstance(obj, ForStatement)

    @classmethod
    def is_switch_statement(cls, obj):
        return isinstance(obj, SwitchStatement)

    @classmethod
    def is_if_statement(cls, obj):
        return isinstance(obj, IfStatement)

    @classmethod
    def is_return_statement(cls, obj):
        return isinstance(obj, ReturnStatement)

    @classmethod
    def is_try_statement(cls, obj):
        return isinstance(obj, TryStatement)

    @classmethod
    def is_method_invocation(cls, obj):
        return isinstance(obj, MethodInvocation)

    @classmethod
    def is_assignment(cls, obj):
        return isinstance(obj, Assignment)

    @classmethod
    def is_basic_type(cls, obj):
        return isinstance(obj, BasicType)

    @classmethod
    def is_reference_type(cls, obj):
        return isinstance(obj, ReferenceType)

    @classmethod
    def is_member_reference(cls, obj):
        return isinstance(obj, MemberReference)

    @classmethod
    def is_for_control(cls, obj):
        return isinstance(obj, ForControl)

    @classmethod
    def is_binary_operation(cls, obj):
        return isinstance(obj, BinaryOperation)

    @classmethod
    def is_cast(cls, obj):
        return isinstance(obj, Cast)

    @classmethod
    def is_this(cls, obj):
        return isinstance(obj, This)

    @classmethod
    def is_literal(cls, obj):
        return isinstance(obj, Literal)

    @classmethod
    def is_ternary_expression(cls, obj):
        return isinstance(obj, TernaryExpression)

    @classmethod
    def is_class_creator(cls, obj):
        return isinstance(obj, ClassCreator)

def get_single(text:str):
    if text.endswith('ies'):
        result = f'{text[:-3]}y'
    elif text.endswith('s'):
        result = text[:-1]
    else:
        result = text
    return result


def get_struct_name(fqn: str):
    fqns = fqn.split('.')
    *_, s1, name = fqns
    if name.startswith('TL_'):
        cname = name[3:]
    else:
        cname = name
    if s1.startswith('TL_'):
        prefix = s1[3:]
        cnamel = cname.lower()
        single = get_single(prefix)
        if cnamel.startswith(prefix) or cnamel.startswith(single):
            sname = cname
        else:
            sname = f'{prefix}_{cname}'
    else:
        sname = cname
    return name_convert_to_snake(sname)

class ClassParser(BaseParser):
    LOG = 'ClassParser'

    def __init__(self, fqn, java_parser: 'JavaParser', level=logging.INFO):
        super().__init__(level)
        self.java_parser = java_parser
        self.object = self.get_class(fqn)
        self.fqn = self.object.fqn
        self.cid = self.cid_info.get(self.fqn)
        name = self.object.name
        assert name, f'parse {self.fqn} name error'
        self.name = name
        self.struct_name = get_struct_name(self.fqn)
        self.fields = self.get_fields(self.object)
        self.methods = self.get_methods(self.object, False)
        self.info = {}
        self.info['cid'] = self.cid
        self.info['sname'] = self.struct_name
        self.struct = self.info.setdefault('struct', {})
        self.switch = self.info.setdefault('switch', [])
        self.flags = self.info.setdefault('flags', {})
        self.vector = []
        self.current_method = None
        self.fields_context = {}
        self.flags_info = {}  # ('flags', 4)=>('flags', 'isPublic', '4', 'is_public', 4)



    def __getattr__(self, name):
        if hasattr(self.java_parser, name):
            return getattr(self.java_parser, name)
        raise AttributeError(f"'ClassParser' object has no attribute '{name}'")

    def get_cid(self, fqn):
        return self.cid_info.get(fqn)

    def get_fqn(self, name: str):
        if name.startswith('org.telegram'):
            return name
        return self.object.get_fqn(name)

    def set_struct(self, name: str, value: str):
        self.struct[name] = value

    def add_switch(self, name, value):
        self.struct[name] = value

    def parse(self):
        self.logger.debug('Parse class %s', self.name)
        has_struct = False
        has_switch = False
        if self.cid:
            if 'serializeToStream' in self.methods:
                has_struct = self.parse_serialize_to_stream()
            if has_struct is False and 'readParams' in self.methods:
                has_struct = self.parse_read_param()
        if self.fqn in self.structure_info:
            has_switch = self.parse_deserialize()
        if not has_struct and not has_switch:
            msg = f'Class {self.name} has no method parsed.'
            if self.strict:
                raise NotImplementedError(msg)
            else:
                self.info['todo'] = 'no method'
                self.logger.error(msg)
        return (has_struct and has_switch)

    def parse_vector(self):
        '''parse vector 0x1cb5c415'''
        data = self.vector[1]
        if self.is_local_variable(data):
            data_name = data.declarators[0].initializer.qualifier
        elif self.is_statement_expression(data):
            expression = data.expression
            if self.is_assignment(expression):
                data_name = expression.value.qualifier
            elif self.is_method_invocation(expression):
                data_name = expression.arguments[0].qualifier
            else:
                raise TypeError(type(expression))
        else:
            return None
        for_item = self.vector[-1]
        statement = for_item.body.statements[0]
        if (self.is_statement_expression(statement) and
            self.is_method_invocation(statement.expression) and
            statement.expression.qualifier == 'stream'):
            member = statement.expression.member
            data_type = get_stream_type(member)
        else:
            data_type, is_array = self.parse_field_type(data_name)
            if is_array is False:
                raise TypeError(data_name)
            if data_type in ('int', 'str', 'bytes'):
                for_member = for_item.body.statements[0].expression.member
                data_type = get_stream_type(for_member)
            else:
                # raise ValueError(f'data_type: {data_type}')
                pass  # pylint: disable=E275
        struct_type = f"self.vector({data_type}, '{data_name}')"
        dname = name_convert_to_snake(data_name)
        return (dname, struct_type)
        
    def parse_class_type(self, data_name, data_type):
        fqn = self.get_fqn(data_type)
        if fqn in self.structure_info:
            sname = self.structure_info[fqn]['name']
            dname = name_convert_to_snake(data_name)
            struct_type = f"self.{sname}_structures('{dname}')"
            return struct_type
        data_class = self.get_class(fqn)
        if data_class is not None:
            for item in self.get_extends_list(data_class):
                if item in self.structure_info:
                    sname = self.structure_info[item]['name']
                    dname = name_convert_to_snake(data_name)
                    struct_type = f"self.{sname}_structures('{dname}')"
                    break
            else:
                cid = self.java_parser.get_cid(data_class)
                if cid is None:
                    raise TypeError(f'Class {fqn} has not constructor.')
                struct_type = f"self.struct_{cid}()"
        else:
            if data_type == 'Integer':
                if data_name.endswith('date'):
                    return 'TTimestamp'
                else:
                    return 'Int32ul'
            elif data_type == 'Long':
                return 'Int64ul'
            elif data_type == 'String':
                return 'TString'
            elif data_type == 'byte':
                return 'TBytes'
            raise ValueError(f'{data_name}, {data_type}')
        return struct_type

    def get_field_type(self, field_name, class_name=None):
        if class_name is None:
            fields = self.fields
        else:
            fqn = self.get_fqn(class_name)
            fields = self.java_parser.get_fields(fqn)
        if fields is None:
            self.logger.error('get_field_type: fields is None: %s', class_name)
            return None
        field = fields.get(field_name)
        if field is None:
            self.logger.error('get_field_type: can not find field %s',
                              field_name)
            return None
        field_type = field.type.name
        return field_type
    
    def parse_type(self, obj: str | FieldDeclaration | FormalParameter):
        if isinstance(obj, str):
            field = self.fields.get(obj)
            if field is None:
                self.logger.error('parse_field: can not find field %s', obj)
                return None
        else:
            field = obj
        if not isinstance(field, (FieldDeclaration, FormalParameter)):
            raise TypeError(type(field))

        if (is_array := (field.type.name == 'ArrayList')):
            field = field.type.arguments[0]
        try:
            if (sub_type := field.type.sub_type.name):
                full_type = f'{field.type.name}.{sub_type}'
            else:
                full_type = field.type.name
        except AttributeError:
            full_type = field.type.name
        return (full_type, is_array)

    def parse_field_type(self, name):
        if name is None:
            self.logger.error('parse_field_type: name is None')
            return None
        if '.' in name:
            name_list = name.split('.')
            class_name = None
            for item in name_list:
                class_name = self.get_field_type(item, class_name)
                if class_name is None:
                    self.logger.error('parse_field_type: field parse fail: %s',
                                      name)
                    return None
            data_name = name.replace('.', '_')
            return (self.parse_class_type(data_name, class_name), False)
        else:
            if (ret := self.parse_type(name)) is not None:
                full_type, is_array = ret
                return (self.parse_class_type(name, full_type), is_array)
            else:
                return None
 
    def parse_statement_expression_r(self, statement):
        expression = statement.expression
        if self.is_assignment(expression):
            memberl = expression.expressionl.member
            value = expression.value
            if self.is_method_invocation(value):
                qualifier = value.qualifier
                member = value.member
                if qualifier == 'stream':
                    sname = memberl
                    stype = get_stream_type(member, sname)
                    return (sname, stype)
                elif qualifier == 'Vector':
                    sname = memberl
                    stype = None
                    if member == 'deserialize':
                        stype = value.arguments[1]
                        stype_member = stype.expression.member
                        if (stype_qualifier := stype.expression.qualifier):
                            arg1_member = f'{stype_qualifier}.{stype_member}'
                        else:
                            arg1_member = stype_member
                        stype = self.parse_class_type(sname, arg1_member)
                        if not stype:
                            raise ValueError(f'Parse java type error: {arg1_member}')
                    elif member == 'deserializeInt':
                        stype = 'Int32ul'
                    elif member == 'deserializeLong':
                        stype = 'Int64ul'
                    elif member == 'deserializeString':
                        stype = 'TString'
                    if stype:
                        stype = f"self.vector({stype}, '{sname}')"
                        return (sname, stype)
                elif member == 'TLdeserialize':
                    sname = memberl
                    stype = name_convert_to_snake(qualifier)
                    return (sname, f"self.{stype}_structures('{sname}')")
            elif self.is_binary_operation(value):
                member = value.operandl.operandl.member
                mask = value.operandl.operandr.value
                self.add_flag_value(member, memberl, mask)
                return Tag.FLAGS_TAG

    def add_flag_value(self, val_name, name, value, prefix=None):
        '''self.add_flag_value('flags', 'isPublic', '4')'''
        # ('flags', 4)=>('flags', 'isPublic', '4', 'is_public', 4)
        mask_value = eval(value) # pylint: disable=W0123
        key = (val_name, mask_value)
        if key not in self.flags_info:
            sname = name_convert_to_snake(name)
            if sname.startswith('is_') or sname.startswith('has_'):
                pname = sname
            else:
                if not prefix:
                    prefix = 'has'
                    if name in self.fields_context:
                        obj_type, _ = self.fields_context[name]
                        if obj_type.lower() == 'boolean':
                            prefix = 'is'
                ppname = f'{prefix}_{sname}'
                for item in self.flags_info.values():
                    if item[0] == val_name and item[3] == ppname:
                        if prefix == 'is':
                            prefix = 'has'
                        else:
                            prefix = 'is'
                        break
                pname = f'{prefix}_{sname}'
            self.flags_info[key] = (val_name, name, value, pname, mask_value)
        return self.flags_info[key]

    def parse_if_statement_r(self, statement):
        result = []
        condition = statement.condition
        operandl = condition.operandl
        if self.is_binary_operation(operandl):
            condition_member = operandl.operandl.member
            condition_value = operandl.operandr.value
            then_statements = statement.then_statement.statements
            result_list = self.parse_blocks_r(then_statements)
            c_m = condition_member
            for item in result_list:
                sname, dtype = item
                flag = self.add_flag_value(c_m, sname, condition_value, prefix='has')
                struct_type = f'If(this.{flag[0]}.{flag[3]}, {dtype})'
                result.append((sname, struct_type))
            return result

    def is_line_w_0(self, line: Node):
        if self.vector:
            return {'object': line}
        else:
            return False

    def parse_line_w_0(self, info: dict):
        line = info['object']
        self.vector.append(line)
        if self.is_for_statement(line):
            res = self.parse_vector()
            if res is None:
                raise ValueError(line)
            self.vector.clear()
            return res
        else:
            return Tag.VECTOR_CONTENT

    def is_line_w_1(self, line: Node):
        if self.is_statement_expression(line) and self.is_method_invocation(line.expression):
            return {'object': line.expression}
        return False


    def parse_line_w_1(self, info: dict):
        '''stream.writeInt32(constructor);'''
        line = info['object']
        qualifier = line.qualifier
        member = line.member
        arguments = line.arguments
        if qualifier in self.fields_context:
            is_array, _ = self.fields_context[qualifier]
        else:
            is_array = False
        if qualifier == 'stream' and member in TYPE_INFO:
            argument = arguments[0]
            arg0 = argument
            if self.is_ternary_expression(arg0):
                if self.is_literal(arg0.if_false):
                    arg0 = arg0.if_true
                else:
                    arg0 = arg0.if_false
            if self.is_cast(arg0):
                arg0 = arg0.expression
            if self.is_this(arg0):
                arg0 = arg0.selectors[0]
            if self.is_method_invocation(arg0):
                if arg0.member == 'get':
                    struct_name = get_single(arg0.qualifier)
                else:
                    struct_name = arg0.qualifier
                struct_name = name_convert_to_snake(struct_name)
                struct_type = get_stream_type(member, struct_name)
                return (struct_name, struct_type)
            elif self.is_member_reference(arg0):
                if arg0.qualifier:
                    if arg0.qualifier == arg0.member:
                        struct_name = arg0.member
                    elif (arg0.qualifier, arg0.member) in NAME_MAP:
                        struct_name = NAME_MAP[(arg0.qualifier, arg0.member)]
                    else:
                        struct_name = arg0.member
                        GDATA[(arg0.qualifier, arg0.member)] = None
                else:
                    struct_name = name_convert_to_snake(arg0.member)
                data_type = get_stream_type(member, struct_name)
                if struct_name == 'constructor':
                    struct_name = 'signature'
                    field = self.fields['constructor']
                    struct_value = field.declarators[0].initializer.value
                    struct_index = int(struct_value, 16)
                    struct_text = f'0x{struct_index:08x}'
                    struct_type = f'Hex(Const({struct_text}, {data_type}))'
                else:
                    struct_type = data_type
                return (struct_name, struct_type)
            elif self.is_literal(arg0):
                arg0_value = eval(arg0.value)   # pylint: disable=W0123
                if arg0_value == 0x1cb5c415:
                    return Tag.VECTOR_START
                elif arg0_value == '':
                    data_type = get_stream_type(member)
                    return ('restriction_reason', data_type)
                elif arg0_value == 0:
                    data_type = get_stream_type(member)
                    return ('_reserve', data_type)
                else:
                    raise ValueError(f'{arg0.value}')
            else:
                raise TypeError(str(argument))
        elif qualifier == 'Vector' and member in VECTOR_TYPE_INFO:
            data_type = VECTOR_TYPE_INFO[member]
            argument = arguments[-1]
            data_name = argument.member
            dname = name_convert_to_snake(data_name)
            if not data_type:
                data_type, is_array = self.parse_field_type(data_name)
                if is_array is False:
                    raise TypeError(data_name)
            if data_type:
                struct_type = f"self.vector({data_type}, '{data_name}')"
                return (dname, struct_type)
            else:
                raise TypeError(line)
        elif not qualifier and member == 'writeAttachPath':
            return ('attach_path', 'TString')
        elif member == 'serializeToStream':
            struct_type, is_array = self.parse_field_type(qualifier)
            struct_name = name_convert_to_snake(qualifier.replace('.', '_'))
            return (struct_name, struct_type)
        elif is_array and member == 'get':
            assert line.selectors[0].member == 'serializeToStream'
            struct_name = name_convert_to_snake(get_single(qualifier))
            full_type, is_array = self.parse_type(qualifier)
            struct_type = self.parse_class_type(struct_name, full_type)
            return (struct_name, struct_type)
        else:
            raise TypeError(line)

    def is_line_w_2(self, line: Node):
        try:
            condition = line.condition
            operandl = condition.operandl
            operandr = condition.operandr
            assert operandr.value == 'null'
            name = operandl.member
            expression = line.then_statement.statements[0].expression
            flag = expression.expressionl.member
            value = expression.value.operandr.value
            info = {'flag' : flag, 'name': name, 'value': value}
            return info
        except Exception:
            return False

    def parse_line_w_2(self, info: dict):
        '''
            if (username == null) {
                flags = flags & ~8;
            }
        '''
        self.add_flag_value(info['flag'], info['name'], info['value'])
        return Tag.FLAGS_TAG

    def is_line_w_3(self, line: Node):
        try:
            condition = line.condition
            operandl = condition.operandl
            operandr = condition.operandr
            assert operandr.value == 'null'
            flag = operandl.member
            expr_true = line.then_statement.statements[0].expression
            name_true = expr_true.expressionl.member
            value_true = expr_true.value.value
            if line.else_statement:
                expr_false = line.else_statement.statements[0].expression
                name_false = expr_false.expressionl.member
                value_false = expr_false.value.value
                assert name_true == name_false
                assert value_true == value_false
            info = {'flag' : name_true, 'name': flag, 'value': value_true}
            return info
        except Exception:
            return False

    def parse_line_w_3(self, info: dict):
        '''
            if (storyItem != null) {
                flags |= 1;
            } else {
                flags &= ~1;
            }
        '''
        self.add_flag_value(info['flag'], info['name'], info['value'])
        return Tag.FLAGS_TAG

    def is_line_w_4(self, line: Node):
        if self.is_statement_expression(line) and self.is_assignment(line.expression):
            return {'object': line.expression}
        return False

    def parse_line_w_4(self, info: dict):
        '''flags = self ? (flags | 1024) : (flags &~ 1024);'''
        line = info['object']
        member = line.expressionl.member
        value = line.value
        if self.is_ternary_expression(value):
            if_false = value.if_false.operandr.value
            if_true = value.if_true.operandr.value
            assert if_false == if_true, f'{if_false} ≠ {if_true}'
            condition = value.condition
            if self.is_member_reference(condition):
                condition_member = condition.member
            elif self.is_binary_operation(condition):
                member_ref = condition
                for i in range(3):
                    if self.is_binary_operation(member_ref):
                        member_ref = member_ref.operandl
                    else:
                        break
                condition_member = member_ref.member
            else:
                raise ValueError(type(condition))
            self.add_flag_value(member, condition_member, if_true)
            return Tag.FLAGS_TAG
        elif self.is_class_creator(value):
            return Tag.FLAGS_GAP
        else:
            raise ValueError(line)

    def is_line_w_5(self, line: Node):
        try:
            condition = line.condition
            operandl = condition.operandl
            operandr = condition.operandr
            assert condition.operator == '!='
            assert operandr.value == '0'
            name = operandl.operandl.member
            value = operandl.operandr.value
            then_statement = line.then_statement
            info = {'name' : name, 'value': value}            
        except Exception:
            return False
        info['result'] = self.parse_block(then_statement)
        return info

    def parse_line_w_5(self, info: dict):
        '''
            if ((flags & 1073741824) != 0) {
                emoji_status.serializeToStream(stream);
            }
        '''
        result = []
        for item in info['result']:
            sname, dtype = item
            flag = self.add_flag_value(info['name'], sname, info['value'], prefix='has')
            stype = f'If(this.{flag[0]}.{flag[3]}, {dtype})'
            result.append((sname, stype))
        return result

    def is_line_w_6(self, line: Node):
        try:
            condition = line.condition
            operandl = condition.operandl
            operandr = condition.operandr
            assert condition.operator == '!='
            assert operandr.value == 'null'
            name = operandl.member
            then_statement = line.then_statement
            value = None
            for item in self.flags_info.values():
                if item[1] == name:
                    value = item
            if not value:
                return False
            info = {'flag' : value[0], 'name': value[3]}            
        except Exception:
            return False
        info['result'] = self.parse_block(then_statement)
        return info

    def parse_line_w_6(self, info: dict):
        '''
            if (about != null) {
                stream.writeString(about);
            }
        '''
        result = []
        for item in info['result']:
            sname, dtype = item
            stype = f'If(this.{info["flag"]}.{info["name"]}, {dtype})'
            result.append((sname, stype))
        return result

    def is_line_w_7(self, line: Node):
        if self.is_if_statement(line):
            return {'object': line}
        return False

    def parse_line_w_7(self, info: dict):
        statement = info['object']
        condition = statement.condition
        operandl = condition.operandl
        operandr = condition.operandr
        if self.is_literal(operandr) and operandr.value == 'null':
            return self.parse_block(statement.then_statement)
        elif condition.operator == 'instanceof':
            return self.parse_block(statement.then_statement)
        else:
            raise ValueError(statement)

    def parse_blocks_w(self, blocks: list):
        result = []
        for index, item in enumerate(blocks):
            res = None
            for i in range(36):
                func1 = getattr(self, f'is_line_w_{i}', None)
                if func1 is None:
                    break
                func2 = getattr(self, f'parse_line_w_{i}')
                if (info := func1(item)):
                    # print(index, i, info)
                    res = func2(info)
                    break
            if res is None:
                raise ValueError(item)
            elif isinstance(res, list):
                result.extend(res)
            elif isinstance(res, tuple):
                result.append(res)
            elif res == Tag.VECTOR_START:
                self.vector.append(item)
            elif res == Tag.FLAGS_TAG:
                continue
            elif res == Tag.FLAGS_GAP:
                continue
        return result

    def parse_blocks_r(self, blocks):
        result = []
        for item in blocks:
            if self.is_statement_expression(item):
                res = self.parse_statement_expression_r(item)
                if res is None:
                    raise ValueError(repr(item))
                if res == Tag.FLAGS_TAG:
                    continue  # pylint: disable=E275
                result.append(res)
            elif self.is_local_variable(item):
                raise TypeError('local_variable')
            elif self.is_for_statement(item):
                raise TypeError('for_statement')
            elif self.is_if_statement(item):
                res = self.parse_if_statement_r(item)
                if res is None:
                    raise ValueError(repr(item))
                result.extend(res)
        return result

    def parse_blocks_d(self, blocks):
        for item in blocks:
            if self.is_switch_statement(item):
                switch_member = item.expression.member
                assert switch_member == 'constructor', 'Switch not constructor'
                for subitem in item.cases:
                    if len(subitem.case) == 0:
                        continue
                    case_expr = subitem.case[0]
                    error = None
                    if self.is_literal(case_expr):
                        cid_value = case_expr.value
                        self.switch.append(f'0x{eval(cid_value):08x}')
                    elif self.is_member_reference(case_expr):
                        case_qualifier = case_expr.qualifier
                        case_member = case_expr.member
                        if case_member == 'constructor':
                            case_fqn = self.object.get_fqn(case_qualifier)
                            if (case_cid := self.get_cid(case_fqn)):
                                self.switch.append(case_cid)
                            else:
                                error = f'Can not find cid of class {case_qualifier}'
                        else:
                            error = f'Case member is not constructor but {case_member}'
                    else:
                        error = f'case_expr is illigal type: {type(case_expr).__name__}'
                    if error:
                        raise TypeError(error)
                return True
            elif self.is_local_variable(item):
                continue  # pylint: disable=E275
            elif self.is_return_statement(item):
                continue  # pylint: disable=E275
            elif self.is_if_statement(item):
                continue  # pylint: disable=E275
            elif self.is_statement_expression(item):
                continue  # pylint: disable=E275
            else:
                raise TypeError(f'Unknow type:{type(item).__name__}')
        # self.logger.error('class %s TLdeserialize contain not switch',
        #                   self.name)
        return False

    def parse_serialize_to_stream(self):
        assert (not self.vector)
        method = self.methods['serializeToStream']
        self.flags_info.clear()
        self.struct.clear()
        self.set_struct('sname',
                        f"Computed('{self.struct_name}')")
        for k, v in self.fields.items():
            self.fields_context[k] = self.parse_type(v)
        for item in method.parameters:
            self.fields_context[item.name] = self.parse_type(item)
        self.current_method = MethodType.WRITE
        result = self.parse_block(method)
        self.current_method = None
        self.fields_context.clear()
        self.flags.clear()
        for k, v in self.flags_info.items():
            fn, _, _, mn, val = v 
            flag = self.flags.setdefault(fn, {})
            flag[mn] = val
        for item in result:
            self.set_struct(*item)
        # print(self.flags)
        for k in self.flags:
            try:
                self.struct[k] = f'FlagsEnum({self.struct[k]}'
            except KeyError:
                return False
        return True

    def parse_read_param(self):
        assert (not self.vector)
        method = self.methods['readParams']
        self.flags_info.clear()
        self.struct.clear()
        self.set_struct('sname',
                        f"Computed('{self.struct_name}')")
        self.set_struct('signature',
                        f'Hex(Const({self.cid}, Int32ul))')
        for k, v in self.fields.items():
            self.fields_context[k] = self.parse_type(v)
        for item in method.parameters:
            self.fields_context[item.name] = self.parse_type(item)
        self.current_method = MethodType.READ
        result = self.parse_block(method)
        self.current_method = None
        self.fields_context.clear()
        self.flags.clear()
        for k, v in self.flags_info.items():
            fn, _, _, mn, val = v 
            flag = self.flags.setdefault(fn, {})
            flag[mn] = val
        for item in result:
            self.set_struct(*item)
        for k in self.flags:
            self.struct[k] = f'FlagsEnum({self.struct[k]}'
        return True

    def parse_deserialize(self):
        assert (not self.vector)
        method = self.structure_info[self.fqn]['method']
        for k, v in self.fields.items():
            self.fields_context[k] = self.parse_type(v)
        for item in method.parameters:
            self.fields_context[item.name] = self.parse_type(item)
        self.current_method = MethodType.TLDES
        self.parse_block(method)
        self.current_method = None
        self.fields_context.clear()
        return True
    
    def parse_block(self, obj: MethodDeclaration | BlockStatement | TryStatement):
        if isinstance(obj, MethodDeclaration):
            body = obj.body
        elif self.is_block_statement(obj):
            body = obj.statements
        elif self.is_try_statement(obj):
            body = obj.block
        else:
            # raise TypeError(f'Unknown type: {type(obj).__name__}: {obj}')
            body = [obj]
        if self.current_method == MethodType.WRITE:
            result = self.parse_blocks_w(body)
        elif self.current_method == MethodType.READ:
            result = self.parse_blocks_r(body)
        elif self.current_method == MethodType.TLDES:
            result = self.parse_blocks_d(body)
        else:
            result = None
        return result

    def generate(self):
        ret = self.parse()
        if ret is None:
            return None
        if not self.info:
            self.logger.error('Class %s parse failed', self.name)
            return None
        result = []
        if self.struct:
            if len(self.struct) == 2:
                result.append(SIMP_STR.format_map({'cid': self.info['cid'],
                                                   'sname': self.info['sname'],
                                                   'content': ''}))
            elif len(self.struct) == 3 and not self.flags:
                item = list(self.struct.items())[2]
                content = f"'{item[0]}' / {item[1]}"
                result.append(SIMP_STR.format_map({'cid': self.info['cid'],
                                                   'sname': self.info['sname'],
                                                   'content': content}))

            else:
                # if 'sname' in self.struct:
                #     del self.struct['sname']
                # if 'signature' in self.struct:
                #     del self.struct['signature']
                content = get_struct_content(self.info)
                if len(self.flags) > 0:
                    content = autopep8.fix_code(content,
                                                options={'max_line_length': 512})
                    if content.startswith('@'):
                        content = '\n'.join(f'    {x}' if x else x for x in content.split('\n'))
                result.append(content)
        if self.switch:
            result.append(get_structures_content(self.info))
        return result


class JavaParser(BaseParser):
    LOG = 'JavaParser'

    def __init__(self, directory, cached=None, level=logging.INFO, strict=False):
        super().__init__(level)
        self.directory = osp.realpath(directory)
        self.cache = {}
        self.strict = strict
        if cached and osp.isdir(cached):
            cached_dir = cached
        else:
            cached_dir = STRUCT_CACHE
        if osp.isdir(cached_dir):
            for path in iglob(osp.join(cached_dir, '*')):
                basename = osp.basename(path)
                with open(path, encoding='utf-8') as f:
                    c = f.read()
                self.cache[eval(basename)] = c

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, value):
        path = osp.join(value, 'TLRPC.java')
        assert osp.isfile(path), f"Not found TLRPC file in {value}"
        self.java_info = {}  # <path, UserCompilationUnit>
        self.class_info = {}  # <fqn, UserClassDeclaration>
        self.tlobj_info = {}  # <fqn, UserClassDeclaration>
        self.cid_info = {}
        self.structure_info = {} # <fqn, dict>
        self.LAYER = None  # pylint: disable=C0103
        self.logger.debug("Parsing %s", osp.basename(path))
        tree = UserCompilationUnit(path)
        package = tree.package.name  # 获取包名
        self.java_info[path] = tree
        # 获取包名下的其他文件
        regex = re.compile(f'^{package}\.(.+)$', re.M)
        for item in tree.imports:
            java_path = item.path
            if not (m := regex.fullmatch(java_path)):
                continue
            relpath = m.group(1).replace('.', os.sep)
            item_path = osp.join(value, f'{relpath}.java')
            if not osp.isfile(item_path):
                self.logger.warning("Not found %s", item_path)
                continue
            self.logger.debug("Parsing %s", osp.basename(item_path))
            tree = UserCompilationUnit(item_path)
            self.java_info[item_path] = tree

        # 获取包名下的所有大类
        for k, v in self.java_info.items():
            for item in v.class_list:
                obj = UserClassDeclaration(item, v)
                self.class_info[obj.fqn] = obj

        # 解析 LAYER
        self.main = self.class_info['org.telegram.tgnet.TLRPC']
        self.LAYER = self.main.get_value('LAYER')
        self.logger.debug('%s = %d', 'LAYER', self.LAYER)

        inner_class_info = {}

        for k, v in self.class_info.items():
            classes = v.class_list
            for item in classes:
                obj = UserClassDeclaration(item, v)
                inner_class_info[obj.fqn] = obj
            self.logger.debug("Parsing %s from %s", len(classes), k)
        
        self.class_info.update(inner_class_info)

        for k, v in inner_class_info.items():
            parents = self.get_extends_list(k)
            if not parents:
                self.logger.error('%s extends is None', k)
                continue
            else:
                if 'org.telegram.tgnet.TLObject' not in parents:
                    self.logger.error('%s is not subclass of TLObject: %s',
                                      k,
                                      parents)
                    continue
            self.tlobj_info[k] = v

        for k, v in self.tlobj_info.items():
            if (conv := v.get_value('constructor')):
                self.cid_info[k] = f'0x{conv:08x}'
            for item in (x for x in v.methods if x.name == 'TLdeserialize'):
                if any(BaseParser.is_switch_statement(x) for x in item.body):
                    self.structure_info[k] = {'name': get_struct_name(k),
                                              'method': item}
                    break

        self.logger.debug('TLRPC files contain class count %d',
                          len(self.tlobj_info))
        self._directory = value

    def get_class(self, fqn: str):
        if isinstance(fqn, UserClassDeclaration):
            return fqn
        return self.class_info.get(fqn)

    def get_extends_list(self, fqn: str):
        if (obj := self.get_class(fqn)) is None:
            return None
        parents = []
        cur = obj
        for i in range(20):
            if not (extends := cur.extends):
                break
            parents.append(extends)
            if not (cur := self.get_class(extends)):
                break
        return parents

    def get_fields(self, fqn: str, recursive=True):
        if (obj := self.get_class(fqn)) is None:
            return None
        fields = {x.declarators[0].name: x for x in obj.fields}
        if not recursive:
            return fields
        for extends in self.get_extends_list(obj):
            if (extends_class := self.get_class(extends)) is None:
                break
            for field in extends_class.fields:
                name = field.declarators[0].name
                if name not in fields:
                    fields[name] = field
        return fields

    def get_methods(self, fqn: str, recursive=True):
        if (obj := self.get_class(fqn)) is None:
            return None
        methods = {x.name: x for x in obj.methods}
        if not recursive:
            return methods
        for extends in self.get_extends_list(obj):
            if (extends_class := self.get_class(extends)) is None:
                break
            for method in extends_class.methods:
                name = method.name
                if name not in methods:
                    methods[name] = method
        return methods

    def get_cid(self, fqn: str) -> str:
        if fqn in self.cid_info:
            return self.cid_info[fqn]
        if not (cl := self.get_class(fqn)):
            return None
        return self.cid_info.get(cl.fqn)

    def generate_class_code(self, name):
        obj = ClassParser(name, self, self.logger_level)
        index = obj.index
        if index in self.cache:
            ret = self.cache[index]
        else:
            ret = obj.generate()
        return ret

    def get_class_struct(self, fqn):
        ret = None
        obj = ClassParser(fqn, self, self.logger_level)
        cid = obj.cid
        sname = obj.struct_name
        if cid and (index := int(cid, 16)) in self.cache:
            res = self.cache[index]
            ret = [res.format_map({'name': sname})]
        else:
            try:
                ret = obj.generate()
            except Exception as e:
                self.logger.error('Generate class %s error: %s', fqn, e)
                # if str(e).startswith('get_field_type'):
                #     raise e
                if self.strict:
                    raise e
            finally:
                if not ret:
                    if obj.info.get('cid') and obj.info.get('sname'):
                        if obj.info.get('todo'):
                            ret = [TODO_STR.format_map(obj.info)]
                        else:
                            ret = [FAIL_STR.format_map(obj.info)]
        return ret

    def parse_tlrpc(self):
        result = []
        parse_result = {}
        for k in self.tlobj_info:
            content = self.get_class_struct(k)
            if content is None:
                print(f'{k} content is null.')
                continue  # pylint: disable=E275
            func_name = re.search(r'def (\w+)', content).group(1)
            if func_name not in parse_result:
                parse_result[func_name] = content
            else:
                print(f'{func_name} has exist.')
                print(content, parse_result[func_name])
        with open(r'datatype/telegram.py', 'r', encoding='utf-8') as f:
            c = f.read()
        for i in range(3):
            c = c.replace('\r\n', '\n')
        c = c.replace('\n', '\r\n')
        func_names = re.findall(r'def (\w+)', c)
        for item in func_names:
            if item in parse_result:
                result.append(parse_result[item])
            else:
                print(f'{item} not in parse result')
        result_text = '\r\n\r\n'.join(result)
        save_code('1.py', result_text, pep8=True)

    def generate_tlrpc(self, target):
        '''
        TL_inputStorePaymentGiftPremium case 0x44618a7d 0x616f7fe8

        Returns
        -------
        None.

        '''
        parse_result = {}
        for k in self.tlobj_info:
            content = self.get_class_struct(k)
            if content is None:
                print(f'{k} content is null.')
                continue  # pylint: disable=E275
            func_name = re.search(r'def (\w+)', content).group(1)
            if func_name not in parse_result:
                parse_result[func_name] = content
            else:
                print(f'{func_name} has exist.')
                print(content, parse_result[func_name])
        structures_func_names = [x for x in parse_result if 'structures' in x]
        structures_func_names = list(sorted(structures_func_names))
        sorted_names = []
        sorted_contents = []
        for item in structures_func_names:
            item_content_list = []
            item_struct = parse_result[item]
            subitems = re.findall(r'self\.(struct_0x\w{8})', item_struct)
            for subitem in subitems:
                sorted_names.append(subitem)
                if subitem in parse_result:
                    item_content_list.append(parse_result[subitem])
                else:
                    text = f'    def {subitem}(self):\n        #TODO\n'
                    item_content_list.append(text)
            item_content_list.append(item_struct)
            sorted_names.append(item)
            sorted_contents.append(item_content_list)
            print(item, len(item_content_list))
        sorted_contents_len = sum(len(x) for x in sorted_contents)
        assert (len(sorted_names) == sorted_contents_len)
        sorted_all_contents = []
        split_line = f'{" " * 4}# {"-" * 73}'
        sorted_all_contents.append(split_line)
        for item in sorted_contents:
            sorted_all_contents.extend(item)
            sorted_all_contents.append(split_line)
        with open(HEADER, 'r', encoding='utf-8') as f:
            header_text = f.read()
        sorted_text = '\r\n\r\n'.join(sorted_all_contents)
        sorted_name_info = dict.fromkeys(sorted_names)
        left_names = [x for x in parse_result if x not in sorted_name_info]
        # assert (len(left_names) == (len(parse_result) - len(sorted_names)))
        left_text = '\r\n\r\n'.join(parse_result[x] for x in left_names)
        result_text = ''
        result_text += header_text
        result_text += sorted_text
        result_text += left_text
        save_code(target, result_text, pep8=True,
                  options={'max_line_length': 119})

    def merge_tlrpc(self, path, target, replace=False):
        parse_result = {}
        for k in self.tlobj_info:
            # print(f'Process {k}')
            content = self.get_class_struct(k)
            if not content:
                print(f'{k} content is null.')
                continue
            for item in content:
                func_name = re.search(r'def (\w+)', item).group(1)
                if func_name not in parse_result:
                    parse_result[func_name] = item
                else:
                    print(f'{func_name} has exist.')
                    print(item, parse_result[func_name])
        with open(path, encoding='utf-8') as f:
            c = f.read()
        for i in range(3):
            c = c.replace('\r\n', '\n')
        c = c.replace('\n', '\r\n')
        cs = c.split('\r\n\r\n')
        info = {}
        for index, item in enumerate(cs):
            try:
                func_name = re.search(r'def (\w+)', item).group(1)
                info[func_name] = index
            except Exception:
                func_name = None
        append_items = {}
        pattern = re.compile(r'LazyBound\(self.(\w+)\)')
        replaces = {}

        for k, v in parse_result.items():
            if k in info:
                index = info[k]
                if k.endswith('structures'):
                    ol = pattern.findall(cs[index])
                    ml = pattern.findall(v)
                    if not tuple(ol) == tuple(ml):
                        start = index - len(ol)
                        end = index
                        result = []
                        for i in ml:
                            if i in info:
                                if i in parse_result:
                                    ov = PATTERN1.search(cs[info[i]]).group(2)
                                    mv = PATTERN1.search(
                                        parse_result[i]).group(2)
                                    if not ov == mv:
                                        iv = rename_struct(cs[info[i]], mv)
                                    else:
                                        iv = cs[info[i]]
                                else:
                                    iv = cs[info[i]]
                            else:
                                iv = parse_result.get(i, 'None')
                                if iv == 'None':
                                    print(f'Parse result get {i} is None')
                            if i in append_items:
                                del append_items[i]
                            result.append(iv)
                        replaces[(start, end)] = result
                    cs[index] = v
                else:
                    if replace:
                        cs[index] = v
                    else:
                        try:
                            ov = PATTERN1.search(cs[index]).group(2)
                        except Exception as e:
                            print(cs[index])
                            raise e
                        mv = PATTERN1.search(v).group(2)
                        flag = False
                        if not ov == mv:
                            cs[index] = rename_struct(cs[index], mv)
                            flag = True
                        if not flag and 'TODO' in cs[index] and 'TODO' not in v:
                            cs[index] = v
                            flag = True
            else:
                append_items[k] = None
        cur = 0
        result_list = []
        # print(cs)
        for item in sorted(replaces):
            s, e = item
            result_list.extend(cs[cur:s])
            result_list.extend(replaces[item])
            cur = e
        else:
            result_list.extend(cs[cur:])
        for k in append_items:
            result_list.append(parse_result[k])
        content_text = '\r\n\r\n'.join(result_list)
        save_code(target, content_text, pep8=False)

    @classmethod
    def collect_dup(cls, path, left, right):
        with open(path, encoding='utf-8') as f:
            c = f.read()
        func_map = {}
        a_list = []
        b_list = []
        for item in FUNCTION_PATTERN.finditer(c):
            func_name = item.group(1)
            if func_name not in func_map:
                func_map[func_name] = item.group(0)
            else:
                a_list.append(func_map[func_name])
                b_list.append(item.group(0))
        with open(left, 'w+', encoding='utf-8') as f:
            f.write(''.join(a_list))
        with open(right, 'w+', encoding='utf-8') as f:
            f.write(''.join(b_list))

    @classmethod
    def remove_duplicate(cls, path, target, all_same=True):
        with open(path, encoding='utf-8') as f:
            c = f.read()
        func_map = {}
        func_index_map = {}
        start = 0
        result = []
        result_index = 0
        for item in FUNCTION_PATTERN.finditer(c):
            result.append(c[start:item.start()])
            result_index += 1
            func_name = item.group(1)
            func_content = item.group(0)
            if func_name not in func_map:
                func_map[func_name] = func_content
                func_index_map[func_name] = result_index
                result.append(func_content)
                result_index += 1
            else:
                if all_same:
                    if not func_map[func_name] == func_content:
                        # result.append(func_content)
                        print(f'Replace {func_name}')
                        result[func_index_map[func_name]] = func_content
            start = item.end()
        else:
            result.append(c[start:])
        with open(target, 'w+', encoding='utf-8') as f:
            f.write(''.join(result))

    @classmethod
    def sort_file(cls, path, target):
        with open(path, encoding='utf-8') as f:
            c = f.read()
        func_map = {}
        start = 0
        result = []
        for item in FUNCTION_PATTERN.finditer(c):
            result.append(c[start:item.start()])
            func_name = item.group(1)
            func_content = item.group(0)
            if (func_name.endswith('_structures') or
                re.fullmatch('struct_0x\w{8}', func_name)):
                func_map[func_name] = func_content
            else:
                result.append(func_content)
            start = item.end()
        else:
            result.append(c[start:])
            
        result.append('\n' + '#' * 79 + '\n')
        
        structures_func_names = [x for x in func_map if x.endswith('_structures')]
        structures_func_names = list(sorted(structures_func_names))
        sorted_names = {}
        sorted_contents = []
        regex = re.compile(r'self\.(struct_0x\w{8})')
        split_line = f'{" " * 4}# {"-" * 73}\n\n'
        for item in structures_func_names:
            item_content_list = []
            item_struct = func_map[item]
            for subitem in regex.finditer(item_struct):
                fname = subitem.group(1)
                if fname in func_map:
                    sorted_names[fname] = None
                    item_content_list.append(func_map[fname])
                else:
                    text = f'    def {fname}(self):\n        #TODO\n'
                    item_content_list.append(text)
            item_content_list.append(item_struct)
            sorted_names[item] = None
            sorted_contents.extend(item_content_list)
            sorted_contents.append(split_line)
            print(item, len(item_content_list))
        result.extend(sorted_contents)
        result.append('\n' + '#' * 79 + '\n')
        for k, v in func_map.items():
            if k not in sorted_names:
               result.append(v)
        result.append('\n' + '#' * 79 + '\n')
        with open(target, 'w+', encoding='utf-8') as f:
            f.write(''.join(result))

    @classmethod
    def format_pycode(cls, path, limit=120):
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if len(line) > limit:
                m = re.search(r'If\([^,]+,', line)
                if m:
                    end = m.end()
                    line1 = f'{line[:end]}\n'
                    line2 = f'{" " * (m.start() + 3)}{line[end:].lstrip()}'
                    # print(line)
                    # print(line1)
                    # print(line2)
                    # break
                    new_lines.append(line1)
                    new_lines.append(line2)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        content = ''.join(new_lines)
        import autopep8
        content = autopep8.fix_code(content, options={'max_line_length': 119})
        with open(path, 'w+', encoding='utf-8', newline='\n') as f:
            f.write(content)

    @classmethod
    def format_pycode2(cls, path, target, limit=120):
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        flag = False
        for line in lines:
            line_strip = line.rstrip()
            if line_strip.endswith(')') or line_strip.endswith('),'):
                if flag:
                    new_combine_line = f'{
                        new_lines[-1].rstrip()} {line.lstrip()}'
                    if len(new_combine_line) <= limit and new_combine_line.count('/') < 2:
                        new_lines[-1] = new_combine_line
                        # print(new_combine_line)
                        continue
                flag = False
            elif line_strip.endswith(','):
                if 'FlagsEnum' not in line_strip and line_strip.count('(') > line_strip.count(')') and not line.lstrip().startswith('#'):
                    flag = True
                else:
                    flag = False
            else:
                flag = False
            new_lines.append(line)
        content = ''.join(new_lines)
        import autopep8
        content = autopep8.fix_code(content, options={'max_line_length': 119})
        with open(target, 'w+', encoding='utf-8', newline='\n') as f:
            f.write(content)

    @classmethod
    def sort_func(cls, path, target):
        parse_result = {}
        with open(path, encoding='utf-8') as f:
            c = f.read()
        parse_result = {}
        left = []
        start = 0
        for item in FUNCTION_PATTERN.finditer(c):
            left.append(c[start:item.start()])
            start = item.start()
            func_name = item.group(1)
            func_content = item.group(0)
            if (func_name.endswith('_structures') or
                func_name.startswith('struct_')):
                if func_name not in parse_result:
                    parse_result[func_name] = func_content
                    start = item.end()
                else:
                    print(f'{func_name} has exists.')
        # print(''.join(left))
        # return
        structures_func_names = [x for x in parse_result if x.endswith('_structures')]
        structures_func_names = list(sorted(structures_func_names))
        sorted_names = []
        sorted_contents = []
        for item in structures_func_names:
            item_content_list = []
            item_struct = parse_result[item]
            subitems = re.findall(r'self\.(struct_0x\w{8})', item_struct)
            for subitem in subitems:
                sorted_names.append(subitem)
                if subitem in parse_result:
                    item_content_list.append(parse_result[subitem])
                else:
                    text = f'    def {subitem}(self):\n        #TODO\n'
                    item_content_list.append(text)
            item_content_list.append(item_struct)
            sorted_names.append(item)
            sorted_contents.append(item_content_list)
            print(item, len(item_content_list))
        sorted_contents_len = sum(len(x) for x in sorted_contents)
        assert (len(sorted_names) == sorted_contents_len)
        sorted_all_contents = []
        split_line = f'{" " * 4}# {"-" * 73}'
        sorted_all_contents.append(split_line)
        for item in sorted_contents:
            sorted_all_contents.extend(item)
            sorted_all_contents.append(split_line)
        with open(HEADER, 'r', encoding='utf-8') as f:
            header_text = f.read()
        sorted_text = '\r\n\r\n'.join(sorted_all_contents)
        sorted_name_info = dict.fromkeys(sorted_names)
        left_names = [x for x in parse_result if x not in sorted_name_info]
        # assert (len(left_names) == (len(parse_result) - len(sorted_names)))
        left_text = '\r\n\r\n'.join(parse_result[x] for x in left_names)
        result_text = ''
        result_text += ''.join(left)
        result_text += header_text
        result_text += sorted_text
        result_text += left_text
        save_code(target, result_text, pep8=True,
                  options={'max_line_length': 512})

    @classmethod
    def format_cid(cls, value):
        if isinstance(value, str):
            return f'0x{int(value, 16):08x}'
        else:
            return f'0x{value:08x}'

    @classmethod
    def remove_dup_func(cls, path, target, javafile):
        with open(javafile, encoding='utf-8') as f:
            c = f.read()
        cid_list = re.findall(r'constructor *= *(0x[\da-f]+);', c, re.I)
        cid_func = [f'struct_{cls.format_cid(x)}' for x in cid_list]
        cid_set = set(cid_func)
        with open(path, encoding='utf-8') as f:
            c = f.read()
        func_map = {}
        start = 0
        with open(target, 'w+', encoding='utf-8') as f:
            for item in FUNCTION_PATTERN.finditer(c):
                f.write(c[start:item.start()])
                start = item.start()
                func_name = item.group(1)
                if func_name.startswith('struct_'):
                    if func_name in cid_set:
                        func_map[func_name] = item.group(0)
                        f.write(item.group(0))
                        start = item.end()
                    else:
                        start = item.end()
                else:
                    f.write(item.group(0))
                    start = item.end()
            else:
                f.write(c[start:])

def test():
    git_path = r'E:\Project\Godsix\teleparser\utils\Telegram'
    path = osp.join(git_path, r"TMessagesProj\src\main\java\org\telegram\tgnet")
    parser = JavaParser(path, level=logging.INFO, strict=True)
    debug = False
    # debug = True
    if not debug:
        parser.merge_tlrpc(r'E:\Project\Godsix\teleparser\datatype\telegram.py',
                           r'E:\Project\Godsix\teleparser\new.py', True)
        if GDATA:
            print('GDATA:', GDATA)
    else:
        # fqn = 'org.telegram.tgnet.TLRPC.TL_messagePeerReaction_layer144'
        fqn = 'org.telegram.tgnet.TLRPC.Update'
        content = parser.get_class_struct(fqn)
        if content:
            print(content[0])

def test2():
    JavaParser.remove_duplicate(r'E:\Project\Godsix\teleparser\datatype\telegram.py',
                            r'E:\Project\Godsix\teleparser\datatype\telegram1.py')
    return


def test3():
    JavaParser.sort_file(r'E:\Project\Godsix\teleparser\datatype\telegram.py',
                         r'E:\Project\Godsix\teleparser\datatype\telegram1.py')
    return


def main():
    test()
    # test2()
    # test3()


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
