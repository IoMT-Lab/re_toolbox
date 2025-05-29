import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;
import ghidra.program.model.pcode.VarnodeAST;

import java.util.*;



public class AccessEdge {
    enum EdgeType{
        Copy,
        Store,
        Load,
        GetElementPtr,
        CMP,
        Select,
        Error
    }
    public Set<Varnode> source = new HashSet<>();
    public Set<Varnode> destination = new HashSet<>();

    public List<Integer> source_offset_seq = new ArrayList<>();
    public List<Integer> dest_offset_seq = new ArrayList<>();

    public Integer offset = 0;

    private PcodeOpAST edge_pcode;
    public EdgeType edge_type;
    public int edge_tag;
    public PcodeOp pcode_op = null;

    public Set<Varnode> getSource() {
        return source;
    }
    public Set<Varnode> getDestination() {
        return destination;
    }

    //    public AccessEdge(VarnodeAST source, VarnodeAST destination, PcodeOpAST edge_pcode) {
//        this.source = source;
//        this.destination = destination;
//        this.edge_pcode = edge_pcode;
//        this.setEdgeType();
//    }
    public AccessEdge(PcodeOp pcode){
        for(var input : pcode.getInputs()){
            source.add(input);
        }
        if(pcode.getOutput() != null){
            destination.add(pcode.getOutput());
        }
        this.edge_tag = pcode.getOpcode();
        this.pcode_op = pcode;
    }
    public AccessEdge(Varnode source, Varnode destination, int edge_tag){
        this.edge_tag = edge_tag;
        this.source.add(source);
        this.destination.add(destination);
    }
    static public List<AccessEdge> AccessControlEdge(PcodeOp source_op, PcodeOp dest_op, int edge_tag){
        List<AccessEdge> result = new ArrayList<>();
        if(source_op.getOutput() != null) {
            //this.source.add(source_op.getOutput());

            int dest_num = dest_op.getNumInputs();

            for (int i = 0; i < dest_num; i++) {
                AccessEdge mult_edge = new AccessEdge(source_op.getOutput(), dest_op.getInput(i), edge_tag);
                result.add(mult_edge);
            }
        }else{
            for(var source_input : source_op.getInputs()){
                for(var dest_input : dest_op.getInputs()){
                    AccessEdge mult_edge = new AccessEdge(source_input, dest_input, edge_tag);
                    result.add(mult_edge);
                }
            }
        }
        return result;
    }

    private void setEdgeType(int pcodeopcode){
        this.edge_tag = pcodeopcode;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        AccessEdge that = (AccessEdge) o;
        return Objects.equals(source, that.source) && Objects.equals(destination, that.destination) && Objects.equals(edge_pcode, that.edge_pcode) && edge_type == that.edge_type;
    }

    @Override
    public int hashCode() {
        return Objects.hash(source, destination, edge_pcode, edge_type);
    }
}
