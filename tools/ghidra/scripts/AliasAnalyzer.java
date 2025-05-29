import ghidra.graph.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.block.*;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.pcode.*;
import ghidra.program.model.symbol.SourceType;
import ghidra.util.exception.CancelledException;
import ghidra.util.exception.DuplicateNameException;
import ghidra.util.exception.InvalidInputException;
import ghidra.graph.jung.JungDirectedGraph;
import ghidra.util.task.TaskMonitor;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

import static ghidra.graph.GraphAlgorithms.getSources;

public class AliasAnalyzer {
    private static final boolean DEBUG = false;

    private GlobalCtx globalCtx;
    private HashMap<Parameter, Set<PcodeOpAST>> param_def_use_map = new HashMap<>();
    private HashMap<HighFunction, Parameter[]> function_param_map = new HashMap<>();
    private HashMap<Parameter, VarnodeAST> param_varnode_map = new HashMap<>();
    private HashMap<Varnode, Varnode> alias_map = new HashMap<>();
    private HashMap<Parameter, HighFunction> param_function_map = new HashMap<>();
    private HashMap<Varnode, Map<Function, Integer>> varnode_alias_function_arg_map = new HashMap<>();


    private Map<HighFunction, Map<Integer, PcodeOpAST>> functionIndexToPcodeASTMap = new HashMap<>();
    private Map<HighFunction, Map<PcodeOpAST, Integer>> functionPcodeASTToIndexMap = new HashMap<>();
    private Map<HighFunction, Map<Integer, PcodeOp>> functionIndexToPcodeMap = new HashMap<>();
    private Map<HighFunction, Map<PcodeOp, Integer>> functionPcodeToIndexMap = new HashMap<>();

    private Map<HighFunction, Map<Integer, PcodeOp>> functionIndexToLowPcodeMap = new HashMap<>();
    private Map<HighFunction, Map<PcodeOp, Integer>> functionLowPcodeToIndexMap = new HashMap<>();

    private Map<HighFunction, Map<Integer, Integer>> functionlowPcodeHashToIndex = new HashMap<>();
    private Map<HighFunction,Map<Integer, Integer>> functionIndexToLowPcodeHash = new HashMap<>();

    private Map<HighFunction, Map<Address, Integer>> functionaddressToIndex = new HashMap<>();
    private Map<HighFunction, Map<Integer, Address>> functionIndexToaddress = new HashMap<>();

    public AliasAnalyzer(GlobalCtx globalCtx) {
        this.globalCtx = globalCtx;
    }
    public void analyze() throws CancelledException {
        System.out.println("-----Analyzing Aliases");
        this.getDefUsePcode();

    }

