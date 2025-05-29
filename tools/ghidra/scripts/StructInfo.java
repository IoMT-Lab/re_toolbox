import generic.stl.Pair;

import java.util.ArrayList;
import java.util.List;

public class StructInfo {
    List<Pair<Integer,StructField>> structFields;
    List<Pair<StructField,Integer>> fieldStructs;
    StructInfo(){
        this.structFields = new ArrayList<>();
        this.fieldStructs = new ArrayList<>();
    }
    void addStructField(StructField sf){
        int idx = structFields.size();
        Pair<Integer, StructField> fieldPair = new Pair<>(idx, sf);
        Pair<StructField,Integer> StructFieldPair = new Pair<>(sf, idx);
        structFields.add(fieldPair);
        fieldStructs.add(StructFieldPair);
    }
}
