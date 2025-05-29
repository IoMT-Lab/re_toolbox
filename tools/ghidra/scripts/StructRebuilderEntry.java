import ghidra.app.util.headless.HeadlessScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Program;

import java.util.ArrayList;
import java.util.List;

public class StructRebuilderEntry extends HeadlessScript {
    private List<Function> function_list = new ArrayList<Function>();
    private GlobalCtx globalCtx;
    @Override
    protected void run() throws Exception {
        //enableHeadlessAnalysis(true);
        println("STARTING FUNCTION PASS\n");
        Program current_program = getCurrentProgram();
        if(current_program == null){
            println("[x]error: no program found\n");
            return;
        }

        current_program.getFunctionManager().getFunctions(true).forEachRemaining(
                function -> {
                    //println("Function name: " + function.getName()+ " address:"+function.getEntryPoint());
                    function_list.add(function);
                }
        );
        //println(" end of function list");
        println("num of functions: " + function_list.size());
        this.globalCtx = new GlobalCtx(function_list,current_program);
        this.globalCtx.analyze();
    }

}