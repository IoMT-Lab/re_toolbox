import ghidra.graph.DefaultGEdge;
import ghidra.graph.GEdge;
import ghidra.graph.GDirectedGraph;
import ghidra.graph.GraphAlgorithms;
import ghidra.graph.jung.JungDirectedGraph;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Parameter;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;
import ghidra.util.task.TaskMonitor;

import java.io.FileWriter;
import java.io.IOException;
import java.util.*;


class AccessPatternVertex{
    enum VertexType {
        Var,
        Op,
        Dummy,
    };

    VertexType vex_type;
    Varnode var_node;
    PcodeOp pcode_op;
    int op;

    List<Integer> offset_seq = new ArrayList<>();

    String name;
    public AccessPatternVertex(String name) {
        this.vex_type = VertexType.Dummy;
        this.name = name;
    }

    public AccessPatternVertex(Varnode varnode) {
        this.vex_type = VertexType.Var;
        this.var_node = varnode;
    }

    public AccessPatternVertex(PcodeOp pcodeop) {
        this.vex_type = VertexType.Op;
        this.pcode_op = pcodeop;
        this.op = pcodeop.getOpcode();
    }

    @Override
    public String toString() {
        if (vex_type == VertexType.Var) {
            if (var_node.isConstant()) {
                return String.format("Const: 0x%x (size=%d)", var_node.getOffset(), var_node.getSize());
            }
            return "Var: " + var_node.toString();
        } else if (vex_type == VertexType.Op) {
            if (!offset_seq.isEmpty()) {
                return "Op: " + pcode_op.getMnemonic() + " Offsets: " + offset_seq;
            }
            return "Op: " + pcode_op.getMnemonic();
        } else {
            return "Dummy: " + name;
        }
    }

    // Hash based on identity
    @Override
    public int hashCode() {
        return Objects.hash(vex_type, var_node, pcode_op);
    }

    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof AccessPatternVertex)) return false;
        AccessPatternVertex other = (AccessPatternVertex) obj;
        return Objects.equals(var_node, other.var_node) &&
                Objects.equals(pcode_op, other.pcode_op) &&
                vex_type == other.vex_type;
    }

}