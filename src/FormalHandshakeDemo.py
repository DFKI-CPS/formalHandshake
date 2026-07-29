from formalHandshake_Hardware import formalHandshake_Hardware
from FileManager import FormalHandshakeHardwareProject

## Dependencies:
# pip install networkx
# pip install matplotlib
# pip install jinja2

print(F'------- Executing Formal Handshake Demo -------')

## Basic Graph Building
if True:
    ## build basic module
    module1 = formalHandshake_Hardware.Hardware_Module('Test-Module1')
    ## displaying the module will not do anything, because it is empty
    module1.draw_Grid_network()

    ## add enable input and done output
    enable = module1.addInput('enable', 'Bool()')
    done = module1.addOutput('done', 'Bool()')
    ## connect input and output
    module1.connect(enable, done)
    ## now displaying is possible and shows the current module
    module1.draw_Grid_network()

## Automated Connections
if True:
    ## build a basic module with enable input, done output and a (prebuild) register
    module2 = formalHandshake_Hardware.Toplevel('Test-Module2')
    module2.addInput('enable', 'Bool()', 'keyword_a')   ## note, that a keywrd was given
    module2.addOutput('done', 'Bool()', 'keyword_b')   ## note, that a keywrd was given
    formalHandshake_Hardware.Register('register', module2, 'Bool()', 'False', 'keyword_a', 'keyword_b')   ## note, that a keywrd was given
    ## displaying the module will show, that the connections are missing
    module2.draw_Grid_network()

    ## using the "connectAllKeywords" makro will automaticall connect matching keywords, if possible
    module2.connectAllKeywords()
    ## displaying the module will show, that the connections are now there
    module2.draw_Grid_network()

    ## Prebuild Blocks
    ## a prebuild Counter with overflow on given max value
    counter = formalHandshake_Hardware.Counter('counter', 5)
    counter.draw_Grid_network()

    ## we can add this module to the original module and then link the new submodules inputs and outputs
    module2.addSubModule(counter)
    module2.draw_Grid_network()
    module2.link([counter.increment(), counter.value()])
    module2.draw_Grid_network()

## Dependency Checking Features
if True:
    ## build a basic module with enable input, done output, a counter
    module3 = formalHandshake_Hardware.Toplevel('Test-Module3')
    module3.addInput('enable', 'Bool()', 'a')
    done = module3.addOutput('done', 'Bool()')
    counter2 = formalHandshake_Hardware.Counter('counter', 3, keywordInc='a')
    module3.addSubModule(counter2)
    module3.connectAllKeywords()
    ## add a boolean function, that compares the counter value to a max value and then connects to the done output
    module3.connect(module3.equals('isMaxValue', counter2.value(), module3.const(counter2.value().getType(), counter2.maxValue)), done)
    module3.draw_Grid_network()

    ## add another "parallel" datapath
    input = module3.addInput('dataIn', 'Vec(Bits(3 bits), 3)', 'in')
    output = module3.addOutput('dataOut', 'Vec(Bits(3 bits), 3)', 'out')
    register = formalHandshake_Hardware.Register('reg', module3, 'Vec(Bits(3 bits), 3)')  ## 'Vec(Bits(3 bits), 3)', 'Bits(3 bits)'
    module3.connect(input, register.input())
    module3.connect(register, output)
    module3.draw_Grid_network()

    ## check if all connetions are hardware conform (e.g. no open wires) -> if they are, they will also be displayed as fully closed circles
    module3.checkIOConnections()
    ## sort the circuit in a sequential fashion, each new row depending on the rows before -> note that this does not work, if the circuit contains loops
    module3.sortSequentialSteps()
    module3.draw_Grid_network()

    ## for a given output, check and mark all dependencies up to any inputs of the given parent module
    module3.getInputDependencies(module3, done, True)
    module3.draw_Grid_network()

## The following part requires the toolchains for SpinalHDL and yosys Symbiyosys to be installed, in order to be executed:
# SpinalHDL: https://spinalhdl.github.io/SpinalDoc-RTD/v1.3.8/SpinalHDL/Getting%20Started/index.html
# Yosys/SymbiYosys: https://symbiyosys.readthedocs.io/en/latest/install.html

## Basic Enable-Done Module, SpinalHDL/Verilog generation and Liveness Proof
if False:
    ## build a basic module with enable input, done output and a counter, increasing the counter after being enabled and setting done to true, if the counter reaches a certain value
    livenessProof = formalHandshake_Hardware.Toplevel('livenessProof')
    enable = livenessProof.addInput('enable', 'Bool()')
    done = livenessProof.addOutput('done', 'Bool()')

    counter = formalHandshake_Hardware.Counter('counter', 3)
    livenessProof.addSubModule(counter)
    isMaxValue = livenessProof.equals('isMaxValue', counter.value(), livenessProof.const(counter.value().getType(), 3))
    livenessProof.connect(isMaxValue, done)

    enabled = formalHandshake_Hardware.Register('enabled', livenessProof, 'Bool()', 'False')
    active = livenessProof.isOr('nextEnabled', enable, enabled)
    livenessProof.connect(active, enabled.input())
    livenessProof.connect(active, counter.increment())
    livenessProof.checkIOConnections()
    livenessProof.draw_Grid_network()

    ## generate SpinalHDL code from this module and add it to a created project called "FormalHandshakeDemo" in the "designs" directory, using the filemanager
    project = FormalHandshakeHardwareProject.load('FormalHandshakeDemo', 'Projects/', True)
    ## if "generateVerilog" is set to true, the SpinalHDL code will also be compiled to verilog code
    project.addDesign(livenessProof, 'test', generateVerilog=True, overwrite= True)
    
    ## create a liveness proof for a given trigger signal, a given expected property and a certain number of cylces
    livenessProof.liveness('liveness', enable, done, 3, True, False, True)
    ## generate the acutal system verilog proof and add it to the projects "proofs" directory
    project.addSymbiYosysProof(livenessProof, 'Counter', 6)
    ## executing all pending proofs in the project, giving status reports and collecting all results in the end
    project.yosysProofAutomation(True, False, True).getStatus(True)

print(F'-------    Formal Handshake Demo Done   -------')