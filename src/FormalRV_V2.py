
from FileManager import FormalHandshakeHardwareProject
from formalHandshake_Hardware import formalHandshake_Hardware
from typing import List, Dict, Any, Union


## Basic definition of a single RISC-V instruction
# If value is None, the respective asset, source or control signal is not used
class InstructionDefinition():
    def __init__(self, id: str, custom: bool = False, f3: str = None, f7: str = None, f12: str = None,  ## ID and decoding values
                 immType: str = None, ## immediate type encoding
                 pcCalcAsset: str = None, ## usually addu (add unsigned)
                 pcCalcSource1: str = None, ## for example pc or rs1_data
                 pcCalcSource2: str = None, ## usually imm
                 branchAsset: str = None, ## for example equals or ltu (larger than unsigned)
                 branchSource1: str = None, ## usually rs1_data
                 branchSource2: str = None, ## usually rs2_data
                 checkMisalignedPc: int = None,  ## can only be 2 or 4
                 aluAsset: str = None,  ## Alu operation addu
                 aluSource1: str = None, ## usually rs1_data or pc
                 aluSource2: str = None, ## usually imm or rs2_data
                 memAddressCalcAsset: str = None, ## usually addu
                 memAddressCalcSource1: str = None, ## usually rs1_data
                 memAddressCalcSource2: str = None, ## usually imm
                 memSize: int = None, ## can be 1, 2, 4
                 memWrite: bool = None, ## if false: read
                 memWriteSource: str = None, ## usually rs2_data
                 memReadFormat: str = None, ## lw (load word) lh, lh (load half word), lhu (load half word unsigned), lb (load byte), lbu (load byte unsigned)
                 checkMisalignedMem: int = None, ## can only be 2 or 4
                 rdSource: str = None  ## usually alu, imm, pcInc (pc + 4), mem
                 ):
        
        self.id = id
        self.custom = custom
        ## stor given parameters in a set
        self.parameters = {'f3': f3,
                           'f7': f7,
                           'f12': f12,
                           'immType': immType,
                           'pcCalcAsset': pcCalcAsset,
                           'pcCalcSource1': pcCalcSource1,
                           'pcCalcSource2': pcCalcSource2, 
                           'branchAsset': branchAsset,
                           'branchSource1': branchSource1,
                           'branchSource2': branchSource2,
                           'checkMisalignedPc': checkMisalignedPc,
                           'aluAsset': aluAsset,
                           'aluSource1': aluSource1,
                           'aluSource2': aluSource2,
                           'memAddressCalcAsset': memAddressCalcAsset,
                           'memAddressCalcSource1': memAddressCalcSource1,
                           'memAddressCalcSource2': memAddressCalcSource2,
                           'memSize': memSize,
                           'memWrite': memWrite,
                           'memWriteSource': memWriteSource,
                           'memReadFormat': memReadFormat,
                           'checkMisalignedMem': checkMisalignedMem,
                           'rdSource': rdSource,
                           'valid': True,
                           }
        
    ## prints textual representation of instruction descriptione
    def display(self, details: bool = False):
        if self.parameters['immType'] == 'S':
            print('|   imm[4:0]   ', end = '')
        elif self.parameters['immType'] == 'B':
            print('| imm[4:1][11] ', end = '')
        else:
            print('|     rd       ', end = '')

        if not self.parameters['f3'] == None:
            print(F'| {self.parameters['f3']} ', end = '')

        sources = []
        if not self.parameters['pcCalcSource1'] == None:
            sources.append(self.parameters['pcCalcSource1'])
        if not self.parameters['pcCalcSource2'] == None:
            sources.append(self.parameters['pcCalcSource2'])
        if not self.parameters['branchSource1'] == None:
            sources.append(self.parameters['branchSource1'])
        if not self.parameters['branchSource2'] == None:
            sources.append(self.parameters['branchSource2'])
        if not self.parameters['aluSource1'] == None:
            sources.append(self.parameters['aluSource1'])
        if not self.parameters['aluSource2'] == None:
            sources.append(self.parameters['aluSource2'])
        if not self.parameters['memAddressCalcSource1'] == None:
            sources.append(self.parameters['memAddressCalcSource1'])
        if not self.parameters['memAddressCalcSource2'] == None:
            sources.append(self.parameters['memAddressCalcSource2'])
        if not self.parameters['memWriteSource'] == None:
            sources.append(self.parameters['memWriteSource'])
        if not self.parameters['rdSource'] == None:
            sources.append(self.parameters['rdSource'])
        
        

        if 'rs1_data' in sources:
            print('| rs1 ', end = '')

        if 'rs2_data' in sources:
            print('|  rs2  ', end = '')

        if self.parameters['immType'] == 'shamt':
            print('| shamt ', end = '')

        if not self.parameters['f7'] == None:
            print(F'|    {self.parameters['f7']}    ', end = '')

        if self.parameters['immType'] == 'I':
            print('|       imm[11:0]       ', end = '')
            
        if self.parameters['immType'] == 'S':
            print('|   imm[11:5]   ', end = '')
            
        if self.parameters['immType'] == 'B':
            print('| imm[12][10:5] ', end = '')

        if self.parameters['immType'] == 'U':
            print('|            imm[31:12]             ', end = '')
            
        if self.parameters['immType'] == 'J':
            print('|      imm[20][10:1][11][19:12]     ', end = '')

        print(F'|       {self.id}', end = '')
        if details:
            print(F':  ', end = '')
            imm = ''
            if not self.parameters['immType'] == None: 
                imm = F'{self.parameters['immType']}-imm'
            
            if not self.parameters['pcCalcAsset'] == None:
                source1 = '' 
                if not self.parameters['pcCalcSource1'] == None:
                    source1 = self.parameters['pcCalcSource1'] 
                    if source1 == 'imm':
                        source1 = imm
                source2 = '' 
                if not self.parameters['pcCalcSource2'] == None:
                    source2 = self.parameters['pcCalcSource2'] 
                    if source2 == 'imm':
                        source2 = imm
                pc = F'jump: {self.parameters['pcCalcAsset']}({source1}, {source2})'
                print(F' -> {pc}', end = '')
                if not self.parameters['checkMisalignedPc'] == None:
                    print(F' if address % {self.parameters['checkMisalignedPc']}', end = '')
                    if not self.parameters['branchAsset'] == None:
                        print(F' and', end = '')
                
                if not self.parameters['branchAsset'] == None:
                    source1 = '' 
                    if not self.parameters['branchSource1'] == None:
                        source1 = self.parameters['branchSource1'] 
                        if source1 == 'imm':
                            source1 = imm
                    source2 = '' 
                    if not self.parameters['branchSource2'] == None:
                        source2 = self.parameters['branchSource2'] 
                        if source2 == 'imm':
                            source2 = imm
                    branch = F'{self.parameters['branchAsset']}({source1}, {source2})'
                    print(F' if {branch}', end = '')

            if not self.parameters['aluAsset'] == None:
                source1 = '' 
                if not self.parameters['aluSource1'] == None:
                    source1 = self.parameters['aluSource1'] 
                    if source1 == 'imm':
                        source1 = imm
                source2 = '' 
                if not self.parameters['aluSource2'] == None:
                    source2 = self.parameters['aluSource2'] 
                    if source2 == 'imm':
                        source2 = imm
                alu = F'ALU: {self.parameters['aluAsset']}({source1}, {source2})'
                print(F' -> {alu}', end = '')
            
            if not self.parameters['rdSource'] == None:
                if self.parameters['rdSource'] == 'imm':
                    print(F' -> rd = {imm}', end = '')
                else:
                    print(F' -> rd = {self.parameters['rdSource']}', end = '')
            
            if not self.parameters['memAddressCalcAsset'] == None:
                source1 = '' 
                if not self.parameters['memAddressCalcSource1'] == None:
                    source1 = self.parameters['memAddressCalcSource1'] 
                    if source1 == 'imm':
                        source1 = imm
                source2 = '' 
                if not self.parameters['memAddressCalcSource2'] == None:
                    source2 = self.parameters['memAddressCalcSource2'] 
                    if source2 == 'imm':
                        source2 = imm
                readFormat = ''
                if not self.parameters['memReadFormat'] == None:
                    readFormat = F' as {self.parameters['memReadFormat']}'
                operation = F'read from memory address {self.parameters['memAddressCalcAsset']}({source1}, {source2}){readFormat}'
                if self.parameters['memWrite']:
                    operation = F'write {self.parameters['memWriteSource']} to memory address {self.parameters['memAddressCalcAsset']}{sources}'
                print(F' -> {operation}', end = '')

            print()
        else:
            print()

## Basic definition of a RISC-V instruction family with a specific opcode
# Parameters given here are defined for all contained instructions
class OpcodeFamily():
    def __init__(self, id: str, opcode: str, f3: str = None, f7: str = None, f12: str = None,  ## ID and decoding values
                 immType: str = None, ## immediate type encoding
                 pcCalcAsset: str = None, ## usually addu (add unsigned)
                 pcCalcSource1: str = None, ## for example pc or rs1_data
                 pcCalcSource2: str = None, ## usually imm
                 branchAsset: str = None, ## for example equals or ltu (larger than unsigned)
                 branchSource1: str = None, ## usually rs1_data
                 branchSource2: str = None, ## usually rs2_data
                 checkMisalignedPc: int = None,  ## can only be 2 or 4
                 aluAsset: str = None,  ## Alu operation addu
                 aluSource1: str = None, ## usually rs1_data or pc
                 aluSource2: str = None, ## usually imm or rs2_data
                 memAddressCalcAsset: str = None, ## usually addu
                 memAddressCalcSource1: str = None, ## usually rs1_data
                 memAddressCalcSource2: str = None, ## usually imm
                 memSize: int = None, ## can be 1, 2, 4
                 memWrite: bool = None, ## if false: read
                 memWriteSource: str = None, ## usually rs2_data
                 memReadFormat: str = None, ## lw (load word) lh, lh (load half word), lhu (load half word unsigned), lb (load byte), lbu (load byte unsigned)
                 checkMisalignedMem: int = None, ## can only be 2 or 4
                 rdSource: str = None  ## usually alu, imm, pcInc (pc + 4), mem
                 ):
               
        self.id = id
        self.opcode = opcode
        
        ## store given opcode family wide parameters in a set
        self.parameters = {'f3': f3,
                           'f7': f7,
                           'f12': f12,
                           'immType': immType,
                           'pcCalcAsset': pcCalcAsset, ## addu
                           'pcCalcSource1': pcCalcSource1,
                           'pcCalcSource2': pcCalcSource2, 
                           'branchAsset': branchAsset,
                           'branchSource1': branchSource1,
                           'branchSource2': branchSource2,
                           'checkMisalignedPc': checkMisalignedPc,   ## 2, 4
                           'aluAsset': aluAsset,  ##
                           'aluSource1': aluSource1,
                           'aluSource2': aluSource2,
                           'memAddressCalcAsset': memAddressCalcAsset,   ## addu
                           'memAddressCalcSource1': memAddressCalcSource1,
                           'memAddressCalcSource2': memAddressCalcSource2,
                           'memSize': memSize,   ## 1, 2, 4
                           'memWrite': memWrite,
                           'memWriteSource': memWriteSource, ## rs2
                           'memReadFormat': memReadFormat,
                           'checkMisalignedMem': checkMisalignedMem,   ## 2, 4
                           'rdSource': rdSource,  ## alu, imm, mem...
                           'valid': None,
                           }
        
        ## store all different values used for each parameter contained in this opcode family
        self.requirements = {
            'immType': [],
            'pcCalcAsset': [],
            'pcCalcSource1': [],
            'pcCalcSource2': [],
            'branchAsset': [],
            'branchSource1': [],
            'branchSource2': [],
            'checkMisalignedPc': [],
            'aluAsset': [],
            'aluSource1': [],
            'aluSource2': [],
            'memAddressCalcAsset': [],
            'memAddressCalcSource1': [],
            'memAddressCalcSource2': [],
            'memSize': [],
            'memWrite': [],
            'memWriteSource': [],
            'memReadFormat': [],
            'checkMisalignedMem': [],
            'rdSource': [],
            'valid': [],
        }

        ## list of contained instructions
        self.instructions = []

    ## add a new instruction to this opcode family, add missing opcode family wide parameters, add parameters to requirements
    def addInstruction(self, instruction: InstructionDefinition):
        for exisitingInstruction in self.instructions:
            if exisitingInstruction.id == instruction.id:
                raise ValueError(F'Instruction with id "{instruction.id}" allready exists in opcode familiy "{self.id}"')
            f3equal = (exisitingInstruction.parameters['f3'] == instruction.parameters['f3'])
            f7equal = (exisitingInstruction.parameters['f7'] == instruction.parameters['f7'])
            f12equal = (exisitingInstruction.parameters['f12'] == instruction.parameters['f12'])
            if f3equal and f7equal and f12equal:
                raise ValueError(F'Instructions with id "{instruction.id}" and "{exisitingInstruction.id}" in opcode family "{self.id}" have same f3, f7 and f12 values defined')

        for key in self.parameters:
            if not self.parameters[key] == None:
                if instruction.parameters[key] == None:
                    instruction.parameters[key] = self.parameters[key]
                elif not instruction.parameters[key] == self.parameters[key]:
                    raise ValueError(F'Instruction "{instruction.id}" parameter "{key}" with value "{instruction.parameters[key]}" contradicts value "{self.parameters[key]}" of opcode family "{self.id}"')
        
        for key in self.requirements:
            if not instruction.parameters[key] == None:
                if not instruction.parameters[key] in self.requirements[key]:
                    self.requirements[key].append(instruction.parameters[key])

        self.instructions.append(instruction)
        return instruction

    ## returns encoding combinations (either whole family or specific instructions), that correspond to a certain value for the given parameter key
    def getParamDefinition(self, parameterKey: str, instructionEncodingKeys: list[str]):
        #print(F' -> {self.id}: getting Definition of "{parameterKey}", depending on "{instructionEncodingKeys}":')
        encodingCombinations = []
        if not self.parameters[parameterKey] == None:
            encoding = []
            encoding.append(self.opcode)
            for key in instructionEncodingKeys:
                encoding.append(self.parameters[key])
            if not encoding in encodingCombinations:
                encodingCombinations.append([encoding, self.parameters[parameterKey]])
        else:
            for instruction in self.instructions:
                if not instruction.parameters[parameterKey] == None:
                    encoding = []
                    encoding.append(self.opcode)
                    for key in instructionEncodingKeys:
                        encoding.append(instruction.parameters[key])
                    if not encoding in encodingCombinations:
                        encodingCombinations.append([encoding, instruction.parameters[parameterKey]])
        return encodingCombinations
    
    ## prints textual representation of all contained instruction descriptions
    def display(self, details: bool = True):
        print(F'- {self.id} -')
        for instruction in self.instructions:
            print(F'| {self.opcode} ', end="")
            instruction.display(details)
        #print(F'______________________')

## Basic definition of a RISC-V instruction set, containing a number of opcode families
class InstructionSet():
    def __init__(self, id: str):
        self.id = id
        self.opcodeFamilies = []

        ## store all specific values used for each parameters contained in this ISA 
        self.requirements = {
            'immType': [],
            'pcCalcAsset': [],
            'pcCalcSource1': [],
            'pcCalcSource2': [],
            'branchAsset': [],
            'branchSource1': [],
            'branchSource2': [],
            'checkMisalignedPc': [],
            'aluAsset': [],
            'aluSource1': [],
            'aluSource2': [],
            'memAddressCalcAsset': [],
            'memAddressCalcSource1': [],
            'memAddressCalcSource2': [],
            'memSize': [],
            'memWrite': [],
            'memWriteSource': [],
            'memReadFormat': [],
            'checkMisalignedMem': [],
            'rdSource': [],
            'valid': []
        }
        
        self.pcCalcSources1 = []
        self.pcCalcSources2 = []
        self.pcCalcAssets = []
        
        self.branchSources1 = []
        self.branchSources2 = []
        self.branchAssets = []
        
        self.aluSources1 = []
        self.aluSources2 = []
        self.aluAssets = []
        
        self.memAddressCalcSources1 = []
        self.memAddressCalcSources2 = []
        self.memAddressCalcAssets = []
        self.memReadFormats = []
        
    ## add a given opcode family, add its requirements to own requirements as well as collect all used assets and sources
    def addOpcodeFamily(self, opcodeFamily: OpcodeFamily):
        for family in self.opcodeFamilies:
            if family.id == opcodeFamily.id:
                raise ValueError(F'Instruction Set "{self.id}" cannot add opcode family "{opcodeFamily.id}", because the id allready exists')
            if family.opcode == opcodeFamily.opcode:
                raise ValueError(F'Instruction Set "{self.id}" cannot add opcode family "{opcodeFamily.opcode}", because the opcode allready exists')
        self.opcodeFamilies.append(opcodeFamily)

        for key in self.requirements:
            for element in opcodeFamily.requirements[key]:
                if not element in self.requirements[key]:
                    self.requirements[key].append(element)
        
        ## pcCalc
        if not opcodeFamily.requirements['pcCalcSource1'] == None:
            sources = opcodeFamily.requirements['pcCalcSource1']
            for source in sources:
                if not source in self.pcCalcSources1:
                    self.pcCalcSources1.append(source)

        if not opcodeFamily.requirements['pcCalcSource2'] == None:
            sources = opcodeFamily.requirements['pcCalcSource2']
            for source in sources:
                if not source in self.pcCalcSources2:
                    self.pcCalcSources2.append(source)
        
        if not opcodeFamily.requirements['pcCalcAsset'] == None:
            toSearch = [] 
            for asset in opcodeFamily.requirements['pcCalcAsset']:
                if isinstance(asset, str):
                    toSearch.append(asset)
                else: 
                    for assetElement in asset:
                        toSearch.append(assetElement)
            for asset in toSearch:
                if not asset in self.pcCalcAssets:
                    self.pcCalcAssets.append(asset)

        ## branch
        if not opcodeFamily.requirements['branchSource1'] == None:
            sources = opcodeFamily.requirements['branchSource1']
            for source in sources:
                if not source in self.branchSources1:
                    self.branchSources1.append(source)

        if not opcodeFamily.requirements['branchSource2'] == None:
            sources = opcodeFamily.requirements['branchSource2']
            for source in sources:
                if not source in self.branchSources2:
                    self.branchSources2.append(source)
        
        if not opcodeFamily.requirements['branchAsset'] == None:
            toSearch = [] 
            for asset in opcodeFamily.requirements['branchAsset']:
                if isinstance(asset, str):
                    toSearch.append(asset)
                else: 
                    for assetElement in asset:
                        toSearch.append(assetElement)
            for asset in toSearch:
                if not asset in self.branchAssets:
                    self.branchAssets.append(asset)

        ## alu
        if not opcodeFamily.requirements['aluSource1'] == None:
            sources = opcodeFamily.requirements['aluSource1']
            for source in sources:
                if not source in self.aluSources1:
                    self.aluSources1.append(source)

        if not opcodeFamily.requirements['aluSource2'] == None:
            sources = opcodeFamily.requirements['aluSource2']
            for source in sources:
                if not source in self.aluSources2:
                    self.aluSources2.append(source)
        
        if not opcodeFamily.requirements['aluAsset'] == None:
            toSearch = [] 
            for asset in opcodeFamily.requirements['aluAsset']:
                if isinstance(asset, str):
                    toSearch.append(asset)
                else: 
                    for assetElement in asset:
                        toSearch.append(assetElement)
            for asset in toSearch:
                if not asset in self.aluAssets:
                    self.aluAssets.append(asset)

        ## memAddressCalc
        if not opcodeFamily.requirements['memAddressCalcSource1'] == None:
            sources = opcodeFamily.requirements['memAddressCalcSource1']
            for source in sources:
                if not source in self.memAddressCalcSources1:
                    self.memAddressCalcSources1.append(source)

        if not opcodeFamily.requirements['memAddressCalcSource2'] == None:
            sources = opcodeFamily.requirements['memAddressCalcSource2']
            for source in sources:
                if not source in self.memAddressCalcSources2:
                    self.memAddressCalcSources2.append(source)
        
        if not opcodeFamily.requirements['memAddressCalcAsset'] == None:
            toSearch = [] 
            for asset in opcodeFamily.requirements['memAddressCalcAsset']:
                if isinstance(asset, str):
                    toSearch.append(asset)
                else: 
                    for assetElement in asset:
                        toSearch.append(assetElement)
            for asset in toSearch:
                if not asset in self.memAddressCalcAssets:
                    self.memAddressCalcAssets.append(asset)

        if not opcodeFamily.requirements['memReadFormat'] == None:
            for format in opcodeFamily.requirements['memReadFormat']:
                if not format in self.memReadFormats:
                    self.memReadFormats.append(format)


        return opcodeFamily

    ## returns encoding combinations, that correspond to a certain value for the given parameter key
    def getParamDefinition(self, parameterKey: str, instructionEncodingKeys: list[str]):
        #print(F'{self.id}: getting Definition of "{parameterKey}", depending on "{instructionEncodingKeys}":')
        encodingCombinations = []
        for family in self.opcodeFamilies:
            for comb in family.getParamDefinition(parameterKey, instructionEncodingKeys):
                if not comb in encodingCombinations:
                    encodingCombinations.append(comb)
        #print(F'encodings: ')
        #for encoding in encodingCombinations:
        #    print(F'- {encoding}')
        return encodingCombinations

    ## prints textual representation of oveall requirements and all contained opcode family descriptions
    def display(self, details: bool = True):
        print(F'_____________________________________________________________')
        print()
        print(F'Display Instrutcion Set: {self.id}')

        ## immType, source1, source2, rdWrite, rdSource, aluAsset, jump, condJump, jumpAddressSource, checkMisalignedPc, memSize, memAddress, memWrite, memSource, checkMisalignedMem
        if details:
            print(F'-- next pc calculation requirenments:')
            print(F'   - assets: {self.pcCalcAssets}')
            print(F'   - source1: {self.pcCalcSources1}')
            print(F'   - source2: {self.pcCalcSources2}')
            if len(self.requirements['checkMisalignedPc']) > 0:
                print(F'   - misaligned jump address checks: {self.requirements['checkMisalignedPc']}')
            print(F'-- branch calculation requirenments:')
            print(F'   - assets: {self.branchAssets}')
            print(F'   - source1: {self.branchSources1}')
            print(F'   - source2: {self.branchSources2}')
            print(F'-- alu requirenments:')
            print(F'   - assets: {self.aluAssets}')
            print(F'   - source1: {self.aluSources1}')
            print(F'   - source1: {self.aluSources1}')
            print(F'-- memory address calculation requirenments:')
            print(F'   - assets: {self.memAddressCalcAssets}')
            print(F'   - source1: {self.memAddressCalcSources1}')
            print(F'   - source2: {self.memAddressCalcSources1}')
            print(F'   - memory write sources: {self.requirements['memWriteSource']}')
            print(F'   - memory read formats: {self.memReadFormats}')
            if len(self.requirements['checkMisalignedMem']) > 0:
                print(F'   - misaligned memory address checks: {self.requirements['checkMisalignedMem']}')
            print(F'-- writeback requirements:')
            print(F'   - rd sources: {self.requirements['rdSource']}')
        print(F'_____________________________________________________________')
        for family in self.opcodeFamilies:
            family.display(details)
        print(F'_____________________________________________________________')
        print()

