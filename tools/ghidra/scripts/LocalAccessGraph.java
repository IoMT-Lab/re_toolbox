import ghidra.program.model.pcode.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Parameter;

import java.util.*;

public class LocalAccessGraph{
    private Parameter parameter;
    private VarnodeAST start_varnodeAST;
    private Set<PcodeOpAST> pcodeOpASTSet;
    private Set<AccessEdge> accessEdges = new HashSet<>();

    private Set<PcodeOp> pcode_set = new HashSet<>();
    private Set<Varnode> in_varnode_set = new HashSet<>();
    private Set<Varnode> out_varnode_set = new HashSet<>();
    private Map<Varnode, AccessEdge> output_access_map = new HashMap<>();
    //private Map<Varnode, AccessEdge> input_access_map = new HashMap<>();
    private Map<AccessEdge, Set<AccessEdge>> access_succ_map = new HashMap<>();
    private Map<AccessEdge, Set<AccessEdge>> access_prev_map = new HashMap<>();
    private Map<Long, AccessEdge> load_source_map = new HashMap<>();

    public HighFunction highFunction;
    private AccessEdge start_edge;
    public Set<PcodeOp> getPcodeSet()
    {
        return pcode_set;
    }
    public void addPcode(PcodeOp pcode)
    {
        this.pcode_set.add(pcode);
    }

    public Set<AccessEdge> getAccessEdges()
    {
        return accessEdges;
    }

    public HighFunction getHighFunction()
    {
        return highFunction;
    }

    public  LocalAccessGraph(Parameter para)
    {
        this.parameter = para;
    }
    public AccessEdge getStartEdge()
    {
        return start_edge;
    }

    private void addSuccAccessEdge(AccessEdge prev_edge, AccessEdge next_edge)
    {
        if(prev_edge == null) return;
        System.out.println("\"" + prev_edge.pcode_op + "\" -> \""  + next_edge.pcode_op +"\";");
        if (access_succ_map.containsKey(prev_edge)) {
            access_succ_map.get(prev_edge).add(next_edge);

        } else {
            Set<AccessEdge> successors = new HashSet<>();
            successors.add(next_edge);
            access_succ_map.put(prev_edge, successors);
        }

        if(access_prev_map.containsKey(next_edge)){
            access_prev_map.get(next_edge).add(prev_edge);
        }
        else {
            Set<AccessEdge> predecessor = new HashSet<>();
            predecessor.add(prev_edge);
            access_prev_map.put(next_edge, predecessor);
        }
    }
    public Set<AccessEdge> getSuccAccessEdge(AccessEdge edge)
    {
        return access_succ_map.get(edge);
    }
    public Set<AccessEdge> getPredAccessEdge(AccessEdge edge)
    {
        return access_prev_map.get(edge);
    }
    public void addEdge(PcodeOp pcode){
        //System.out.println("adding pcode to the edge " + pcode);
        if(this.pcode_set.contains(pcode)){
            return;
        }
        this.pcode_set.add(pcode);

        AccessEdge edge = new AccessEdge(pcode);
        if(this.accessEdges.isEmpty()){
            this.start_edge = edge;
        }
        this.accessEdges.add(edge);

        for(var input : pcode.getInputs()){
            if(this.load_source_map.containsKey(input.getAddress().getOffset()) && pcode.getOpcode() == PcodeOp.LOAD){
                addSuccAccessEdge(this.load_source_map.get(input.getAddress().getOffset()), edge);
            }

            if(out_varnode_set.contains(input)){
                AccessEdge prev = output_access_map.get(input);
                addSuccAccessEdge(prev, edge);
            }
            for(var out : out_varnode_set){
                if(out.equals(input)){
                    AccessEdge prev = output_access_map.get(out);
                    addSuccAccessEdge(prev, edge);
                }
            }
            this.in_varnode_set.add(input);
        }
        if(pcode.getOpcode() == PcodeOp.LOAD){
            //System.out.println("pcode : "+pcode +"  +address" + pcode.getInput(0).getAddress().getOffset());
            output_access_map.put(pcode.getInput(0), edge);
            output_access_map.put(pcode.getInput(1), edge);

            this.load_source_map.put(pcode.getInput(0).getAddress().getOffset(), edge);
        }
        if(pcode.getOutput() != null) {
            out_varnode_set.add(pcode.getOutput());
            output_access_map.put(pcode.getOutput(), edge);
        }
    }

    public void addControlEdge(PcodeOp source, PcodeOp target, int edge_tag){
        List<AccessEdge> new_edges = AccessEdge.AccessControlEdge(source, target, edge_tag);
        accessEdges.addAll(new_edges);
    }

}