    private void getDefUsePcode() throws CancelledException {
        List<HighFunction> highFunctionList = this.globalCtx.getHighFunctionList();
        if(highFunctionList != null){
            for(HighFunction highFunction : highFunctionList){

                AccessPatternGraph apg = new AccessPatternGraph(highFunction);
                //apg.exportToDot("/tmp/func/" + highFunction.getFunction().getName() +".dot");
                //apg.exportDomTreeToDot("/tmp/func_dom/" +  highFunction.getFunction().getName() +".dot");
                //apg.exportRevDomTreeToDot("/tmp/func_rev_dom/" +  highFunction.getFunction().getName() +".dot");

                LocalSymbolMap localSymbolMap = highFunction.getLocalSymbolMap();
                Function function = highFunction.getFunction();
                Parameter[] parameters = function.getParameters();
                if(DEBUG) {
                    System.out.println("Function analyzing:" + function.getName());
                    if (!function.getName().contains("1014ef")) {
                        continue;
                    }
                    System.out.println("Parameters:" + Arrays.toString(parameters));
                    //printFunctionPcodeAddress(highFunction);
                    printCBRANCHPcode(highFunction);
                }

                if(parameters.length == 0) {
                    if(DEBUG) {
                        System.out.println("Broken Function signature :" + function.getSignature());
                    }
                    //adding the parameter information back to the definition
                    for (Iterator<HighSymbol> it = highFunction.getLocalSymbolMap().getSymbols(); it.hasNext(); ) {
                        HighSymbol symbol = it.next();
                        if (symbol.isParameter()) {
                            System.out.println("Arg: " + symbol.getName() + " Type: " + symbol.getDataType() + " Storage: " + symbol.getStorage());
                            try {
                                DataType dataType = symbol.getDataType();
                                ParameterImpl new_param = new ParameterImpl(symbol.getName(), dataType, this.globalCtx.program);
                                function.addParameter(new_param, SourceType.USER_DEFINED);

                                System.out.println("Adding the parameter information to "+ function.getName() + " Parameter: " + new_param);

                            } catch (InvalidInputException e) {
                                System.out.println("Unable to handle the parameter");
                            } catch (DuplicateNameException e) {
                                System.out.println("Unable to create the parameter");
                            }
                        }

                    }

                }
                if(DEBUG) {
                    System.out.println("Fixed Function signature :" + function.getSignature());
                }
                this.function_param_map.put(highFunction, parameters);
                //adding the index for the PcodeOpAST
                createPcodeIndexMap(highFunction);

                //opt the loop
                //todo!
                for(Parameter parameter : function.getParameters()){

                    this.param_function_map.put(parameter, highFunction);

                    getFunctionDom(highFunction);

                    if(DEBUG){
                        System.out.println("Current parameter: " + parameter);
                    }
                    if(parameter.getDataType() instanceof Pointer32DataType ||
                            parameter.getDataType() instanceof Pointer64DataType ||
                            parameter.getDataType() instanceof PointerDataType||
                            parameter.getDataType() instanceof Pointer
                    ){
                        if(DEBUG){
                            System.out.println("Start def-use analysis");
                        }

                        String para_name = parameter.getName();
                        VariableStorage para_vs = parameter.getVariableStorage();
                        //we need to know which pcode use the storage in order to trace the dataflow
                        //and get the def-use information
                        Optional<Varnode> start_varnode = Optional.empty();
                        if(DEBUG){
                            System.out.println("Function Pcode: " );
                            for (Iterator<PcodeOpAST> it = highFunction.getPcodeOps(); it.hasNext(); ){
                                PcodeOp op = it.next();
                                System.out.println("Address " + op.getSeqnum().getTarget() +  " Pcode " + op);
                                if(op.getOpcode() == PcodeOp.CBRANCH){
                                    var target = op.getInput(0);
                                    //System.out.println("Target: " + target);
                                }
                            }
                        }
                        for (Iterator<PcodeOpAST> it = highFunction.getPcodeOps(); it.hasNext(); ) {
                            //we start checking the pcodeOpAST's inputs
                            PcodeOpAST pcodeOpAST = it.next();
                            Varnode[] varnodes = pcodeOpAST.getInputs();

                            if(start_varnode.isEmpty()) {
                                for (Varnode varnode : varnodes) {

                                    if (varnode.getAddress().equals(para_vs.getMinAddress()) ) {
                                        //we find the usage PcodeOpAST
                                        if(DEBUG){
                                            System.out.println("Varnode address " + varnode.getAddress() +
                                                    " Parameter address " + para_vs.getMinAddress()
                                            +" We find the varnode");
                                        }
                                        if (!this.param_def_use_map.containsKey(parameter)) {
                                            this.param_def_use_map.put(parameter, new HashSet<PcodeOpAST>());

                                        }

                                        this.param_def_use_map.get(parameter).add(pcodeOpAST);
                                        //use the result
                                        start_varnode = Optional.of(pcodeOpAST.getOutput());

                                        //need to check whether this is allowed
                                        //to generate the VarnodeAST
                                        this.param_varnode_map.put(parameter, (VarnodeAST) varnode);

                                    }
                                }
                            }

                        }//end of Iterator of PcodeOpAST

                        if (start_varnode.isPresent()) {

                            Set<PcodeOpAST> visited = new HashSet<>();
                            //we start doing the def use collection
                            PcodeOpAST defuse_pcode = (PcodeOpAST) start_varnode.get().getDef();
                            //

                            //update the alias map with the function
                            assert para_vs.getVarnodes().length == 1;
                            this.alias_map.put(para_vs.getFirstVarnode(), defuse_pcode.getOutput());
                            Queue<PcodeOpAST> pcode_queue = new LinkedList<>();
                            pcode_queue.add(defuse_pcode);
                            //List<PcodeOpAST> param_uses = getNextUsePcodeOps(parameter.g);
                            for(Varnode u : defuse_pcode.getInputs()){
                                List<PcodeOpAST> tmp_list = getNextUsePcodeOps(u);
                                pcode_queue.addAll(tmp_list);
                            }
                            while(!pcode_queue.isEmpty()) {
                                PcodeOpAST curr_pcode = pcode_queue.poll();
                                if (visited.contains(curr_pcode) || curr_pcode == null) {
                                    continue;
                                }
                                visited.add(curr_pcode);
                                //update the local varnodes to the parameter's
                                //alias map
                                this.alias_map.put(start_varnode.get(), curr_pcode.getOutput());


                                this.param_def_use_map.get(parameter).add(curr_pcode);


                                //fine-grained def-use analysis
                                if(curr_pcode.getOutput() == null || curr_pcode.getOutput().getDescendants() == null){
                                    continue;
                                }
                                List<PcodeOpAST> use_list = getNextUsePcodeOps(curr_pcode.getOutput());

                                if(!use_list.isEmpty()){
                                    //we get the next use and we don't need to care about whether this
                                    //address is high or low
                                    for(var use : use_list){

                                        if(use.getOpcode() == PcodeOp.CALL){
                                            //we find a function call
                                            //and we need to know the index of the
                                            for(int i = 0; i < use.getNumInputs(); ++i){
                                                if(use.getInput(i) == curr_pcode.getOutput()){
                                                    //we find the index
                                                    System.out.println("the index of next function " + i);
                                                    //todo save the inforamtion
                                                    this.varnode_alias_function_arg_map.putIfAbsent(curr_pcode.getOutput(), new HashMap<>());
                                                    Varnode next_func = use.getInput(0);
                                                    if(next_func != null){
                                                        Function callee = this.globalCtx.program.getFunctionManager().getFunctionAt(next_func.getAddress());
                                                        if(callee != null) {
                                                            System.out.println("We find the callee function " + callee.getName());
                                                            this.varnode_alias_function_arg_map.get(curr_pcode.getOutput()).put(callee, i);
                                                        }else{
                                                            System.out.println("error in parsing callee " + use );
                                                        }
                                                    }

                                                    //for bottom up analysis
                                                }
                                            }
                                        }

                                        pcode_queue.add(use);
                                    }//end def-use analysis
                                }


                            }
                            //we need to scan again to create the edge
                            Set<PcodeOpAST> def_use_set = this.param_def_use_map.get(parameter);
                            //add graph information

                            Map<Integer, PcodeOpAST> index_pcodeopast = this.functionIndexToPcodeASTMap.get(highFunction);
                            Map<PcodeOpAST, Integer> pcodeopast_index = this.functionPcodeASTToIndexMap.get(highFunction);

                            Map<Integer, PcodeOp> index_pcode = this.functionIndexToLowPcodeMap.get(highFunction);
                            Map<PcodeOp, Integer> pcode_index = this.functionLowPcodeToIndexMap.get(highFunction);

                            Map<Integer, Integer> index_pcodehash = this.functionIndexToLowPcodeHash.get(highFunction);
                            Map<Integer, Integer> pcodehash_index = this.functionlowPcodeHashToIndex.get(highFunction);

                            Map<Address, Integer> addressToIndex = this.functionaddressToIndex.get(highFunction);
                            Map<Integer, Address> IndexToaddress = this.functionIndexToaddress.get(highFunction);

                            postprocessDefUseMap(
                                    parameter,
                                    highFunction,
                                    def_use_set,
                                    index_pcodeopast,
                                    pcodeopast_index,
                                    index_pcode,
                                    pcode_index,
                                    index_pcodehash,
                                    pcodehash_index,
                                    addressToIndex,
                                    IndexToaddress
                                    );
                        }//end optional
                        else{
                            System.out.println("We cannot find any structure used as pointer");
                        }
                    }
                }//end para loop
            }
        }
    }


