import generic.stl.Pair;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.pcode.*;
import ghidra.program.model.symbol.SourceType;
import ghidra.program.model.util.CodeUnitInsertionException;
import ghidra.util.exception.InvalidInputException;
import ghidra.program.model.mem.MemoryBlock;
import java.util.*;

public class StructBuilder extends PCodeVistor{
    GlobalCtx globalCtx;
    HashMap<HighFunction, List<PcodeOpAST>> func2PcodeAST;
    HashMap<HighFunction,StructFieldArray> hfunctionListHashMap = new HashMap<>();
    HighFunction currentHighFunction;
    Deque<PcodeOpAST> trace_deque = new ArrayDeque<>();
    Map<Long,PcodeOpAST> offset2stackPcodeAST = new HashMap<>();
    List<PcodeOpAST> structhead_lists = new ArrayList<>();
    List<Pair<DataType,PcodeOpAST>> type_list = new ArrayList<>();
    HashMap<PcodeOpAST,Pair<Function,Integer>> sourceOp_function_map = new HashMap<>();
    Map<Pair<Function,Integer>, DataType> function_args_size_map = new HashMap<>();
    @Override
    public void visit(PcodeOp pcodeOp){
        //we have pcodeOp and use them to find the callinst
        //currently, we don't use this flat pcode format to do analysis.
        switch (pcodeOp.getOpcode()){
            case PcodeOp.STORE:
                System.out.println("STORE Inst: ");
                System.out.println("0: "+pcodeOp.getInput(0) +" 1" +pcodeOp.getInput(1)+" 2" + pcodeOp.getInput(2));
                System.out.println("0 def"+ pcodeOp.getInput(0).getDef());
                System.out.println("1 def"+ pcodeOp.getInput(1).getDef());
                System.out.println("2 def"+ pcodeOp.getInput(2).getDef());
                break;
        }//end of switch
    }
    private boolean VarnodeEqual(Varnode v1, Varnode v2){
        if(v1 == null || v2 == null) return false;
        if(v1.getAddress() == v2.getAddress()){
            return true;
        }
        else
            return false;
    }
    private PcodeOpAST findLastUser(PcodeOpAST pcodeOpAST, int input_index){
        //backward trace to find the creater
        List<PcodeOpAST> current_pcode_list = func2PcodeAST.get(currentHighFunction);
        int pcode_index = 0;
        for(int i =0 ; i < current_pcode_list.size(); i++){
            if(current_pcode_list.get(i).equals(pcodeOpAST)){
                //we find the Last User
                pcode_index = i;
            }
        }
        //System.out.println("found current index: "+pcode_index);
        //System.out.println("68: "+ current_pcode_list.get(pcode_index-4) + "  "+ current_pcode_list.get(pcode_index-4).getOutput());
        //System.out.println("equal?: "+ PcodeOpASTEqual(current_pcode_list.get(pcode_index-4).getOutput(), pcodeOpAST.getInput(input_index)) );
        for(int i = pcode_index-1 ; i >0; i--){
            if(current_pcode_list.get(i).getOutput()!=null && VarnodeEqual(current_pcode_list.get(i).getOutput(), (pcodeOpAST.getInput(input_index)))){
                //we find the Last User
                return current_pcode_list.get(i);
            }
        }
        //can't find => may be caused by branch and loop
        //indicating we need to find a branch and bb to do forward.
        //todo!
        return null;
    }
    private PcodeOpAST findNextUse(PcodeOpAST pcodeOpAST,int input_index){
        List<PcodeOpAST> current_pcode_list = func2PcodeAST.get(currentHighFunction);
        int pcode_index = 0;
        for(int i =0 ; i < current_pcode_list.size(); i++){
            if(current_pcode_list.get(i).equals(pcodeOpAST)){
                //we find the Last User
                pcode_index = i;
            }
        }
        for(int i = pcode_index+1; i < current_pcode_list.size(); i++){
            int arg_num = current_pcode_list.get(i).getNumInputs();
            for(int arg_index = 0 ; arg_index < arg_num ; arg_index++){
                if(current_pcode_list.get(i).getOutput()!=null && VarnodeEqual(current_pcode_list.get(i).getInput(arg_index), pcodeOpAST.getOutput())){
                    // we find the nex use
                    return current_pcode_list.get(i);
                }
            }
        }
        return null;
    }
    private void searchField(PcodeOpAST pcodeOpAST){
        int input_num = pcodeOpAST.getNumInputs();
        if(input_num>=1){
            for(int i = 0 ; i < input_num ; i++){
                if(pcodeOpAST.getInput(i).toString().contains("stack")){
                    //we find a stack var can could be regard as a start address
                    System.out.println("Head Address at "+ pcodeOpAST);
                    structhead_lists.add(pcodeOpAST);
                }else if(pcodeOpAST.getInput(i).toString().contains("const")){
                    //we find a const var, which may represent a stack address,
                    //lookup whether there is a stack variable use this const
                    System.out.println("Const :" + pcodeOpAST.getInput(i) + pcodeOpAST.getInput(i).getOffset());
                    PcodeOpAST sourcePcode = offset2stackPcodeAST.get(pcodeOpAST.getInput(i).getOffset());
                    if(sourcePcode!=null){
                        //we find the head offset and sourcePcode
                        System.out.println("Source pcode: " + sourcePcode);
                        structhead_lists.add(sourcePcode);
                    }
                } else if (pcodeOpAST.getInput(i).toString().contains("unique")) {
                    PcodeOpAST last_user = findLastUser(pcodeOpAST,i);
                    if(last_user != null){
                        trace_deque.addLast(last_user);
                    }
                }else{
                    System.out.println("some thing to do with: "+ pcodeOpAST);
                }
            }
        }
    }
    public void visit(PcodeOpAST pcodeOpAST, StructFieldArray current_function_field_array){
        System.out.println("PcodeOpsAST: "+pcodeOpAST);
        if(pcodeOpAST.getOutput()!=null && pcodeOpAST.getOutput().toString().contains("stack")){
            //update stack map
            Address stack_address = pcodeOpAST.getOutput().getAddress();
            offset2stackPcodeAST.put(stack_address.getOffset(), pcodeOpAST);
            //System.out.println("stack offset : " + pcodeOpAST.getOutput().getOffset());
        }

        switch (pcodeOpAST.getOpcode()){
            case PcodeOp.CALL:
                int input_nums = pcodeOpAST.getNumInputs();
                if(input_nums <=1) {break;}
                else {
                    //analyze the argument
                    //input 1 ->first argument, input 2-> second argument ...

                    for(int arginde = 1; arginde<input_nums; arginde++) {
                        //we need to implement the backward analyze in order to find the varnode's user(define)
                        //System.out.println("searching PcodeOpAST: " +pcodeOpAST.getInput(arginde));
                        //System.out.println("Last PcodeOpAST: "+findLastUser(pcodeOpAST, arginde));
                        PcodeOpAST last_user = findLastUser(pcodeOpAST, arginde);
                        //System.out.println(last_user);
                        //System.out.println(last_user.toString().contains("stack"));
                        if(last_user!=null){
                            trace_deque.addLast(last_user);
                            //
                            Function callee = globalCtx.getProgram().getFunctionManager().getFunctionAt( pcodeOpAST.getInput(0).getAddress());
                            if(callee!=null) {
                                Pair<Function,Integer> func_int_pair =  new Pair<Function,Integer>(callee,arginde);
                                function_args_size_map.put(func_int_pair, null);
                                //need to change due to mult use of address!
                                //todo!
                                sourceOp_function_map.put(last_user, func_int_pair);

                            }
                        }
//                        while (!trace_deque.isEmpty()){
//                            PcodeOpAST tracing = trace_deque.pollFirst();
//                            PcodeOpAST lastPcode = findLastUser(tracing,arginde);
//                            if(lastPcode==null){ break; }
//                            last_user=lastPcode;
//                        }
//                        //we get a stack varnode and regard it as a start filed of a structure
//                        System.out.println("start address of stack: " + last_user);
                    }
                }
                break;
            case PcodeOpAST.COPY:
                StructField new_field = new StructField(pcodeOpAST.getOutput().getSize(),pcodeOpAST);
                current_function_field_array.addStructField(new_field);
                //System.out.println("COPY Inst: " + new_field.getSize());
                break;
            case PcodeOpAST.STORE:
                //System.out.println("PcodeOpsAST: "+pcodeOpAST);
                //System.out.println("deref: " + pcodeOpAST.getInput(0).getPCAddress());
                break;

        }
    }
    StructBuilder(GlobalCtx globalCtx){
        this.globalCtx = globalCtx;
        List<HighFunction> highFunctions = globalCtx.getHighFunctionList();
        this.func2PcodeAST = getFunc2PcodeAST(highFunctions);
    }
    HashMap<HighFunction, List<PcodeOpAST>> getFunc2PcodeAST(List<HighFunction> highFunction){
        HashMap<HighFunction, List<PcodeOpAST>> func2PcodeAST = new HashMap<>();
        for(HighFunction hfunc: highFunction){
            Iterator<PcodeOpAST> pcodeOpASTIterator = hfunc.getPcodeOps();
            List<PcodeOpAST> pcodeOpASTs = new ArrayList<>();
            while (pcodeOpASTIterator.hasNext()){
                PcodeOpAST pcodeOpAST = pcodeOpASTIterator.next();
                pcodeOpASTs.add(pcodeOpAST);
            }
            func2PcodeAST.put(hfunc, pcodeOpASTs);
        }
        return func2PcodeAST;
    }