## Specific definition of the RISC-V 32I ISA
def generateRV32I(display: bool = False, catchMisalignedMemoryAddress: bool = True):
    rv32i = InstructionSet('rv32i')

    ## Comp RI
    if True:
        compRI = OpcodeFamily('compRI', '0010011', aluSource1 = 'rs1_data', aluSource2 = 'imm', rdSource = 'alu')
        addI = compRI.addInstruction(InstructionDefinition('addI', f3 = '000', immType = 'I', aluAsset = 'addu'))
        slti = compRI.addInstruction(InstructionDefinition('slti', f3 = '010', immType = 'I', aluAsset = 'lts'))
        sltiu = compRI.addInstruction(InstructionDefinition('sltiu', f3 = '011', immType = 'I', aluAsset = 'ltu'))
        xori = compRI.addInstruction(InstructionDefinition('xori', f3 = '100', immType = 'I', aluAsset = 'xor'))
        ori = compRI.addInstruction(InstructionDefinition('ori', f3 = '110', immType = 'I', aluAsset = 'or'))
        andi = compRI.addInstruction(InstructionDefinition('andi', f3 = '111', immType = 'I', aluAsset = 'and'))
        slli = compRI.addInstruction(InstructionDefinition('slli', f3 = '001', f7 = '0000000', immType = 'shamt', aluAsset = 'sll'))
        srli = compRI.addInstruction(InstructionDefinition('srli', f3 = '101', f7 = '0000000', immType = 'shamt', aluAsset = 'srl'))
        srai = compRI.addInstruction(InstructionDefinition('srai', f3 = '101', f7 = '0100000', immType = 'shamt', aluAsset = 'sra'))
        rv32i.addOpcodeFamily(compRI)

    ## Comp RI - LUI
    if True:
        compRILUI = OpcodeFamily('compRILUI', '0110111', immType = 'U', rdSource = 'imm')
        lui = compRILUI.addInstruction(InstructionDefinition('lui'))
        rv32i.addOpcodeFamily(compRILUI)

    ## Comp RI - AUIPC
    if True:
        compRIAUIPC = OpcodeFamily('compRIAUIPC', '0010111', immType = 'U', aluAsset = 'addu', aluSource1 = 'pc', aluSource2 = 'imm', rdSource = 'alu')
        auipc = compRIAUIPC.addInstruction(InstructionDefinition('auipc'))
        rv32i.addOpcodeFamily(compRIAUIPC)

    ## Comp RR
    if True:
        compRR = OpcodeFamily('compRR', '0110011', aluSource1 = 'rs1_data', aluSource2 = 'rs2_data', rdSource = 'alu')
        add = compRR.addInstruction(InstructionDefinition('add', f3 = '000', f7 = '0000000', aluAsset = 'adds'))
        sub = compRR.addInstruction(InstructionDefinition('sub', f3 = '000', f7 = '0100000', aluAsset = 'subs'))
        sll = compRR.addInstruction(InstructionDefinition('sll', f3 = '001', f7 = '0000000', aluAsset = 'sll'))
        slt = compRR.addInstruction(InstructionDefinition('slt', f3 = '010', f7 = '0000000', aluAsset = 'lts'))
        sltu = compRR.addInstruction(InstructionDefinition('sltu', f3 = '011', f7 = '0000000', aluAsset = 'ltu'))
        xor = compRR.addInstruction(InstructionDefinition('xor', f3 = '100', f7 = '0000000', aluAsset = 'xor'))
        srl = compRR.addInstruction(InstructionDefinition('srl', f3 = '101', f7 = '0000000', aluAsset = 'srl'))
        sra = compRR.addInstruction(InstructionDefinition('sra', f3 = '101', f7 = '0100000', aluAsset = 'sra'))
        orrr = compRR.addInstruction(InstructionDefinition('or', f3 = '110', f7 = '0000000', aluAsset = 'or'))
        andrr = compRR.addInstruction(InstructionDefinition('and', f3 = '111', f7 = '0000000', aluAsset = 'and'))
        rv32i.addOpcodeFamily(compRR)

    ## ContTrans - JAL
    if True:
        contTransJAL = OpcodeFamily('contTransJAL', '1101111', immType = 'J', pcCalcSource1 = 'pc', pcCalcSource2 = 'imm', pcCalcAsset = 'addu', rdSource = 'pcInc')
        contTransJAL.parameters['checkMisalignedPc'] = 4
        jal = contTransJAL.addInstruction(InstructionDefinition('jal'))
        rv32i.addOpcodeFamily(contTransJAL)

    ## ContTrans - JALR
    if True:
        contTransJALR = OpcodeFamily('contTransJALR', '1100111', f3 = '000', immType = 'I', pcCalcSource1 = 'rs1_data', pcCalcSource2 = 'imm', rdSource = 'pcInc', pcCalcAsset = 'addu31')
        jalr = contTransJALR.addInstruction(InstructionDefinition('jalr'))
        contTransJALR.parameters['checkMisalignedPc'] = 4
        rv32i.addOpcodeFamily(contTransJALR)

    ## ContTrans
    if True:
        contTrans = OpcodeFamily('contTrans', '1100011', immType = 'B', pcCalcSource1 = 'pc', pcCalcSource2 = 'imm', pcCalcAsset = 'addu31', branchSource1 = 'rs1_data', branchSource2 = 'rs2_data')
        contTrans.parameters['checkMisalignedPc'] = 4
        beq = contTrans.addInstruction(InstructionDefinition('beq', f3 = '000', branchAsset = 'equals'))
        bne = contTrans.addInstruction(InstructionDefinition('bne', f3 = '001', branchAsset = 'equalsNot'))
        blt = contTrans.addInstruction(InstructionDefinition('blt', f3 = '100', branchAsset = 'lts'))
        bge = contTrans.addInstruction(InstructionDefinition('bge', f3 = '101', branchAsset = 'ges'))
        bltu = contTrans.addInstruction(InstructionDefinition('bltu', f3 = '110', branchAsset = 'ltu'))
        bgeu = contTrans.addInstruction(InstructionDefinition('bgeu', f3 = '111', branchAsset = 'geu'))

        rv32i.addOpcodeFamily(contTrans)

    ## Mem Load
    if True:
        memLoad = OpcodeFamily('memLoad', '0000011', immType = 'I', memAddressCalcSource1 = 'rs1_data', memAddressCalcSource2 = 'imm', memAddressCalcAsset = 'addu', rdSource = 'mem', memWrite = False)
        lb = memLoad.addInstruction(InstructionDefinition('lb', f3 = '000', memReadFormat = 'lb', memSize=1))
        lh = InstructionDefinition('lh', f3 = '001', memReadFormat = 'lh', memSize=2)
        if catchMisalignedMemoryAddress: lh.parameters['checkMisalignedMem'] = 2
        memLoad.addInstruction(lh)
        lw = InstructionDefinition('lw', f3 = '010', memReadFormat = 'lw', memSize=4)
        if catchMisalignedMemoryAddress: lw.parameters['checkMisalignedMem'] = 4
        memLoad.addInstruction(lw)
        lbu = memLoad.addInstruction(InstructionDefinition('lbu', f3 = '100', memReadFormat = 'lbu', memSize=1))
        lhu = InstructionDefinition('lhu', f3 = '101', memReadFormat = 'lhu', memSize=2)
        if catchMisalignedMemoryAddress: lhu.parameters['checkMisalignedMem'] = 2
        memLoad.addInstruction(lhu)
        rv32i.addOpcodeFamily(memLoad)

    ## Mem Store
    if True:
        memStore = OpcodeFamily('memStore', '0100011', immType = 'S', memAddressCalcSource1 = 'rs1_data', memAddressCalcSource2 = 'imm', memAddressCalcAsset = 'addu', memWrite = True, memWriteSource = 'rs2_data')
        sb = memStore.addInstruction(InstructionDefinition('sb', f3 = '000', memSize=1))
        sh = InstructionDefinition('sh', f3 = '001', memSize=2)
        if catchMisalignedMemoryAddress: sh.parameters['checkMisalignedMem'] = 2
        memStore.addInstruction(sh)
        sw = InstructionDefinition('sw', f3 = '010', memSize=4)
        if catchMisalignedMemoryAddress: sw.parameters['checkMisalignedMem'] = 4
        memStore.addInstruction(sw)
        rv32i.addOpcodeFamily(memStore)

    ## Fence
    if True:
        fence = OpcodeFamily('fence', '0001111', f3 = '000')
        ins = fence.addInstruction(InstructionDefinition('fence'))
        rv32i.addOpcodeFamily(fence)

    ## System CSR
    #if True:

    if display:
        rv32i.display(True)
        
    return rv32i

## Generic stage class to build a RISC-V CPU stage with a unified handshake protocol for the controll path and a usable resource linking mechanic
class RV32Stage(formalHandshake_Hardware.Hardware_Module):
    def __init__(self, id: str, pipelined: bool):
        #print(F'   - FormalRV: Building RV stage "{id}"')
        super().__init__(id)

        self.pipelined = pipelined
        self.buffered = False

        ## Control Signals for unified handshake protocol
        self.stageControlIO = []
        ## next stage is ready
        self.nextReady = self.addInput('io.nextReady', 'Bool()')
        self.stageControlIO.append(self.nextReady)
        ## this stage is ready
        self.ready = self.addOutput('io.ready', 'Bool()')
        self.stageControlIO.append(self.ready)
        ## enable this stage, if it is ready
        self.enable = self.addInput('io.enable', 'Bool()')
        self.stageControlIO.append(self.enable)
        ## stage is currently active
        self.active = self.addOutput('io.active', 'Bool()')
        self.stageControlIO.append(self.active)
        ## stage has finished execution
        self.done = self.addOutput('io.done', 'Bool()')
        self.stageControlIO.append(self.done)
        ## execution was valid
        self.valid = self.addOutput('io.valid', 'Bool()')
        self.stageControlIO.append(self.valid)

        ## last stage insertet a NOP
        self.lastNOP = self.addInput('io.lastNop', 'Bool()')
        self.stageControlIO.append(self.lastNOP)
        ## stage inserts or passes through a NOP
        self.NOP = self.addOutput('io.nop', 'Bool()')
        self.stageControlIO.append(self.NOP)

        ## Signals/resoucres expected from other stages
        self.stageInputs = []
        ## Signals/resoucres supplied to other stages
        self.stageOutputs = []

        ## Outputs that are delayed by default (like the answer of a memory bus)
        self.delayedOutputs = []

        ## Signals for potential Hazard detection
        self.conflictOutputs = []
        self.conflictedReads = []
        self.conflictedWrites = []

    ## Add specialized input, that also represents the request for a recource for the rest of the pipeline
    def addStageInput(self, id: str, type: str, keyword: str = None):
        input = super().addInput(id, type, keyword)
        self.stageInputs.append(input)
        return input
    
    ## Add specialized output, that also represents a recource for the rest of the pipeline
    def addStageOutput(self, id: str, type: str, delayed: bool = False, keyword: str = None):
        output = super().addOutput(id, type, keyword)
        self.stageOutputs.append(output)
        if delayed: 
            self.delayedOutputs.append(output)
        return output

    ## Add a conflicted output
    def addConflictOutput(self, id: str, type: str, keyword: str = None):
        output = super().addOutput(id, type, keyword)
        self.conflictOutputs.append(output)
        return output
    
    ## Automatically connects the corresponding control signals for a combinational stage
    def combinational(self):
        self.connect(self.enable, self.done)
        self.connect(self.enable, self.active)
        self.connect(self.nextReady, self.ready)
        return self

    ## Automatically connects the corresponding control signals to stall, whenever the stage is enabled and the given condition is not met
    def stallingOn(self, condition: Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_IOPort]):
        if not condition.parent == self:
            raise ValueError(F'Stage "{self.id}" cannot stall on "{condition.id}", it is not its parent')
        
        #notDone = self.isNot('notDone', condition)
        #waiting = formalHandshake_Hardware.Register('waiting', self, 'Bool()', 'False')
        #active = self.isOr('active', waiting, self.enable)
        #self.connect(active, self.active)
        #stall = self.isAnd('stall', active, notDone)
        #self.connect(stall, waiting.input())
        #self.connect(self.isAnd('activeAndCondition', active, condition), self.done)
        #self.connect(self.isNot('noStall', stall), self.ready)

        stallLogic = self.addSubModule(formalHandshake_Hardware.Hardware_Module('stallLogic'))
        ready = stallLogic.addOutput('io.ready', 'Bool()')
        self.connect(self.isAnd('ready', ready, self.nextReady), self.ready)
        enable = stallLogic.addInput('io.enable', 'Bool()')
        self.connect(self.enable, enable)
        active = stallLogic.addOutput('io.active', 'Bool()')
        self.connect(active, self.active)
        done = stallLogic.addOutput('io.done', 'Bool()')
        self.connect(done, self.done)

        cond = stallLogic.addInput('io.condition', 'Bool()')
        self.connect(condition, cond)

        notDone = stallLogic.isNot('notDone', cond)
        waiting = formalHandshake_Hardware.Register('waiting', stallLogic, 'Bool()', 'False')
        isActive = stallLogic.isOr('isActive', waiting, enable)
        stallLogic.connect(isActive, active)
        stall = stallLogic.isAnd('stall', isActive, notDone)
        stallLogic.connect(stall, waiting.input())
        stallLogic.connect(stallLogic.isAnd('activeAndCondition', isActive, cond), done)
        #stallLogic.connect(stallLogic.isNot('noStall', stall), ready)
        stallLogic.connect(stallLogic.isOr('ready', stallLogic.isNot('inactive', isActive), done), ready) ## ?!
        return self

    ## Automatically connects the corresponding control signals to only produce a positiove valid signal, if the stage is enabled and the given condition is met
    def validOn(self, conditions: Union[list[Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_IOPort]], Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_IOPort]] = None):
        if conditions == None:
            self.connect(self.true(), self.valid)
            self.connect(self.lastNOP, self.NOP)
        else:
            if isinstance(conditions, list):
                for condition in conditions:
                    if not condition.parent == self:
                        raise ValueError(F'Stage "{self.id}" cannot stall on "{condition.id}", it is not its parent')
                valid = self.multiOr('valid', conditions)
            else:
                valid = conditions
            self.connect(valid, self.valid)
            self.connect(self.isOr('nop', self.lastNOP, self.isAnd('invalidDone', self.done, self.isNot('invalid', valid))), self.NOP)
        return self

    ## Automatically add a select Input for a given instruction parameter, with a corresponding bit width
    def addSelectInput(self, selectID: str, instructionSet: InstructionSet):
        if not selectID in instructionSet.requirements:
            raise ValueError(F'Stage "{self.id}" cannot build select input "{selectID}" from instruction set "{instructionSet.id}"')
        sourceIDs = instructionSet.requirements[selectID]
        bitLength = len(sourceIDs).bit_length()
        type = F'UInt({bitLength} bits)'
        return self.addStageInput(F'io.{selectID}', type)

    ## Either use stages existing internal signal as resource or request it from the rest of the pipeline via a stage input according to the given ISA
    def getResource(self, key: str, createFrom: InstructionSet = None):
        if key == False:
            return self.false()
        if key == True:
            return self.true()
        for input in self.inputs:
            if input.id == F'io.{key}':
                return input
        for function in self.functions:
            if function.id == F'{key}':
                return function
        for module in self.subModules:
            for output in module.outputs:
                if output.id == F'io.{key}':
                    return output
        if not createFrom == None:
            return self.addSelectInput(key, createFrom)

    ## Either use existing or create and return an equals function of the given select signal and the given specific value -> can be used for example for creating a "memNotActive" signal
    def getSelectValCompare(self, select: str, instructionSet: InstructionSet, val: int):
        ## check if select is in instructionSet
        if not select in instructionSet.requirements:
            raise ValueError(F'Stage "{self.id}" cannot create equals for "{select}" and val "{val}", it is not part of instruction set "{instructionSet.id}"')
        ## check if selectValCompare exists
        for function in self.functions:
            if function.id == F'{select}_{val}':
                return function
        if len(instructionSet.requirements[select]) == 0:
            return self.false()
        
        selectIDs = instructionSet.requirements[select]
        bitLength = len(selectIDs).bit_length()
        type = F'UInt({bitLength} bits)'

        if self.getResource(select):
            selectSignal = self.getResource(select)
        else:
            selectSignal = self.addStageInput(F'io.{select}', type)

        equals = self.equals(F'{select}_{val}', selectSignal, self.const(type, F'U({val}, {bitLength} bits)'))
        return equals

    ## Creates a multiplexer for a given instruction parameter, choosing the corresponding source input for a corresponding source select signal
    def createMultiplexerFromDecode(self, id: str, instructionSet: InstructionSet, defaultValue: Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_IOPort], prioritySource: formalHandshake_Hardware.Hardware_Module = None):
        select = self.getResource(id)
        #print(F'Stage "{self.id}" creating multiplexer for: "{id}" with sources: {instructionSet.requirements[id]}, selected by {select.parent.id}.{select.id}')
        
        ## check if signal is in instructionSet
        if not id in instructionSet.requirements:
            raise ValueError(F'Stage "{self.id}" cannot create decode multiplexer for "{id}", it is not part of instruction set "{instructionSet.id}"')
        
        ## requirements empty ?
        if len(instructionSet.requirements[id]) == 0:
            multiplexer = defaultValue
        else:
            sourceIDs = instructionSet.requirements[id]
            bitLength = len(sourceIDs).bit_length()
            type = F'UInt({bitLength} bits)'
            if select == None:
                if self.getInput(F'io.{id}'):
                    select = self.getInput(F'io.{id}')
                else:
                    select = self.addStageInput(F'io.{id}', type)

            sources = []
            sources.append(defaultValue)

            for source in sourceIDs:
                found = False
                if not prioritySource == None:
                    if prioritySource.getOutput(F'io.{source}'):
                        sources.append(prioritySource.getOutput(F'io.{source}'))
                        found = True
                if not found:
                    recource = self.getResource(source)
                    if not recource:
                        sources.append(self.addStageInput(F'io.{source}', defaultValue.getType()))
                    else:
                        sources.append(recource)
            multiplexer = self.multiplex(F'{id}Select', defaultValue.getType(), select, sources)
        return multiplexer

    ## returns a boolean signal that determines if a certain parameter value was selected by the respective existing or newly created source select input
    def getIDSelected(self, sourceSelect: str, instructionSet: InstructionSet, sourceID: str, create: bool = False):
        #print(F'If source "{sourceID}" is in instructionSet "{instructionSet.id}":  try and return boolean, that determines, if source is selected by "{sourceSelect}" ')
        #print(F' -> {sourceID} in {instructionSet.requirements[sourceSelect]}?')
        if not sourceID in instructionSet.requirements[sourceSelect]:
            #print(F' -> not in sources')
            return False
        else:
            value = None
            for s, source in enumerate(instructionSet.requirements[sourceSelect]):
                if source == sourceID:
                    value = s
                    break
            if self.getResource(sourceSelect):
                #print(F' -> source select is {self.getResource(sourceSelect).parent.id}.{self.getResource(sourceSelect).id}, type: {self.getResource(sourceSelect).getType()}, value would be: {value + 1}')
                return self.getSelectValCompare(sourceSelect, instructionSet, value + 1)
            else:
                if create:
                    self.addSelectInput(sourceSelect, instructionSet)
                    return self.getSelectValCompare(sourceSelect, instructionSet, value + 1)
                else:
                    raise ValueError(F'Stage "{self.id}" is trying to build "IDSelected" boolean for source "{sourceID}", but select signal "{sourceSelect}" is missing')

    ## Announce the read of a source with a certain id and a certain address, potentially leading to a hazard -> for example reading from a certain register
    def readConflicted(self, conflictID: str, addressID: str, sourceID: str, readCondition: Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_IOPort] = None, actualRead: bool = False):
        if readCondition == None: 
            readCondition = self.true()
        else:
            if not (readCondition.parent == self or (isinstance(readCondition, formalHandshake_Hardware.Hardware_IOPort) and readCondition.parent.parent == self)):
                raise ValueError(F'Stage "{self.id}" cannot add conflicted read "[{conflictID}, {addressID}, {sourceID}]", condition "{readCondition.id}" is part of this stages recources')
            if not formalHandshake_Hardware.isBoolean(readCondition):
                raise ValueError(F'Stage "{self.id}" cannot add conflicted read "[{conflictID}, {addressID}, {sourceID}]" with non boolean condition "{readCondition.id}"')
        if not self.getOutput('io.' + addressID):
            raise ValueError(F'Stage "{self.id}" cannot add conflicted read "[{conflictID}, {addressID}, {sourceID}]", address "{addressID}" is not own output')
        else:
            address = self.getOutput('io.' + addressID)
        if not self.getInput('io.' + sourceID):
            raise ValueError(F'Stage "{self.id}" cannot add conflicted read "[{conflictID}, {addressID}, {sourceID}]", read source "{sourceID}" is not own input')
        else:
            source = self.getInput('io.' + sourceID)
        output = self.addConflictOutput(F'io.{addressID}Read', 'Bool()')
        self.connect(readCondition, output)
        self.conflictedReads.append([conflictID, address, source, output, actualRead])
        self.conflictOutputs.append(address)
        return self
    
    ## Announce the writing to a destination with a certain id and a certain address, potentially leading to a hazard -> for example writing to a certain register
    def writeConflicted(self, conflictID: str, addressID: str, dataID: str, writeCondition: Union[formalHandshake_Hardware.Hardware_Function, formalHandshake_Hardware.Hardware_IOPort] = None, actualWrite: bool = False):
        if writeCondition == None: 
            writeCondition = self.true()
        else:
            if not (writeCondition.parent == self or (isinstance(writeCondition, formalHandshake_Hardware.Hardware_IOPort) and writeCondition.parent.parent == self)):
                raise ValueError(F'Stage "{self.id}" cannot add conflicted write "[{conflictID}, {addressID}, {dataID}]", condition "{writeCondition.id}" is part of this stages recources')
            if not formalHandshake_Hardware.isBoolean(writeCondition):
                raise ValueError(F'Stage "{self.id}" cannot add conflicted write "[{conflictID}, {addressID}, {dataID}]" with non boolean condition "{writeCondition.id}"')
        if not self.getOutput('io.' + addressID):
            raise ValueError(F'Stage "{self.id}" cannot add conflicted write "[{conflictID}, {addressID}, {dataID}]", address "{addressID}" is not own output')
        else:
            address = self.getOutput('io.' + addressID)
        if not self.getOutput('io.' + dataID):
            raise ValueError(F'Stage "{self.id}" cannot add conflicted write "[{conflictID}, {addressID}, {dataID}]", write data "{dataID}" is not own output')
        else:
            data = self.getOutput('io.' + dataID)
        output = self.addConflictOutput(F'io.{addressID}Write', 'Bool()')
        self.connect(writeCondition, output)
        self.conflictedWrites.append([conflictID, address, data, output, actualWrite])
        self.conflictOutputs.append(address)
        
    ## Return all stageInputs
    def getUsedRecources(self):
        return self.stageInputs
        
    ## Return all stageOutputs
    def getProvidedRecources(self):
        return self.stageOutputs

    ## Return all IOs, that are not part of the resource mechanic
    def getNonStagedIO(self):
        signals = []
        for input in self.inputs:
            if not (input in self.stageInputs or input in self.stageControlIO):
                signals.append(input)
        for output in self.outputs:
            if not (output in self.stageOutputs or output in self.stageControlIO):
                signals.append(output)
        return signals