    //localAccessGraph: the graph based on the def-use analysis
    //usage: use def-use analysis to find the ptr_add and ptr_sub to find
    //the field access sequence, and use the sequence as the id
    private void graph_based_rule_match(LocalAccessGraph localAccessGraph)
    {
        System.out.println("starting graph based rule matching ");
        HighFunction highFunction = localAccessGraph.getHighFunction();
        Set<AccessEdge> load_edge_set = new HashSet<>();
        for(var edge : localAccessGraph.getAccessEdges()){
            if(edge.edge_tag == PcodeOp.LOAD){
                load_edge_set.add(edge);
            }
        }
        Set<List<String>> seq_result = new HashSet<>();

        Set<AccessEdge> start_edge_set = new HashSet<>();
        for(var load_edge: load_edge_set){
            Set<AccessEdge> pred_edge_set = localAccessGraph.getPredAccessEdge(load_edge);
            if(pred_edge_set != null && !pred_edge_set.isEmpty()) {
                start_edge_set.addAll(pred_edge_set);
            }
            else{
                start_edge_set.add(load_edge);
            }
        }

        for(var start_edge : start_edge_set){
            System.out.println("starting dfs");
            List<String> currentSeq = new ArrayList<>();
            Set<AccessEdge> visited = new HashSet<>();

            dfsPtrAddSequence(start_edge, currentSeq, visited, seq_result, localAccessGraph);

        }
        System.out.println("Function Name: " + highFunction.getFunction().getName());
        for(var seq : seq_result){
            System.out.println(seq + ",");
        }

        String funcName = highFunction.getFunction().getName();
        String outDirPath = "/tmp/structanalysis";
        String filePath = outDirPath + "/" + funcName + ".txt";


        File outDir = new File(outDirPath);
        if (!outDir.exists()) {
            outDir.mkdirs();
        }

        try (FileWriter writer = new FileWriter(filePath)) {
            for (var seq : seq_result) {
                writer.write(seq + "\n");
            }
        } catch (IOException e) {
            System.out.println("Failed to write to file: " + filePath);
            e.printStackTrace();
        }

    }

    public static boolean isConditional(int opcode) {
        return opcode == PcodeOp.INT_EQUAL ||
                opcode == PcodeOp.INT_NOTEQUAL ||
                opcode == PcodeOp.INT_LESS ||
                opcode == PcodeOp.INT_LESSEQUAL ||
                opcode == PcodeOp.INT_SLESS ||
                opcode == PcodeOp.INT_SLESSEQUAL ||
                opcode == PcodeOp.INT_CARRY ||
                opcode == PcodeOp.INT_SBORROW;
    }

    public void dfsPtrAddSequence(AccessEdge current,
                                  List<String> currentSeq,
                                  Set<AccessEdge> visited,
                                  Set<List<String>> allSequences,
                                  LocalAccessGraph localAccessGraph)
    {
        //System.out.println("pcode:" +current.pcode_op);
        if (current.edge_tag == PcodeOp.INT_ADD || current.edge_tag == PcodeOp.INT_SUB) {
            long offset = current.pcode_op.getInput(1).getOffset();
            String ptr_offset = String.valueOf(offset);
            currentSeq.add(ptr_offset);
        } else if (current.edge_tag == PcodeOp.LOAD) {
            if(current.pcode_op != null){
                var pcode = current.pcode_op;
                if (pcode.getInput(1).isConstant()){
                    String ptr_offset = String.valueOf(pcode.getInput(1).getOffset());
                    currentSeq.add(ptr_offset);
                }
            }
        } else if (isConditional(current.edge_tag) && current.edge_tag != PcodeOp.INT_SBORROW){
            if(isConditional(current.edge_tag)){
                if (current.pcode_op != null) {
                    var pcode = current.pcode_op;
                    if (pcode.getInput(1).isConstant()) {
                        String ptr_offset = String.valueOf(pcode.getInput(1).getOffset());
                        currentSeq.add("\""+ current.pcode_op.getMnemonic()+"_" +ptr_offset +"\"");
                    }
                }else {
                    String cmp = current.pcode_op.getMnemonic();
                    currentSeq.add(cmp);
                }
            }else {
                String cmp = current.pcode_op.getMnemonic();
                currentSeq.add(cmp);
            }
        }else if (current.edge_tag == PcodeOp.CALL){
            currentSeq.add("CALL");
        }

        Set<AccessEdge> successors = localAccessGraph.getSuccAccessEdge(current);
        if (successors == null || successors.isEmpty()) {
            allSequences.add(new ArrayList<>(currentSeq));
        } else {
            for (AccessEdge succ : successors) {
                if (!visited.contains(succ)) {
                    visited.add(succ);
                    dfsPtrAddSequence(succ, currentSeq, visited, allSequences, localAccessGraph);
                    visited.remove(succ);
                }
            }
        }

        if (current.edge_tag == PcodeOp.INT_ADD || current.edge_tag == PcodeOp.INT_SUB) {
            currentSeq.remove(currentSeq.size() - 1);
        }
    }

