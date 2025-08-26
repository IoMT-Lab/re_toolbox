"""
We define three roles in this file.

advisor: output the specific advice, how to change
operator: partially adopt the advice from advisor, ensure the original semantic
referee: comment on the changed code, provide next step for refinement
"""

import os
import re
import sys
import traceback
import json
import argparse
import signal
from enum import Enum, unique
from typing import Optional, Dict, List, Tuple
from cinspector.interfaces import CCode
from cinspector.nodes import Util

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(DIR, '.'))
OUTPUT_DIR = os.path.join(os.path.dirname(DIR), 'output')
from util import Log, is_code_in_response, response_filter, check_dir, get_output_filenames
from mssc import SemanticComparison
from chat import QueryChatGPT

logger = Log().get(__file__)

PROMPT_PATH = os.path.join(DIR, 'prompt.json')  # file path storing the prompts


def run_timer(func, *, args = [], time = 1, info = 'run_timer failed'):
    def timeout_callback(signum, frame):
        raise Exception('timeout')

    signal.signal(signal.SIGALRM, timeout_callback)
    signal.alarm(time)
    try:
        rtn = func(*args)
        signal.alarm(0)
        return rtn
    except Exception as e:
        print(e)
        print(info)
        return None


def is_valid_json(data: str) -> bool:
    try:
        json.loads(data)
    except ValueError:
        return False
    return True


def get_prompt(name: str, _type: str, prompt_path: str = PROMPT_PATH) -> Optional[Dict[str, str]]:
    import json
    prompts = None
    with open(prompt_path, 'r') as f:
        prompts = json.load(f)
    assert prompts
    for _p in prompts:
        if _p['name'] == name and _p['type'] == _type:
            return _p['prompt']
    return None


@unique
class DType(str, Enum):
    ADD_COMMENT = 'ADD_COMMENT'
    RENAME_VAR = 'RENAME_VAR'
    SIMPLIFY = 'SIMPLIFY'
    STRUCT_REC = 'STRUCT_REC'
    CF_SIMPLIFY = 'CF_SIMPLIFY'
    LIB_REC = 'LIB_REC'
    ALL = 'ALL'


class Role:
    def __init__(self):
        pass


class Advisor(Role):
    def __init__(self):
        self.dtype_mapping = {
            DType.ADD_COMMENT: self._add_comment,
            DType.RENAME_VAR: self._rename_var,
            DType.SIMPLIFY: self._simplify,
            DType.STRUCT_REC: self._struct_rec,
            DType.CF_SIMPLIFY: self._cf_simplify,
            DType.LIB_REC: self._lib_rec,
        }

    def get_advice(self, code: str, dtype: DType) -> Tuple[str, Optional[str]]:
        if dtype not in self.dtype_mapping.keys():
            logger.warning(f"Fail to get the processing method for the dtype {dtype}, skip")
            return (code, None)
        method = self.dtype_mapping[dtype]
        code, response = method(code)
        return (code, response)

    @staticmethod
    def _replace_variable_name(old_new_dic, code) -> str:
        cc = CCode(code)
        ids = cc.get_by_type_name('identifier')
        old_names = list(old_new_dic.keys())
        for id in ids:
            s_pos = Util.point2index(code, id.start_point[0], id.start_point[1])
            e_pos = Util.point2index(code, id.end_point[0], id.end_point[1])
            assert s_pos is not None and e_pos is not None
            if str(id) in old_names:
                code = code[:s_pos] + old_new_dic[str(id)] + code[e_pos:]
                return code
        return code

    @staticmethod
    def replace_variable_name(old_new_dic, code) -> str:
        last_code = None
        while last_code != code:
            last_code = code
            code = Advisor._replace_variable_name(old_new_dic, code)
        return code

    def _rename_var(self, code: str, response: Optional[str] = None) -> Tuple[str, str]:
        prompt = get_prompt('rename_var', 'advisor')
        assert prompt
        if not response:
            q = QueryChatGPT()
            q.insert_system_prompt('You provide the programming suggestions.')
            response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        if "':" in response:
            response = response.replace("'", '"')
        if not is_valid_json(response):
            logger.warning(f"Fail to rename variables since the response is not valid JSON: {response}")
            return (code, response)
        old_new_dic = json.loads(response)
        try:
            code = self.replace_variable_name(old_new_dic, code)
        except Exception as e:
            logger.warning(e)
            return (code, response)
        return (code, response)

    def _add_comment(self, code: str) -> Tuple[str, str]:
        prompt = get_prompt('add_comment', 'advisor')
        assert prompt
        q = QueryChatGPT()
        q.insert_system_prompt('You provide the programming suggestions.')
        response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        response = response_filter(response)
        if not is_code_in_response(code, response):
            response = f"\\*{response}*\\ \n \n{code}"
        return (response, response)

    def _simplify(self, code: str) -> Tuple[str, str]:
        prompt = get_prompt('remove_unnecessary', 'advisor')
        assert prompt
        q = QueryChatGPT()
        q.insert_system_prompt('You provide the programming suggestions.')
        response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        response = response_filter(response)
        return (response, response)

    def _struct_rec(self, code: str) -> Tuple[str, str]:
        prompt = get_prompt('reconstruct_struct', 'advisor')
        assert prompt
        q = QueryChatGPT()
        q.insert_system_prompt('You provide the programming suggestions.')
        response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        response = response_filter(response)
        return (response, response)

    def _cf_simplify(self, code: str) -> Tuple[str, str]:
        prompt = get_prompt('cf_simplify', 'advisor')
        assert prompt
        q = QueryChatGPT()
        q.insert_system_prompt('You provide the programming suggestions.')
        response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        response = response_filter(response)
        return (response, response)

    def _lib_rec(self, code: str, response: Optional[str] = None) -> Tuple[str, str]:
        prompt = get_prompt('reconstruct_lib', 'advisor')
        assert prompt
        if not response:
            q = QueryChatGPT()
            q.insert_system_prompt('You provide the programming suggestions.')
            response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        if "':" in response:
            response = response.replace("'", '"')
        if not is_valid_json(response):
            logger.warning(f"Fail to rename variables since the response is not valid JSON: {response}")
            return (code, response)
        old_new_dic = json.loads(response)
        try:
            code = self.replace_variable_name(old_new_dic, code)
        except Exception as e:
            logger.warning(e)
            return (code, response)
        return (code, response)


