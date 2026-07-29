
from __future__ import annotations
from typing import Union

from pathlib import Path
import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import ast

## Dependencies:
# pip install networkx
# pip install matplotlib
# pip install jinja2

## Helperfunction to help with parameterized input/output definitions
def eval_if_pure_numeric(expr: str, replacePower: bool = True) -> str:
    expr = expr.strip()
    if replacePower: 
        expr = expr.replace("^", "**")
    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        # Not even a valid expression → leave as is
        return expr

    # Allowed node types (expressions, constants, operators, unary ops)
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Num,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.UAdd, ast.USub,
    )
    allowed_bin_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    allowed_unary_ops = (ast.UAdd, ast.USub)

    for n in ast.walk(node):
        if isinstance(n, ast.BinOp):
            if not isinstance(n.op, allowed_bin_ops):
                return expr
        elif isinstance(n, ast.UnaryOp):
            if not isinstance(n.op, allowed_unary_ops):
                return expr
        elif not isinstance(n, allowed_nodes):
            # Anything else (Name, Call, etc.) → reject
            return expr

    # Safe-ish eval: no builtins
    try:
        value = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return expr

    # Only accept integer(-like) results
    if isinstance(value, bool):
        return expr
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return expr

## Parameter used by module for parameterized IO-type definitions
class Parameter():
    def __init__(self, id: str, parent: Module, type: str, default: str = None, value: Union[Parameter, str] = None):
        self.id = id
        self.parent = parent
        self.type = type
        self.default = default
        self.value = value

    def setValue(self, value: Union[Parameter, str]):
        if isinstance(value, Parameter):
            if not (value.type == self.type):
                raise TypeError(F'Cannot set value of parameter {self.id} with type {self.type} to parameter {value.id}, because type {value.type} does not match.')
        self.value = value
    
    def getValue(self, reference: bool = False):
        ## geting value or parameter name, for referencing in module/submodule
        if reference:
            if self.value == None:
                raise ValueError(F'No value defined for parameter {self.id}')
            if isinstance(self.value, str):
                return self.value
            else:
                return self.id
        ## Type checking, looking for an actual root value for a parameter
        if self.parent.parent == None:
            return self.id
        if self.value == None:
            if self.default == None:
                print(F'!!! No Value or Default Value for parameter {self.id}')
                print(F'!!! -> module: {self.parent.id}')
                print(F'!!! -> module parameters:')
                for parameter in self.parent.parameters:
                    print(F'!!!     -> {parameter.id}')
                print(F'!!! -> module parent: {self.parent.parent.id}')

                raise ValueError(F'No value or default value defined for parameter {self.id} (Module: {self.parent.id})')
            else:
                return self.default
        else:
            if isinstance(self.value, Union[str, int]):
                return self.value
            else:
                return self.value.getValue()
            
    def getToplevelValueSource(self):
        if isinstance(self.value, Parameter):
            return self.value.getToplevelValueSource()
        else:
            return self.parent
 
    ## textual representation of this Parameter on the terminal
    def display(self, space: int = 0):
        end = ', value: None'
        if not self.value == None:
            end =  F', value: {self.getValue()} ({self.getToplevelValueSource().id})'
        
        print('\t' * space, F'{self.id}, type: {self.type}, default: {self.default}{end}')

## IO ports, used to connect modules or functions
class IOPort:
    def __init__(self, id: str, parent: Union[Function, Module], keyword: str = None):
        # internal variables
        self.id = parent.checkID(id)
        self.parent = parent
        self.keyword = keyword
        self.source = 0  # connected to one IOPort or Function
        self.destinations = []  # all IOPorts connected to this signal
        self.type = 0   # 0 = undefined
        self.firstCell = (0, 0) # used for network operations
        self.marked = False
        self.unmarked = False
        self.taint = False
        self.connected = False 
        self.parameters = []

    ## Placeholder for specific type handling
    def getType(self):
        return self.type

    ## Returns given keyword or else generic keyword 
    def getKeyword(self):
        if self.keyword == None:
            return F'{self.parent.id}.{self.id}'
        else:
            return self.keyword

    ## Disconnect this node from source and all destinations, for example to remove it
    def disconnect(self):
        for destination in self.destinations:
            if isinstance(destination, IOPort):
                destination.source = 0
        if isinstance(self.source, Union[IOPort, Function]):
            if self in self.source.destinations:
                self.source.destinations.remove(self)
        self.source = 0
        self.destinations = []

    ## Unfinished and unused placeholder to prepare for JSON based storing
    def to_dict(self):
        return {
            'id': self.id,
            'module': self.parent.id,   ## ?
            'source': self.source,
            'destinations': list(self.destinations),
            'type': self.type
        }

    ## Unfinished and unused placeholder to prepare for JSON based loading
    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get('id', 0), data.get('parent', 0))
        obj.source = data.get('source', 0)
        obj.destinations = data.get('destinations', [])
        obj.type = data.get('type', 0)
        return obj
    
    ## textual representation of this IOPort on the terminal
    def display(self, space: int = 0):
        print('\t' * space, self.id, F'(keyword: {self.getKeyword()})', end="")
        if isinstance(self.parent, Module) and self.parent.blackbox:
            print(' | due to parent being blackbox, no more details available')
        else: 
            if self.getType() != 0:
                print(' | type:', self.getType(), end="")
            if len(self.parameters) > 0:
                print(' | parameters:', end="")
                for p in self.parameters:
                    print(F' {p.id}', end=F"")
            if self.source != 0:
                print(' | source: ', end="")
                if isinstance(self.source, Function):
                    print(self.source.id, end="")
                if isinstance(self.source, IOPort):  
                    print(F'{self.source.parent.id}.{self.source.id}', end="")

            if len(self.destinations) > 0:
                print(' | destinations: ', end="")
                for num, d in enumerate(self.destinations):
                    if isinstance(d.parent, Module):
                        print(d.parent.id, end="(M).")
                    if isinstance(d.parent, Function):
                        print(d.parent.id, end="(F).")
                    if num < (len(self.destinations) - 1):
                        print(d.id, end=", ")
                    else:
                        print(d.id, end=" ")
        print()

    ## Unfinished and unused placeholder for constant propagation
    def solve(self, toplevel: Module, allowUnknown: bool = False, visited: list[Union[IOPort, Function]] = None, tabs: int = 1):
        ## track unitl toplevel inputs are reached
        if visited == None:
            visited = []
        #visited.append(self)
        if self in toplevel.inputs:
            return '\t' * tabs + F'{self.id}'
        else:
            if not isinstance(self.source, Union[IOPort, Function]):
                return None
            else:
                return self.source.solve(toplevel, allowUnknown, visited, tabs)


