# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 08:47:59 2022

@author: 皓
"""
import os.path as osp
from glob import iglob
import re
import logging
from enum import IntEnum
from javalang.parse import parse
from javalang.tree import (FieldDeclaration, ClassDeclaration,
                           MethodDeclaration,
                           StatementExpression, LocalVariableDeclaration,
                           ForStatement, SwitchStatement, IfStatement,
                           ReturnStatement,
                           MethodInvocation, Assignment,
                           BasicType, ReferenceType, BlockStatement,
                           ForControl, BinaryOperation,
                           Cast, MemberReference, Literal)
from .common import STRUCT_CACHE, HEADER
from .tools import get_struct_content, get_structures_content
from .utils import name_convert_to_snake, save_code


TYPE_INFO = {
    'writeInt32': 'Int32ul',
    'writeInt64': 'Int64ul',
    'writeBool': 'TBool',
    'writeString': 'TString',
    'writeByteArray': 'TBytes',
    'writeDouble': 'Double',
    'writeByteBuffer': 'TBytes',
}

PATTERN1 = re.compile(r"@constructor\((\w+), '(\w+)'(.*)\)")
PATTERN2 = re.compile(r"'sname'\s*/\s*Computed\(\s*'(\w+)'\s*\)")


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
    if datatype == 'Int32ul' and (name == 'date' or name.endswith('date')):
        return 'TTimestamp'
    return datatype


class Tag(IntEnum):
    VECTOR_START = 1
    VECTOR_CONTENT = 2
    VECTOR_END = 3
    FLAGS_TAG = 4


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
    def is_class(cls, obj):
        return isinstance(obj, ClassDeclaration)

    @classmethod
    def is_field(cls, obj):
        return isinstance(obj, FieldDeclaration)

    @classmethod
    def is_method(cls, obj):
        return isinstance(obj, MethodDeclaration)

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
    def is_literal(cls, obj):
        return isinstance(obj, Literal), MemberReference, Literal


class InnerClassParser(BaseParser):
    LOG = 'InnerClassParser'

    def __init__(self, inner_class, parent_class, level=logging.INFO):
        super().__init__()
        self.parent_class = parent_class
        self.strict = self.parent_class.strict
        self.classes = parent_class.classes
        self.inner_class = parent_class.get_inner_class(inner_class)
        self.inner_class_name = self.inner_class.name
        if not self.parent_class.is_extends_TLObject(self.inner_class):
            msg = f'Class {self.inner_class_name} is not extends TLObject'
            if self.strict:
                raise TypeError(msg)
            self.logger.debug(msg)
        self.fields = parent_class.get_fields(self.inner_class)
        self.methods = parent_class.get_methods(self.inner_class)
        self.info = {}
        self.structs = []
        self.info['structs'] = self.structs
        self.content_0x1cb5c415 = []
        self.flags = {}
        self.info['flags'] = self.flags

    @property
    def index(self):
        if 'constructor' not in self.fields:
            return None
        value = self.fields['constructor'].declarators[0].initializer.value
        return eval(value)

    def parse_inner_class(self):
        self.logger.debug('Parse inner class %s', self.inner_class_name)
        if self.inner_class_name.startswith('TL_'):
            return self.parse_inner_class_tl()
        else:
            return self.parse_inner_class_switch()

    def parse_inner_class_tl(self):
        name = self.inner_class_name
        struct_name = name_convert_to_snake(name[3:])
        struct_index = self.index
        struct_text = f'0x{struct_index:08x}'
        self.info['struct_name'] = struct_name
        self.info['struct_index'] = struct_index
        self.info['struct_index_text'] = struct_text
        self.structs.append(('sname', f"Computed('{struct_name}')"))
        if 'serializeToStream' in self.methods:
            self.parse_serialize()
        elif 'readParams' in self.methods:
            msg = f"Class {name} can't parse readParams."
            if self.strict:
                raise NotImplementedError(msg)
            else:
                self.logger.error(msg)
                return {}
        else:
            msg = f'Class {name} has no needed method.'
            if self.strict:
                raise NotImplementedError(msg)
            else:
                self.logger.error(msg)
                return {}
        return self.info

    def parse_0x1cb5c415(self):
        data = self.content_0x1cb5c415[1]
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
        data_type, is_array = self.parse_field_type(data_name)
        if is_array is False:
            raise TypeError(data_name)
        if data_type in ('int', 'str', 'bytes'):
            for_item = self.content_0x1cb5c415[-1]
            for_member = for_item.body.statements[0].expression.member
            data_type = get_stream_type(for_member)
        else:
            # raise ValueError(f'data_type: {data_type}')
            pass  # pylint: disable=E275
        struct_type = f"self.struct_0x1cb5c415({data_type}, '{data_name}')"
        dname = name_convert_to_snake(data_name)
        return (dname, struct_type)

    def parse_inner_class_type(self, data_name, data_type):
        data_class = self.classes.get(data_type)
        if data_class is not None:
            if data_type.startswith('TL_'):
                constructor = self.parent_class.get_constructor(data_class)
                if constructor is None:
                    raise TypeError(f'Class {data_type} has not constructor.')
                struct_type = f"self.struct_{constructor}()"
            else:
                sname = name_convert_to_snake(data_type)
                dname = name_convert_to_snake(data_name)
                struct_type = f"self.{sname}_structures('{dname}')"
        else:
            if data_type == 'Integer':
                return 'int'
            elif data_type == 'Long':
                return 'int'
            elif data_type == 'String':
                return 'str'
            elif data_type == 'byte':
                return 'bytes'
            raise ValueError(f'{data_name}, {data_type}')
        return struct_type

    def get_field_type(self, field_name, class_name=None):
        if class_name is None:
            fields = self.fields
        else:
            fields = self.parent_class.get_fields(class_name)
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

    def parse_field_type(self, field_name):
        if field_name is None:
            self.logger.error('parse_field_type: field_name is None')
            return None
        if '.' in field_name:
            field_name_list = field_name.split('.')
            class_name = None
            for item in field_name_list:
                class_name = self.get_field_type(item, class_name)
                if class_name is None:
                    self.logger.error('parse_field_type: field parse fail: %s',
                                      field_name)
                    return None
            data_name = field_name.replace('.', '_')
            return (self.parse_inner_class_type(data_name, class_name), False)
        else:
            field = self.fields.get(field_name)
            if field is None:
                self.logger.error('parse_field_type: can not find field %s',
                                  field_name)
                return None
            is_array_list = False
            field_type = field.type.name
            if field_type == 'ArrayList':
                is_array_list = True
                contain_type = field.type.arguments[0].type.name
                return (self.parse_inner_class_type(field_name, contain_type),
                        is_array_list)
            return (self.parse_inner_class_type(field_name, field_type),
                    is_array_list)

    @classmethod
    def is_member_reference_or_cast(cls, obj):
        return cls.is_member_reference(obj) or cls.is_cast(obj)

    def parse_statement_expression(self, statement):
        expression = statement.expression
        if self.is_method_invocation(expression):
            qualifier = expression.qualifier
            member = expression.member
            arguments = expression.arguments
            if qualifier == 'stream':
                assert len(arguments) == 1, f'{statement} {len(arguments)}'
                argument = arguments[0]
                if self.is_member_reference_or_cast(argument):
                    if self.is_member_reference(argument):
                        struct_name = argument.member
                    else:
                        struct_name = argument.expression.member
                    data_type = get_stream_type(member, struct_name)
                    if struct_name == 'constructor':
                        struct_name = 'signature'
                        field = self.fields['constructor']
                        struct_value = field.declarators[0].initializer.value
                        struct_index = int(struct_value, 16)
                        struct_text = f'0x{struct_index:08x}'
                        struct_type = f'Hex(Const({struct_text}, {data_type}))'
                    elif struct_name in ('flags', 'flags2'):
                        return (struct_name, f'FlagsEnum({data_type}')
                    else:
                        struct_type = data_type
                    return (struct_name, struct_type)
                elif self.is_literal(argument):
                    try:
                        argument_value = argument.value
                    except AttributeError as e:
                        print(self.inner_class_name, argument)
                        raise e
                    if argument_value == '0x1cb5c415':
                        return Tag.VECTOR_START
                    elif argument_value in ('""', '0'):
                        data_type = get_stream_type(member)
                        return ('_reserve', data_type)
                    else:
                        raise ValueError(f'{argument.value}')
                else:
                    TypeError(type(argument))
            elif not qualifier and member == 'writeAttachPath':
                return ('attach_path', 'TString')
            else:
                if member == 'serializeToStream':
                    struct_name = qualifier
                    try:
                        struct_type, is_array = self.parse_field_type(
                            struct_name)
                    except Exception as e:
                        print(statement)
                        raise e
                    if '.' in struct_name:
                        struct_name = struct_name.replace('.', '_')
                    dname = name_convert_to_snake(struct_name)
                    return (dname, struct_type)
                elif member == 'get':
                    struct_name = qualifier
                    if struct_name.endswith('s'):
                        struct_name = struct_name[:-1]
                    selectors = expression.selectors
                    selector = selectors[0]
                    assert selector.member == 'serializeToStream'
                    struct_type, is_array = self.parse_field_type(qualifier)
                    assert is_array
                    assert struct_type.startswith('self')
                    struct_type = struct_type.replace(qualifier, struct_name)
                    # TODO
                    dname = name_convert_to_snake(struct_name)
                    return (struct_name, struct_type)
        elif self.is_assignment(expression):
            member = expression.expressionl.member
            if member in ('flags', 'flags2'):
                if_false = expression.value.if_false.operandr.value
                if_true = expression.value.if_true.operandr.value
                assert if_false == if_true, f'{if_false} ≠ {if_true}'
                condition = expression.value.condition
                if self.is_member_reference(condition):
                    condition_member = condition.member
                elif self.is_binary_operation(condition):
                    condition_member = condition.operandl.member
                else:
                    raise ValueError(type(condition))
                value = if_true
                if condition_member.startswith('is'):
                    flag_tag = name_convert_to_snake(condition_member)
                elif condition_member.startswith('has_'):
                    flag_tag = condition_member
                else:
                    flag_tag = f'is_{condition_member}'
                self.add_flags(member, flag_tag, value)
                return Tag.FLAGS_TAG
            else:
                raise ValueError(member)

    def add_flags(self, tag, name, value, force=False):
        flag_info = self.flags.setdefault(tag, {})
        if force:
            flag_info.setdefault(name, value)
            return name
        info = {v: k for k, v in flag_info.items()}
        if value not in info:
            flag_info.setdefault(name, value)
            return name
        else:
            return info[value]

    def parse_if_statement(self, statement):
        result = []
        condition = statement.condition
        operandl = condition.operandl
        if self.is_binary_operation(operandl):
            condition_member = operandl.operandl.member
            condition_value = operandl.operandr.value
            then_statements = statement.then_statement.statements
            result_list = self._parse_serialize(then_statements)
            c_m = condition_member
            for item in result_list:
                struct_name, data_type = item
                f_n = f'has_{struct_name}'
                fnn = self.add_flags(c_m, f_n, condition_value)
                struct_type = f'If(this.{c_m}.{fnn}, {data_type})'
                result.append((struct_name, struct_type))
            return result
        elif self.is_member_reference(operandl):
            struct_name = operandl.member
            try:
                then_statement = getattr(statement, 'then_statement')
                member1 = then_statement.expression.member
                data_type1 = get_stream_type(member1, struct_name)
                else_statement = getattr(statement, 'else_statement', None)
                if else_statement:
                    member2 = then_statement.expression.member
                    data_type2 = get_stream_type(member2, struct_name)
                else:
                    data_type2 = None
                assert data_type1 == data_type2, statement
                result.append((struct_name, data_type1))
                return result
            except AttributeError:
                pass  # pylint: disable=E275
            try:
                is_ = f'is_{struct_name}'
                has_ = f'has_{struct_name}'
                if condition.operandr.value == 'null':
                    for k, v in self.flags.items():
                        c_m = k
                        value = v.get(is_)
                        if value is not None:
                            f_n = is_
                            break  # pylint: disable=E275
                        value = v.get(has_)
                        if value is not None:
                            f_n = has_
                            break  # pylint: disable=E275
                    else:
                        if self.strict:
                            raise AttributeError(
                                f'Can not found flag {is_} or {has_}')
                        return []
                    then_statements = statement.then_statement.statements
                    result_list = self._parse_serialize(then_statements)
                    for item in result_list:
                        _, data_type = item
                        struct_type = f'If(this.{c_m}.{f_n}, {data_type})'
                        result.append((struct_name, struct_type))
                    return result
                else:
                    raise AttributeError('condition.operandr.value not null')
            except AttributeError as e:
                if self.strict:
                    self.logger.error('Class %s, statement %s, error %s',
                                      self.inner_class_name,
                                      statement, e)
                    raise e
                else:
                    self.logger.error('Class %s, statement %s, error %s',
                                      self.inner_class_name,
                                      statement, e)
                return []
        else:
            t = type(condition.operandl).__name__
            msg = f'Condition left type is {t}'
            if self.strict:
                raise TypeError(msg)
            else:
                self.logger.error(msg)

    def _parse_serialize(self, statements):
        assert (not self.content_0x1cb5c415)
        result = []
        for item in statements:
            if self.content_0x1cb5c415:
                self.content_0x1cb5c415.append(item)
                if self.is_for_statement(item):
                    res = self.parse_0x1cb5c415()
                    if res is None:
                        raise ValueError(repr(item))
                    self.content_0x1cb5c415.clear()
                    result.append(res)
                continue  # pylint: disable=E275
            if self.is_statement_expression(item):
                res = self.parse_statement_expression(item)
                if res is None:
                    raise ValueError(repr(item))
                if res == Tag.VECTOR_START:
                    self.content_0x1cb5c415.append(item)
                    continue  # pylint: disable=E275
                if res == Tag.FLAGS_TAG:
                    continue  # pylint: disable=E275
                result.append(res)
            elif self.is_local_variable(item):
                raise TypeError('local_variable')
            elif self.is_for_statement(item):
                raise TypeError('for_statement')
            elif self.is_if_statement(item):
                res = self.parse_if_statement(item)
                if res is None:
                    raise ValueError(repr(item))
                result.extend(res)
        return result

    def parse_serialize(self):
        method = self.methods['serializeToStream']
        assert (not self.content_0x1cb5c415)
        result = self._parse_serialize(method.body)
        self.structs.extend(result)

    def parse_read_param(self):
        method = self.methods['readParams']
        for item in method.body:
            pass  # pylint: disable=E275

    def parse_deserialize(self):
        method = self.methods['TLdeserialize']
        for item in method.body:
            if self.is_switch_statement(item):
                switch_member = item.expression.member
                assert switch_member == 'constructor', 'Switch not constructor'
                for subitem in item.cases:
                    assert len(subitem.case) == 1
                    struct_value = subitem.case[0].value
                    struct_index = int(struct_value, 16)
                    struct_text = f'0x{struct_index:08x}'
                    self.structs.append(struct_text)
                return True
            elif self.is_local_variable(item):
                continue  # pylint: disable=E275
            elif self.is_return_statement(item):
                continue  # pylint: disable=E275
            elif self.is_if_statement(item):
                continue  # pylint: disable=E275
            else:
                raise TypeError(f'Unknow type:{type(item).__name__}')
        self.logger.error('class %s TLdeserialize contain not switch',
                          self.inner_class_name)
        return False

    def parse_inner_class_switch(self):
        name = self.inner_class_name
        struct_name = name_convert_to_snake(name)
        self.info['struct_name'] = struct_name
        if 'TLdeserialize' in self.methods:
            self.parse_deserialize()
            return True
        else:
            # Class has not TLdeserialize: Vector
            self.logger.warning('Class has not TLdeserialize: %s', name)
            return None

    def generate_inner_class(self):
        ret = self.parse_inner_class()
        if ret is None:
            return None
        if not self.info:
            self.logger.error('Class %s parse failed', self.inner_class_name)
            return None
        if self.inner_class_name.startswith('TL_'):
            return get_struct_content(self.info)
        else:
            return get_structures_content(self.info)


class TLRPCParser(BaseParser):
    LOG = 'TLRPCParser'

    def __init__(self, path, cached=None, level=logging.INFO, strict=False):
        super().__init__(level)
        self.path = path
        self.cache = {}
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
        self.strict = strict

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        with open(value, encoding='utf-8') as f:
            c = f.read()
        self.tree = parse(c)
        classes = self.tree.children[-1]
        for item in (x for x in classes if self.is_class(x)):
            if item.name == 'TLRPC':
                self.tlrpc = item
                break  # pylint: disable=E275
        else:
            self.tlrpc = None
        if self.tlrpc is None:
            raise ValueError('Can not find class TLRPC')
        self.classes = {x.name: x for x in self.tlrpc.body if self.is_class(x)}
        self.logger.debug('TLRPC contain class count %d', len(self.classes))
        self._path = value

    def get_inner_class(self, name: str):
        class_ = self.classes.get(name) if isinstance(name, str) else name
        if class_ is None:
            return None
        return class_

    def get_parents(self, name: str):
        inner_class = self.get_inner_class(name)
        if inner_class is None:
            return None
        parents = []
        cur = inner_class
        for i in range(20):
            extends = cur.extends.name
            parents.append(extends)
            cur = self.classes.get(extends)
            if cur is None:
                break  # pylint: disable=E275
        return parents

    def get_fields(self, name: str):
        inner_class = self.get_inner_class(name)
        if inner_class is None:
            return None
        field_iter = (x for x in inner_class.body if self.is_field(x))
        fields = {x.declarators[0].name: x for x in field_iter}
        for extend in self.get_parents(inner_class):
            if extend == 'TLObject':
                break  # pylint: disable=E275
            extend_class = self.get_inner_class(extend)
            if extend_class is None:
                continue  # pylint: disable=E275
            extend_iter = (x for x in extend_class.body if self.is_field(x))
            for extend_field in extend_iter:
                extend_field_name = extend_field.declarators[0].name
                if extend_field_name not in fields:
                    fields[extend_field_name] = extend_field
        return fields

    def get_methods(self, name: str):
        inner_class = self.get_inner_class(name)
        if inner_class is None:
            return None
        method_iter = (x for x in inner_class.body if self.is_method(x))
        methods = {x.name: x for x in method_iter}
        for extend in self.get_parents(inner_class):
            if extend == 'TLObject':
                break  # pylint: disable=E275
            extend_class = self.get_inner_class(extend)
            if extend_class is None:
                continue  # pylint: disable=E275
            extend_iter = (x for x in extend_class.body if self.is_method(x))
            for extend_method in extend_iter:
                extend_method_name = extend_method.name
                if extend_method_name not in methods:
                    methods[extend_method_name] = extend_method
        return methods

    def is_extends_TLObject(self, name: str):
        extends = self.get_parents(name)
        return (bool(extends) and 'TLObject' in extends)

    def get_constructor(self, name: ClassDeclaration) -> str:
        inner_class = self.get_inner_class(name)
        if inner_class is None:
            return None
        for item in inner_class.body:
            if not self.is_field(item):
                continue  # pylint: disable=E275
            declarator = item.declarators[0]
            if declarator.name == 'constructor':
                value = declarator.initializer.value
                index = int(value, 16)
                text = f'0x{index:08x}'
                return text
        return None

    def generate_class_code(self, name):
        inner_class = InnerClassParser(name, self, self.logger_level)
        index = inner_class.index
        if index in self.cache:
            ret = self.cache[index]
        else:
            ret = inner_class.generate_inner_class()
        return ret

    def get_class_struct(self, name):
        inner_class = InnerClassParser(name, self, self.logger_level)
        index = inner_class.index
        if index in self.cache:
            res = self.cache[index]
            ov = PATTERN1.search(res).group(2)
            mv = name_convert_to_snake(inner_class.inner_class_name[3:])
            if not ov == mv:
                ret = rename_struct(res, mv)
            else:
                ret = res
        else:
            ret = inner_class.generate_inner_class()
        return ret

    def parse_tlrpc(self):
        result = []
        parse_result = {}
        for k in self.classes:
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
        for k in self.classes:
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
                item_content_list.append(parse_result[subitem])
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
        assert (len(left_names) == (len(parse_result) - len(sorted_names)))
        left_text = '\r\n\r\n'.join(parse_result[x] for x in left_names)
        result_text = ''
        result_text += header_text
        result_text += sorted_text
        result_text += left_text
        save_code(target, result_text, pep8=True)

    def merge_tlrpc(self, path, target):
        parse_result = {}
        for k in self.classes:
            # print(f'Process {k}')
            try:
                content = self.get_class_struct(k)
            except Exception:
                print(f'Parse {k} error')
                continue
            if content is None:
                print(f'{k} content is null.')
                continue  # pylint: disable=E275
            func_name = re.search(r'def (\w+)', content).group(1)
            if func_name not in parse_result:
                parse_result[func_name] = content
            else:
                print(f'{func_name} has exist.')
                print(content, parse_result[func_name])
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
                                iv = parse_result[i]
                            if i in append_items:
                                del append_items[i]
                            result.append(iv)
                        replaces[(start, end)] = result
                    cs[index] = v
                else:
                    ov = PATTERN1.search(cs[index]).group(2)
                    mv = PATTERN1.search(v).group(2)
                    if not ov == mv:
                        cs[index] = rename_struct(cs[index], mv)
            else:
                append_items[k] = None
        cur = 0
        result_list = []
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


def test():
    path = "TLRPC.java"
    parser = TLRPCParser(path, 'structs', level=logging.INFO, strict=True)
    parser.generate_tlrpc()


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    test()