class Operator(Role):
    def __init__(self):
        pass

    def operate(self, original_code: str, advised_code: str, dtype: DType) -> str:
        if dtype == DType.ADD_COMMENT:
            return advised_code
        elif dtype == DType.RENAME_VAR:
            return advised_code
        elif dtype == DType.SIMPLIFY:
            return advised_code
        elif dtype == DType.STRUCT_REC:
            return advised_code
        elif dtype == DType.CF_SIMPLIFY:
            return advised_code
        elif dtype == DType.LIB_REC:
            return advised_code
        else:
            logger.warning(f"The operator on {dtype} is not implemented, skip this change")
        return original_code


class Referee(Role):
    def __init__(self):
        pass

    def get_direction(self, code: str) -> Tuple[str, List[DType]]:
        prompt = get_prompt('need', 'referee')
        assert prompt
        q = QueryChatGPT()
        q.insert_system_prompt('You provide the programming suggestions')
        response = q.query(prompt['content'].format(code=code))
        assert isinstance(response, str)
        directions = self._parse_need(response)
        return (response, directions)

    def _parse_need(self, response: str) -> List[DType]:
        rtn = []
        pattern = r'\b(?:Yes|yes|No|no)\b'
        matches = re.findall(pattern, response)
        assert len(matches) == 6
        if matches[0] in ['Yes', 'yes']:
            rtn.append(DType.SIMPLIFY)
        if matches[1] in ['Yes', 'yes']:
            rtn.append(DType.ADD_COMMENT)
        if matches[2] in ['Yes', 'yes']:
            rtn.append(DType.RENAME_VAR)
        if matches[3] in ['Yes', 'yes']:
            rtn.append(DType.STRUCT_REC)
        if matches[4] in ['Yes', 'yes']:
            rtn.append(DType.CF_SIMPLIFY)
        return rtn


def single_opt(decompile_code: str, opt_type: DType) -> dict:
    dic = {'decompiler_output': decompile_code}
    advisor = Advisor()
    advisor_code, response = advisor.get_advice(decompile_code, opt_type)
    operator = Operator()
    operator_code = operator.operate(decompile_code, advisor_code, opt_type)
    dic['output'] = operator_code
    return dic