    void analyze() throws CodeUnitInsertionException {
        for(HighFunction hfunc : func2PcodeAST.keySet()){
            structhead_lists.clear();
            hfunctionListHashMap.put(hfunc, new StructFieldArray(hfunc));
            this.currentHighFunction = hfunc;
            analyzeHighFunction(hfunc);
            analyzeStackStruct(hfunc);
            buildType();
            //structFieldArray.add(new StructFieldArray(hfunc));
        }
    }
    void analyzeStackStruct(HighFunction hfunc){
        StructFieldArray structFieldArray = hfunctionListHashMap.get(hfunc);
        System.out.println("head num: " + structhead_lists.size());
        for (PcodeOpAST structheadList : structhead_lists) {
            System.out.println(structheadList);
        }
        type_list = structFieldArray.analyzeHeadList(structhead_lists);
    }
    void analyzeHighFunction(HighFunction hfunction){
        trace_deque.clear();
        StructFieldArray current_hfunction_structlist = hfunctionListHashMap.get(hfunction);
        System.out.println("Function Name: " + hfunction.getFunction().getName());
        if(!hfunction.getFunction().getName().contains("1139")) return;
        //System.out.println("args " + hfunction.getFunction().getParameters());
        LocalSymbolMap localSymbolMap = hfunction.getLocalSymbolMap();
        //System.out.println(localSymbolMap);
        HashMap<Varnode,PcodeOp> user_map = new HashMap<>();
        int num = 0;
        for(PcodeOpAST pcodeOpAST : func2PcodeAST.get(hfunction)){
//            System.out.println(pcodeOp);
//            //System.out.println(pcodeOp.getOutput());
//            user_map.put(pcodeOp.getOutput(),pcodeOp);
            //num+=1;

            visit(pcodeOpAST,current_hfunction_structlist);
        }
        while(!trace_deque.isEmpty()){
            PcodeOpAST pcodeOpAST = trace_deque.removeFirst();
            searchField(pcodeOpAST);
        }
        System.out.println("the function pcode use map size: "+ user_map.size());
        System.out.println("the function pcode size: "+ num);
    }

