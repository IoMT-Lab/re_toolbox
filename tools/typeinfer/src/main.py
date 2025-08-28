import os
import sys
import textwrap

from typing import Optional, Dict, List

from alias_visitor import AliasVisitor
from combined_flow_sensitive_analyzer import CombinedFlowSensitiveAnalyzer
from dense_graph import CFLRule, EdgePattern, AddressOfEdge, DereferenceEdge, EqualsEdge, OperationEdge, Var
from function_extractor import extract_functions_from_file
from ssa_parser_ply import parser, lexer
from type_definitions import UnknownType, UNKNOWN
from log_setup import setup_logging
from loguru import logger

from type_propagator import TypePropagator
from utils import time_it, append_var_type_json, append_var_type_jsonl
from cfg import ControlFlowGraph

from ssainput import ssa_text

import argparse

from var_map_extractor import extract_all_vars_map_from_file


@time_it
def parse_ssa(ssa_text):
    all_instructions = []
    for line_num, line in enumerate(ssa_text.strip().split('\n'), 1):
        line = line.strip()

        if not line:
            continue
        if line.startswith('...'):
            line = line.lstrip('.').strip()

        try:
            instruction = parser.parse(line, lexer=lexer.clone())  # Use a clone of the lexer
            if instruction:
                all_instructions.append(instruction)
            else:
                pass
        except Exception as e:
            print(f"Error parsing line {line_num}: '{line}' -> {e}")

    if len(all_instructions) > 0:
        return all_instructions
    return None


def get_all_grammar():
    andersen_rule = CFLRule(
        patterns=[EdgePattern(AddressOfEdge), EdgePattern(DereferenceEdge)],
        result_factory=lambda bindings: EqualsEdge()
    )

    add_sub_cancel_rule = CFLRule(
        patterns=[
            EdgePattern(OperationEdge, 'IntAdd', Var('k')),
            EdgePattern(OperationEdge, 'IntSub', lambda b: b.get('k'))
        ],
        result_factory=lambda bindings: EqualsEdge()
    )
    assign_rule = CFLRule(
        patterns=[EdgePattern(OperationEdge, 'Assign')],
        result_factory=lambda bindings: EqualsEdge()
    )
    full_grammar = [andersen_rule, add_sub_cancel_rule, assign_rule]
    return full_grammar


def parse_function_name_from_variable(variable_key: str) -> Optional[str]:
    parts = variable_key.split('@')
    if len(parts) >= 3:

        return parts[1]
    return None


def demo():
    ssa_insts = parse_ssa(ssa_text)
    ssa_insts = [inst for inst in ssa_insts if
                 inst.operation not in ("FunctionStart", "FunctionEnd", "NOP")]

    ssa_name = "v275"


    cfg = ControlFlowGraph()
    cfg.build(ssa_insts)
    cfsa = CombinedFlowSensitiveAnalyzer(cfg)
    cfsa.visit_program_flow_insensitive()
    cfsa.run_gvn_simplification()
    g = cfsa.get_graph()
    g.run_cfl_solver(get_all_grammar())
    start_node_id = g.find_node_by_name(ssa_name)
    if start_node_id:
        forward_slice = g.get_reachable_subgraph(start_node_id)
        type_propagator = TypePropagator(forward_slice)
        type_propagator.run()
        #type_propagator.get_graph().generate_dot("infer_result.dot")

        final_types, final_structs = type_propagator.get_final_report()
        ssa_var_type = type_propagator.get_variable_type(start_node_id)


    else:
        pass


