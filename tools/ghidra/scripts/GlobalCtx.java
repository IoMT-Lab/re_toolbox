import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.data.*;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolTable;
import ghidra.program.model.util.CodeUnitInsertionException;
import ghidra.util.exception.CancelledException;
import ghidra.util.task.TaskMonitor;
import ghidra.program.model.symbol.Reference;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

import static ghidra.program.model.data.DataUtilities.ClearDataMode.CHECK_FOR_SPACE;
import static ghidra.program.model.data.DataUtilities.ClearDataMode.CLEAR_ALL_CONFLICT_DATA;

public class GlobalCtx {
    private List<Function> function_list;
    private List<HighFunction> high_function_list;
    private DecompInterface decompInterface = new DecompInterface();
    public Program program;
    private PCodeVistor pcodeVistor = new PCodeVistor();
    private HashMap<Function,List<PcodeOp>> func2Pcode;
    private FCG fcg;
    private FunctionManager functionManager;
    private Set<Function> visited = new HashSet<>();
    private Stack<Function> stack = new Stack<>();
    private Stack<Function> inStack =  new Stack<>();
    public Map<Address, Symbol> addr_sym_map;
    GlobalCtx(List function_list, Program program){
        decompInterface.openProgram(program);

        this.function_list = function_list;
        this.high_function_list = new ArrayList<>();
        this.program = program;
        this.func2Pcode = new HashMap<>();
        this.functionManager = program.getFunctionManager();
    }
    Map<Address, Symbol> analyze_symbols(){
        var ref_manager = this.program.getReferenceManager();
        var symb_table = this.program.getSymbolTable();
        ArrayList<Symbol> tot_vars = new ArrayList<>();
        for(var blk: this.program.getMemory().getBlocks()){
            if(blk.isExecute()){
                var addrs = new AddressSet(blk.getStart(), blk.getEnd());
                var ref_source_iter = ref_manager.getReferenceSourceIterator(addrs, true);
                while(ref_source_iter.hasNext()){
                    var curr_src_addr = ref_source_iter.next();
                    for(var ref : ref_manager.getReferencesFrom(curr_src_addr)){
                        if(ref.isMemoryReference() && ref.getReferenceType().isData()){
                            var symb = symb_table.getPrimarySymbol(ref.getToAddress());
                            if(symb != null){
                                tot_vars.add(symb);
                            }
                        }
                    }
                }
            }
        }


        Map<Address, Symbol> addr_sym_map = new HashMap<>();
        for(var sym : tot_vars){
            System.out.println("Symbol: " + sym + " Type :" + sym.getSymbolType() );
            System.out.println("Symbol address: " + sym.getAddress());
            addr_sym_map.put(sym.getAddress(), sym);
            //current no need to use the reference to do retype
//            for(var sym_ref : sym.getReferences()){
//                var ref_address = sym_ref.getFromAddress();
//                Instruction ref_addr_inst = this.program.getListing().getInstructionAt(ref_address);
//                if(ref_addr_inst != null){
//                    //System.out.println("ref address:" + ref_address + " Pcode:\n");
//                    for(var pcode: ref_addr_inst.getPcode()){
//                        System.out.println(pcode + "\n");
//                        if(pcode.getOutput() != null && pcode.getOutput().isUnique()){
//                            Address curr_addr = pcode.getOutput().getAddress();
//                            //addr_sym_map.put(curr_addr, sym);
//                        }
//
//                    }
//                }
//
//            }
        }
        if(true){
            return addr_sym_map;
        }
        //start===

        Listing listing = this.program.getListing();
        DataTypeManager dtm = this.program.getDataTypeManager();


        DataType baseDT = CharDataType.dataType;
        DataType pointerDT = new PointerDataType(baseDT);

        for(var sym : tot_vars){

            if(Objects.equals(sym.getSymbolType().toString(), "Label")){
                Address addr = sym.getAddress();
                try {

                    listing.clearCodeUnits(addr, addr.add(pointerDT.getLength()), false);

                    DataUtilities.createData(
                            this.program,
                            addr,
                            pointerDT,
                            pointerDT.getLength(),
                            DataUtilities.ClearDataMode.CLEAR_ALL_CONFLICT_DATA);
                    System.out.println("Updated symbol at " + addr + " to pointer type: " + pointerDT.getName());
                } catch(Exception e) {
                    System.err.println("Failed to update symbol at " + addr + ": " + e.getMessage());
                }
            }
        }
        for(var sym : tot_vars){
            System.out.println("Symbol: " + sym + " Type :" + sym.getSymbolType());
        }
        //end====
        return addr_sym_map;
    }
    void analyze() throws CodeUnitInsertionException, CancelledException {
        for(Function function :function_list){
            analyze(function);
        }
        this.fcg =  buildFCG();
        List<Function> functions_ordered = sort(this.fcg);
        System.out.println("After sorting function num: "+functions_ordered.size());
        //then we can start analyzing from the leaf funciton
        updateFunctionList(functions_ordered);
        for(Function f: functions_ordered){
            HighFunction highFunction = decompileFunction(f);
            if(highFunction !=null){
                this.high_function_list.add(highFunction);
            }
        }

        //saveAsCSV("/home/kali/Desktop/testdump.csv");
        System.out.println("Start Field Analysis");
        this.addr_sym_map = analyze_symbols();
        StructBuilder structBuilder = new StructBuilder(this);
        structBuilder.analyze();

        AliasAnalyzer aliasAnalyzer = new AliasAnalyzer(this);
        aliasAnalyzer.analyze();
        //segmentAnalyze();
        //globaldataAnalyze();
//        for(Function function :function_list){
//            dump(function);
//        }
        //saveAsCSV("/tmp/decompiled_result.csv");
        //globaldataAnalyze();
        //String target_file_name = this.program.getDomainFile().getName();
        saveAsTXT("/tmp/decompiled_result");
        decompInterface.dispose();

    }
    void globaldataAnalyze(){
        Listing listing = program.getListing();

        // Iterate through all instructions in the program
        InstructionIterator instructions = listing.getInstructions(true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();

            // Check for assignments involving stack and .data segment variables
            if (isAssignmentOperation(instruction)) {
                //System.out.println("Current Instruction: "+ instruction);
                propagateTypeFromStackToData(instruction);
            }
        }
    }
    void segmentAnalyze(){
        //scan the data and bss segment
        System.out.println("Start analyzing the data segment and bss segment");
        Memory memory = program.getMemory();
        Listing listing = program.getListing();
        SymbolTable symbolTable = program.getSymbolTable();
        for(MemoryBlock mem_block : memory.getBlocks()){
            String blockName = mem_block.getName().toLowerCase();
            if (blockName.contains(".data") || blockName.contains(".bss")) {
                System.out.println("Scanning block: " + blockName);
                scanBlockWithoutSymbols(mem_block, listing);
            }
        }
    }
    String dump(Function function){
        DecompileResults dresult = decompInterface.decompileFunction(function,30,TaskMonitor.DUMMY);
        if(!dresult.decompileCompleted()){
            System.out.println("Error decompiling "+function);
            return null;
        }
        String decompiledCode = dresult.getDecompiledFunction().getC();
        System.out.println("Decompiled function: "+function.getName());
        System.out.println("Decompiled code: "+decompiledCode);
        return decompiledCode;
    }
    //has some errors
    //need to correct to get the csv format
    void saveAsCSV(String file_path)  {
        try (FileWriter fw = new FileWriter(file_path)){
            for(Function function:function_list){
                fw.append(function.getName()).append(",")
                        .append(dump(function)).append("\n");
            }
        }catch (IOException e){
            System.out.println("Error saving "+file_path);
        }
    }