    private void graph_rule_match(LocalAccessGraph localAccessGraph)
    {
            System.out.println("graph_rule_match");
        //we want to know the cmp instructions dominate pcode inst
        //with that, we can infer the varnodes' type
        //and if it dominated by cmp and also the pointer type
        //we regard it as the possible field pointers to distinguish the doubly linked list
        //and tree
            Set<AccessEdge> access_edge_set = localAccessGraph.getAccessEdges();
            Set<AccessEdge> cmp_edge_set = new HashSet<>();
            for(AccessEdge access_edge : access_edge_set){
                //System.out.println("the cbranch tage: "+ PcodeOp.CBRANCH);
                if(access_edge.edge_tag == PcodeOp.CBRANCH){
                    cmp_edge_set.add(access_edge);
                }

            }
            if(cmp_edge_set.isEmpty()){
               System.out.println("no cmp edge found, we need to check the local access graph");

            }
            else{
                access_edge_set.removeAll(cmp_edge_set);
                if(access_edge_set.isEmpty()){
                    System.out.println("We find something wrong");
                }
                System.out.println("The remaining access edge number: " + access_edge_set.size());
                HashMap<AccessEdge, Set<AccessEdge>> cmp_dom_edges = new HashMap<>();
                for(AccessEdge cmp_edge : cmp_edge_set){
                    Set<AccessEdge> dom_edges = new HashSet<>();
                    Set<Varnode> cmp_dest = cmp_edge.destination;
                    if(!cmp_dest.isEmpty()){
                        for(AccessEdge rem_edge: access_edge_set){
                            if(rem_edge.source.contains(cmp_dest)){
                                System.out.println("we find dominated edge");
                                dom_edges.add(rem_edge);
                            }
                        }
                    }
                    cmp_dom_edges.put(cmp_edge, dom_edges);

                }
                HashMap<AccessEdge, Set<Integer>> cmp_dom_fields_map = new HashMap<>();
                for(AccessEdge cmp_edge : cmp_dom_edges.keySet()){
                    Set<AccessEdge> dom_edges = cmp_dom_edges.get(cmp_edge);
                    Set<Varnode> dom_varnodes = new HashSet<>();

                    for(AccessEdge edge: dom_edges){
                        dom_varnodes.addAll(edge.source);
                    }
                    for(Varnode varnode: dom_varnodes){
                        var pcode_inst = varnode.getDef();
                        if(pcode_inst != null){
                            if(pcode_inst.getOpcode() == PcodeOp.PTRADD){
                                Varnode index = pcode_inst.getInput(1);
                                Varnode scale = pcode_inst.getInput(2);
                                long offset = index.getOffset() * scale.getOffset();
                                Set<Integer> fieldOffsets = cmp_dom_fields_map.getOrDefault(cmp_edge, new HashSet<>());
                                fieldOffsets.add((int) offset);
                                cmp_dom_fields_map.put(cmp_edge, fieldOffsets);
                            } else if (pcode_inst.getOpcode() == PcodeOp.PTRSUB) {
                                Varnode index = pcode_inst.getInput(1);
                                Varnode scale = pcode_inst.getInput(2);
                                long offset = index.getOffset() * scale.getOffset();
                                Set<Integer> fieldOffsets = cmp_dom_fields_map.getOrDefault(cmp_edge, new HashSet<>());
                                fieldOffsets.add((int) (-offset));
                            }
                        }
                    }


                }
                Boolean flag = false;
                for(AccessEdge cmp_edge : cmp_dom_edges.keySet()){
                    Set<Integer> field_nums = cmp_dom_fields_map.get(cmp_edge);
                    if(field_nums != null && field_nums.size() >= 3){
                        flag = true;
                    }
                }
                if(flag){
                    System.out.println("We find a tree");
                }else{
                    System.out.println("We find a doubly linked list");

                }
            }



    }

