# Code Parser part of the ComCat pipeline.
# Calling get_blocks gets all the code blocks in a file to be commented.

import clang.cindex
import re
import subprocess
import tempfile
import os
from clang.cindex import CursorKind as K

# Global collection of blocks
blocks = []


def run_linter(cpp_code):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write(cpp_code)
        temp_file.flush()
        process = subprocess.Popen(
            ['clang-format', temp_file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
    os.unlink(temp_file.name)
    return stdout.strip() if process.returncode == 0 else stderr.strip()


# -------------------------
# Source extraction helpers
# -------------------------
def extent_to_source(source_file, start_line_1based, end_line_1based):
    with open(source_file) as f:
        lines = f.readlines()
    return ''.join(lines[start_line_1based - 1:end_line_1based])


def block2str(cursor, source_file):
    ext = cursor.extent
    return extent_to_source(source_file, ext.start.line, ext.end.line)


def _children_in_order(cursor, file_name):
    kids = [
        c for c in cursor.get_children()
        if c.location.file is None or c.location.file.name == file_name
    ]
    kids.sort(key=lambda c: (c.extent.start.line, c.extent.start.column))
    return kids


# -------------------------
# Variable declaration grouping
# -------------------------
def is_decl_only(node):
    """True if node is a single or list of var declarations (no other statements)."""
    if node.kind == K.VAR_DECL:
        return True
    if node.kind == K.DECL_STMT:
        kids = list(node.get_children())
        return kids and all(ch.kind == K.VAR_DECL for ch in kids)
    return False


def first_decl_type(node):
    if node.kind == K.VAR_DECL:
        return node.type.spelling
    if node.kind == K.DECL_STMT:
        for ch in node.get_children():
            if ch.kind == K.VAR_DECL:
                return ch.type.spelling
    return None


def _emit_grouped_var_decls(children, file_name, require_same_type=True, max_line_gap=0):
    """
    Scan 'children' (sibling nodes in one scope) for runs of consecutive declaration-only
    nodes and emit one (template_id=1) block per run. Returns a set of indices consumed.
    """
    consumed = set()
    i, n = 0, len(children)
    while i < n:
        if not is_decl_only(children[i]):
            i += 1
            continue

        run_start = i
        last = i
        base_type = first_decl_type(children[i])

        j = i + 1
        while j < n and is_decl_only(children[j]):
            prev, nxt = children[last], children[j]
            # Stop if there's a line gap beyond allowed tolerance (whitespace/comments ok if within gap)
            if nxt.extent.start.line > prev.extent.end.line + max_line_gap + 1:
                break
            if require_same_type and first_decl_type(nxt) != base_type:
                break
            last = j
            j += 1

        # Group [run_start, last] into one snippet
        start_line = children[run_start].extent.start.line
        end_line = children[last].extent.end.line
        snippet = extent_to_source(file_name, start_line, end_line)
        blocks.append((1, snippet))
        consumed.update(range(run_start, last + 1))
        i = last + 1

    return consumed


# -------------------------
# Complexity-aware control-block selection
# -------------------------
CONTROL_KINDS = {
    K.IF_STMT, K.SWITCH_STMT,
    K.FOR_STMT, K.WHILE_STMT, K.DO_STMT, K.CXX_FOR_RANGE_STMT,
    K.CXX_TRY_STMT
}
TERNARY_KIND = getattr(K, 'CONDITIONAL_OPERATOR', None)

# Tuning knobs
LINES_COMPLEX_THRESHOLD = 4        # lines in subtree to call it "complex"
BRANCH_COMPLEX_THRESHOLD = 1       # number of branch nodes (in descendants) to call complex
CALL_COMPLEX_THRESHOLD = 2         # number of call expressions (in descendants)
RESIDUAL_STMTS_THRESHOLD = 2       # shallow non-control statements to call parent non-trivial


def is_control_block(n):
    return n.kind in CONTROL_KINDS


def block_template_id(n):
    return 3 if n.kind in (K.IF_STMT, K.SWITCH_STMT) else 2  # if/switch vs loops/try


def count_subtree(node, file_name, exclude_root=True):
    """
    Return cheap metrics for complexity: (lines, branch_count, call_count).
    If exclude_root is True, counts are computed over DESCENDANTS only (not 'node' itself).
    """
    lines = node.extent.end.line - node.extent.start.line + 1

    # Seed stack with descendants (exclude the node itself) to avoid
    # labeling a lone 'if' as complex just for being a branch node.
    stack = []
    for ch in node.get_children():
        if ch.location.file is None or ch.location.file.name == file_name:
            stack.append(ch)

    branch = call = 0
    while stack:
        cur = stack.pop()
        if cur.location.file is not None and cur.location.file.name != file_name:
            continue
        k = cur.kind
        if k in (K.IF_STMT, K.SWITCH_STMT, K.CASE_STMT, K.DEFAULT_STMT):
            branch += 1
        elif TERNARY_KIND and k == TERNARY_KIND:
            branch += 1
        elif k == K.CALL_EXPR:
            call += 1
        for ch in cur.get_children():
            if ch.location.file is None or ch.location.file.name == file_name:
                stack.append(ch)
    return lines, branch, call


def is_complex(node, file_name):
    lines, branch_desc, call_desc = count_subtree(node, file_name, exclude_root=True)
    return (
        lines >= LINES_COMPLEX_THRESHOLD or
        branch_desc >= BRANCH_COMPLEX_THRESHOLD or
        call_desc >= CALL_COMPLEX_THRESHOLD
    )


def body_compound_nodes(ctrl, file_name):
    """Return COMPOUND_STMT bodies of a control block (then/else, loop body, try body)."""
    return [
        c for c in ctrl.get_children()
        if c.kind == K.COMPOUND_STMT and
           (c.location.file is None or c.location.file.name == file_name)
    ]


def shallow_body_children(compound_node, file_name):
    """Immediate statements inside { ... } of a compound body, in source order."""
    kids = [
        c for c in compound_node.get_children()
        if c.location.file is None or c.location.file.name == file_name
    ]
    kids.sort(key=lambda c: (c.extent.start.line, c.extent.start.column))
    return kids


def residual_stmt_count(ctrl, file_name):
    """
    Count immediate (shallow) non-control statements in all bodies of ctrl.
    If the body is a single statement without braces, approximate residual=1 when non-control.
    """
    total = 0
    compounds = body_compound_nodes(ctrl, file_name)

    if compounds:
        for comp in compounds:
            for ch in shallow_body_children(comp, file_name):
                if not is_control_block(ch):
                    total += 1
    else:
        # No braces: try to find a single-statement body among children.
        stmt_like = [
            c for c in ctrl.get_children()
            if (c.location.file is None or c.location.file.name == file_name)
        ]
        # If the single body is present and it's not a control, count it as residual.
        for c in stmt_like:
            if is_control_block(c):
                return 0
        total = 1  # conservative default
    return total


def direct_child_controls(ctrl, file_name):
    """Find control blocks that are directly inside the ctrl's bodies (not deeper)."""
    result = []
    for comp in body_compound_nodes(ctrl, file_name):
        for ch in shallow_body_children(comp, file_name):
            if is_control_block(ch):
                result.append(ch)
    return result


def group_vars_in_bodies(ctrl, file_name):
    """Group consecutive var decls inside each immediate { ... } body of ctrl."""
    for comp in body_compound_nodes(ctrl, file_name):
        kids = _children_in_order(comp, file_name)
        _emit_grouped_var_decls(
            kids, file_name,
            require_same_type=True,  # set False to allow mixed-type groups
            max_line_gap=0           # increase to allow blank/comment lines between
        )


def emit_control_block(ctrl, file_name, allow_self=True):
    """
    Decide whether to emit 'ctrl' and/or its immediate child control blocks.
    Also preserves var-decl grouping and continues recursion for non-control children,
    so other block types (e.g., type decls) are still discovered.
    """
    # Preserve var-decl grouping inside this control block's bodies
    group_vars_in_bodies(ctrl, file_name)

    # Complexity of this parent
    parent_complex = is_complex(ctrl, file_name)

    # Gather immediate child controls and classify by complexity
    child_ctrls = direct_child_controls(ctrl, file_name)
    complex_children = [c for c in child_ctrls if is_complex(c, file_name)]
    num_complex_children = len(complex_children)

    # Shallow residual complexity of the parent (outside child controls)
    residual = residual_stmt_count(ctrl, file_name)

    # Decide what to emit under the policy
    emit_parent = False
    emit_children = set()

    if not parent_complex:
        # Parent is simple → only emit complex children (if any)
        emit_parent = False
        emit_children.update(complex_children)
    else:
        if num_complex_children == 0:
            emit_parent = True
        elif num_complex_children >= 2:
            emit_parent = True
            emit_children.update(complex_children)
        else:  # exactly one complex child
            if residual < RESIDUAL_STMTS_THRESHOLD:
                # child dominates; parent explains it → emit parent only
                emit_parent = True
            else:
                # both have substance → emit both
                emit_parent = True
                emit_children.update(complex_children)

    # Emit parent (if allowed)
    if allow_self and emit_parent:
        blocks.append((block_template_id(ctrl), block2str(ctrl, file_name)))

    # Recurse into child controls:
    # - If a child is selected for emission, recurse with allow_self=True (so it can emit itself).
    # - If a child is NOT selected, recurse with allow_self=False so we can still discover
    #   its grandchildren without emitting the child itself.
    for ch in child_ctrls:
        emit_self_for_child = (ch in emit_children)
        emit_control_block(ch, file_name, allow_self=emit_self_for_child)

    # Also walk NON-control, shallow body children so that nested types/etc. are found.
    for comp in body_compound_nodes(ctrl, file_name):
        for ch in shallow_body_children(comp, file_name):
            if is_control_block(ch):
                continue
            # We already handled var-decl groups; skip DECL_STMT to avoid duplicates.
            if ch.kind == K.DECL_STMT:
                continue
            parse(ch, file_name)


# -------------------------
# Main AST traversal
# -------------------------
GROUPING_SCOPES = {
    K.TRANSLATION_UNIT,
    K.NAMESPACE,
    K.COMPOUND_STMT,  # function/loop bodies with braces
    K.DECL_STMT,      # inside blocks: 'int a=0;' or 'int a=0, b=1;'
}

def parse(cursor, file_name):
    # Skip nodes from other files
    if cursor.location.file is not None and cursor.location.file.name != file_name:
        return

    k = cursor.kind

    # Handle control blocks with the complexity-aware policy
    if is_control_block(cursor):
        emit_control_block(cursor, file_name, allow_self=True)
        return  # we've taken care of recursion for this subtree

    # At scope-like nodes, group consecutive variable declarations among children
    if k in GROUPING_SCOPES:
        children = _children_in_order(cursor, file_name)
        consumed = _emit_grouped_var_decls(
            children, file_name,
            require_same_type=False,  # set False to allow mixed types
            max_line_gap=2           # increase to allow blank/comment lines
        )
        # Visit remaining (non-consumed) children
        for idx, child in enumerate(children):
            if idx in consumed:
                continue
            parse(child, file_name)
        return

    # --- Selection logic for other block types (functions, types, etc.) ---
    if k in (K.FUNCTION_DECL, K.CXX_METHOD, K.CONSTRUCTOR, K.DESTRUCTOR, K.FUNCTION_TEMPLATE):
        blocks.append((0, block2str(cursor, file_name)))
    elif k in (K.STRUCT_DECL, K.UNION_DECL, K.CLASS_DECL, K.CLASS_TEMPLATE, K.ENUM_DECL, K.TYPEDEF_DECL):
        blocks.append((1, block2str(cursor, file_name)))

    # Default recursion
    for child in cursor.get_children():
        parse(child, file_name)


# -------------------------
# Public API
# -------------------------
def get_blocks(filename):
    blocks.clear()
    index = clang.cindex.Index.create()
    translation_unit = index.parse(filename)
    parse(translation_unit.cursor, translation_unit.spelling)
    return list(dict.fromkeys(blocks))  # dedupe while preserving order


def get_blocks_str(code):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp') as temp_file:
        temp_file.write(code)
        temp_file.flush()
        return get_blocks(temp_file.name)


def main():
    print(get_blocks("./test.cpp"))


if __name__ == '__main__':
    main()