    private void buildType() throws CodeUnitInsertionException{
        if(type_list==null || type_list.isEmpty()) return;
        DataTypeManager dtm = globalCtx.getProgram().getDataTypeManager();
        Listing listing = globalCtx.getProgram().getListing();
        for(Pair<DataType,PcodeOpAST> pcodeOpASTPair : type_list){
            //intersect structure size
            DataType dt = dtm.addDataType(pcodeOpASTPair.first, DataTypeConflictHandler.REPLACE_HANDLER);
            //update the type information
            //use the function signature to update the type information
            //always  select the smallest one as the correct type
            DataType current_struct_type = function_args_size_map.get(sourceOp_function_map.get(pcodeOpASTPair.second));
            if(current_struct_type==null || current_struct_type.getLength()>dt.getLength()){ current_struct_type = dt;}
            function_args_size_map.put(sourceOp_function_map.get(pcodeOpASTPair.second),current_struct_type);

        }
        for(Pair<DataType,PcodeOpAST> pcodeOpASTPair : type_list){
            //There are problems, we need to change the stack to merge some field and create a struct
            //but how to select the correct address for changing the datatype on stack space?
            //current solution is using the variables we found
            //but need to think about the registers and global variables.
            //DataType dt = dtm.addDataType(pcodeOpASTPair.first, DataTypeConflictHandler.REPLACE_HANDLER);
            DataType dt = function_args_size_map.get(sourceOp_function_map.get(pcodeOpASTPair.second));
            PointerDataType current_struct_pointer = new PointerDataType(pcodeOpASTPair.first);

            Variable[] variables = currentHighFunction.getFunction().getAllVariables();

            for(Variable v: variables){
                //HighFunctionDBUtil.updateDBVariable();
                //-0x68 for test use
                if(v.getMinAddress().getOffset()==pcodeOpASTPair.second.getOutput().getOffset()){
                    listing.clearCodeUnits(v.getMinAddress(),v.getMinAddress().add(8),false);
                    //System.out.println("variable :" + v + "  address: " + v.getMinAddress());
                    //System.out.println("variable pcode:" + pcodeOpASTPair.second.getOutput().getOffset() + " Pcode "+ pcodeOpASTPair.second);
                    System.out.println("Current Pcode: " + pcodeOpASTPair.second);
                    Queue<PcodeOp> pcodeOpQueue = new LinkedList<>();
                    Set<PcodeOp> visited = new HashSet<>();
                    for(var pcodeOpASTinput : pcodeOpASTPair.second.getInputs()){
                        pcodeOpQueue.add(pcodeOpASTinput.getDef());
                    }
                    if(pcodeOpQueue.isEmpty()){
                        continue;
                    }

                    while(!pcodeOpQueue.isEmpty()){
                        var curr_pcode = pcodeOpQueue.poll();

                        if(curr_pcode == null || visited.contains(curr_pcode)){
                            continue;
                        }
                        visited.add(curr_pcode);

                        if(this.globalCtx.addr_sym_map.containsKey(curr_pcode.getOutput().getAddress())){
                            System.out.println("\nWe find the global symbols !!!!!!!!!!\n");
                        }
                        for(var input : curr_pcode.getInputs()){
                            //System.out.println("Adding new pcode :" + input.getDef());
                            pcodeOpQueue.add(input.getDef());
                            if(input.getDef()!=null && input.getDef().getInput(0)!= null && input.getDef().getInput(0).isAddress()){
                                var symbol_address = input.getDef().getInput(0).getAddress();
                                if(this.globalCtx.addr_sym_map.containsKey(symbol_address)){
                                    System.out.println("We find the global variable to retype !");

                                    try {

                                        listing.clearCodeUnits(symbol_address, symbol_address.add(dt.getLength()), false);

                                        DataUtilities.createData(
                                                this.globalCtx.program,
                                                symbol_address,
                                                dt,
                                                dt.getLength(),
                                                DataUtilities.ClearDataMode.CLEAR_ALL_CONFLICT_DATA);
                                        System.out.println("Updated symbol at " + symbol_address + " to structure type" );
                                    } catch(Exception e) {
                                        System.err.println("Failed to update symbol at " + symbol_address + ": " + e.getMessage());
                                    }
                                }
                                else {
                                    for(var address: this.globalCtx.addr_sym_map.keySet()){
                                        System.out.println("global variable address :" + address);
                                    }
                                }
                            }

                        }
                        System.out.println("\nend round\n");
                    }
                    try {
                        //v.setDataType(current_struct_pointer, SourceType.USER_DEFINED);
                        //must use this function to resize the variable
                        //or storage conflict
                        v.setDataType(dt,true,true, SourceType.USER_DEFINED);
                        System.out.println("v: " + v);

                        Address varAddr = v.getMinAddress();
                        if (varAddr == null) {
                            System.out.println("No min address for variable: " + v);
                            return;
                        }

                        // Get the function containing this variable
                        Function func = v.getFunction();
                        if (func == null) {
                            System.out.println("No function associated with variable: " + v);
                            return;
                        }


                        InstructionIterator instrIter = listing.getInstructions(func.getBody(), true);
                        while (instrIter.hasNext()) {
                            Instruction instr = instrIter.next();
                            PcodeOp[] pcodeOps = instr.getPcode();
                            if (pcodeOps == null) continue;

                            for (PcodeOp op : pcodeOps) {
                                //System.out.println("Op output " + op.getOutput().getAddress());
//                                if(op.getOutput()!=null) {
//                                    System.out.println("var offset " + v.getMinAddress().getOffset() + " Pcode: " +op +" \npcd offset " + op.getOutput().getOffset());
//                                }
                                boolean referencesVar = false;
                                // Check if op references the stack variable (varAddr)

//                                if(op.getOutput()!=null && op.getOutput().getHigh() == v){
//                                    System.out.println("We find the op which has current variable !!!!");
//                                }
//                                for(var input: op.getInputs()){
//                                    if(input != null && input == v){
//                                        System.out.println("We find the op which has current variable !!!!");
//                                    }
//                                }

                                if (op.getOutput() != null && isAddressMatch(op.getOutput(), varAddr)) {

                                    referencesVar = true;
                                } else {
                                    int numInputs = op.getNumInputs();
                                    for (int i = 0; i < numInputs; i++) {
                                        Varnode inputVn = op.getInput(i);
                                        if (inputVn != null && isAddressMatch(inputVn, varAddr)) {
                                            referencesVar = true;
                                            break;
                                        }
                                    }
                                }

                                if (referencesVar) {
                                    // Found a PcodeOp referencing the stack variable.
                                    System.out.println("We are starting set the type to global variable");
                                    findAndApplyDataSegmentTypeFromOpBFS(op, dt);
                                }
                            }
                        }


                        //end
                    } catch (InvalidInputException e) {
                        throw new RuntimeException(e);
                    }
                }
            }

            //System.out.println("address: "+ pcodeOpASTPair.second);
            //Address address = pcodeOpASTPair.second.getOutput().getAddress();

            //listing.clearCodeUnits(address, address.add( pcodeOpASTPair.first.getLength()), false);
            //listing.createData(address,dt);





        }//end


    }
    private void findAndApplyDataSegmentTypeFromOpBFS(PcodeOp startOp, DataType dt) {
        Queue<PcodeOp> queue = new LinkedList<>();
        queue.add(startOp);

        while (!queue.isEmpty()) {
            PcodeOp currentOp = queue.poll();
            if (currentOp.getOpcode() == PcodeOp.STORE) {
                Varnode addressVn = currentOp.getInput(1);
                Address dataAddr = resolveDataSegmentAddressRecursive(addressVn, queue);
                if (dataAddr != null) {
                    applyDataTypeToDataSegment(dataAddr, dt);
                    return;
                }
            } else {

            }
        }
    }