    private void graph_sub_match(LocalAccessGraph localAccessGraph){
        System.out.println("Starting sub graph analysis--");
        Set<AccessEdge> access_edge_set = localAccessGraph.getAccessEdges();
        Set<AccessEdge> cmp_edge_set = new HashSet<>();
        TaskMonitor monitor = TaskMonitor.DUMMY;
        Function function = localAccessGraph.highFunction.getFunction();
        CodeBlockModel blockModel = new BasicBlockModel(function.getProgram());


        for(AccessEdge access_edge : access_edge_set){
            if(access_edge.edge_tag == PcodeOp.CBRANCH){
                cmp_edge_set.add(access_edge);
            }

        }
        if(cmp_edge_set.isEmpty()){
            System.out.println("no cmp edge found, we need to check the local access graph");
            return;
        }
        else{
            for(var cmp_edge: cmp_edge_set){
                for(var dst: cmp_edge.getDestination()){
                    PcodeOp dst_pcode = dst.getDef();
                    if(dst_pcode == null)
                        continue;

                    HighFunction highFunction = localAccessGraph.highFunction;
                    try {
                        var dom = getFunctionDom(highFunction);
                        CodeBlock cmp_dst_block = blockModel.getFirstCodeBlockContaining(dst_pcode.getSeqnum().getTarget(), monitor);
                        Set<CodeBlock> dom_blocks = GraphAlgorithms.findDominance(dom, cmp_dst_block, monitor);
                        //List<CodeBlock> dom_blocks = getDominators(dst_pcode, dom);

                        if(dom_blocks.isEmpty()){
                            System.out.println("We cannot gen the dom tree for function :" + highFunction.getFunction().getName());
                            return;
                        }
                        System.out.println("the dom size: " + dom_blocks.size());

                    }
                    catch (Exception e){
                        System.out.println("exception in graph_sub_match: " + e);
                    }
                }

            }
        }




    }



