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


public class AccessPatternGraph {
    private GDirectedGraph<AccessPatternVertex, AccessPatternEdge> graph;
    private GDirectedGraph<AccessPatternVertex, AccessPatternEdge> rev_graph;

    private Map<Varnode, AccessPatternVertex> varnode_map = new HashMap<>();
    private Map<PcodeOp, AccessPatternVertex> op_map = new HashMap<>();
    private  GDirectedGraph<AccessPatternVertex, GEdge<AccessPatternVertex>> dom_tree;
    private  GDirectedGraph<AccessPatternVertex, GEdge<AccessPatternVertex>> rev_dom_tree;
    AccessPatternVertex source_vertex = new AccessPatternVertex("Dummy Source");
    AccessPatternVertex sink_vertex = new AccessPatternVertex("Dummy Sink");
    String function_name;
    HighFunction high_function;
    Function function;
    Parameter parameter;
    public AccessPatternGraph(HighFunction highFunction, Parameter parameter) {
        this.high_function = highFunction;
        this.parameter = parameter;
        this.graph = new JungDirectedGraph<>();
        this.graph.addVertex(source_vertex);
        this.graph.addVertex(sink_vertex);
        this.graph.addEdge(new AccessPatternEdge(source_vertex, sink_vertex));

    }


    public void AddEdge(AccessPatternVertex start, AccessPatternVertex end) {
        this.graph.addVertex(start);
        this.graph.addVertex(end);
        if(end.vex_type == AccessPatternVertex.VertexType.Op){
            if(end.op == PcodeOp.PTRADD || end.op == PcodeOp.PTRSUB){
                var offset = end.pcode_op.getInput(1);
                if (offset.isConstant()) {
                    end.offset_seq.add((int) offset.getOffset());
                }
            }
        } else if (start.vex_type == AccessPatternVertex.VertexType.Op) {
            if(start.op == PcodeOp.PTRADD || start.op == PcodeOp.PTRSUB){
                var offset = start.pcode_op.getInput(1);
                if (offset.isConstant()) {
                    end.offset_seq.add((int) offset.getOffset());
                }
            }
        }
        this.graph.addEdge(new AccessPatternEdge(start, end));

    }

    public AccessPatternVertex AddEdge(PcodeOp op){

        AccessPatternVertex op_vertex = new AccessPatternVertex(op);

        op_map.put(op, op_vertex);
        graph.addVertex(op_vertex);

        graph.addEdge(new AccessPatternEdge(source_vertex, op_vertex));
        graph.addEdge(new AccessPatternEdge(op_vertex, sink_vertex));


        for (int i = 0; i < op.getNumInputs(); i++) {
            Varnode input = op.getInput(i);
            AccessPatternVertex input_vertex = getOrCreateVarVertex(input);
            graph.addVertex(input_vertex);
            if(op_vertex.equals(source_vertex) || op_vertex.equals(sink_vertex)) { continue; }
            graph.addEdge(new AccessPatternEdge(input_vertex, op_vertex));
            graph.addEdge(new AccessPatternEdge(source_vertex, input_vertex));
            graph.addEdge(new AccessPatternEdge(input_vertex, sink_vertex));

        }

        Varnode output = op.getOutput();
        if (output != null) {
            AccessPatternVertex outputVertex = getOrCreateVarVertex(output);
            graph.addVertex(outputVertex);
            graph.addEdge(new AccessPatternEdge(op_vertex, outputVertex));
            graph.addEdge(new AccessPatternEdge(source_vertex, outputVertex));
            graph.addEdge(new AccessPatternEdge(outputVertex, sink_vertex));

        }

        return op_vertex;

    }

    public void AddBranchEdge(PcodeOp start, PcodeOp end){


        this.AddEdge(this.AddEdge(start), this.AddEdge(end));
    }


