from type_definitions import *
from dense_graph import *

from ssa_objects import Constant
import time
from functools import wraps
from loguru import logger

import json
import os
import tempfile
from typing import Dict, Any, Callable

def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Starting '{func.__name__}'...")
        start_time = time.perf_counter()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        duration = end_time - start_time
        logger.success(f"Function '{func.__name__}' finished in {duration:.4f} seconds.")
        return result

    return wrapper

def get_signed_value(constant_or_int, bit_width=64):
    """
    Interprets a Constant object or an integer as a signed value
    using two's complement representation.

    :param constant_or_int: The Constant object or raw integer to interpret.
    :param bit_width: The bit width for the interpretation (e.g., 64, 32).
    :return: The signed integer value.
    :raises TypeError: if the input is not a Constant or an int.
    """
    if isinstance(constant_or_int, Constant):
        unsigned_val = constant_or_int.value
    elif isinstance(constant_or_int, int):
        unsigned_val = constant_or_int
    else:
        raise TypeError(f"Input must be a Constant or an int, not {type(constant_or_int)}")

    sign_bit_threshold = 1 << (bit_width - 1)

    if unsigned_val >= sign_bit_threshold:
        return unsigned_val - (1 << bit_width)
    else:
        # Otherwise, it's a positive number.
        return unsigned_val

def is_negative(constant_or_int, bit_width=64):
    """
    Checks if a Constant object or an integer represents a negative number.

    :param constant_or_int: The Constant object or raw integer to check.
    :param bit_width: The bit width for the interpretation.
    :return: True if the number is negative, False otherwise.
    """
    # A number is negative if its signed value is less than 0.
    return get_signed_value(constant_or_int, bit_width) < 0



def append_var_type_json(path: str, var_name: str, type_str: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    data: Dict[str, Any] = {"variables": {}}
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"wrong  JSON：{e}")

    if "variables" not in data or not isinstance(data["variables"], dict):
        data["variables"] = {}

    data["variables"][var_name] = type_str

    tmp_dir = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_vars_", dir=tmp_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass

type_cache = {}
def append_var_type_jsonl(path: str, var_name: str, type_obj_or_str: Any) -> None:

    global type_cache
    def type_to_c_string(type_obj: Type, var_name: str = "", cache=type_cache) -> str:
        if cache is None:
            cache = {}

        if id(type_obj) in cache and not var_name:
            return cache[id(type_obj)]

        base_type = ""
        if isinstance(type_obj, IntType):
            base_type = f"int{type_obj.bits}_t"
        elif isinstance(type_obj, FloatType):
            base_type = "double"
        elif isinstance(type_obj, BoolType):
            base_type = "bool"
        elif isinstance(type_obj, (UnknownType, BaseType)):
            base_type = "void"
        elif isinstance(type_obj, (RecursiveType, StructType)):
            base_type = f"{type_obj.to_c_string()}"
        elif isinstance(type_obj, PointerType):
            return type_to_c_string(type_obj.points_to, f"*{var_name}", cache)
        elif isinstance(type_obj, ArrayType):
            return type_to_c_string(type_obj.element_type, f"{var_name}[]", cache)
        elif isinstance(type_obj, UnionType):
            if type_obj.types:
                return type_to_c_string(list(type_obj.types)[0], var_name, cache)
            else:
                base_type = "void"
        else:
            base_type = "/* unknown_type */"

        result = f"{base_type} {var_name}".strip()

        if not var_name:
            cache[id(type_obj)] = result

        return result

    if isinstance(type_obj_or_str, str):
        type_decl = type_obj_or_str
    else:
        type_decl = type_to_c_string(type_obj_or_str, var_name)

    with open(path, "a+", encoding="utf-8") as f:
        json.dump({"var": var_name, "type": type_decl}, f, ensure_ascii=False)
        f.write("\n")