    private LocalAccessGraph postprocessDefUseMap(Parameter param,
                                      HighFunction highFunction,
                                      Set<PcodeOpAST> def_use_set,
                                      Map<Integer, PcodeOpAST> index_pcodeopast,
                                      Map<PcodeOpAST, Integer> pcodeopast_index,
                                      Map<Integer, PcodeOp> index_pcode,
                                      Map<PcodeOp, Integer> pcode_index,
                                      Map<Integer, Integer> index_pcodehash,
                                      Map<Integer, Integer> pcodehash_index,
                                      Map<Address, Integer> addressToIndex,
                                      Map<Integer, Address> IndexToaddress
                                      )
    {
        LocalAccessGraph local_access_graph = new LocalAccessGraph(param);
        AccessPatternGraph def_use_apg = new AccessPatternGraph(highFunction, param);


        List<PcodeOpAST> sortedList = new ArrayList<>(def_use_set);
        List<PcodeOp> lowPcodeSet = new ArrayList<>();

        sortedList.sort(Comparator.comparingInt(op -> {
            Integer index = pcodeopast_index.get(op);
            return index != null ? index : Integer.MAX_VALUE;
        }));

        // from function's beginning to start
        for(var pcodeOpAST : sortedList){
            Address target_addr = pcodeOpAST.getSeqnum().getTarget();
            PcodeOp[] inst_pcode_list = this.globalCtx.program.getListing().getInstructionAt(target_addr).getPcode();
            lowPcodeSet.addAll(Arrays.asList(inst_pcode_list));
        }

        Set<PcodeOp> def_use_set_low = new HashSet<>(lowPcodeSet);

        Set<PcodeOp> visited = new HashSet<>();

        for (PcodeOp op : lowPcodeSet) {
            processPcodeOp(op,
                    def_use_set_low,
                    index_pcodeopast,
                    pcodeopast_index,
                    index_pcode,
                    pcode_index,
                    index_pcodehash,
                    pcodehash_index,
                    addressToIndex,
                    IndexToaddress,
                    local_access_graph,
                    def_use_apg,
                    visited);
        }

        local_access_graph.highFunction = highFunction;
        //graph_rule_match(local_access_graph);
        graph_sub_match(local_access_graph);
        graph_based_rule_match(local_access_graph);
        //def_use_apg.exportToDupDot("/tmp/def_use_dup/" + highFunction.getFunction().getName()+".dot");
        //def_use_apg.exportDomTreeToDot("/tmp/def_use_dom/" + highFunction.getFunction().getName()+".dot");
        //def_use_apg.exportRevDomTreeToDot("/tmp/def_use_rev_dom/" + highFunction.getFunction().getName()+".dot");
        return local_access_graph;
    }
    private void processPcodeOp(PcodeOp op,
                                Set<PcodeOp> def_use_set,
                                Map<Integer, PcodeOpAST> index_pcodeopast,
                                Map<PcodeOpAST, Integer> pcodeopast_index,
                                Map<Integer, PcodeOp> index_pcode,
                                Map<PcodeOp, Integer> pcode_index,
                                Map<Integer, Integer> index_pcodehash,
                                Map<Integer, Integer> pcodehash_index,
                                Map<Address, Integer> addressToIndex,
                                Map<Integer, Address> IndexToaddress,
                                LocalAccessGraph local_access_graph,
                                AccessPatternGraph def_use_apg,
                                Set<PcodeOp> visited)
    {
        if (op == null || visited.contains(op)) {
            return;
        }
        visited.add(op);

        if(!pcodehash_index.containsKey(op.hashCode())) {
            System.out.println("Cannot find the pcode hash?!");
            return;
        }
        int index = pcodehash_index.get(op.hashCode());


        switch (op.getOpcode()) {
            case PcodeOp.CBRANCH: {
                Optional<PcodeOpAST> false_branch = Optional.empty();
                for(int i = index; i< Collections.max(index_pcodeopast.keySet()); i++){
                    PcodeOpAST curr_pcode = index_pcodeopast.get(i);
                    if(def_use_set.contains(curr_pcode)){
                        false_branch = Optional.of(curr_pcode);
                    }
                }
                if(false_branch.isPresent() || index>=0){
                    if(index_pcode.containsKey(index+1)) {
                        def_use_apg.AddBranchEdge(op, index_pcode.get(index + 1));
                        processPcodeOp(index_pcode.get(index + 1),
                                def_use_set,
                                index_pcodeopast,
                                pcodeopast_index,
                                index_pcode,
                                pcode_index,
                                index_pcodehash,
                                pcodehash_index,
                                addressToIndex,
                                IndexToaddress,
                                local_access_graph,
                                def_use_apg,
                                visited);
                    }
                }
                else {
                    System.out.println("We find a false branch problem!");
                }

                Optional<PcodeOp[]> true_branch = getBranchTarget(op);
                if(true_branch.isPresent()){
                    Address branch_target = op.getInput(0).getAddress();
                    PcodeOp[] pcodelist = this.globalCtx.program.getListing().getInstructionAt(branch_target).getPcode();
                    if(pcodelist.length > 0){
                        PcodeOp pcodeOp = pcodelist[0];
                        Address target_addr = pcodeOp.getSeqnum().getTarget();
                        if(pcodehash_index.containsKey(pcodeOp.hashCode())){
                            //System.out.println("We find the next pcode!");
                        }
                        else if (pcode_index.containsKey(pcodeOp)){
                            System.out.println("We find something related to the pcode index map");
                        }
                        else if(addressToIndex.containsKey(target_addr)){
                            //System.out.println("We find the next pcode by address! " + addressToIndex.get(target_addr));
                            for(int curr_index = addressToIndex.get(target_addr) + 1 ; curr_index < Collections.max(IndexToaddress.keySet()); curr_index++){
                                //System.out.println("Current index: " + curr_index);
                                if(IndexToaddress.containsKey(curr_index)){
                                    Address next_addr = IndexToaddress.get(curr_index);
                                    //PcodeOp[] next_ops = this.globalCtx.program.getListing().getInstructionAt(next_addr).getPcode();
                                    for(var def_use : def_use_set){
                                        Address defuse_addr = def_use.getSeqnum().getTarget();
                                        if(defuse_addr.equals(next_addr)){
                                            //System.out.println("We find the next defuse");
                                            //op <- def_use
                                            local_access_graph.addControlEdge(op, def_use, PcodeOp.CBRANCH);

                                            def_use_apg.AddBranchEdge(op, def_use);


                                            processPcodeOp(def_use,
                                                    def_use_set,
                                                    index_pcodeopast,
                                                    pcodeopast_index,
                                                    index_pcode,
                                                    pcode_index,
                                                    index_pcodehash,
                                                    pcodehash_index,
                                                    addressToIndex,
                                                    IndexToaddress,
                                                    local_access_graph,
                                                    def_use_apg,
                                                    visited);

                                        }
                                    }

                                }else{
                                    System.out.println("We find somthing wrong with the index2addr map");
                                }
                            }
                            System.out.println("End search");
                        }
                        else{
                            for(var key: addressToIndex.keySet()){
                                System.out.println("Cmping: " + key + "\t " + target_addr);
                            }
                        }
                    }
                }//end of is present
                else{
                    System.out.println("We find some problems about the true branch!");
                }

                break;
            }
            case PcodeOp.BRANCH: {
                Optional<PcodeOp[]> targetbranch = getBranchTarget(op);
                if(targetbranch.isPresent()){
                    //to do
                    Address branch_target = op.getInput(0).getAddress();
                    PcodeOp[] pcodelist = this.globalCtx.program.getListing().getInstructionAt(branch_target).getPcode();
                    if(pcodelist.length > 0){
                        PcodeOp pcodeOp = pcodelist[0];
                        Address target_addr = pcodeOp.getSeqnum().getTarget();
                        if(pcodehash_index.containsKey(pcodeOp.hashCode())){
                            System.out.println("We find the next pcode!");
                        }
                        else if (pcode_index.containsKey(pcodeOp)){
                            System.out.println("We find something related to the pcode index map");
                        }
                        else if(addressToIndex.containsKey(target_addr)){
                            System.out.println("We find the next pcode by address! " + addressToIndex.get(target_addr));
                            for(int curr_index = addressToIndex.get(target_addr) + 1 ; curr_index < Collections.max(IndexToaddress.keySet()); curr_index++){
                                //System.out.println("Current index: " + curr_index);
                                if(IndexToaddress.containsKey(curr_index)){
                                    Address next_addr = IndexToaddress.get(curr_index);
                                    //PcodeOp[] next_ops = this.globalCtx.program.getListing().getInstructionAt(next_addr).getPcode();
                                    for(var def_use : def_use_set){
                                        Address defuse_addr = def_use.getSeqnum().getTarget();
                                        if(defuse_addr.equals(next_addr)){
                                            //System.out.println("We find the next defuse");
                                            local_access_graph.addControlEdge(op, def_use, PcodeOp.BRANCH);
                                            def_use_apg.AddBranchEdge(op, def_use);

                                            processPcodeOp(def_use,
                                                    def_use_set,
                                                    index_pcodeopast,
                                                    pcodeopast_index,
                                                    index_pcode,
                                                    pcode_index,
                                                    index_pcodehash,
                                                    pcodehash_index,
                                                    addressToIndex,
                                                    IndexToaddress,
                                                    local_access_graph,
                                                    def_use_apg,
                                                    visited);
                                        }
                                    }

                                }else{
                                    System.out.println("We find somthing wrong with the index2addr map");
                                }
                            }
                            System.out.println("End search");
                        }
                        else{
                            for(var key: addressToIndex.keySet()){
                                System.out.println("Cmping: " + key + "\t " + target_addr);
                            }
                        }
                    }
                }
                break;
            }
            case PcodeOp.CALL: {
                //System.out.println("Find a call");
                local_access_graph.addEdge(op);
                break;
            }
            default:
                local_access_graph.addEdge(op);
                def_use_apg.AddEdge(op);
                break;
        }
    }