## Fixed outputPort defined in dependency of a number of inputs
class Function:
    def __init__(self, id: str, parent: Module, keyword: str = None):
        # internal variables
        self.id = parent.checkID(id)
        self.parent = parent
        self.keyword = keyword
        self.parameters = parent.parameters
        self.inputs = [] # has a list of IOPorts, can also have none -> constant value
        self.destinations = []  # all IOPorts connected to this signal
        self.definition = None 
        self.type = 0   # 0 = undefined
        self.firstCell = (0, 0) # used for network operations
        self.marked = False
        self.unmarked = False
        self.taint = False
        self.connected = True
        self.parameters = []
        # self.properties = []
        parent.addFunction(self)

    ## Placeholder for specific type handling
    def getType(self):
        return self.type

    ## Returns given keyword or else generic keyword 
    def getKeyword(self):
        if self.keyword == None:
            self.keyword = F'{self.parent.id}.{self.id}'
        #else:
        return self.keyword

    ## Checks if given ID is free. If any submodule, function or IO_Port is already using it, it is tried again with an increasing added number until free
    def checkID(self, id:str, num=0):
        returnId = id
        if num > 0:
            returnId = returnId + F'_{num}'
        if not (self.getInput(id) or id == self.id):
            return id
        else:
            newId = self.checkID(returnId, (num + 1))
            print(F'!! Caution, the id "{returnId}" already exists in function "{self.id}" - had to change to {newId} !!')
            return newId

    ## finds an input of a given id or returns False - with info=True, a list of possible inputs is printed on terminal, if no input was found
    def getInput(self, id: str, info=False):
        for input in self.inputs:
            if input.id == id:
                return input
        if info:
            print(F" --- Input not found: {self.id}.{id}")
            if len(self.inputs) > 0:
                print(' -> possible inputs: ', end='')
                for input in self.inputs:
                    print(input.id, end=', ')
                print()
            print('---')
        return False
    
    ## Disconnect this node from all destinations and all sources, for example to remove it 
    def disconnect(self):
        for destination in self.destinations:
            if isinstance(destination, IOPort):
                destination.source = 0
        self.destinations = []
        for input in self.inputs:
            if isinstance(input.source, Union[IOPort, Function]):
                if input in input.source.destinations:
                    input.source.destinations.remove(input)
            input.source = 0

    ## returns a set of all modules and functions (no dublicates), directly connected to this modules inputPorts via their outputPorts
    def getPredecessors(self):
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

    ## search and list all predecessors
    def listAllPredecessors(self, found=None):
        #print(F"looking for predecessors of: {self.id}")
        if found is None:
            found = set()

        predecessors = set()

        for pred in self.getPredecessors():
            if pred not in found:
                found.add(pred)
                predecessors.add(pred)
                predecessors.update(pred.listAllPredecessors(found))
        return predecessors

    ## return all inputs (and inputless functions) of a given topmodule, that this function depends on
    def getInputDependencies(self, topModule: Module, mark = False, assumeDependency=False, visited=None):
        debug = False
        if debug: print(F"Checking function dependencies for {self.id}")

        if visited is None:
            visited = set()
        dependencies = set()

        # Avoid cycles
        if self in visited:
            return dependencies
        visited.add(self)

        ## mark self if desired
        if mark:
            self.marked = True

        if not self.inputs:
            if debug: print(F"-| -> no source")
            dependencies.add(self)
            if len(dependencies) == 0:
                if debug: print(F"(F1)) no dependencies for {self.id} -> is constant value?!")
            return dependencies
        else:
            if debug: print(F"-| | checking inputs")
            for input in self.inputs:
                ## mark inputs if desired
                if mark:
                    input.marked = True

                if debug: print(F"-| | | checking {input.id}")
                source = input.source
                ## input not connected?
                if source != None:
                    if debug: print(F"-| | | | check source of {input.id}")
                    ## if connected to another function, trace inputs further
                    if isinstance(source, Function):
                        if debug: print(F"-| | | | -> is function")
                        dependencies.update(source.getInputDependencies(topModule, mark, assumeDependency, visited))
                    ## if connected to IOPort, can be topmodule input, this functions topmodule input or output of other module
                    elif isinstance(source, IOPort):
                        if debug: print(F"-| | | | -> is IOPort")
                        if source in topModule.inputs:
                            if debug: print(F"-| | | | | topmodule input found")
                            ## mark toplevel input if desired
                            if mark:
                                source.marked = True
                            dependencies.add(source)
                        elif isinstance(source.parent, Module):
                            if debug: print(F"-| | | | | | connected to module")
                            if source in source.parent.outputs:
                                if debug: print(F"-| | | | | | -> connected to submodule output")
                                dependencies.update(source.parent.getInputDependencies(topModule, source, mark, assumeDependency, visited))
                            elif source in source.parent.inputs:
                                if debug: print(F"-| | | | | | -> connected to parent module input")
                                ## mark parent module input if desired
                                if mark:
                                    source.marked = True
                                if source.source != 0:
                                    if debug: print(F"-| | | | | | | source: {source.id} is connected to unconnected parent module input -> Problem?!")
                                    if isinstance(source.source, Function):
                                        if debug: print(F"-| | | | | | | connected to parent that is conneceted to function")
                                        dependencies.update(source.source.getInputDependencies(topModule, mark, assumeDependency, visited))
                                    elif isinstance(source.source.parent, Module):
                                        if debug: print(F"-| | | | | | | connected to connected parent -> reuse module.getInputDependencies?!")
                                        ## ?! using getInputDependencies with input eventhough it is intended to work with output?
                                        dependencies.update(source.source.parent.getInputDependencies(topModule, source.source, mark, assumeDependency, visited))
        
            if len(dependencies) == 0:
                if debug: print(F"(F2)no dependencies for {self.id}")
            return dependencies
    
    ## resets all marks on self, all IOs, submodules and functions
    def resetAllMarks(self):
        self.marked = False
        for input in self.inputs:
            input.marked = False

    ## textual representation of this Function on the terminal
    def display(self, space: int = 0):
        print('\t' * space, self.id, F'(keyword: {self.getKeyword()})', end="")
        if self.parent.blackbox:
            print(' | due to parent being blackbox, no more details available')
        else: 
            if self.type != 0:
                print(' | type:', self.getType(), end="")
            print()
            if len(self.parameters) > 0:
                print(' | parameters:', end="")
                for p in self.parameters:
                    print(F' {p.id}', end=F"")
            if len(self.inputs) > 0:
                print('\t' * (space + 1), 'inputs: ')
                for i in self.inputs:
                    i.display(space + 2)
            if len(self.destinations) > 0:
                print('\t' * (space + 1), 'destinations: ')
                for d in self.destinations:
                    if isinstance(d.parent, Module):
                        print('\t' * (space + 2), d.parent.id, end="(M).")
                    if isinstance(d.parent, Function):
                        print('\t' * (space + 2), d.parent.id, end="(F).")
                    print(d.id)

    ## Unfinished and unused placeholder to prepare for JSON based storing
    def to_dict(self):
        return {
            'id': self.id,
            'module': self.parent.id,   ## ?
            'inputs': list(self.inputs),
            'destinations': list(self.destinations),
            'type': self.type
            ## ?!
        }

    ## Unfinished and unused placeholder to prepare for JSON based loading
    @classmethod
    def from_dict(cls, data):
        obj = cls(data.get('id', 0), data.get('parent', 0))
        obj.source = data.get('inputs', [])
        obj.destinations = data.get('destinations', [])
        obj.type = data.get('type', 0)
        ## ?!
        return obj

    ## Unfinished and unused placeholder for constant propagation
    def solve(self, toplevel: Module, allowUnknown: bool = False, visited: list[Union[IOPort, Function]] = None, tabs: int = 1):
        ## track unitl toplevel inputs are reached
        if visited == None:
            visited = []
        #visited.append(self)

        if allowUnknown:
            string = '\t' * tabs + F'unknown[{self.parent.id}.{self.id}]('
            if len(self.inputs) > 0:
                for input in self.inputs:
                    string += "\n"
                    string += input.solve(toplevel, allowUnknown, visited, tabs + 1)
                string += "\n"
                string += '\t' * tabs + ')'
            else:
                string += ')'
            return string
        else:
            raise NotImplementedError()


