import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.app.decompiler.*;

public class DecompileFile extends GhidraScript {

    @Override
    public void run() throws Exception {

        DecompInterface decompiler = new DecompInterface();
	// get default decompiler config
	//decompiler.setOptions(currentProgram.getOptions("Decompiler"));

        decompiler.openProgram(currentProgram);
        FunctionManager functionManager = currentProgram.getFunctionManager();
        FunctionIterator functions = functionManager.getFunctions(true);
        while (functions.hasNext()) {
            Function function = functions.next();
            DecompileResults results = decompiler.decompileFunction(function, 60, monitor);
            if (results.getDecompiledFunction() != null) {
                String decompiledCode = results.getDecompiledFunction().getC();
                println(decompiledCode);
            } else {
                println("Decompilation failed: " + results.getErrorMessage());
            }
        }
        println("DONE");

        decompiler.dispose();
    }
}