    private Optional<PcodeOp[]> getBranchTarget(PcodeOp op)
    {
        //int targetIndex = getBranchTargetIndex(op);
        Optional<Address> target = getBranchTargetAddress(op);
        if(target.isPresent()){
            PcodeOp[] next_pcodes = this.globalCtx.program.getListing().getInstructionAt(target.get()).getPcode();
            return Optional.ofNullable(next_pcodes);
        }
        else {
            return Optional.empty();
        }
    }


    private Optional<Address> getBranchTargetAddress(PcodeOp op) {
        Optional<Address> result = Optional.empty();
        if (op.getOpcode() == PcodeOp.BRANCH || op.getOpcode() == PcodeOp.CBRANCH) {
            if(op.getInput(0).isAddress()){
                return Optional.ofNullable(op.getInput(0).getAddress());
            }
        }
        return result;
    }

    private void createPcodeIndexMap(HighFunction highFunction) {
        Map<Integer, PcodeOpAST> indexToPcodeAST = new HashMap<>();
        Map<PcodeOpAST, Integer> pcodeASTToIndex = new HashMap<>();

        Map<Integer, PcodeOp> indexToPcode = new HashMap<>();
        Map<PcodeOp, Integer> pcodeToIndex = new HashMap<>();

        Map<Integer, PcodeOp> indexTolowPcode = new HashMap<>();
        Map<PcodeOp, Integer> lowPcodeToIndex = new HashMap<>();

        Map<Integer, Integer> lowPcodeHashToIndex = new HashMap<>();
        Map<Integer, Integer> indexToLowPcodeHash = new HashMap<>();

        Map<Address, Integer> addressToIndex = new HashMap<>();
        Map<Integer, Address> IndexToaddress = new HashMap<>();

        int index = 0;
        int low_index = 0;
        for (Iterator<PcodeOpAST> opIter = highFunction.getPcodeOps(); opIter.hasNext(); ) {
            PcodeOpAST opAST = opIter.next();
            PcodeOp op = opAST;

            indexToPcodeAST.put(index, opAST);
            pcodeASTToIndex.put(opAST, index);

            indexToPcode.put(index, op);
            pcodeToIndex.put(op, index);

            Address target = opAST.getSeqnum().getTarget();
            if(this.globalCtx.program.getListing().getInstructionAt(target) == null){
                continue;
            }
            PcodeOp[] inst_pcodes = this.globalCtx.program.getListing().getInstructionAt(target).getPcode();
            for(var inst_pcode: inst_pcodes){
                indexTolowPcode.put(low_index, inst_pcode);
                lowPcodeToIndex.put(inst_pcode, low_index);
                lowPcodeHashToIndex.put(inst_pcode.hashCode(), low_index);
                indexToLowPcodeHash.put(low_index, inst_pcode.hashCode());
                Address target_addr = inst_pcode.getSeqnum().getTarget();
                if(!addressToIndex.containsKey(target_addr) ){
                    addressToIndex.put(target_addr, index);
                    IndexToaddress.put(index, target_addr);
                }
                low_index++;
            }

            index++;
        }

        Function function = highFunction.getFunction();
        AddressSetView address_set = function.getBody();
        for(InstructionIterator inst_itor =  this.globalCtx.program.getListing().getInstructions(address_set, true);
            inst_itor.hasNext();
        )
        {
            Instruction inst = inst_itor.next();
            PcodeOp[] inst_pcodes = inst.getPcode();
            for(var inst_pcode: inst_pcodes){
                Address target_addr = inst_pcode.getSeqnum().getTarget();

                if(!addressToIndex.containsKey(target_addr) ){
                    addressToIndex.put(target_addr, index);
                }
                IndexToaddress.put(index, target_addr);
                index++;
            }
        }

        this.functionIndexToPcodeASTMap.put(highFunction, indexToPcodeAST);
        this.functionPcodeASTToIndexMap.put(highFunction, pcodeASTToIndex);
        this.functionIndexToPcodeMap.put(highFunction, indexToPcode);
        this.functionPcodeToIndexMap.put(highFunction, pcodeToIndex);
        this.functionIndexToLowPcodeMap.put(highFunction, indexTolowPcode);
        this.functionLowPcodeToIndexMap.put(highFunction, lowPcodeToIndex);
        this.functionIndexToLowPcodeHash.put(highFunction, indexToLowPcodeHash);
        this.functionlowPcodeHashToIndex.put(highFunction, lowPcodeHashToIndex);
        this.functionaddressToIndex.put(highFunction, addressToIndex);
        this.functionIndexToaddress.put(highFunction, IndexToaddress);
    }

    private void printFunctionPcodeAddress(HighFunction highFunction){
        for (Iterator<PcodeOpAST> it = highFunction.getPcodeOps(); it.hasNext(); ) {
            PcodeOpAST pcode = it.next();

            if(pcode.getOutput() != null) {
                for(var input : pcode.getInputs()){
                    System.out.println("Address: " + input.getAddress());
                }
                System.out.println("Address: " + pcode.getOutput().getAddress()  + " PCode: " + pcode);
            }
        }
    }