class RoleModel:
    def __init__(self, *, decompile_code: Optional[str] = None, src_code: Optional[str] = None):
        self.code = decompile_code
        self.src_code = src_code
        self.advisor = Advisor()
        self.operator = Operator()
        self.referee = Referee()

    def sort_directions(self, direction_lst: List[DType]) -> List[str]:
        sort_index = {
            DType.SIMPLIFY: 0,
            DType.ADD_COMMENT: 0.5,
            DType.RENAME_VAR: 1,
            DType.STRUCT_REC: 2,
            DType.CF_SIMPLIFY: 0.1,
            DType.LIB_REC: 3,
        }
        sorted_directions: List[DType] = []
        directions = set(direction_lst)
        for _d in directions:
            if _d is None or sort_index.get(_d, -1) == -1:
                continue
            if not sorted_directions:
                sorted_directions.append(_d)
                continue
            inserted = False
            for _i, _sd in enumerate(sorted_directions):
                if sort_index[_d] < sort_index[_sd]:
                    sorted_directions.insert(_i, _d)
                    inserted = True
                    break
            if not inserted:
                sorted_directions.append(_d)
        # return enum values as strings for downstream string comparisons
        return [d.value for d in sorted_directions]

    @staticmethod
    def sub_wf(wf1: str, wf2: str) -> int:
        dic = {
            'INIT': 0,
            'REFEREE': 1,
            'OPT:SIMPLIFY': 2,
            'DONE': 3,
        }
        return dic[wf1] - dic[wf2]

    @staticmethod
    def restore_to(workflow: str, existing_json: str, output: Optional[str] = None):
        assert workflow in ['INIT', 'REFEREE', 'OPT:SIMPLIFY', 'DONE']
        r = open(existing_json, 'r')
        res = json.load(r)
        r.close()
        cur_workflow = res['workflow']
        if RoleModel.sub_wf(workflow, cur_workflow) >= 0:
            print(f"Skip {existing_json} (workflow: {cur_workflow})")
            return
        if RoleModel.sub_wf(workflow, 'DONE') < 0:
            if 'SIMPLIFY' in res['optimization'].keys():
                res['optimization'] = {'SIMPLIFY': res['optimization']['SIMPLIFY']}
            else:
                res['optimization'] = dict()
        if RoleModel.sub_wf(workflow, 'OPT:SIMPLIFY') < 0:
            res['optimization'].clear()
        if RoleModel.sub_wf(workflow, 'REFEREE') < 0:
            for _ in ['optimization', 'sorted_directions', 'original_directions', 'original_directions_src']:
                res.pop(_)
        res['workflow'] = workflow
        out = output if output else existing_json
        with open(out, 'w') as w:
            print(f"Restore {existing_json} (workflow: {cur_workflow}) to {workflow} and dump to {out}")
            json.dump(res, w, indent=4)

    def work(self, end_at: str = 'DONE', existing_json: Optional[str] = None):
        if existing_json:
            res = None
            with open(existing_json, 'r') as r:
                res = json.load(r)
            if self.sub_wf(res['workflow'], end_at) >= 0:
                return res
        else:
            res = dict()
            res['source_code'] = self.src_code
            res['decompiler_output'] = self.code
            res['workflow'] = 'INIT'

        if self.sub_wf(end_at, 'INIT') <= 0:
            return res

        if self.sub_wf('REFEREE', res['workflow']) > 0:
            response, directions = self.referee.get_direction(res['decompiler_output'])
            res['original_directions_src'] = response
            res['original_directions'] = directions
            directions_sorted = self.sort_directions(directions)
            res['sorted_directions'] = directions_sorted
            res['optimization'] = dict()
            res['workflow'] = 'REFEREE'

        if self.sub_wf(end_at, res['workflow']) == 0:
            return res

        if 'SIMPLIFY' not in res['sorted_directions'] and self.sub_wf('OPT:SIMPLIFY', res['workflow']) > 0:
            res['workflow'] = 'OPT:SIMPLIFY'

        if self.sub_wf(end_at, res['workflow']) == 0:
            return res

        for _direction in res['sorted_directions']:
            if _direction == 'SIMPLIFY' and self.sub_wf('OPT:SIMPLIFY', res['workflow']) <= 0:
                continue

            optimization = dict()
            res['optimization'][_direction] = optimization

            dindex = res['sorted_directions'].index(_direction)
            if dindex == 0:
                optimization['input'] = res['decompiler_output']
            else:
                found = False
                i = dindex - 1
                while i >= 0:
                    dir_key = res['sorted_directions'][i]
                    if 'output' in res['optimization'].get(dir_key, {}):
                        optimization['input'] = res['optimization'][dir_key]['output']
                        found = True
                        break
                    i -= 1
                if not found:
                    optimization['input'] = res['decompiler_output']

            adviced_code, response = self.advisor.get_advice(optimization['input'], DType(_direction))
            optimization['advisor'] = adviced_code
            optimization['advisor_response'] = response
            if adviced_code == optimization['input']:
                optimization['status'] = 'FAIL|ADVISOR'
                if _direction == 'SIMPLIFY' and self.sub_wf('OPT:SIMPLIFY', res['workflow']) > 0:
                    res['workflow'] = 'OPT:SIMPLIFY'
                if self.sub_wf(end_at, 'OPT:SIMPLIFY') == 0:
                    return res
                continue

            optimization['operator'] = self.operator.operate(optimization['input'], adviced_code, DType(_direction))

            if optimization['operator'] == optimization['input']:
                optimization['status'] = 'FAIL|OPERATOR'
                optimization['output'] = optimization['input']
            else:
                optimization['status'] = 'SUCC'
                optimization['output'] = optimization['operator']

            if _direction == 'SIMPLIFY' and self.sub_wf('OPT:SIMPLIFY', res['workflow']) > 0:
                res['workflow'] = 'OPT:SIMPLIFY'
            if self.sub_wf(end_at, 'OPT:SIMPLIFY') == 0:
                return res

        res['workflow'] = 'DONE'
        res['output'] = get_optimized_from_dic(res)
        return res


