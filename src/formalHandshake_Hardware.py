#import formalHandshake
from __future__ import annotations
import re
#from typing import Union, List, Dict, Tuple, Any
from typing import List, Dict, Any, Union
from pathlib import Path

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import copy

from formalHandshake import Function
from formalHandshake import IOPort
from formalHandshake import Parameter
from formalHandshake import Module
from formalHandshake import eval_if_pure_numeric


## Helper function to collect the full SpinalHDL description of a given Component
def extract_definition(file_path: str, target_name: str) -> list[str] | None:
    # Matches: class Foo, case class Bar, object Baz, case object Qux
    _DECL_RE = re.compile(
        r"""
        ^\s*(?:case\s+)?                           # optional 'case'
        (?P<kind>class|object)\s+                  # class or object
        (?P<name>[A-Za-z_]\w*)\b                   # identifier
        """,
        re.MULTILINE | re.VERBOSE,
    )

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Join for regex matching, but keep line boundaries
    text = "".join(lines)

    # Find the declaration of the target
    for m in _DECL_RE.finditer(text):
        if m.group("name") == target_name:
            start_index = text[:m.start()].count("\n")   # line number of match
            break
    else:
        return None  # not found

    # Starting at the matched line, extract the full block
    result = []
    brace_level = 0
    started = False

    for line in lines[start_index:]:
        result.append(line)

        # Detect start of body (the first '{')
        if "{" in line and not started:
            brace_level += line.count("{")
            brace_level -= line.count("}")
            started = True
            continue

        # Already inside body
        if started:
            brace_level += line.count("{")
            brace_level -= line.count("}")

            # When brace level drops to 0, the definition is complete
            if brace_level <= 0:
                break

        # Case where the class/object is one-liner without braces
        # (e.g., "class X")
        if not started and "{" not in line:
            # A class without a body → return just that line
            break
    return [line.rstrip("\n") for line in result]

## Returns a list of SpinalHDL code lines, for the class definition of a given class in a given file
def getSpinalHDLClassDefinition(filePath: str, className: str):
    #"""Extract SpinalHDL class definition and constructor parameters with types and defaults."""

    #with open(filePath, 'r') as f:
    #    lines = f.readlines()
    #    class_lines = []
    #    collecting = False
    #    brace_level = 0
#
    #    for line in lines:
    #        if not collecting:
    #            if re.search(rf'\bclass\s+{className}\b.*Component', line):
    #                collecting = True
    #                brace_level = line.count("{") - line.count("}")
    #                class_lines.append(line.rstrip())
    #        else:
    #            brace_level += line.count("{") - line.count("}")
    #            class_lines.append(line.rstrip())
    #            if brace_level == 0:
    #                break
#
    #    return class_lines

    with open(filePath, 'r') as f:
        lines = f.readlines()

    class_lines = []
    collecting_header = False   # we're between `class X` and the first `{`
    collecting_body = False     # we've seen `{` and confirmed it's a Component
    header_text = ""            # full header (possibly multi-line)
    brace_level = 0

    for line in lines:
        line_stripped = line.rstrip('\n')

        # ---- Already collecting the body of the component ----
        if collecting_body:
            brace_level += line.count("{") - line.count("}")
            class_lines.append(line_stripped)
            if brace_level == 0:
                # finished the class definition
                return class_lines
            continue

        # ---- Collecting multi-line header (`class X ...` up to first `{`) ----
        if collecting_header:
            header_text += line
            class_lines.append(line_stripped)

            if '{' in line:
                # Header completed – now decide if it's a Component
                if re.search(r'\bextends\b[\s\S]*\bComponent\b', header_text):
                    collecting_header = False
                    collecting_body = True
                    brace_level = line.count("{") - line.count("}")
                    if brace_level == 0:
                        # Edge case: `{}` on same line and nothing else
                        return class_lines
                else:
                    # Not a Component: discard and reset
                    collecting_header = False
                    class_lines = []
                    header_text = ""
            continue

        # ---- Not currently collecting anything: look for `class <className>` ----
        if re.search(rf'\bclass\s+{re.escape(className)}\b', line):
            collecting_header = True
            header_text = line
            class_lines = [line_stripped]

            if '{' in line:
                # Single-line header (no multi-line params) – decide immediately
                if re.search(r'\bextends\b[\s\S]*\bComponent\b', header_text):
                    collecting_header = False
                    collecting_body = True
                    brace_level = line.count("{") - line.count("}")
                    if brace_level == 0:
                        return class_lines
                else:
                    # class Foo, but not a Component
                    collecting_header = False
                    class_lines = []
                    header_text = ""
            continue

    # If we get here, we didn't find a matching Component class
    return []

## Takes a SpinalHDL description and returns a list of parameters belonging to the corresponding blackbox module
def extract_spinalhdl_parameters(class_lines, module: formalHandshake_Hardware.Hardware_Module):
    """Extract parameters from a SpinalHDL class constructor."""
    parameters = []
    class_def = ""

    # Join all class declaration lines (in case it's multiline)
    in_class_def = False
    for line in class_lines:
        stripped = line.strip()

        # Start when we first see "class "
        if not in_class_def and stripped.startswith("class "):
            in_class_def = True
        if in_class_def:
            # Remove line comment part for structure parsing
            code_part = stripped.split("//", 1)[0].strip()
            class_def += code_part + " "
            # Stop once we hit a ')' in the *code* (not in the comment)
            if ")" in code_part:
                break

    # Match parameters inside the class(...) constructor
    param_pattern = re.compile(r'(?:val\s+)?(\w+)\s*:\s*(\w+)(?:\s*=\s*([^,\)]+))?')
    params_match = re.search(r'class\s+\w+\s*\((.*)\)', class_def)
    if params_match:
        param_str = params_match.group(1)
        for match in param_pattern.finditer(param_str):
            name, ptype, default = match.groups()
            parameter = Parameter(name, module, ptype, default.strip() if default else None, None)
            parameters.append(parameter)
    return parameters

## standalone SpinalHDL Type Parser
def analyze_type_expression(expr: str, parameters: List[Parameter]) -> Dict[str, Any]:
    param_ids = []
    for parameter in parameters:
        param_ids.append(parameter.id)

    vec_dims = []

    def split_vec_content(content: str):
        depth = 0
        for i, c in enumerate(content):
            if c == ',' and depth == 0:
                return content[:i], content[i+1:]
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
        return content, ''

    expr = expr.strip()
    while expr.startswith("Vec("):
        inner, length = split_vec_content(expr[4:-1])
        vec_dims.append(length.strip())
        expr = inner.strip()

    def parse_base(expr: str):
        match = re.match(r'(\w+)\((.*)\)', expr)
        if not match:
            return expr.strip(), None
        base, width_expr = match.groups()
        width_expr = width_expr.strip()
        width_match = re.match(r'([\w\d_]+)\s+bits', width_expr)
        if width_match:
            return base.strip(), width_match.group(1).strip()
        clean_width = re.sub(r'\bbits\b', '', width_expr).strip()
        return base.strip(), clean_width if clean_width else None

    base_type, width = parse_base(expr)

    all_exprs = vec_dims + ([width] if width else [])

    parameters = [p for p in param_ids if any(p in e for e in all_exprs)]

    return {
        "base_type": base_type,
        "width": width,
        "vec_dims": reversed(vec_dims),
        "parameters": parameters
    }

## Extracts the IOs from thr SpinalHDL description of a component in order to build and connect a blackbox module with the corresponding input and output ports
def parse_spinal_ios(code_lines: List[str], parameters: List[Parameter]) -> List[Dict[str, Any]]:
    io_defs = []

    def extract_io(line: str, name_prefix: str):
        match = re.match(r'\s*val\s+(\w+)\s*=\s*(in|out|inout)\s+(.*)', line)
        if not match:
            return
        name, direction, type_expr = match.groups()
        full_name = f"{name_prefix}.{name}" if name_prefix else name

        analysis = analyze_type_expression(type_expr, parameters)

        io_defs.append({
            "name": full_name,
            "direction": direction,
            "type_expression": type_expr,
            "type": analysis["base_type"],
            "width": analysis["width"],
            "vec_dims": analysis["vec_dims"],
            "parameters": analysis["parameters"]
        })

    def parse_bundle(start_index: int, name_prefix: str):
        i = start_index
        while i < len(code_lines):
            line = code_lines[i].strip()
            if line.startswith("val "):
                extract_io(code_lines[i], name_prefix)
            elif re.match(r'val\s+(\w+)\s*=\s*new\s+Bundle\s*{', line):
                sub_bundle_name = re.match(r'val\s+(\w+)', line).group(1)
                i = parse_bundle(i + 1, f"{name_prefix}.{sub_bundle_name}")
            elif line == "}":
                return i
            i += 1
        return i

    for i, line in enumerate(code_lines):
        if re.match(r'\s*val\s+io\s*=\s*new\s+Bundle\s*{', line):
            parse_bundle(i + 1, "io")
            break
    return io_defs


