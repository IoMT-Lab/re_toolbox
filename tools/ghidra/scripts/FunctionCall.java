import ghidra.program.model.listing.Function;

import java.util.ArrayList;
import java.util.List;

public class FunctionCall {
    String function_name;
    Function function;
    List<Function> callee_functions;
    List<Function> caller_functions;
    GlobalCtx globalCtx;
    FunctionCall(String function_name, Function function){
        this.function_name = function_name;
        this.callee_functions = new ArrayList<>();
        this.caller_functions = new ArrayList<>();
        //this.globalCtx = globalCtx;
    }
    public void updateGlobalCtx(GlobalCtx globalCtx){
        this.globalCtx = globalCtx;
    }
    public void addCallee(Function func){
        callee_functions.add(func);
        if(globalCtx != null){
            if(globalCtx.getFcg()!=null){
                if(globalCtx.getFcg().getFunctionCallMap()!=null){
                    globalCtx.getFcg().getFunctionCallMap().get(func).addCaller(function);
                }
            }
        }
    }
    public void addCaller(Function func){
        caller_functions.add(func);
    }
}
