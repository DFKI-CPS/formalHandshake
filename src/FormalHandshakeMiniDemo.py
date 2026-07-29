from formalHandshake_Hardware import formalHandshake_Hardware
from FileManager import FormalHandshakeHardwareProject

## Dependencies:
# pip install networkx
# pip install matplotlib
# pip install jinja2


## The follwoing script executes a mini demo, demonstrating a few features of the FormalHandshake tool mentioned in the scientific Paper "FormalHandshake - Open Source Design and Verification Flow for complex Hardware Circuits"
print(F'------- Executing Formal Handshake Demo -------')

## Preprepared MiniALU, adding or subtracting two data inputs, depending on the ctrl signal
class MiniALU(formalHandshake_Hardware.Hardware_Module):
    def __init__(self, id: str, bits: int = 3):
        super().__init__(id)
        self.dataIn1 = self.addInput('io.dataIn1', F'Bits({bits} bits)')
        self.dataIn2 = self.addInput('io.dataIn2', F'Bits({bits} bits)')
        self.ctrl = self.addInput('io.ctrl', 'Bool()')
        self.dataOut = self.addOutput('io.dataOut', F'Bits({bits} bits)')

        add = formalHandshake_Hardware.AdderUnsigned('add', self, bits, self.dataIn1, self.dataIn2)
        substract = formalHandshake_Hardware.SubtractUnsigned('substract', self, bits, self.dataIn1, self.dataIn2)
        buffer = formalHandshake_Hardware.Register('dataBuffer', self, F'Bits({bits} bits)')
        self.connect(self.whenOtherwise('select', self.ctrl, add, substract), buffer.input())
        self.connect(buffer, self.dataOut)

## We instanciate an empty module to use as a toplevel
module = formalHandshake_Hardware.Hardware_Module('examplary_module')

## We add the preprepared MiniALU as a submodule
alu = module.addSubModule(MiniALU('alu'))

## We check, sort and display the subgraph of the MiniALU
alu.checkIOConnections()
alu.sortSequentialSteps()
alu.draw_Grid_network()

## We add toplevel inputs and connect them to the corresponding inputs of the MiniALU
module.connect(module.addInput('io.dataIn1', 'Bits(3 bits)'), alu.dataIn1)
module.connect(module.addInput('io.dataIn2', 'Bits(3 bits)'), alu.dataIn2)
module.connect(module.addInput('io.ctrl', 'Bool()'), alu.ctrl)

## We add an enable signal to serve as the starting signal for the toplevels control path
enable = module.addInput('io.enable', 'Bool()')
## We add a prebuild boolean register function node, called buffer
buffer = formalHandshake_Hardware.Register('buffer', module, 'Bool()', 'False')
## We connect the enable signal to the input of the buffer register
module.connect(enable, buffer.input())
## We use a function of the module class, automatically creating a two input multiplexer from two given signals and a control signal.
# This way we create a controlled bypass for the datapath.
bypass = module.whenOtherwise('bypass', buffer, alu.dataOut, alu.dataIn1)
## We connect the bypass multiplexer to a newly added toplevel data output
module.connect(bypass, module.addOutput('io.dataOut', 'Bits(3 bits)'))

## We connect the buffered enable signal to a newly added toplevel done output
done = module.addOutput('io.done', 'Bool()')
module.connect(buffer, done)

## We check, sort and display the resulting graph of the toplevel module
module.checkIOConnections()
module.sortSequentialSteps()
module.draw_Grid_network()

## We apply a graph traversal algorithm to mark all dependencies of a given toplevel output
module.getInputDependencies(module, done, True)
module.checkIOConnections()
module.sortSequentialSteps()
module.draw_Grid_network()

## The following part requires the toolchains for SpinalHDL and yosys Symbiyosys to be installed, in order to be executed:
# SpinalHDL: https://spinalhdl.github.io/SpinalDoc-RTD/v1.3.8/SpinalHDL/Getting%20Started/index.html
# Yosys/SymbiYosys: https://symbiyosys.readthedocs.io/en/latest/install.html
if True:
    ## We generate SpinalHDL code from this module and add it to a created project called "FormalHandshakeDemo" in the "designs" directory, using the filemanager.
    # If "generateVerilog" is set to true, the SpinalHDL code will also be compiled to verilog code
    project = FormalHandshakeHardwareProject.load('FormalHandshakeMiniDemo', 'Projects/')
    project.addDesign(module, 'examplary_module', generateVerilog=False, overwrite= True)

    ## We add assumptions and assertions to formally verify the data path

    ## We assume an initial reset for the bounded model check
    module.assumeInitialReset()
    ## We assume the ctrl signal to be set for addition
    module.assumption('io.ctrl')
    ## We assert the data output to be the result of the sum of both past data inputs, whenever the done output is set to true
    module.assertion('io.dataOut === (past(io.dataIn1.asUInt) + past(io.dataIn2.asUInt)).asBits').on(done)
    ## We compile the module - including the formal statements - to SpinalHDL and then to System Verilog.
    # The generated file is placed in a dedicated subdirectory in the projects proof directory, storing the given depth in the JSON metadata file
    project.addSymbiYosysProof(module, 'examplary_module_datapath', 5)

    ## We clean up the formal statements
    module.formalStatements = []

    ## We use the tools prebuild formal proof blocks, to formally verify the control path

    ## We create a liveness proof for a given trigger signal, a given property expected to be true after a given number of cylces
    module.liveness('liveness', enable, done, 1)
    ## Again, we generate the acutal system verilog proof and add it to the projects "proofs" directory
    project.addSymbiYosysProof(module, 'examplary_module_controlpath', 5)
    ## We execute all pending proofs in the project, giving status reports and collecting all results in the end
    # First all cover statements are automatically checked, up to the given depth
    # Then with the minimum depth required to reached all cover statements, the assertions are checked
    # If desired, cover traces can be kept, if assertions fail th counter example traces are stored
    # The rest of the produced file-overhead is automatically cleaned up
    project.yosysProofAutomation(True, False, True).getStatus(True)

print(F'-------    Formal Handshake Demo Done   -------')