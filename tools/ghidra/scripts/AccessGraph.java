import java.util.HashSet;
import java.util.Set;



public class AccessGraph {
    private Set<AccessEdge> edges = new HashSet<>();

    public AccessGraph(Set<AccessEdge> edges) {
        this.edges = edges;
    }
}