    private void printCBRANCHPcode(HighFunction highFunction) {
        HashMap<Address, List<PcodeOpAST>> pcodeMap = new HashMap<>();

        for (Iterator<PcodeOpAST> it = highFunction.getPcodeOps(); it.hasNext(); ) {
            PcodeOpAST pcode = it.next();
            Address addr = pcode.getSeqnum().getTarget();
            pcodeMap.computeIfAbsent(addr, k -> new ArrayList<>()).add(pcode);
        }

        for (Iterator<PcodeOpAST> it = highFunction.getPcodeOps(); it.hasNext(); ) {
            PcodeOpAST pcode = it.next();
            if (pcode.getOpcode() == PcodeOp.CBRANCH) {
                Varnode targetVarnode = pcode.getInput(0);
                long offset = pcode.getInput(0).getOffset();

                Instruction ins = this.globalCtx.getProgram().getListing().getInstructionAt(targetVarnode.getAddress());

                PcodeOp[] pcode_cb = this.globalCtx.getProgram().getListing().getInstructionAt(targetVarnode.getAddress()).getPcode();
                if(it.hasNext()){
                    PcodeOpAST false_branch = it.next();
                    System.out.println("false_branch: \n\t" + false_branch);
                }
            }
        }
    }

    private List<PcodeOpAST> getNextUsePcodeOps(Varnode varnode) {
        List<PcodeOpAST> useOps = new ArrayList<>();

        // find all the uses
        Iterator<PcodeOp> iter = varnode.getDescendants();

        while (iter.hasNext()) {
            PcodeOpAST next_pcode = (PcodeOpAST) iter.next();

            useOps.add(next_pcode);
        }

        return useOps;
    }



    private  GDirectedGraph<CodeBlock, GEdge<CodeBlock>>
    getFunctionDom(HighFunction highFunction) throws CancelledException {
        Function function = highFunction.getFunction();
        System.out.println("Function name : " + function.getName());
        TaskMonitor monitor = TaskMonitor.DUMMY;

        CodeBlockModel blockModel = new BasicBlockModel(function.getProgram());
        CodeBlockIterator blockIterator = blockModel.getCodeBlocksContaining(function.getBody(), monitor);
        GDirectedGraph<CodeBlock, DefaultGEdge<CodeBlock>> cfg = new JungDirectedGraph<>();

        Address entryAddress = function.getEntryPoint();
        CodeBlock entryBlock = blockModel.getFirstCodeBlockContaining(entryAddress, monitor);

        AddressSet addressSet = new AddressSet(entryAddress, entryAddress);

        CodeBlock virtualSourceBlock = new CodeBlockImpl(blockModel, new Address[]{entryAddress}, addressSet);

        if (entryBlock != null) {
            cfg.addVertex(entryBlock);
            cfg.addVertex(virtualSourceBlock);
            cfg.addEdge(new DefaultGEdge<>(virtualSourceBlock, entryBlock));
        }

        while (blockIterator.hasNext()) {
            CodeBlock block = blockIterator.next();
            System.out.println("We have block:" + block);
            cfg.addVertex(block);
        }
        blockIterator = blockModel.getCodeBlocksContaining(function.getBody(), monitor);
        while (blockIterator.hasNext()) {
            CodeBlock block = blockIterator.next();
            CodeBlockReferenceIterator dests = block.getDestinations(monitor);
            while (dests.hasNext()) {
                CodeBlockReference ref = dests.next();
                CodeBlock targetBlock = ref.getDestinationBlock();
                if (cfg.containsVertex(targetBlock)) {
                    cfg.addEdge(new DefaultGEdge<>(block, targetBlock));
                }else{
                    cfg.addVertex(targetBlock);
                    cfg.addEdge(new DefaultGEdge<>(block, targetBlock));
                }
                cfg.addEdge(new DefaultGEdge<>(virtualSourceBlock, targetBlock));
            }
        }
        GDirectedGraph<CodeBlock, GEdge<CodeBlock>> dominatorTree = null;
        try {
            dominatorTree = GraphAlgorithms.findDominanceTree(cfg, monitor);
        }
        catch (Exception exception){
            System.out.println(exception);
        }
        if(dominatorTree != null) {
            System.out.println("dominatorTree: " + dominatorTree);
        }
        return dominatorTree;

    }


    private List<CodeBlock> getDominators(Instruction instr, GDirectedGraph<CodeBlock, GEdge<CodeBlock>> dominatorTree) throws CancelledException {
        TaskMonitor monitor = TaskMonitor.DUMMY;
        CodeBlockModel blockModel = new BasicBlockModel(instr.getProgram());
        CodeBlock block = blockModel.getFirstCodeBlockContaining(instr.getAddress(), monitor);
        List<CodeBlock> dominators = new ArrayList<>();
        while (block != null) {
            dominators.add(block);
            List<CodeBlock> predecessors = new ArrayList<>(dominatorTree.getPredecessors(block));
            if (predecessors.isEmpty()) {
                break;
            }
            block = predecessors.get(0);
        }
        return dominators;
    }


    //get Pcode's dominating blocks
    private List<CodeBlock> getDominators(PcodeOp pcode, GDirectedGraph<CodeBlock, GEdge<CodeBlock>> dominatorTree) throws CancelledException {
        TaskMonitor monitor = TaskMonitor.DUMMY;
        CodeBlockModel blockModel = new BasicBlockModel(this.globalCtx.program);
        Address pcode_addr = pcode.getSeqnum().getTarget();
        Instruction pcode_inst = this.globalCtx.program.getListing().getInstructionAt(pcode_addr);
        return getDominators(pcode_inst, dominatorTree);
    }



}