## Network of IO-Ports, Functions and Submodules
class Module:
    def __init__(self, id: str):
        # internal variables
        self.id = id
        self.parameters = []
        self.inputs = []    # list of IOPorts
        self.outputs = []       # list of IOPorts
        self.parent = None
        #self.parentID = 0    # 0 = toplevel
        self.firstCell = (0, 0)  # used for network operations
        self.lastCell = (0, 0)   # used for network operations
        self.subModules = []    # list of all submodules
        self.functions = []        # list of all functions
        self.properties = []    # List of LTL properties (SVAs for Hardware)
        self.internalLoopsChecked = False   # Determines, if this module has been checked for any dependency-loops - also False if loops were detected
        self.steps = 0  # used for hirarchical analysis 
        #self.network = []   ## connections as two touples ((parent1.id, source.id), (parent2.id, destination.id))
        self.marked = False
        self.unmarked = False
        self.connected = False
        self.blackbox = False
        self.includes = []
        # self.properties = []

    ## Checks if given ID is free. If any submodule, function or IO_Port is already using it, it is tried again with an increasing added number until free
    def checkID(self, id: str, num: int = 0):
        returnId = id
        if num > 0:
            returnId = returnId + F'_{num}'

        if (not self.get(id) or id == self.id):
            return id
        else:
            newId = self.checkID(returnId, (num + 1))
            print(F'Caution, the id "{returnId}" already exists in module "{self.id}" - had to change to {newId}')
            return newId

    ## Add a parameter used for parameterized IO-type definitions
    def addParameter(self, id: str, type: str, default: str = None, value: str = None):
        for p in self.parameters:
            if p.id == id:
                raise ValueError(F'Parameter with id {id} allready exists')
        param = Parameter(id, self, type, default, value)
        self.parameters.append(param)

    ## Look for a parameter used for parameterized IO-type definitions
    def getParameter(self, id: str):
        for parameter in self.parameters:
            if parameter.id == id:
                return parameter
        return False

    ## Set parameter for parameterized IO-type definitions to use a specific value or the value of another paramter
    def setParameter(self, id: str, value: Union[Parameter, str]):
        if not self.getParameter(id):
            raise ValueError(F'Module {self.id} has no parameter called {id}')
        else:
            self.getParameter(id).setValue(value)

    ## add input from given id and optional type
    def addInput(self, id: str, type = 0):
        input = IOPort(id, self)
        input.type = type
        self.inputs.append(input)
        return input

    ## add output from given id and optional type
    def addOutput(self, id: str, type = 0):
        output = IOPort(id, self)
        output.type = type
        self.outputs.append(output)
        return output
 
    ## finds an input of a given id or returns False - with info=True, a list of possible inputs is printed on terminal, if no input was found
    def getInput(self, id: str, info=False):
        for input in self.inputs:
            if input.id == id:
                return input
        if info:
            print(F" --- input not found: {self.id}.{id}")
            if len(self.inputs) > 0:
                print(' -> possible inputs: ', end='')
                for input in self.inputs:
                    print(input.id, end=', ')
                print()
            print('---')
        return False
    
    ## finds and returns an output of a given id or returns False - with info=True, a list of possible outputs is printed on terminal, if no output was found
    def getOutput(self, id: str, info=False):
        for output in self.outputs:
            if output.id == id:
                return output
        if info:
            print(F" --- output not found: {self.id}.{id}")
            if len(self.outputs) > 0:
                print(' -> possible outputs: ', end='')
                for output in self.outputs:
                    print(output.id, end=', ')
                print()
            print('---')
        return False
    
    ## add subModule
    # -> adds the number of submodules as first Cell koordinate
    def addSubModule(self, module: Module):
        module.id = self.checkID(module.id)
        module.parent = self
        module.firstCell = (len(self.subModules) + len(self.functions) + 1, len(self.subModules) + len(self.functions))
        self.subModules.append(module)
        self.steps += 1
        return module
        
    ## add one ore more subModules
    def addSubModules(self, *modules):
        if len(modules) == 1:
            self.addSubModule(modules[0])
        else:
            for module in modules:
                self.addSubModule(module)
    
    ## finds and returns a subModule of a given id or returns False
    def getSubModule(self, id: str):
        for module in self.subModules:
            if module.id == id:
                return module
        return False
    
    ## add function -> adds the number of submodules plus the number of functions as first Cell koordinate
    def addFunction(self, function: Function):
        if self.getFunction(function.id):
            if self.getFunction(function.id) == function:
                print(F'Function {function.id} was allready added to module {self.id}')
            else:
                raise ValueError(F"Module {self.id} already has a different function under the name of {function.id}")
        else:
            function.firstCell = (len(self.subModules) + len(self.functions) + 1, len(self.subModules) + len(self.functions))
            self.functions.append(function)
            self.steps += 1

    ## finds and returns a function of a given id or returns False - with info=True, a list of possible functions is printed on terminal, if no function was found
    def getFunction(self, id: str, info=False):
        for function in self.functions:
            if function.id == id:
                return function
        if info:
            print(F" --- function not found: {self.id}.{id}")
            if len(self.functions) > 0:
                print(' -> possible functions: ', end='')
                for function in self.function:
                    print(function.id, end=', ')
                print()
            print('---')
        return False
        
    ## search for given input/output/submodule/function and return, if possible - otherwise return False
    def get(self, id: str):
        for module in self.subModules:
            if module.id == id:
                return module
        for function in self.functions:
            if function.id == id:
                return function
        for input in self.inputs:
            if input.id == id:
                return input
        for output in self.outputs:
            if output.id == id:
                return output
        return False

    ## connects two signals if types match and adds connection to list of connections
    def connect(self, source: Union[IOPort, Function], destination: IOPort):
        if (source.type == destination.type):
            destination.source = source
            source.destinations.append(destination)
            #self.network.append(((source.parent.id, source.id), (destination.parent.id, destination.id)))
        else:
            raise TypeError(F'Source and destination types dont match({source.type} - {destination.type})')

    ## Disconnect this node from all destinations and all sources, for example to remove it 
    def disconnect(self):
        for input in self.inputs:
            if isinstance(input.source, Union[IOPort, Function]):
                if input in input.source.destinations:
                    input.source.destinations.remove(input)
            input.source = 0

        for output in self.outputs:
            for destination in output.destinations:
                if isinstance(destination, IOPort):
                    if destination.source == output:
                        destination.source = 0
            output.destinations = []

    ## Remove this Node from graph network
    def remove(self, object: Union[IOPort, Function, Module]):
        if isinstance(object, IOPort):
            if not (object in self.inputs or object in self.outputs):
                raise ValueError(F'{self.id} cannot remove io {object.id}, is not part of Module')
            if object in self.inputs:
                self.inputs.remove(object)
            else:
                self.outputs.remove(object)

        
        if isinstance(object, Function):
            if not object in self.functions:
                raise ValueError(F'{self.id} cannot remove function {object.id}, is not part of Module')
            self.functions.remove(object)
            
        if isinstance(object, Module):
            if not object in self.subModules:
                raise ValueError(F'{self.id} cannot remove module {object.id}, is not part of Module')
            self.subModules.remove(object)
        
        object.disconnect()
    
        return object

    ## connects all ios and submodules/function ios, that correspond to the same keyword
    def connectAllKeywords(self):
        possibleSources = []
        for input in self.inputs:
            possibleSources.append(input)
        for function in self.functions:
            possibleSources.append(function)
        for submodule in self.subModules:
            for output in submodule.outputs:
                possibleSources.append(output)

        destinations = []
        for output in self.outputs:
            destinations.append(output)
        for function in self.functions:
            for input in function.inputs:
                destinations.append(input)
        for submodule in self.subModules:
            for input in submodule.inputs:
                destinations.append(input)

        sources = {}
        for possibleSource in possibleSources:
            keyword = possibleSource.getKeyword()
            #print(F'possibleSource: {possibleSource.id}, keyword: {possibleSource.keyword}, getKeyword(): {possibleSource.getKeyword()}')
            if keyword in sources:
                raise ValueError(F'Module {self.id}: source {possibleSource.parent.id}.{possibleSource.id} uses same keyword "{keyword}" as source {sources[keyword].parent.id}.{sources[keyword].id}')
            else:
                #print(F"Source {possibleSource.id} not found -> adding to sources")
                sources[keyword] = possibleSource

        #print(F'Module {self.id}: trying to match keywords:')
        for destination in destinations:
            destinationKey = destination.getKeyword()
            #print(F'    Destination Key is: {destinationKey}')
            for sourceKey in sources.keys():
                #print(F'    -> Comparing with: {sourceKey}')
                if sourceKey == destinationKey:
                    #print(F'       -> Match with keyword "{sourceKey}", source: {sources[sourceKey].parent.id}.{sources[sourceKey].id}, destination: {destination.parent.id}.{destination.id}')
                    self.connect(sources[sourceKey], destination)

    ## Add function with given function_id and definition, add given inputs to it and connect to corresponding sources, as well as given destination (adds same types corresponding to sources and destination)
    def defineDestinationFromSources(self, function: Function, destination: IOPort, definition, sources: list = None):
        if sources is None:
            sources = []
        else:
            ## first check if valid
            for source in sources:
                if not (isinstance(source, IOPort) or isinstance(source, Function)):
                    raise TypeError(F"No valid source for defining {function.id}")
                
        function.type = destination.type
        function.definition = definition
        self.connect(function, destination)
        self.addFunction(function)
        for source in sources:
            input = IOPort(source.id, function)
            input.type = source.type
            function.inputs.append(input)
            self.connect(source, input)

    ## returns a set of all modules and functions (no dublicates), directly connected to this modules inputPorts
    def getPredecessors(self):
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

    ## search all predecessors
    def listAllPredecessors(self, found=None):
        #print(F"looking for predecessors of: {self.id}")
        if found is None:
            found = set()

        predecessors = set()

        for pred in self.getPredecessors():
            if pred not in found:
                found.add(pred)
                predecessors.add(pred)
                predecessors.update(pred.listAllPredecessors(found))
        return predecessors

    ## check if any submodules are connected in a loop to them self
    def detectLoops(self):
        print(' --- check for loops in:', self.id)
        for element in self.subModules + self.functions:
            if element in element.listAllPredecessors():
                print(F"    -> Loop detected for {element.id}")
                self.internalLoopsChecked = False
                return False
            
        #print(F"No loop detected in {self.id}")
        self.internalLoopsChecked = True
        return True

    ## return all inputs (and inputless functions) of a given topmodule, that a given output of the topmodule depends on
    def getInputDependencies(self, topModule: Module, output: IOPort, mark=False, assumeDependency=False, visited=None):
        if visited is None:
            if not topModule.getOutput(output.id):
                raise ValueError(F'Output {output.id} is no valid output of topodule {topModule.id}')
            visited = set()
        dependencies = set()

        #print(F"| getting inputDependencies for {self.id}.{output.id}")

        ## Avoid cycles
        if output in visited:
            #print(F"| -> dependencies for {self.id}.{output.id} -> already visited")
            #if len(dependencies) == 0:
            #    print(F"(M1) no dependencies for {self.id}.{output.id}")
            return dependencies
        visited.add(output)
        ## mark if desired
        if mark:
            output.marked = True
            self.marked = True
        source = output.source

        ## check if given output is actually a parentmodules input and if this parent module is the toplevel
        #print(F"| |")
        if output in topModule.inputs:
            #print(F"| | -> output is actually toplevel input")
            dependencies.add(output)
            return dependencies

        ## if source is not defined, no dependecies are returned. Alternatively it could be assumed, that in this case the output depends on all inputs of the same module # ?!
        #print(F"| | |")
        if source == None:
            #print(F"| | | -> no source!")
            if assumeDependency:
                #print(F"should assume connection to all submodules inputs? -> not implemented yet")
                #if len(dependencies) == 0:
                #    print(F"(M2) no dependencies for {self.id}.{output.id}")
                return dependencies
            else:
                #if len(dependencies) == 0:
                #    print(F"(M3) no dependencies for {self.id}.{output.id}")
                return dependencies

        ## If the source is a top-level input, we're done
        #print(F"| | | |")
        if source in topModule.inputs:
            #print(F"| | | | -> found toplevel input!")
            ## mark if desired
            if mark:
                source.marked = True
            dependencies.add(source)
            #if len(dependencies) == 0:
            #    print(F"(M4) no dependencies for {self.id}.{output.id}")
            return dependencies
        
        ## if output is directly connected to function, the functions inputs have to be traced
        #print(F"| | | | |")
        if isinstance(source, Function):
            #print(F"| | | | | -> connected to function!")
            dependencies.update(source.getInputDependencies(topModule, mark, assumeDependency, visited))
        
        ## If source is IOPort, it could the output of a submodule or there is a direct connection to a input of the current module
        #print(F"| | | | | |")
        if isinstance(source, IOPort):
            if isinstance(source.parent, Module):
                ## connected to output submodule?
                if source in source.parent.outputs:
                    #print(F"| | | | | | -> connected to submodule!")
                    dependencies.update(source.parent.getInputDependencies(topModule, source, mark, assumeDependency, visited))
                    #if len(dependencies) == 0:
                    #    print(F"(M5) no dependencies for {self.id}.{output.id}")
                    return dependencies
                ## connected to input of current module? # ?! or input of parentmodule?!
                elif source in source.parent.inputs: # and source.parent == output.parent: 
                    #print(F"| | | | | | -> connected to parent module input -> reuse parentmodules getinputDependencies?!")
                    dependencies.update(source.parent.getInputDependencies(topModule, source, mark, assumeDependency, visited))
                    #if len(dependencies) == 0:
                    #    print(F"(M6) no dependencies for {self.id}.{output.id}")
                    return dependencies
                    ## ?! using getInputDependencies with input eventhough it is intended to work with output?
                    ## What is source of this input? -> none, func, input or output?
        #if len(dependencies) == 0:
        #    print(F"(M7) no dependencies for {self.id}.{output.id}")
        return dependencies
    
    ## check if all inputs are connected to any output and all outputs are connected to at least one input -> set connected flag accordingly
    def checkIOConnections(self, all=True, checkType=False, noEmptyConnections=False, toplevel=True):
        if toplevel:
            if all:
                print(' --- checking IO connections for:', self.id, 'and all its submodules')
            else:
                print(' --- checking IO connections for:', self.id)


        inputsFound = set()
        connected = True

        if all:
            for module in self.subModules:
                if not module.checkIOConnections(True, checkType, noEmptyConnections, toplevel = False):
                    connected = False

        for output in self.outputs:
            #print(F" ___________________________________________ checking IO connections for: {self.id}.{output.id}")
            dependencies = self.getInputDependencies(self, output)
            if len(dependencies) > 0:
                output.connected = True
                inputsFound.update(dependencies)
            else:
                #print(F"----------------- -> No dependencies {self.id}.{output.id}:")
                #if isinstance(output.source, Function):
                #    output.connected = True
                #    #print('function found:', output.source.id, input.id)
                #    #for input in output.source.sources:
                #    #    print('function input:', output.source.id, input.id)
                #    #    inputsFound.add(input)
                #else:
                connected = False
            #print(F" ------------------------------------------- checking IO connections for: {self.id}.{output.id}")
        #print(F"--------------------- Checking Inputs for {self.id}:")
        #print('__ inputs found:')
        #for i in inputsFound:
        #    print(i)
        #print('__')
        for input in self.inputs:
            #print('---------------------  -> Checking:', input.id)
            if input in inputsFound:
                #print('---------------------  -> found!')
                input.connected = True
            else:
                connected = False
                #print('---------------------  -> non found')
        
        self.connected = connected
        #if connected:
        #    print(print('---------------------', self.id, 'is connected!'))
        #else:
        #    print(print('---------------------', self.id, 'is not connected!'))
        return connected
    
    ## sort modules into sequential steps based on dependencies -> only works, without loops
    def sortSequentialSteps(self):
        print(' --- sort sequential steps for:', self.id)
        if not self.internalLoopsChecked:
            if not self.detectLoops():
                print('  -> cannot sort, because of internal loop')
                return False
        
        if (len(self.subModules) > 0) or (len(self.functions) > 0):
            self.steps = 0
            toSort = []
            
            visited = []
            visited.append(self)

            for element in self.subModules + self.functions:
                toSort.append(element)
            while len(toSort) > 0:
                self.steps += 1
                sorted = []
                num = len(toSort)
                for element in toSort:
                    found = 0
                    predecessors = element.getPredecessors()
                    for predecessor in predecessors:
                        if predecessor in visited:
                            found += 1
                    if found == len(predecessors):
                        element.firstCell = (self.steps, len(sorted))
                        sorted.append(element)
                            
                for element in sorted:
                    toSort.remove(element)
                    visited.append(element)
                if len(toSort) == num:
                    print('none Found - Error: Either Loop or false connections?! (sort all unsorted elements?)')
                    break

    ## Checking for invalid edges between multiple output ports
    def checkForOutputToOutputConnections(self, raiseError: bool = False, rewire: bool = True):
        for output in self.outputs:
            for output2 in self.outputs:
                if output.source == output2:
                    if raiseError:
                        raise ValueError(F'Output "{self.id}.{output.id}" is connected to modules own output "{self.id}.{output2.id}"')
                    else:
                        print(F'!! Warning: Output "{self.id}.{output.id}" is connected to modules own output "{self.id}.{output2.id}"')
                        if not output2.source == 0:
                            if rewire:
                                validRewire = False
                                if isinstance(output2.source, IOPort):
                                    if output2.source in self.inputs:
                                        validRewire = True
                                    else:
                                        if output2.source.parent.parent == self and output2.source in output2.source.parent.outputs:
                                            validRewire = True
                                else:
                                    if output2.source.parent == self:
                                        validRewire = True
                                if validRewire:
                                    output.source.destinations.remove(output)
                                    self.connect(output2.source, output)
                                else:
                                    raise ValueError(F'Output "{self.id}.{output.id}" is connected to modules own output "{self.id}.{output2.id}" and cannot be connected to its source')
                            else:
                                print(F'    -> source of own output would be "{output2.source.parent.id}.{output2.source.id}"')

    ## display a layered textual view of whole module tree            
    def display(self, space: int = 0, detailed: bool = True):
        print('\t' * space, '--- Display Module: ', self.id)
        if len(self.subModules) > 0:
            print('\t' * (space + 1), 'number of submodules: ', len(self.subModules))
        if len(self.functions) > 0:
            print('\t' * (space + 1), 'number of functions: ', len(self.functions))
        if self.steps > 0:
            print('\t' * (space + 1), 'number of steps: ', self.steps)
        if space > 0 and self.parent != None:
            print('\t' * (space + 1), 'ParentID:', self.parent.id)
            if self.firstCell != (0,0):
                print('\t' * (space + 1), 'Cells: ', self.firstCell, end='')
                if self.lastCell != (0,0):
                    print('-', self.lastCell)
                else:
                    print()
        if len(self.parameters) > 0:
            print('\t' * space, F"   - parameters of {self.id}:")
            for parameter in self.parameters:
                parameter.display(space+1)
        if len(self.inputs) > 0:
            print('\t' * space, F"   - inputs of {self.id}:")
            for input in self.inputs:
                input.display(space + 1)
        if len(self.outputs) > 0:
            print('\t' * space, F"   - outputs of {self.id}:")
            for output in self.outputs:
                output.display(space + 1)
        if len(self.subModules) > 0:
            print('\t' * space, F"   - submodules of {self.id}:")
            for module in self.subModules:
                if detailed:
                    module.display(space + 1)
                else:
                    print('\t' * (space + 1), F"   {module.id}:")
        if len(self.functions) > 0:
            print('\t' * space, F"   - functions of {self.id}:")
            for function in self.functions:
                if detailed:
                    function.display(space + 1)
                else:
                    print('\t' * (space + 1), F"   {function.id}:")
    
    ## print network connections
    def printNetwork(self, space: int = 0):
        print('\t' * space, '--- Display Network for: ', self.id)
        for connection in self.network:
            #print('\t' * (space + 1), connection[0], '->', connection[1])
            print('\t' * (space + 1),F"{connection[0][0]}.{connection[0][1]} -> {connection[1][0]}.{connection[1][1]}")

    ## resets all marks on self, all IOs, submodules and functions
    def resetAllMarks(self):
        self.marked = False
        for input in self.inputs:
            input.marked = False
        for output in self.outputs:
            output.marked = False
        for module in self.subModules:
            module.resetAllMarks()
        for function in self.functions:
            function.resetAllMarks()

    ## draw current network on sorted grid
    def draw_Grid_network(self, show: bool = True, save: Union[bool, str] = False):
        print(' --- drawGrid for:', self.id)
        G = nx.DiGraph()

        numNodes = 0

        # Add nodes with types
        for inp in self.inputs:
            numNodes += 1
            t = 'Input'
            if inp.unmarked:
                t = 'Unmarked'
            if inp.marked:
                t = 'Marked'
            G.add_node(inp.id, type=t)
            #print('node: ', inp.id)

        for out in self.outputs:
            numNodes += 1
            t = 'Output'
            if out.unmarked:
                t = 'Unmarked'
            if out.marked:
                t = 'Marked'
            G.add_node(out.id, type=t)
            #print('node: ', out.id)

        for module in self.subModules:
            numNodes += 1
            t = 'Module'
            if module.blackbox:
                t = 'Blackbox'
            if module.unmarked:
                t = 'Unmarked'
            if module.marked:
                t = 'Marked'
            G.add_node(module.id, type=t)
            #print('node: ', module.id)

        for function in self.functions:
            numNodes += 1
            t = 'Function'
            if function.unmarked:
                t = 'Unmarked'
            if function.marked:
                t = 'Marked'
            G.add_node(function.id, type=t)
            #print('node: ', function.id)

        if numNodes > 0:

            ## Add edges from inputs to outputs/functions
            #for connection in self.network:
            #    #print('edge: ', F"{connection[0][0]}.{connection[0][1]} -> {connection[1][0]}.{connection[1][1]}")
            #    id1 = connection[0][0]
            #    if id1 == self.id:
            #        id1 = connection[0][1]
            #    id2 = connection[1][0]
            #    if id2 == self.id:
            #        id2 = connection[1][1]
            #    G.add_edge(id1, id2)

            for input in self.inputs:
                for destination in input.destinations:
                    if destination.parent == self:
                        G.add_edge(input.id, destination.id)
                    else:
                        if destination.parent.parent == self:
                            G.add_edge(input.id, destination.parent.id)
            for function in self.functions:
                for destination in function.destinations:
                    if destination.parent == self:
                        G.add_edge(function.id, destination.id)
                    else:
                        if destination.parent.parent == self:
                            G.add_edge(function.id, destination.parent.id)
            for module in self.subModules:
                for output in module.outputs:
                    for destination in output.destinations:
                        if destination.parent == self:
                            G.add_edge(module.id, destination.id)
                        else:
                            if destination.parent.parent == self:
                                G.add_edge(module.id, destination.parent.id)
 
            pos = {}

            def scale_position(cell, scale=100):
                # Converts grid cell (row, col) to plot coordinates
                return (cell[1] * scale, -cell[0] * scale)  # X = col, Y = -row (invert Y for top-down)

            # --- Position nodes based on firstCell (grid coordinates) ---
            for i, inp in enumerate(self.inputs):
                pos[inp.id] = scale_position((0, i))    # ?!
            for o, out in enumerate(self.outputs):
                pos[out.id] = scale_position(((self.steps + 1), o))  # ?!
            for mod in self.subModules:
                pos[mod.id] = scale_position(mod.firstCell)
            for func in self.functions:
                pos[func.id] = scale_position(func.firstCell)

            # --- Coloring nodes based on type ---
            color_map = {
                'Input': 'skyblue',
                'Output': 'orange',
                'Module': 'lightgreen',
                'Function': 'green',
                'Marked': 'red',
                'Unmarked': 'mistyrose',
                'Backbox': 'dimgrey'
            }
            #node_colors = [color_map.get(G.nodes[n].get('type'), 'gray') for n in G.nodes()]

            # Create the plot manually
            fig, ax = plt.subplots()

            # Draw edges
            #nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray')
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray')    #, connectionstyle="arc3,rad=-0.15")    #, min_source_margin=20, min_target_margin=40, connectionstyle="arc3,rad=-0.15")

            # Draw labels
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=12)

            # Custom node drawing: half color based on 'defined'
            for node in G.nodes():
                x, y = pos[node]
                base_color = color_map.get(G.nodes[node].get('type'), 'gray')
                is_defined = getattr(self.get(node), 'connected', False)  # ?!

                # If defined, base_color + gray; else gray + base_color
                if is_defined:
                    wedge1 = mpatches.Wedge((x, y), 20, 0, 360, facecolor=base_color)
                    wedge2 = mpatches.Wedge((x, y), 20, 0, 0, facecolor=base_color)
                else:
                    wedge1 = mpatches.Wedge((x, y), 20, 275, 85, facecolor=base_color)
                    wedge2 = mpatches.Wedge((x, y), 20, 95, 265, facecolor=base_color)

                ax.add_patch(wedge1)
                ax.add_patch(wedge2)

            # --- Automatically set axis limits to include all nodes
            x_vals, y_vals = zip(*pos.values())
            margin = 50  # Add padding around nodes

            ax.set_xlim(min(x_vals) - margin, max(x_vals) + margin)
            ax.set_ylim(min(y_vals) - margin, max(y_vals) + margin)


            plt.title(F"{self.id}")

            plt.axis('off')


            if not save == False:  
                # Save it to a file (e.g., PNG, PDF, SVG, etc.)
                if isinstance(save, str):
                    path = F'img/{save}.png'
                else:
                    path = F'img/{self.id}.png'
                Path('img').mkdir(parents=True, exist_ok=True)
                plt.savefig(path, format="png", dpi=1000, bbox_inches="tight")

            if show:
                plt.show()
        else:
            print(F'   -> cannot drawGrid for: {self.id}, there are no nodes')

    ## Unfinished and unused placeholder to prepare for JSON based loading
    @classmethod
    def from_json(cls, filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: File '{filename}' is not valid JSON.")
            return None

        # Create a new instance
        obj = cls(data.get("id", 0))

        # Basic fields
        ##obj.id = data.get("id", 0)
        ### etc.

        return obj
    
    ## Unfinished and unused placeholder to prepare for JSON based storing
    def save_to_json(self, filename):
        def serialize(obj):
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            else:
                return obj  # fall back for int, str, etc.

        data = {
            "id": self.id
            ## etc.
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)


    ## Automatically remove all marked nodes from network
    def pruneUnmarked(self, display: bool = False):
        pruned = []
        for element in self.outputs + self.functions + self.inputs + self.subModules:
            if not element.marked:
                pruned.append(element)
                if display:
                    print(F'    -> Pruning "{element.parent.id}.{element.id}"')
                self.remove(element)
        return pruned
    
    ## Automatically mark, and then remove all nodes from a network, that no output is depending on
    def pruneUnused(self, display: bool = False, mark = True):
        if mark:
            for output in self.outputs:
                self.getInputDependencies(self, output, True)
        pruned = self.pruneUnmarked(display)
        for module in self.subModules:
            pruned += module.pruneUnused(display, False)
        self.resetAllMarks()
        return pruned

