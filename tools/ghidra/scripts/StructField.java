import ghidra.program.model.address.Address;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;

public class StructField {
    private int size;
    PcodeOpAST pcode;
    Address struct_address;
    StructField(int size, PcodeOpAST pcode) {
        this.size = size;
        this.pcode = pcode;
        this.struct_address = pcode2addr(pcode);
    }
    Address pcode2addr(PcodeOpAST pcode) {
        return pcode.getSeqnum().getTarget();
    }

    Integer getSize(){
        return size;
    }
    Address getAddress(){
        return pcode2addr(pcode);
    }

}
