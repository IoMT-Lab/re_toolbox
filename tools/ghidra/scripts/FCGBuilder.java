import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.BlockGraph;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;

import java.util.HashMap;
import java.util.List;

public class FCGBuilder extends PCodeVistor{
    GlobalCtx globalCtx;
    Function currentFunction;
    @Override
    public void visit(PcodeOp pcodeOp){
        //we have pcodeOp and use them to find the callinst
        switch (pcodeOp.getOpcode()){
            case PcodeOp.CALLIND:
                break;
            case PcodeOp.CALL:
                //System.out.println("CALL Instruction: "+pcodeOp);
                Address targetAddress = getCallTargetAddress(pcodeOp);
                if(targetAddress != null){
                    //System.out.println("Target Address: "+targetAddress);
                    Function calleeFunction = getCallFunction(targetAddress);
                    if(calleeFunction != null){
                        //System.out.println("Callee Function: "+calleeFunction);
                        if(globalCtx.getFcg()!=null){
                            HashMap<Function,FunctionCall>  fcallMap = globalCtx.getFcg().getFunctionCallMap();
                            if(fcallMap!=null) {
                                FunctionCall fcall = fcallMap.get(currentFunction);
                                if (fcall != null) {
                                    fcall.addCallee(calleeFunction);
                                }
                            }
                        }
                    }
                }
                break;
        }//end of switch
    }
    private Function getCallFunction(Address address){
        if(address ==null) return null;
        return globalCtx.getFunctionManager().getFunctionAt(address);
    }
    private Address getCallTargetAddress(PcodeOp pcodeOp){
        if(pcodeOp.getNumInputs()>0){
            Varnode calltarget = pcodeOp.getInput(0);
            if(calltarget.isAddress()){
                return calltarget.getAddress();
            }
        }
            return null;
    }
    public FCG build(GlobalCtx globalCtx){
        this.globalCtx = globalCtx;
        List<Function> functions = globalCtx.getFunctionList();
        HashMap<Function,List<PcodeOp>> func2Pcode = globalCtx.getFunc2Pcode();
        FCG fcg = new FCG(functions);
        for(Function func : functions){
            List<PcodeOp> ops = func2Pcode.get(func);
            if(ops.size()<=0){
                System.out.println("Function "+func.getName()+" has no ops : external lib function found!");
            }else {
                analyzeFunction(fcg, func, ops);
            }
        }
        return fcg;

    }
    public void analyzeFunction(FCG fcg, Function function,List<PcodeOp> pcodeOps) {
        this.currentFunction = function;
        for(PcodeOp pcodeOp : pcodeOps){
            visit(pcodeOp);
        }
    }
}