def analyze(ssa_file_path, var_map_file_path, output_jsonl_path):
    error_dir = "error"


    all_functions: Dict[str, str] = extract_functions_from_file(ssa_file_path)

    variable_map: Dict[str, List[str]] = extract_all_vars_map_from_file(var_map_file_path)

    analysis_results: Dict[str, TypePropagator] = {}

    for func_id, (func_name, ssa_code) in enumerate(all_functions.items()):
        logger.info(f"--- analyzing {func_id + 1}/{len(all_functions)}: {func_name} ---")
        try:
            ssa_insts = parse_ssa(ssa_code)
            ssa_insts = [inst for inst in ssa_insts if inst.operation not in ("FunctionStart", "FunctionEnd", "NOP")]
            if not ssa_insts:
                continue

            cfg = ControlFlowGraph()
            cfg.build(ssa_insts)

            cfsa = CombinedFlowSensitiveAnalyzer(cfg)
            cfsa.visit_program_flow_insensitive()
            cfsa.run_gvn_simplification()
            g = cfsa.get_graph()
            g.run_cfl_solver(get_all_grammar())
            #g.generate_dot("single_graph_cfl.dot")
            type_propagator = TypePropagator(g)
            type_propagator.run()
            #type_propagator.get_graph().generate_dot("single_graph_type_propagator.dot")
            analysis_results[func_name] = type_propagator
            logger.success(f"func '{func_name}' done")

        except Exception as e:
            logger.error(f"func '{func_name}' error {e}", exc_info=True)
            if not os.path.exists(error_dir):
                os.makedirs(error_dir)
            error_ssa_path = os.path.join(error_dir, f"error_analysis_{func_name}.txt")
            with open(error_ssa_path, "w", encoding="utf-8") as f:
                f.write(f"# Error during analysis phase for function: {func_name}\n\n")
                f.write(ssa_code)
            logger.info(f"wrong ssa code has be saved to: {error_ssa_path}")

    logger.info("======================== STAGE 1 FINISHED ========================")


    logger.info("======================== STAGE 2: query variables ========================")
    for vid, target_global_var in enumerate(variable_map):
        logger.debug(f"--- query {vid + 1}/{len(variable_map)}: {target_global_var} ---")

        target_func_name = parse_function_name_from_variable(target_global_var)
        if not target_func_name:
            continue

        type_propagator = analysis_results.get(target_func_name)
        if not type_propagator:
            continue

        ssa_name_list = variable_map.get(target_global_var, [])

        all_inferred_types = []
        for ssa_name in ssa_name_list:
            ssa_var_type = type_propagator.get_variable_type(ssa_name)
            if ssa_var_type:
                all_inferred_types.append(ssa_var_type)

        if len(all_inferred_types) > 0:
            final_joined_type = all_inferred_types[0]
            for t in all_inferred_types:
                final_joined_type.join(t)

            logger.success(f"query successfully '{target_global_var}' -> {final_joined_type}")
            append_var_type_jsonl(output_jsonl_path, target_global_var, final_joined_type)
        else:
            logger.warning(f"cannot find'{target_global_var}' in '{target_func_name}' any type。")

    logger.info("======================== STAGE 2 FINISHED ========================")


def run_demo():
    demo()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog='TypeInferenceService',
        description='=== SSA Code Type Inference Tool ===\n'
                    'This service infers variable types from a Static Single Assignment (SSA)\n'
                    'code file and a corresponding variable map file.',
        epilog='Example usage:\n'
               '  python %(prog)s my_code_ssa.txt variables_map.txt -o result.json\n'
               '  python %(prog)s --demo\n\n'
               'Please ensure the provided file paths are correct.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--demo',
        action='store_true',
        help='Show a demonstration of the service with example inputs and exit.'
    )

    parser.add_argument(
        'ssa_file',
        metavar='SSA_CODE_FILE',
        type=str,
        nargs='?',
        default=None,
        help='Path to the input file containing the code in SSA (Static Single Assignment) format.'
    )

    parser.add_argument(
        'var_map_file',
        metavar='VAR_MAP_FILE',
        type=str,
        nargs='?',
        default=None,
        help='Path to the input file containing the variable name mappings.'
    )

    parser.add_argument(
        '-o', '--output',
        metavar='OUTPUT_FILE',
        type=str,
        default=None,
        help='Specify a file path to save the inference results. If not provided, results are printed to the console.'
    )


    args = parser.parse_args()

    if args.demo:
        run_demo()

    if not args.ssa_file or not args.var_map_file:
        print("Error: You must provide both SSA_CODE_FILE and VAR_MAP_FILE unless using --demo.")
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.ssa_file):
        print(f"Error: SSA code file not found at -> '{args.ssa_file}'")
        sys.exit(1)

    if not os.path.exists(args.var_map_file):
        print(f"Error: Variable map file not found at -> '{args.var_map_file}'")
        sys.exit(1)

    print("--- Type Inference Service Initialized ---")
    print(f"SSA Code File: {args.ssa_file}")
    print(f"Variable Map File: {args.var_map_file}")

    analyze(args.ssa_file, args.var_map_file, args.output)

    if args.output:
        print(f"Inference results will be saved to: {args.output}")
    else:
        print("Inference results will be printed to the console.")



if __name__ == '__main__':
    main()