    void clearTXTunderDirectory(File dir) {
        File[] files = dir.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    clearTXTunderDirectory(file);
                }
                file.delete();
            }
        }
    }

    void saveAsTXT(String dir_path) {
        File dir = new File(dir_path);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        else{
            File[] files = dir.listFiles((file) -> file.isFile() && file.getName().endsWith(".txt"));
            for(var file : files){
                clearTXTunderDirectory(file);
            }
        }
        for (Function function : function_list) {
            String filename = function.getName() + ".txt";
            File file = new File(dir, filename);
            try (FileWriter fw = new FileWriter(file)) {
                fw.write(dump(function));
            } catch (IOException e) {
                System.out.println("Error saving " + file.getAbsolutePath());
            }
        }
    }


    //How to use Maven? todo!
//    void saveAsJSON(String file_path)  {
//        Gson gson = new GsonBuilder().setPrettyPirinting().create();
//    }
    private void scanBlockWithoutSymbols(MemoryBlock block, Listing listing) {
        Address start = block.getStart();
        Address end = block.getEnd();
        Address current = start;


        while (current.compareTo(end) < 0 ) {
            ReferenceIterator references = program.getReferenceManager().getReferencesTo(current);

            while (references.hasNext() ) {
                Reference reference = references.next();
                Address fromAddress = reference.getFromAddress();
                Function function = listing.getFunctionContaining(fromAddress);

                if (function != null) {
                    System.out.println("Address: " + current + " referenced in function: " + function.getName() +
                            " at " + function.getEntryPoint());
                    if (isCopiedToStack(fromAddress, listing)) {
                        System.out.println("  --> This variable is copied to the stack.");
                    }
                    propagateTypeIfStruct(fromAddress, listing);
                }
            }

            current = current.add(1);
        }
    }
    private boolean isCopiedToStack(Address fromAddress, Listing listing) {
        Instruction instruction = listing.getInstructionAt(fromAddress);

        while (instruction != null) {
            //todo replace to ARM
            if (instruction.getMnemonicString().startsWith("MOV")) {
                Object[] operands = instruction.getOpObjects(1);
                for (Object operand : operands) {
                    if (operand.toString().contains("[RSP") || operand.toString().contains("[RBP")) {
                        return true;
                    }
                }
            }

            instruction = instruction.getNext();
        }

        return false;
    }
    private void propagateTypeIfStruct(Address fromAddress, Listing listing) {
        Instruction instruction = listing.getInstructionAt(fromAddress);

        while (instruction != null ) {
            // Check if the instruction is a MOV or similar copy operation
            if (instruction.getMnemonicString().startsWith("MOV")) {
                Object[] operands = instruction.getOpObjects(0); // Source operands
                Object[] destOperands = instruction.getOpObjects(1); // Destination operands

                if (operands.length > 0 && destOperands.length > 0) {
                    // Retrieve the types of source and destination
                    DataType srcType = getDataTypeForOperand(operands[0]);
                    DataType destType = getDataTypeForOperand(destOperands[0]);

                    // Type propagation: if one operand is a structure type, propagate to the other
                    if (srcType instanceof Structure && destType == null) {
                        setOperandDataType(destOperands[0], srcType);
                        System.out.println("  --> Propagated structure type to destination.");
                    } else if (destType instanceof Structure && srcType == null) {
                        setOperandDataType(operands[0], destType);
                        System.out.println("  --> Propagated structure type to source.");
                    }
                }
            }

            // Get the next instruction
            instruction = instruction.getNext();
        }
    }

    private DataType getDataTypeForOperand(Object operand) {
        if (operand instanceof Address) {
            Data data = program.getListing().getDataAt((Address) operand);
            if (data != null) {
                return data.getDataType();
            }
        }
        return null;
    }

    private void setOperandDataType(Object operand, DataType dataType) {
        if (operand instanceof Address) {
            Address address = (Address) operand;
            Data data = program.getListing().getDataAt(address);
            try {
                // Apply the data type to the address using DataUtilities
                DataUtilities.createData(program, address, dataType, -1, CHECK_FOR_SPACE);
            } catch (Exception e) {
                System.out.println("Failed to apply data type at address: " + address + " Error: " + e.getMessage());
            }
        }
    }
    void analyze(Function function){
        List<PcodeOp> pcodeOpsList = new ArrayList<>();
        //System.out.println("Analyzing: " + function.getName());
        Listing listing = program.getListing();
        InstructionIterator instructionIterator = listing.getInstructions(function.getBody(),true);
        while(instructionIterator.hasNext()){
            Instruction instruction = instructionIterator.next();
            for(PcodeOp pcodeOp: instruction.getPcode()){
                pcodeOpsList.add(pcodeOp);
            }
        }
        func2Pcode.put(function,pcodeOpsList);


    }
    private boolean isAssignmentOperation(Instruction instruction) {
        //System.out.println("checking the instruction");
        String mnemonic = instruction.getMnemonicString();
        return mnemonic.equals("MOV") || mnemonic.equals("LEA");
    }

    private boolean isStackVariable(Address address, Instruction instruction) {
        // Check if address space is stack space
        if (address.isStackAddress()) {
            return true;
        }

        // If the above is not sufficient (some addresses may appear as stack but not mapped properly),
        // try to find a corresponding stack variable from the function's stack frame.
        Function func = program.getFunctionManager().getFunctionContaining(instruction.getMinAddress());
        if (func != null) {
            StackFrame frame = func.getStackFrame();
            if (frame != null) {
                Variable var = frame.getVariableContaining((int) address.getOffset());
                if (var != null) {
                    return true;
                }
            }
        }

        return false; // Not identified as a stack variable
    }

    private void printDataSegmentInfo(Address address) {
        // Retrieve the Data object at the given address
        Data data = program.getListing().getDataAt(address);
        if (data == null) {
            System.out.println("No data defined at " + address);
            return;
        }

        DataType dt = data.getDataType();
        if (dt == null) {
            System.out.println("Data at " + address + " has no type information.");
            return;
        }

        System.out.println("Data at " + address + " is of type: " + dt.getName());
        System.out.println("Data length: " + data.getLength());

        // If the data type is a structure, we can iterate over its components
        if (dt instanceof Structure) {
            Structure structType = (Structure) dt;
            System.out.println("Structure " + structType.getName() + " has " + structType.getNumComponents() + " components:");

            for (int i = 0; i < structType.getNumComponents(); i++) {
                DataType componentType = structType.getComponent(i).getDataType();
                String fieldName = structType.getComponent(i).getFieldName();
                long fieldOffset = structType.getComponent(i).getOffset();
                System.out.println("  Field " + i + ": "
                        + (fieldName != null ? fieldName : "unnamed")
                        + ", type: " + componentType.getName()
                        + ", offset: " + fieldOffset);
            }
        }
    }
    private Address resolveEffectiveAddress(Object[] operands, Instruction instruction) {
        for (Object operand : operands) {
            if (operand instanceof Address) {
                // If the operand is a direct memory address, return it.
                return (Address) operand;
            }
            else if (isRegisterOperand(operand)) {
                // If the operand is a register, trace back its source to find if it comes from stack or heap (or data segment).
                Address tracedAddress = traceOperandSource(operand, instruction);
                if (tracedAddress != null) {
                    return tracedAddress;
                }
            }
            else {
                // If the operand is neither an address nor a register, we still attempt to trace its source.
                Address tracedAddress = traceOperandSource(operand, instruction);
                if (tracedAddress != null) {
                    return tracedAddress;
                }
            }
        }
        return null; // No valid memory address found.
    }
    private void propagateTypeFromStackToData(Instruction instruction) {
        // MOV dest, src format:
        // dest is getOpObjects(0), src is getOpObjects(1)
        Object[] destOperands = instruction.getOpObjects(0);
        Object[] srcOperands = instruction.getOpObjects(1);

        Address destAddress = resolveEffectiveAddress(destOperands, instruction);
        Address srcAddress = resolveEffectiveAddress(srcOperands, instruction);


        if (srcAddress == null || destAddress == null) {
            return; // Cannot proceed without valid addresses
        }
        printDataSegmentInfo(srcAddress);
        printDataSegmentInfo(destAddress);
        // Check roles:
        //  src is data segment, dest is stack variable
        boolean srcIsData = isDataSegmentVariable(srcAddress);
        boolean destIsStack = isStackVariable(destAddress, instruction);

        // If the instruction effectively moves data -> stack,
        // after analysis, we want to apply the stack variable's type back to the data segment.
        if (srcIsData && destIsStack) {

            DataType stackType = getStackTypeFromVariable(destAddress, instruction);
            if (stackType == null) {
                System.out.println("No stack type found for address: " + destAddress);
                return;
            }

            // If it's a structure, apply it to the .data variable at srcAddress
            if (stackType instanceof Structure) {
                Structure structType = (Structure) stackType;
                int structSize = structType.getLength();
                try {
                    // Clear the data segment area to avoid conflicts
                    Address endAddress = srcAddress.add(structSize - 1);
                    program.getListing().clearCodeUnits(srcAddress, endAddress, false);

                    // Apply the structure at srcAddress
                    DataUtilities.createData(program, srcAddress, structType, -1, DataUtilities.ClearDataMode.CLEAR_ALL_CONFLICT_DATA);
                    System.out.println("Applied structure type " + structType.getName() + " to .data variable at " + srcAddress);
                } catch (Exception e) {
                    System.out.println("Failed to apply type to .data variable at " + srcAddress + ": " + e.getMessage());
                }
            } else {
                System.out.println("Stack type is not a structure, cannot apply to data segment.");
            }
        } else {
            System.out.println("Conditions not met to apply structure type. "
                    + "isDataSegment(src): " + srcIsData
                    + ", isStackVariable(dest): " + destIsStack);
        }
    }


    private DataType getStackTypeFromVariable(Address stackAddress, Instruction instruction) {
        // Get the function that contains this instruction
        Function func = program.getFunctionManager().getFunctionContaining(instruction.getMinAddress());
        if (func == null) return null;
        StackFrame frame = func.getStackFrame();
        if (frame == null) return null;

        // Try to find a variable that contains this stack address offset
        Variable var = frame.getVariableContaining((int) stackAddress.getOffset());
        if (var != null) {
            return var.getDataType();
        }
        return null;
    }

    private boolean isDataSegmentVariable(Address address) {
        MemoryBlock block = program.getMemory().getBlock(address);
        if (block == null) return false;
        String blockName = block.getName().toLowerCase();
        return blockName.contains("data");
    }

    private boolean isStackVariableAddress(Address address, Instruction instruction) {
        if (address.isStackAddress()) {
            return true;
        }
        // If not recognized, try another approach:
        // For example, if address belongs to function's stack frame:
        Function func = program.getFunctionManager().getFunctionContaining(instruction.getMinAddress());
        if (func != null && func.getStackFrame() != null) {
            Variable var = func.getStackFrame().getVariableContaining((int)address.getOffset());
            return var != null;
        }
        return false;
    }



    private boolean isRegisterOperand(Object operand) {

        if (operand instanceof Register) {
            return true;
        }
        if (operand instanceof String) {
            String opStr = ((String) operand).toUpperCase();
            return opStr.matches("RAX|RBX|RCX|RDX|RSI|RDI|RSP|RBP|EAX|EBX|ECX|EDX|ESI|EDI|ESP|EBP|AX|BX|CX|DX|SI|DI|SP|BP|R\\d+");
        }
        return false;
    }

    private Address traceOperandSource(Object operand, Instruction instruction) {
        Instruction prevInstruction = instruction.getPrevious();

        while (prevInstruction != null) {

            Object[] prevDestOperands = prevInstruction.getOpObjects(0);
            Object[] prevSrcOperands = prevInstruction.getOpObjects(1);

            // Check if the previous instruction defines 'operand'
            for (Object prevDestOperand : prevDestOperands) {
                if (operand.equals(prevDestOperand)) {

                    for (Object prevSrcOperand : prevSrcOperands) {
                        if (prevSrcOperand instanceof Address) {
                            Address addr = (Address) prevSrcOperand;
                            // Check if it's stack, heap, or data
                            if (isStackAddress(addr, prevInstruction)) {
                                return addr;
                            } else if (isHeapAddress(addr)) {
                                return addr;
                            } else if (isDataSegmentVariable(addr)) {
                                return addr;
                            } else {
                                // If it doesn't belong to known segments, still return it
                                return addr;
                            }
                        }
                        else if (isRegisterOperand(prevSrcOperand)) {

                            Address deeperAddr = traceOperandSource(prevSrcOperand, prevInstruction);
                            if (deeperAddr != null) {
                                return deeperAddr;
                            }
                        }
                        else {
                            Address deeperAddr = traceOperandSource(prevSrcOperand, prevInstruction);
                            if (deeperAddr != null) {
                                return deeperAddr;
                            }
                        }
                    }
                }
            }

            prevInstruction = prevInstruction.getPrevious();
        }

        return null; // Unable to trace a valid memory source
    }

    private boolean isStackAddress(Address address, Instruction instruction) {
        // Check if address belongs to the stack.
        // For example, stack addresses often come from [RBP - offset] or are in the stack space.
        if (address.isStackAddress()) {
            return true;
        }

        // Additionally, try looking up the function stack frame:
        Function func = program.getFunctionManager().getFunctionContaining(instruction.getMinAddress());
        if (func != null && func.getStackFrame() != null) {
            Variable var = func.getStackFrame().getVariableContaining((int)address.getOffset());
            if (var != null) {
                return true;
            }
        }
        return false;
    }

    private boolean isHeapAddress(Address address) {
        long addrValue = address.getOffset();
        return (addrValue >= 0x600000 && addrValue < 0x700000);
    }



    private void applyTypeToDataSegmentVariable(Address dataAddress, DataType dataType) {
        //System.out.println("apply the stack type to the data segment variable.");
        try {
            DataUtilities.createData(program, dataAddress, dataType, -1, CLEAR_ALL_CONFLICT_DATA);
        } catch (Exception e) {
            System.out.println("Failed to apply type to .data variable at " + dataAddress + ": " + e.getMessage());
        }
    }



    private Address getAddressOperand(Object operand) {
        if (operand instanceof Address) {
            return (Address) operand;
        }
        return null;
    }



    private HighFunction decompileFunction(Function function){
        DecompileResults results = this.decompInterface.decompileFunction(function,30, TaskMonitor.DUMMY);
        if(results.decompileCompleted()){
            return results.getHighFunction();
        }
        return null;
    }

    public List<Function> getFunctionList(){
        return function_list;
    }
    public HashMap<Function, List<PcodeOp>> getFunc2Pcode(){
        return func2Pcode;
    }
    public FunctionManager getFunctionManager(){
        return functionManager;
    }
    public FCG getFcg(){
        return fcg;
    }
    public List<HighFunction> getHighFunctionList(){
        return high_function_list;
    }
    public Program getProgram(){
        return this.program;
    }
    //build function call graph by using the call inst
    FCG buildFCG(){
        FCGBuilder fcgBuilder = new FCGBuilder();
        return fcgBuilder.build(this);
    }
    void updateFunctionList(List<Function> function_list){
        this.function_list = function_list;
    }
    //need to replace it by weak sort
    //todo!
    public List<Function> sort(FCG fcg) {
        for (Function function : fcg.getFunctionCallMap().keySet()) {
            if (!visited.contains(function)) {
                if (dfs(function, fcg.getFunctionCallMap())) {
                    System.out.println("Funciton Call Graph contains a cycle");
                    return Collections.emptyList();
                }
            }
        }

        List<Function> sortedList = new ArrayList<>();
        while (!stack.isEmpty()) {
            sortedList.add(stack.pop());
        }
        return sortedList;
    }

    private boolean dfs(Function function, HashMap<Function, FunctionCall> functionCallMap) {
        visited.add(function);
        inStack.add(function);

        for (Function callee : functionCallMap.get(function).callee_functions) {
            if (!visited.contains(callee) && dfs(callee, functionCallMap)) {
                return true;
            } else if (inStack.contains(callee)) {
                return true;
            }
        }

        inStack.remove(function);
        stack.push(function);
        return false;
    }
}
