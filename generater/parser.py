# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 08:47:59 2022

@author: 皓
"""
import os
import os.path as osp
from glob import iglob
import re
import logging
from enum import IntEnum
from javalang.parse import parse
from javalang.tree import (CompilationUnit, FieldDeclaration,
                           ClassDeclaration, MethodDeclaration,
                           StatementExpression, LocalVariableDeclaration,
                           ForStatement, SwitchStatement, IfStatement,
                           ReturnStatement,
                           MethodInvocation, Assignment,
                           BasicType, ReferenceType, BlockStatement,
                           ForControl, BinaryOperation,
                           Cast, MemberReference, Literal)
try:
    from .common import STRUCT_CACHE, HEADER
    from .tools import get_struct_content, get_structures_content
    from .utils import name_convert_to_snake, save_code
except ImportError:
    from generater.common import STRUCT_CACHE, HEADER
    from generater.tools import get_struct_content, get_structures_content
    from generater.utils import name_convert_to_snake, save_code


TYPE_INFO = {
    'writeInt32': 'Int32ul',
    'writeInt64': 'Int64ul',
    'writeBool': 'TBool',
    'writeString': 'TString',
    'writeByteArray': 'TBytes',
    'writeDouble': 'Double',
    'writeByteBuffer': 'TBytes',
    'readInt32': 'Int32ul',
    'readInt64': 'Int64ul',
    'readBool': 'TBool',
    'readString': 'TString',
    'readByteArray': 'TBytes',
    'readDouble': 'Double',
    'readByteBuffer': 'TBytes',
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


FUNCTION_PATTERN = re.compile(r"^ +@.+\n +def (\w+)\(.+\)(?s:.+?)\n\n", re.M)


def is_class(obj):
    '''判断对象是否为类声明'''
    return isinstance(obj, ClassDeclaration)


def get_parent_class(class_decl: ClassDeclaration):
    if not (extends := class_decl.extends):
        return None
    if extends.sub_type:
        return f'{extends.name}.{extends.sub_type.name}'
    else:
        return extends.name


class UserClassDeclaration:
    def __init__(self,
                 compile_unit: CompilationUnit,
                 declaration: ClassDeclaration,
                 outer: 'UserClassDeclaration' = None):
        self.c_unit = compile_unit
        self.decl = declaration
        self.outer = outer
        self.imports = {}
        self.outer_imports = {}
        for item in self.c_unit.imports:
            item_path = item.path
            self.imports[item_path.split('.')[-1]] = item_path
        if self.outer:
            fqn = self.outer.fqn
            for item in (x for x in self.outer.decl.body if is_class(x)):
                item_name = item.name
                self.outer_imports[item_name] = f'{fqn}.{item_name}'

    @property
    def name(self):
        return self.decl.name

    @property
    def fqn(self):
        '''类的全限定名(Fully Qualified Name, FQN)'''
        if self.outer:
            return f'{self.outer.fqn}.{self.decl.name}'
        else:
            return f'{self.c_unit.package.name}.{self.decl.name}'

    @property
    def extends(self):
        v = get_parent_class(self.decl)
        if not v:
            return None
        return self.get_fqn(v)

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
        return f'{self.c_unit.package.name}.{value}'

JAVA_TYPE = {
    'int': eval,
}


def get_class_value(cls_: ClassDeclaration, name: str):
    for field in cls_.fields:
        declarators = field.declarators
        type_name = field.type.name
        for declarator in declarators:
            if declarator.name == name:
                name = declarator.name
                init_value = declarator.initializer.value
                if (func := JAVA_TYPE.get(type_name)):
                    return func(init_value)
                else:
                    return init_value

def parse_java_file(path) -> CompilationUnit:
    with open(path, 'rb') as f:
        c = f.read()
    return parse(c)


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
        '''判断对象是否为类声明'''
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
        return isinstance(obj, Literal)


class ClassParser(BaseParser):
    LOG = 'ClassParser'

    def __init__(self, fqn, java_parser, level=logging.INFO):
        super().__init__(level)
        self.fqn = fqn
        self.java_parser = java_parser
        self.user_class = self.get_inner_class(fqn)
        self.cid = self.cid_info.get(fqn)
        name = self.user_class.name
        assert name, f'parse {fqn} name error'
        self.name = name
        if name.startswith('TL_'):
            self.cname = name[3:]
            self.is_tl = True
        else:
            self.cname = name
            self.is_tl = False
        fqns = fqn.split('.')
        if fqns[-2].startswith('TL_'):
            prefix = fqns[-2][3:]
            cnamel = self.cname.lower()
            if prefix.endswith('ies'):
                prefixs = f'{prefix[:-3]}y'
            elif prefix.endswith('s'):
                prefixs = prefix[:-1]
            else:
                prefixs = prefix
            if cnamel.startswith(prefix) or cnamel.startswith(prefixs):
                self.sname = self.cname
            else:
                self.sname = f'{prefix}_{self.cname}'
        else:
            self.sname = self.cname
        self.struct_name = name_convert_to_snake(self.sname)
        self.fields = self.get_fields(self.user_class)
        self.methods = self.get_methods(self.user_class, False)
        self.info = {}
        self.struct = []
        self.info['struct'] = self.struct
        self.switch = []
        self.info['switch'] = self.switch
        self.content_0x1cb5c415 = []
        self.flags = {}
        self.info['flags'] = self.flags

    def __getattr__(self, name):
        if hasattr(self.java_parser, name):
            return getattr(self.java_parser, name)
        raise AttributeError(f"'ClassParser' object has no attribute '{name}'")
    
    def get_cid(self, fqn):
        return self.cid_info.get(fqn)

    def parse(self):
        name = self.name
        struct_name = self.struct_name
        self.info['sname'] = struct_name
        self.logger.debug('Parse class %s', name)
        result = None
        if self.cid:
            self.info['cid'] = self.cid
            if 'serializeToStream' in self.methods:
                self.struct.append(('sname', f"Computed('{struct_name}')"))
                self.parse_serialize_to_stream()
                result = True
            elif 'readParams' in self.methods:
                self.struct.append(('sname', f"Computed('{struct_name}')"))
                self.struct.append(('signature',
                                    f'Hex(Const({self.cid}, Int32ul))'))
                self.parse_read_param()
                result = True
            elif 'TLdeserialize' in self.methods:
                pass
            else:
                msg = f'Class {name} has no method parsed.'
                if self.strict:
                    raise NotImplementedError(msg)
                else:
                    self.info['todo'] = 'no method'
                    self.logger.error(msg)
        if 'TLdeserialize' in self.methods:
            self.parse_deserialize()
            result = True
        else:
            if not result:
                self.logger.warning('Class has not TLdeserialize: %s', name)
        return result


    def parse_vector(self):
        '''parse 0x1cb5c415'''
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
        struct_type = f"self.vector({data_type}, '{data_name}')"
        dname = name_convert_to_snake(data_name)
        return (dname, struct_type)

    def parse_class_type(self, data_name, data_type):
        fqn = self.user_class.get_fqn(data_type)
        data_class = self.get_inner_class(fqn)
        if data_class is not None:
            dtype = data_class.name
            if dtype.startswith('TL_'):
                constructor = self.java_parser.get_constructor(data_class)
                if constructor is None:
                    raise TypeError(f'Class {fqn} has not constructor.')
                struct_type = f"self.struct_{constructor}()"
            else:
                sname = name_convert_to_snake(dtype)
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
            fqn = self.user_class.get_fqn(class_name)
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
            return (self.parse_class_type(data_name, class_name), False)
        else:
            field = self.fields.get(field_name)
            if field is None:
                self.logger.error('parse_field_type: can not find field %s',
                                  field_name)
                return None
            if (is_array := (field.type.name == 'ArrayList')):
                field = field.type.arguments[0]
            field_type = field.type.name
            full_type = field_type
            
            try:
                if (field_sub_type := field.type.sub_type.name):
                    full_type = f'{field_type}.{field_sub_type}'
            except AttributeError:
                pass
            return (self.parse_class_type(field_name, full_type), is_array)

    @classmethod
    def is_member_reference_or_cast(cls, obj):
        return cls.is_member_reference(obj) or cls.is_cast(obj)

    def parse_statement_expression_w(self, statement):
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
                        print(self.name, argument)
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
            elif qualifier == 'Vector':
                argument = arguments[1]
                data_name = argument.member
                dname = name_convert_to_snake(data_name)
                data_type = None
                if member == 'serialize':
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
                elif member == 'serializeInt':
                    data_type = 'Int32ul'
                elif member == 'serializeLong':
                    data_type = 'Int64ul'
                elif member == 'serializeString':
                    data_type = 'TString'
                if data_type:
                    struct_type = f"self.vector({data_type}, '{data_name}')"
                    return (dname, struct_type)
            elif not qualifier and member == 'writeAttachPath':
                return ('attach_path', 'TString')
            else:
                if member == 'serializeToStream':
                    try:
                        struct_type, is_array = self.parse_field_type(qualifier)
                    except Exception as e:
                        print('Parse statement error',
                              self.name, statement, self.user_class)
                        raise e
                    dname = name_convert_to_snake(qualifier.replace('.', '_'))
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

    def parse_statement_expression_r(self, statement):
        expression = statement.expression
        if self.is_assignment(expression):
            memberl = expression.expressionl.member
            value = expression.value
            if self.is_method_invocation(value):
                qualifier = value.qualifier
                member = value.member
                if qualifier == 'stream':
                    struct_name = memberl
                    data_type = get_stream_type(member, struct_name)
                    if struct_name in ('flags', 'flags2'):
                        return (struct_name, f'FlagsEnum({data_type}')
                    else:
                        struct_type = data_type
                        return (struct_name, struct_type)
                elif qualifier == 'Vector':
                    struct_name = memberl
                    struct_type = None
                    if member == 'deserialize':
                        stype = value.arguments[1]
                        argument_member = stype.expression.member
                        struct_type = self.parse_class_type(struct_name,
                                                            argument_member)
                        if not struct_type:
                            raise ValueError(f'Parse java type error: {argument_member}')
                    elif member == 'deserializeInt':
                        struct_type = 'Int32ul'
                    elif member == 'deserializeLong':
                        struct_type = 'Int64ul'
                    elif member == 'deserializeString':
                        struct_type = 'TString'
                    if struct_type:
                        struct_type = f"self.vector({struct_type}, '{struct_name}')"
                        return (struct_name, struct_type)
                elif member == 'TLdeserialize':
                    sname = memberl
                    stype = name_convert_to_snake(qualifier)
                    ret = {'name': sname, 'type': stype}
            elif self.is_binary_operation(value):
                member = value.operandl.operandl.member
                mask = value.operandl.operandr.value
                if member.startswith('is'):
                    flag_tag = name_convert_to_snake(member)
                else:
                    flag_tag = f'is_{member}'
                self.add_flags(memberl, flag_tag, mask)
                return Tag.FLAGS_TAG


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

    def parse_if_statement_w(self, statement):
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
                                      self.name,
                                      statement, e)
                    raise e
                else:
                    self.logger.error('Class %s, statement %s, error %s',
                                      self.name,
                                      statement, e)
                return []
        else:
            t = type(condition.operandl).__name__
            msg = f'Condition left type is {t}'
            if self.strict:
                raise TypeError(msg)
            else:
                self.logger.error(msg)

    def parse_if_statement_r(self, statement):
        result = []
        condition = statement.condition
        operandl = condition.operandl
        if self.is_binary_operation(operandl):
            condition_member = operandl.operandl.member
            condition_value = operandl.operandr.value
            then_statements = statement.then_statement.statements
            result_list = self._parse_read_param(then_statements)
            c_m = condition_member
            for item in result_list:
                struct_name, data_type = item
                f_n = f'has_{struct_name}'
                fnn = self.add_flags(c_m, f_n, condition_value)
                struct_type = f'If(this.{c_m}.{fnn}, {data_type})'
                result.append((struct_name, struct_type))
            return result

    def _parse_serialize(self, statements):
        assert (not self.content_0x1cb5c415)
        result = []
        for item in statements:
            if self.content_0x1cb5c415:
                self.content_0x1cb5c415.append(item)
                if self.is_for_statement(item):
                    res = self.parse_vector()
                    if res is None:
                        raise ValueError(repr(item))
                    self.content_0x1cb5c415.clear()
                    result.append(res)
                continue  # pylint: disable=E275
            if self.is_statement_expression(item):
                res = self.parse_statement_expression_w(item)
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
                res = self.parse_if_statement_w(item)
                if res is None:
                    raise ValueError(repr(item))
                result.extend(res)
        return result

    def _parse_read_param(self, statements):
        result = []
        for item in statements:
            if self.is_statement_expression(item):
                res = self.parse_statement_expression_r(item)
                if res is None:
                    raise ValueError('++++++++++++++++++' + repr(item))
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

    def parse_serialize_to_stream(self):
        method = self.methods['serializeToStream']
        result = self._parse_serialize(method.body)
        self.struct.extend(result)

    def parse_read_param(self):
        method = self.methods['readParams']
        result = self._parse_read_param(method.body)
        self.struct.extend(result)

    def parse_deserialize(self):
        method = self.methods['TLdeserialize']
        for item in method.body:
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
                            case_fqn = self.user_class.get_fqn(case_qualifier)
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

    def generate(self):
        ret = self.parse()
        if ret is None:
            return None
        if not self.info:
            self.logger.error('Class %s parse failed', self.name)
            return None
        result = []
        if self.struct:
            result.append(get_struct_content(self.info))
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
        self.java_info = {}
        self.class_info = {}
        self.i_class_info = {}
        self.ii_class_info = {}
        self.cid_info = {}
        self.LAYER = None
        self.logger.debug("Parsing %s", osp.basename(path))
        self.tree = parse_java_file(path)
        self.package = self.tree.package.name  # 获取包名
        self.java_info[path] = self.tree
        # 获取包名下的其他文件
        java_path_regex = re.compile(f'^{self.package}\.(.+)$', re.M)
        for item in self.tree.imports:
            java_path = item.path
            if not (m := java_path_regex.fullmatch(java_path)):
                continue
            relpath = m.group(1).replace('.', os.sep)
            item_path = osp.join(value, f'{relpath}.java')
            if not osp.isfile(item_path):
                self.logger.warning("Not found %s", item_path)
                continue
            self.logger.debug("Parsing %s", osp.basename(item_path))
            tree = parse_java_file(item_path)
            self.java_info[item_path] = tree

        # 获取包名下的所有大类
        for java_path, java_data in self.java_info.items():
            for item in (x for x in java_data.types if is_class(x)):
                obj = UserClassDeclaration(java_data, item)
                self.class_info[obj.fqn] = obj

        # 解析 LAYER
        self.main = self.class_info['org.telegram.tgnet.TLRPC']
        self.LAYER = get_class_value(self.main.decl, 'LAYER')
        self.logger.debug('%s = %d', 'LAYER', self.LAYER)

        for k, v in self.class_info.items():
            inner_classes = [x for x in v.decl.body if is_class(x)]
            self.logger.debug("Parsing %s from %s", len(inner_classes), k)
            for item in inner_classes:
                obj = UserClassDeclaration(v.c_unit, item, v)
                self.i_class_info[obj.fqn] = obj

        for k, v in self.i_class_info.items():
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
            self.ii_class_info[k] = v

        for k, v in self.ii_class_info.items():
            conv = get_class_value(v.decl, 'constructor')
            if conv is not None:
                self.cid_info[k] = f'0x{conv:08x}'

        self.logger.debug('TLRPC files contain class count %d', len(self.ii_class_info))
        self._directory = value

    def get_inner_class(self, fqn: str):
        if isinstance(fqn, UserClassDeclaration):
            return fqn
        return self.i_class_info.get(fqn)

    def get_extends_list(self, fqn: str):
        if (inner_class := self.get_inner_class(fqn)) is None:
            return None
        parents = []
        cur = inner_class
        for i in range(20):
            if not (extends := cur.extends):
                break
            parents.append(extends)
            if not (cur := self.get_inner_class(extends)):
                break
        return parents

    def get_fields(self, fqn: str, recursive=True):
        if (inner_class := self.get_inner_class(fqn)) is None:
            return None
        fields = {x.declarators[0].name: x for x in inner_class.decl.fields}
        if not recursive:
            return fields
        for extends in self.get_extends_list(inner_class):
            if (extends_class := self.get_inner_class(extends)) is None:
                break
            for extends_field in extends_class.decl.fields:
                field_name = extends_field.declarators[0].name
                if field_name not in fields:
                    fields[field_name] = extends_field
        return fields

    def get_methods(self, fqn: str, recursive=True):
        if (inner_class := self.get_inner_class(fqn)) is None:
            return None
        methods = {x.name: x for x in inner_class.decl.methods}
        if not recursive:
            return methods
        for extends in self.get_extends_list(inner_class):
            if (extends_class := self.get_inner_class(extends)) is None:
                break
            for extends_method in extends_class.decl.methods:
                method_name = extends_method.name
                if method_name not in methods:
                    methods[method_name] = extends_method
        return methods

    def get_constructor(self, fqn: str) -> str:
        if not (cl := self.get_inner_class(fqn)):
            return cl
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
        if cid and (index := eval(cid)) in self.cache:
            res = self.cache[index]
            ret = [res.format_map({'name': sname})]
        else:
            try:
                ret = obj.generate()
            except Exception as e:
                print(f'Generate class {fqn} error', e)
                if str(e).startswith('get_field_type'):
                    raise e
                # raise e
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
        for k in self.ii_class_info:
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
        for k in self.ii_class_info:
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

    def merge_tlrpc(self, path, target):
        parse_result = {}
        for k in self.ii_class_info:
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
                                    mv = PATTERN1.search(parse_result[i]).group(2)
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
    def remove_dup(cls, path, target, all_same=True):
        with open(path, encoding='utf-8') as f:
            c = f.read()
        func_map = {}
        start = 0
        with open(target, 'w+', encoding='utf-8') as f:
            for item in FUNCTION_PATTERN.finditer(c):
                f.write(c[start:item.start()])
                func_name = item.group(1)
                if func_name not in func_map:
                    func_map[func_name] = item.group(0)
                    f.write(item.group(0))
                else:
                    if all_same:
                        if not func_map[func_name] == item.group(0):
                            f.write(item.group(0))
                start = item.end()
            else:
                f.write(c[start:])

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
            if ('structures' in func_name or func_name.startswith('struct_')) and not func_name == 'vector':
                if func_name not in parse_result:
                    parse_result[func_name] = item.group(0)
                    start = item.end()
                else:
                    print(f'{func_name} has exists.')
        # print(''.join(left))
        # return
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
        assert (len(left_names) == (len(parse_result) - len(sorted_names)))
        left_text = '\r\n\r\n'.join(parse_result[x] for x in left_names)
        result_text = ''
        result_text += ''.join(left)
        result_text += header_text
        result_text += sorted_text
        result_text += left_text
        save_code(target, result_text, pep8=True,
                  options={'max_line_length': 119})

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
    # path = r"utils\files\TLRPC-9.4.5-152-810bc4ae.java"
    # path = r"utils\files\TLRPC-10.9.1-176-d62d2ed5.java"
    # path = r"utils\files\TLRPC-11.7.0-198-eee720ef.java"
    path = r"E:\Project\Godsix\teleparser\utils\Telegram\TMessagesProj\src\main\java\org\telegram\tgnet"
    parser = JavaParser(path, level=logging.INFO, strict=False)
    parser.merge_tlrpc(r'E:\Project\Godsix\teleparser\datatype\telegram.py',
                       r'E:\Project\Godsix\teleparser\new.py')
    # content = parser.get_class_struct('org.telegram.tgnet.tl.TL_stories.TL_togglePinnedToTop')
    # 
    # content = parser.get_class_struct('org.telegram.tgnet.TLRPC.TL_pageBlockEmbedPost_layer82')
    # if content:
    #     print(content[0])

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    test()
