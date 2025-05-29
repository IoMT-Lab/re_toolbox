import ghidra.program.model.listing.Function;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;


public class FCG {
    HashMap<Function,FunctionCall> functionCallMap;
    FCG(List<Function> functions){
        this.functionCallMap = new HashMap<>();
        for(Function func : functions){
            functionCallMap.put(func,new FunctionCall(func.getName(), func));
        }
    }
    public void updateFCG(Function func){
        if(!functionCallMap.containsKey(func)){
            functionCallMap.put(func,new FunctionCall(func.getName(), func));
        }
    }
    public boolean containsFunction(Function func){
        return functionCallMap.containsKey(func);
    }
    public HashMap<Function,FunctionCall> getFunctionCallMap(){
        return functionCallMap;
    }
}