def replay_advisor_rename(dic_path):
    dic = None
    with open(dic_path, 'r') as r:
        dic = json.load(r)
    rename_input = dic['optimization']['RENAME_VAR']['input']
    rename_response = dic['optimization']['RENAME_VAR']['advisor_response']
    advisor = Advisor()
    advisor._rename_var(rename_input, rename_response)


def restore_dir(dir_path: str, workflow: str):
    for case in os.listdir(dir_path):
        case = os.path.join(dir_path, case)
        RoleModel.restore_to(workflow, case)


def resume_from_dic(dir_path: str, workflow: str):
    for case in os.listdir(dir_path):
        case = os.path.join(dir_path, case)
        model = RoleModel()
        dic = model.work(workflow, case)
        with open(case, 'w') as w:
            json.dump(dic, w, indent=4)


def get_optimized_from_dic(dic) -> str:
    opts = dic['optimization']
    opt_order = ['SIMPLIFY', 'CF_SIMPLIFY', 'ADD_COMMENT', 'RENAME_VAR', 'STRUCT_REC', 'LIB_REC']
    out = dic['decompiler_output']
    for _ in opt_order:
        if _ not in opts or opts[_]['status'].startswith('FAIL'):
            return out
        else:
            out = opts[_]['output']
    return out


def opt_str2dtype(opt_type: str) -> DType:
    mapping = {
        'rename': DType.RENAME_VAR,
        'simplify': DType.SIMPLIFY,
        'comment': DType.ADD_COMMENT,
        'all': DType.ALL,
    }
    return mapping[opt_type]



def _node_slice(code: str, node) -> Tuple[int, int, str]:
    s_pos = getattr(node, "start_byte", None)
    e_pos = getattr(node, "end_byte", None)
    if isinstance(s_pos, int) and isinstance(e_pos, int) and 0 <= s_pos <= e_pos <= len(code):
        return s_pos, e_pos, code[s_pos:e_pos]

    try:
        sp = getattr(node, "start_point", None)
        ep = getattr(node, "end_point", None)
        if sp is not None and ep is not None:
            s_idx = Util.point2index(code, sp[0], sp[1])
            e_idx = Util.point2index(code, ep[0], ep[1])
            if s_idx is not None and e_idx is not None and 0 <= s_idx <= e_idx <= len(code):
                return s_idx, e_idx, code[s_idx:e_idx]
    except Exception:
        pass

    t = getattr(node, "src", None)
    if not t:
        t = str(node) if node is not None else ""
    if t:
        idx = code.find(t)
        if idx != -1:
            return idx, idx + len(t), t

    raise ValueError("cannot map node to source")


def _guess_func_name(func_text: str) -> str:
    try:
        head = func_text.split('{', 1)[0]
    except Exception:
        head = func_text
    pre = head.split('(', 1)[0]
    ids = re.findall(r'[A-Za-z_]\w*', pre)
    return ids[-1] if ids else 'ANON_FUNC'


def split_functions_with_spacers(code: str) -> List[Dict]:
    cc = CCode(code)
    fns = cc.get_by_type_name('function_definition')
    spans = []
    for fn in fns:
        try:
            s, e, t = _node_slice(code, fn)
        except Exception as exc:
            logger.warning(f"Failed to slice a function node: {exc}")
            # best-effort: try node.src presence
            t = getattr(fn, "src", None)
            if not t:
                # skip un-mappable node
                continue
            idx = code.find(t)
            if idx == -1:
                continue
            s, e = idx, idx + len(t)
        name = _guess_func_name(t)
        spans.append((s, e, t, name))
    spans.sort(key=lambda x: x[0])

    pieces = []
    cur = 0
    for s, e, t, name in spans:
        if s > cur:
            pieces.append({"type": "text", "text": code[cur:s]})
        pieces.append({"type": "func", "name": name, "text": t, "start": s, "end": e})
        cur = e
    if cur < len(code):
        pieces.append({"type": "text", "text": code[cur:]})
    return pieces