    private Address resolveDataSegmentAddressRecursive(Varnode vn, Queue<PcodeOp> queue) {
        if (vn == null) return null;

        if (vn.isConstant()) {
            Address addr = globalCtx.getProgram().getAddressFactory().getDefaultAddressSpace().getAddress(vn.getOffset());
            if (isDataSegmentVariable(addr)) {
                return addr;
            }
            return null;
        }

        PcodeOp defOp = vn.getDef();
        if (defOp == null) {
            return null;
        }

        switch (defOp.getOpcode()) {
            case PcodeOp.COPY:
            case PcodeOp.CAST:
            case PcodeOp.SUBPIECE:
                // These ops don't change data source meaning, just try inputs directly
                for (int i = 0; i < defOp.getNumInputs(); i++) {
                    Address addr = resolveDataSegmentAddressRecursive(defOp.getInput(i), queue);
                    if (addr != null) return addr;
                }
                break;

            case PcodeOp.PTRADD:
            case PcodeOp.INT_ADD:
                Address base = resolveDataSegmentAddressRecursive(defOp.getInput(0), queue);
                if (base != null) {
                    Varnode offsetVn = defOp.getInput(1);
                    if (offsetVn.isConstant()) {
                        long offset = offsetVn.getOffset();
                        Address newAddr = base.getNewAddress(base.getOffset() + offset);
                        return isDataSegmentVariable(newAddr) ? newAddr : null;
                    } else {
                        Address offsetAddr = resolveDataSegmentAddressRecursive(offsetVn, queue);
                        if (offsetAddr != null) {
                            return offsetAddr;
                        }
                    }
                }
                break;
            case PcodeOp.LOAD:
                Varnode loadAddrVn = defOp.getInput(1);
                return resolveDataSegmentAddressRecursive(loadAddrVn, queue);
            default:
                for (int i = 0; i < defOp.getNumInputs(); i++) {
                    Varnode inVn = defOp.getInput(i);
                    Address addr = resolveDataSegmentAddressRecursive(inVn, queue);
                    if (addr != null) return addr;
                }
                break;
        }

        return null;
    }

