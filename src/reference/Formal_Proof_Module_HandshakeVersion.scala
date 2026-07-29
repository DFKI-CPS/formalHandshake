import spinal.lib._
import spinal.core._
import spinal.core.formal._

// Formalized RISC-V ISA
case class LivenessCheck(
  maxCycles : Int = 15,
  coverage : Boolean = false,
  retrigger : Boolean = false
)extends Component{
  val trigger = in Bool()
  val property = in Bool()
  val active = in Bool()
  val restart = in Bool()

  val postTrigger = Reg(Bool())
  val postTriggerCycles = Reg(UInt(32 bits))
  val propWitnessed = Reg(Bool())

  val cycles = out UInt(32 bits)
  val valid = out Bool()

  cycles := postTriggerCycles
  valid := property || propWitnessed

  GenerationFlags.formal{
    clockDomain.withoutReset(){
      assumeInitial(!postTrigger)
      assumeInitial(postTriggerCycles === 0)
      assumeInitial(!propWitnessed)

      when(restart){
        postTrigger := False
        postTriggerCycles := 0
      }.otherwise{
        when(trigger){
          postTrigger := True
          if(retrigger){
            postTriggerCycles := 1
          }
        }
        when(active){
          if(retrigger){
            when(postTrigger && !trigger){
              postTriggerCycles := postTriggerCycles + 1
            }
          }else{
            when(postTrigger || trigger){
              postTriggerCycles := postTriggerCycles + 1
            }
          }
        }
        when(postTrigger && property){
          propWitnessed := True
        }
      }

      cover(trigger)
      cover(postTriggerCycles >= maxCycles)
      cover(postTriggerCycles >= maxCycles && valid)
      if(!coverage){
        when(postTriggerCycles >= maxCycles){
          assert(valid)
        }
      }
    }
  }
}

case class Formal_ISA32I_IO() extends Bundle{
  val instruction = in Bits(32 bits)
  val pc = in UInt(32 bits)
  val rs1_data = in Bits(32 bits)
  val rs2_data = in Bits(32 bits)
  val memRead_data = in Bits(32 bits)
  
  val insNr = out UInt(8 bits)
  val insType = out UInt(8 bits)          // Codierung: 0 Unknown, 1 RI, 2 RR

  val rs1 = out UInt(5 bits)
  val rs2 = out UInt(5 bits)
  val rd = out UInt(5 bits)
  val reg1Read = out Bool()
  val reg2Read = out Bool()
  val regWrite = out Bool()
  val regWrite_data = out Bits(32 bits)

  val csr_data = in Bits(32 bits)
  val csr_mepc = in Bits(32 bits)
  val csrRead = out Bool()
  val csrWrite = out Bool()
  val csr = out UInt(12 bits)
  val csrWrite_data = out Bits(32 bits)

  val memActive = out Bool()
  val memAddress = out UInt(32 bits)
  val memAddressMisaligned = out Bool()
  val memWrite = out Bool()
  val memSize = out Bits(2 bits)
  val memWrite_data = out Bits(32 bits)

  val jump = out Bool()
  val jumpAddress = out UInt(32 bits)
  val jumpCond = out Bool()


  val trap = out Bool()
  val exception = out UInt(5 bits)  // 0: none/unknown instruction, 1: instruction address misaligned, 2: memory-address misaligned
}

