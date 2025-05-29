import generic.stl.Pair;
import ghidra.dbg.gadp.protocol.Gadp;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.Function;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.stream.Collectors;

public class StructFieldArray {
    HashMap<PcodeOpAST,Integer> pcode2Index;
    HashMap<Integer,PcodeOpAST> index2Pcode;
    List<StructField> structFields;
    Function current_function;
    HighFunction current_high_function;
    public StructFieldArray(HighFunction highFunction){
        this.current_high_function = highFunction;
        this.current_function = highFunction.getFunction();
        pcode2Index = new HashMap<>();
        index2Pcode = new HashMap<>();
        structFields = new ArrayList<>();
    }
    public void addStructField(StructField field){
        structFields.add(field);
    }
    public void addPcodeOpAST(PcodeOpAST pcode){
        if(!pcode2Index.containsKey(pcode)){
            int index = pcode2Index.size();
            pcode2Index.put(pcode,pcode2Index.size());
            index2Pcode.put(index,pcode);
        }
    }
    private List<StructField> sortStructFields(){
        List<StructField> sortUniqueFields = structFields.stream().sorted(Comparator.comparing(f->f.getAddress(), Comparator.reverseOrder()))
                .distinct()
                .collect(Collectors.toList());
        return sortUniqueFields;
    }
    private boolean VarnodeOpASTEqual(Varnode v1, Varnode v2){
        if(v1 == null || v2 == null) return false;
        if(v1.getAddress().equals(v2.getAddress()) &&
                v1.getSize() == v2.getSize()&&
                v1.getOffset()==v2.getOffset()){
            return true;
        }
        else
            return false;
    }
    private boolean PcodeOpASTEqual(PcodeOpAST p1, PcodeOpAST p2){
        if(p1 == null || p2 == null) return false;
        if(VarnodeOpASTEqual(p1.getOutput() ,p2.getOutput())){
            return true;
        }
        else
            return false;
    }
    public List<Pair<DataType,PcodeOpAST>> analyzeHeadList(List<PcodeOpAST> pcodeOpASTs){
        //update the array
        //ensure the addresses are continuous
        //may cause problem: decrese the struct we identified by
        //stack pointer
        //this.structFields = sortStructFields();

        if(pcodeOpASTs.size()<=1) return null;
        List<Pair<DataType,PcodeOpAST>> result = new ArrayList<>();
        PcodeOpAST curr_head = pcodeOpASTs.get(0);
        PcodeOpAST next_head = pcodeOpASTs.get(1);
        int num = 1;
//        for(StructField field :structFields){
//            System.out.println("field info: " + field.pcode);
//            System.out.println("head :" + pcodeOpASTs.get(0));
//            System.out.println("equal :"+ PcodeOpASTEqual(pcodeOpASTs.get(0),field.pcode));
//        }
        Pair<DataType,PcodeOpAST> dtypepair;
        while(curr_head !=null && next_head !=null){
            //System.out.println("enter loop"+ structFields.size());
            int left = 0, right = 0;

            for(int field_index = 0; field_index < structFields.size(); field_index++){
                if(PcodeOpASTEqual(structFields.get(field_index).pcode, curr_head)){
                    //we found a head in structFieldArray
                    for(int next_field_index = field_index+1; next_field_index < structFields.size(); next_field_index++){
                        if(PcodeOpASTEqual(structFields.get(next_field_index).pcode , next_head)){
                            // we need to merge the array
                            left = field_index;
                            right = next_field_index;
                            //System.out.println("left : "+left +"right "+ right);
                        }
                    }
                }
            }
            if(left<right && right!=0){
                for(int field_index = left; field_index < right; field_index++){
                    System.out.println("struct : "+left+ "field size :" + structFields.get(field_index).getSize() );
                }
                DataType dtype = toDataType(structFields,left,right);
                //???
                dtypepair = new Pair<>(dtype,curr_head);
                result.add(dtypepair);
            }
            curr_head = next_head;
            num+=1;
            if(num>=pcodeOpASTs.size()){ break;}
            next_head = pcodeOpASTs.get(num);
        }
        if(next_head!=null){
            //greedy build struct
            int last_field_index = 0;
            System.out.println("Last structure");
            for(int field_index = 0; field_index < structFields.size(); field_index++){
                if(PcodeOpASTEqual(structFields.get(field_index).pcode, next_head)){
                    last_field_index = field_index;
                    for(int last_index = field_index+1; last_index < structFields.size(); last_index++){
                        System.out.println("struct : "+field_index+ "field size :" + structFields.get(last_index).getSize() );
                    }
                }
            }
            if(last_field_index!=structFields.size()){
                dtypepair = new Pair<>(toDataType(structFields,last_field_index,structFields.size()),next_head);
                result.add(dtypepair);
            }
        }
        return result;
    }
    static int type_index = 0;
    public DataType toDataType(List<StructField> field, int left, int right){
        Structure struct = new StructureDataType("Test"+type_index++, 0);
        int field_num =0;
        for(int field_index = left; field_index < right; field_index++){
            struct.add(new ByteDataType(),field.get(field_index).getSize(),"field_"+field_num++,null);
        }
        return struct;
    }

}
