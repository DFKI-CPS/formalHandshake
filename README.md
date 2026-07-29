# File description:
### Libraries
- formalHandshake.py: basic library for building, managing, analysing and visualizing hirarchical graph structures.
- formalHandshake_Hardware.py: hardware specific library.
- Filemanager.py: library used for a design/verification projects file management and proof automation.
### Executable python scripts
- formalHandshakeDemo.py: basic demo showing the core features of the tool.
- formalHandshakeMiniDemo.py: a second demo, used for the examplary demonstration in the puplication titled "FormalHandshake - Open Source Design and Verification Flow for complex Hardware Circuits".
- formalRV_V2.py: The implementation of a RISC-V CPU generator using the tool, also mentioned in he puplication titled "FormalHandshake - Open Source Design and Verification Flow for complex Hardware Circuits". This includes a script in the end, generating an upipelined RISCV 32i CPU and executing all formal proofs.
### Others
- reference/Formal_Proof_Module_HandshakeVersion.scala: the RISC-V ISA reference implementation used in the RISC-V CPU generator for the formal verification of the generated CPUs


# Installation Requirements
In order to use and execute all of the demonstrated features, certain python librarys and two toolchains have to be installed:

### Python Dependencies:
- pip install networkx
- pip install matplotlib
- pip install jinja2

### Toolchains:
- SpinalHDL: https://spinalhdl.github.io/SpinalDoc-RTD/v1.3.8/SpinalHDL/Getting%20Started/index.html
- Yosys/SymbiYosys: https://symbiyosys.readthedocs.io/en/latest/install.html