// Formalized RISC-V ISA
case class Formal_ISA(
  catchPcMisaligned: Boolean = true,
  catchMemoryMisaligned: Boolean = true,
  dataWidth : Int = 32,
  e : Boolean = false,
  mul : Boolean = false,
  div : Boolean = false,
  comp: Boolean = false,
  csr : Boolean = true,
  sret : Boolean = true,
  mret : Boolean = true
  ) extends Component{

  val io = new Bundle{
    val instruction = in Bits(32 bits)
    val pc = in UInt(32 bits)
    val rs1_data = in Bits(32 bits)
    val rs2_data = in Bits(32 bits)
    val memRead_data = in Bits(32 bits)
    
    val insNr = out UInt(8 bits)
    val insType = out UInt(8 bits)          // Codierung: 0 Unknown, 1 RI, 2 RR

    val rs1 = out UInt(5 bits)
    val rs2 = out UInt(5 bits)
    val rd = out UInt(5 bits)
    val reg1Read = out Bool()
    val reg2Read = out Bool()
    val regWrite = out Bool()
    val regWrite_data = out Bits(32 bits)

    val csr_data = in Bits(32 bits)
    val csr_mepc = in Bits(32 bits)
    val csrRead = out Bool()
    val csrWrite = out Bool()
    val csr = out UInt(12 bits)
    val csrWrite_data = out Bits(32 bits)

    val memActive = out Bool()
    val memAddress = out UInt(32 bits)
    val memAddressMisaligned = out Bool()
    val memWrite = out Bool()
    val memSize = out Bits(2 bits)
    val memWrite_data = out Bits(32 bits)

    val jump = out Bool()
    val jumpAddress = out UInt(32 bits)
    val jumpCond = out Bool()


    val trap = out Bool()
    val exception = out UInt(5 bits)  // 0: none/unknown instruction, 1: instruction address misaligned, 2: memory-address misaligned
  }

  // Instruction decoding
  val instruction = new Area{
    val opcode = Bits(7 bits)
    val f3 = Bits(3 bits)
    val f7 = Bits(7 bits)
    val f12 = Bits(12 bits)
    val rs1 = Bits(5 bits)
    val rs2 = Bits(5 bits)
    val rd = Bits(5 bits)
    val shamt = Bits(5 bits)
    val IImm = Bits(32 bits)
    val BImm = Bits(32 bits)
    val SImm = Bits(32 bits)
    val UImm = Bits(32 bits)
    val JImm = Bits(32 bits)
    val loadAddress = UInt(dataWidth bits)
    val storeAddress = UInt(dataWidth bits)
    val csrAddress = UInt(12 bits)

    opcode := io.instruction(6 downto 0)
    f3 := io.instruction(14 downto 12)
    f7 := io.instruction(31 downto 25)
    f12 := io.instruction(31 downto 20)
    rs1 := io.instruction(19 downto 15)
    rs2 := io.instruction(24 downto 20)
    rd := io.instruction(11 downto 7)
    shamt := io.instruction(24 downto 20)
    IImm := S(io.instruction(31), 21 bits) ## io.instruction(30 downto 25) ## io.instruction(24 downto 21) ## io.instruction(20)
    BImm := S(io.instruction(31), 20 bits) ## io.instruction(7) ## io.instruction(30 downto 25) ## io.instruction(11 downto 8) ## B(0,1 bit)
    SImm := S(io.instruction(31), 21 bits) ## io.instruction(30 downto 25) ## io.instruction(11 downto 8) ## io.instruction(7)
    UImm := io.instruction(31) ## io.instruction(30 downto 20) ## io.instruction(19 downto 12) ## B(0, 12 bits)
    JImm := S(B(io.instruction(31) ## io.instruction(19 downto 12) ## io.instruction(20) ## io.instruction(30 downto 25) ## io.instruction(24 downto 21) ## B(0, 1 bit)),32 bits).asBits
    loadAddress := io.rs1_data.asUInt + IImm.asUInt
    storeAddress := io.rs1_data.asUInt + SImm.asUInt
    csrAddress := io.instruction(31 downto 20).asUInt

    /* // csr extension  
    csr := instrSwapped(31 downto 20)
    csr_uimm := instrSwapped(19 downto 15)  
    */
  }

  // Initially every instruction is treated as an unknown (illegal) instruction
  io.insNr := 0
  io.insType := 0

  io.rs1 := 0
  io.rs2 := 0
  io.rd := 0
  io.reg1Read := False
  io.reg2Read := False
  io.regWrite := False
  io.regWrite_data := 0

  io.csrRead := False
  io.csrWrite := False
  io.csr := 0
  io.csrWrite_data := 0

  io.memActive := False
  io.memAddress := 0
  io.memAddressMisaligned := False
  io.memWrite := False
  io.memSize := 0
  io.memWrite_data := 0

  io.jump := False
  io.jumpAddress := 0
  io.jumpCond := False
  
  io.trap := False
  io.exception := 0

  switch(instruction.opcode){
    is(B"0010011"){  // Comp RI
      when((instruction.f3 =/= 1 && instruction.f3 =/= 5) || (instruction.f3 === 5 && (instruction.f7 === B"0100000" || instruction.f7 === B"0000000")) || (instruction.f3 === 1 && instruction.f7 === B"0000000")){
        io.insType := 1
        io.reg1Read := True
        io.regWrite := True
        io.rs1 := instruction.rs1.asUInt
        io.rd := instruction.rd.asUInt
        switch(instruction.f3){
          is(0){ // AddI
            io.insNr := 1
            io.regWrite_data := (io.rs1_data.asUInt + instruction.IImm.asUInt).asBits
          }
          is(2){ // SLTI
            io.insNr := 2
            when(io.rs1_data.asSInt < instruction.IImm.asSInt){
              io.regWrite_data := B(1,32 bits)
            }.otherwise{
              io.regWrite_data := B(0,32 bits)
            }
          }
          is(3){ // SLTIU
            io.insNr := 3
            when(io.rs1_data.asUInt < instruction.IImm.asUInt){
              io.regWrite_data := B(1,32 bits)
            }.otherwise{
              io.regWrite_data := B(0,32 bits)
            }
          }
          is(4){ // XORI
            io.insNr := 4
            io.regWrite_data := (io.rs1_data ^ instruction.IImm)
          }
          is(6){ // ORI
            io.insNr := 5
            io.regWrite_data := (io.rs1_data | instruction.IImm)
          }
          is(7){ // ANDI
            io.insNr := 6
            io.regWrite_data := (io.rs1_data & instruction.IImm)
          }
          is(1){ // SLLI
            when(instruction.f7 === 0){
              io.insNr := 7
              io.regWrite_data := (io.rs1_data |<< instruction.shamt.asUInt)
            }
          }
          is(5){
            switch(instruction.f7){
              is(0){ // SRLI
                io.insNr := 8
                io.regWrite_data := (io.rs1_data |>> instruction.shamt.asUInt)
              }
              is(B"0100000"){ // SRAI
                io.insNr := 9
                io.regWrite_data := (io.rs1_data.asSInt >> instruction.shamt.asUInt).asBits
              }
              default{}
            }
          }
        }
      }
    }
    is(B"0110111"){  // Comp RI - LUI
      io.insType := 1
      io.regWrite := True
      io.rd := instruction.rd.asUInt
      io.insNr := 10
      io.regWrite_data := instruction.UImm
    }
    is(B"0010111"){  // Comp RI - AUIPC
      io.insType := 1
      io.regWrite := True
      io.rd := instruction.rd.asUInt
      io.insNr := 11
      io.regWrite_data := (io.pc + instruction.UImm.asUInt).asBits
    }
    is(B"0110011"){  // Comp RR
      when((instruction.f3 =/= 0 && instruction.f3 =/= 5 && instruction.f7 === 0) || ((instruction.f3 === 0 || instruction.f3 === 5) && (instruction.f7 === B"0000000" || instruction.f7 === B"0100000"))){
        io.reg1Read := True
        io.reg2Read := True
        io.regWrite := True
        io.rs1 := instruction.rs1.asUInt
        io.rs2 := instruction.rs2.asUInt
        io.rd := instruction.rd.asUInt
        /*
        when(instruction.f7 === 1){
          switch(instruction.f3){
            is(0){ //MUL
              if(mul){
                io.insType := 7
                io.insNr := 41
                io.regWrite_data := (io.rs1_data.asUInt * io.rs2_data.asUInt).asBits(31 downto 0)
              }
            }
            is(1){//MULH
              if(mul){
                io.insType := 7
                io.insNr := 42
                io.regWrite_data := (io.rs1_data.asSInt * io.rs2_data.asSInt).asBits(63 downto 32)
              }
            }
            is(2){//MULHSU
              if(mul){
                io.insType := 7
                io.insNr := 43
                io.regWrite_data(30 downto 0) := (io.rs1_data.asSInt * io.rs2_data.asSInt).asBits(62 downto 32)
                io.regWrite_data(31) := io.rs1_data(31)
              }
            }
            is(3){//MULHU
              if(mul){
                io.insType := 7
                io.insNr := 44
                io.regWrite_data := (io.rs1_data.asUInt * io.rs2_data.asUInt).asBits(63 downto 32)
              }
            }
            is(4){//DIV
              if(div){
                io.insType := 8
                io.insNr := 45
                when(io.rs2_data === 0){
                  io.regWrite_data := (S(-1, 32 bits)).asBits
                }.otherwise{
                  when(io.rs1_data.asSInt === S(-2^31, 32 bits) && io.rs2_data.asSInt === -1){
                      io.regWrite_data := S(-2^31, 32 bits).asBits 
                  }.otherwise{
                    io.regWrite_data := (io.rs1_data.asSInt / io.rs2_data.asSInt).asBits
                  }
                }
              }
            }
            is(5){//DIVU
              if(div){
                io.insType := 8
                io.insNr := 46
                when(io.rs2_data === 0){
                  io.regWrite_data := S(2^32 - 1, 32 bits).asBits
                }.otherwise{
                  io.regWrite_data := (io.rs1_data.asUInt / io.rs2_data.asUInt).asBits
                }
              }
            }
            is(6){//REM
              if(div){
                io.insType := 8
                io.insNr := 47
                when(io.rs2_data === 0){
                  io.regWrite_data := io.rs1_data
                }.otherwise{
                  when(io.rs1_data.asSInt === S(-2^31, 32 bits) && io.rs2_data.asSInt === -1){
                      io.regWrite_data := 0
                  }.otherwise{
                    io.regWrite_data := (io.rs1_data.asSInt / io.rs2_data.asSInt).asBits
                  }
                }
              }
            }
            is(7){//REMU
              if(div){
                io.insType := 8
                io.insNr := 48
                when(io.rs2_data === 0){
                  io.regWrite_data := io.rs1_data
                }.otherwise{
                  io.regWrite_data := (io.rs1_data.asUInt / io.rs2_data.asUInt).asBits
                }
              }
            }
          }
        }.otherwise{
        */
        io.insType := 2
        switch(instruction.f3){
          is(0){
            switch(instruction.f7){
              is(B"0000000"){ // Add
                io.insNr := 12
                io.regWrite_data := (io.rs1_data.asSInt + io.rs2_data.asSInt).asBits
              }
              is(B"0100000"){ // Sub
                io.insNr := 13
                io.regWrite_data := (io.rs1_data.asSInt - io.rs2_data.asSInt).asBits
              }
              default{}
            }
          }
          is(1){ // SLL
            when(instruction.f7 === 0){
              io.insNr := 14
              io.regWrite_data := (io.rs1_data |<< (io.rs2_data(4 downto 0).asUInt))
            }
          }
          is(2){ // SLT
            when(instruction.f7 === 0){
              io.insNr := 15
              when(io.rs1_data.asSInt < io.rs2_data.asSInt){
                io.regWrite_data := B(1,32 bits)
              }.otherwise{
                io.regWrite_data := B(0,32 bits)
              }
            }
          }
          is(3){ // SLTU
            when(instruction.f7 === 0){
              io.insNr := 16
              when(io.rs1_data.asUInt < io.rs2_data.asUInt){
                io.regWrite_data := B(1,32 bits)
              }.otherwise{
                io.regWrite_data := B(0,32 bits)
              }
            }
          }
          is(4){ // XOR
            when(instruction.f7 === 0){
              io.insNr := 17
              io.regWrite_data := io.rs1_data ^ io.rs2_data
            }
          }
          is(5){
            switch(instruction.f7){
              is(0){ // SRL
                io.insNr := 18
                io.regWrite_data := io.rs1_data |>> io.rs2_data(4 downto 0).asUInt
              }
              is(B"0100000"){ // SRA
                io.insNr := 19
                io.regWrite_data := (io.rs1_data.asSInt >> io.rs2_data(4 downto 0).asUInt).asBits
              }
              default{
              }
            }
          }
          is(6){ // OR
            when(instruction.f7 === 0){
              io.insNr := 20
              io.regWrite_data := (io.rs1_data | io.rs2_data)
            }
          }
          is(7){ // AND
            when(instruction.f7 === 0){
              io.insNr := 21
              io.regWrite_data := (io.rs1_data & io.rs2_data)
            }
          }
        }
        // }
      }
    }
    is(B"1101111"){  // ContTrans - JAL
      io.insType := 3
      io.insNr := 22
      io.jumpAddress := io.pc + instruction.JImm.asUInt
      if(catchPcMisaligned){
        io.trap := !(io.jumpAddress % 4 === 0)
      }else{
        io.trap := False
      }
      when(io.trap){
        io.exception := 1
      }.otherwise{
        io.regWrite := True
        io.rd := instruction.rd.asUInt
        io.regWrite_data := (io.pc + 4).asBits
        io.jump := True
      }
    }
    is(B"1100111"){  // ContTrans - JALR
      when(instruction.f3 === 0){
        io.insType := 3
        io.insNr := 23
        io.reg1Read := True
        io.rs1 := instruction.rs1.asUInt
        io.jumpAddress := U((io.rs1_data.asUInt + instruction.IImm.asUInt).asBits(dataWidth - 1 downto 1) ## B(0, 1 bits))
        if(catchPcMisaligned){
          io.trap := !(io.jumpAddress % 4 === 0)
        }else{
          io.trap := False
        }
        when(io.trap){
          io.exception := 1
        }.otherwise{
          io.regWrite := True
          io.rd := instruction.rd.asUInt
          io.regWrite_data := (io.pc + 4).asBits
          io.jump := True
        }
      }
    }
    is(B"1100011"){  // ContTrans
      when(!(instruction.f3 === 2) || (instruction.f3 === 3)){
        io.insType := 3
        io.reg1Read := True
        io.reg2Read := True
        io.rs1 := instruction.rs1.asUInt
        io.rs2 := instruction.rs2.asUInt
        switch(instruction.f3){
          is(0){  // BEQ
            io.insNr := 24
            io.jumpCond := (io.rs1_data === io.rs2_data)
          }
          is(1){  // BNE
            io.insNr := 25
            io.jumpCond := (io.rs1_data =/= io.rs2_data)
          }
          is(4){  // BLT
            io.insNr := 26
            io.jumpCond := (io.rs1_data.asSInt < io.rs2_data.asSInt)
          }
          is(5){  // BGE
            io.insNr := 27
            io.jumpCond := (io.rs1_data.asSInt >= io.rs2_data.asSInt)
          }
          is(6){  // BLTU
            io.insNr := 28
            io.jumpCond := (io.rs1_data.asUInt < io.rs2_data.asUInt)
          }
          is(7){  // BGEU
            io.insNr := 29
            io.jumpCond := (io.rs1_data.asUInt >= io.rs2_data.asUInt)
          }
          default{
          }
        }
        when(io.jumpCond){
          io.jumpAddress := io.pc + instruction.BImm.asUInt
          if(catchPcMisaligned){
            when(!((io.pc + instruction.BImm.asUInt) % 4 === 0)){
              io.trap := True
              io.exception := 1
              io.jumpAddress := 0
            }.otherwise{
              io.jump := True
            }
          }else{
            io.jump := True
            io.jumpAddress := io.pc + instruction.BImm.asUInt
          }
        }.otherwise{
          io.jumpAddress := io.pc + instruction.BImm.asUInt
        }
      }
    }
    is(B"0000011"){  // LS - Load
      when(!(instruction.f3 === 3 || instruction.f3 === 6 || instruction.f3 === 7)){
        io.insType := 4
        io.rs1 := instruction.rs1.asUInt
        io.rd := instruction.rd.asUInt
        io.reg1Read := True
        io.memAddress := instruction.loadAddress
        
        switch(instruction.f3){
          is(0){  // LB
            io.insNr := 30
            io.memSize := 1
            io.regWrite_data := S(io.memRead_data(7 downto 0), dataWidth bits).asBits
          }
          is(1){  // LH
            io.insNr := 31
            io.memSize := 2
            io.regWrite_data := S(io.memRead_data(15 downto 0), dataWidth bits).asBits
            if(catchMemoryMisaligned){
              io.memAddressMisaligned := (io.memAddress % 2 =/= 0)
            }
          }
          is(2){  // LW
            io.insNr := 32
            io.memSize := 3
            io.regWrite_data := B(io.memRead_data(31 downto 0), dataWidth bits)
            if(catchMemoryMisaligned){
              io.memAddressMisaligned := (io.memAddress % 4 =/= 0)
            }
          }
          is(4){  // LBU
            io.insNr := 33
            io.memSize := 1
            io.regWrite_data := U(io.memRead_data(7 downto 0), dataWidth bits).asBits
          }
          is(5){  // LHU
            io.insNr := 34
            io.memSize := 2
            io.regWrite_data := U(io.memRead_data(15 downto 0), dataWidth bits).asBits
            if(catchMemoryMisaligned){
              io.memAddressMisaligned := (io.memAddress % 2 =/= 0) 
            }
          }
          default{
          }
        }
        if(catchMemoryMisaligned){
          when(!io.memAddressMisaligned){
            io.regWrite := True
            io.memActive := True
          }.otherwise{
            io.trap := True
            io.exception := 2
          }
        }else{
          io.regWrite := True
          io.memActive := True
        }
      }
      
    }
    is(B"0100011"){  // LS - Store
      when(instruction.f3 === 0 || instruction.f3 === 1 || instruction.f3 === 2){
        io.insType := 4
        io.reg1Read := True
        io.reg2Read := True
        io.rs1 := instruction.rs1.asUInt
        io.rs2 := instruction.rs2.asUInt
        io.memAddress := instruction.storeAddress

        switch(instruction.f3){
          is(0){  // SB
            io.insNr := 35
            io.memSize := 1
            io.memWrite_data := io.rs2_data // B(io.rs2_data(7 downto 0), dataWidth bits)
          }
          is(1){  // SH
            io.insNr := 36
            io.memSize := 2
            io.memWrite_data := io.rs2_data // B(io.rs2_data(15 downto 0), dataWidth bits)
            if(catchMemoryMisaligned){
              io.memAddressMisaligned := (io.memAddress % 2 =/= 0)
            }
          }
          is(2){  // SW
            io.insNr := 37
            io.memSize := 3
            io.memWrite_data := io.rs2_data
            if(catchMemoryMisaligned){
              io.memAddressMisaligned := (io.memAddress % 4 =/= 0)
            }
          }
          default{}
        }
        
        if(catchMemoryMisaligned){
          when(!io.memAddressMisaligned){
            io.memActive := True
            io.memWrite := True
          }.otherwise{
            io.trap := True
            io.exception := 2
            io.memWrite_data := 0
          }
        }else{
          io.memWrite := True
          io.memActive := True
        }
      }
    }
    /*
    is(B"1110011"){ // System/CSR
      when(instruction.f3 === 0){
        when(instruction.rs1 === 0 && instruction.rd === 0 ){
          switch(instruction.f12){
            is(0){  // ECALL
              io.insType := 5
              io.insNr := 39
            }
            is(1){  // EBREAK
              io.insType := 5
              io.insNr := 39
            }
          }
        }
      }
    }
    */
    
    is(B"0001111"){ // Fence
      when(instruction.f3 === 0){ 
        io.insType := 6
        io.insNr := 40
      }
    }
    default{}
  }
  when(io.insNr === 0){
    io.trap := True
    io.exception := 3
  }
}

case class Formal_Proof_ModuleV2(
    ProofMode : Int = 0,              // 0: all proofs, 1: fetchCheck, 2: regCheck, 3: pcCheck, 4: memCheck, 5: exceptionCheck, 6: RegFileCheck,
    Coverage : Boolean = false,
    RegProofMode : Int = 0,
    regProofStart : Int = 0,               // 0-31,
    regProofStop : Int = 31,               // 0-31,
    BMC : Boolean = true,             // true: BMC, false: Induction step
    Instruction: Int = 0,             // 0: all instructions, > 0: single instruction
    traphandler : Boolean = true,     // ExceptionMode: 0 = Halt on Exception, 1 TrapPc
    catchPcMisaligned: Boolean = true,
    catchMemoryMisaligned: Boolean = false,
    IBusCheck : Boolean = false,      // not yet implemented
    DBusCheck : Boolean = false,      // not yet implemented
    MemMode : Int = 0,                // MemMode (rsize and wsize): 0 - small endian, b = 0001, HW = 0011, W = 1111, no 4-byte boundary overlapping
    dataWidth : Int = 32,             // ??
    regLength : Int = 32,             // ??
    IALIGN : Int = 8,                 // ??
    pipelineLength : Int = 0,         // ??
    startUpDelay : Int = 5,           // ??
    maxExecutionDelay : Int = 6,      // ??
    e : Boolean = false,              // not yet implemented
    mul : Boolean = false,            // not yet implemented
    div : Boolean = false,            // not yet implemented
    comp: Boolean = false             // not yet implemented
) extends Component{


  val fpmi = new Bundle{
    val fetch = in Bool()
    val fetchedInstruction = in Bits(dataWidth bits)
    val fetchedPc = in UInt(dataWidth bits)

    val execute = in Bool()
    val executedInstruction = in Bits(dataWidth bits)
    val executedPc = in UInt(dataWidth bits)
    
    val nop = in Bool()

    val trap = in Bool()
    val halt = in Bool()
    val intr = in Bool()
    
    // Commandos sparen?
    val rs1 = in UInt(5 bits)
    val rs2 = in UInt(5 bits)
    val rs1_data = in Bits(dataWidth bits)
    val rs2_data = in Bits(dataWidth bits)
    val rd = in UInt(5 bits)
    val rd_data = in Bits(dataWidth bits)
    val csr_data = in Bits(dataWidth bits)

    // Commandos sparen?
    val pc_next = in UInt(dataWidth bits)

    // Commandos sparen?
    val mem_addr = in UInt(dataWidth bits)
    val mem_rsize = in Bits(dataWidth/8 bits)
    val mem_wsize = in Bits(dataWidth/8 bits)
    val mem_rdata = in Bits(dataWidth bits)
    val mem_wdata = in Bits(dataWidth bits)

    val regs = in Bits(dataWidth * regLength bits)
  }
  
  val csr = new Bundle{
    val mtvec = in Bits(dataWidth bits) // Machine trap-handler base address
    val mepc  = in Bits(dataWidth bits) // Machine exception program counter -> Muss wohl geändert werden?!
    val mcause = in Bits(dataWidth bits) // Machine trap cause
    val mtval = in Bits(dataWidth bits) // Machine bad address or instruction -> Muss wohl geändert werden?!
  }

  val dbg = new Bundle{
    val postReset = out Bool()
    val postResetCycles = out UInt(12 bits)
    val firstFetch = out Bool()
    val postFetchCycles = out UInt(12 bits)

    //? val rs1_data = out Bits(32 bits)
    //? val rs2_data = out Bits(32 bits)
  }

  //? dbg.rs1_data := fpmi.regs(32 * (isa.io.rs1+1) -1 downto 32 * (isa.io.rs1))
  //? dbg.rs2_data := fpmi.regs(32 * (isa.io.rs2+1) -1 downto 32 * (isa.io.rs2))

  // formal ISA, fed with the necessary infromation
  val isa = new Formal_ISA(
    mul = mul,
    div = div,
    catchPcMisaligned = catchPcMisaligned,
    catchMemoryMisaligned = catchMemoryMisaligned
  )
  isa.io.instruction := fpmi.executedInstruction
  isa.io.pc := fpmi.executedPc
  isa.io.rs1_data := fpmi.rs1_data
  isa.io.rs2_data := fpmi.rs2_data
  isa.io.memRead_data := fpmi.mem_rdata
  isa.io.csr_data := fpmi.csr_data
  isa.io.csr_mepc := csr.mepc
  
  // ready when first fetch and after every finished state transition
  val proofCtrl = new Area{
    val postReset = Reg(Bool())
    val postResetCycles = Reg(UInt(12 bits))
    val firstFetch = Reg(Bool())
    val postFetchCycles = Reg(UInt(12 bits))

    when(fpmi.fetch){
      firstFetch := True
    }

    GenerationFlags.formal {
      clockDomain.withoutReset(){
        assumeInitial(postReset === False)
        assumeInitial(postResetCycles === 0)
        assumeInitial(firstFetch === False)
        assumeInitial(postFetchCycles === 0)

        when(clockDomain.isResetActive){
          postReset := True
          postResetCycles := 1
          firstFetch := False
          postFetchCycles := 0
        }.otherwise{  
          when(postReset){
            postResetCycles := postResetCycles + 1
          }
          when(firstFetch){
            postFetchCycles := postFetchCycles + 1
          }
        }
      }
    }

    dbg.postReset := postReset
    dbg.postResetCycles := postResetCycles
    dbg.firstFetch := firstFetch
    dbg.postFetchCycles := postFetchCycles
  }

  val fetchCheck = new Area{
    val valid = out Bool()
    val fullInstructionDone = Reg(UInt(8 bits))
    val insCount = out UInt(8 bits)
    val fetched = out UInt(3 bits)
    val popped = out UInt(3 bits)
    val fetchedExecuted = out Bool()
    val expectedInstr = out Bits(dataWidth bits)
    val expectedPc = out UInt(dataWidth bits)

    if(ProofMode == 0 | ProofMode == 1 | !BMC | ProofMode == 8 | ProofMode == 9){
      
      val fetchedInstr = Vec(Reg(Bits(dataWidth bits)) init(0), 8)
      val fetchedPc	= Vec(Reg(UInt(dataWidth bits)) init(0), 8)
      val nextFetch = Reg(UInt(3 bits)) init(0)
      val nextExecute = Reg(UInt(3 bits)) init(0)

      fetched := nextFetch
      popped := nextExecute
      expectedInstr := fetchedInstr(nextExecute)
      expectedPc := fetchedPc(nextExecute)

      GenerationFlags.formal {
        clockDomain.withoutReset(){
          for(element <- fetchedInstr){
            assumeInitial(element === 0)
          }
          for(element <- fetchedPc){
            assumeInitial(element === 0)
          }

          if(BMC){
            assumeInitial(nextFetch === 0)
          }else{
            assumeInitial(nextFetch === pipelineLength)
          }

          assumeInitial(nextExecute === 0)
          assumeInitial(fullInstructionDone === 0)

          when(fpmi.fetch){
            fetchedInstr(nextFetch) := fpmi.fetchedInstruction
            fetchedPc(nextFetch) := fpmi.fetchedPc
            nextFetch := nextFetch + 1
          }

          when(
            !proofCtrl.postReset
            && (nextExecute < pipelineLength)
            && (fpmi.nop || fpmi.execute || fpmi.trap)
          ){
            nextExecute := nextExecute + 1
            valid := True
            fetchedExecuted := False
          }.otherwise{
            when(proofCtrl.firstFetch && (fpmi.nop || fpmi.execute)){   // firstFetch??  // (nextExecute < nextFetch)?!
              nextExecute := nextExecute + 1
            }
            
            // (nextExecute <= nextFetch) && 
            valid :=  (!fpmi.execute || //!(fpmi.execute || fpmi.nop) ||  // Trap fehlt?
                      ((fpmi.executedInstruction === fetchedInstr(nextExecute)) && (fpmi.executedPc === fetchedPc(nextExecute)))) // && (nextExecute <= nextFetch))  // NOP rausnehmen?
            fetchedExecuted := (fpmi.execute || fpmi.nop) && valid && proofCtrl.firstFetch
          }

          when(fetchedExecuted){
            fullInstructionDone := fullInstructionDone + 1
          }
        }
        insCount := fullInstructionDone
      }
    }else{
      valid := True
      insCount := 0
      fetched := 0
      popped := 0
      fetchedExecuted := False
      expectedInstr := 0
      expectedPc := 0
    }
  }

  val regCheck = new Area{
    val valid = out Bool()
    val errorNr = out UInt(3 bits)  // 0: none, 1: faulty regChange, 2: faulty regRead, 3: faulty write command, 4: faulty write execution, 5: zero reg error
    if(ProofMode == 0 | ProofMode == 2){

      GenerationFlags.formal {
        clockDomain.withoutReset(){
          errorNr := 0
          when(fpmi.execute){
            when(isa.io.regWrite){
              when(isa.io.rd =/= fpmi.rd){
                errorNr := 1
              }
              when(isa.io.regWrite_data =/= fpmi.rd_data && isa.io.rd =/= 0){ //Müsste auch für Reg0 gelten
                errorNr := 2
              }
            }.otherwise{
              when(fpmi.rd =/= 0 || fpmi.rd_data =/= 0){
                errorNr := 3
              }
            }
            when(isa.io.reg1Read){
              when(isa.io.rs1 =/= fpmi.rs1){
                errorNr := 4
              }             
            }
            when(isa.io.reg2Read){
              when(isa.io.rs2 =/= fpmi.rs2){
                errorNr := 5
              }  
            }
          }
          valid := (errorNr === 0)
        }
      }
    }else{
      valid := True
      errorNr := 0
    }
  }

  val regFileCheck = new Area{    // Initialization?!?!
    val valid = out Bool()
    val errorNr = out UInt(4 bits)
    val regChange = out Bool()
    if(ProofMode == 0 | ProofMode == 6){
      GenerationFlags.formal {
        errorNr := 0

        val lastRegs = Reg(Bits(dataWidth * regLength bits))
        regChange := lastRegs =/= fpmi.regs && !clockDomain.isResetActive
        when((fpmi.fetch && !proofCtrl.firstFetch) || fpmi.execute){
          lastRegs := fpmi.regs
        }

        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 1){
          // Zero Reg not Zero after Boot
          when(proofCtrl.firstFetch && fpmi.regs(0, dataWidth bits) =/= 0){
            errorNr := 1
          }
        }

        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 2){
          // Regchange without a Regwrite
          when(!isa.io.regWrite && proofCtrl.firstFetch && regChange){
            errorNr := 2
          }
        }

        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 3){  //??
          // Regchange without a Regwrite (+execute)
          when(fpmi.execute && !isa.io.regWrite && regChange){
            errorNr := 3
          }
        }

        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 4){
          // rd write execution error
          when(fpmi.execute && isa.io.regWrite && isa.io.rd === regProofStart && isa.io.rd =/= 0 && fpmi.regs(isa.io.rd * dataWidth, dataWidth bits) =/= isa.io.regWrite_data){
            errorNr := 4
          }
        }

        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 5){
          // faulty change during write
          when(fpmi.execute && isa.io.regWrite && regProofStart =/= isa.io.rd && fpmi.regs(regProofStart * dataWidth, dataWidth bits) =/= lastRegs(regProofStart * dataWidth, dataWidth bits)){
            errorNr := 5
          }
        }

        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 6){
          // rs1 read error
          when(fpmi.execute && isa.io.rs1 === regProofStart && isa.io.reg1Read && (isa.io.rs1_data =/= lastRegs(isa.io.rs1 * dataWidth, dataWidth bits))){
            errorNr := 6
          }
        }
        if(ProofMode == 0 | RegProofMode == 0 | RegProofMode == 7){
          // rs2 read error
          when(fpmi.execute && isa.io.rs2 === regProofStart && isa.io.reg2Read && (isa.io.rs2_data =/= lastRegs(isa.io.rs2 * dataWidth, dataWidth bits))){
            errorNr := 7
          }
        }

        valid := (errorNr === 0)
      }
    }else{
      valid := True
      errorNr := 0
      regChange := False
    }
  }

  val pcCheck = new Area{ // Initialization
    val valid = out Bool()
    val errorNr = out UInt(2 bits)
    val expected = out UInt(32 bits)
    if(ProofMode == 0 | ProofMode == 3){
      val expectedPc = Reg(UInt(32 bits))

      // collecting the initial pc
      when(!proofCtrl.firstFetch && fpmi.fetch){
        expectedPc := fpmi.fetchedPc
      }

      errorNr := 0
      when(fpmi.execute){
        when(fpmi.executedPc =/= expectedPc){
          errorNr := 1
        }
        when(isa.io.jump){
          expectedPc := isa.io.jumpAddress
          when(fpmi.pc_next =/= isa.io.jumpAddress){
            errorNr := 2
          }
        }.otherwise{
          expectedPc := expectedPc + 4
          when(fpmi.pc_next =/= expectedPc + 4){
            errorNr := 3
          }
        }
      }.otherwise{
        when(fpmi.trap){ // && fpmi.nop){
          /* when(fpmi.executedPc =/= expectedPc){ // Only on Executed Traps?!
            errorNr := 3
          } */
          if(traphandler){
            expectedPc := U(csr.mtvec(31 downto 2) << 2, 32 bits)  // Falsch?
          }else{
            expectedPc := expectedPc + 4
          }
        }
      }
      valid := errorNr === 0
      expected := expectedPc
    }else{
      valid := True
      errorNr := 0
      expected := 0
    }
  }

  val memCheck = new Area{
    val valid = out Bool()
    val errorNr = out UInt(3 bits)
    if(ProofMode == 0 | ProofMode == 4){
      errorNr := 0
      when(fpmi.execute && isa.io.memActive){
        when(isa.io.memAddress =/= fpmi.mem_addr){
          errorNr := 1
        }
        when(isa.io.memWrite){
          when(fpmi.mem_rsize =/= 0){
            errorNr := 2
          }
          when(isa.io.memSize === 1 && fpmi.mem_wsize =/= 1){
            errorNr := 3
          }
          when(isa.io.memSize === 2 && fpmi.mem_wsize =/= 3){
            errorNr := 3
          }
          when(isa.io.memSize === 3 && fpmi.mem_wsize =/= 15){
            errorNr := 3
          }
          when(isa.io.memSize === 1 && fpmi.mem_wdata(7 downto 0) =/= isa.io.memWrite_data(7 downto 0)){
            errorNr := 4
          }
          when(isa.io.memSize === 2 && fpmi.mem_wdata(15 downto 0) =/= isa.io.memWrite_data(15 downto 0)){
            errorNr := 4
          }
          when(isa.io.memSize === 3 && fpmi.mem_wdata =/= isa.io.memWrite_data){
            errorNr := 4
          }
        }.otherwise{
          when(fpmi.mem_wsize =/= 0){
            errorNr := 2
          }
          when(isa.io.memSize === 1 && fpmi.mem_rsize =/= 1){
            errorNr := 3
          }
          when(isa.io.memSize === 2 && fpmi.mem_rsize =/= 3){
            errorNr := 3
          }
          when(isa.io.memSize === 3 && fpmi.mem_rsize =/= 15){
            errorNr := 3
          }
        }
      }.otherwise{
        when(fpmi.execute && isa.io.memActive){
          errorNr := 5
        }
      }
      valid := errorNr === 0
    }else{
      valid := True
      errorNr := 0
    }
  }

  val exceptionCheck = new Area{
    val valid = out Bool()
    val errorNr = out UInt(2 bits)
    if(ProofMode == 0 | ProofMode == 5){  // Right Exceptions thrown?!?! -> checking on a nop
      errorNr := 0
      when(fpmi.execute && isa.io.exception =/= 0){   // isa.io.trap?
        errorNr := 1
      }
      when(fpmi.trap && (isa.io.trap === False)){
        errorNr := 2
      }
      valid := (errorNr === 0) 
    }else{
      errorNr := 0
      valid := True
    }
  }

  val formalProof = new Area{
    GenerationFlags.formal{
      if(BMC){
        assumeInitial(ClockDomain.current.isResetActive)
      }
      clockDomain.withoutReset(){
        assume(isa.io.insNr =/= 39)
        // assume(isa.io.insNr =/= 40)

        if(!Coverage){
            when(proofCtrl.postReset){
            assert(fetchCheck.valid)
            assert(regCheck.valid)
            assert(regFileCheck.valid)
            assert(pcCheck.valid)
            assert(memCheck.valid)
            assert(exceptionCheck.valid)
          }.otherwise{
            when(fetchCheck.fullInstructionDone > 1){
              assert(fetchCheck.valid)
              assert(regCheck.valid)
              assert(regFileCheck.valid)
              assert(pcCheck.valid)
              assert(memCheck.valid)
              assert(exceptionCheck.valid)
            }.otherwise{
              assume(fetchCheck.valid)
              assume(regCheck.valid)
              assume(regFileCheck.valid)
              assume(pcCheck.valid)
              assume(memCheck.valid)
              assume(exceptionCheck.valid)
            }
          }
        }
        
        if(ProofMode == 7 | ProofMode == 0){
          val live1 = new LivenessCheck(
            maxCycles = startUpDelay,
            retrigger = true
          )
          live1.trigger := clockDomain.isResetActive
          live1.property := fpmi.fetch
          live1.active := True
          live1.restart := False
        }
        if(ProofMode == 8 | ProofMode == 0){
          // Liveness 2
          val live2 = new LivenessCheck(
            maxCycles = maxExecutionDelay,
            retrigger = false
          )
          live2.trigger := fpmi.fetch
          live2.property := fetchCheck.fetchedExecuted
          live2.active := !fpmi.halt
          live2.restart := clockDomain.isResetActive

          /*
          // ?
          val live2_1 = new LivenessCheck(
            maxCycles = maxExecutionDelay + maxExecutionDelay,
            retrigger = false
          )
          live2_1.trigger := fpmi.fetch
          live2_1.property := (fetchCheck.fullInstructionDone >= 2)
          live2_1.active := !fpmi.halt
          live2_1.restart := clockDomain.isResetActive 

          */
        }

        if(ProofMode == 9 | ProofMode == 0){
          // Liveness 3
          val live3 = new LivenessCheck(
            maxCycles = maxExecutionDelay,
            retrigger = false
          )
          live3.trigger := fetchCheck.fetchedExecuted
          live3.property := fetchCheck.fetchedExecuted
          live3.active := !fpmi.halt
          live3.restart := clockDomain.isResetActive
        }

        if(ProofMode == 10 | ProofMode == 0){
          // Sanity Checks
          cover(!clockDomain.isResetActive && fpmi.fetch)
          cover(!clockDomain.isResetActive && fpmi.execute)
          cover(!clockDomain.isResetActive && fpmi.nop)
          cover(!clockDomain.isResetActive && fpmi.trap)
        }
      }
    }
  }
}