class formalHandshake_Hardware:
    ## Makro for comparing two hardware types, returns True/False if equal/unequal.
    def compareHardwareTypes(type1: str, type2: str):
        #print(F'Checking if {type1} = {type2}')
        if type1 == type2:
            return True
        if ((type1 == 'Bool()' or type1 == 'Bits(1 bits)' or type1 == 'UInt(1 bits)') and (type2 == 'Bool()' or type2 == 'Bits(1 bits)' or type2 == 'UInt(1 bits)')):
            return True
        return False

    ## Makro for checking if something is a valid hardware IOPort or Function
    def isHardwareSignal(variable: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
        return True

    ## Makro for checking if something is a valid hardware IOPort or Function of type 'Bool()'
    def isBoolean(variable: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
        # type ? if not formalHandshake_Hardware.compareHardwareTypes(variable.type, 'Bool()'):
        if not formalHandshake_Hardware.compareHardwareTypes(variable.getType(), 'Bool()'):
            raise TypeError(F'variable "{variable.id}" of type {variable.getType()} is not of Type Bool')
        return True

    ## Makro to get SpinalHDL code name for a signal source:
    def getSpinalHDLSource(signal: formalHandshake_Hardware.Hardware_IOPort, toplevel: formalHandshake_Hardware.Hardware_Module) -> str:
        if isinstance(signal, formalHandshake_Hardware.Hardware_Function):
            if not signal.parent == toplevel:
                raise ValueError(F'Signal {signal.parent.id}.{signal.id} is function and has to belong to toplevel {toplevel.id}, in order to get the spinalHDL source')
            return signal.id
        else:
            source = signal.source
            if isinstance(source, formalHandshake_Hardware.Hardware_Function):
                return source.id
            if isinstance(source, formalHandshake_Hardware.Hardware_IOPort):
                if source.parent == toplevel:
                    return source.id
                else:
                    return F'{source.parent.id}.{source.id}'

    ## Splits a given hardware type from a single string description (Like in SpinalHDL) into the base type, the bitwidth and passoble vector dimensions
    def checkType(type: str):   
        typeDef = analyze_type_expression(type, [])
        #print(typeDef['base_type'], typeDef['width'], typeDef['vec_dims'], typeDef['parameters'])
        baseType = typeDef['base_type']
        width = typeDef['width']   # ?! not none but []?
        vectorDimensions = []
        for dim in typeDef['vec_dims']:
            vectorDimensions.append(dim)
        return [baseType, width, vectorDimensions]

    ## Evaluates correct encoding format for a given constant value of a given type and possibly converts it to the tols internal format
    def typeCheckValue(type: str, value: Union[str, int], allowUnknown: bool = True):
        typeCeck = formalHandshake_Hardware.checkType(type)
        #print(F'typeCheckValue: type "{type}" with value "{value}" -> [{typeCeck[0]}, {typeCeck[1]}]')
        knownType = False
        valid = False

        if type == F'Bool()':
            knownType = True
            if isinstance(value, str):
                if value == 'False' or value == 'B"0"':
                    value = 'False'
                    valid = True
                if value == 'True' or value == 'B"1"':
                    value = 'True'
                    valid = True
        
        if typeCeck[0] == 'Bits': 
            knownType = True
            if isinstance(value, str):
                # Precompile regex patterns
                PATTERN_LITERAL = re.compile(r'^B"([01]+)"$')
                PATTERN_NUMERIC = re.compile(r'^B\(\s*(\d+)\s*,\s*(\d+)\s*bits\s*\)$')

                # Try literal format: B"0101"
                m = PATTERN_LITERAL.fullmatch(value)
                if m:
                    valid = True
                else:
                    # Try numeric format: B(3, 5 bits)
                    m = PATTERN_NUMERIC.fullmatch(value)
                    if m:
                        val = int(m.group(1))
                        length = int(m.group(2))

                        # Validate that val fits in given bit length
                        if val >= (1 << length):
                            raise ValueError(f"value {val} does not fit in {length} bits")
                        else:
                            value = F'B"{format(val, f'0{length}b')}"'
                            valid = True
                            #print(F' -> !! converted {oldValue} to {value} !!')
            else:
                value = F'B"{format(value, f'0{typeCeck[1]}b')}"'
                valid = True
        
        if typeCeck[0] == 'UInt': 
            knownType = True
            if isinstance(value, str):
                # Precompile regex patterns
                PATTERN_LITERAL = re.compile(r'^U"([01]+)"$')
                PATTERN_NUMERIC = re.compile(r'^U\(\s*(\d+)\s*,\s*(\d+)\s*bits\s*\)$')

                # Try literal format: U"0101"
                m = PATTERN_LITERAL.fullmatch(value)
                if m:
                    valid = True
                else:
                    # Try numeric format: U(3, 5 bits)
                    m = PATTERN_NUMERIC.fullmatch(value)
                    if m:
                        val = int(m.group(1))
                        length = int(m.group(2))

                        # Validate that val fits in given bit length
                        if val >= (1 << length):
                            raise ValueError(f"value {val} does not fit in {length} bits")
                        else:
                            value = F'U"{format(val, f'0{length}b')}"'
                            valid = True
                            #print(F' -> !! converted {oldValue} to {value} !!')
            else:
                value = F'U"{format(value, f'0{typeCeck[1]}b')}"'
                valid = True

        if typeCeck[0] == 'SInt': 
            knownType = True
            if isinstance(value, str):
                # Precompile regex patterns
                PATTERN_LITERAL = re.compile(r'^S"([01]+)"$')
                PATTERN_NUMERIC = re.compile(r'^S\(\s*(\d+)\s*,\s*(\d+)\s*bits\s*\)$')

                # Try literal format: S"0101"
                m = PATTERN_LITERAL.fullmatch(value)
                if m:
                    valid = True
                else:
                    # Try numeric format: S(3, 5 bits)
                    m = PATTERN_NUMERIC.fullmatch(value)
                    if m:
                        val = int(m.group(1))
                        length = int(m.group(2))

                        # Validate that val fits in given bit length
                        if val >= (1 << length):
                            raise ValueError(f"value {val} does not fit in {length} bits")
                        else:
                            value = F'S"{format(val, f'0{length}b')}"'
                            valid = True
                            #print(F' -> !! converted {oldValue} to {value} !!')
            else:
                value = F'S"{format(value, f'0{typeCeck[1]}b')}"'
                valid = True

        if not knownType:
            if allowUnknown:
                print(F'!! Warning: value "{value}" has unknown type "{type}"')
            else:
                raise TypeError(F'!! Warning: value "{value}" has unknown type "{type}"')
            return False
        if not valid:
            if allowUnknown:
                print(F'!! Warning: value with type "{type}" has unknown value encoding "{value}"')
            else:
                raise ValueError(F'!! Warning: value with type "{type}" has unknown value encoding "{value}"')
            return False
        return value

    ## Converts an int into a string representing the equivalent unsigned bit encoding in a given numer of bits
    def intToBit(n, bits):
        mask = (1 << bits) - 1
        return (n & mask)

    ## converts a string representing a bit number into the equivalent integer
    def strBitToInt(s: str) -> str:
        _LITERAL_RE = re.compile(r'^([BUS])"([01]+)"$')

        s = s.strip()
        m = _LITERAL_RE.fullmatch(s)
        if not m:
            return False
            #raise ValueError(f"Not a valid bit encoded value: {s}")

        kind = m.group(1)      # B, U, S
        bit_str = m.group(2)
        width = len(bit_str)

        value = int(bit_str, 2)

        # Handle signed (two's complement)
        if kind == 'S' and bit_str[0] == '1':
            value -= (1 << width)

        return f"{kind}({value}, {width} bits)"

    ## Converts an int into a string representing the equivalent signed bit encoding in a given numer of bits
    def toSigned(n, bits):
        if n & (1 << (bits - 1)):  # sign bit set
            return n - (1 << bits)
        return n


    ## The base class for formal statements representing a boolean property
    class Harware_Formal_Statement():
        def __init__(self, booleanProperty: Union[str, formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], parent: formalHandshake_Hardware.Hardware_Module):
            if isinstance(booleanProperty, str):
                self.booleanProperty = booleanProperty
            else:
                if not formalHandshake_Hardware.isBoolean(booleanProperty):
                    raise TypeError(F'Cannot make formal statements with non-boolean values. ({booleanProperty.parent.id}.{booleanProperty.id})')
                self.booleanProperty = booleanProperty.id
                #formalHandshake_Hardware.getSpinalHDLSource(booleanProperty, parent)
            self.condition = None
            self.parent = parent

        ## Adds a condition to the property
        def on(self, condition: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            if not formalHandshake_Hardware.isBoolean(condition):
                raise TypeError(F'Cannot make formal statements with a non-boolean condition. ({condition.parent.id}.{condition.id})')
            if not (condition.parent == self.parent or (condition in condition.parent.outputs and condition.parent.parent == self.parent)):
                raise ValueError(F'Cannot make formal statements with boolean condition {condition.parent.id}.{condition.id} from outside of parent module {self.parent.id}')
            self.condition = condition
            return self

        ## Placeholder for specific generation of a formal statements system verilog assertion in SpinalHDl Code
        def toSpinalHDL(self):
            raise NotImplementedError(F'{self.booleanProperty} is not implemented')

    ## Interprets the boolean property as an initial assumption
    class InitialAssumtion(Harware_Formal_Statement):
        def toSpinalHDL(self):
            return F'            assumeInitial({self.booleanProperty})'

    ## Interprets the boolean property as an assumption
    class Assumption(Harware_Formal_Statement):
        def toSpinalHDL(self):
            line = F'            assume({self.booleanProperty})'
            if not self.condition == None:
                #line = (F'            when({formalHandshake_Hardware.getSpinalHDLSource(self.condition, self.parent)})' + '{\n    ' + line + '\n            }')
                line = (F'            when({self.condition.id})' + '{\n    ' + line + '\n            }')
            return line

    ## Interprets the boolean property as an assertion
    class Assertion(Harware_Formal_Statement):
        def toSpinalHDL(self):
            line = F'            assert({self.booleanProperty})'
            if not self.condition == None:
                #line = (F'            when({formalHandshake_Hardware.getSpinalHDLSource(self.condition, self.parent)})' + '{\n    ' + line + '\n            }')
                line = (F'            when({self.condition.id})' + '{\n    ' + line + '\n            }')
            return line

    ## Interprets the boolean property as a cover statement
    class Cover(Harware_Formal_Statement):
        def toSpinalHDL(self):
            line = F'            cover({self.booleanProperty})'
            if not self.condition == None:
                line = (F'            when({self.condition.id})' + '{\n    ' + line + '\n            }')
            return line



    ## Hardware Version of IOPort, expecting specific type
    class Hardware_IOPort(IOPort):
        def __init__(self, id: str, parent: Union[formalHandshake_Hardware.Hardware_Module, formalHandshake_Hardware.Hardware_Function], type: str, keyword: str = None):
            super().__init__(id, parent, keyword)
            typeDef = analyze_type_expression(type, parent.parameters)
            #print(typeDef['base_type'], typeDef['width'], typeDef['vec_dims'], typeDef['parameters'])
            self.baseType = typeDef['base_type']
            self.width = [typeDef['width'], None]   # ?! not none but []?
            self.vectorDimensions = []
            for parameter in parent.parameters:
                if not typeDef['width'] == None:
                    if re.search(rf"\b{re.escape(parameter.id)}\b", typeDef['width']):
                        if self.width[1] == None:
                            self.width[1] = []
                        self.width[1].append(parameter)
                        self.parameters.append(parameter)
            for dim in typeDef['vec_dims']:
                dimension = [dim, None]
                for parameter in parent.parameters:
                    if isinstance(dim, str) and re.search(rf"\b{re.escape(parameter.id)}\b", dim):
                        if dimension[1] == None:
                            dimension[1] = []
                        dimension[1].append(parameter)
                        self.parameters.append(parameter)
                self.vectorDimensions.append(dimension)

            self.type = F'{id}_type'
            self.isFormal = False

            self.solved = False
            self.result = None

        ## Set hardware specific type
        def setType(self, type:str):
            typeDef = analyze_type_expression(type, self.parent.parameters)
            self.baseType = typeDef['base_type']
            self.width = [typeDef['width'], None]
            self.vectorDimensions = []
            for parameter in self.parent.parameters:
                if not typeDef['width'] == None:
                    if re.search(rf"\b{re.escape(parameter.id)}\b", typeDef['width']):
                        if self.width[1] == None:
                            self.width[1] = []
                        self.width[1].append(parameter)
                        self.parameters.append(parameter)
            for dim in typeDef['vec_dims']:
                dimension = [dim, None]
                for parameter in self.parent.parameters:
                    if isinstance(dim, str) and re.search(rf"\b{re.escape(parameter.id)}\b", dim):
                        if dimension[1] == None:
                            dimension[1] = []
                        dimension[1].append(parameter)
                        self.parameters.append(parameter)
                self.vectorDimensions.append(dimension)

        ## Get hardware specific type
        def getType(self, reference: bool = False):
            type = ''
            for dimension in self.vectorDimensions:
                type = type + 'Vec('
            width = ''
            if not self.width[0] == None:
                if self.width[1] == None:
                    width = F'{self.width[0]} bits'
                else:
                    width = self.width[0]
                    ## is parent not toplevel?
                    if not self.parent.parent == None:
                        for param in self.width[1]:
                            width = re.sub(rf"\b{re.escape(param.id)}\b", str(param.getValue(reference)), width)
                        width = eval_if_pure_numeric(width)
                        width = F'{width} bits'
            type = (type + F'{self.baseType}({width})')
            for dimension in self.vectorDimensions:
                if dimension[1] == None:
                    ## no parameter
                        type = type + F', {dimension[0]})'
                else:
                    ## is parent toplevel?
                    type = type + F', {dimension[0]})'
                    if not self.parent.parent == None:
                        for param in dimension[1]:
                            type = re.sub(rf"\b{re.escape(param.id)}\b", str(param.getValue(reference)), type)
                        type = eval_if_pure_numeric(type)
            return type

            ## Set formalMarker to true -> function is only generated in formal proof block

        ## check if type is 'Bool()'
        def isBoolean(self):
            return (self.getType() == 'Bool()')

        ## mark as formal to be included only in a formal block, but not the actual design
        def formal(self):
            self.isFormal = True
            self.unmarked = True
            return self

        ## Generate a copy of this IOPort
        def copy(self, id: str, newParent: Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_Module]):
            return formalHandshake_Hardware.Hardware_IOPort(id, newParent, self.getType())

    ## Hardware Version of Function, expecting specific type
    class Hardware_Function(Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str, cycles: int, keyword: str = None):
            super().__init__(id, parent, keyword)
            self.cycles = cycles      # number of cycles to execute
            typeDef = analyze_type_expression(type, parent.parameters)
            #print(typeDef['base_type'], typeDef['width'], typeDef['vec_dims'], typeDef['parameters'])
            self.baseType = typeDef['base_type']
            self.width = [typeDef['width'], None]
            self.vectorDimensions = []
            for parameter in parent.parameters:
                if typeDef['width'] == parameter.id:
                    self.width[1] == parameter
            for dim in typeDef['vec_dims']:
                dimension = [dim, None]
                for parameter in parent.parameters:
                    if dim == parameter.id:
                        dimension[1] = parameter
                self.vectorDimensions.append(dimension)

            #self.type = type
            self.type = F'{id}_type'
            self.isFormal = False

            self.solved = False
            self.result = None

        ## Set hardware specific type
        def setType(self, type:str):
            typeDef = analyze_type_expression(type, self.parent.parameters)
            self.baseType = typeDef['base_type']
            self.width = [typeDef['width'], None]
            self.vectorDimensions = []
            for parameter in self.parent.parameters:
                if typeDef['width'] == parameter.id:
                    self.width[1] == parameter
            for dim in typeDef['vec_dims']:
                dimension = [dim, None]
                for parameter in self.parent.parameters:
                    if dim == parameter.id:
                        dimension[1] = parameter
                self.vectorDimensions.append(dimension)

        ## Get hardware specific type
        def getType(self, reference: bool = False):
            type = ''
            for dimension in self.vectorDimensions:
                type = type + 'Vec('
            width = ''
            if not self.width[0] == None:
                if self.width[1] == None:
                    width = F'{self.width[0]} bits'
                else:
                    ## is parent toplevel?
                    if self.parent.parent == None:
                        width = F'{self.width[1].id} bits'
                    else:
                        width = F'{self.width[1].getValue(reference)} bits'
            type = (type + F'{self.baseType}({width})')
            for dimension in self.vectorDimensions:
                if dimension[1] == None:
                    ## no parameter
                        type = type + F', {dimension[0]})'
                else:
                    ## is parent toplevel?
                    if self.parent.parent == None:
                        type = type + F', {dimension[1].id})'
                    else:
                        type = type + F', {dimension[1].getValue(reference)})'
            #print(type)
            return type

        ## check if type is 'Bool()'
        def isBoolean(self):
            return (self.getType() == 'Bool()')
        
        ## Makro for adding a input according and directly connecting to a given Hardware Function or IOPort
        def connectInput(self, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            # type ? input = formalHandshake_Hardware.Hardware_IOPort(f'i{len(self.inputs)}', self, source.type)
            input = formalHandshake_Hardware.Hardware_IOPort(f'i{len(self.inputs)}', self, source.getType())
            self.parent.connect(source, input)
            self.inputs.append(input)
            ## when adding inputs -> add corresponding sva property?
            return input

        ## Set formalMarker to true -> function is only generated in formal prrof block
        def formal(self):
            self.isFormal = True
            self.unmarked = True
            for input in self.inputs:
                input.formal()
            return self

        ## Returns a line of SpinalHDL code, defining what this functions is
        def getSpinalHDLInstance(self, code: list):
            for input in self.inputs:
                if input.source == 0:
                    raise ConnectionRefusedError(F'{self.parent.id}.{self.id}.{input.id} is not connected, cannot generate working SpinalHDL Code')
            tab = ''
            if self.isFormal:
                tab = '        '
            code.append(F'{tab}    val {self.id} = {self.getType(True)}')

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            tab = ''
            if self.isFormal:
                tab = '        '
            code.append(F'{tab}    {self.id} := ({self.definition})')

        ## Generate a copy of this Function
        def copy(self, id: str, newParent: formalHandshake_Hardware.Hardware_Module):
            #new = copy.deepcopy(self)
            new = copy.copy(self)
            new.id = id
            new.parent = newParent
            newParent.functions.append(new)
            new.inputs = []
            new.destinations = []
            for input in self.inputs:
                new.inputs.append(input.copy(input.id, new))
            #copy = formalHandshake_Hardware.Hardware_Function(id, newParent, self.getType(), self.cycles)
            #copy.definition = self.definition
            #for input in self.inputs:
            #    copy.inputs.append(input.copy(input.id, copy))
            return new


        ## advanced dataflow analysis
        ## Returns all non-sequentially direct predecessor nodes contained in the same module as self
        def getCombinationalPredecessors(self):
            predecessors = set()
            if self.cycles == 0:
                for input in self.inputs:
                    if isinstance(input.source, IOPort):
                        if isinstance(input.source.parent, Module):
                            ## check if other submodule of same parent and not connected to inputs of parent module
                            if input.source in input.source.parent.outputs:
                                predecessors.add(input.source.parent)
                    if isinstance(input.source, Function):
                        predecessors.add(input.source)
            return predecessors

        ## Iteratively returns all non-sequentially predecessory nodes contained in the same module as self
        def listAllCombinationalPredecessors(self, found=None):
            #print(F"looking for predecessors of: {self.id}")
            if found is None:
                found = set()

            predecessors = set()

            for pred in self.getCombinationalPredecessors():
                if pred not in found:
                    found.add(pred)
                    predecessors.add(pred)
                    predecessors.update(pred.listAllCombinationalPredecessors(found))
            return predecessors

    ## Function sublcass, representing a simple wire
    class Wire(Hardware_Function):
        def __init__(self, id: str, input: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            parent = input.parent
            super().__init__(id, parent, input.getType(), 0)
            i = formalHandshake_Hardware.Hardware_IOPort('input', self, input.getType())
            self.inputs.append(i)
            parent.connect(input, i)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(i, parent)}'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Function sublcass, representing a wire combining multiple signals
    class SplitConnector(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str):
            #print(F'Warning, SplitConnector does not provide proper typechecking yet.')
            super().__init__(id, parent, type, 0)
            self.splitDefinitions: list[str] = []
            self.bitSize = self.width[0]
            self.bitsCollected = 0

        def addSplit(self, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], definition: str):
            if source.parent == None:
                raise ValueError(F'Splitconnector {self.id} cannot add a new split connection to a signal without parent')
            if isinstance(source, formalHandshake_Hardware.Hardware_IOPort):
                if source.parent == self.parent and not source in self.parent.inputs:
                    raise ValueError(F'Splitconnector {self.id} cannot add a new split connection to a parents IO-Port, that is not an input')
                if not (source.parent == self.parent or source.parent.parent == self.parent):
                    raise ValueError(F'Splitconnector {self.id} cannot add a new split connection to a signal, that is not visible in own parent')
            else:
                if not source.parent == self.parent:
                    raise ValueError(F'Splitconnector {self.id} cannot add a new split connection to a function without having the same parent')

            newBits = source.width[0]
            if isinstance(newBits, int) and isinstance(self.bitSize, int):
                if (self.bitsCollected + newBits) > self.bitSize:
                    print(F'!! Warning SplitConnector "{self.parent.id}.{self.id}" has collected more bits (connecting "{source.parent.id}.{source.id}"), than its own type "{self.getType()}" would allow')
                    self.bitsCollected += newBits
            #else:
            #    print(F'!! Warning SplitConnector "{self.parent.id}.{self.id}" has collected bits (connecting "{source.parent.id}.{source.id}"), with unknwon width')

            funcIn = formalHandshake_Hardware.Hardware_IOPort(F'split_{len(self.inputs)}', self, source.getType())
            self.inputs.append(funcIn)
            self.splitDefinitions.append(definition)
            self.parent.connect(source, funcIn)
            return funcIn

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            tab = ''
            if self.isFormal:
                tab = '    '
            if not len(self.inputs) == len(self.splitDefinitions):
                raise ValueError(F"SplitConnector {self.id} does not have the same number of inputs and split definitions")
            for i, input in enumerate(self.inputs):
                code.append(F'{tab}    {self.id}{self.splitDefinitions[i]} := {formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)}')

    ## Prebuild conditional Block hardware function
    class WhenOtherwise(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, when: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], then: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], otherwise: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            if not formalHandshake_Hardware.isBoolean(when):
                raise TypeError(F'Condition for when-else block with id "{id}" has to be of type Bool()')
            # type ? if not formalHandshake_Hardware.compareHardwareTypes(then.type, otherwise.type):
            if not formalHandshake_Hardware.compareHardwareTypes(then.getType(), otherwise.getType()):
                raise TypeError(F'Both possible outputs "{then.parent.id}.{then.id} ({then.getType()})" and ""{otherwise.parent.id}.{otherwise.id} ({otherwise.getType()})"" for when-else block with id "{id}" have to be of same type')
            # type ? type = then.type
            type = then.getType()
            super().__init__(id, parent, type, 0, keyword)
            self.definition = f'when {when.id}, then {then.id}, otherwise {otherwise.id}'

            cond = formalHandshake_Hardware.Hardware_IOPort(f'when', self, 'Bool()')
            i1 = formalHandshake_Hardware.Hardware_IOPort(f'then', self, type)
            i2 = formalHandshake_Hardware.Hardware_IOPort(f'otherwise', self, type)
            self.inputs.append(cond)
            self.inputs.append(i1)
            self.inputs.append(i2)
            parent.connect(when, cond)
            parent.connect(then, i1)
            parent.connect(otherwise, i2)

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            tab = ''
            if self.isFormal:
                tab = '    '
            code.append(F'{tab}    when({formalHandshake_Hardware.getSpinalHDLSource(self.getInput('when'), self.parent)})' + '{')
            code.append(F'{tab}        {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.getInput('then'), self.parent)}')
            code.append(tab + '    }.otherwise{')
            code.append(F'{tab}        {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.getInput('otherwise'), self.parent)}')
            code.append(tab + '    }')

    ## Prebuild Multiplexer hardware function
    class Multiplexer(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str, keyword: str = None):
            super().__init__(id, parent, type, 0, keyword)
            self.definition = f'{type}_Multiplexer'
            select = formalHandshake_Hardware.Hardware_IOPort(f'select', self, f'UInt(1 bits)')
            self.inputs.append(select)

        def select(self):
            return self.getInput('select')

        def connectInput(self, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            # type ? input = formalHandshake_Hardware.Hardware_IOPort(f'i{len(self.inputs) - 1}', self, self.type)
            input = formalHandshake_Hardware.Hardware_IOPort(f'i{len(self.inputs) - 1}', self, self.getType())
            self.parent.connect(source, input)
            ## change select signal type
            if len(self.inputs) > 1:
                # type ? self.inputs[0].type = f'UInt({(len(self.inputs) - 1).bit_length()} bits)'
                self.inputs[0].setType(f'UInt({(len(self.inputs) - 1).bit_length()} bits)')
            self.inputs.append(input)
            ## when adding inputs -> add corresponding sva property?

        ## Returns a line of SpinalHDL code, defining what this functions is
        def getSpinalHDLInstance(self, code = list):
            tab = ''
            if self.isFormal:
                tab = '    '
            # type ? code.append(F'    {self.id} = {self.type}')
            code.append(F'{tab}    val {self.id} = {self.getType()}')

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code = list):
            tab = ''
            if self.isFormal:
                tab = '    '
            if len(self.inputs) < 2:
                raise ValueError(F'Cannot create SpinalHDL code for multiplexer {self.id} with less than one multiplexed input')
            code.append(F'{tab}    switch({formalHandshake_Hardware.getSpinalHDLSource(self.getInput('select'), self.parent)})' + '{')
            bitwidth = (len(self.inputs) - 2).bit_length()
            for i, input in enumerate(self.inputs):
                if i > 0:
                    if i > 1:
                        code.append(F'{tab}        is(U"{format((i-1), f'0{bitwidth}b')}")' + '{')
                        code.append(F'{tab}            {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)}')
                        code.append(tab + '        }')
                    else:
            #if len(self.inputs) > 3:
                        code.append(tab + '        default{')
                        code.append(F'{tab}            {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}')
                        code.append(tab + '        }')
            code.append(tab + '    }')
            ## ? Use muxList instead?!

    ## Prebuild "when, elsewhen, ..., otherwise" variant of a multiplexerlike hardware function
    class Multiconditional(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, default: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], ConditionOutputPairs: list[[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]]], keyword: str = None):
            # type ? type = default.type
            type = default.getType()
            self.conditions = []
            self.outputs = []
            for pair in ConditionOutputPairs:
                condition = pair[0]
                output = pair[1]

                if not (isinstance(condition, Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]) and formalHandshake_Hardware.isBoolean(condition)):
                    raise TypeError(F'Each condition in multiconditional statement has to be of boolean hardware type.')
                self.conditions.append(condition)
                # type ? if not (isinstance(output, Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]) and output.type == type):
                if not (isinstance(output, Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]) and output.getType() == type):
                    raise TypeError(F'Each output in multiconditional statement has to be of the same hardware type as the default case.')
                self.outputs.append(output)

            super().__init__(id, parent, type, 0, keyword)
            self.definition = "Multiconditional output determination"

            firstInput = formalHandshake_Hardware.Hardware_IOPort(F'default', self, type)
            self.inputs.append(firstInput)
            self.parent.connect(default, firstInput)
            for o, output in enumerate(self.outputs):
                out = formalHandshake_Hardware.Hardware_IOPort(F'output{o}', self, type)
                self.inputs.append(out)
                self.parent.connect(output, out)
                self.outputs[o] = out
            for c, condition in enumerate(self.conditions):
                cond = formalHandshake_Hardware.Hardware_IOPort(F'cond{c}', self, 'Bool()')
                self.inputs.append(cond)
                self.parent.connect(condition, cond)
                self.conditions[c] = cond

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code = list):
            tab = ''
            if self.isFormal:
                tab = '    '

            # formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)

            for index, condition in enumerate(self.conditions):
                #code.append(F'    {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.input(), self.parent)}')
                if index == 0:
                    code.append(F'{tab}    when({formalHandshake_Hardware.getSpinalHDLSource(condition, self.parent)})' + '{')
                else:
                    code.append(tab + '    }.elsewhen(' + F'{formalHandshake_Hardware.getSpinalHDLSource(condition, self.parent)})' + '{')
                code.append(F'{tab}        {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.outputs[index], self.parent)}')
            code.append(tab + '    }.otherwise{')
            code.append(F'{tab}        {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}')
            code.append(tab + '    }')

    ## Prebuild Register hardware function
    class Register(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str, initialValue: str = None, keywordIn: str = None, keywordOut: str = None):
            super().__init__(id, parent, type, 1, keywordOut)
            if (not initialValue == None) and formalHandshake_Hardware.typeCheckValue(type, initialValue):
                self.initialValue = formalHandshake_Hardware.typeCheckValue(type, initialValue)
            else:
                self.initialValue = initialValue
            self.definition = f'{type}_Register'
            #self.type = type
            self.inputs.append(formalHandshake_Hardware.Hardware_IOPort(f'in', self, type, keywordIn))

        def input(self):
            return self.inputs[0]

        ## Returns a line of SpinalHDL code, defining what this functions is
        def getSpinalHDLInstance(self, code = list):
            tab = ''
            if self.isFormal:
                tab = '    '
            # type ? code.append(F'    {self.id} = Reg({self.type}) init({self.initialValue})')
            if self.initialValue == None:
                code.append(F'{tab}    val {self.id} = Reg({self.getType()})')
            else:
                code.append(F'{tab}    val {self.id} = Reg({self.getType()}) init({self.initialValue})')

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code = list):
            tab = ''
            if self.isFormal:
                tab = '    '
            code.append(F'{tab}    {self.id} := {formalHandshake_Hardware.getSpinalHDLSource(self.input(), self.parent)}')

    ## Prebuild Const Value hardware function
    class Const(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str, value: str, keyword: str = None):
            super().__init__(id, parent, type, 0, keyword)
            #oldValue = value
            knownType = False
            valid = False

            if type == F'Bool()':
                knownType = True
                if isinstance(value, str):
                    if value == 'False' or value == 'B"0"':
                        value = 'False'
                        valid = True
                    if value == 'True' or value == 'B"1"':
                        value = 'True'
                        valid = True
            
            if self.baseType == 'Bits': 
                knownType = True
                if isinstance(value, str):
                    # Precompile regex patterns
                    PATTERN_LITERAL = re.compile(r'^B"([01]+)"$')
                    PATTERN_NUMERIC = re.compile(r'^B\(\s*(\d+)\s*,\s*(\d+)\s*bits\s*\)$')

                    # Try literal format: B"0101"
                    m = PATTERN_LITERAL.fullmatch(value)
                    if m:
                        valid = True
                    else:
                        # Try numeric format: B(3, 5 bits)
                        m = PATTERN_NUMERIC.fullmatch(value)
                        if m:
                            val = int(m.group(1))
                            length = int(m.group(2))

                            # Validate that val fits in given bit length
                            if val >= (1 << length):
                                raise ValueError(f"value {val} does not fit in {length} bits")
                            else:
                                value = F'B"{format(val, f'0{length}b')}"'
                                valid = True
                                #print(F' -> !! converted {oldValue} to {value} !!')
                else:
                    value = F'B"{format(value, f'0{self.width[0]}b')}"'
                    valid = True
            
            if self.baseType == 'UInt': 
                knownType = True
                if isinstance(value, str):
                    # Precompile regex patterns
                    PATTERN_LITERAL = re.compile(r'^U"([01]+)"$')
                    PATTERN_NUMERIC = re.compile(r'^U\(\s*(\d+)\s*,\s*(\d+)\s*bits\s*\)$')

                    # Try literal format: U"0101"
                    m = PATTERN_LITERAL.fullmatch(value)
                    if m:
                        valid = True
                    else:
                        # Try numeric format: U(3, 5 bits)
                        m = PATTERN_NUMERIC.fullmatch(value)
                        if m:
                            val = int(m.group(1))
                            length = int(m.group(2))

                            # Validate that val fits in given bit length
                            if val >= (1 << length):
                                raise ValueError(f"value {val} does not fit in {length} bits")
                            else:
                                value = F'U"{format(val, f'0{length}b')}"'
                                valid = True
                                #print(F' -> !! converted {oldValue} to {value} !!')
                else:
                    value = F'U"{format(value, f'0{self.width[0]}b')}"'
                    valid = True

            if self.baseType == 'SInt': 
                knownType = True
                if isinstance(value, str):
                    # Precompile regex patterns
                    PATTERN_LITERAL = re.compile(r'^S"([01]+)"$')
                    PATTERN_NUMERIC = re.compile(r'^S\(\s*(\d+)\s*,\s*(\d+)\s*bits\s*\)$')

                    # Try literal format: S"0101"
                    m = PATTERN_LITERAL.fullmatch(value)
                    if m:
                        valid = True
                    else:
                        # Try numeric format: S(3, 5 bits)
                        m = PATTERN_NUMERIC.fullmatch(value)
                        if m:
                            val = int(m.group(1))
                            length = int(m.group(2))

                            # Validate that val fits in given bit length
                            if val >= (1 << length):
                                raise ValueError(f"value {val} does not fit in {length} bits")
                            else:
                                value = F'S"{format(val, f'0{length}b')}"'
                                valid = True
                                #print(F' -> !! converted {oldValue} to {value} !!')
                else:
                    value = F'S"{format(value, f'0{self.width[0]}b')}"'
                    valid = True

            if not knownType:
                print(F'!! Warning: constant of module "{parent.id}" with value "{value}" has unknown type "{type}"')
            if not valid:
                print(F'!! Warning: constant of module "{parent.id}" with type "{type}" has unknown value encoding "{value}"')

            self.valid = valid
            if self.isBoolean():
                self.id = value
            else:
                self.id = formalHandshake_Hardware.strBitToInt(value)
            self.definition = value

        ## ?
        def value(self, asInt: bool = False):
            if asInt:
                return int(self.definition[2:-1], 2)
            else:
                return self.definition

        ## Returns a line of SpinalHDL code, defining what this functions is
        def getSpinalHDLInstance(self, code = list):
            #code.append(F'    {self.id} = {self.type}')
            pass

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code = list):
            #code.append(F'    {self.id} := ({self.definition})')
            pass

    ## Prebuild Incrementer hardware function
    class Incrementer(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            if not input.baseType == 'UInt':
                raise TypeError(F'Cannot build Incrementer with id: {id}, input has to be of type UInt and not of type {input.baseType}')
            super().__init__(id[0].lower() + id[1:], parent, input.getType(), 0, keyword)
            in1 = formalHandshake_Hardware.Hardware_IOPort('input', self, input.getType(), None)
            self.inputs.append(in1)
            self.parent.connect(input, in1)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)} + 1'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} + 1'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Incrementer hardware function
    class Decrementer(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            if not input.baseType == 'UInt':
                raise TypeError(F'Cannot build Decrementer with id: {id}, input should be of type UInt and not of type {input.baseType}')
            super().__init__(id[0].lower() + id[1:], parent, input.getType(), 0, keyword)
            in1 = formalHandshake_Hardware.Hardware_IOPort('input', self, input.getType(), None)
            self.inputs.append(in1)
            self.parent.connect(input, in1)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)} - 1'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} - 1'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild unsigned multi bit Adder
    class AdderUnsigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None, input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None, keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            if not input1 == None:
                parent.connect(input1, in1)
            if not input2 == None:
                parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asUInt + {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asUInt).asBits'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asUInt + {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asUInt).asBits'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild signed multi bit Adder
    class AdderSigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None, input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None, keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            if not input1 == None:
                parent.connect(input1, in1)
            if not input2 == None:
                parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt + {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asSInt).asBits'

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt + {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asSInt).asBits'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild unsigned multi bit Subtractor
    class SubtractUnsigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asUInt - {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asUInt).asBits'
                
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asUInt - {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asUInt).asBits'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild signed multi bit Subtractor
    class SubtractSigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt - {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asSInt).asBits'

        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt - {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asSInt).asBits'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild unsigned multi bit LowerThan
    class LowerThanUnsigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asUInt < {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asUInt) ? B(1, {bitSize} bits) | B(0, {bitSize} bits)'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asUInt < {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asUInt) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild signed multi bit LowerThan
    class LowerThanSigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt < {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asSInt) ? B(1, {bitSize} bits) | B(0, {bitSize} bits)'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt < {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asSInt) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild unsigned multi bit GreaterEquals
    class GreaterEqualsUnsigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asUInt >= {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asUInt) ? B(1,32 bits) | B(0,32 bits)'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asUInt >= {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asUInt) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild signed multi bit GreaterEquals
    class GreaterEqualsSigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt >= {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asSInt) ? B(1, {bitSize} bits) | B(0, {bitSize} bits)'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt >= {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asSInt) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit XOR
    class XOR(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} ^ {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} ^ {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit OR
    class OR(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} | {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} | {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit AND
    class AND(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} & {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} & {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit AND
    class NAND(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'!({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} & {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)})'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'!({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} & {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)})'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit SLL
    class SLL(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} |<< ({formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}(4 downto 0).asUInt'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} |<< {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}(4 downto 0).asUInt'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit SRL
    class SRL(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            ## io.regWrite_data := io.rs1_data |>> io.rs2_data(4 downto 0).asUInt
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} |>> ({formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}(4 downto 0).asUInt'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} |>> {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}(4 downto 0).asUInt'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit SRA
    class SRA(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            ## io.regWrite_data := (io.rs1_data.asSInt >> io.rs2_data(4 downto 0).asUInt).asBits
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt >> {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}(4 downto 0).asUInt).asBits'
        
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt >> {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}(4 downto 0).asUInt).asBits'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit Equals
    class Equals(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} === {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} === {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild multi bit EqualsNot
    class EqualsNot(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, bitSize: int, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bits({bitSize} bits)', 0, keyword)
            self.bitSize = bitSize
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, F'Bits({bitSize} bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, F'Bits({bitSize} bits)')
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} =/= {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} =/= {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}) ? B(1, {self.bitSize} bits) | B(0, {self.bitSize} bits)'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean Equals
    class BooleanEquals(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not input1.getType() == input2.getType():
                raise TypeError(F'Cannot build BooleanEquals, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) are not of same type')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} === {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} === {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean EqualsNot
    class BooleanEqualsNot(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not input1.getType() == input2.getType():
                raise TypeError(F'Cannot build BooleanEqualsNot, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) are not of same type')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} =/= {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
                            
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} =/= {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean Inversion
    class NOT(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not formalHandshake_Hardware.isBoolean(input1):
                raise TypeError(F'Cannot build BooleanEqualsNot, input "{input1.id}" ({input1.getType()}) has to be boolean')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            self.inputs.append(in1)
            parent.connect(input1, in1)
            self.definition = F'!{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}'
                            
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'!{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean AND
    class BooleanAND(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (formalHandshake_Hardware.isBoolean(input1) and formalHandshake_Hardware.isBoolean(input2)):
                raise TypeError(F'Cannot build BooleanAND, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be boolean')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} && {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
                            
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} && {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean NAND
    class BooleanNAND(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (formalHandshake_Hardware.isBoolean(input1) and formalHandshake_Hardware.isBoolean(input2)):
                raise TypeError(F'Cannot build BooleanNAND, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be boolean')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'!({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} && {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)})'
                                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'!({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} && {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)})'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean AND with more than two inputs
    class BooleanMultiAND(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, sources: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], keyword: str = None):
            if len(sources) < 1:
                raise TypeError(F'Module "{self.id}" cannot build multiAND funtion with no sources')
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            self.definition = ''
            for s, source in enumerate(sources):
                if not formalHandshake_Hardware.isBoolean(source):
                    raise TypeError(F'Module "{parent.id}" cannot build multiAND "{id}" funtion with non boolean source "{source.id}"')
                input = formalHandshake_Hardware.Hardware_IOPort(f'in{s}', self, 'Bool()')
                self.inputs.append(input)
                parent.connect(source, input)
                if s > 0:
                    self.definition += ' && '
                self.definition += F'{formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)}'
                                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = ''
            for i, input in enumerate(self.inputs):
                if i > 0:
                    self.definition += ' && '
                self.definition += F'{formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean OR
    class BooleanOR(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (formalHandshake_Hardware.isBoolean(input1) and formalHandshake_Hardware.isBoolean(input2)):
                raise TypeError(F'Cannot build BooleanOR, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be boolean')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} || {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
                                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} || {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean NOR
    class BooleanNOR(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (formalHandshake_Hardware.isBoolean(input1) and formalHandshake_Hardware.isBoolean(input2)):
                raise TypeError(F'Cannot build BooleanNOR, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be boolean')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'!({formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} || {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)})'
                                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'!({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} || {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)})'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean OR with more than two inputs
    class BooleanMultiOR(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, sources: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], keyword: str = None):
            if len(sources) < 1:
                raise TypeError(F'Module "{self.id}" cannot build multiOR funtion with no sources')
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            self.definition = ''
            for s, source in enumerate(sources):
                if not formalHandshake_Hardware.isBoolean(source):
                    raise TypeError(F'Module "{parent.id}" cannot build multiOR "{id}" funtion with non boolean source "{source.id}"')
                input = formalHandshake_Hardware.Hardware_IOPort(f'in{s}', self, 'Bool()')
                self.inputs.append(input)
                parent.connect(source, input)
                if s > 0:
                    self.definition += ' || '
                self.definition += F'{formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)}'
                                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = ''
            for i, input in enumerate(self.inputs):
                if i > 0:
                    self.definition += ' || '
                self.definition += F'{formalHandshake_Hardware.getSpinalHDLSource(input, self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild Boolean XOR
    class BooleanXOR(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (formalHandshake_Hardware.isBoolean(input1) and formalHandshake_Hardware.isBoolean(input2)):
                raise TypeError(F'Cannot build BooleanXOR, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be boolean')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)} ^ {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}'
                                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} ^ {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild unsigned GreaterEquals, creating a boolean output
    class BooleanGreaterEqualsUnsigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (input1.getType() == 'UInt' and input2.getType() == 'UInt'):
                raise TypeError(F'Cannot build BooleanEquals, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be of type UInt')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asUInt >= {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asUInt'
                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asUInt >= {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asUInt'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild signed GreaterEquals, creating a boolean output
    class BooleanGreaterEqualsSigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (input1.getType() == 'UInt' and input2.getType() == 'UInt'):
                raise TypeError(F'Cannot build BooleanEquals, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be of type UInt')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt >= {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asSInt'
                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt >= {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asSInt'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild unsigned LowerEquals, creating a boolean output
    class BooleanLowerEqualsUnsigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (input1.getType() == 'UInt' and input2.getType() == 'UInt'):
                raise TypeError(F'Cannot build BooleanEquals, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be of type UInt')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asUInt < {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asUInt'
                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asUInt < {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asUInt'
            return super().getSpinalHDLDefinition(code)

    ## Prebuild signed LowerEquals, creating a boolean output
    class BooleanLowerEqualsSigned(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, input1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], input2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            super().__init__(id[0].lower() + id[1:], parent, F'Bool()', 0, keyword)
            if not (input1.getType() == 'UInt' and input2.getType() == 'UInt'):
                raise TypeError(F'Cannot build BooleanEquals, inputs "{input1.id}" ({input1.getType()}) and "{input2.id}" ({input2.getType()}) have to be of type UInt')
            in1 = formalHandshake_Hardware.Hardware_IOPort('input1', self, input1.getType())
            in2 = formalHandshake_Hardware.Hardware_IOPort('input2', self, input2.getType())
            self.inputs.append(in1)
            self.inputs.append(in2)
            parent.connect(input1, in1)
            parent.connect(input2, in2)
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, parent)}.asSInt < {formalHandshake_Hardware.getSpinalHDLSource(in2, parent)}.asSInt'
                    
        ## Returns a line of SpinalHDL code, defining the value of this function
        def getSpinalHDLDefinition(self, code: list):
            self.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)}.asSInt < {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[1], self.parent)}.asSInt'
            return super().getSpinalHDLDefinition(code)

    ## Hardware version of Module with modified or added funtions
    class Hardware_Module(Module):
        def __init__(self, id: str):
            super().__init__(id[0].lower() + id[1:])
            self.className = id[0].upper() + id[1:]# +'_classname_is_not_defined'
            self.filePath = None
            self.isFormal = False
            self.formalStatements = []

        @classmethod
        def from_SpinalHDL(cls, id: str, filePath: str, className: str, includeFiles: Union[str, list[str]] = None, getIO: bool = True, getSubmodules: bool = True):
            module = formalHandshake_Hardware.Hardware_Module(id)
            module.className = className
            module.filePath = filePath
            code = getSpinalHDLClassDefinition(filePath, className)
            module.parameters = extract_spinalhdl_parameters(code, module)

            if getIO:
                #print(F'        Parameters for module {id}:')
                #for parameter in module.parameters:
                #    print(F'         -> id: {parameter.id}, type: {parameter.type}, default: {parameter.default}')
                ios = parse_spinal_ios(code, module.parameters)

                #print(F'        IOs for module {id}:')
                for io in ios:
                    if io['direction'] == 'in':
                        module.addInput(io['name'], F'{io['type_expression']}')
                    if io['direction'] == 'out':
                        module.addOutput(io['name'], F'{io['type_expression']}')

            if getSubmodules:
                files: list[str] = []
                files.append(filePath)
                if not includeFiles == None:
                    if isinstance(includeFiles, str):
                        files.append(includeFiles)
                    else:
                        for element in includeFiles:
                            files.append(element)

                _CLASS_OR_OBJECT_RE = re.compile(
                    r"""
                    (?P<header>                                           # everything until first '{'
                        ^\s*(?:case\s+)?                                   # optional 'case'
                        (?P<kind>class|object)\s+                          # class or object
                        (?P<name>[A-Za-z_]\w*)                             # name
                        (?P<aftername>                                     # parameters, extends, with...
                            [^{]*                                          # anything until '{'
                        )
                    )
                    \{                                                     # the opening brace of the body
                    """,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )

                #if re.search(r"\bextends\b[\s\S]*?\bComponent\b", header):
                #    # This class is a Component

                #classes: list[str] = []
                #classesFiles: list[str] = []

                spinalHDLComponents       = []
                spinalHDLComponentsFiles  = []
                otherClasses    = []
                otherClassesFiles = []
                otherObjects    = []
                otherObjectsFiles = []

                for name in files:
                    with open(name, 'r') as f:
                        lines = f.read()
                        #ident = _COMPONENT_RE.finditer(lines)
                        #for m in ident:
                        #    if re.search(r"\bextends\b[\s\S]*?\bComponent\b", m.group("header")):
                        #        #print(F'{m.group("name")} is a Component')
                        #        classes.append(m.group("name"))
                        #        classesFiles.append(name)

                        for m in _CLASS_OR_OBJECT_RE.finditer(lines):
                            header = m.group("header")
                            kind   = m.group("kind")   # 'class' or 'object'
                            cname  = m.group("name")

                            # Is it a SpinalHDL Component?
                            if re.search(r"\bextends\b[\s\S]*?\bComponent\b", header):
                                spinalHDLComponents.append(cname)
                                spinalHDLComponentsFiles.append(name)
                            else:
                                # It's some other class/object
                                if kind == "class":
                                    otherClasses.append(cname)
                                    otherClassesFiles.append(name)
                                else:
                                    otherObjects.append(cname)
                                    otherObjectsFiles.append(name)

                new_re = re.compile(r"\bnew\s+([A-Za-z_]\w*)\b")
                newMatches = new_re.findall("\n".join(code))

                candidates = set(newMatches)

                # 2) Optional: also catch Name(...) style (no `new`)
                # This will also match regular function calls, so we filter using all_components.
                call_re = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
                call_matches = call_re.findall("\n".join(code))
                for name in call_matches:
                    if not name == className:
                        candidates.add(name)

                ## Keep only user-defined components
                #components_set = set(classes)
                components_set = set(spinalHDLComponents + otherClasses + otherObjects)
                result = [name for name in candidates if name in components_set]

                ## throw out doubles:
                components: list[str] = []
                for name in result:
                    if not name in components:
                        if not name == className:
                            components.append(name)

                #for name in components:
                #    print(F'name: {name}')

                for component in components:
                    for e, element in enumerate(spinalHDLComponents):
                        if element == component:
                            #print(F'!!      -> Blackboxing {component} from file {classesFiles[e]} as submodule of {className}')
                            #submodule = formalHandshake_Hardware.Hardware_Module.from_SpinalHDL(F'submodule_{e}', spinalHDLComponentsFiles[e], component, includeFiles, getIO, getSubmodules)
                            submodule = formalHandshake_Hardware.Hardware_Module.from_SpinalHDL(F'submdoule_{e}_{component}', spinalHDLComponentsFiles[e], component, includeFiles, getIO, getSubmodules)
                            module.addSubModule(submodule)
                    for e, element in enumerate(otherClasses):
                        if element == component:
                            found = False
                            for include in module.includes:
                                if element == include[0]:
                                    found == True
                                    break
                            if not found:
                                module.includes.append([element, otherClassesFiles[e]])
                    for e, element in enumerate(otherObjects):
                        if element == component:
                            found = False
                            for include in module.includes:
                                if element == include[0]:
                                    found == True
                                    break
                            if not found:
                                module.includes.append([element, otherObjectsFiles[e]])

            module.blackbox = True
            return module

        ## Set formalMarker to true -> function is only generated in formal prrof block
        def formal(self):
            self.isFormal = True
            self.unmarked = True
            for element in (self.inputs + self.outputs + self.subModules + self.functions):
                element.formal()
            return self

        ## add input with specific type
        def addInput(self, id: str, type: str, keyword: str = None):
            input = formalHandshake_Hardware.Hardware_IOPort(id, self, type, keyword)
            self.inputs.append(input)
            return input

        ## add output with specific type
        def addOutput(self, id: str, type: str, keyword: str = None):
            output = formalHandshake_Hardware.Hardware_IOPort(id, self, type, keyword)
            self.outputs.append(output)
            return output

        ## add hardware function -> adds the number of submodules + the number of functions as first Cell koordinate
        def addFunction(self, function: formalHandshake_Hardware.Hardware_Function, keyword: str = None):
            if not keyword == None:
                function.keyword = keyword
            function.firstCell = (len(self.subModules) + len(self.functions) + 1, len(self.subModules) + len(self.functions))
            self.functions.append(function)
            self.steps += 1
            return function

        ## add subModule # -> adds the number of submodules as first Cell koordinate
        def addSubModule(self, module: formalHandshake_Hardware.Hardware_Module):
            super().addSubModule(module)
            return module

        ## connects two hardware signals if types match and adds connection to list of connections
        def connect(self, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], destination: formalHandshake_Hardware.Hardware_IOPort):
            # type ? if formalHandshake_Hardware.compareHardwareTypes(source.type, destination.type):
            if formalHandshake_Hardware.compareHardwareTypes(source.getType(), destination.getType()):
                ## non formal parts of the circuit cannot depend on formal/optional sources
                if (source.isFormal and (not destination.isFormal)):
                    raise TypeError(F'Cannot connect non formal destination {destination.parent.id}.{destination.id} to formal source {source.parent.id}.{source.id}')
                destination.source = source
                source.destinations.append(destination)
                #self.network.append(((source.parent.id, source.id), (destination.parent.id, destination.id)))
            else:
                # type ?raise TypeError(F'{self.id} cannot connect {source.parent.id}.{source.id} with type: {source.type} and {destination.parent.id}.{destination.id} with type: {destination.type} - no matching types')
                raise TypeError(F'{self.id} cannot connect {source.parent.id}.{source.id} with type: {source.getType()} and {destination.parent.id}.{destination.id} with type: {destination.getType()} - no matching types')

        ## Manual Connection to split the signal into only certain bits
        def connectManual(self, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], destination: formalHandshake_Hardware.Hardware_IOPort, definition: str):
            #print(F'Warning, connectManual does not provide proper typechecking yet.')
            ## non formal parts of the circuit cannot depend on formal/optional sources
            if (source.isFormal and (not destination.isFormal)):
                raise TypeError(F'Cannot connect non formal destination {destination.parent.id}.{destination.id} to formal source {source.parent.id}.{source.id}')
            ##
            #func = self.addFunction(formalHandshake_Hardware.Hardware_Function((F'{source.parent.id}_{source.id}_To_{destination.parent.id}_{destination.id}').replace('.', '_'), self, destination.getType(), 0))
            func = formalHandshake_Hardware.Hardware_Function((F'{source.parent.id}_{source.id}_To_{destination.parent.id}_{destination.id}').replace('.', '_'), self, destination.getType(), 0)
            self.connect(func, destination)
            funcIn = formalHandshake_Hardware.Hardware_IOPort({source.id}, func, source.getType())
            func.inputs.append(funcIn)
            self.connect(source, funcIn)
            func.definition = definition
            return destination

        ## Build and add a custom function with given definition
        def manualFunctionFrom(self, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], id: str, type: str, definition: str):
            func = formalHandshake_Hardware.Hardware_Function(id, self, type, 0)
            funcIn = formalHandshake_Hardware.Hardware_IOPort({source.id}, func, source.getType())
            func.inputs.append(funcIn)
            self.connect(source, funcIn)
            func.definition = definition
            return func

        ## Create a splitconnecter to a given destination
        def split(self, destination: formalHandshake_Hardware.Hardware_IOPort):
            if destination.parent == None:
                raise ValueError(F'Module {self.id} cannot split destination {destination.id}, it has no parent')
            if destination.parent == self:
                if not destination in self.outputs:
                    raise ValueError(F'Module {self.id} cannot split is own IOPort {destination.id}, that is not an output')
            else:
                if not destination.parent.parent == self:
                    raise ValueError(F'Module {self.id} cannot split destination {destination.id}, it does not belong to any submodule')
                if not destination in destination.parent.inputs:
                    raise ValueError(F'Module {self.id} cannot split destination {destination.id}, it does not belong to inputs of submodule {destination.parent.id}')

            splitConnector = formalHandshake_Hardware.SplitConnector((F'{destination.parent.id}_{destination.id}_split').replace('.', '_'), self, destination.getType())
            self.connect(splitConnector, destination)
            return splitConnector

        ## Create own SpinalHDL description
        def toSpinalHDL(self, code: list = None, classes: list = None, includes: list = None, toplevel = True, imports = None, report = True, warnings = False):
            if code == None:
                code = []
            if classes == None:
                classes = []
            if includes == None:
                includes = []
            if imports == None:
                imports = []

            if toplevel:
                if report:
                    print(' --- Generating SpinalHDL code for:', self.id)
                code.append('import spinal.core._')
                code.append('import spinal.lib._')
                code.append('import spinal.core.formal._')

                for line in imports:
                    code.append(F'import {line}')

            for element in self.includes:
                if not element[0] in includes:
                    #print(F'Module: {self.id} - Should include {element[0]} from {element[1]}')
                    AdditionalCode = extract_definition(element[1], element[0])
                    code.append(F'')
                    for line in AdditionalCode: code.append(line)
                    includes.append(element[0])

            if not self.className in classes:
                ## build submodules
                for module in self.subModules:
                    module.toSpinalHDL(code, classes, includes, False)
                if self.filePath == None:
                    parameters = ''
                    if len(self.parameters) > 0:
                        parameters += '\n'
                        for p, parameter in enumerate(self.parameters):
                            parameters += F'    {parameter.id}: {parameter.type}'
                            if not parameter.default == None:
                                parameters += F' = {parameter.default}'
                            if not (p == (len(self.parameters) - 1)):
                                parameters += ','
                            parameters += '\n'
                    code.append('')
                    code.append(F"class {self.className}({parameters}) extends Component" + '{')

                    #code.append('   val io = new Bundle {')    ## ?

                    ## IOs
                    formalInputs = []
                    nonFormalInputs = []
                    formalOutputs = []
                    nonFormalOutputs = []

                    for input in self.inputs:
                        if input.isFormal:
                            formalInputs.append(input)
                        else:
                            nonFormalInputs.append(input)
                    for output in self.outputs:
                        if output.isFormal:
                            formalOutputs.append(output)
                        else:
                            nonFormalOutputs.append(output)

                    ## ?
                    class Bundle():
                        def __init__(self, id: str = None):
                            self.id = id
                            self.ios: list[tuple[formalHandshake_Hardware.Hardware_IOPort, str, str]] = []
                            self.bundles: list[Bundle] = []

                        ## ?
                        def addIO(self, io: formalHandshake_Hardware.Hardware_IOPort, direction: str, newID: str = None):
                            if newID == None:
                                newID = io.id
                            before, sep, after = newID.partition(".")
                            if sep == "":
                                self.ios.append((io, direction, newID))
                            else:
                                newID = after
                                found = False
                                for bundle in self.bundles:
                                    if bundle.id == before:
                                        found = True
                                        bundle.addIO(io, direction, newID)
                                        break
                                if not found:
                                    bundle = Bundle(before)
                                    bundle.addIO(io, direction, newID)
                                    self.bundles.append(bundle)
                        ## ?
                        def toSpinalHDL(self, code: list[str], tab: int = 0):
                            if not (len(self.ios) == 0 and len(self.bundles) == 0):
                                if not self.id == None:
                                    code.append('\t' * (tab) + F'val {self.id} = new Bundle' + " {")
                                for io in self.ios:
                                    code.append('\t' * (tab + 1) + F'val {io[2]} = {io[1]} {io[0].getType(True)}')
                                for bundle in self.bundles:
                                    bundle.toSpinalHDL(code, (tab + 1))
                                if not self.id == None:
                                    code.append('\t' * (tab) + "}")

                    if len(nonFormalInputs + nonFormalOutputs) > 0:
                        bundle = Bundle()
                        code.append('    // IOs:')
                        for input in nonFormalInputs:
                            if toplevel == False and input.source == 0:
                                key = ''
                                if not input.keyword == None:
                                    key = F' (keyword: {input.keyword})'
                                raise ConnectionRefusedError(F'{self.id}.{input.id}{key} is not connected, cannot generate working SpinalHDL Code')
                            # type ? code.append(F'    val {input.id} = in {input.type}')

                            #code.append(F'    val {input.id} = in {input.getType(True)}')
                            bundle.addIO(input, 'in')

                        for output in nonFormalOutputs:
                            if output.source == 0:
                                key = ''
                                if not output.keyword == None:
                                    key = F' (keyword: {output.keyword})'
                                raise ConnectionRefusedError(F'{self.id}.{output.id}{key} is not connected, cannot generate working SpinalHDL Code')
                            # type ? code.append(F'    val {output.id} = out {output.type}')
                            #code.append(F'    val {output.id} = out {output.getType(True)}')
                            bundle.addIO(output, 'out')
                        #code.append('   }')
                        bundle.toSpinalHDL(code)
                        code.append('')

                    nonFormalFunctions = []
                    formalFunctions = []
                    ## Instanciating functions
                    if len(self.functions) > 0:
                        for function in self.functions:
                            if function.isFormal:
                               formalFunctions.append(function)
                            else:
                                nonFormalFunctions.append(function)
                        if len(nonFormalFunctions) > 0:
                            code.append('    // functions:')
                            for function in nonFormalFunctions:
                                if len(function.destinations) == 0:
                                    key = ''
                                    if not function.keyword == None:
                                        key = F' (keyword: {function.keyword})'
                                    #print('Here!')
                                    if warnings:
                                        print(F' !!! Warning: {self.id}.{function.id}{key} is not connected, might not generate working SpinalHDL Code')
                                    #raise ConnectionRefusedError(F'{self.id}.{function.id}{key} is not connected, cannot generate working SpinalHDL Code')
                                for functionInput in function.inputs:
                                    if functionInput.source == 0:
                                        key = ''
                                        if not functionInput.keyword == None:
                                            key = F' (keyword: {functionInput.keyword})'
                                        raise ConnectionRefusedError(F'{function.id}.{functionInput.id}{key} is not connected, cannot generate working SpinalHDL Code')
                                function.getSpinalHDLInstance(code)
                            code.append('')


                    formalSubmodules = []
                    nonFormalSubmodules = []

                    ## Instanciating submodules
                    if len(self.subModules) > 0:
                        for submodule in self.subModules:
                            if submodule.isFormal:
                                formalSubmodules.append(submodule)
                            else:
                                nonFormalSubmodules.append(submodule)
                        if len(nonFormalSubmodules) > 0:
                            code.append('    // Subcomponents:')
                            for module in nonFormalSubmodules:
                                parameters = ''
                                if len(module.parameters) > 0:
                                    for p, parameter in enumerate(module.parameters):
                                        if parameter.default == None and parameter.value == None:
                                            raise ValueError(F'Module with id {self.id} cannot instanciate submodule with id {module.id}, because parameter {parameter.id} has no given or default value.')
                                        if not parameter.value == None:
                                            if isinstance(parameter.value, Parameter):
                                                if not parameter.value.parent == self:
                                                    raise ValueError(F'Submodules of module {self.id} can not be instanciated with parameter {parameter.id}, because this parameter does not belong to said module.')
                                                parameters += F'{parameter.value.id}'
                                            else:
                                                parameters += F'{parameter.value}'
                                        else:
                                            parameters += F'{parameter.default}'
                                        if not (p == (len(module.parameters) - 1)):
                                            parameters += ', '
                                code.append(F'    val {module.id} = new {module.className}({parameters})')  # Parameters
                            code.append('')

                    ## Connecting function-inputs
                    if len(nonFormalFunctions) > 0:
                        code.append('    // function definitions:')
                        for function in nonFormalFunctions:
                            function.getSpinalHDLDefinition(code)
                        code.append('')

                    ## Connecting module-inputs
                    if len(nonFormalSubmodules) > 0:
                        code.append('    // subcomponent connections:')
                        for module in nonFormalSubmodules:
                            for input in module.inputs:
                                code.append(F'    {module.id}.{input.id} := {formalHandshake_Hardware.getSpinalHDLSource(input, self)}')
                        code.append('')

                    ## Connecting own outputs
                    if len(nonFormalOutputs) > 0:
                        code.append('    // output connections:')
                        for output in nonFormalOutputs:
                            code.append(F'    {output.id} := {formalHandshake_Hardware.getSpinalHDLSource(output, self)}')

                    ## formal Block
                    if (len(self.formalStatements) > 0 or len(formalInputs) > 0 or  len(formalOutputs) > 0  or  len(formalFunctions) > 0 or  len(formalSubmodules) > 0 ):
                        code.append('')
                        code.append('    GenerationFlags.formal{')
                        code.append('        clockDomain.withoutReset(){')
                        ## ? reset/non reset?

                        ## formal IOs
                        if len(formalInputs + formalOutputs) > 0:
                            formalBundle = Bundle()
                            code.append('            // formal IOs:')
                            for input in formalInputs:
                                if toplevel == False and input.source == 0:
                                    key = ''
                                    if not input.keyword == None:
                                        key = F' (keyword: {input.keyword})'
                                    raise ConnectionRefusedError(F'{self.id}.{input.id}{key} is not connected, cannot generate working SpinalHDL Code')
                                # type ? code.append(F'    val {input.id} = in {input.type}')
                                #code.append(F'            val {input.id} = in {input.getType(True)}')
                                formalBundle.addIO(input, 'in')
                            for output in formalOutputs:
                                if output.source == 0:
                                    key = ''
                                    if not output.keyword == None:
                                        key = F' (keyword: {output.keyword})'
                                    raise ConnectionRefusedError(F'{self.id}.{output.id}{key} is not connected, cannot generate working SpinalHDL Code')
                                # type ? code.append(F'    val {output.id} = out {output.type}')
                                #code.append(F'            val {output.id} = out {output.getType(True)}')
                                formalBundle.addIO(output, 'out')
                            #code.append('   }')
                            formalBundle.toSpinalHDL(code, 1)
                            code.append('')

                        ## Instanciating non formal functions
                        if len(formalFunctions) > 0:
                            code.append('        // formal functions:')
                            for function in formalFunctions:
                                for functionInput in function.inputs:
                                    if functionInput.source == 0:
                                        key = ''
                                        if not functionInput.keyword == None:
                                            key = F' (keyword: {functionInput.keyword})'
                                        raise ConnectionRefusedError(F'{function.id}.{functionInput.id}{key} is not connected, cannot generate working SpinalHDL Code')
                                function.getSpinalHDLInstance(code)
                            code.append('')

                        ## instanciating formal submodules
                        if len(formalSubmodules) > 0:
                            for module in formalSubmodules:
                                parameters = ''
                                if len(module.parameters) > 0:
                                    for p, parameter in enumerate(module.parameters):
                                        if parameter.default == None and parameter.value == None:
                                            raise ValueError(F'Module with id {self.id} cannot instanciate submodule with id {module.id}, because parameter {parameter.id} has no given or default value.')
                                        if not parameter.value == None:
                                            if isinstance(parameter.value, Parameter):
                                                if not parameter.value.parent == self:
                                                    raise ValueError(F'Submodules of module {self.id} can not be instanciated with parameter {parameter.id}, because this parameter does not belong to said module.')
                                                parameters += F'{parameter.value.id}'
                                            else:
                                                parameters += F'{parameter.value}'
                                        else:
                                            parameters += F'{parameter.default}'
                                        if not (p == (len(module.parameters) - 1)):
                                            parameters += ', '
                                code.append(F'            val {module.id} = new {module.className}({parameters})')  # Parameters
                            code.append('')

                        ## Connecting module-inputs
                        if len(formalSubmodules) > 0:
                            code.append('            // subcomponent connections:')
                            for module in formalSubmodules:
                                for input in module.inputs:
                                    code.append(F'            {module.id}.{input.id} := {formalHandshake_Hardware.getSpinalHDLSource(input, self)}')
                            code.append('')

                        ## Connecting own formal outputs
                        if len(formalOutputs) > 0:
                            code.append('            // formal output connections:')
                            for output in formalOutputs:
                                code.append(F'            {output.id} := {formalHandshake_Hardware.getSpinalHDLSource(output, self)}')


                        ## Connecting non-formal function-inputs
                        if len(formalFunctions) > 0:
                            code.append('            // formal function definitions:')
                            for function in formalFunctions:
                                function.getSpinalHDLDefinition(code)
                            code.append('')

                        hasInitialReset = False
                        for s, statement in enumerate(self.formalStatements):
                            ## eliminate doubles:
                            i = s+1
                            while i < len(self.formalStatements):
                                if (self.formalStatements[i].toSpinalHDL() == statement.toSpinalHDL()):
                                    self.formalStatements.pop(i)
                                else:
                                    i += 1
                            if isinstance(statement, formalHandshake_Hardware.InitialAssumtion) and statement.booleanProperty == 'ClockDomain.current.isResetActive':
                                hasInitialReset = True
                            else:
                                code.append(statement.toSpinalHDL())
                        code.append('        }')
                        if hasInitialReset:
                            code.append('        assumeInitial(ClockDomain.current.isResetActive)')
                        code.append('    }')

                    code.append('}')

                else:
                    code.append('')
                    for line in getSpinalHDLClassDefinition(self.filePath, self.className):
                        code.append(line)

                classes.append(self.className)

            ## Meta information
            if toplevel and report:
                print(F'    -> generated {len(code)} lines')
                print(F'    -> {len(classes)} classes defined ')

            return code

        ## Create executable SystemVerilog Description from self at given file path, including formal statements as well as the corresponding proof script
        def createExecutableProof(self, filepath: str, depth: int, overwrite: bool = False, spinalVersion: str = '1.8.1', scalaVersion: str = '2.11.12'):
            import HardwareHelper
            toplevel = self.className
            code = []
            self.toSpinalHDL(code)

            HardwareHelper.makeBuildSBT(filepath, overwrite, spinalVersion, scalaVersion)
            HardwareHelper.makeSpinalHDLFile(code, filepath, toplevel, overwrite)
            HardwareHelper.makeSBY(filepath, toplevel, depth, overwrite)

            lines = []
            lines.append(F'sbt "runMain {toplevel}"')
            lines.append(F'sby -f Check.sby bmc')

            file = filepath + 'executeProof.sh'
            lines = "\n".join(lines)

            ## check if file exists
            if not overwrite and Path(file).exists():
                print("    -> File already exists. Not overwriting.")
            else:
                with open(file, "w") as f:
                    f.write(lines)
            pass

        ## Create SpinalHDL file from own SpinalHDL description at given at given destination, optionally compiling to verilog as well
        def writeSpinalHDLFile(self, filepath: str, filename: str, overwrite: bool, addVerilogBuildSection: bool = False, includeFormal: bool = False):
            file = filepath + filename + '.scala'
            print(' --- Writing SpinalHDL code for:', self.id, F'to "{file}"')

            codeList = []
            self.toSpinalHDL(codeList)
            import HardwareHelper
            HardwareHelper.makeSpinalHDLFile(codeList, filepath, self.className, overwrite, addVerilogBuildSection, includeFormal)

            ### check if file exists
            #if not overwrite and Path(file).exists():
            #    print("    -> File already exists. Not overwriting.")
            #else:
            #    codeList = []
            #    self.toSpinalHDL(codeList)
            #    code = "\n".join(codeList)
            #    with open(file, "w") as f:
            #        f.write(code)

        ## instanciate/add a hardware function with given id, type, cycles and definition and connect it to a list of given inputs (can be None for const)
        def addFunctionFromSources(self, id: str, type: str, cycles: int, definition, sources = None):
            if sources == None:
                ## Building const
                return self.const(type, definition)
            else:
                func = formalHandshake_Hardware.Hardware_Function(id, self, type, cycles)
                func.definition = definition
                if isinstance(sources, list):
                    i = 0
                    for source in sources:
                        if formalHandshake_Hardware.isHardwareSignal(source):
                           # type ? inp = formalHandshake_Hardware.Hardware_IOPort(F'i{i}', func, source.type)
                            inp = formalHandshake_Hardware.Hardware_IOPort(F'i{i}', func, source.getType())
                            func.inputs.append(inp)
                            self.connect(source, inp)
                            i += 1
                    return func
                else:
                    if formalHandshake_Hardware.isHardwareSignal(sources):
                        # type ? inp = formalHandshake_Hardware.Hardware_IOPort(F'i0', func, sources.type)
                        inp = formalHandshake_Hardware.Hardware_IOPort(F'i0', func, sources.getType())
                        func.inputs.append(inp)
                        self.connect(sources, inp)
                        return func
                    else:
                        raise TypeError(F'list of inputs or single input expected to build function with id: {id} for {self.id}')

        ## Add hardware function with given function_id and definition, add given inputs to it and connect to corresponding sources, as well as given destination (adds same types corresponding to sources and destination)
        def defineDestinationFromSources(self, function: formalHandshake_Hardware.Hardware_Function, destination: formalHandshake_Hardware.Hardware_IOPort, definition, sources: list = None):
            if sources is None:
                sources = []
            else:
                ## first check if sources valid
                for source in sources:
                    if not formalHandshake_Hardware.isHardwareSignal(source):
                        raise TypeError("No valid source for defining {function.id}")

            # type ? function.type = destination.type
            function.setType(destination.getType())
            function.definition = definition
            self.connect(function, destination)
            self.addFunction(function)
            function.parent = self
            for source in sources:
                # type ? input = formalHandshake_Hardware.Hardware_IOPort(source.id, function, source.type)
                input = formalHandshake_Hardware.Hardware_IOPort(source.id, function, source.getType())
                function.inputs.append(input)
                self.connect(source, input)

        ## creata an open wire from a given source
        def wire(self, id: str, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            wire = formalHandshake_Hardware.Wire(id, source)
            return wire

        ## NOT Finished yet
        def reset(self):
            if self.getFunction('reset'):
                return self.getFunction('reset')
            else:
                reset = formalHandshake_Hardware.Hardware_Function('reset', self, 'Bool()', 0)
                reset.definition = 'ClockDomain.current.isResetActive'
                return reset

        ## Makro for building, adding and returning a hardware function of type 'Bool()' with const value 'True' -> if this const already exists, it will be returned instead
        def true(self):
            if self.get('True'):
                return self.get('True')
            else:
                true = formalHandshake_Hardware.Const('True', self, 'Bool()', 'True')
                return true

        ## Makro for building, adding and returning a hardware function of type 'Bool()' with const value 'False' -> if this const already exists, it will be returned instead
        def false(self):
            if self.get('False'):
                return self.get('False')
            else:
                false = formalHandshake_Hardware.Const('False', self, 'Bool()', 'False')
                return false

        ## Makro for building, adding and returning a hardware function of given type with given const value -> if this const already exists, it will be returned instead
        def const(self, type: str, value: str, keyword: str = None):
            #id = F'{value}_{type}
            #if isinstance(value, int):
            #    value = str(value)
            if formalHandshake_Hardware.typeCheckValue(type, value):
                value = formalHandshake_Hardware.typeCheckValue(type, value)
            if formalHandshake_Hardware.strBitToInt(value):
                id = formalHandshake_Hardware.strBitToInt(value)
            else:
                id = value
            if self.get(id):
                # type ? if formalHandshake_Hardware.compareHardwareTypes(self.get(value).type, type):
                if formalHandshake_Hardware.compareHardwareTypes(self.get(id).getType(), type):
                    return self.get(id)
                else:
                    raise TypeError("Constant already exists, but with a different type")
            else:
                return formalHandshake_Hardware.Const(id, self, type, value, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Equals" comparator of two given hardware signals (signals will be connected automatically)
        def equals(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanEquals(id, self, source1, source2)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "EqualsNot" comparator of two given hardware signals (signals will be connected automatically)
        def equalsNot(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanEqualsNot(id, self, source1, source2)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Larger Than" comparator of two given Uint/Int hardware signals (signals will be connected automatically)
        def larger(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            print(F'!! Warning: module "{self.id}" is using larger function with id "{id}", which is an old version and sholuld be replaced with largerEquals or lower !!')
            if not formalHandshake_Hardware.compareHardwareTypes(source1.getType(), source2.getType()):
                raise TypeError("source1 and source 2 must be of same type")
            if not (source1.baseType == 'UInt' or source1.baseType == 'Int'):
                raise TypeError("source1 and source 2 must be of type Uint or Int")
            larger = formalHandshake_Hardware.Hardware_Function(id, self, 'Bool()', 0)
            i1 = formalHandshake_Hardware.Hardware_IOPort(f'i1', larger, source1.getType())
            larger.inputs.append(i1)
            self.connect(source1, i1)
            i2 = formalHandshake_Hardware.Hardware_IOPort(f'i2', larger, source2.getType())
            larger.inputs.append(i2)
            self.connect(source2, i2)
            larger.definition = f'{formalHandshake_Hardware.getSpinalHDLSource(i1, self)} > {formalHandshake_Hardware.getSpinalHDLSource(i2, self)}'
            larger.keyword = keyword
            return larger

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Larger or Equal" comparator of two given Uint/Int hardware signals (signals will be connected automatically)
        def largerEquals(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            if not formalHandshake_Hardware.compareHardwareTypes(source1.getType(), source2.getType()):
                raise TypeError("source1 and source 2 must be of same type")
            if not (source1.baseType == 'UInt' or source1.baseType == 'Int'):
                raise TypeError("source1 and source 2 must be of type Uint or Int")
            if source1.baseType == 'UInt':
                return formalHandshake_Hardware.BooleanGreaterEqualsUnsigned(id, source1, source2, keyword)
            else:
                return formalHandshake_Hardware.BooleanGreaterEqualsSigned(id, source1, source2, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Lower" comparator of two given Uint/Int hardware signals (signals will be connected automatically)
        def lower(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            if not formalHandshake_Hardware.compareHardwareTypes(source1.getType(), source2.getType()):
                raise TypeError("source1 and source 2 must be of same type")
            if not (source1.baseType == 'UInt' or source1.baseType == 'Int'):
                raise TypeError("source1 and source 2 must be of type Uint or Int")
            if source1.baseType == 'UInt':
                return formalHandshake_Hardware.BooleanLowerUnsigned(id, source1, source2, keyword)
            else:
                return formalHandshake_Hardware.BooleanLowerSigned(id, source1, source2, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing the negation of a given hardware signal (signal will be connected automatically)
        def isNot(self, id: str, source: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.NOT(id, self, source, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "And" comparator of two given boolean hardware signals (signals will be connected automatically)
        def isAnd(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanAND(id, self, source1, source2, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "And" comparator of two given boolean hardware signals (signals will be connected automatically)
        def isNand(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanNAND(id, self, source1, source2, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "And" comparator of given list of boolean hardware signals (signals will be connected automatically)
        def multiAnd(self, id: str, sources: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], keyword: str = None):
            return formalHandshake_Hardware.BooleanMultiAND(id, self, sources, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Or" comparator of two given boolean hardware signals (signals will be connected automatically)
        def isOr(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanOR(id, self, source1, source2, keyword)
        
        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Or" comparator of two given boolean hardware signals (signals will be connected automatically)
        def isNOr(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanNOR(id, self, source1, source2, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "Or" comparator of given list of boolean hardware signals (signals will be connected automatically)
        def multiOr(self, id: str, sources: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], keyword: str = None):
            return formalHandshake_Hardware.BooleanMultiOR(id, self, sources, keyword)

        ## Makro for building, adding and returning a hardware function of type 'Bool()', representing an "XOR" comparator of two given boolean hardware signals (signals will be connected automatically)
        def isXor(self, id: str, source1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], source2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.BooleanXOR(id, self, source1, source2, keyword)

        ## Macro for building a multiplexer of given id, multiplexing two given hardware signals depending on a given boolean hardware signal (signals will be connected automatically)
        def whenOtherwise(self, id: str, when: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], then: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], otherwise: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            return formalHandshake_Hardware.WhenOtherwise(id, self, when, then, otherwise, keyword)

        ## Macro for building a multiplexer hardware function of given id, multiplexing a given list of hardware signals with a given hardware select signal of type UInt() (signals will be connected automatically)
        def multiplex(self, id: str, type: str, select: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], inputs: list, keyword: str = None):
            if len(inputs) < 1:
                raise ValueError(F"Multiplexer {id} cannot multiplex empty list of signals")
            if len(inputs) < 2:
                raise ValueError(F"Multiplexer {id} cannot multiplex a single signal")

            ## if len == 2 -> when else statement
            ## else ... -> default value, only if not to the power of two?

            numFound = []
            for input in inputs:
                if not input in numFound:
                    numFound.append(input)
            if len(numFound) == 1:
                #print(F"Multiplexer {id} is only connected to one input source - returning this source instead")
                return inputs[0]
            else:
                if len(inputs) == 2 and select.getType() == 'Bool()':
                    return self.whenOtherwise(id, select, inputs[1], inputs[0])
                else:
                    multiplexer = formalHandshake_Hardware.Multiplexer(id, self, type, keyword)
                    for input in inputs:
                        if formalHandshake_Hardware.isHardwareSignal(input):
                            # type ? if not formalHandshake_Hardware.compareHardwareTypes(input.type, type):
                            if not formalHandshake_Hardware.compareHardwareTypes(input.getType(), type):
                                raise TypeError("Input type has to be equivalent to type")
                            multiplexer.connectInput(input)
                    self.connect(select, multiplexer.getInput('select'))
                    return multiplexer

        ## Macro for building a hardware function of given id, that outputs one of a number of given hardware signals, depending on a given chain of boolean signals condiions as conditions (signals will be connected automatically)
        def multiConditional(self, id: str, default: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], ConditionOutputPairs: list[[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]]], keyword: str = None):
            func = formalHandshake_Hardware.Multiconditional(id, self, default, ConditionOutputPairs, keyword)
            return func

        ## Macro for building a hardware function of given id, that outputs a given UInt signal, incremented by one.
        def increment(self, id: str, input: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            incrementer = formalHandshake_Hardware.Incrementer(id, self, input, keyword)
            return incrementer

        ## Macro for building a hardware function of given id, that outputs a given UInt signal, incremented by one.
        def decrement(self, id: str, input: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            decrementer = formalHandshake_Hardware.Decrementer(id, self, input, keyword)
            return decrementer

        ## Create and connect coresponding input or output ports for given signals contained in self
        def link(self, signals: Union[list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], keepNames: bool = False):
            if not isinstance(signals, list):
                temp = signals
                signals = []
                signals.append(temp)
            for signal in signals:
                if not isinstance(signal, Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
                    raise TypeError(F'{self.id} can only link hardware signals and functions')
                if isinstance(signal, formalHandshake_Hardware.Hardware_IOPort):
                    if not signal.parent.parent == self:
                        raise TypeError(F'{self.id} cannot link io {signal.id}, must be io of function or submodule')
                    if keepNames:
                        name = signal.id
                    else:
                        name = F'{signal.parent.id}_{signal.id.replace(".", "_")}_link'
                    if signal.parent.getInput(signal.id):
                        self.addInput(name, signal.getType(), signal.getKeyword())
                    if signal.parent.getOutput(signal.id):
                        self.addOutput(name, signal.getType(), signal.getKeyword())
                if isinstance(signal, formalHandshake_Hardware.Hardware_Function):
                    if not signal.parent == self:
                        raise TypeError(F'{self.id} cannot link {signal.parent.id}.{signal.id}, function belongs to other module')
                    if keepNames:
                        name = signal.id
                    else:
                        name = F'{signal.id}_link'
                    self.addOutput(name, signal.getType(), signal.getKeyword())

                self.connectAllKeywords()

        ## Create a register, that only updates, if boolean input is "True" and resets to "False" (Often needed for formal proofs to wittness properties)
        def collectBoolean(self, value: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], outputKeyword: str = None, formal: bool = True):
            id = F'{value.id}_collector'
            if not formalHandshake_Hardware.isBoolean(value):
                raise TypeError(F'Cannot build boolean collector {id}, value {value.parent.id}.{value.id} has to be boolean')
            collector = formalHandshake_Hardware.Hardware_Module(id)
            collector.className = F'{value.id[0].upper() + value.id[1:]}_Collector'
            collector.addInput(F'{value.id}_in', 'Bool()')
            self.connect(value, collector.getInput(F'{value.id}_in'))
            out = collector.addOutput(F'{value.id}_collector_out', 'Bool()', outputKeyword)

            reg = formalHandshake_Hardware.Register(F'Collector_register', collector, 'Bool()', 'False')
            collector.assumeInitial(F'!Collector_register')

            collector.connect(collector.multiplex('regIn', 'Bool()', collector.getInput(F'{value.id}_in'), [reg, collector.getInput(F'{value.id}_in')]), reg.input())
            collector.connect(reg, out)

            self.addSubModule(collector)

            return out

        ## Create a register, that only updates to new values on given boolean trigger
        def collectOnBoolean(self, id: str, value: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], trigger: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], outputKeyword: str = None):
            if not formalHandshake_Hardware.isBoolean(trigger):
                raise TypeError(F'Cannot build collector Proof {id}, trigger {trigger.parent.id}.{trigger.id} has to be boolean')
            raise NotImplementedError()


        ### Formal StatementMakros

        ## Creates a n cylce register chain of a given signal
        def past(self, value: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], cycles: int = 1, initialValue = None, assumeInitial: bool = True):
            if cycles < 1:
                raise TypeError(F'Cannot generate past of {value.parent.id}.{value.id} with less than one cycle')
            current = value
            for c in range(cycles):
                pastReg = formalHandshake_Hardware.Register(F'past_{value.id.replace('.', '_')}_{c+1}', self, value.getType(), initialValue)
                if not initialValue == None and assumeInitial:
                    self.assumeInitial(F'past_{value.id.replace('.', '_')}_{c+1} === {initialValue}')
                self.connect(current, pastReg.input())
                current = pastReg
            return current

        ## Adds a formal statement initially assuming a reset
        def assumeInitialReset(self):
            self.formalStatements.append(formalHandshake_Hardware.InitialAssumtion('ClockDomain.current.isResetActive', self))

        ## Adds a formal statement initially assuming the given boolean property
        def assumeInitial(self, booleanProperty: Union[str, formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            statement = formalHandshake_Hardware.InitialAssumtion(booleanProperty, self)
            self.formalStatements.append(statement)

        ## Adds a formal statement covering the given boolean property
        def cover(self, booleanProperty: Union[str, formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            statement = formalHandshake_Hardware.Cover(booleanProperty, self)
            self.formalStatements.append(statement)
            return statement

        ## Adds a formal statement assuming the given boolean property
        def assumption(self, booleanProperty: Union[str, formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            statement = formalHandshake_Hardware.Assumption(booleanProperty, self)
            self.formalStatements.append(statement)
            return statement

        ## Adds a formal statement asserting the given boolean property
        def assertion(self, booleanProperty: Union[str, formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            statement = formalHandshake_Hardware.Assertion(booleanProperty, self)
            self.formalStatements.append(statement)
            return statement

        ## Adds a formal construct that assumes a certain property to happen at the latest or cpecifically after a given number of cycles
        def fairness(self, trigger: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], property: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], cycles: int = 0, pipelined: bool = False, formal: bool = False, assumeInitial: bool = False):
            if not formalHandshake_Hardware.isBoolean(trigger):
                raise TypeError(F'Cannot build fairness for module {self.id}, trigger {trigger.parent.id}.{trigger.id} has to be boolean')
            if not formalHandshake_Hardware.isBoolean(property):
                raise TypeError(F'Cannot build fairness for module {self.id}, property {property.parent.id}.{property.id} has to be boolean')

            if isinstance(trigger, formalHandshake_Hardware.Hardware_IOPort):
                if not (trigger in self.inputs or trigger in self.outputs or trigger.parent.parent == self):
                    raise ValueError(F'Cannot build fairness for module {self.id}, io trigger {trigger.parent.id}.{trigger.id} is not io of module, subfunction or io of submodule')
            else:
                if not (trigger in self.functions):
                    raise ValueError(F'Cannot build fairness for module {self.id}, function trigger {trigger.parent.id}.{trigger.id} is not a subfunction')

            if isinstance(property, formalHandshake_Hardware.Hardware_IOPort):
                if not (property in self.inputs or property in self.outputs or property.parent.parent == self):
                    raise ValueError(F'Cannot build fairness for module {self.id}, io property {property.parent.id}.{property.id} is not io of module, subfunction or io of submodule')
            else:
                if not (property in self.functions):
                    raise ValueError(F'Cannot build fairness for module {self.id}, function property {property.parent.id}.{property.id} is not a subfunction')

            fairness = formalHandshake_Hardware.Fairness(F'fairness_{trigger.id.replace('.', '_')}_{property.id.replace('.', '_')}', cycles, pipelined, formal, assumeInitial)
            self.addSubModule(fairness)

            self.connect(trigger, fairness.start)
            if formal:
                self.connect(property, fairness.finish)
                #self.connect(trigger, fairness.start)
            else:
                self.connect(fairness.finish, property)

        ## Adds a formal construct that asserts a certain property to happen at the latest or cpecifically after a given number of cycles
        def liveness(self, id: str, trigger: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], property: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], maxCycles, specificCycles: bool = False, pipelined: bool = False, initialReset : bool = True):
            if not formalHandshake_Hardware.isBoolean(trigger):
                raise TypeError(F'Cannot build Liveness Proof {id}, trigger {trigger.parent.id}.{trigger.id} has to be boolean')
            if not formalHandshake_Hardware.isBoolean(property):
                raise TypeError(F'Cannot build Liveness Proof {id}, property {property.parent.id}.{property.id} has to be boolean')
            if not (trigger.parent == self or trigger.parent.parent == self):
                raise ValueError(F'Cannot build Liveness Proof {id}, trigger {trigger.parent.id}.{trigger.id} has to belong to self or a submodule')
            if not (property.parent == self or property.parent.parent == self):
                raise ValueError(F'Cannot build Liveness Proof {id}, trigger {property.parent.id}.{property.id} has to belong to self or a submodule')

            liveness = formalHandshake_Hardware.LivenessProof(id, maxCycles, specificCycles, pipelined, initialReset)
            self.addSubModule(liveness)
            self.connect(trigger, liveness.trigger())
            self.connect(property, liveness.property())
            return liveness

        ## Adds a formal construct that assumes equivalence of a given list of signals
        def assumeEquivalence(self, id: str, signals: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]]):
            return formalHandshake_Hardware.Equivalence(id, self, signals, True, True)

        ## Adds a formal construct, that asserts equivalence of a given list of signals
        def assertEquivalence(self, id: str, signals: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]]):
            return formalHandshake_Hardware.Equivalence(id, self, signals, True, False)

        ## Adds a formal construct that assumes equivalence of two modules given inputs and then asserts equivalence of the given outputs of both modules
        def equivalenceCheck(self,
                                  module1: formalHandshake_Hardware.Hardware_Module,
                                  module2: formalHandshake_Hardware.Hardware_Module,
                                  inputsModule1: list[str] = None,
                                  inputsModule2: list[str] = None,
                                  outputsModule1: list[str] = None,
                                  outputsModule2: list[str] = None,
                                  initialReset : bool = True):

            inputs1 = []
            inputs2 = []

            if inputsModule1 == None and inputsModule2 == None:
                if not (len(module1.inputs) == len(module2.inputs)):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of inputs dont match')
                for input in module1.inputs:
                    if not (module2.getInput(input.id) and input.getType() == module2.getInput(input.id).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding input for "{module1.id}.{input.id}"')
                    inputs1.append(input)
                    inputs2.append(module2.getInput(input.id))

            if ((not inputsModule1 == None) and inputsModule2 == None):
                for inputName in inputsModule1:
                    if not module1.getInput(inputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module1.id}.{inputName}"')
                    input = module1.getInput(inputName)
                    if not (module2.getInput(inputName) and input.getType() == module2.getInput(inputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding input for "{module1.id}.{input.id}"')
                    inputs1.append(input)
                    inputs2.append(module2.getInput(inputName))

            if (inputsModule1 == None and (not inputsModule2 == None)):
                for inputName in inputsModule2:
                    if not module2.getInput(inputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module2.id}.{inputName}"')
                    input = module2.getInput(inputName)
                    if not (module1.getInput(inputName) and input.getType() == module1.getInput(inputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding input for "{module2.id}.{input.id}"')
                    inputs2.append(input)
                    inputs1.append(module1.getInput(inputName))

            if not (inputsModule1 == None or inputsModule2 == None):
                if not len(inputsModule1) == len(inputsModule2):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of inputs dont match')
                for i, inputName1 in enumerate(inputsModule1):
                    inputName2 = inputsModule2[i]
                    if not module1.getInput(inputName1):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module1.id}.{inputName1}"')
                    if not module2.getInput(inputName2):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module2.id}.{inputName2}"')
                    input1 = module1.getInput(inputName1)
                    input2 = module2.getInput(inputName2)
                    if not input1.getType() == input2.getType():
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because inputs "{module1.id}.{inputName1}" ({input1.getType()}) and "{module2.id}.{inputName2}" ({input2.getType()}) types dont match')
                    inputs1.append(input1)
                    inputs2.append(input2)

            outputs1 = []
            outputs2 = []

            if outputsModule1 == None and outputsModule2 == None:
                if not (len(module1.outputs) == len(module2.outputs)):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of outputs dont match')
                for output in module1.outputs:
                    if not (module2.getOutput(output.id) and output.getType() == module2.getOutput(output.id).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding output for "{module1.id}.{output.id}"')
                    outputs1.append(output)
                    outputs2.append(module2.getOutput(output.id))

            if ((not outputsModule1 == None) and outputsModule2 == None):
                for outputName in outputsModule1:
                    if not module1.getOutput(outputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module1.id}.{outputName}"')
                    output = module1.getOutput(outputName)
                    if not (module2.getOutput(outputName) and output.getType() == module2.getOutput(outputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding output for "{module1.id}.{output.id}"')
                    outputs1.append(output)
                    outputs2.append(module2.getOutput(outputName))

            if (outputsModule1 == None and (not outputsModule2 == None)):
                for outputName in outputsModule2:
                    if not module2.getOutput(outputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module2.id}.{outputName}"')
                    output = module2.getOutput(outputName)
                    if not (module1.getOutput(outputName) and output.getType() == module1.getOutput(outputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding output for "{module2.id}.{output.id}"')
                    outputs2.append(output)
                    outputs1.append(module1.getOutput(outputName))

            if not (outputsModule1 == None or outputsModule2 == None):
                if not len(outputsModule1) == len(outputsModule2):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of outputs dont match')
                for i, outputName1 in enumerate(outputsModule1):
                    outputName2 = outputsModule2[i]
                    if not module1.getOutput(outputName1):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module1.id}.{outputName1}"')
                    if not module2.getOutput(outputName2):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module2.id}.{outputName2}"')
                    output1 = module1.getOutput(outputName1)
                    output2 = module2.getOutput(outputName2)
                    if not output1.getType() == output2.getType():
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because outputs "{module1.id}.{outputName1}" ({output1.getType()}) and "{module2.id}.{outputName2}" ({output2.getType()}) types dont match')
                    outputs1.append(output1)
                    outputs2.append(output2)

            equivalence = formalHandshake_Hardware.EquivalenceProof(F'{module1.id}_equals_{module2.id}', inputs1, inputs2, outputs1, outputs2, initialReset)
            equivalence.parent = self

            self.addSubModule(equivalence)
            self.connectAllKeywords()
            return equivalence

        ## Adds a formal construct that assumes equivalence of two modules given inputs at the time, each of their respective "start" property was true for the first time.
        # Then the given outputs of both modules are asserted to be equivalent, at the time each respective "finish" propery was set to true.
        # In Other words, this is an asynchroneous Equivalence check, that can be seperatly triggered by each module.
        def equivalenceCheckTriggered(self,
                                  module1: formalHandshake_Hardware.Hardware_Module,
                                  module2: formalHandshake_Hardware.Hardware_Module,
                                  start1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None,
                                  finish1: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None,
                                  start2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None,
                                  finish2: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function] = None,
                                  inputsModule1: list[str] = None,
                                  inputsModule2: list[str] = None,
                                  outputsModule1: list[str] = None,
                                  outputsModule2: list[str] = None,
                                  initialReset : bool = True):

            inputs1 = []
            inputs2 = []

            ## Two plain modules, that need to have equivalent inputs
            if inputsModule1 == None and inputsModule2 == None:
                if not (len(module1.inputs) == len(module2.inputs)):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of inputs dont match')
                for input in module1.inputs:
                    if not (module2.getInput(input.id) and input.getType() == module2.getInput(input.id).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding input for "{module1.id}.{input.id}"')
                    inputs1.append(input)
                    inputs2.append(module2.getInput(input.id))

            ## inputs for module1 given, inputs for module 2 have to be equivalent
            if ((not inputsModule1 == None) and inputsModule2 == None):
                for inputName in inputsModule1:
                    if not module1.getInput(inputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module1.id}.{inputName}"')
                    input = module1.getInput(inputName)
                    if not (module2.getInput(inputName) and input.getType() == module2.getInput(inputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding input for "{module1.id}.{input.id}"')
                    inputs1.append(input)
                    inputs2.append(module2.getInput(inputName))

            ## inputs for module2 given, inputs for module1 have to be equivalent
            if (inputsModule1 == None and (not inputsModule2 == None)):
                for inputName in inputsModule2:
                    if not module2.getInput(inputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module2.id}.{inputName}"')
                    input = module2.getInput(inputName)
                    if not (module1.getInput(inputName) and input.getType() == module1.getInput(inputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding input for "{module2.id}.{input.id}"')
                    inputs2.append(input)
                    inputs1.append(module1.getInput(inputName))

            ## Two input lists given, have to be equivalent
            if not (inputsModule1 == None or inputsModule2 == None):
                if not len(inputsModule1) == len(inputsModule2):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of inputs dont match')
                for i, inputName1 in enumerate(inputsModule1):
                    inputName2 = inputsModule2[i]
                    if not module1.getInput(inputName1):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module1.id}.{inputName1}"')
                    if not module2.getInput(inputName2):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no input "{module2.id}.{inputName2}"')
                    input1 = module1.getInput(inputName1)
                    input2 = module2.getInput(inputName2)
                    if not input1.getType() == input2.getType():
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because inputs "{module1.id}.{inputName1}" ({input1.getType()}) and "{module2.id}.{inputName2}" ({input2.getType()}) types dont match')
                    inputs1.append(input1)
                    inputs2.append(input2)

            outputs1 = []
            outputs2 = []

            ## Two plain modules, that need to have equivalent outputs
            if outputsModule1 == None and outputsModule2 == None:
                if not (len(module1.outputs) == len(module2.outputs)):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of outputs dont match')
                for output in module1.outputs:
                    if not (module2.getOutput(output.id) and output.getType() == module2.getOutput(output.id).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding output for "{module1.id}.{output.id}"')
                    outputs1.append(output)
                    outputs2.append(module2.getOutput(output.id))

            ## outputs for module1 given, outputs for module2 have to be equivalent
            if ((not outputsModule1 == None) and outputsModule2 == None):
                for outputName in outputsModule1:
                    if not module1.getOutput(outputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module1.id}.{outputName}"')
                    output = module1.getOutput(outputName)
                    if not (module2.getOutput(outputName) and output.getType() == module2.getOutput(outputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding output for "{module1.id}.{output.id}"')
                    outputs1.append(output)
                    outputs2.append(module2.getOutput(outputName))

            ## outputs for module2 given, outputs for module1 have to be equivalent
            if (outputsModule1 == None and (not outputsModule2 == None)):
                for outputName in outputsModule2:
                    if not module2.getOutput(outputName):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module2.id}.{outputName}"')
                    output = module2.getOutput(outputName)
                    if not (module1.getOutput(outputName) and output.getType() == module1.getOutput(outputName).getType()):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no corresponding output for "{module2.id}.{output.id}"')
                    outputs2.append(output)
                    outputs1.append(module1.getOutput(outputName))

            ## Two input lists given, have to be equivalent
            if not (outputsModule1 == None or outputsModule2 == None):
                if not len(outputsModule1) == len(outputsModule2):
                    raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because number of outputs dont match')
                for i, outputName1 in enumerate(outputsModule1):
                    outputName2 = outputsModule2[i]
                    if not module1.getOutput(outputName1):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module1.id}.{outputName1}"')
                    if not module2.getOutput(outputName2):
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", there is no output "{module2.id}.{outputName2}"')
                    output1 = module1.getOutput(outputName1)
                    output2 = module2.getOutput(outputName2)
                    if not output1.getType() == output2.getType():
                        raise ValueError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}", because outputs "{module1.id}.{outputName1}" ({output1.getType()}) and "{module2.id}.{outputName2}" ({output2.getType()}) types dont match')
                    outputs1.append(output1)
                    outputs2.append(output2)

            a1 = start1
            if a1 == None:
                a1 = self.const('Bool()', 'True')
            else:
                if not formalHandshake_Hardware.isBoolean(start1):
                    raise TypeError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}" with non boolean start1 signal "{start1.parent.id}.{start1.id}"')
            a2 = start2
            if a2 == None:
                a2 = self.const('Bool()', 'True')
            else:
                if not formalHandshake_Hardware.isBoolean(start2):
                    raise TypeError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}" with non boolean start2 signal "{start2.parent.id}.{start2.id}"')

            b1 = finish1
            if b1 == None:
                b1 = self.const('Bool()', 'True')
            else:
                if not formalHandshake_Hardware.isBoolean(finish1):
                    raise TypeError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}" with non boolean finish1 signal "{finish1.parent.id}.{finish1.id}"')
            b2 = finish2
            if b2 == None:
                b2 = self.const('Bool()', 'True')
            else:
                if not formalHandshake_Hardware.isBoolean(finish2):
                    raise TypeError(F'Cannot build equivalence check for module "{module1.id}" and module "{module2.id}" with non boolean finish2 signal "{finish2.parent.id}.{finish2.id}"')

            equivalence = formalHandshake_Hardware.EquivalenceProofTriggerd(F'{module1.id}_equals_{module2.id}', inputs1, inputs2, outputs1, outputs2, initialReset)
            equivalence.parent = self

            self.connect(a1, equivalence.start1())
            self.connect(a2, equivalence.start2())
            self.connect(b1, equivalence.finish1())
            self.connect(b2, equivalence.finish2())

            self.addSubModule(equivalence)
            self.connectAllKeywords()

            #equivalence.display()
            #equivalence.draw_Grid_network(False, True)
            return equivalence


        ### Advanced hardware circuit building makros:

        ## Adds a one-cylce delay to each output, by Wrapping module in new module inserting registers before the new outputs
        def bufferOutputs(self):
            if not self.parent == None:
                raise ValueError(F'Cannot buffer outputs of module {self.id}, because it is already integrated in module {self.parent.id}')
            newModule = formalHandshake_Hardware.Hardware_Module(F'{self.id}_buffered')
            newModule.className = self.id[0].upper() + self.id[1:] + '_buffered'
            newModule.addSubModule(self)
            newModule.link(self.inputs, keepNames=True)
            for output in self.outputs:
                formalHandshake_Hardware.Register((F'{output.id}_reg').replace('.', '_'), newModule, output.getType(), None, output.getKeyword(), newModule.addOutput(output.id, output.getType()).getKeyword())
            newModule.connectAllKeywords()
            return newModule

        ## Advanced Network Management

        ## Performs a graph decomposition of all Nodes, effectively flattening the hirarchy so only functions and no more modules are contained in this module
        def extractAllSubModules(self, linkOpenIO: bool = False):
            if self.blackbox:
                raise ValueError(F'Module "{self.id}" cannot extract submodules, it is a blackbox')
            deleted = []
            for module in self.subModules:
                if module.blackbox:
                    raise ValueError(F'Module "{self.id}" cannot extract submodule "{module.id}", it is a blackbox')
                module.extractAllSubModules()

                for function in module.functions:
                    if isinstance(function, formalHandshake_Hardware.Const):
                        const = self.const(function.getType(), function.definition)
                        for destination in function.destinations:
                            self.connect(const, destination)
                    else:
                        function.id = F'{function.parent.id}_{function.id}' #_extracted'
                        function.parent = self
                        self.addFunction(function)

                for signal in module.inputs + module.outputs:
                    destinations = signal.destinations
                    source = signal.source
                    for destination in destinations:
                        if destination.source == signal:
                            destination.source = source
                    if not (source == 0 or source == None):
                        if signal in source.destinations:
                            source.destinations.remove(signal)
                        source.destinations += destinations

                deleted.append(module)
            for module in deleted:
                self.remove(module)
            
            if linkOpenIO:
                for function in self.functions:
                    if len(function.destinations) == 0:
                        self.connect(function, self.addOutput(F'{function.id}', function.getType()))
                    for input in function.inputs:
                        if input.source == 0 or input.source == None:
                            self.connect(self.addInput(F'{function.id}_{input.id}', input.getType()), input)

        ## Replaces all contained registers functions witch a corresponding input for the current value and an output for the next value
        def externalizeRegisters(self, addToParent: bool = False):
            if self.blackbox:
                raise ValueError(F'Module "{self.id}" cannot externalize registers, it is a blackbox')
            regs = []
            for function in self.functions:
                if isinstance(function, formalHandshake_Hardware.Register): # or function.cycles == 1:
                    regInput = function.inputs[0]
                    source = function.inputs[0].source
                    destinations = function.destinations
                    regType = function.getType()
                    initVal = function.initialValue
                    input = self.addInput(F'{function.id}_external_reg_output', regType)
                    output = self.addOutput(F'{function.id}_external_reg_input', regType)
                    regs.append([function.id, regType, initVal, output, input])
                    if isinstance(source, Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]) and regInput in source.destinations:
                        source.destinations.remove(regInput)
                        self.connect(source, output)
                        function.source = 0
                    for destination in destinations:
                        self.connect(input, destination)
                        function.destinations = []
                    if addToParent:
                        if isinstance(self.parent, formalHandshake_Hardware.Hardware_Module):
                            function.parent = self.parent
                            self.parent.addFunction(function)
                            self.parent.connect(function, input)
                            self.parent.connect(output, function.inputs[0])
                        else:
                            raise ValueError(F'Module "{self.id}" cannot externalize registers and add them to parent, because parent is no module')
                    else:
                        self.remove(function)
            return regs

        ## Create a copy of this module
        def copy(self, id: str):    #, newParent: formalHandshake_Hardware.Hardware_Module):
            #print(F'Module "{self.id}" is trying to copy itself')
            new = formalHandshake_Hardware.Hardware_Module(id)

            new.blackbox = new.blackbox
            new.className = self.className
            new.filePath = self.filePath
            new.isFormal = self.isFormal

            signals = []

            for input in self.inputs:
                signals.append([input, new.addInput(input.id, input.getType())])
            for output in self.outputs:
                new.addOutput(output.id, output.getType())
            for function in self.functions:
                signals.append([function, function.copy(function.id, new)])
            for module in self.subModules:
                newModule = new.addSubModule(module.new(module.id))
                for o, output in enumerate(module.outputs):
                    signals.append(output, newModule.outputs[o])

            for s, signal in enumerate(signals):
                #print(F'Trying to connect signal "{signal[0].id}", signals Match:  {signal[0].parent.id}.{signal[0].id} (destinations: {len(signal[0].destinations)}) -> {signal[1].parent.id}.{signal[1].id} (destinations: {len(signal[1].destinations)})')
                for destination in signal[0].destinations:
                    #print(F' -> destination: {destination.parent.id}.{destination.id}')
                    found = False
                    if destination in self.outputs:
                        for o, output in enumerate(self.outputs):
                            if destination == output:
                                found = True
                                #print(F'    -> found: destination is own output "{output.id}"')
                                new.connect(signals[s][1], new.outputs[o])
                                break
                    ## search for function inputs
                    if not found:
                        for f, function in enumerate(self.functions):
                            if destination in function.inputs:
                                for i2, funcIn in enumerate(function.inputs):
                                    if destination == funcIn:
                                        found = True
                                        #print(F'    -> found: destination is functions input "{function.id}.{funcIn.id}"')
                                        new.connect(signals[s][1], new.functions[f].inputs[i2])
                                        break
                                break
                    ## search for module inputs
                    if not found:
                        print(F'Module "{self.id}" is copying itself, but modules are missing')

                    if not found:
                        print(F'!! Warning - Could not properly copy "{self.id}" as "{id}" no connection found for destination "{destination.id}" of signal "{signal[0].id}"')

            return new

        ## advanced dataflow analysis
        ## Returns a list of all direct non-sequential predecessors
        def getCombinationalPredecessors(self):
            predecessors = set()
            for input in self.inputs:
                if isinstance(input.source, IOPort):
                    if isinstance(input.source.parent, Module):
                        ## check if other submodule of same parent and not connected to inputs of parent module
                        if input.source in input.source.parent.outputs:
                            predecessors.add(input.source.parent)
                if isinstance(input.source, Function):
                    predecessors.add(input.source)
            return predecessors

        ## Returns a list of all non-sequential predecessors
        def listAllCombinationalPredecessors(self, found=None):
            #print(F"looking for predecessors of: {self.id}")
            if found is None:
                found = set()

            predecessors = set()

            for pred in self.getCombinationalPredecessors():
                if pred not in found:
                    found.add(pred)
                    predecessors.add(pred)
                    predecessors.update(pred.listAllCombinationalPredecessors(found))
            return predecessors

        ## Checks, if any contained node has a purely combinational connection from one of its outputs to one of its own inputs
        def checkForCombinationalLoops(self):
            print(' --- check for combinational loops in:', self.id)
            for element in self.subModules + self.functions:
                if element in element.listAllCombinationalPredecessors():
                    print(F"    -> combinational loop detected for {element.parent.id}.{element.id}")
                    self.internalLoopsChecked = False
                    return False
            self.internalLoopsChecked = True
            return True


    ## Prebuild Counter with a given max and a given initial value - increments internal UInt register, when increment input is True
    class Counter(Hardware_Module):
        def __init__(self, id: str, maxValue: int, initialValue: int = 0, keywordInc: str = None, keywordVal: str = None):
            super().__init__(id)
            self.className = F'Counter_{maxValue}'
            self.maxValue = maxValue
            self.outputType = F'UInt({(maxValue).bit_length()} bits)'
            self.addInput('increment', 'Bool()', keywordInc)
            self.addOutput('value', self.outputType, keywordVal)
            initValue = F'U"{format(initialValue, f'0{(maxValue).bit_length()}b')}"'
            reg = formalHandshake_Hardware.Register('countValue', self, self.outputType, initValue)
            self.connect(reg, self.value())
            
            add = formalHandshake_Hardware.Incrementer('add', self, reg)
            #add = formalHandshake_Hardware.Hardware_Function('add', self, self.outputType, 0)
            #add.connectInput(reg)
            #add.connectInput(self.const(self.outputType, F'U(1, {(maxValue).bit_length()} bits)'))
            #add.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(add.inputs[0], self)} + 1'
            isMax = self.equals('isMax', reg, self.const(F'UInt({(maxValue).bit_length()} bits)', F'U"{format(maxValue, f'0{(maxValue).bit_length()}b')}"'))
            nextValue = self.multiConditional('nextValue', reg, [[self.isAnd('overflow', isMax, self.getInput('increment')), self.const(self.outputType, initValue)], [self.increment(), add]])
            self.connect(nextValue, reg.input())

        def value(self):
            return self.getOutput('value')

        def increment(self):
            return self.getInput('increment')

    ## Conter with increment and decrement functionality
    class AdvancedCounter(Hardware_Module):
         def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, maxVal: int, initialValue: int = 0):  #, keywordIn: str = None, keywordOut: str = None, keywordStore: str = None):
            if maxVal < 1:
                raise ValueError(F'Cannot build advanceCounter "{id}" with maximum value smaller than 1')
            if maxVal < initialValue:
                raise ValueError(F'Cannot build advanceCounter "{id}" with maximum value "{maxVal}" smaller than initial Value "{initialValue}"')

            super().__init__(id)
            self.className = F'AdvancedCounter_{maxVal}_{initialValue}'
            self.parent = parent
            parent.addSubModule(self)

            bits = maxVal.bit_length()
            type = F'UInt({bits} bits)'

            value = formalHandshake_Hardware.Register('value', self, type, F'U({initialValue}, {bits} bits)')
            self.connect(value, self.addOutput('io.value', type))
            self.increase = self.addInput('io.inc', 'Bool()')
            self.decrease = self.addInput('io.dec', 'Bool()')

            empty = self.equals('empty', value, self.const(type, F'U({0}, {bits} bits)'))
            full = self.equals('full', value, self.const(type, F'U({maxVal}, {bits} bits)'))
            self.empty = self.addOutput('io.empty', 'Bool()')
            self.connect(empty, self.empty)
            self.full = self.addOutput('io.full', 'Bool()')
            self.connect(full, self.full)

            increase = self.multiAnd('increase', [self.increase, self.isNot('notDecrease', self.decrease), self.isNot('notFull', full)])
            decrease = self.multiAnd('decrease', [self.decrease, self.isNot('notIncreas', self.increase), self.isNot('notEmpty', empty)])
            change = self.isOr('change', increase, decrease)
            #add = formalHandshake_Hardware.AdderUnsigned('add', self, bits, value, self.const(type, F'U({1}, {bits} bits)'), asUInt= True)
            add = self.increment('add', value)
            #subtract = formalHandshake_Hardware.SubtractUnsigned('subtract', self, bits, value, self.const(type, F'U({1 + maxVal}, {bits} bits)'), asUInt= True)
            subtract = self.decrement('subtract', value)
            changeValue = self.whenOtherwise('changeValue', increase, add, subtract)
            nextValue = self.whenOtherwise('nextValue', change, changeValue, value)
            self.connect(nextValue, value.input())

    ## FiFo Implementation
    class FIFO(Hardware_Module):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str, depth: int, initialValue: str = None):  #, keywordIn: str = None, keywordOut: str = None, keywordStore: str = None):
            if depth < 1:
                raise ValueError(F'Cannot build FIFO "{id}" with depth smaller than 1')
            super().__init__(id)
            self.className = F'FIFO_{type.replace('(', '').replace(')', '').replace(' ', '').replace(',', '')}_{depth}'
            self.parent = parent
            parent.addSubModule(self)
            bits = (depth - 1).bit_length()

            self.write = self.addInput('io.write', 'Bool()')
            self.write_data = self.addInput('io.write_data', type)
            self.read = self.addInput('io.read', 'Bool()')
            self.full = self.addOutput('io.full', 'Bool()')
            self.empty = self.addOutput('io.empty', 'Bool()')
            self.read_data = self.addOutput('io.read_data', type)

            storedValues = formalHandshake_Hardware.AdvancedCounter('storedValues', self, depth, 0)
            self.connect(storedValues.full, self.full)
            self.connect(storedValues.empty, self.empty)
            self.connect(self.write, storedValues.increase)
            self.connect(self.read, storedValues.decrease)

            writePointer = formalHandshake_Hardware.Counter('writePointer', (depth - 1))
            self.addSubModule(writePointer)
            self.connect(self.write, writePointer.increment())
            readPointer = formalHandshake_Hardware.Counter('readPointer', (depth - 1))
            self.addSubModule(readPointer)
            self.connect(self.read, readPointer.increment())

            regOutputs = []

            for i in range(depth):
                reg = formalHandshake_Hardware.LoopedReg(F'reg_{(i+1)}', self, type)
                regOutputs.append(reg.value())
                self.connect(self.write_data, reg.input())
                write = self.equals(F'write_{(i+1)}', writePointer.value(), self.const(F'UInt({bits} bits)', F'U({i}, {bits} bits)'))
                self.connect(write, reg.store())

            readValue = self.multiplex('readValue', type, readPointer.value(), regOutputs)
            meptyReadWrite = self.multiAnd('emtpyReadWrite', [self.empty, self.read, self.write])
            bypass = self.whenOtherwise('bypass', meptyReadWrite, self.write_data, readValue)
            self.connect(bypass, self.read_data)

    ## StateMaschine Builder
    ## Providing a State class and a FSM class, allowing to build a hardware finite statemschine of given IOs, states, state transitions and state- (and input-) dependent outputs

    ## State with list of output functions and list of conditional/non-conditional transitions to a following state
    class State:
        def __init__(self, id: str, outputs: list = None):
            self.id = id
            self.outputs = outputs or [] # tuples of output-id and corresponding output signal/function
            self.transitions = []  # tuples of next_state_name and condition(can be "None" or boolean hardware signal)

        def addTransition(self, next_state: str, condition = None):
            self.transitions.append((next_state, condition))

        ## Builds a hardware function for the next state, depending on certain inputs, from the given state transitions
        def buildNextStateFunction(self, fsm: formalHandshake_Hardware.FSM):
            if len(self.transitions) < 1:
                raise ValueError(F'State "{self.id}" has no transitions registered')
            pairs = []
            for transition in self.transitions:
                if transition[1] == None:
                    nextStateFunction = fsm.const(fsm.stateType, fsm.getStateUIntFromID(transition[0]))
                    return nextStateFunction
                else:
                    pairs.append((transition[1], fsm.const(fsm.stateType, fsm.getStateUIntFromID(transition[0]))))
            return fsm.multiConditional(F'{self.id[0].lower() + self.id[1:]}_nextState', fsm.const(fsm.stateType, fsm.getStateUIntFromID(self.id)), pairs)

    ## Finite State Maschine
    class FSM(Hardware_Module):
        def __init__(self, id: str):
            super().__init__(id)
            #self.className = (id[0].upper() + id[1:]+ '_FSM')
            ## self connect to Reg in/out?
            self.defaultValues = [] # default output value, if no specific value is given for a state
            self.states = []    # list of states
            self.stateType = 'UInt(1 bit)'  # dynamically adjusted to number of states
            self.initialState = None       ## initial state
            self.currentState = None    ## either input or output of internel state register -> will be linked by installState()
            self.nextState = None    ## either output or input of internel state register -> will be linked by installState()
            self.externalReg = True

        ## add output with specific type and specific defaul value (can be hardware IOPort or Function)
        def addOutput(self, id: str, type: str, defaultValue: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function], keyword: str = None):
            ## check if given default value is this FSMs input or internal signal
            if not defaultValue.parent == self:
                raise ValueError("defaultValue has to be hardware IOPort or Function of this fsm")
            ## Expect IO_Port or Func with corresponding Type
            # type ? if not formalHandshake_Hardware.compareHardwareTypes(defaultValue.type, type):
            if not formalHandshake_Hardware.compareHardwareTypes(defaultValue.getType(), type):
                raise TypeError("defaultValue has to be of same type as output")
            ## somehow store the value?
            output = formalHandshake_Hardware.Hardware_IOPort(id, self, type, keyword)
            self.outputs.append(output)
            self.defaultValues.append(defaultValue)
            return output

        ## adds a state of certain ID, initial state marker and list of statedependend outputs
        def addState(self, id: str, initial: bool, outputs: list = None):
            if not outputs == None:
                for output in outputs:
                    if not (isinstance(output, tuple) and isinstance(output[0], str) and formalHandshake_Hardware.isHardwareSignal(output[1])):
                        raise TypeError(F'Invalid output - value tuple given for state {id}')
                    if not self.getOutput(output[0]):
                        raise ValueError(F'Output {output[0]} given for state {id} is not and output of {self.id}')
            state = formalHandshake_Hardware.State(id, outputs)
            if initial:
                self.initialState = state
            self.states.append(state)
            return state

        ## returns the state with given ID or thorws error, if state is not registered
        def getState(self, id: str):
            for state in self.states:
                if state.id == id:
                    return state
            raise ValueError(F'No state with id {id} registered for {self.id}')

        ## returns the state number for the state with a given ID and thorws error, if state is not registered
        def getStateUIntFromID(self, id: str):
            for i, state in enumerate(self.states):
                if state.id == id:
                    return F'U"{bin(i)[2:].zfill((len(self.states) - 1).bit_length())}"'
            raise ValueError(F'No state with id {id} registered for {self.id}')

        ## Adds a conditional/non-conditional transition from a given state to a second given state - accepts only boolean hardware signals as a condition
        def addTransition(self, from_state: str, to_state: str, condition=None):
            if not (self.getState(from_state)):
                raise ValueError("Not a valid starting state")
            if not (self.getState(to_state)):
                raise ValueError("Not a valid target state")
            if (condition == None or formalHandshake_Hardware.isBoolean(condition)):
                self.getState(from_state).addTransition(to_state, condition)
            else:
                raise TypeError(F'Condition for state transition has to be either None or a boolean hardware function')

        ## Either adds input and output or an internal state register and links them to the corresponding currentState and nextState signals
        def installState(self, internal = False):
            if self.initialState == None:
                raise ValueError(F'Cannot install state for FSM {self.id} - no initial state defined')
            self.stateType = F'UInt({((len(self.states) - 1)).bit_length()} bits)'
            if internal:
                state = formalHandshake_Hardware.Register('state', self, self.stateType, self.getStateUIntFromID(self.initialState.id))
                self.currentState = state
                self.nextState = state.input()
            else:
                self.addInput('currentState', self.stateType)
                self.currentState = self.getInput('currentState')
                nextStateOutput = formalHandshake_Hardware.Hardware_IOPort('nextState', self, self.stateType)
                self.outputs.append(nextStateOutput)
                self.nextState = nextStateOutput

        ## Builds a "fake" FSM for testing and defines "worst case" input dependencies for all the outputs, no Sates or Transitions needed
        def buildAbstractFSM(self, internalReg=False, mealy=False):
            self.installState(internalReg)
            for output in self.outputs:
                if not output.id == 'nextState':
                    # type ? func = formalHandshake_Hardware.Hardware_Function(F'{output.id}_function', self, output.type, 0)
                    func = formalHandshake_Hardware.Hardware_Function(F'{output.id}_function', self, output.getType(), 0)
                    self.connect(func, output)

                    # type ? input = formalHandshake_Hardware.Hardware_IOPort('stateIn', func, self.currentState.type)
                    input = formalHandshake_Hardware.Hardware_IOPort('stateIn', func, self.currentState.getType())
                    func.inputs.append(input)
                    self.connect(self.currentState, input)

                    ## Mealy: outputs also depend on inputs
                    if mealy:
                        i = 0
                        for input in self.inputs:
                            if not input.id == 'stateIn':
                                # type ? inp = formalHandshake_Hardware.Hardware_IOPort(F'i{i}', func, input.type)
                                inp = formalHandshake_Hardware.Hardware_IOPort(F'i{i}', func, input.getType())
                                func.inputs.append(inp)
                                self.connect(input, inp)
                                i += 1
            ## connecting nextState function
            i = 0
            # type ? nextStateFunc = formalHandshake_Hardware.Hardware_Function(F'nextState_function', self, self.nextState.type, 0)
            nextStateFunc = formalHandshake_Hardware.Hardware_Function(F'nextState_function', self, self.nextState.getType(), 0)

            if internalReg:
                # type ? input = formalHandshake_Hardware.Hardware_IOPort(F'currentStateIn', nextStateFunc, self.currentState.type)
                input = formalHandshake_Hardware.Hardware_IOPort(F'currentStateIn', nextStateFunc, self.currentState.getType())
                nextStateFunc.inputs.append(input)
                self.connect(self.currentState, input)

            for input in self.inputs:
                # type ? inp = formalHandshake_Hardware.Hardware_IOPort(F'i{i}', nextStateFunc, input.type)
                inp = formalHandshake_Hardware.Hardware_IOPort(F'i{i}', nextStateFunc, input.getType())
                nextStateFunc.inputs.append(inp)
                self.connect(input, inp)
                i += 1
            self.connect(nextStateFunc, self.nextState)

        ## Multiplexes the state reg input or the nextState output from all the states individual nextstate functions, depending on the current state
        def installNextStateFunction(self):
            nextStates = []
            for state in self.states:
                nextStates.append(state.buildNextStateFunction(self))
            self.connect(self.multiplex('nextStateFunction', self.stateType, self.currentState, nextStates), self.nextState)

        ## Multiplexes each of the FSMs output signals with all the state-dependent output functions or the outputs given default value, depending on the current state
        def installOutputFunctions(self):
            o = 0
            for output in self.outputs:
                if not (output == self.nextState):
                    values = []
                    for state in self.states:
                        value = self.defaultValues[o]
                        for pair in state.outputs:
                            outputId = pair[0]
                            if outputId == output.id:
                                value = pair[1]
                        values.append(value)
                    # type ? outputFunction = self.multiplex(F'{output.id}_function', output.type, self.currentState, values)
                    outputFunction = self.multiplex((F'{output.id}_function').replace('.', '_'), output.getType(), self.currentState, values)
                    self.connect(outputFunction, output)
                    o += 1

        ## Completly builds and connects the FSMs internal network from all given information
        def buildFSM(self, internalReg: bool = False):
            self.externalReg = not internalReg
            self.installState(internalReg)
            self.installNextStateFunction()
            self.installOutputFunctions()

        ## ?
        def show(self, outputValues: bool = False, conditions: bool = False, show: bool = True, save: bool = False, nonDefaultVaulesOnly: bool = True):
            print(F' --- showing state maschine "{self.id}"')

            if self.initialState == None:
                raise ValueError(F'Cannot show state maschine "{self.id}" withput an initial state')

            column = []
            nextColumn = []
            done = []
            nodes = []
            outputs = []
            connections = []
            column.append(self.initialState)
            done.append(self.initialState)
            while len(column) > 0:
                ids = []
                outputStrings = []
                for currentState in column:
                    #done.append(currentState)
                    #print(F' -> CurrentState is "{currentState.id}"')
                    for transition in currentState.transitions:
                        found = False
                        for state in self.states:
                            if state.id == transition[0]:
                                targetState = state
                                if transition[1] == None:
                                    condition = ''
                                else:
                                    if isinstance(transition[1], formalHandshake_Hardware.Hardware_Function):
                                        if isinstance(transition[1], formalHandshake_Hardware.Const):
                                            condition = F'{transition[1].id}'
                                        else:
                                            condition = F'{transition[1].definition}'
                                    else:
                                        condition = F'{transition[1].id}'
                                #condition = transition[1]
                                #print(F'    -> found transition to {targetState.id}')

                                connections.append([currentState.id, targetState.id, condition])

                                found = True
                                if not targetState in done:
                                    done.append(targetState)
                                    nextColumn.append(targetState)
                                break
                        if not found:
                            raise ValueError(F'Fsm "{self.id}" annot find target state {transition[0]} for transition from {currentState.id}')

                    if outputValues:
                        if nonDefaultVaulesOnly:
                            outputstring = ''
                            o = 0
                            for output in self.outputs:
                                #print(F'o is {o}')
                                if not (self.externalReg and output.id == 'nextState'):
                                    #print(F'Output: {output.id}')
                                    found = None
                                    for output2 in currentState.outputs:
                                        if output.id == output2[0]:
                                            found = output2
                                            break
                                    if found == None:
                                        #print(F'!!! -> {output.id} not found, default value is: {self.defaultValues[o].id}')
                                        source = self.defaultValues[o]
                                    else:
                                        source = found[1]
                                        if isinstance(source, formalHandshake_Hardware.Hardware_Function):
                                            if isinstance(source, formalHandshake_Hardware.Const):
                                                definition = F'{source.id}'
                                            else:
                                                definition = F'{source.definition}'
                                        else:
                                            definition = F'{source.id}'

                                        #print(F'!!! {output.id} := {definition} ')
                                        outputstring += F'\n{output.id} := {definition}'
                                        o += 1
                            outputStrings.append(outputstring)
                        else:
                            outputstring = ''
                            o = 0
                            for output in self.outputs:
                                #print(F'o is {o}')
                                if not (self.externalReg and output.id == 'nextState'):
                                    #print(F'Output: {output.id}')
                                    found = None
                                    for output2 in currentState.outputs:
                                        if output.id == output2[0]:
                                            found = output2
                                            break
                                    if found == None:
                                        #print(F'!!! -> {output.id} not found, default value is: {self.defaultValues[o].id}')
                                        source = self.defaultValues[o]
                                    else:
                                        source = found[1]
                                    if isinstance(source, formalHandshake_Hardware.Hardware_Function):
                                        if isinstance(source, formalHandshake_Hardware.Const):
                                            definition = F'{source.id}'
                                        else:
                                            definition = F'{source.definition}'
                                    else:
                                        definition = F'{source.id}'

                                    #print(F'!!! {output.id} := {definition} ')
                                    outputstring += F'\n{output.id} := {definition}'
                                    o += 1
                            outputStrings.append(outputstring)

                    ids.append(currentState.id)
                nodes.append(ids)
                if outputValues:
                    outputs.append(outputStrings)
                column = nextColumn
                nextColumn = []

            G = nx.DiGraph()

            ## Add Nodes
            numNodes = 0
            for c, column in enumerate(nodes):
                for s, stateId in enumerate(column):
                    if stateId == self.initialState.id:
                        t = 'initial'
                    else:
                        t = 'normal'
                    if outputValues:
                        G.add_node(stateId, type=t, value=outputs[c][s])
                    else:
                        G.add_node(stateId, type=t)
                    numNodes += 1


            ## Add edges
            if numNodes > 0:
                for connection in connections:
                    type = 'condition'
                    if connection[2] == '': type = 'always'
                    if conditions:
                        G.add_edge(connection[0], connection[1], label = connection[2], type=type)
                    else:
                        G.add_edge(connection[0], connection[1], type=type)

                pos = {}

                def scale_position(cell, scale=100):
                    # Converts grid cell (row, col) to plot coordinates
                    return (cell[1] * scale, -cell[0] * scale)  # X = col, Y = -row (invert Y for top-down)

                # --- Position nodes based on firstCell (grid coordinates) ---
                for c, column in enumerate(nodes):
                    for s, stateId in enumerate(column):
                        pos[stateId] = scale_position((c, s))

                # --- Coloring nodes based on type ---
                color_map = {
                    'initial': 'lightgreen',
                    'normal': 'skyblue',
                    'condition': "grey",
                    'always': 'black'
                }
                node_colors = [color_map.get(G.nodes[n].get('type'), 'gray') for n in G.nodes()]
                edge_colors = [
                    color_map.get(G.edges[e].get("type"), "black")
                    for e in G.edges()
                ]

                nx.draw_networkx_edges(G, pos, edge_color=edge_colors, min_source_margin=25, min_target_margin=25, connectionstyle="arc3,rad=0.3")
                edge_labels = nx.get_edge_attributes(G, "label")
                nx.draw_networkx_edge_labels(G,pos, edge_labels=edge_labels, rotate=False, alpha=0.8, label_pos=0.5)    #, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))

                if outputValues:
                    node_labels = {
                        n: f"{n}{G.nodes[n].get('value')}"
                        for n in G.nodes()
                    }
                    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
                    nx.draw_networkx_nodes(
                        G, pos,
                        node_color=node_colors,
                        node_size=2000
                    )
                else:
                    nx.draw_networkx_labels(G, pos, font_size=8)
                    nx.draw_networkx_nodes(
                        G, pos,
                        node_color=node_colors,
                        node_size=2000
                    )

                plt.title(F"{self.id}")
                plt.axis('off')
                if show:
                    plt.show()
                if save:
                    # Save it to a file (e.g., PNG, PDF, SVG, etc.)
                    path = F'img/{self.id}.png'
                    Path('img').mkdir(parents=True, exist_ok=True)
                    plt.savefig(path, format="png", dpi=1000, bbox_inches="tight")
            else:
                print(F'   -> cannot drawGrid for: {self.id}, there are no nodes')

    ## Collects a boolean signal if it is set to true, and resets back to false
    class BooleanCollectorReg(Hardware_Module):
        def __init__(self, id: str):
            super().__init__(id)
            self.className = 'BooleanCollectorReg'
            reg = formalHandshake_Hardware.Register(F'{id}_register', self, 'Bool()', 'False')
            self.addInput(F'{id}_in', 'Bool()')
            self.addOutput(F'{id}_out', 'Bool()')

            self.connect(self.multiplex('regIn', 'Bool()', self.getInput(F'{id}_in'), [reg, self.getInput(F'{id}_in')]), reg.input())
            self.connect(reg, self.getOutput(F'{id}_out'))

        def collected(self):
            return self.getOutput(F'{self.id}_out')

    ## Register with a designated boolean input to decide, if new value is loaded or not
    class LoopedReg(Hardware_Module):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, type: str, initialValue: str = None, keywordIn: str = None, keywordOut: str = None, keywordStore: str = None):
            super().__init__(id)
            self.className = F'LoopedReg_{type.replace('(', '').replace(')', '').replace(' ', '').replace(',', '')}'
            self.parent = parent
            parent.addSubModule(self)
            reg = formalHandshake_Hardware.Register('register', self, type, initialValue)
            input = self.addInput('input', type, keywordIn)
            store = self.addInput('store', 'Bool()', keywordStore)
            value = self.addOutput('value', type, keywordOut)

            self.connect(self.multiplex('regIn', type, store, [reg, input]), reg.input())
            self.connect(reg, value)


        def input(self):
            return self.getInput('input')

        def store(self):
            return self.getInput('store')

        def value(self):
            return self.getOutput('value')

    ## A formal construct that assumes a certain boolean trigger leads to a boolean property at the latest or cpecifically after a given number of cycles
    class Fairness(Hardware_Module):
        def __init__(self, id: str, cycles: int = 0, pipelined: bool = False, formal: bool = False, assumeInitial: bool = False, readyImmediately: bool = True):
            super().__init__(id)
            self.className = F'Fairness_{cycles}cycles'
            if formal:
                self.className += '_formal'

            self.start = self.addInput('start', 'Bool()')
            if formal:
                self.finish = self.addInput('finish', 'Bool()')
            else:
                self.finish = self.addOutput('finish', 'Bool()')

            if cycles == 0:
                finish = self.start
            else:
                if not pipelined:
                    if readyImmediately:
                        activeReg = formalHandshake_Hardware.Register('activeReg', self, 'Bool()', 'False')
                        if cycles > 1:
                            activeCycles = formalHandshake_Hardware.Counter('activeCycles', cycles - 1, 0)
                            self.addSubModule(activeCycles)
                            lastCycle = self.equals('lastCycle', activeCycles.value(), self.const(activeCycles.value().getType(), cycles - 1))
                            finish = formalHandshake_Hardware.Register('isFinish', self, 'Bool()', 'False')
                            self.connect(lastCycle, finish.input())
                            isActive = self.isOr('isActive', self.start, self.isAnd('stillAcitve', activeReg, self.isNot('notFinish', finish)))
                            self.connect(isActive, activeReg.input())
                            self.connect(isActive, activeCycles.increment())
                            if formal:
                                if assumeInitial:
                                    self.assumeInitial(F'!activeReg')
                                    self.assumeInitial(F'activeCycles.value === 0')
                                else:
                                    self.assumeInitial(F'(!activeReg && activeCycles.value === 0 || activeReg && activeCycles.value > 0)')
                        else:
                            finish = activeReg
                            isActive = self.isOr('isActive', self.start, self.isAnd('stillAcitve', activeReg, self.isNot('notFinish', finish)))
                            self.connect(isActive, activeReg.input())
                            if formal and assumeInitial:
                                    self.assumeInitial(F'!activeReg')
                    else:
                        raise NotImplementedError()
                else:
                    finish = self.past(self.start, cycles, 'False', assumeInitial)

            if formal:
                self.assumption(F'{self.finish.id} === {finish.id}')
            else:
                self.connect(finish, self.finish)

    ## Liveness Proof, to check if a boolean trigger leads to a boolean property at the latest or cpecifically after a given number of cycles
    class LivenessProof(Hardware_Module):
        def __init__(self, id: str, maxCycles: int, specificCycles: bool = False, pipelined: bool = False, initialReset : bool = True, readyImmediately: bool = True):
            super().__init__(id)
            #self.className = F'{id[0].upper() + id[1:]}'
            str1 = ''
            if specificCycles:
                str1 = '_specificCycles'
            str2 = ''
            if initialReset:
                str2 = '_initialReset'
            str3 = ''
            if pipelined:
                str3 = '_pipelined'
            self.className = F'LivenessProof_{maxCycles}_cycles{str1}{str2}{str3}'

            trigger = self.addInput('trigger', 'Bool()')
            property = self.addInput('property', 'Bool()')
            valid = self.addOutput('valid', 'Bool()')

            if maxCycles == 0:
                self.connect(self.equals('isValid', trigger, property, self.id + '.valid'), valid)
            else:
                if not pipelined:
                    #postTrigger = formalHandshake_Hardware.LoopedReg('postTrigger', self, 'Bool()', 'False', keywordIn = F'{self.id}.trigger', keywordOut = F'postTrigger' , keywordStore = F'{self.id}.trigger')
                    postTrigger = formalHandshake_Hardware.Register('postTrigger', self, 'Bool()', 'False')
                    self.assumeInitial('!postTrigger')
                    if readyImmediately:
                        if maxCycles > 1:
                            postTriggerCycles = self.addSubModule(formalHandshake_Hardware.Counter('postTriggerCycles', maxCycles - 1, 0))
                            self.assumeInitial('postTriggerCycles.value === 0')
                            self.connect(postTriggerCycles.value(), self.addOutput('cycles', postTriggerCycles.value().getType()))
                            lastCycle = self.equals('lastCycle', postTriggerCycles.value(), self.const(postTriggerCycles.value().getType(), maxCycles - 1))
                            maxCyclesReached = formalHandshake_Hardware.Register('maxCyclesReached', self, 'Bool()', 'False')
                            self.connect(lastCycle, maxCyclesReached.input())
                            triggered = self.isOr('triggered', trigger, self.isAnd('stillTriggered', postTrigger, self.isNot('notMaxCyclesReached', maxCyclesReached)))
                            self.connect(triggered, postTrigger.input())
                            self.connect(triggered, postTriggerCycles.increment())
                        else:
                            maxCyclesReached = postTrigger
                            triggered = self.isOr('triggered', trigger, self.isAnd('stillTriggered', postTrigger, self.isNot('notMaxCyclesReached', maxCyclesReached)))
                            self.connect(triggered, postTrigger.input())
                    else:
                        postTriggerCycles = self.addSubModule(formalHandshake_Hardware.Counter('postTriggerCycles', maxCycles, 0))
                        self.assumeInitial('postTriggerCycles.value === 0')
                        self.connect(postTriggerCycles.value(), self.addOutput('cycles', postTriggerCycles.value().getType()))
                        maxCyclesReached = self.equals('lastCycle', postTriggerCycles.value(), self.const(postTriggerCycles.value().getType(), maxCycles))
                        wasTriggered = self.isOr('wasTriggered', trigger, postTrigger)
                        triggered = self.isAnd('triggered', self.isNot('notMaxCyclesReached', maxCyclesReached), wasTriggered)
                        self.connect(triggered, postTrigger.input())
                        self.connect(wasTriggered, postTriggerCycles.increment())

                    if specificCycles:
                        self.whenOtherwise('isValid', maxCyclesReached, property, self.isNot('notProperty', property), self.id + '.valid')
                    else:
                        postProperty = formalHandshake_Hardware.LoopedReg('postProperty', self, 'Bool()', 'False', keywordIn = F'{self.id}.property', keywordOut = F'postProperty' , keywordStore = F'{self.id}.property')
                        propertyWitnessed = self.isOr('propertyWitnessed', property, postProperty.value(), 'propertyWitnessed')
                        self.isOr('isValid', self.isNot('notMaxVal', maxCyclesReached), self.isAnd('propertyAfterMaxCycles', maxCyclesReached, propertyWitnessed), self.id + '.valid')
                        self.assumeInitial('!postProperty.value')

                else:
                    pastRegs: list[formalHandshake_Hardware.Register] = []
                    for c in range(maxCycles):
                        pastReg = formalHandshake_Hardware.Register(F'pastReg_{c}', self, 'Bool()', 'False')
                        pastRegs.append(pastReg)
                        if c > 0:
                            self.connect(pastRegs[c-1], pastReg.input())
                        else:
                            self.connect(trigger, pastReg.input())

                    expectedProperty = pastRegs[-1]
                    if initialReset:
                        self.connect(self.equals('isValid', expectedProperty, property), valid)

                        pipelineFullyWitnessedCycles = (2 * maxCycles - 1)
                        proofCycles = self.addSubModule(formalHandshake_Hardware.Counter('proofCycles', pipelineFullyWitnessedCycles, 0))
                        self.connect(self.true(), proofCycles.increment())
                        self.assumeInitial('proofCycles.value === 0')
                        pipelineFullyWitnessed = self.equals('pipelineFullyWitnessed', proofCycles.value(), self.const(proofCycles.value().getType(), F'{pipelineFullyWitnessedCycles}'))
                        self.cover(pipelineFullyWitnessed)

                    else:
                        witnessedCycles = (maxCycles)
                        proofCycles = self.addSubModule(formalHandshake_Hardware.Counter('proofCycles', witnessedCycles, 0))
                        self.connect(self.true(), proofCycles.increment())
                        self.assumeInitial('proofCycles.value === 0')
                        wasWitnessed = self.equals('pipelineFullyWitnessed', proofCycles.value(), self.const(proofCycles.value().getType(), F'{witnessedCycles}'))
                        self.cover(wasWitnessed)
                        self.connect(self.isOr('isValid', self.isNot('wasNotWitnessd', wasWitnessed), self.isAnd('wintessedCorrect', wasWitnessed, self.equals('correctProperty', expectedProperty, property))), valid)

                    #self.checkIOConnections()
                    #self.sortSequentialSteps()
                    #self.draw_Grid_network()


            self.connectAllKeywords()
            if initialReset:
                self.assumeInitialReset()
                self.assumeInitial('!trigger')

            self.cover(trigger)
            self.cover(property)
            self.cover(valid)
            self.assertion(valid)

        ## returns trigger input
        def trigger(self):
            return self.getInput('trigger')

        ## returns property input
        def property(self):
            return self.getInput('property')

    ## Basic equivalence block, assuming or asserting equivalence of multiple signals of the same hardware type
    class Equivalence(Hardware_Function):
        def __init__(self, id: str, parent: formalHandshake_Hardware.Hardware_Module, inputs: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], formal: bool = True, assume: bool = False, keyword: str = None):
            if len(inputs) < 2:
                raise ValueError(F'Cannot build equivalence block {id} with less than two inputs')
            super().__init__(id, parent, 'Bool()', 0, keyword)
            type = inputs[0].getType()
            self.definition = ''
            for i, input in enumerate(inputs):
                if not input.getType() == type:
                    raise TypeError(F'Cannot build equivalence block {id} with inputs of different types')
                self.connectInput(input)
                if i > 1:
                    self.definition += ' && '
                if i > 0:
                    self.definition += F'({formalHandshake_Hardware.getSpinalHDLSource(self.inputs[0], self.parent)} === {formalHandshake_Hardware.getSpinalHDLSource(self.inputs[i], self.parent)})'
            if formal:
                self.formal()
                self.statement: formalHandshake_Hardware.Harware_Formal_Statement
                if assume:
                    self.statement = parent.assumption(self)
                else:
                    self.statement = parent.assertion(self)
                parent.formalStatements.append(self.statement)

        def on(self, trigger: Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]):
            self.statement.on(trigger)
            self.connectInput(trigger)
            self.definition += F' && {formalHandshake_Hardware.getSpinalHDLSource(trigger, self.parent)}'
            return self

    ## ?
    class Toplevel(Hardware_Module):
        def __init__(self, id: str):
            super().__init__(id)
            self.className = id[0].upper() + id[1:]

    ## ?!
    def loopDataPath(module: formalHandshake_Hardware.Hardware_Module,
                     start: Union[str, formalHandshake_Hardware.Hardware_IOPort],
                     finish: Union[str, formalHandshake_Hardware.Hardware_IOPort],
                     inputs: Union[list[Union[str, formalHandshake_Hardware.Hardware_IOPort]], Union[str, formalHandshake_Hardware.Hardware_IOPort]] = None,
                     outputs: Union[list[Union[str, formalHandshake_Hardware.Hardware_IOPort]], Union[str, formalHandshake_Hardware.Hardware_IOPort]] = None,
                     bypass: bool = True,
                     formal: bool = False,
                     assume: bool = True
                     ):

        s = start
        if isinstance(start, str):
            if not module.getInput(start):
                raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no start signal under the name {start} found.')
            s = module.getInput(start)
        else:
            if not start in module.inputs:
                raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no start signal {start.id} found.')
        if not formalHandshake_Hardware.isBoolean(s):
            raise TypeError(F'Cannot wrapp a looped datapath around module "{module.id}", start signal {s.id} has to be a boolean signal.')

        f = finish
        if isinstance(finish, str):
            if not module.getOutput(finish):
                raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no finish signal under the name {finish} found.')
            f = module.getOutput(finish)
        else:
            if not finish in module.inputs:
                raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no finish signal {finish.id} found.')
        if not formalHandshake_Hardware.isBoolean(f):
            raise TypeError(F'Cannot wrapp a looped datapath around module "{module.id}", finish signal {f.id} has to be a boolean signal.')

        i: list[formalHandshake_Hardware.Hardware_IOPort] = []
        if inputs == None:
            i = inputs
            print(F'!! None!!')
        else:
            if isinstance(inputs, list):
                for element in inputs:
                    if isinstance(element, str):
                        if not module.getInput(element):
                            raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no input under the name {element} found.')
                        else:
                            i.append(module.getInput(element))
                    else:
                        if not element in module.inputs:
                            raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no input under the name {element.id} found.')
                        else:
                            i.append(element)
            else:
                if isinstance(inputs, str):
                    if not module.getInput(inputs):
                        raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no input under the name {inputs} found.')
                    else:
                        i.append(module.getInput(inputs))
                else:
                    if not inputs in module.inputs:
                        raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no input under the name {inputs.id} found.')
                    else:
                        i.append(inputs)

        o: list[formalHandshake_Hardware.Hardware_IOPort] = []
        if outputs == None:
            o = outputs
        else:
            if isinstance(outputs, list):
                for element in outputs:
                    if isinstance(element, str):
                        if not module.getOutput(element):
                            raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no output under the name {element} found.')
                        else:
                            o.append(module.getOutput(element))
                    else:
                        if not element in module.outputs:
                            raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no output under the name {element.id} found.')
                        else:
                            o.append(element)
            else:
                if isinstance(outputs, str):
                    if not module.getOutput(outputs):
                        raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no output under the name {outputs} found.')
                    else:
                        o.append(module.getOutput(outputs))
                else:
                    if not outputs in module.outputs:
                        raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no output under the name {outputs.id} found.')
                    else:
                        o.append(outputs)


        if not len(i) == len(o):
            raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", given lists of in- and outpus have to be of the same length.')

        if not len(i) > 0:
            raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", no inputs/outputs given to be looped.')

        wrapper = formalHandshake_Hardware.Toplevel(module.id + '_loopedDatapath')
        wrapper.addSubModule(module)

        for input in module.inputs:
            if (not input == s) and (not input in i):
                wrapper.connect(wrapper.addInput(input.id, input.getType()), input)
        for output in module.outputs:
            if (not output == f) and (not output in o):
                wrapper.connect(output, wrapper.addOutput(output.id, output.getType()))

        activeDetector = formalHandshake_Hardware.ActiveDetector('activeDetector')
        wrapper.addSubModule(activeDetector)

        wrapperStart = wrapper.addInput(s.id, 'Bool()')
        wrapperFinish = wrapper.addOutput(f.id, 'Bool()')
        wrapper.connect(wrapperStart, s)
        wrapper.connect(wrapperStart, activeDetector.start)
        wrapper.connect(f, wrapperFinish)
        wrapper.connect(f, activeDetector.finish)

        for num, input in enumerate(i):
            output = o[num]
            if not input.getType() == output.getType():
                raise ValueError(F'Cannot wrapp a looped datapath around module "{module.id}", input {input.id} ({input.getType()}) and output {output.id} ({output.getType()}) are not of the same type.')

            wrapperInput = wrapper.addInput(input.id, input.getType())
            wrapperOutput = wrapper.addOutput(output.id, output.getType())
            valReg = formalHandshake_Hardware.Register(F'{output.id.replace('.', '_')}_reg', wrapper, output.getType())
            wrapper.connect(output, valReg.input())
            if not formal:
                wrapper.connect(wrapper.whenOtherwise(F'{input.id.replace('.', '_')}_loopOnActive', activeDetector.active, valReg, wrapperInput), input)
                if bypass:
                    wrapper.connect(wrapper.whenOtherwise(F'{output.id.replace('.', '_')}_bypass', f, output, wrapperInput), wrapperOutput)
                else:
                    wrapper.connect(output, wrapperOutput)
            else:
                wrapper.connect(wrapperInput, input)
                wrapper.connect(output, wrapperOutput)
                inEqualsPastOut = wrapper.equals(F'inEqualsPastOut_{num}', input, valReg)
                inEqualsWrapperIn = wrapper.equals(F'inEqualsWrapperIn_{num}', input, wrapperInput)
                isLooped = wrapper.whenOtherwise(F'isLooped_{num}', activeDetector.active, inEqualsPastOut, inEqualsWrapperIn)
                if assume:
                    wrapper.assumption(isLooped)
                else:
                    wrapper.assertion(isLooped)
                    shouldBypass = wrapper.isNot(F'shouldNotBypass_{num}', wrapper.isOr(F'shouldBypass_{num}', wrapperStart, activeDetector.active))
                    outEqualsIn = wrapper.equals(F'outEqualsIn_{num}', wrapperInput, wrapperOutput)
                    wrapper.assertion(outEqualsIn).on(shouldBypass)
        return wrapper


    ## LivenessProofMakro
    def createLivenessProof(id: str, module: formalHandshake_Hardware.Hardware_Module, trigger: str, property: str, maxCycles: int, specificCycles: bool = False, pipelined: bool = False, initialReset : bool = True):
        proof = formalHandshake_Hardware.Toplevel(id)
        proof.addSubModule(module)
        proof.link(module.inputs)
        #proof.liveness(id + '_Livenessproof1', module.getInput(trigger), module.getOutput(property), maxCycles, specificCycles, initialReset, sequential)
        #proof.liveness2(id + '_Livenessproof2', module.getInput(trigger), module.getOutput(property), maxCycles, specificCycles, pipelined, initialReset)
        proof.liveness(id + '_Livenessproof2', module.get(trigger), module.get(property), maxCycles, specificCycles, pipelined, initialReset)
        return proof

    ## Unfinished
    class EquivalenceProof(Hardware_Module):
        def __init__(self,
                     id: str,
                     inputs1: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     outputs1: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     inputs2: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     outputs2: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     initialReset : bool = True):

            if len(inputs1) == 0 and len(outputs1) == 0:
                raise ValueError(F'Cannot build equivalence proof "{id}" with no inputs or outputs')
            if not len(inputs1) == len(inputs2):
                raise ValueError(F'Cannot build equivalence proof "{id}", because number of inputs dont match')
            if not len(outputs1) == len(outputs2):
                raise ValueError(F'Cannot build equivalence proof "{id}", because number of outputs dont match')

            super().__init__(id)
            self.className = F'{id[0].upper() + id[1:]}_Equivalenceproof'

    ## Adds a formal construct that assumes equivalence of two modules given inputs at the time, each of their respective "start" property was true for the first time.
    # Then the given outputs of both modules are asserted to be equivalent, at the time each respective "finish" propery was set to true.
    # In Other words, this is an asynchroneous Equivalence check, that can be seperatly triggered by each module.
    class EquivalenceProofTriggerd(Hardware_Module):
        def __init__(self,
                     id: str,
                     inputs1: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     inputs2: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     outputs1: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     outputs2: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]],
                     pipelineLength1: int = 0,
                     pipelineLength2: int = 0,
                     initialReset : bool = True
                     ):

            if len(inputs1) == 0 and len(outputs1) == 0:
                raise ValueError(F'Cannot build equivalence proof "{id}" with no inputs or outputs')
            if not len(inputs1) == len(inputs2):
                raise ValueError(F'Cannot build equivalence proof "{id}", because number of inputs dont match')
            if not len(outputs1) == len(outputs2):
                raise ValueError(F'Cannot build equivalence proof "{id}", because number of outputs dont match')

            super().__init__(id)
            ## ?!
            self.className = F'{id[0].upper() + id[1:]}_Equivalenceproof_Triggered'

            self.start1 = self.addInput('start1', 'Bool()')
            self.start2 = self.addInput('start2', 'Bool()')
            self.finish1 = self.addInput('finish1', 'Bool()')
            self.finish2 = self.addInput('finish2', 'Bool()')

            start1Reg = self.collectBoolean(self.start1)
            started1 = self.isOr('started1', self.start1, start1Reg)
            firstStart1 = self.isAnd('firstStart1', self.start1, self.isNot('notStart1Reg', start1Reg))

            start2Reg = self.collectBoolean(self.start2)
            started2 = self.isOr('started2', self.start2, start2Reg)
            firstStart2 = self.isAnd('firstStart2', self.start2, self.isNot('notStart2Reg', start2Reg))

            assumeEqualInputs = self.isAnd('assumeEqualInputs', started1, started2)

            if pipelineLength1 == 0:
                validFinish1 = self.isAnd('validFinish1', started1, self.finish1)
            else:
                validFinish1 = self.past(self.start1, pipelineLength1, 'False')
                self.assertion(self.finish1).on(validFinish1)
            validFinish1Reg = self.collectBoolean(validFinish1)
            finished1 = self.isOr('finished1', validFinish1, validFinish1Reg)
            firstFinish1 = self.isAnd('firstFinish1', validFinish1, self.isNot('notValidFinish1Reg', validFinish1Reg))

            if pipelineLength2 == 0:
                validFinish2 = self.isAnd('validFinish2', started2, self.finish2)
            else:
                validFinish2 = self.past(self.start2, pipelineLength2, 'False')
                self.assertion(self.finish1).on(validFinish1)
            validFinish2Reg = self.collectBoolean(validFinish2)
            finished2 = self.isOr('finished2', validFinish2, validFinish2Reg)
            firstFinish2 = self.isAnd('firstFinish2', validFinish2, self.isNot('notValidFinish2Reg', validFinish2Reg))

            assertEqualOutputs = self.isAnd('assertEqualOutputs', finished1, finished2)

            assumeEqualFunctions = []
            assertEqualFunctions = []

            for i, input1 in enumerate(inputs1):
                input2 = inputs2[i]
                if not input1.getType() == input2.getType():
                    raise ValueError(F'Cannot build equivalence proof "{id}", because inputs "{input1.parent.id}.{input1.id}" ({input1.getType()}) and "{input2.parent.id}.{input2.id}" ({input2.getType()}) types dont match')

                in1 = self.addInput(F'm1_in{i+1}', input1.getType(), input1.getKeyword())
                inReg1 = formalHandshake_Hardware.LoopedReg(F'm1_in{i+1}_Reg', self, input1.getType(), keywordIn= in1.getKeyword(), keywordStore=firstStart1.getKeyword())
                usedValue1 = self.whenOtherwise(F'usedValue1_{i+1}', start1Reg, inReg1.value(), in1)

                in2 = self.addInput(F'm2_in{i+1}', input2.getType(), input2.getKeyword())
                inReg2 = formalHandshake_Hardware.LoopedReg(F'm2_in{i+1}_Reg', self, input2.getType(), keywordIn= in2.getKeyword(), keywordStore=firstStart2.getKeyword())
                usedValue2 = self.whenOtherwise(F'usedValue2_{i+1}', start2Reg, inReg2.value(), in2)

                assumeEqualFunctions.append(self.equals(F'equalInput_{i+1}', usedValue1, usedValue2))

            for o, output1 in enumerate(outputs1):
                output2 = outputs2[o]
                if not output1.getType() == output2.getType():
                    raise ValueError(F'Cannot build equivalence proof "{id}", because outputs "{output1.parent.id}.{output1.id}" ({output1.getType()}) and "{output2.parent.id}.{output2.id}" ({output2.getType()}) types dont match')

                out1 = self.addInput(F'm1_out{o+1}', output1.getType(), output1.getKeyword())
                outReg1 = formalHandshake_Hardware.LoopedReg(F'm1_out{o+1}_Reg', self, output1.getType(), keywordIn= out1.getKeyword(), keywordStore=firstFinish1.getKeyword())
                result1 = self.whenOtherwise(F'result1_{o+1}', validFinish1Reg, outReg1.value(), out1)

                out2 = self.addInput(F'm2_out{o+1}', output2.getType(), output2.getKeyword())
                outReg2 = formalHandshake_Hardware.LoopedReg(F'm2_out{o+1}_Reg', self, output2.getType(), keywordIn= out2.getKeyword(), keywordStore=firstFinish2.getKeyword())
                result2 = self.whenOtherwise(F'result2_{o+1}', validFinish2Reg, outReg2.value(), out2)

                assertEqualFunctions.append(self.equals(F'equalOutput_{o+1}', result1, result2))

            current = None
            for i, equalFunction in enumerate(assumeEqualFunctions):
                if i == 0:
                    current = equalFunction
                else:
                    current = self.isAnd(F'equalInputLink_{i+1}', current, equalFunction)
            validInputs = self.isAnd('validInputs', assumeEqualInputs, current)
            current = None
            for o, equalFunction in enumerate(assertEqualFunctions):
                if o == 0:
                    current = equalFunction
                else:
                    current = self.isAnd(F'equalOutputLink_{o+1}', current, equalFunction)
            checkOutputs = self.isAnd('checkOutputs', validInputs, assertEqualOutputs)
            validResult = self.isOr('validResult', self.isNot('notCheckOutputs', checkOutputs), self.isAnd('validOutputs', checkOutputs, current))
            self.connect(validResult, self.addOutput('valid', 'Bool()'))

            if initialReset:
                self.assumeInitialReset()
            for boolean in assumeEqualFunctions:
                self.assumption(boolean).on(assumeEqualInputs)
            for boolean in assertEqualFunctions:
                self.assertion(boolean).on(assertEqualOutputs)

            #self.formal()
            self.connectAllKeywords()