    public AccessPatternGraph(HighFunction highFunction) {
        this.function_name = highFunction.getFunction().getName();
        graph = new JungDirectedGraph<>();

        AccessPatternVertex source_vertex = new AccessPatternVertex("Dummy Source");
        AccessPatternVertex sink_vertex = new AccessPatternVertex("Dummy Sink");
        graph.addVertex(source_vertex);
        graph.addVertex(sink_vertex);

        for (Iterator<PcodeOpAST> it = highFunction.getPcodeOps(); it.hasNext(); ) {
            PcodeOp op = it.next();
            AccessPatternVertex op_vertex = new AccessPatternVertex(op);

            op_map.put(op, op_vertex);
            graph.addVertex(op_vertex);
//            rev_graph.addVertex(op_vertex);

            graph.addEdge(new AccessPatternEdge(source_vertex, op_vertex));
            graph.addEdge(new AccessPatternEdge(op_vertex, sink_vertex));

//            rev_graph.addEdge(new AccessPatternEdge(op_vertex, source_vertex));
//            rev_graph.addEdge(new AccessPatternEdge(sink_vertex, op_vertex));

            for (int i = 0; i < op.getNumInputs(); i++) {
                Varnode input = op.getInput(i);
                AccessPatternVertex input_vertex = getOrCreateVarVertex(input);
                graph.addVertex(input_vertex);
                if(op_vertex.equals(source_vertex) || op_vertex.equals(sink_vertex)) { continue; }
                graph.addEdge(new AccessPatternEdge(input_vertex, op_vertex));
                graph.addEdge(new AccessPatternEdge(source_vertex, input_vertex));
                graph.addEdge(new AccessPatternEdge(input_vertex, sink_vertex));

//                rev_graph.addEdge(new AccessPatternEdge(op_vertex, input_vertex));
//                rev_graph.addEdge(new AccessPatternEdge(input_vertex, source_vertex));
//                rev_graph.addEdge(new AccessPatternEdge(sink_vertex, input_vertex));
            }

            Varnode output = op.getOutput();
            if (output != null) {
                AccessPatternVertex outputVertex = getOrCreateVarVertex(output);
                graph.addVertex(outputVertex);
                graph.addEdge(new AccessPatternEdge(op_vertex, outputVertex));
                graph.addEdge(new AccessPatternEdge(source_vertex, outputVertex));
                graph.addEdge(new AccessPatternEdge(outputVertex, sink_vertex));

//                rev_graph.addVertex(outputVertex);
//                rev_graph.addEdge(new AccessPatternEdge(outputVertex, op_vertex));
//                rev_graph.addEdge(new AccessPatternEdge(outputVertex, source_vertex));
//                rev_graph.addEdge(new AccessPatternEdge(sink_vertex, outputVertex));

            }
        }
        graph.addEdge(new AccessPatternEdge(source_vertex, sink_vertex));


        try {
            Set<AccessPatternVertex> dummy_source_for_clean = new HashSet<>();

            for (AccessPatternVertex v : graph.getVertices()) {
                if (v.vex_type == AccessPatternVertex.VertexType.Dummy && "Dummy Source".equals(v.name)) {
                    dummy_source_for_clean.add(v);
                }
            }

            for (AccessPatternVertex v : dummy_source_for_clean) {
                var in_edges = new HashSet<>(graph.getInEdges(v));
                graph.removeEdges(in_edges);
            }

            var source_set = GraphAlgorithms.getSources(graph);
            var rev_source_set = GraphAlgorithms.getSources(rev_graph);
            System.out.println("the source num: " + source_set.size() + " rev source" + rev_source_set);
            this.dom_tree = GraphAlgorithms.findDominanceTree(graph, TaskMonitor.DUMMY);
            this.rev_graph = reverseGraph(graph);
            this.rev_dom_tree = GraphAlgorithms.findDominanceTree(reverseGraph(this.rev_graph), TaskMonitor.DUMMY);
        }
        catch (Exception e){
            System.out.println("CFGbased dom error : " + e);
        }
    }

    private AccessPatternVertex getOrCreateVarVertex(Varnode varnode) {
        return varnode_map.computeIfAbsent(varnode, AccessPatternVertex::new);
    }

    public GDirectedGraph<AccessPatternVertex, AccessPatternEdge> getGraph() {
        return graph;
    }