//Generate the Top Verilog
object Formal_Proof_Module {
  def main(args: Array[String]) {
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      // targetDirectory = "pm"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2())
  }
}

//Generate all Variants for BMC
object Formal_Proof_Module_allSubProofs {
  def main(args: Array[String]) {
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Fetch"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 1, BMC = true))
      .printPruned()
      SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Reg"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 2, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Pc"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 3, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Mem"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 4, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Exception"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 5, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/RegFile_1"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 1))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/RegFile_2"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 2))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/RegFile_3"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 3))
    .printPruned()
    for(i <- 0 to 31){
      SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = s"BMC/RegFile_4/${i+1}"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 4, regProofStart = i, regProofStop = i))
    .printPruned()
    }
    for(i <- 0 to 31){
      SpinalConfig(
        // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
        targetDirectory = s"BMC/RegFile_5/${i+1}"
      ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 5, regProofStart = i, regProofStop = i))
      .printPruned()
    }
    for(i <- 0 to 31){
      SpinalConfig(
        // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
        targetDirectory = s"BMC/RegFile_6/${i+1}"
      ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 6, regProofStart = i, regProofStop = i))
      .printPruned()
    }
    for(i <- 0 to 31){
      SpinalConfig(
        // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
        targetDirectory = s"BMC/RegFile_7/${i+1}"
      ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = true, RegProofMode = 7, regProofStart = i, regProofStop = i))
      .printPruned()
    }
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Live1"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 7, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Live2"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 8, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Live3"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 9, BMC = true))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "BMC/Coverage"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 0, Coverage = true, BMC = true))
    .printPruned()
  }
}

