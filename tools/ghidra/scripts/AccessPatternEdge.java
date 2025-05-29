import ghidra.graph.DefaultGEdge;

public class AccessPatternEdge extends DefaultGEdge<AccessPatternVertex> {
    public AccessPatternEdge(AccessPatternVertex start, AccessPatternVertex end) {
        super(start, end);
    }
}