    public void exportToDot(String filePath) {
        try (FileWriter writer = new FileWriter(filePath)) {
            writer.write("digraph SeaOfNodes {\n");

            for (AccessPatternVertex vertex : graph.getVertices()) {
                if (vertex.vex_type == AccessPatternVertex.VertexType.Dummy) continue;
                String nodeId = getNodeId(vertex);
                String label = escapeDotLabel(vertex.toString());
                String shape = (vertex.vex_type == AccessPatternVertex.VertexType.Op) ? "box" : "ellipse";
                writer.write(String.format("  %s [label=\"%s\", shape=%s];\n", nodeId, label, shape));
            }

            for (AccessPatternEdge edge : graph.getEdges()) {

                AccessPatternVertex from = edge.getStart();
                AccessPatternVertex to = edge.getEnd();

                if (from.vex_type == AccessPatternVertex.VertexType.Dummy || to.vex_type == AccessPatternVertex.VertexType.Dummy)
                    continue;

                writer.write(String.format("  %s -> %s;\n", getNodeId(from), getNodeId(to)));
            }

            writer.write("}\n");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    public void exportToDupDot(String filePath) {
        try (FileWriter writer = new FileWriter(filePath)) {
            writer.write("digraph SeaOfNodes {\n");

            for (AccessPatternVertex vertex : graph.getVertices()) {
                if (vertex.vex_type == AccessPatternVertex.VertexType.Dummy) continue;
                String nodeId = getNodeId(vertex);
                String label = escapeDotLabel(vertex.toString());
                String shape = (vertex.vex_type == AccessPatternVertex.VertexType.Op) ? "box" : "ellipse";
                writer.write(String.format("  %s [label=\"%s\", shape=%s];\n", nodeId, label, shape));
            }


            Set<String> seenEdges = new HashSet<>();

            for (AccessPatternEdge edge : graph.getEdges()) {
                AccessPatternVertex from = edge.getStart();
                AccessPatternVertex to = edge.getEnd();

                if (from.vex_type == AccessPatternVertex.VertexType.Dummy || to.vex_type == AccessPatternVertex.VertexType.Dummy)
                    continue;

                String edgeKey = getNodeId(from) + "->" + getNodeId(to);
                if (seenEdges.contains(edgeKey)) continue;

                seenEdges.add(edgeKey);
                writer.write(String.format("  %s -> %s;\n", getNodeId(from), getNodeId(to)));
            }

            writer.write("}\n");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    public void exportDomTreeToDot(String filePath) {
        if (dom_tree == null) {
            System.err.println("❌ Dom tree is null, skipping export.");
            return;
        }

        try (FileWriter writer = new FileWriter(filePath)) {
            writer.write("digraph DominatorTree {\n");

            for (AccessPatternVertex vertex : dom_tree.getVertices()) {
                if (vertex.vex_type == AccessPatternVertex.VertexType.Dummy) continue;
                String nodeId = getNodeId(vertex);
                String label = escapeDotLabel(vertex.toString());
                String shape = (vertex.vex_type == AccessPatternVertex.VertexType.Op) ? "box" : "ellipse";
                writer.write(String.format("  %s [label=\"%s\", shape=%s];\n", nodeId, label, shape));
            }

            for (GEdge<AccessPatternVertex> edge : dom_tree.getEdges()) {
                AccessPatternVertex from = edge.getStart();
                AccessPatternVertex to = edge.getEnd();
                if (from.vex_type == AccessPatternVertex.VertexType.Dummy || to.vex_type == AccessPatternVertex.VertexType.Dummy)
                    continue;

                writer.write(String.format("  %s -> %s;\n", getNodeId(from), getNodeId(to)));
            }

            writer.write("}\n");
        } catch (IOException e) {
            System.err.println("❌ Failed to export Dom Tree: " + e);
            e.printStackTrace();
        }
    }

    public void exportRevDomTreeToDot(String filePath) {
        if (this.rev_dom_tree == null) {
            System.err.println("❌ Dom tree is null, skipping export.");
            return;
        }

        try (FileWriter writer = new FileWriter(filePath)) {
            writer.write("digraph DominatorTree {\n");

            for (AccessPatternVertex vertex : rev_dom_tree.getVertices()) {
                if (vertex.vex_type == AccessPatternVertex.VertexType.Dummy) continue;
                String nodeId = getNodeId(vertex);
                String label = escapeDotLabel(vertex.toString());
                String shape = (vertex.vex_type == AccessPatternVertex.VertexType.Op) ? "box" : "ellipse";
                writer.write(String.format("  %s [label=\"%s\", shape=%s];\n", nodeId, label, shape));
            }

            for (GEdge<AccessPatternVertex> edge : rev_dom_tree.getEdges()) {
                AccessPatternVertex from = edge.getStart();
                AccessPatternVertex to = edge.getEnd();
                if (from.vex_type == AccessPatternVertex.VertexType.Dummy || to.vex_type == AccessPatternVertex.VertexType.Dummy)
                    continue;

                writer.write(String.format("  %s -> %s;\n", getNodeId(from), getNodeId(to)));
            }

            writer.write("}\n");
        } catch (IOException e) {
            System.err.println("❌ Failed to export Dom Tree: " + e);
            e.printStackTrace();
        }
    }

    private GDirectedGraph<AccessPatternVertex, AccessPatternEdge> reverseGraph(GDirectedGraph<AccessPatternVertex, AccessPatternEdge> original) {
        GDirectedGraph<AccessPatternVertex, AccessPatternEdge> reversed = new JungDirectedGraph<>();

        for (AccessPatternVertex v : original.getVertices()) {
            reversed.addVertex(v);
        }

        for (AccessPatternEdge edge : original.getEdges()) {
            reversed.addEdge(new AccessPatternEdge(edge.getEnd(), edge.getStart()));
        }

        return reversed;
    }


    private String getNodeId(AccessPatternVertex vertex) {
        if (vertex.vex_type == AccessPatternVertex.VertexType.Op) {
            return "op_" + vertex.pcode_op.getSeqnum().getTime();
        } else if (vertex.vex_type == AccessPatternVertex.VertexType.Var){
            return "var_" + vertex.var_node.hashCode();
        }else{
            return "Dummy_" + vertex.name;
        }
    }

    private String escapeDotLabel(String label) {
        return label.replace("\"", "\\\"");
    }

}