//Generate all Variants for BMC
object Formal_Proof_Module_allSubProofsInduct {
  def main(args: Array[String]) {
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Fetch"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 1, BMC = false))
      .printPruned()
      SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Reg"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 2, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Pc"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 3, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Mem"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 4, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Exception"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 5, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/RegFile/1"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 1))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/RegFile/2"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 2))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/RegFile/3"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 3))
    .printPruned()
    for(i <- 0 to 31){
      SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = s"Induction/RegFile/4/${i+1}"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 4, regProofStart = i, regProofStop = i))
    .printPruned()
    }
    for(i <- 0 to 31){
      SpinalConfig(
        // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
        targetDirectory = s"Induction/RegFile/5/${i+1}"
      ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 5, regProofStart = i, regProofStop = i))
      .printPruned()
    }
    for(i <- 0 to 31){
      SpinalConfig(
        // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
        targetDirectory = s"Induction/RegFile/6/${i+1}"
      ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 6, regProofStart = i, regProofStop = i))
      .printPruned()
    }
    for(i <- 0 to 31){
      SpinalConfig(
        // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
        targetDirectory = s"Induction/RegFile/7/${i+1}"
      ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 6, BMC = false, RegProofMode = 7, regProofStart = i, regProofStop = i))
      .printPruned()
    }
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Live1"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 7, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Live2"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 8, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Live3"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 9, BMC = false))
    .printPruned()
    SpinalConfig(
      // defaultConfigForClockDomains = ClockDomainConfig(resetKind=SYNC, resetActiveLevel=HIGH),
      targetDirectory = "Induction/Sanity"
    ).includeFormal.generateSystemVerilog(new Formal_Proof_ModuleV2(ProofMode = 10, BMC = false))
    .printPruned()
  }
}