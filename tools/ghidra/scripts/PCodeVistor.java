import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;

public class PCodeVistor {
    //need to replace with <T>
    //todo!
    public void visit(PcodeOp pcodeOp){
        System.out.println(pcodeOp);
    }
    public void visit(Instruction inst){
        //PcodeOp[] pcodeOps = function.get
        PcodeOp[] pcodeOps = inst.getPcode();
        for(PcodeOp pcodeOp : pcodeOps){
            visit(pcodeOp);
        }
    }
//    public void visit(Function func){
//        func.
//    }
}