## Generic stage proof class to build a number of standard control signal proofs
class RV32StageProof(formalHandshake_Hardware.Hardware_Module):
    def __init__(self, id: str, stage: RV32Stage, project: FormalHandshakeHardwareProject):
        super().__init__(id)
        self.stage = stage
        self.addSubModule(stage)
        self.project = project

    ## liveness proof
    def build_livenessProof(self, maxCycles: bool, specificCycles: int, pipelined: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        self.link(self.stage.inputs, True)
        self.link(self.stage.done, True)
        id = F'{self.stage.id}_liveness'
        #self.liveness(id, self.isAnd('validStart', self.stage.getInput('io.enable'), self.stage.getOutput('io.ready')), self.stage.getOutput('io.done'), maxCycles, specificCycles, pipelined, initialReset)
        self.liveness(id, self.stage.getInput('io.enable'), self.stage.getOutput('io.done'), maxCycles, specificCycles, pipelined, initialReset)
        if add:
            self.project.addSymbiYosysProof(self, self.stage.id, (maxCycles + 3), None, priority, overwrite, False)
        return self
   
    ## proof that only done when active
    def build_activeProof(self, maxCycles: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        self.link(self.stage.inputs, True)
        self.link([self.stage.active, self.stage.done], True)
        self.assertion(self.getOutput('io.active')).on(self.getOutput('io.done'))
        if initialReset:
            self.stage.assumeInitialReset()
        if add:
            self.project.addSymbiYosysProof(self, self.stage.id, (maxCycles + 3), None, priority, overwrite, False)
        return self
        
    ## proof that only ready when expected
    def build_readyProof(self, maxCycles: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        self.link(self.stage.inputs, True)
        readyExpected = self.isAnd('readyExpected', self.getInput('io.nextReady'), self.isOr('internalReady', self.isNot('inactive', self.stage.active), self.stage.done))
        valid = self.isOr('valid', self.isAnd('readyWhenExpected', self.stage.ready, readyExpected), self.isAnd('notReadyWhenNotExpected', self.isNot('notReady', self.stage.ready), self.isNot('notReadyExpected', readyExpected)))
        self.assertion(valid).on(self.isNot('noReset', self.reset()))
        if initialReset:
            self.stage.assumeInitialReset()
        if add:
            self.project.addSymbiYosysProof(self, self.stage.id, (maxCycles + 3), None, priority, overwrite, False)
        return self
    
    ## proof that nop is correctly passed through or inserted
    def build_NOPProof(self, maxCycles: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        self.link(self.stage.inputs, True)
        lastNop = self.getInput('io.lastNop')
        self.link(self.stage.NOP, True)
        invalidDone = self.isAnd('invalidDone', self.stage.done, self.isNot('invalid', self.stage.valid))
        nopExpected = self.isOr('nopExpected', lastNop, invalidDone)
        self.assertion(self.getOutput('io.nop')).on(nopExpected)
        if initialReset:
            self.stage.assumeInitialReset()
        if add:
            self.project.addSymbiYosysProof(self, self.stage.id, (maxCycles + 3), None, priority, overwrite, False)
        return self

## Prebuild register file
def build_RV32RegFile(id: str, readBypass: bool = False, display: bool = False):
    print(F'   - FormalRV: Building rv32 regfile "{id}"')
    regfile = formalHandshake_Hardware.Hardware_Module(id)
    rs1 = regfile.addInput('rs1', 'UInt(5 bits)')
    rs1_data = regfile.addOutput('rs1_data', 'Bits(32 bits)')
    rs2 = regfile.addInput('rs2', 'UInt(5 bits)')
    rs2_data = regfile.addOutput('rs2_data', 'Bits(32 bits)')
    rd = regfile.addInput('rd', 'UInt(5 bits)')
    rd_data = regfile.addInput('rd_data', 'Bits(32 bits)')
    writeEnable = regfile.addInput('writeEnable', 'Bool()')

    regs = []

    for i in range(32):
        source = regfile.const('Bits(32 bits)', 'B(0, 32 bits)')
        if i > 0:
            rdAddress = regfile.equals(F'rdAddress_{i}', rd, regfile.const('UInt(5 bits)', F'U({i}, 5 bits)'))
            write = regfile.isAnd(F'write_{i}', rdAddress, writeEnable)
            reg = formalHandshake_Hardware.LoopedReg(F'reg_{i}', regfile, 'Bits(32 bits)', 'B(0, 32 bits)', keywordIn=rd_data.getKeyword(), keywordStore=write.getKeyword())
            source = reg.value()
        regs.append(source)
    
    rs1_dataSource = regfile.multiplex('rs1_dataSource', 'Bits(32 bits)', rs1, regs)
    rs2_dataSource = regfile.multiplex('rs2_dataSource', 'Bits(32 bits)', rs2, regs)

    if readBypass:
        rs1ReadRd = regfile.equals('rs1ReadRd', rs1, rd)
        rs2ReadRd = regfile.equals('rs2ReadRd', rs2, rd)
        bypassRs1 = regfile.whenOtherwise('bypassRs1', rs1ReadRd, rd_data, rs1_dataSource, rs1_data.getKeyword())
        bypassRs2 = regfile.whenOtherwise('bypassRs2', rs2ReadRd, rd_data, rs2_dataSource, rs2_data.getKeyword())
    else:
        rs1_dataSource.keyword = rs1_data.getKeyword()
        rs2_dataSource.keyword = rs2_data.getKeyword()

    
    regfile.connectAllKeywords()

    if display:
        regfile.checkIOConnections()
        regfile.sortSequentialSteps()
        regfile.draw_Grid_network()
    return regfile

## Generic pipeline class to build a RISC-V CPU pipeline with a unified handshake protocol for the controll path and a usable resource linking mechanic
class RV32Pipeline(formalHandshake_Hardware.Hardware_Module):
    def __init__(self, id: str):
        super().__init__(id)

        ## Control Signals for unified handshake protocol:

        ## next element is ready
        self.nextReady =  self.addInput('io.nextReady', 'Bool()')
        ## enable first stage, if it is ready
        self.enable = self.addInput('io.enable', 'Bool()')
        ## frist stage is ready
        self.ready = self.addOutput('io.ready', 'Bool()')
        ## at least one stage is currently active
        self.active = self.addOutput('io.active', 'Bool()')
        ## last stage has finished execution
        self.done = self.addOutput('io.done', 'Bool()')
        ## execution was valid
        self.valid = self.addOutput('io.valid', 'Bool()')
        ## pipeline has produced a NOP
        self.NOP = self.addOutput('io.nop', 'Bool()')

        self.hazardDetection = None

    ## Unused yet
    def bufferStage(self, resources: list[Union[formalHandshake_Hardware.Hardware_IOPort, formalHandshake_Hardware.Hardware_Function]], lastStage: RV32Stage, stage: RV32Stage, display: bool = False):
        print(F'   - FormalRV: Buffering stage "{stage.id}"')
        buffer = formalHandshake_Hardware.Hardware_Module(F'{stage.id}_buffer')
        self.addSubModule(buffer)

        load = buffer.addInput('io.load', 'Bool()')
        if not self.hazardDetection == None and self.hazardDetection.getOutput(F'io.{stage.id}_stall'):
            #print(F'!!! Should look for hazard stall for current stage here, connecting ("{stage.id}.{stage.ready.id}" and not "{self.hazardDetection.getOutput(F'io.{stage.id}_stall').parent.id}.{self.hazardDetection.getOutput(F'io.{stage.id}_stall').id}") to buffer.load')
            self.connect(self.isAnd(F'{stage.id}_readyAndNoStall', stage.ready, self.isNot(F'{stage.id}_noStall', self.hazardDetection.getOutput(F'io.{stage.id}_stall'))), load)
        else:
            self.connect(stage.ready, load)
        
        ## buffering stage enable
        enableBuffered = buffer.addInput('io.enable_buffered', 'Bool()')
        self.connect(self.isAnd(F'{lastStage.id}_validDone', lastStage.done, lastStage.valid), enableBuffered)
        enable = buffer.addOutput('io.enable', 'Bool()')
        self.connect(enable, stage.enable)
        enableBuffer = formalHandshake_Hardware.LoopedReg('enable', buffer, 'Bool()', 'False')
        buffer.connect(load, enableBuffer.store())
        buffer.connect(enableBuffered, enableBuffer.input())
        buffer.connect(enableBuffer.value(), enable)

        
        ## buffering stage NOP
        NOPBuffered = buffer.addInput('io.nop_buffered', 'Bool()')
        self.connect(lastStage.NOP, NOPBuffered)
        nop = buffer.addOutput('io.nop', 'Bool()')
        self.connect(nop, stage.lastNOP)
        NOPBuffer = formalHandshake_Hardware.LoopedReg('nop', buffer, 'Bool()', 'False')
        buffer.connect(load, NOPBuffer.store())
        buffer.connect(NOPBuffered, NOPBuffer.input())
        buffer.connect(NOPBuffer.value(), nop)

        newResources = []

        for resource in resources:
            if resource in lastStage.delayedOutputs:
                #print(F'should not buffer {lastStage.id}.{resource.id}')
                newResources.append(resource)
            else:
                id = F'{resource.id}_buffered'
                #print(F' -> stage "{stage.id}" buffering {resource.id}')
                type = resource.getType()
                bufferInput =  buffer.addInput(id, type)
                self.connect(resource, bufferInput)
                bufferReg = formalHandshake_Hardware.LoopedReg(F'{id.replace('.', '_')}_buffer', buffer, type)
                buffer.connect(load, bufferReg.store())
                buffer.connect(bufferInput, bufferReg.input())
                bufferOutput = buffer.addOutput(resource.id, type)
                buffer.connect(bufferReg.value(), bufferOutput)
                newResources.append(bufferOutput)

        if display:
            buffer.checkIOConnections()
            buffer.sortSequentialSteps()
            buffer.draw_Grid_network()
        return newResources

    ## Unused yet
    def buildHazardDetection(self, stages: list[RV32Stage], forwarding: bool = False, writeReadBypasses: list[str] = None, display: bool = False):
        print(F'   - FormalRV: Building hazard detection for Pipeline "{self.id}"')
        hazard = None
        for s1, stage1 in enumerate(stages):
            stallConditions = []
            toForward = []
            if len(stage1.conflictedReads) > 0:
                #print(F' - Checking potential conflicts for stage "{stage1.id}"')
                for r, conflictRead in enumerate(stage1.conflictedReads):
                    for s2, stage2 in enumerate(stages):
                        if s2 > s1 and len(stage2.conflictedWrites) > 0:
                            for w, conflictWrite in enumerate(stage2.conflictedWrites):
                                ## check if conflictID is equal and [conflictID, stage2, stage1] is not in assumed bypasses
                                if conflictRead[0] == conflictWrite[0] and not (conflictRead[4] and conflictWrite[4] and conflictRead[0] in writeReadBypasses):
                                    #print(F'   -> not ({conflictRead[4]} and {conflictWrite[4]} and {conflictRead[0]} in writeReadBypasses): can be skipped for {conflictRead[2].parent.id}.{conflictRead[2].id} from {conflictWrite[2].parent.id}.{conflictWrite[2].id}')
                                    if hazard == None:
                                        hazard = formalHandshake_Hardware.Hardware_Module('hazardDetection')
                                        self.addSubModule(hazard)
                                        self.hazardDetection = hazard
                                    #print(F'   -> potential conflict "{conflictRead[0]}" between reading stage "{stage1.id}" and writing stage "{stage2.id}"')
                                    conditions = []
                                    #print(F'      -> Condition 1: {conflictRead[3].parent.id}.{conflictRead[3].id}')
                                    input1 = hazard.addInput(F'{conflictRead[3].id}_s{s1}r{r}_s{s2}w{w}', 'Bool()')
                                    self.connect(conflictRead[3], input1)
                                    conditions.append(input1)
                                    #print(F'      -> Condition 2: {conflictWrite[3].parent.id}.{conflictWrite[3].id}')
                                    input2 = hazard.addInput(F'{conflictWrite[3].id}_s{s1}r{r}_s{s2}w{w}', 'Bool()')
                                    self.connect(conflictWrite[3], input2)
                                    conditions.append(input2)
                                    #print(F'      -> Condition 3: {conflictRead[1].parent.id}.{conflictRead[1].id} equals {conflictWrite[1].parent.id}.{conflictWrite[1].id}')
                                    input3 = hazard.addInput(F'{conflictRead[1].id}_s{s1}r{r}_s{s2}w{w}', conflictRead[1].getType())
                                    self.connect(conflictRead[1], input3)
                                    input4 = hazard.addInput(F'{conflictWrite[1].id}_s{s1}r{r}_s{s2}w{w}', conflictWrite[1].getType())
                                    self.connect(conflictWrite[1], input4)
                                    conditions.append(hazard.equals(F'addressMatch_s{s1}r{r}_s{s2}w{w}', input3, input4))
                                    
                                    condition = hazard.multiAnd(F'conflict_s{s1}r{r}_s{s2}w{w}', conditions)
                                    if forwarding and not conflictWrite[2] in stage2.delayedOutputs:
                                        if not hazard.getInput(conflictWrite[2].id):
                                            newSource = hazard.addInput(conflictWrite[2].id, conflictWrite[2].getType())
                                        else: 
                                            newSource = hazard.getInput(conflictWrite[2].id)
                                        self.connect(conflictWrite[2], newSource)
                                        found = None
                                        for f in toForward:
                                            if f[0] == conflictRead[2]:
                                                found = f
                                        if found == None:
                                            found = [conflictRead[2], [[condition, newSource]]]
                                            toForward.append(found)
                                        else:
                                            found[1].append([condition, newSource])
                                    else:
                                        stallConditions.append(condition)
            if len(stallConditions) > 0:
                hazard.connect(hazard.multiOr(F'{stage1.id}_stall', stallConditions), hazard.addOutput(F'io.{stage1.id}_stall', 'Bool()'))
                #print(F'      -> stalling {stage1.id} when condition fulfilled')
            for f in toForward:
                target = f[0]
                currentSource = hazard.addInput(F'{target.id}', target.getType())
                #print(F'CurrentSource for {target.parent.id}.{target.id} = {currentSource.id}')
                for alternativeSource in reversed(f[1]):
                    condition = alternativeSource[0]
                    source = alternativeSource[1]
                    #print(F'      -> forwarding {source.parent.id}.{source.id} ({source.getType()}) to {target.parent.id}.{target.id} ({target.getType()}), when {condition.parent.id}.{condition.id}')
                    currentSource = hazard.whenOtherwise(F'{source.id.replace('.', '_')}_to_{target.id.replace('.', '_')}', condition, source, currentSource)
                    #print(F'CurrentSource for {target.parent.id}.{target.id} = {currentSource.id}')
                
                forwardOutput = hazard.addOutput(F'{target.id}_{stage1.id}', target.getType())
                hazard.connect(currentSource, forwardOutput)
                self.connect(forwardOutput, target)

        if display:
            hazard.checkIOConnections()
            hazard.sortSequentialSteps()
            hazard.draw_Grid_network()
        return hazard

    ## automatically construct the pipeline from a number of given stages
    def build(self, stages: list[RV32Stage], pipelined: bool = False, forwarding: bool = False, writeReadBypasses: list[str] = None, display: bool = False):
        if not len(stages) > 0:
            raise ValueError(F'   - FormalRV: Cannot build {string1} Pipeline "{self.id}"{string2}{string3}{string4} - there are no stages')
        string1 = 'single instruction'
        string2 = ''
        string3 = ', with'
        string4 = ''
        if pipelined:
            string1 = 'pipelined'
        if forwarding:
            string2 = ', with forwarding'
        if forwarding and not writeReadBypasses == None:
            string3 = ' and '
        if (not forwarding) and writeReadBypasses == None:
            string3 = ''
        if not writeReadBypasses == None:
            string4 = F'assumed write-read-bypasses for: '
            for s, bypass in enumerate(writeReadBypasses):
                if s > 0:
                    string4 += ', '
                string4 += F'{bypass}'
        print(F'   - FormalRV: Building {string1} Pipeline "{self.id}"{string2}{string3}{string4}')

        resources = []
        requestedResources = []

        #print(F'Number of resources: {len(resources)}')
        #print(F'Number of requested resources: {len(requestedResources)}')

        activeSignals = []

        if pipelined:
            self.buildHazardDetection(stages, forwarding, writeReadBypasses)

        for s, stage in enumerate(stages):
            #print(F' - Stage: {stage.id}:')
            self.addSubModule(stage)
            activeSignals.append(stage.active)
            if s == 0:
                if not self.hazardDetection == None and self.hazardDetection.getOutput(F'io.{stage.id}_stall'):
                    self.connect(self.isAnd(F'{stage.id}_readyAndNoStall', stage.ready, self.isNot(F'{stage.id}_noStall', self.hazardDetection.getOutput(F'io.{stage.id}_stall'))), self.ready)
                else:
                    self.connect(stage.ready, self.ready)
                self.connect(self.enable, stage.enable)
                self.connect(self.false(), stage.lastNOP)
            else:                
                self.connect(stage.ready, stages[s - 1].nextReady)
                if stage.pipelined:
                    resources = self.bufferStage(resources, stages[s - 1], stage)
                else:
                    self.connect(self.isAnd(F'{stage.id}_Enable', stages[s - 1].done, stages[s - 1].valid), stage.enable)
                    self.connect(stages[s - 1].NOP, stage.lastNOP)

            for input in stage.inputs:
                if not self.hazardDetection == None and self.hazardDetection.getOutput(F'{input.id}_{stage.id}'):
                    #print(F'!!!!!! Missing hazard intervention here, replacing input "{input.parent.id}.{input.id}" with "{self.hazardDetection.getInput(input.id).parent.id}.{self.hazardDetection.getInput(input.id).id}"')
                    #print(F'       -> connecting "{self.hazardDetection.getOutput(F'{input.id}_{stage.id}').parent.id}.{self.hazardDetection.getOutput(F'{input.id}_{stage.id}').id}" to "{input.parent.id}.{input.id}"')
                    self.connect(self.hazardDetection.getOutput(F'{input.id}_{stage.id}'), input)
                    input = self.hazardDetection.getInput(input.id)
                if input in stage.stageInputs:
                    found = False
                    for resource in resources:
                        if resource.id == input.id:
                            if resource.getType() == input.getType():
                                found = True
                                self.connect(resource, input)
                                break
                            else:
                                print(F'Warning: matching input "{input.parent.id}.{input.id}" and resource "{resource.parent.id}.{resource.id}" found, but types dont match: "{input.getType()}" and "{resource.getType()}"')
                    if not found:
                        requestedResources.append(input)
                elif not input in stage.stageControlIO:
                    # ## connect to existing inputs or link
                    # for exisiting in self.inputs:
                    #     if exisiting.id == input.id:
                    #         self.connect(exisiting, input)
                    #     else:
                    self.link(input, True)
            
            for output in stage.outputs:
                if output in stage.stageOutputs:
                    requestsFound = []
                    for requestedResource in requestedResources:
                        if requestedResource.id == output.id:
                            if requestedResource.getType() == output.getType():
                                requestsFound.append(requestedResource)
                                self.connect(output, requestedResource)
                                #print(F'Found requested recource: {requestedResource.id}')
                            else:
                                print(F'Warning: matching output "{output.parent.id}.{output.id}" and requested resource "{requestedResource.parent.id}.{requestedResource.id}" found, but types dont match: "{output.getType}" and "{requestedResource.getType}"')
                            break
                    for request in requestsFound:
                        #print(F' -> removing {request.id} from requested resources')
                        requestedResources.remove(request)
                    resources.append(output)
                elif output in stage.conflictOutputs:
                    pass
                    # print(F'!!!!!! Conflict outputs for stages !!')
                elif not output in stage.stageControlIO:
                    resources.append(output)
                    ## connect to existing outputs or link
                    self.link(output, True)

            ## delete all unneeded resources
            newResources = []
            for resource in resources:
                for s2, nextStage in enumerate(stages):
                    if s2 > s:
                        for input in nextStage.stageInputs:
                            if input.id == resource.id:
                                if not resource in newResources:
                                    newResources.append(resource)
            resources = newResources

            #print(F'Number of resources: {len(resources)}')
            #for resource in resources:
            #    print(F'    -> {resource.parent.id}.{resource.id}')
            #print(F'Number of requested resources: {len(requestedResources)}')

        self.connect(self.nextReady, stages[- 1].nextReady)
        self.connect(self.multiOr('active', activeSignals), self.active)
        self.connect(stages[- 1].done, self.done)
        self.connect(stages[- 1].valid, self.valid)
        self.connect(stages[- 1].NOP, self.NOP)
        
        if len(requestedResources) > 0:
            print(F'Warning, still {len(requestedResources)} requested resources missing:')
            for resource in requestedResources:
                print(F'    -> {resource.parent.id}.{resource.id}')
        if len(resources) > 0:
            print(F'Warning, still {len(resources)} resources unused:')
            for resource in resources:
                print(F'    -> {resource.parent.id}.{resource.id}')

        if display:
            self.checkIOConnections()
            self.sortSequentialSteps()
            self.draw_Grid_network()
        return self
        
## Generic pipeline proof class to build a number of standard control signal proofs
class RV32PipelineProof(formalHandshake_Hardware.Hardware_Module):
    def __init__(self, id: str, pipeline: RV32Pipeline, project: FormalHandshakeHardwareProject):
        super().__init__(id)
        self.pipeline = pipeline
        self.addSubModule(pipeline)
        self.project = project

    ## liveness proof
    def build_livenessProof(self, maxCycles: bool, specificCycles: int, pipelined: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        id = F'{self.pipeline.id}_liveness'
        self.link(self.pipeline.inputs, True)

        if pipelined:
            print(F'- pipelined: Track/Count Enables at least numStages times -> assert Done or NOP')
            raise NotImplementedError()
        else:
            validStart = self.isAnd('validStart', self.getInput('io.enable'), self.pipeline.getOutput('io.ready'))
            validFinish = self.isOr('validFinish', self.pipeline.getOutput('io.done'), self.pipeline.getOutput('io.nop'))
            self.assumption(self.getInput('io.nextReady'))
            self.liveness(id, validStart, validFinish, maxCycles, specificCycles, pipelined, initialReset)
            #self.assumption(self.isNot('noNop', self.pipeline.getOutput('io.nop')))
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (maxCycles + 3), None, priority, overwrite, False)
        return self
       
    ## only done, when active
    def build_activeProof(self, maxCycles: bool, pipelined: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            self.link(self.pipeline.inputs, True)
            self.link([self.pipeline.active, self.pipeline.done], True)
            self.cover(self.getOutput('io.done'))
            self.assertion(self.getOutput('io.active')).on(self.getOutput('io.done'))
            
            if initialReset:
                self.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (maxCycles + 3), None, priority, overwrite, False)
        return self
   
    ## ready when inactive or done
    def build_readyProof(self, maxCycles: bool, pipelined: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            self.link(self.pipeline.inputs, True)
            self.assumption(self.getInput('io.nextReady'))
            self.assumption(self.isNot('notEnableWhenDone', self.equals('enableWhenDone', self.getInput('io.enable'), self.pipeline.getOutput('io.done'))))
            readyExpected = self.multiAnd('readyExpected', [self.getInput('io.nextReady'), self.isOr('internalReady', self.isNot('inactive', self.pipeline.active), self.isOr('finishedInstruction', self.pipeline.done, self.pipeline.NOP))])
            valid = self.isOr('valid', self.isAnd('readyWhenExpected', self.pipeline.ready, readyExpected), self.isAnd('notReadyWhenNotExpected', self.isNot('notReady', self.pipeline.ready), self.isNot('notReadyExpected', readyExpected)))
            noReset = self.isNot('noReset', self.reset())
            self.cover(noReset)
            self.assertion(valid).on(noReset)
            if initialReset:
                self.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (maxCycles + 3), None, priority, overwrite, False)
        return self
    
    ## NOP Proof
    def build_NOPProof(self, maxCycles: bool, pipelined: bool, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            self.link(self.pipeline.inputs, True)
            self.link(self.pipeline.NOP, True)
            invalid = self.isNot('invalid', self.pipeline.valid)
            invalidDone = self.isAnd('invalidDone', self.pipeline.done, invalid)
            nopExpected = invalidDone
            self.assertion(self.getOutput('io.nop')).on(nopExpected)
            if initialReset:
                self.pipeline.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (maxCycles + 3), None, priority, overwrite, False)
        return self

    ## Functional Proofs:
    ## Fetch Proof
    def build_fetchProof(self, referenceISA: formalHandshake_Hardware.Hardware_Module, maxInstructionCycles: bool, pipelined: bool, numStages: int, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            linkInputs = [
                self.pipeline.getInput('io.i_mem_bus_reqAck'), 
                self.pipeline.getInput('io.i_mem_bus_rdata'),
                self.pipeline.getInput('io.reg_rs1_data'),
                self.pipeline.getInput('io.reg_rs2_data'),
                self.pipeline.getInput('io.d_mem_bus_reqAck'),
                self.pipeline.getInput('io.d_mem_bus_rdata'),
                ]
            self.link(linkInputs, True)

            pc = formalHandshake_Hardware.LoopedReg('pc', self, 'Bits(32 bits)', 'B(4, 32 bits)')
            self.connect(pc.value(), self.pipeline.getInput('io.pc_readValue'))
            self.connect(self.pipeline.getOutput('io.pc_writeBackValid'), pc.store())
            self.connect(self.pipeline.getOutput('io.pc_writeBackValue'), pc.input())

            self.connect(self.true(), self.pipeline.getInput('io.nextReady'))
            enable = formalHandshake_Hardware.Register('enable', self, 'Bool()', 'True')
            pipelineDoneOrNop = self.isOr('pipelineDoneOrNop', self.pipeline.done, self.pipeline.NOP)
            self.connect(pipelineDoneOrNop, enable.input())
            self.connect(enable, self.pipeline.enable)

            validValues = []

            fifoPc = formalHandshake_Hardware.FIFO('fifoPc', self, 'Bits(32 bits)', 2)
            ## assert that never full
            self.assertion('!fifoPc.io.full')
            ## collect fetched pc
            self.connect(self.pipeline.getOutput('io.i_mem_bus_req'), fifoPc.write)
            self.connect(self.pipeline.getOutput('io.i_mem_bus_address'), fifoPc.write_data)
            instructionExecuted = self.pipeline.getOutput('verification.instructionValid') 
            self.connect(instructionExecuted, fifoPc.read)
            expectedPc = fifoPc.read_data
            self.connect(expectedPc, self.addOutput('verification.expectedPc', 'Bits(32 bits)'))
            executedPc = self.pipeline.getOutput('verification.pc')
            self.connect(executedPc, self.addOutput('verification.executedPc', 'Bits(32 bits)'))
            ## compare fetched pc to executed pc
            pcValid = self.equals('pcValid', expectedPc, executedPc)
            validValues.append(pcValid)
            
            valid = self.addOutput('verification.valid', 'Bool()')
            self.connect(self.multiAnd('valid', validValues), valid)
            instructionExecuted = self.addOutput('verification.instructionExecuted', 'Bool()')
            self.connect(self.pipeline.done, instructionExecuted)
            self.cover(instructionExecuted)
            self.assertion(valid).on(instructionExecuted)

            if initialReset:
                self.pipeline.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (2*maxInstructionCycles + 3), None, priority, overwrite, False)


        # self.checkIOConnections()
        # self.sortSequentialSteps()
        # self.draw_Grid_network()
        return self

    ## Exception Proof
    def build_exceptionProof(self, referenceISA: formalHandshake_Hardware.Hardware_Module, maxInstructionCycles: bool, pipelined: bool, numStages: int, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            linkInputs = [
                self.pipeline.getInput('io.i_mem_bus_reqAck'), 
                self.pipeline.getInput('io.i_mem_bus_rdata'),
                self.pipeline.getInput('io.d_mem_bus_reqAck'),
                self.pipeline.getInput('io.d_mem_bus_rdata'),
                ]
            self.link(linkInputs, True)

            pc = formalHandshake_Hardware.LoopedReg('pc', self, 'Bits(32 bits)', 'B(4, 32 bits)')
            self.connect(pc.value(), self.pipeline.getInput('io.pc_readValue'))
            self.connect(self.pipeline.getOutput('io.pc_writeBackValid'), pc.store())
            self.connect(self.pipeline.getOutput('io.pc_writeBackValue'), pc.input())

            self.connect(self.true(), self.pipeline.getInput('io.nextReady'))
            enable = formalHandshake_Hardware.Register('enable', self, 'Bool()', 'True')
            pipelineDoneOrNop = self.isOr('pipelineDoneOrNop', self.pipeline.done, self.pipeline.NOP)
            self.connect(pipelineDoneOrNop, enable.input())
            self.connect(enable, self.pipeline.enable)

            regfile = build_RV32RegFile('regfile')
            self.addSubModule(regfile)

            self.connectManual(self.pipeline.getOutput('io.reg_rs1'), regfile.getInput('rs1'), F'{self.pipeline.id}.io.reg_rs1.asUInt')
            self.connect(regfile.getOutput('rs1_data'), self.pipeline.getInput('io.reg_rs1_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rs2'), regfile.getInput('rs2'), F'{self.pipeline.id}.io.reg_rs2.asUInt')
            self.connect(regfile.getOutput('rs2_data'), self.pipeline.getInput('io.reg_rs2_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rd'), regfile.getInput('rd'), F'{self.pipeline.id}.io.reg_rd.asUInt')
            self.connect(self.pipeline.getOutput('io.reg_rd_data'), regfile.getInput('rd_data'))
            self.connect(self.pipeline.getOutput('io.reg_WriteBack'), regfile.getInput('writeEnable'))

            self.addSubModule(referenceISA)
            
            executedInstruction = self.pipeline.getOutput('verification.instruction')
            self.connect(executedInstruction, referenceISA.getInput('io.instruction'))
            executedPc = self.pipeline.getOutput('verification.pc')
            self.connectManual(executedPc, referenceISA.getInput('io.pc'), F'{self.pipeline.id}.verification.pc.asUInt')
            memeReadData = self.pipeline.getOutput('verification.mem_rdata')
            self.connect(memeReadData, referenceISA.getInput('io.memRead_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_mepc'))

            self.connect(self.pipeline.getOutput('verification.rs1_data'), referenceISA.getInput('io.rs1_data'))
            self.connect(self.pipeline.getOutput('verification.rs2_data'), referenceISA.getInput('io.rs2_data'))

            exception = self.pipeline.getOutput('verification.exception')
            exceptionExpected = referenceISA.getOutput('io.trap')

            valid = self.addOutput('verification.valid', 'Bool()')
            instructionExecuted = self.addOutput('verification.instructionExecuted', 'Bool()')
            self.connect(self.pipeline.done, instructionExecuted)
            isValid = self.whenOtherwise('isValid', self.pipeline.done, self.equals('exceptionMatch', exception, exceptionExpected), self.true())
            self.connect(isValid, valid)

            self.cover(instructionExecuted)
            self.assertion(valid)
            

            if initialReset:
                self.pipeline.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (2*maxInstructionCycles + 3), None, priority, overwrite, False)


        # self.checkIOConnections()
        # self.sortSequentialSteps()
        # self.draw_Grid_network()
        return self

    ## Pc Proof
    def build_pcProof(self, referenceISA: formalHandshake_Hardware.Hardware_Module, maxInstructionCycles: bool, pipelined: bool, numStages: int, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            linkInputs = [
                self.pipeline.getInput('io.i_mem_bus_reqAck'), 
                self.pipeline.getInput('io.i_mem_bus_rdata'),
                self.pipeline.getInput('io.d_mem_bus_reqAck'),
                self.pipeline.getInput('io.d_mem_bus_rdata'),
                ]
            self.link(linkInputs, True)

            pc = formalHandshake_Hardware.LoopedReg('pc', self, 'Bits(32 bits)', 'B(4, 32 bits)')
            self.connect(pc.value(), self.pipeline.getInput('io.pc_readValue'))
            self.connect(self.pipeline.getOutput('io.pc_writeBackValid'), pc.store())
            self.connect(self.pipeline.getOutput('io.pc_writeBackValue'), pc.input())

            self.connect(self.true(), self.pipeline.getInput('io.nextReady'))
            enable = formalHandshake_Hardware.Register('enable', self, 'Bool()', 'True')
            pipelineDoneOrNop = self.isOr('pipelineDoneOrNop', self.pipeline.done, self.pipeline.NOP)
            self.connect(pipelineDoneOrNop, enable.input())
            self.connect(enable, self.pipeline.enable)

            regfile = build_RV32RegFile('regfile')
            self.addSubModule(regfile)

            self.connectManual(self.pipeline.getOutput('io.reg_rs1'), regfile.getInput('rs1'), F'{self.pipeline.id}.io.reg_rs1.asUInt')
            self.connect(regfile.getOutput('rs1_data'), self.pipeline.getInput('io.reg_rs1_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rs2'), regfile.getInput('rs2'), F'{self.pipeline.id}.io.reg_rs2.asUInt')
            self.connect(regfile.getOutput('rs2_data'), self.pipeline.getInput('io.reg_rs2_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rd'), regfile.getInput('rd'), F'{self.pipeline.id}.io.reg_rd.asUInt')
            self.connect(self.pipeline.getOutput('io.reg_rd_data'), regfile.getInput('rd_data'))
            self.connect(self.pipeline.getOutput('io.reg_WriteBack'), regfile.getInput('writeEnable'))

            self.addSubModule(referenceISA)
            
            executedInstruction = self.pipeline.getOutput('verification.instruction')
            self.connect(executedInstruction, referenceISA.getInput('io.instruction'))
            executedPc = self.pipeline.getOutput('verification.pc')
            self.connectManual(executedPc, referenceISA.getInput('io.pc'), F'{self.pipeline.id}.verification.pc.asUInt')
            memeReadData = self.pipeline.getOutput('verification.mem_rdata')
            self.connect(memeReadData, referenceISA.getInput('io.memRead_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_mepc'))

            self.connect(self.pipeline.getOutput('verification.rs1_data'), referenceISA.getInput('io.rs1_data'))
            self.connect(self.pipeline.getOutput('verification.rs2_data'), referenceISA.getInput('io.rs2_data'))

            expectedNextPcCalculator = formalHandshake_Hardware.Hardware_Module('expectedNextPcCalculator')
            self.addSubModule(expectedNextPcCalculator)
            pc = expectedNextPcCalculator.addInput('pc', 'Bits(32 bits)')
            jump = expectedNextPcCalculator.addInput('jump', 'Bool()')
            jumpAddress = expectedNextPcCalculator.addInput('jumpAddress', 'Bits(32 bits)')
            expectedNextPc = expectedNextPcCalculator.addOutput('expectedNextPc', 'Bits(32 bits)')

            self.connect(executedPc, pc)
            self.connect(referenceISA.getOutput('io.jump'), jump)
            self.connectManual(referenceISA.getOutput('io.jumpAddress'), jumpAddress, F'{referenceISA.id}.io.jumpAddress.asBits')
            pc4 = formalHandshake_Hardware.AdderUnsigned('pc4', expectedNextPcCalculator, 32, pc, expectedNextPcCalculator.const('Bits(32 bits)', 'B(4, 32 bits)'))

            expectedNextPcCalculator.connect(expectedNextPcCalculator.whenOtherwise('expectedPc', jump, jumpAddress, pc4), expectedNextPc)
            nextExecutedPc = self.pipeline.getOutput('verification.nextPc')

            valid = self.addOutput('verification.valid', 'Bool()')
            instructionExecuted = self.addOutput('verification.instructionExecuted', 'Bool()')
            self.connect(self.pipeline.done, instructionExecuted)

            ## ? Traphandler ?!
            expectedPc = self.whenOtherwise('expectedPc', referenceISA.getOutput('io.trap'), self.const('Bits(32 bits)', 'B(0, 32 bits)'), expectedNextPc)
            
            isValid = self.whenOtherwise('isValid', self.pipeline.done, self.equals('nextPcMatch', nextExecutedPc, expectedPc), self.true())
            self.connect(isValid, valid)

            self.cover(instructionExecuted)
            self.assertion(valid)

            if initialReset:
                self.pipeline.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (2*maxInstructionCycles + 3), None, priority, overwrite, False)

        # self.checkIOConnections()
        # self.sortSequentialSteps()
        # self.draw_Grid_network()
        return self

    ## Reg Proof
    def build_regProof(self, referenceISA: formalHandshake_Hardware.Hardware_Module, maxInstructionCycles: bool, pipelined: bool, numStages: int, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            linkInputs = [
                self.pipeline.getInput('io.i_mem_bus_reqAck'), 
                self.pipeline.getInput('io.i_mem_bus_rdata'),
                self.pipeline.getInput('io.d_mem_bus_reqAck'),
                self.pipeline.getInput('io.d_mem_bus_rdata'),
                ]
            self.link(linkInputs, True)

            pc = formalHandshake_Hardware.LoopedReg('pc', self, 'Bits(32 bits)', 'B(4, 32 bits)')
            self.connect(pc.value(), self.pipeline.getInput('io.pc_readValue'))
            self.connect(self.pipeline.getOutput('io.pc_writeBackValid'), pc.store())
            self.connect(self.pipeline.getOutput('io.pc_writeBackValue'), pc.input())

            self.connect(self.true(), self.pipeline.getInput('io.nextReady'))
            enable = formalHandshake_Hardware.Register('enable', self, 'Bool()', 'True')
            pipelineDoneOrNop = self.isOr('pipelineDoneOrNop', self.pipeline.done, self.pipeline.NOP)
            self.connect(pipelineDoneOrNop, enable.input())
            self.connect(enable, self.pipeline.enable)

            regfile = build_RV32RegFile('regfile')
            self.addSubModule(regfile)

            self.connectManual(self.pipeline.getOutput('io.reg_rs1'), regfile.getInput('rs1'), F'{self.pipeline.id}.io.reg_rs1.asUInt')
            self.connect(regfile.getOutput('rs1_data'), self.pipeline.getInput('io.reg_rs1_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rs2'), regfile.getInput('rs2'), F'{self.pipeline.id}.io.reg_rs2.asUInt')
            self.connect(regfile.getOutput('rs2_data'), self.pipeline.getInput('io.reg_rs2_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rd'), regfile.getInput('rd'), F'{self.pipeline.id}.io.reg_rd.asUInt')
            self.connect(self.pipeline.getOutput('io.reg_rd_data'), regfile.getInput('rd_data'))
            self.connect(self.pipeline.getOutput('io.reg_WriteBack'), regfile.getInput('writeEnable'))

            self.addSubModule(referenceISA)
            
            executedInstruction = self.pipeline.getOutput('verification.instruction')
            self.connect(executedInstruction, referenceISA.getInput('io.instruction'))
            executedPc = self.pipeline.getOutput('verification.pc')
            self.connectManual(executedPc, referenceISA.getInput('io.pc'), F'{self.pipeline.id}.verification.pc.asUInt')
            memeReadData = self.pipeline.getOutput('verification.mem_rdata')
            self.connect(memeReadData, referenceISA.getInput('io.memRead_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_mepc'))

            self.connect(self.pipeline.getOutput('verification.rs1_data'), referenceISA.getInput('io.rs1_data'))
            self.connect(self.pipeline.getOutput('verification.rs2_data'), referenceISA.getInput('io.rs2_data'))

            ## ?!
            expectedWrite = referenceISA.getOutput('io.regWrite')
            expectedWriteReg = referenceISA.getOutput('io.rd')
            expectedWriteValue = referenceISA.getOutput('io.regWrite_data')

            executedWrite = self.pipeline.getOutput('verification.rdWrite')
            executedWriteReg = self.pipeline.getOutput('verification.rd')
            executedWriteValue = self.pipeline.getOutput('verification.rd_data')

            writeMatch = self.equals('writeMatch', expectedWrite, executedWrite)

            writeRegMatch = formalHandshake_Hardware.Hardware_Function('writeRegMatch', self, 'Bool()', 0)
            in1 = formalHandshake_Hardware.Hardware_IOPort('expectedReg', writeRegMatch, F'UInt(5 bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('executedReg', writeRegMatch, F'Bits(5 bits)')
            writeRegMatch.inputs.append(in1)
            writeRegMatch.inputs.append(in2)
            self.connect(expectedWriteReg, in1)
            self.connect(executedWriteReg, in2)
            writeRegMatch.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, self)}.asBits === {formalHandshake_Hardware.getSpinalHDLSource(in2, self)}'
            writeRegValid = self.whenOtherwise('writeRegValid', expectedWrite, writeRegMatch, self.true())

            writeValueMatch = self.equals('writeValueMatch', expectedWriteValue, executedWriteValue)
            writeValueValid = self.whenOtherwise('writeValueValid', expectedWrite, writeValueMatch, self.true())

            validSources = [writeMatch, writeRegValid, writeValueValid]

            valid = self.addOutput('verification.valid', 'Bool()')
            instructionExecuted = self.addOutput('verification.instructionExecuted', 'Bool()')
            self.connect(self.pipeline.done, instructionExecuted)
            isValid = self.whenOtherwise('isValid', self.pipeline.done, self.multiAnd('validSources', validSources), self.true())
            self.connect(isValid, valid)

            self.cover(instructionExecuted)
            self.assertion(valid)

            if initialReset:
                self.pipeline.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (2*maxInstructionCycles + 3), None, priority, overwrite, False)

        # self.checkIOConnections()
        # self.sortSequentialSteps()
        # self.draw_Grid_network()
        return self
    
    ## mem Proof
    def build_memProof(self, referenceISA: formalHandshake_Hardware.Hardware_Module, maxInstructionCycles: bool, pipelined: bool, numStages: int, initialReset: bool = True, priority: bool = False, overwrite: bool = True, add: bool = False):
        if pipelined:
            raise NotImplementedError()
        else:
            linkInputs = [
                self.pipeline.getInput('io.i_mem_bus_reqAck'),
                self.pipeline.getInput('io.d_mem_bus_reqAck'),
                self.pipeline.getInput('io.d_mem_bus_rdata'),
                ]
            self.link(linkInputs, True)

            pc = formalHandshake_Hardware.LoopedReg('pc', self, 'Bits(32 bits)', 'B(4, 32 bits)')
            self.connect(pc.value(), self.pipeline.getInput('io.pc_readValue'))
            self.connect(self.pipeline.getOutput('io.pc_writeBackValid'), pc.store())
            self.connect(self.pipeline.getOutput('io.pc_writeBackValue'), pc.input())

            i_mem = formalHandshake_Hardware.LoopedReg('i_mem', self, 'Bits(32 bits)')
            self.connect(self.addInput('io.i_mem_bus_rdata', 'Bits(32 bits)'), i_mem.input())
            self.connect(self.pipeline.getOutput('io.i_mem_bus_req'), i_mem.store())
            self.connect(i_mem.value(), self.pipeline.getInput('io.i_mem_bus_rdata'))

            self.connect(self.true(), self.pipeline.getInput('io.nextReady'))
            enable = formalHandshake_Hardware.Register('enable', self, 'Bool()', 'True')
            pipelineDoneOrNop = self.isOr('pipelineDoneOrNop', self.pipeline.done, self.pipeline.NOP)
            self.connect(pipelineDoneOrNop, enable.input())
            self.connect(enable, self.pipeline.enable)

            regfile = build_RV32RegFile('regfile')
            self.addSubModule(regfile)

            self.connectManual(self.pipeline.getOutput('io.reg_rs1'), regfile.getInput('rs1'), F'{self.pipeline.id}.io.reg_rs1.asUInt')
            self.connect(regfile.getOutput('rs1_data'), self.pipeline.getInput('io.reg_rs1_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rs2'), regfile.getInput('rs2'), F'{self.pipeline.id}.io.reg_rs2.asUInt')
            self.connect(regfile.getOutput('rs2_data'), self.pipeline.getInput('io.reg_rs2_data'))
            self.connectManual(self.pipeline.getOutput('io.reg_rd'), regfile.getInput('rd'), F'{self.pipeline.id}.io.reg_rd.asUInt')
            self.connect(self.pipeline.getOutput('io.reg_rd_data'), regfile.getInput('rd_data'))
            self.connect(self.pipeline.getOutput('io.reg_WriteBack'), regfile.getInput('writeEnable'))

            self.addSubModule(referenceISA)

            executedInstruction = self.pipeline.getOutput('verification.instruction')
            self.connect(executedInstruction, referenceISA.getInput('io.instruction'))
            executedPc = self.pipeline.getOutput('verification.pc')
            self.connectManual(executedPc, referenceISA.getInput('io.pc'), F'{self.pipeline.id}.verification.pc.asUInt')
            memeReadData = self.pipeline.getOutput('verification.mem_rdata')
            self.connect(memeReadData, referenceISA.getInput('io.memRead_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_data'))
            self.connect(self.const('Bits(32 bits)', 'B(0, 32 bits)'), referenceISA.getInput('io.csr_mepc'))

            self.connect(self.pipeline.getOutput('verification.rs1_data'), referenceISA.getInput('io.rs1_data'))
            self.connect(self.pipeline.getOutput('verification.rs2_data'), referenceISA.getInput('io.rs2_data'))

            expectedMemActive = referenceISA.getOutput('io.memActive')
            executedMemActive = self.pipeline.getOutput('verification.memUsed')
            activeMatch = self.equals('activeMatch', expectedMemActive, executedMemActive)

            expectedMemAddress = referenceISA.getOutput('io.memAddress')
            executedMemAddress = self.pipeline.getOutput('verification.memAddress')
            addressMatch = formalHandshake_Hardware.Hardware_Function('addressMatch', self, 'Bool()', 0)
            in1 = formalHandshake_Hardware.Hardware_IOPort('expectedMemAddress', addressMatch, F'UInt(32 bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('executedMemAddress', addressMatch, F'Bits(32 bits)')
            addressMatch.inputs.append(in1)
            addressMatch.inputs.append(in2)
            self.connect(expectedMemAddress, in1)
            self.connect(executedMemAddress, in2)
            addressMatch.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, self)}.asBits === {formalHandshake_Hardware.getSpinalHDLSource(in2, self)}'
            addressMatchValid = self.whenOtherwise('addressMatchValid', expectedMemActive, addressMatch, self.true())

            expectedMemWrite = referenceISA.getOutput('io.memWrite')
            executedMemWrite = self.pipeline.getOutput('verification.memWrite')
            memWriteMatch = self.equals('memWriteMatch', expectedMemWrite, executedMemWrite)
            memWriteMatchValid = self.whenOtherwise('writeMatchValid', expectedMemActive, memWriteMatch, self.true())

            expectedMemSize = referenceISA.getOutput('io.memSize')
            executedMemSize = self.pipeline.getOutput('verification.memSize')
            
            memSizeMatch = formalHandshake_Hardware.Hardware_Function('memSizeMatch', self, 'Bool()', 0)
            in1 = formalHandshake_Hardware.Hardware_IOPort('expectedMemSize', memSizeMatch, F'Bits(2 bits)')
            in2 = formalHandshake_Hardware.Hardware_IOPort('executedMemSize', memSizeMatch, F'UInt(2 bits)')
            memSizeMatch.inputs.append(in1)
            memSizeMatch.inputs.append(in2)
            self.connect(expectedMemSize, in1)
            self.connect(executedMemSize, in2)
            memSizeMatch.definition = F'{formalHandshake_Hardware.getSpinalHDLSource(in1, self)}.asUInt === {formalHandshake_Hardware.getSpinalHDLSource(in2, self)}'
            memSizeMatchValid = self.whenOtherwise('memSizeMatchValid', expectedMemActive, memSizeMatch, self.true())

            expectedMemWriteData = referenceISA.getOutput('io.memWrite_data')
            executedMemWriteData = self.pipeline.getOutput('verification.mem_wdata')
            writeDataMatch = self.equals('writeDataMatch', expectedMemWriteData, executedMemWriteData)
            writeDataMatchValid = self.whenOtherwise('writeDataMatchValid', expectedMemActive, writeDataMatch, self.true())

            validSources = [activeMatch, addressMatchValid, memWriteMatchValid, memSizeMatchValid, writeDataMatchValid]

            valid = self.addOutput('verification.valid', 'Bool()')
            instructionExecuted = self.addOutput('verification.instructionExecuted', 'Bool()')
            self.connect(self.pipeline.done, instructionExecuted)
            isValid = self.whenOtherwise('isValid', self.pipeline.done, self.multiAnd('validSources', validSources), self.true())
            self.connect(isValid, valid)

            self.cover(instructionExecuted)
            self.assertion(valid)

            if initialReset:
                self.pipeline.assumeInitialReset()
            if add:
                self.project.addSymbiYosysProof(self, self.pipeline.id, (2*maxInstructionCycles + 3), None, priority, overwrite, False)

        # self.checkIOConnections()
        # self.sortSequentialSteps()
        # self.draw_Grid_network()
        return self
    
    
## Returns a proposed RISC-V Fetch Stage
def build_RV32FetchStage(id: str, pipelined: bool, memStallAllowed: bool, memReadDataDelayed: bool = True, display: bool = False):
    print(F'   - FormalRV: Building rv32 fetch stage "{id}", memory stalls allowed: {memStallAllowed}')
    stage = RV32Stage(id, pipelined)
    
    if memReadDataDelayed == False:
        raise NotImplementedError(F'Need to implement mem read data not delayed!')

    pc = stage.addInput('io.pc_readValue', 'Bits(32 bits)')
    stage.connect(pc, stage.addStageOutput('io.pc', 'Bits(32 bits)'))
    
    ## i_mem_bus
    memReq = stage.addOutput('io.i_mem_bus_req', 'Bool()')
    memAddress = stage.addOutput('io.i_mem_bus_address', 'Bits(32 bits)')
    memReqAck = stage.addInput('io.i_mem_bus_reqAck', 'Bool()') ## ?!
    ## memValid = stage.addInput('io.i_mem_bus_valid', 'Bool()') ## ?!
    memReadData = stage.addInput('io.i_mem_bus_rdata', 'Bits(32 bits)')

    stage.connect(stage.enable, memReq)
    stage.connect(pc, memAddress)
    stage.connect(memReadData, stage.addStageOutput('io.instruction', 'Bits(32 bits)', memReadDataDelayed))

    pcInc = formalHandshake_Hardware.AdderUnsigned('pcInc', stage, 32, pc, stage.const('Bits(32 bits)', 'B(4, 32 bits)'))
    stage.connect(pcInc, stage.addStageOutput('io.pcInc', 'Bits(32 bits)'))

    jump = stage.addStageInput('io.jump', 'Bool()')
    jumpAddress = stage.addStageInput('io.jumpAddress', 'Bits(32 bits)')
    if pipelined:
        pcValid = stage.whenOtherwise('pcValid', jump, stage.equals('correctAddress', pc, jumpAddress), stage.true())
    nextPc = stage.whenOtherwise('nextPc', jump, jumpAddress, pcInc)
    stage.connect(nextPc, stage.addOutput('io.pc_writeBackValue', 'Bits(32 bits)'))
    ## stage.connect(memReqAck, stage.addOutput('io.pc_WriteBackValid', 'Bool()')) ## ?!

    if not memStallAllowed:
        raise NotImplementedError()

    if pipelined:
        stage.stallingOn(memReqAck)
        stage.validOn(pcValid)
    else:
        pastEnabled = formalHandshake_Hardware.Register('pastEnabled', stage, 'Bool()', 'False')
        enabled = stage.isOr('enabled', pastEnabled, stage.enable)
        stage.connect(stage.isAnd('enabledNoAck', stage.isNot('notAck', memReqAck), enabled), pastEnabled.input())
        wasAcknowledged = formalHandshake_Hardware.Register('wasAcknowledged', stage, 'Bool()', 'False')
        stage.connect(stage.isAnd('acknowledgedReq', memReqAck, enabled), wasAcknowledged.input())
        stage.stallingOn(wasAcknowledged)
        stage.validOn(wasAcknowledged)

    ### connecting pc_WriteBackValid to source of own done signal
    # stage.connect(stage.done.source, stage.addOutput('io.pc_writeBackValid', 'Bool()'))
    ## setting pc_WriteBackValid when pipeline ready for next instruction
    stage.connect(stage.ready.source, stage.addOutput('io.pc_writeBackValid', 'Bool()'))

    if display:
        stage.checkIOConnections()
        stage.sortSequentialSteps()
        stage.draw_Grid_network()
    return stage

## Returns a proposed RISC-V Decode Stage
def build_RV32DecodeStage(id: str, pipelined: bool, instructionSet: InstructionSet,
                          instructionDecomposition: formalHandshake_Hardware.Hardware_Module = None,
                          decoderLogic: formalHandshake_Hardware.Hardware_Module = None,
                          jumpAddressCalculator: formalHandshake_Hardware.Hardware_Module = None,
                          branchUnit: formalHandshake_Hardware.Hardware_Module = None,
                          memoryAddressCalculator: formalHandshake_Hardware.Hardware_Module = None,
                          trapHandler: formalHandshake_Hardware.Hardware_Module = None,
                          display: bool = False):
    print(F'   - FormalRV: Building rv32 decode stage "{id}", with instruction set: "{instructionSet.id}"')
    stage = RV32Stage(id, pipelined)
    instruction = stage.addStageInput('io.instruction', 'Bits(32 bits)')

    ## instruction decomposition
    def rv32InstructionDecomp(id: str, display: bool = False):
        decomp = formalHandshake_Hardware.Hardware_Module(id)
        instructionIn = decomp.addInput('io.instruction', 'Bits(32 bits)')
        opcode = decomp.connectManual(instructionIn, decomp.addOutput('io.opcode', 'Bits(7 bits)'), 'io.instruction(6 downto 0)')
        f3 = decomp.connectManual(instructionIn, decomp.addOutput('io.f3', 'Bits(3 bits)'), 'io.instruction(14 downto 12)')
        f7 = decomp.connectManual(instructionIn, decomp.addOutput('io.f7', 'Bits(7 bits)'), 'io.instruction(31 downto 25)')
        f12 = decomp.connectManual(instructionIn, decomp.addOutput('io.f12', 'Bits(12 bits)'), 'io.instruction(31 downto 20)')
        rs1 = decomp.connectManual(instructionIn, decomp.addOutput('io.rs1', 'Bits(5 bits)'), 'io.instruction(19 downto 15)')
        rs2 = decomp.connectManual(instructionIn, decomp.addOutput('io.rs2', 'Bits(5 bits)'), 'io.instruction(24 downto 20)')
        rd = decomp.connectManual(instructionIn, decomp.addOutput('io.rd', 'Bits(5 bits)'), 'io.instruction(11 downto 7)')
        shamt = decomp.connectManual(instructionIn, decomp.addOutput('io.shamt', 'Bits(32 bits)'), 'B(0, 27 bits) ## io.instruction(24 downto 20)')
        I = decomp.connectManual(instructionIn, decomp.addOutput('io.I', 'Bits(32 bits)'), 'S(io.instruction(31), 21 bits) ## io.instruction(30 downto 25) ## io.instruction(24 downto 21) ## io.instruction(20)')
        B = decomp.connectManual(instructionIn, decomp.addOutput('io.B', 'Bits(32 bits)'), 'S(io.instruction(31), 20 bits) ## io.instruction(7) ## io.instruction(30 downto 25) ## io.instruction(11 downto 8) ## B(0,1 bit)')
        S = decomp.connectManual(instructionIn, decomp.addOutput('io.S', 'Bits(32 bits)'), 'S(io.instruction(31), 21 bits) ## io.instruction(30 downto 25) ## io.instruction(11 downto 8) ## io.instruction(7)')
        U = decomp.connectManual(instructionIn, decomp.addOutput('io.U', 'Bits(32 bits)'), 'io.instruction(31) ## io.instruction(30 downto 20) ## io.instruction(19 downto 12) ## B(0, 12 bits)')
        J = decomp.connectManual(instructionIn, decomp.addOutput('io.J', 'Bits(32 bits)'), 'S(B(io.instruction(31) ## io.instruction(19 downto 12) ## io.instruction(20) ## io.instruction(30 downto 25) ## io.instruction(24 downto 21) ## B(0, 1 bit)),32 bits).asBits')
        #csrAddress := io.instruction(31 downto 20).asUInt

        if display:
            decomp.checkIOConnections()
            decomp.sortSequentialSteps()
            decomp.draw_Grid_network()
        return decomp

    if instructionDecomposition == None:
        decomp = stage.addSubModule(rv32InstructionDecomp('decomp'))
    else:
        decomp = stage.addSubModule(instructionDecomposition)
    
    stage.connect(instruction, decomp.getInput('io.instruction'))

    ## register loads
    rs1 = decomp.getOutput('io.rs1')
    rs2 = decomp.getOutput('io.rs2')
    stage.connect(rs1, stage.addOutput('io.reg_rs1', 'Bits(5 bits)'))
    stage.connect(rs2, stage.addOutput('io.reg_rs2', 'Bits(5 bits)'))
    rs1_data = stage.wire('rs1_data', stage.addInput('io.reg_rs1_data', 'Bits(32 bits)'))
    rs2_data = stage.wire('rs2_data', stage.addInput('io.reg_rs2_data', 'Bits(32 bits)'))

    ## decoder logic
    def build_RV32_Decoder_Logic(id: str, instructionSet: InstructionSet, display: bool = False):
        print(F'   - FormalRV: Building rv32 decoder logic "{id}" with instruction set "{instructionSet.id}"')
        decoder = formalHandshake_Hardware.Hardware_Module(id)

        f3Found = False
        f7Found = False
        f12Found = False

        for family in instructionSet.opcodeFamilies:
            for instruction in family.instructions:
                if not instruction.parameters['f3'] == None:
                    f3Found = True
                if not instruction.parameters['f7'] == None:
                    f7Found = True
                if not instruction.parameters['f12'] == None:
                    f12Found = True
                    print(F'f12Found')

        opcode = decoder.addInput('io.opcode', 'Bits(7 bits)')
        if f3Found:
            f3 = decoder.addInput('io.f3', 'Bits(3 bits)')
        if f7Found:
            f7 = decoder.addInput('io.f7', 'Bits(7 bits)')
        if f12Found:
            f12 = decoder.addInput('io.f12', 'Bits(12 bits)')

        decodeFunctions = []
        outputsToGenerate = []

        for key in instructionSet.requirements: #['jumpAddressSource', ]:  #['jumpAddressSource', 'jump','valid']:  #
            keyEncoding = instructionSet.getParamDefinition(key, ['f3', 'f7', 'f12'])
            if len(keyEncoding) > 0:
                values = []
                conditions = []
                conditionsName = [] ## ?!
                for encoding in keyEncoding:
                    value = encoding[1]
                    if not value in values:
                        values.append(value)
                        conditions.append([])
                        conditionsName.append([])
                if len(values) > 0: #1: ##?!
                    bitLength = (len(values)).bit_length()
                    outputType = F'UInt({bitLength} bits)'
                    funcValPairs = []
                    for v, value in enumerate(values):
                        for encoding in keyEncoding:
                            if encoding[1] == value:
                                conditionFunctions = []
                                condition = []  ## ?
                                names = []
                                names.append(['opcode', encoding[0][0]])
                                if not encoding[0][1] == None:
                                    names.append(['f3', encoding[0][1]])
                                if not encoding[0][2] == None:
                                    names.append(['f7', encoding[0][2]])
                                if not encoding[0][3] == None:
                                    names.append(['f12', encoding[0][3]])
                                for name in names:
                                    found = False
                                    for function in decodeFunctions:
                                        if function.id == F'{name[0]}_{name[1]}':
                                            found = True
                                            conditionFunctions.append(function)
                                            
                                            condition.append(function.id)    ##  ?!
                                    if not found:
                                        type = F'Bits({len(name[1])} bits)'
                                        newFunction = decoder.equals(F'{name[0]}_{name[1]}', decoder.getInput(F'io.{name[0]}'), decoder.const(type, F'B"{name[1]}"'))

                                        decodeFunctions.append(newFunction)
                                        conditionFunctions.append(newFunction)
                                        
                                        condition.append(newFunction.definition)    ##  ?!
                                
                                val = value
                                if isinstance(value, list):
                                    val = ''
                                    for e, element in enumerate(value):
                                        if e > 0:
                                            val += '_'
                                        val += element
                                andFunction = decoder.multiAnd(F'{key}_{val}_{len(conditions[v])}', conditionFunctions)

                                conditions[v].append(andFunction)
                                conditionsName[v].append(condition) ## ?!

                        orFunction = decoder.multiOr(F'{key}_{val}', conditions[v])
                        for i, val in enumerate(instructionSet.requirements[key]):
                            if value == val:
                                const = decoder.const(outputType, F'U"{format(i + 1, f"0{bitLength}b")}"')
                                funcValPairs.append([orFunction, const])

                    const = decoder.const(outputType, F'U"{format(0, f"0{bitLength}b")}"')

                    func = decoder.multiConditional(F'{key}_source', const, funcValPairs)
                    outputsToGenerate.append([func, const, F'io.{key}', outputType])

        valid = None
        for output in outputsToGenerate:
            if output[0].id == 'valid_source':
                valid = decoder.equals('valid', output[0], decoder.const('UInt(1 bits)', 'U(1, 1 bits)'))
                decoder.connect(valid, decoder.addOutput(F'io.valid', 'Bool()'))
        
        for output in outputsToGenerate:
            if not output[0].id == 'valid_source':
                func = output[0]
                const = output[1]
                decoder.connect(decoder.whenOtherwise(F'{func.id}_onValid', valid, func, const) , decoder.addOutput(output[2], output[3]))
                
        if display:
            decoder.checkIOConnections()
            decoder.sortSequentialSteps()
            decoder.draw_Grid_network()
        return decoder
    
    if decoderLogic == None:
        decoder = stage.addSubModule(build_RV32_Decoder_Logic('decoderLogic', instructionSet, False))
    else:
        decoder = stage.addSubModule(decoderLogic)
    
    stage.connect(decomp.getOutput('io.opcode'), decoder.getInput('io.opcode'))
    if decoder.getInput('io.f3'):
        stage.connect(decomp.getOutput('io.f3'), decoder.getInput('io.f3'))
    if decoder.getInput('io.f7'):
        stage.connect(decomp.getOutput('io.f7'), decoder.getInput('io.f7'))
    if decoder.getInput('io.f12'):
        stage.connect(decomp.getOutput('io.f12'), decoder.getInput('io.f12'))

    ## immediate multiplexer
    imm = stage.wire('imm', stage.createMultiplexerFromDecode('immType', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')))
    stage.connect(imm, stage.addStageOutput('io.imm', 'Bits(32 bits)'))
    
    ## pcCalc
    if len(instructionSet.requirements['pcCalcAsset']) > 0:
        ## pcCalc sources
        pcCalcSource1 = stage.createMultiplexerFromDecode('pcCalcSource1', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))
        pcCalcSource2 = stage.createMultiplexerFromDecode('pcCalcSource2', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))

        ## pc calc
        def build_RV32_JumpAddressCalculator(id: str, instructionSet: InstructionSet, display: bool = False):
            print(F'   - FormalRV: Building rv32 jump address calculator "{id}" with instruction set "{instructionSet.id}"')

            pcCalc = formalHandshake_Hardware.Hardware_Module(id)
            source1 = pcCalc.addInput('io.source1', 'Bits(32 bits)')
            source2 = pcCalc.addInput('io.source2', 'Bits(32 bits)')
            addu = formalHandshake_Hardware.AdderUnsigned('addu', pcCalc, 32, source1, source2)
            for asset in instructionSet.pcCalcAssets:
                if asset == 'addu':
                    pcCalc.connect(addu, pcCalc.addOutput('io.addu', 'Bits(32 bits)'))
                elif asset == 'addu31':
                    pcCalc.connectManual(addu, pcCalc.addOutput('io.addu31', 'Bits(32 bits)'), F'addu(31 downto 1) ## B(0, 1 bits)')
                else:
                    raise ValueError(F'Asset "{asset}" is not provided by jump address calculator "{id}"')
            
            if display:
                pcCalc.checkIOConnections()
                pcCalc.sortSequentialSteps()
                pcCalc.draw_Grid_network()

            return pcCalc
        
        if jumpAddressCalculator == None:
            pcCalcAssets = stage.addSubModule(build_RV32_JumpAddressCalculator('pcCalc', instructionSet, False))
        else:
            pcCalcAssets = stage.addSubModule(jumpAddressCalculator)
        
        stage.connect(pcCalcSource1, pcCalcAssets.getInput(F'io.source1'))
        stage.connect(pcCalcSource2, pcCalcAssets.getInput(F'io.source2'))

        ## jumpAddress multiplexer
        jumpAddress = stage.createMultiplexerFromDecode('pcCalcAsset', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))
        jumpAttempt = stage.isNot('jumpAttempt', stage.getSelectValCompare('pcCalcAsset', instructionSet, 0))

        ## branch
        if len(instructionSet.requirements['branchAsset']) > 0:
            ## branch calc sources
            branchSource1 = stage.createMultiplexerFromDecode('branchSource1', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))
            branchSource2 = stage.createMultiplexerFromDecode('branchSource2', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))
            
            ## branch calc
            def build_RV32_BranchUnit(id: str, instructionSet: InstructionSet, display: bool = False):
                print(F'   - FormalRV: Building rv32 branch unit "{id}" with instruction set "{instructionSet.id}"')
                branchUnit = formalHandshake_Hardware.Hardware_Module(id)
                source1 = branchUnit.addInput('io.source1', 'Bits(32 bits)')
                source2 = branchUnit.addInput('io.source2', 'Bits(32 bits)')
                
                equals = formalHandshake_Hardware.Equals('equals', branchUnit, 32, source1, source2)
                equalsNot = formalHandshake_Hardware.EqualsNot('equalsNot', branchUnit, 32, source1, source2)
                lts = formalHandshake_Hardware.LowerThanSigned('lts', branchUnit, 32, source1, source2)
                ges = formalHandshake_Hardware.GreaterEqualsSigned('ges', branchUnit, 32, source1, source2)
                ltu = formalHandshake_Hardware.LowerThanUnsigned('ltu', branchUnit, 32, source1, source2)
                geu = formalHandshake_Hardware.GreaterEqualsUnsigned('geu', branchUnit, 32, source1, source2)

                for asset in instructionSet.branchAssets:
                    if asset == 'equals':
                        branchUnit.connect(equals, branchUnit.addOutput('io.equals', 'Bits(32 bits)'))
                    elif asset == 'equalsNot':
                        branchUnit.connect(equalsNot, branchUnit.addOutput('io.equalsNot', 'Bits(32 bits)'))
                    elif asset == 'lts':
                        branchUnit.connect(lts, branchUnit.addOutput('io.lts', 'Bits(32 bits)'))
                    elif asset == 'ges':
                        branchUnit.connect(ges, branchUnit.addOutput('io.ges', 'Bits(32 bits)'))
                    elif asset == 'ltu':
                        branchUnit.connect(ltu, branchUnit.addOutput('io.ltu', 'Bits(32 bits)'))
                    elif asset == 'geu':
                        branchUnit.connect(geu, branchUnit.addOutput('io.geu', 'Bits(32 bits)'))
                    else:
                        raise ValueError(F'Asset "{asset}" is not provided by branch unit "{id}"')
                
                if display:
                    branchUnit.checkIOConnections()
                    branchUnit.sortSequentialSteps()
                    branchUnit.draw_Grid_network()

                return branchUnit

            if branchUnit == None:
                branchUnit = stage.addSubModule(build_RV32_BranchUnit('branchUnit', instructionSet, False))
            else:
                stage.addSubModule(branchUnit)
            stage.connect(branchSource1, branchUnit.getInput(F'io.source1'))
            stage.connect(branchSource2, branchUnit.getInput(F'io.source2'))

            branchTrue = stage.equals('branchTrue', stage.createMultiplexerFromDecode('branchAsset', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')), stage.const(F'Bits(32 bits)', 'B(1, 32 bits)'))
            noBranch = stage.getSelectValCompare('branchAsset', instructionSet, 0)

            jumpValid = stage.isAnd('jumpValid', jumpAttempt, stage.isOr('branchValid', branchTrue, noBranch))
        else:
            jumpValid = jumpAttempt
    
    ## alu
    if len(instructionSet.requirements['aluAsset']) > 0:
        stage.connect(decoder.getOutput('io.aluAsset'), stage.addStageOutput('io.aluAsset', decoder.getOutput('io.aluAsset').getType()))

        ## alu sources
        stage.connect(stage.createMultiplexerFromDecode('aluSource1', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')), stage.addStageOutput('io.aluSource1', 'Bits(32 bits)'))
        stage.connect(stage.createMultiplexerFromDecode('aluSource2', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')), stage.addStageOutput('io.aluSource2', 'Bits(32 bits)'))
        
    ## mem
    if len(instructionSet.requirements['memAddressCalcAsset']) > 0:
        stage.connect(decoder.getOutput('io.memAddressCalcAsset'), stage.addStageOutput('io.memAddressCalcAsset', decoder.getOutput('io.memAddressCalcAsset').getType()))
        
        ## mem address calc sources
        memAddressCalcSource1 = stage.createMultiplexerFromDecode('memAddressCalcSource1', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))
        memAddressCalcSource2 = stage.createMultiplexerFromDecode('memAddressCalcSource2', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)'))

        ## mem address calc
        def build_RV32_MemoryAddressCalculator(id: str, instructionSet: InstructionSet, display: bool = False):
            print(F'   - FormalRV: Building rv32 memory address calculator "{id}" with instruction set "{instructionSet.id}"')
            memAddressCalc = formalHandshake_Hardware.Hardware_Module(id)
            source1 = memAddressCalc.addInput('io.source1', 'Bits(32 bits)')
            source2 = memAddressCalc.addInput('io.source2', 'Bits(32 bits)')
            
            addu = formalHandshake_Hardware.AdderUnsigned('addu', memAddressCalc, 32, source1, source2)

            for asset in instructionSet.memAddressCalcAssets:
                if asset == 'addu':
                    memAddressCalc.connect(addu, memAddressCalc.addOutput('io.addu', 'Bits(32 bits)'))
                else:
                    raise ValueError(F'Asset "{asset}" is not provided by memory address calculator "{id}"')
            
            if display:
                memAddressCalc.checkIOConnections()
                memAddressCalc.sortSequentialSteps()
                memAddressCalc.draw_Grid_network()

            return memAddressCalc

        if memoryAddressCalculator == None:
            memAddressCalc = stage.addSubModule(build_RV32_MemoryAddressCalculator('memAddressCalc', instructionSet, False))
        else:
            memAddressCalc = stage.addSubModule(memoryAddressCalculator)
        stage.connect(memAddressCalcSource1, memAddressCalc.getInput(F'io.source1'))
        stage.connect(memAddressCalcSource2, memAddressCalc.getInput(F'io.source2'))

        memAddress = stage.createMultiplexerFromDecode('memAddressCalcAsset', instructionSet, stage.const('Bits(32 bits)', 'B(0, 32 bits)'), memAddressCalc)
        stage.connect(memAddress, stage.addStageOutput('io.memAddress', 'Bits(32 bits)'))

        ## memory control
        if len(instructionSet.requirements['memSize']) > 0:
            stage.connect(decoder.getOutput('io.memSize'), stage.addStageOutput('io.memSize', decoder.getOutput('io.memSize').getType()))
        if len(instructionSet.requirements['memWrite']) > 0:
            stage.connect(decoder.getOutput('io.memWrite'), stage.addStageOutput('io.memWrite', decoder.getOutput('io.memWrite').getType()))
        if len(instructionSet.requirements['memWriteSource']) > 0:
            stage.connect(decoder.getOutput('io.memWriteSource'), stage.addStageOutput('io.memWriteSource', decoder.getOutput('io.memWriteSource').getType()))
        if len(instructionSet.requirements['memReadFormat']) > 0:
            stage.connect(decoder.getOutput('io.memReadFormat'), stage.addStageOutput('io.memReadFormat', decoder.getOutput('io.memReadFormat').getType()))

    stage.connect(rs1_data, stage.addStageOutput('io.rs1_data', 'Bits(32 bits)'))
    stage.connect(rs2_data, stage.addStageOutput('io.rs2_data', 'Bits(32 bits)'))

    ## exception handling
    decodeValid = decoder.getOutput('io.valid')
    exceptionSources = []
    exceptionSources.append(stage.isNot('notInstructionValid', decodeValid))
    
    ## jump address misaligned
    if len(instructionSet.requirements['pcCalcAsset']) > 0 and len(instructionSet.requirements['checkMisalignedPc']) > 0:
        #bitLength = len(instructionSet.requirements['checkMisalignedPc']).bit_length()
        #type = F'UInt({bitLength} bits)'
        checkMisalignedPc = decoder.getOutput('io.checkMisalignedPc')
        values = []
        values.append(stage.false())
        for misalignedVal in instructionSet.requirements['checkMisalignedPc']:
            func = formalHandshake_Hardware.Hardware_Function(F'pc_Mod_{misalignedVal}', stage, 'Bool()', 0)
            input = formalHandshake_Hardware.Hardware_IOPort('address', func, 'Bits(32 bits)')
            stage.connect(jumpAddress, input)
            func.inputs.append(input)
            func.definition = F'({jumpAddress.id}.asUInt % {misalignedVal}) =/= 0'
            values.append(func)

        instruction_address_misaligned_exception = stage.isAnd('instruction_address_misaligned_exception', jumpValid, stage.multiplex('instruction_address_misaligned', 'Bool()', checkMisalignedPc, values))
        exceptionSources.append(instruction_address_misaligned_exception)

    ## memory address misaligned
    if len(instructionSet.requirements['memAddressCalcAsset']) > 0 and len(instructionSet.requirements['checkMisalignedMem']) > 0:
        #bitLength = len(instructionSet.requirements['checkMisalignedMem']).bit_length()
        #type = F'UInt({bitLength} bits)'
        checkMisalignedMem = decoder.getOutput('io.checkMisalignedMem')
        values = []
        values.append(stage.false())
        for misalignedVal in instructionSet.requirements['checkMisalignedMem']:
            func = formalHandshake_Hardware.Hardware_Function(F'mem_Mod_{misalignedVal}', stage, 'Bool()', 0)
            input = formalHandshake_Hardware.Hardware_IOPort('address', func, 'Bits(32 bits)')
            stage.connect(memAddress, input)
            func.inputs.append(input)
            func.definition = F'({memAddress.id}.asUInt % {misalignedVal}) =/= 0'
            values.append(func)

        address_misaligned_exception = stage.multiplex('address_misaligned_exception', 'Bool()', checkMisalignedMem, values)
        #stage.connect(address_misaligned_exception, stage.addStageOutput('io.address_misaligned_exception', 'Bool()'))
        exceptionSources.append(address_misaligned_exception)

    if len(exceptionSources) > 0:
        if len(exceptionSources) == 1:
            exception = exceptionSources[0]
        else:
            exception = stage.multiOr('exception', exceptionSources)
    else:
        exception = stage.false()
    #stage.connect(stage.isAnd('activeException', exception, stage.enable), stage.addStageOutput('io.exception', 'Bool()'))
    stage.connect(exception, stage.addStageOutput('io.exception', 'Bool()'))

    ## TrapHandler
    def build_RV32_TrapHandler_Simple(id: str, display: bool = False, trapAddress: str = 'B(0, 32 bits)'):
        print(F'   - FormalRV: Building rv32 basic trap handler, executing a trap to address "{trapAddress}" on exceptions')
        handler = formalHandshake_Hardware.Hardware_Module(id)
        exception = handler.addInput('io.exception', 'Bool()')
        trap = handler.addOutput('io.trap', 'Bool()')
        trapHandlerAddress = handler.addOutput('io.trapHandlerAddress', 'Bits(32 bits)')

        handler.connect(exception, trap)
        handler.connect(handler.const('Bits(32 bits)', trapAddress), trapHandlerAddress)

        if display:
            handler.checkIOConnections()
            handler.sortSequentialSteps()
            handler.draw_Grid_network()
        return handler
        
    if trapHandler == None:
        trapHandler = stage.addSubModule(build_RV32_TrapHandler_Simple('trapHandler'))
    else:
        stage.addSubModule(trapHandler)
    stage.connect(exception, trapHandler.getInput('io.exception'))
    trap = trapHandler.getOutput('io.trap')
    stage.connect(trap, stage.addStageOutput('io.trap', 'Bool()'))
    trapHandlerAddress = trapHandler.getOutput('io.trapHandlerAddress')

    ## jump
    if len(instructionSet.requirements['pcCalcAsset']) > 0:
        stage.connect(stage.isOr('jump', jumpValid, trap), stage.addStageOutput('io.jump', 'Bool()'))
    else:
        stage.connect(trap, stage.addStageOutput('io.jump', 'Bool()'))

    ## jumpAddress
    if len(instructionSet.requirements['pcCalcAsset']) > 0:
        stage.connect(stage.whenOtherwise('jumpAddress', trap, trapHandlerAddress, jumpAddress), stage.addStageOutput('io.jumpAddress', 'Bits(32 bits)'))
    else:
        stage.connect(trapHandlerAddress, stage.addStageOutput('io.jumpAddress', 'Bits(32 bits)'))

    ## writeBack control
    if len(instructionSet.requirements['rdSource']) > 0:
        stage.connect(decomp.getOutput('io.rd'), stage.addStageOutput('io.rd', 'Bits(5 bits)'))
        stage.connect(decoder.getOutput('io.rdSource'), stage.addStageOutput('io.rdSource', decoder.getOutput('io.rdSource').getType()))

    if pipelined:
        ## Hazard detection: rs1/rs2 used?
        rs1UsedFunctions = []
        rs2UsedFunctions = []

        ## pcCalc sources 
        func = stage.getIDSelected('pcCalcSource1', instructionSet, 'rs1_data')
        if func: rs1UsedFunctions.append(func)
        func = stage.getIDSelected('pcCalcSource2', instructionSet, 'rs1_data')
        if func: rs1UsedFunctions.append(func)
        func = stage.getIDSelected('pcCalcSource1', instructionSet, 'rs2_data')
        if func: rs2UsedFunctions.append(func)
        func = stage.getIDSelected('pcCalcSource2', instructionSet, 'rs2_data')
        if func: rs2UsedFunctions.append(func)

        ## branch sources
        func = stage.getIDSelected('branchSource1', instructionSet, 'rs1_data')
        if func: rs1UsedFunctions.append(func)
        func = stage.getIDSelected('branchSource2', instructionSet, 'rs1_data')
        if func: rs1UsedFunctions.append(func)
        func = stage.getIDSelected('branchSource1', instructionSet, 'rs2_data')
        if func: rs2UsedFunctions.append(func)
        func = stage.getIDSelected('branchSource2', instructionSet, 'rs2_data')
        if func: rs2UsedFunctions.append(func)
        
        ## alu rs1/rs2 used
        aluRs1UsedFunctions = []
        aluRs2UsedFunctions = []

        func = stage.getIDSelected('aluSource1', instructionSet, 'rs1_data')
        if func: aluRs1UsedFunctions.append(func)
        func = stage.getIDSelected('aluSource2', instructionSet, 'rs1_data')
        if func: aluRs1UsedFunctions.append(func)
        func = stage.getIDSelected('aluSource1', instructionSet, 'rs2_data')
        if func: aluRs2UsedFunctions.append(func)
        func = stage.getIDSelected('aluSource2', instructionSet, 'rs2_data')
        if func: aluRs2UsedFunctions.append(func)

        if len(aluRs1UsedFunctions) > 0:
            stage.connect(stage.multiOr('aluRs1Used', aluRs1UsedFunctions), stage.addStageOutput('io.aluRs1Used', 'Bool()'))
        if len(aluRs2UsedFunctions) > 0:
            stage.connect(stage.multiOr('aluRs2Used', aluRs2UsedFunctions), stage.addStageOutput('io.aluRs2Used', 'Bool()'))

            
        ## memory rs1/rs2 used
        memRs1UsedFunctions = []
        memRs2UsedFunctions = []

        func = stage.getIDSelected('memAddressCalcSource1', instructionSet, 'rs1_data')
        if func: rs1UsedFunctions.append(func)
        func = stage.getIDSelected('memAddressCalcSource2', instructionSet, 'rs1_data')
        if func: rs1UsedFunctions.append(func)
        func = stage.getIDSelected('memAddressCalcSource1', instructionSet, 'rs2_data')
        if func: rs2UsedFunctions.append(func)
        func = stage.getIDSelected('memAddressCalcSource2', instructionSet, 'rs2_data')
        if func: rs2UsedFunctions.append(func)

        func = stage.getIDSelected('memWriteSource', instructionSet, 'rs1_data')
        if func:
            memRs1UsedFunctions.append(func)
        func = stage.getIDSelected('memWriteSource', instructionSet, 'rs2_data')
        if func: 
            memRs2UsedFunctions.append(func)

        if len(memRs1UsedFunctions) > 0:
            stage.connect(stage.multiOr('memRs1Used', memRs1UsedFunctions), stage.addStageOutput('io.memRs1Used', 'Bool()'))
        if len(memRs2UsedFunctions) > 0:
            stage.connect(stage.multiOr('memRs2Used', memRs2UsedFunctions), stage.addStageOutput('io.memRs2Used', 'Bool()'))

        if len(aluRs1UsedFunctions) > 0 or len(memRs1UsedFunctions) > 0:
            stage.connect(rs1, stage.addStageOutput('io.rs1', 'Bits(5 bits)'))
            
        if len(aluRs2UsedFunctions) > 0 or len(memRs2UsedFunctions) > 0:
            stage.connect(rs2, stage.addStageOutput('io.rs2', 'Bits(5 bits)'))

        if len(rs1UsedFunctions) > 0:
            rs1UsedAndNotZero = stage.isAnd('rs1UsedAndNotZero', stage.isNot('rs1_not0', stage.equals('rs1_0', rs1, stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), stage.multiOr('rs1Used', rs1UsedFunctions))
            stage.readConflicted('reg', 'reg_rs1', 'reg_rs1_data', rs1UsedAndNotZero, True)
        if len(rs2UsedFunctions) > 0:
            rs2UsedAndNotZero = stage.isAnd('rs2UsedAndNotZero', stage.isNot('rs2_not0', stage.equals('rs2_0', rs2, stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), stage.multiOr('rs2Used', rs2UsedFunctions))
            stage.readConflicted('reg', 'reg_rs2', 'reg_rs2_data', rs2UsedAndNotZero, True)

    stage.combinational()
    stage.validOn(stage.isNot('noException', exception))

    if display:
        stage.checkIOConnections()
        stage.sortSequentialSteps()
        stage.draw_Grid_network()
    return stage

## Returns a proposed RISC-V Execute Stage
def build_RV32ExecuteStage(id: str, pipelined: bool, instructionSet: InstructionSet, alu: formalHandshake_Hardware.Hardware_Module = None, display: bool = False):
    print(F'   - FormalRV: Building rv32 execute stage "{id}", with instruction set: "{instructionSet.id}"')
    stage = RV32Stage(id, pipelined)
    stage.combinational()
    stage.validOn()

    if len(instructionSet.requirements['aluAsset']) > 0:
        ##?
        def build_RV32IALUAssetsModule(id: str, display: bool = False):
            print(F'   - FormalRV: Building rv32i ALU asset module "{id}"')
            alu = formalHandshake_Hardware.Hardware_Module(id)

            source1 = alu.addInput('io.source1', 'Bits(32 bits)')
            source2 = alu.addInput('io.source2', 'Bits(32 bits)')


            formalHandshake_Hardware.AdderUnsigned('addu', alu, 32, source1, source2, alu.addOutput('io.addu', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.LowerThanSigned('lts', alu, 32, source1, source2, alu.addOutput('io.lts', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.LowerThanUnsigned('ltu', alu, 32, source1, source2, alu.addOutput('io.ltu', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.XOR('xor', alu, 32, source1, source2, alu.addOutput('io.xor', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.OR('or', alu, 32, source1, source2, alu.addOutput('io.or', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.AND('and', alu, 32, source1, source2, alu.addOutput('io.and', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.SLL('sll', alu, 32, source1, source2, alu.addOutput('io.sll', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.SRL('srl', alu, 32, source1, source2, alu.addOutput('io.srl', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.SRA('sra', alu, 32, source1, source2, alu.addOutput('io.sra', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.AdderSigned('adds', alu, 32, source1, source2, alu.addOutput('io.adds', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.SubtractSigned('subs', alu, 32, source1, source2, alu.addOutput('io.subs', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.Equals('equals', alu, 32, source1, source2, alu.addOutput('io.equals', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.EqualsNot('equalsNot', alu, 32, source1, source2, alu.addOutput('io.equalsNot', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.GreaterEqualsSigned('ges', alu, 32, source1, source2, alu.addOutput('io.ges', 'Bits(32 bits)').getKeyword())
            formalHandshake_Hardware.GreaterEqualsUnsigned('geu', alu, 32, source1, source2, alu.addOutput('io.geu', 'Bits(32 bits)').getKeyword())
            
            alu.connectAllKeywords()

            if display:
                alu.checkIOConnections()
                alu.sortSequentialSteps()
                alu.draw_Grid_network()
            return alu

        if alu == None:
            alu = stage.addSubModule(build_RV32IALUAssetsModule('alu', False))
        else:
            stage.addSubModule(alu)

        stage.connect(stage.addStageInput('io.aluSource1', 'Bits(32 bits)'), alu.getInput('io.source1'))
        stage.connect(stage.addStageInput('io.aluSource2', 'Bits(32 bits)'), alu.getInput('io.source2'))
    stage.connect(stage.createMultiplexerFromDecode('aluAsset', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')), stage.addStageOutput('io.alu', 'Bits(32 bits)'))

    if pipelined:
        ## input source data conflicts
        if 'rs1_data' in instructionSet.requirements['aluSource1']:
            stage.connect(stage.addStageInput('io.rs1', 'Bits(5 bits)'), stage.addOutput('io.aluRs1', 'Bits(5 bits)'))
            rs1Used = stage.addStageInput('io.aluRs1Used', 'Bool()')
            rs1UsedAndNotZero = stage.isAnd('rs1UsedAndNotZero', stage.isNot('rs1_not0', stage.equals('rs1_0', stage.getInput('io.rs1'), stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), rs1Used)
            stage.readConflicted('reg', 'aluRs1', 'aluSource1', rs1UsedAndNotZero)
        if 'rs2_data' in instructionSet.requirements['aluSource2']:
            stage.connect(stage.addStageInput('io.rs2', 'Bits(5 bits)'), stage.addOutput('io.aluRs2', 'Bits(5 bits)'))
            rs2Used = stage.addStageInput('io.aluRs2Used', 'Bool()')
            rs2UsedAndNotZero = stage.isAnd('rs2UsedAndNotZero', stage.isNot('rs2_not0', stage.equals('rs2_0', stage.getInput('io.rs2'), stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), rs2Used)
            stage.readConflicted('reg', 'aluRs2', 'aluSource2', rs2UsedAndNotZero)

        ## output write data conflicts
        if 'alu' in instructionSet.requirements['rdSource']:
            stage.connect(stage.addStageInput('io.rd', 'Bits(5 bits)'), stage.addOutput('io.aluRd', 'Bits(5 bits)'))
            rdUsed = stage.getIDSelected('rdSource', instructionSet, 'alu', True)
            rdUsedAndNotZero = stage.isAnd('rdUsedAndNotZero', stage.isNot('rd_not0', stage.equals('rd_0', stage.getInput('io.rd'), stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), rdUsed)
            stage.writeConflicted('reg', 'aluRd', 'alu', rdUsedAndNotZero)

    if display:
        stage.checkIOConnections()
        stage.sortSequentialSteps()
        stage.draw_Grid_network()
    return stage

## Returns a proposed RISC-V Memory Stage
def build_RV32MemoryStage(id: str, pipelined: bool, instructionSet: InstructionSet, memStallAllowed: bool, memReadDataDelayed: bool = True, memReadFormatAssets: formalHandshake_Hardware.Hardware_Module = None, display: bool = False):
    print(F'   - FormalRV: Building rv32 memory stage "{id}", with instruction set: "{instructionSet.id}"')
    stage = RV32Stage(id, pipelined)

    if memReadDataDelayed == False:
        raise NotImplementedError(F'Need to implement mem read data not delayed!')

    if len(instructionSet.requirements['memAddressCalcAsset']) > 0:
        ## d_mem_bus
        memReq = stage.addOutput('io.d_mem_bus_req', 'Bool()')
        memAddress = stage.addOutput('io.d_mem_bus_address', 'Bits(32 bits)')
        memSize = stage.addOutput('io.d_mem_bus_size', 'UInt(2 bits)')
        memWriteEnable = stage.addOutput('io.d_mem_bus_wEnable', 'Bool()')
        memWriteData = stage.addOutput('io.d_mem_bus_wdata', 'Bits(32 bits)')
        memReqAck = stage.addInput('io.d_mem_bus_reqAck', 'Bool()') ## ?!
        ## memValid = stage.addInput('io.d_mem_bus_valid', 'Bool()') ## ?!
        memReadData = stage.addInput('io.d_mem_bus_rdata', 'Bits(32 bits)')
        ## connect to memory bus
        noException = stage.isNot('noException', stage.addStageInput('io.exception', 'Bool()'))
        stage.connect(stage.isAnd('req', stage.enable, noException), memReq)
        stage.connect(stage.addStageInput('io.memAddress', 'Bits(32 bits)'), memAddress)
        stage.connect(stage.addStageInput('io.memSize', 'UInt(2 bits)'), memSize)
        stage.connect(stage.createMultiplexerFromDecode('memWrite', instructionSet, stage.false()), memWriteEnable)
        stage.connect(stage.createMultiplexerFromDecode('memWriteSource', instructionSet, stage.const('Bits(32 bits)', 'B(0, 32 bits)')), memWriteData)

        ## memory read output formats
        if memReadFormatAssets == None:
            ## ?
            def build_RV32ImemFormatAssetsModule(id: str, display: bool = False):
                print(F'   - FormalRV: Building rv32i memory format asset module "{id}"')
                read = formalHandshake_Hardware.Hardware_Module(id)

                memReadData = read.addInput('io.memReadData', 'Bits(32 bits)')
                read.connectManual(memReadData, read.addOutput('io.lbu', 'Bits(32 bits)'), 'U(io.memReadData(7 downto 0), 32 bits).asBits')
                read.connectManual(memReadData, read.addOutput('io.lhu', 'Bits(32 bits)'), 'U(io.memReadData(15 downto 0), 32 bits).asBits')
                read.connectManual(memReadData, read.addOutput('io.lb', 'Bits(32 bits)'), 'S(io.memReadData(7 downto 0), 32 bits).asBits')
                read.connectManual(memReadData, read.addOutput('io.lh', 'Bits(32 bits)'), 'S(io.memReadData(15 downto 0), 32 bits).asBits')
                read.connect(memReadData, read.addOutput('io.lw', 'Bits(32 bits)'))

                if display:
                    read.checkIOConnections()
                    read.sortSequentialSteps()
                    read.draw_Grid_network()
                return read

            memReadFormatAssets = stage.addSubModule(build_RV32ImemFormatAssetsModule('memReadFormatAssets', False))
        else:
            stage.addSubModule(memReadFormatAssets)
        stage.connect(memReadData, memReadFormatAssets.getInput('io.memReadData'))
        stage.connect(stage.createMultiplexerFromDecode('memReadFormat', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')), stage.addStageOutput('io.mem', 'Bits(32 bits)', memReadDataDelayed))
        
        if not memStallAllowed:
            raise NotImplementedError(9)

        memNotActive = stage.getSelectValCompare('memAddressCalcAsset', instructionSet, 0)
        
        if pipelined:
            ## input source data conflicts
            if 'rs1_data' in instructionSet.requirements['memWriteSource']:
                stage.connect(stage.addStageInput('io.rs1', 'Bits(5 bits)'), stage.addOutput('io.memRs1', 'Bits(5 bits)'))
                rs1Used = stage.isAnd('rs1Used', stage.isNot('rs1_not0', stage.equals('rs1_0', stage.getInput('io.rs1'), stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), stage.addStageInput('io.memRs1Used', 'Bool()'))
                stage.readConflicted('reg', 'memRs1', 'rs1_data', rs1Used)
            if 'rs2_data' in instructionSet.requirements['memWriteSource']:
                stage.connect(stage.addStageInput('io.rs2', 'Bits(5 bits)'), stage.addOutput('io.memRs2', 'Bits(5 bits)'))
                rs2Used = stage.isAnd('rs2Used', stage.isNot('rs2_not0', stage.equals('rs2_0', stage.getInput('io.rs2'), stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), stage.addStageInput('io.memRs2Used', 'Bool()'))
                stage.readConflicted('reg', 'memRs2', 'rs2_data', rs2Used)

            ## output write data conflicts
            if 'mem' in instructionSet.requirements['rdSource']:
                stage.connect(stage.addStageInput('io.rd', 'Bits(5 bits)'), stage.addOutput('io.memRd', 'Bits(5 bits)'))
                rdUsed = stage.isAnd('rdUsed', stage.isNot('rd_not0', stage.equals('rd_0', stage.getInput('io.rd'), stage.const('Bits(5 bits)', 'B(0, 5 bits)'))), stage.getIDSelected('rdSource', instructionSet, 'mem', True))
                stage.writeConflicted('reg', 'memRd', 'mem', rdUsed)

            ackOrInactive = stage.isOr('ackOrInactive', memNotActive, memReqAck)
            stage.stallingOn(ackOrInactive)
            stage.validOn(ackOrInactive)
        else:
            pastEnabledAndActive = formalHandshake_Hardware.Register('pastEnabled', stage, 'Bool()', 'False')
            memActive = stage.isNot('memActive', memNotActive)
            enabledAndActive = stage.isOr('enabledAndActive', pastEnabledAndActive, stage.isAnd('enableAndActive', stage.enable, memActive))
            stage.connect(stage.isAnd('enabledAndActiveNoAck', stage.isNot('notAck', memReqAck), enabledAndActive), pastEnabledAndActive.input())
            waiting = formalHandshake_Hardware.Register('waiting', stage, 'Bool()', 'False')
            stage.connect(stage.isAnd('acknowledgedReq', memReqAck, enabledAndActive), waiting.input())
            acknowledgedReqOrInactive = stage.isOr('acknowledgedReqOrInactive', waiting, memNotActive)
            stage.stallingOn(acknowledgedReqOrInactive)
            stage.validOn(acknowledgedReqOrInactive)
    
    else:
        stage.combinational()


    if display:
        stage.checkIOConnections()
        stage.sortSequentialSteps()
        stage.draw_Grid_network()
    return stage

## Returns a proposed RISC-V Writeback Stage
def build_RV32WriteBackStage(id: str, pipelined: bool, instructionSet: InstructionSet, display: bool = False):
    print(F'   - FormalRV: Building rv32 write back stage "{id}", with instruction set: "{instructionSet.id}"')
    stage = RV32Stage(id, pipelined)
    stage.combinational()
    stage.validOn()

    stage.connect(stage.createMultiplexerFromDecode('rdSource', instructionSet, stage.const(F'Bits(32 bits)', 'B(0, 32 bits)')), stage.addOutput('io.reg_rd_data', 'Bits(32 bits)'))
    writeBack = stage.isAnd('isWriteBack', stage.enable, stage.isNot('writeBack', stage.isOr('exceptionOrInactive', stage.addStageInput('io.exception', 'Bool()'), stage.getSelectValCompare('rdSource', instructionSet, 0))))
    stage.connect(stage.addStageInput('io.rd', 'Bits(5 bits)'), stage.addOutput('io.reg_rd', 'Bits(5 bits)'))
    stage.connect(writeBack, stage.addOutput('io.reg_WriteBack', 'Bool()'))

    if pipelined:
        ## output write data conflicts
        rdUsed = stage.isAnd('rdUsed', writeBack, stage.isNot('rd_not0', stage.equals('rd_0', stage.getInput('io.rd'), stage.const(F'Bits(5 bits)', 'B(0, 5 bits)'))))
        stage.writeConflicted('reg', 'reg_rd', 'reg_rd_data', rdUsed, True)

    if display:
        stage.checkIOConnections()
        stage.sortSequentialSteps()
        stage.draw_Grid_network()
    return stage

## Returns a proposed RISC-V Verification Stage
def build_RV32ISAVerificationStage(id: str, instructionSet: InstructionSet, display: bool = False):
    print(F'   - FormalRV: Building rv32 verification stage "{id}", with instruction set: "{instructionSet.id}"')
    stage = RV32Stage(id, False)
    stage.combinational()
    stage.validOn()

    ## verification outputs
    # fetch
    stage.connect(stage.addStageInput('io.pc_writeBackValid', 'Bool()'), stage.addOutput('verification.fetch', 'Bool()'))
    # pc
    stage.connect(stage.addStageInput('io.pc', 'Bits(32 bits)'), stage.addOutput('verification.pc', 'Bits(32 bits)'))
    # instruction
    stage.connect(stage.addStageInput('io.instruction', 'Bits(32 bits)'), stage.addOutput('verification.instruction', 'Bits(32 bits)'))
    # instruction valid
    stage.connect(stage.isOr('instructionValid', stage.enable, stage.lastNOP), stage.addOutput('verification.instructionValid', 'Bool()'))
    # exception
    stage.connect(stage.addStageInput('io.exception', 'Bool()'), stage.addOutput('verification.exception', 'Bool()'))
    # nextPc
    stage.connect(stage.addStageInput('io.pc_writeBackValue', 'Bits(32 bits)'), stage.addOutput('verification.nextPc', 'Bits(32 bits)'))
    # jump
    stage.connect(stage.addStageInput('io.jump', 'Bool()'), stage.addOutput('verification.jump', 'Bool()'))
    # jumpAddress
    stage.connect(stage.addStageInput('io.jumpAddress', 'Bits(32 bits)'), stage.addOutput('verification.jumpAddress', 'Bits(32 bits)'))
    
    # rs1
    stage.connect(stage.addStageInput('io.reg_rs1', 'Bits(5 bits)'), stage.addOutput('verification.rs1', 'Bits(5 bits)'))
    # rs1_data
    stage.connect(stage.addStageInput('io.rs1_data', 'Bits(32 bits)'), stage.addOutput('verification.rs1_data', 'Bits(32 bits)'))
    # rs2
    stage.connect(stage.addStageInput('io.reg_rs2', 'Bits(5 bits)'), stage.addOutput('verification.rs2', 'Bits(5 bits)'))
    # rs2_data
    stage.connect(stage.addStageInput('io.rs2_data', 'Bits(32 bits)'), stage.addOutput('verification.rs2_data', 'Bits(32 bits)'))
    # rdWrite
    stage.connect(stage.addStageInput('io.reg_WriteBack', 'Bool()'), stage.addOutput('verification.rdWrite', 'Bool()'))
    # rd
    stage.connect(stage.addStageInput('io.reg_rd', 'Bits(5 bits)'), stage.addOutput('verification.rd', 'Bits(5 bits)'))
    # rd_data
    stage.connect(stage.addStageInput('io.reg_rd_data', 'Bits(32 bits)'), stage.addOutput('verification.rd_data', 'Bits(32 bits)'))
    
    # memUsed
    pastMemReqAck = formalHandshake_Hardware.Register('pastMemReqAck', stage, 'Bool()', 'False')
    stage.connect(stage.addStageInput('io.d_mem_bus_req', 'Bool()'), pastMemReqAck.input())
    stage.connect(pastMemReqAck, stage.addOutput('verification.memUsed', 'Bool()'))
    # memAddress
    stage.connect(stage.addStageInput('io.d_mem_bus_address', 'Bits(32 bits)'), stage.addOutput('verification.memAddress', 'Bits(32 bits)'))
    # memSize
    stage.connect(stage.addStageInput('io.memSize', 'UInt(2 bits)'), stage.addOutput('verification.memSize', 'UInt(2 bits)'))
    # memWrite
    stage.connect(stage.addStageInput('io.d_mem_bus_wEnable', 'Bool()'), stage.addOutput('verification.memWrite', 'Bool()'))
    # mem_rdata
    stage.connect(stage.addStageInput('io.mem', 'Bits(32 bits)'), stage.addOutput('verification.mem_rdata', 'Bits(32 bits)'))
    # mem_wdata
    stage.connect(stage.addStageInput('io.d_mem_bus_wdata', 'Bits(32 bits)'), stage.addOutput('verification.mem_wdata', 'Bits(32 bits)'))

    if display:
        stage.checkIOConnections()
        stage.sortSequentialSteps()
        stage.draw_Grid_network()
    return stage


## Generates a complete RISC-V 32I CPU connectinga pipeline to a register file, a programm counter and linking all toplevel memory bus IOs
def build_RV32ICPU(id: str, pipelined: bool = False, project: FormalHandshakeHardwareProject = None, display: bool = False):
    if pipelined: 
        raise NotImplementedError()
    else:
        print(F'   - FormalRV: Building unpipelined rv32i cpu "{id}"')
        cpu = formalHandshake_Hardware.Hardware_Module(id)
        
        ## isa
        isa = generateRV32I(display)

        ## stages:
        fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, True, display=display)
        decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
        executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
        memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, True, display=display)
        writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
        pipeline_0BufferedStages = RV32Pipeline('pipeline_0BufferedStages').build([fetchStageUnpipelined, decodeStageUnpipelined, executeStageUnpipelined, memoryStageUnpipelined, writeBackStageUnpipelined], False, False, None, display=display)

        cpu.addSubModule(pipeline_0BufferedStages)

        for input in pipeline_0BufferedStages.inputs:
            print(F'PipelineInput: {input.id}')
        for output in pipeline_0BufferedStages.outputs:
            print(F'PipelineOutput: {output.id}')

        linkIO = [
            pipeline_0BufferedStages.getOutput('io.ready'),
            pipeline_0BufferedStages.getOutput('io.active'),
            pipeline_0BufferedStages.getOutput('io.done'),
            pipeline_0BufferedStages.getOutput('io.nop'),
            pipeline_0BufferedStages.getOutput('io.i_mem_bus_req'),
            pipeline_0BufferedStages.getOutput('io.i_mem_bus_address'),
            pipeline_0BufferedStages.getInput('io.i_mem_bus_reqAck'),
            pipeline_0BufferedStages.getInput('io.i_mem_bus_rdata'),
            pipeline_0BufferedStages.getOutput('io.d_mem_bus_req'),
            pipeline_0BufferedStages.getOutput('io.d_mem_bus_address'),
            pipeline_0BufferedStages.getOutput('io.d_mem_bus_size'),
            pipeline_0BufferedStages.getOutput('io.d_mem_bus_wEnable'),
            pipeline_0BufferedStages.getOutput('io.d_mem_bus_wdata'),
            pipeline_0BufferedStages.getInput('io.d_mem_bus_reqAck'),
            pipeline_0BufferedStages.getInput('io.d_mem_bus_rdata'),
        ]
        cpu.link(linkIO, True)

        pc = formalHandshake_Hardware.LoopedReg('pc', cpu, 'Bits(32 bits)', 'B(4, 32 bits)')
        cpu.connect(pc.value(), pipeline_0BufferedStages.getInput('io.pc_readValue'))
        cpu.connect(pipeline_0BufferedStages.getOutput('io.pc_writeBackValid'), pc.store())
        cpu.connect(pipeline_0BufferedStages.getOutput('io.pc_writeBackValue'), pc.input())

        cpu.connect(cpu.true(), pipeline_0BufferedStages.getInput('io.nextReady'))
        enable = formalHandshake_Hardware.Register('enable', cpu, 'Bool()', 'True')
        pipelineDoneOrNop = cpu.isOr('pipelineDoneOrNop', pipeline_0BufferedStages.done, pipeline_0BufferedStages.NOP)
        cpu.connect(pipelineDoneOrNop, enable.input())
        cpu.connect(enable, pipeline_0BufferedStages.enable)

        regfile = build_RV32RegFile('regfile')
        cpu.addSubModule(regfile)

        cpu.connectManual(pipeline_0BufferedStages.getOutput('io.reg_rs1'), regfile.getInput('rs1'), F'{pipeline_0BufferedStages.id}.io.reg_rs1.asUInt')
        cpu.connect(regfile.getOutput('rs1_data'), pipeline_0BufferedStages.getInput('io.reg_rs1_data'))
        cpu.connectManual(pipeline_0BufferedStages.getOutput('io.reg_rs2'), regfile.getInput('rs2'), F'{pipeline_0BufferedStages.id}.io.reg_rs2.asUInt')
        cpu.connect(regfile.getOutput('rs2_data'), pipeline_0BufferedStages.getInput('io.reg_rs2_data'))
        cpu.connectManual(pipeline_0BufferedStages.getOutput('io.reg_rd'), regfile.getInput('rd'), F'{pipeline_0BufferedStages.id}.io.reg_rd.asUInt')
        cpu.connect(pipeline_0BufferedStages.getOutput('io.reg_rd_data'), regfile.getInput('rd_data'))
        cpu.connect(pipeline_0BufferedStages.getOutput('io.reg_WriteBack'), regfile.getInput('writeEnable')) 
        
        if display:
            cpu.checkIOConnections()
            cpu.sortSequentialSteps()
            cpu.draw_Grid_network()

        if not project == None:
            project.addDesign(cpu, id, generateVerilog=True, overwrite= True)

        return cpu

## Generates and proves the RISC-V 32i CPU
def generateAndProof(
        toolChainInstalled: bool = False,   ## Only set to true, if SpinalHDl and Yosys/SymbiYosys are properly installed
        generateProofs: bool = False,       ## Set to true, if formal proofs are to be generated and executed
        pruneUnused: bool = False           ## Set to true, to apply decomposition to the proof, reducing them to only the parts of the circuit descriptions relevant to each respective proof
        ):
    
    print('------')
    path = 'Projects/'
    project = FormalHandshakeHardwareProject.load('RV32V2Test', path, True)

    ## paramters
    display = False                         ## detailed reporting on the executed steps and generated structures
    pipelined = False                       ## only the unpipelined version is tested yet
    i_memStallAllowed = True                ## allows for the i_mem bus to take variably longer than one cycle
    d_memStallAllowed = True                ## allows for the d_mem bus to take variably longer than one cycle
    forwarding = True                       ## generates a forwarding logic, if possible to avoid pipeline stalls due to hazards -> only relevant for pipelining
    registerFileWriteReadBypass = True      ## allows the registerfile to directly pass on the write value to the read outputs, if addresses match, this is also part of the forwarding logic

    ## CPU generation
    # generates all stages, the pipeline as well as the full CPU and adds the corresponding files to the project

    isa = generateRV32I(display)
    if True: 
        fetchStage = build_RV32FetchStage('fetchStage', pipelined, i_memStallAllowed, display=display)
        project.addDesign(fetchStage, 'fetchStage', generateVerilog=toolChainInstalled, overwrite= True)
        decodeStage = build_RV32DecodeStage('decodeStage', pipelined, isa, display=display)
        project.addDesign(decodeStage, 'decodeStage', generateVerilog=toolChainInstalled, overwrite= True)
        executeStage = build_RV32ExecuteStage('executeStage', pipelined, isa, display=display)
        project.addDesign(executeStage, 'executeStage', generateVerilog=toolChainInstalled, overwrite= True)
        memoryStage = build_RV32MemoryStage('memoryStage', pipelined, isa, d_memStallAllowed, display=display)
        project.addDesign(memoryStage, 'memoryStage', generateVerilog=toolChainInstalled, overwrite= True)
        writeBackStage = build_RV32WriteBackStage('writeBackStage', pipelined, isa, display=display)
        project.addDesign(writeBackStage, 'writeBackStage', generateVerilog=toolChainInstalled, overwrite= True)
        writeReadBypasses = None
        if registerFileWriteReadBypass:
            writeReadBypasses = ['reg']
        pipeline = RV32Pipeline('pipeline').build([fetchStage, decodeStage, executeStage, memoryStage, writeBackStage], pipelined, forwarding, writeReadBypasses)
        project.addDesign(pipeline, 'pipeline', generateVerilog=toolChainInstalled, overwrite= True)
        if toolChainInstalled:
            build_RV32ICPU('rv32i_cpu', False, project)

    if generateProofs:
        ## FetchStage Proofs
        if True:
            ## Liveness
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed)
            if pruneUnused: 
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.done, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), True)
                fetchStageUnpipelined.pruneUnmarked()
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            RV32StageProof('fetchStageUnpipelined_liveness', fetchStageUnpipelined, project).build_livenessProof(1, True, False, True, add = True)
            ## "Only Done when Active"
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed)
            if pruneUnused: 
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.done, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.active, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), True)
                fetchStageUnpipelined.pruneUnmarked()
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            RV32StageProof('fetchStageUnpipelined_active', fetchStageUnpipelined, project).build_activeProof(1, True, False, True, add = True)
            ## NOP behavior
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed)
            if pruneUnused: 
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.done, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.valid, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.NOP, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), True)
                fetchStageUnpipelined.pruneUnmarked()
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            RV32StageProof('fetchStageUnpipelined_NOP', fetchStageUnpipelined, project).build_NOPProof(1, True, False, True, add = True)
            ## Ready behavior
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed)
            if pruneUnused: 
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.ready, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.active, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.done, True)
                fetchStageUnpipelined.getInputDependencies(fetchStageUnpipelined, fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), True)
                fetchStageUnpipelined.pruneUnmarked()
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            RV32StageProof('fetchStageUnpipelined_Ready', fetchStageUnpipelined, project).build_readyProof(1, True, False, True, add = True)
            
        ## Decode Proofs
        if True:
            ## Liveness 
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.done, True)
                decodeStageUnpipelined.pruneUnmarked()
            RV32StageProof('decodeStageUnpipelined_liveness', decodeStageUnpipelined, project).build_livenessProof(0, True, False, True, add = True)
            ## "Only Done when Active"
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.active, True)
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.done, True)
                decodeStageUnpipelined.pruneUnmarked()
            RV32StageProof('decodeStageUnpipelined_active', decodeStageUnpipelined, project).build_activeProof(0, True, False, True, add = True)
            ## NOP behavior
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.done, True)
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.valid, True)
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.NOP, True)
                decodeStageUnpipelined.pruneUnmarked()
            RV32StageProof('decodeStageUnpipelined_NOP', decodeStageUnpipelined, project).build_NOPProof(0, True, False, True, add = True)
            ## Ready behavior
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.ready, True)
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.active, True)
                decodeStageUnpipelined.getInputDependencies(decodeStageUnpipelined, decodeStageUnpipelined.done, True)
                decodeStageUnpipelined.pruneUnmarked()
            RV32StageProof('decodeStageUnpipelined_Ready', decodeStageUnpipelined, project).build_readyProof(0, True, False, True, add = True)
            
        ## Execute Proofs
        if True:
            ## Liveness
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.done, True)
                executeStageUnpipelined.pruneUnmarked()
            RV32StageProof('executeStageUnpipelined_liveness', executeStageUnpipelined, project).build_livenessProof(0, True, False, True, add = True)
            ## "Only Done when Active"
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.active, True)
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.done, True)
                executeStageUnpipelined.pruneUnmarked()
            RV32StageProof('executeStageUnpipelined_active', executeStageUnpipelined, project).build_activeProof(0, True, False, True, add = True)
            ## NOP behavior
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.done, True)
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.valid, True)
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.NOP, True)
                executeStageUnpipelined.pruneUnmarked()
            RV32StageProof('executeStageUnpipelined_NOP', executeStageUnpipelined, project).build_NOPProof(0, True, False, True, add = True)
            ## Ready behavior
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.active, True)
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.ready, True)
                executeStageUnpipelined.getInputDependencies(executeStageUnpipelined, executeStageUnpipelined.done, True)
                executeStageUnpipelined.pruneUnmarked()
            RV32StageProof('executeStageUnpipelined_Ready', executeStageUnpipelined, project).build_readyProof(0, True, False, True, add = True)

        ## Memory Proofs
        if True:
            ## Liveness
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            if pruneUnused: 
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.done, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), True)
                memoryStageUnpipelined.pruneUnmarked()
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            memoryStageUnpipelined.assumption('!io.exception')
            RV32StageProof('memoryStageUnpipelined_liveness', memoryStageUnpipelined, project).build_livenessProof(1, False, False, True, add = True)
            ## "Only Done when Active"
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            if pruneUnused: 
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.active, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.done, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), True)
                memoryStageUnpipelined.pruneUnmarked()
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            memoryStageUnpipelined.assumption('!io.exception')
            RV32StageProof('memoryStageUnpipelined_active', memoryStageUnpipelined, project).build_activeProof(1, True, False, True, add = True)
            ## NOP behavior
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            if pruneUnused: 
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.done, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.valid, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.NOP, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), True)
                memoryStageUnpipelined.pruneUnmarked()
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            memoryStageUnpipelined.assumption('!io.exception')
            RV32StageProof('memoryStageUnpipelined_NOP', memoryStageUnpipelined, project).build_NOPProof(1, True, False, True, add = True)
            ## Ready behavior
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            if pruneUnused: 
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.active, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.ready, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.done, True)
                memoryStageUnpipelined.getInputDependencies(memoryStageUnpipelined, memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), True)
                memoryStageUnpipelined.pruneUnmarked()
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            memoryStageUnpipelined.assumption('!io.exception')
            RV32StageProof('memoryStageUnpipelined_Ready', memoryStageUnpipelined, project).build_readyProof(1, True, False, True, add = True)
        
        ## WriteBack Proofs
        if True:
            ## Liveness
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.done, True)
                writeBackStageUnpipelined.pruneUnmarked()
            RV32StageProof('writeBackStageUnpipelined_liveness', writeBackStageUnpipelined, project).build_livenessProof(0, True, False, True, add = True)
            ## "Only Done when Active"
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.active, True)
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.done, True)
                writeBackStageUnpipelined.pruneUnmarked()
            RV32StageProof('writeBackStageUnpipelined_active', writeBackStageUnpipelined, project).build_activeProof(0, True, False, True, add = True)
            # NOP behavior
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.done, True)
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.valid, True)
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.NOP, True)
                writeBackStageUnpipelined.pruneUnmarked()
            RV32StageProof('writeBackStageUnpipelined_NOP', writeBackStageUnpipelined, project).build_NOPProof(0, True, False, True, add = True)
            ## Ready behavior
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            if pruneUnused: 
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.ready, True)
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.active, True)
                writeBackStageUnpipelined.getInputDependencies(writeBackStageUnpipelined, writeBackStageUnpipelined.done, True)
                writeBackStageUnpipelined.pruneUnmarked()
            RV32StageProof('writeBackStageUnpipelined_Ready', writeBackStageUnpipelined, project).build_readyProof(0, True, False, True, add = True)
        
        ## Pipeline Control Signal Proofs
        if True:
            ## Liveness
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed, display=display)
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            verificationStage = build_RV32ISAVerificationStage('verificationStage', isa, display=display)
            pipeline_0BufferedStages = RV32Pipeline('pipeline_0BufferedStages').build([fetchStageUnpipelined, decodeStageUnpipelined, executeStageUnpipelined, memoryStageUnpipelined, writeBackStageUnpipelined, verificationStage], False, False, None, display=display)
            if pruneUnused:
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.done, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.ready, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.NOP, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.i_mem_bus_req'), True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.d_mem_bus_req'), True)
                pipeline_0BufferedStages.pruneUnmarked()
                pipeline_0BufferedStages.pruneUnused()
            RV32PipelineProof('pipeline_0BufferedStages_liveness', pipeline_0BufferedStages, project).build_livenessProof(2, False, False, True, add = True)
            ## "Only Done when Active"
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed, display=display)
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            verificationStage = build_RV32ISAVerificationStage('verificationStage', isa, display=display)
            pipeline_0BufferedStages = RV32Pipeline('pipeline_0BufferedStages').build([fetchStageUnpipelined, decodeStageUnpipelined, executeStageUnpipelined, memoryStageUnpipelined, writeBackStageUnpipelined, verificationStage], False, False, None, display=display)
            if pruneUnused:
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.done, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.active, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.i_mem_bus_req'), True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.d_mem_bus_req'), True)
                pipeline_0BufferedStages.pruneUnmarked()
                pipeline_0BufferedStages.pruneUnused()
            RV32PipelineProof('pipeline_0BufferedStages_active', pipeline_0BufferedStages, project).build_activeProof(2, False, True, add = True)
            ## Ready behavior
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed, display=display)
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            memoryStageUnpipelined.assumption('!io.exception')
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            verificationStage = build_RV32ISAVerificationStage('verificationStage', isa, display=display)
            pipeline_0BufferedStages = RV32Pipeline('pipeline_0BufferedStages').build([fetchStageUnpipelined, decodeStageUnpipelined, executeStageUnpipelined, memoryStageUnpipelined, writeBackStageUnpipelined, verificationStage], False, False, None, display=display)
            if pruneUnused:
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.done, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.active, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.ready, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.NOP, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.i_mem_bus_req'), True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.d_mem_bus_req'), True)
                pipeline_0BufferedStages.pruneUnmarked()
                pipeline_0BufferedStages.pruneUnused()
            RV32PipelineProof('pipeline_0BufferedStages_ready', pipeline_0BufferedStages, project).build_readyProof(2, False, True, add = True)
            ## NOP behavior
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed, display=display)
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            verificationStage = build_RV32ISAVerificationStage('verificationStage', isa, display=display)
            pipeline_0BufferedStages = RV32Pipeline('pipeline_0BufferedStages').build([fetchStageUnpipelined, decodeStageUnpipelined, executeStageUnpipelined, memoryStageUnpipelined, writeBackStageUnpipelined, verificationStage], False, False, None, display=display)
            if pruneUnused:
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.done, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.NOP, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.valid, True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.i_mem_bus_req'), True)
                pipeline_0BufferedStages.getInputDependencies(pipeline_0BufferedStages, pipeline_0BufferedStages.getOutput('io.d_mem_bus_req'), True)
                pipeline_0BufferedStages.pruneUnmarked()
                pipeline_0BufferedStages.pruneUnused()
            RV32PipelineProof('pipeline_0BufferedStages_NOP', pipeline_0BufferedStages, project).build_NOPProof(2, False, True, add = True)
        
        ## ISA Compliance Proofs
        if True:
            fetchStageUnpipelined = build_RV32FetchStage('fetchStageUnpipelined', False, i_memStallAllowed, display=display)
            fetchStageUnpipelined.fairness(fetchStageUnpipelined.getOutput('io.i_mem_bus_req'), fetchStageUnpipelined.getInput('io.i_mem_bus_reqAck'), 0, False, True)
            decodeStageUnpipelined = build_RV32DecodeStage('decodeStageUnpipelined', False, isa, display=display)
            executeStageUnpipelined = build_RV32ExecuteStage('executeStageUnpipelined', False, isa, display=display)
            memoryStageUnpipelined = build_RV32MemoryStage('memoryStageUnpipelined', False, isa, i_memStallAllowed, display=display)
            memoryStageUnpipelined.fairness(memoryStageUnpipelined.getOutput('io.d_mem_bus_req'), memoryStageUnpipelined.getInput('io.d_mem_bus_reqAck'), 0, False, True)
            writeBackStageUnpipelined = build_RV32WriteBackStage('writeBackStageUnpipelined', False, isa, display=display)
            verificationStage = build_RV32ISAVerificationStage('verificationStage', isa, display=display)
            pipeline_0BufferedStages = RV32Pipeline('pipeline_0BufferedStages').build([fetchStageUnpipelined, decodeStageUnpipelined, executeStageUnpipelined, memoryStageUnpipelined, writeBackStageUnpipelined, verificationStage], False, False, None, display=display)
            
            isaSourcePath = 'src/reference/'
            referenceISA = formalHandshake_Hardware.Hardware_Module.from_SpinalHDL('referenceISA', isaSourcePath + 'Formal_Proof_Module_HandshakeVersion.scala', 'Formal_ISA')
            RV32PipelineProof('pipeline_0BufferedStages_fetchProof', pipeline_0BufferedStages, project).build_fetchProof(referenceISA, 2, False, 5, True, add = True)
            RV32PipelineProof('pipeline_0BufferedStages_exceptionProof', pipeline_0BufferedStages, project).build_exceptionProof(referenceISA, 2, False, 5, True, add = True)
            RV32PipelineProof('pipeline_0BufferedStages_pcProof', pipeline_0BufferedStages, project).build_pcProof(referenceISA, 2, False, 5, True, add = True)
            RV32PipelineProof('pipeline_0BufferedStages_regProof', pipeline_0BufferedStages, project).build_regProof(referenceISA, 2, False, 5, True, add = True)
            RV32PipelineProof('pipeline_0BufferedStages_memProof', pipeline_0BufferedStages, project).build_memProof(referenceISA, 2, False, 5, True, add = True)

        ## Initiate proof automation
        if toolChainInstalled: project.yosysProofAutomation(True, False, True).getStatus(True)
        
    print('------')


## This line of code executes the generation single cycle RISC-V 32I CPU and also optionally compiles it to verilog, as well as executes a number of formal proofs regarding a correct control flow and ISA compliance
generateAndProof(toolChainInstalled=True, generateProofs=True, pruneUnused=True)