def rebuild_code_from_pieces(pieces: List[Dict]) -> str:
    out = []
    for p in pieces:
        if p["type"] == "func":
            out.append(p.get("out_text", p["text"]))
        else:
            out.append(p["text"])
    return "".join(out)


def multi_run(decompile_code: str, output: str, opt_type: str) -> str:
    pieces = split_functions_with_spacers(decompile_code)
    per_func_results = []
    optimized_any = False

    for idx, p in enumerate(pieces):
        if p["type"] != "func":
            continue
        fn_src = p["text"]
        fn_name = p["name"]

        try:
            if opt_type != 'all':
                dic = single_opt(fn_src, opt_str2dtype(opt_type))
                out_fn = dic['output']
            else:
                model = RoleModel(decompile_code=fn_src)
                dic = model.work()
                out_fn = dic['output']
        except Exception as e:
            logger.warning(f"[multi_run] {fn_name}: {e}")
            traceback.print_exc()
            dic = {"workflow": "INIT", "decompiler_output": fn_src, "output": fn_src, "error": str(e)}
            out_fn = fn_src

        pieces[idx]["out_text"] = out_fn
        optimized_any = optimized_any or (out_fn != fn_src)

        per_func_results.append({
            "index": idx,
            "name": fn_name,
            "start": p["start"],
            "end": p["end"],
            "result": dic,
        })

    merged_output = rebuild_code_from_pieces(pieces)

    summary_dic = {
        "workflow": "DONE" if optimized_any else "INIT",
        "source_code": None,
        "decompiler_output": decompile_code,
        "output": merged_output,
        "per_function": per_func_results,
    }

    output_json, output_opt_c = get_output_filenames(output)
    with open(os.path.join(OUTPUT_DIR, output_json), 'w') as w:
        json.dump(summary_dic, w, indent=4)
    with open(os.path.join(OUTPUT_DIR, output_opt_c), 'w') as f:
        f.write(merged_output)

    return merged_output



def single_run(decompile_code: str, output: str, opt_type: str) -> None:
    is_multi = False
    try:
        cc = CCode(decompile_code)
        fns = cc.get_by_type_name('function_definition')
        is_multi = len(fns) > 1
    except Exception as e:
        logger.warning(f"Function detection failed, fallback to single-run: {e}")

    if is_multi:
        return multi_run(decompile_code, output, opt_type)

    assert opt_type in ['rename', 'simplify', 'comment', 'all']
    try:
        if opt_type != 'all':
            dic = single_opt(decompile_code, opt_str2dtype(opt_type))
        else:
            model = RoleModel(decompile_code=decompile_code)
            dic = model.work()
    except Exception as e:
        logger.warning(f"Fail to run due to {e}")
        print(traceback.format_exc())
        return

    output_json, output_opt_c = get_output_filenames(output)
    with open(os.path.join(OUTPUT_DIR, output_json), 'w') as w:
        json.dump(dic, w, indent=4)
    with open(os.path.join(OUTPUT_DIR, output_opt_c), 'w') as f:
        f.write(dic['output'])
    return dic['output']


def single_run_file(decompile_file: str, output: str, opt_type: str) -> None:
    def read_code(f: str) -> str:
        with open(f, 'r') as r:
            return r.read()
    single_run(read_code(decompile_file), output, opt_type)


def parse_arguments():
    parser = argparse.ArgumentParser(description='DeGPT: Optimizing Decompiler Output with LLM')
    parser.add_argument('-t', choices = ['rename', 'simplify', 'comment', 'all'], default='all', help='Assign the optimization type')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--string', nargs=2, metavar=('decompiler_str', 'output_name'), help='Optimize the decompiler_str and save to %s/'%OUTPUT_DIR)
    group.add_argument('-f', '--file', nargs=2, metavar=('decompiler_file', 'output_name'), help='Optimize the content of the file decompiler_file and save to %s/'%OUTPUT_DIR)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    check_dir(OUTPUT_DIR)
    args = parse_arguments()
    if args.string:
        single_run(args.string[0], args.string[1], args.t)
    elif args.file:
        single_run_file(args.file[0], args.file[1], args.t)