    private void applyDataTypeToDataSegment(Address dataAddr, DataType dt) {
        Program program = globalCtx.getProgram();
        Listing listing = program.getListing();
        Address endAddress = dataAddr.add(dt.getLength() - 1);
        listing.clearCodeUnits(dataAddr, endAddress, false);
        try {
            DataUtilities.createData(program, dataAddr, dt, -1, DataUtilities.ClearDataMode.CLEAR_ALL_CONFLICT_DATA);
            System.out.println("Applied structure type " + dt.getName() + " to .data variable at " + dataAddr);
        } catch (Exception e) {
            System.out.println("Failed to apply type to .data variable at " + dataAddr + ": " + e.getMessage());
        }
    }

    private boolean isDataSegmentVariable(Address address) {
        if (address == null) return false;
        MemoryBlock block = globalCtx.getProgram().getMemory().getBlock(address);
        if (block == null) return false;
        String blockName = block.getName().toLowerCase();
        return blockName.contains("data");
    }

    private boolean isAddressMatch(Varnode vn, Address varAddr) {
        //System.out.println("cmping " + vnAddr + " to " + varAddr);
        Address vnAddr = vn.getAddress();
        if (vnAddr == null) return false;

        if (varAddr.isStackAddress()) {
            boolean result = vn.getAddress() == varAddr;
            //System.out.println("cmping " + vn.getAddress() + " to " + varAddr +" result is :" + result);
            return vnAddr.isStackAddress() && (vn.getAddress() == varAddr);
        }

        return vnAddr.equals(varAddr);
    }

}
