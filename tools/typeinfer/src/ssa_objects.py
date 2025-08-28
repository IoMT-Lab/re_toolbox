from collections import defaultdict


class Variable:
    """Represents an SSA variable (e.g., v0, v1, v29)."""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    # ✅ --- Hashing and Equality for Variable ---
    def __eq__(self, other):
        if isinstance(other, Variable):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other):
        return self.name < other.name if isinstance(other, Variable) else NotImplemented


class Constant:
    """Represents an immediate constant (e.g., $0x8, 0x102008)."""
    def __init__(self, value_str):
        self.raw_value = value_str.strip()
        try:
            self.value = int(self.raw_value.replace('$', ''), 16)
        except ValueError:
            self.value = self.raw_value

    def __repr__(self):
        return self.raw_value

    def __eq__(self, other):
        if isinstance(other, Constant):
            return self.raw_value == other.raw_value
        return False

    def __hash__(self):
        return hash(self.raw_value)


class FunctionCall:
    """Represents a nested function call, e.g., MCA(0x101040)"""
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        args_str = ", ".join(map(str, self.args))
        return f"{self.name}({args_str})"

    def __eq__(self, other):
        if isinstance(other, FunctionCall):
            return self.name == other.name and self.args == other.args
        return False

    def __hash__(self):
        return hash((self.name, tuple(self.args)))


class Instruction:
    """Represents a complete SSA instruction."""
    def __init__(self, inst_id, address, operation, output=None, args=None):
        self.id = inst_id
        self.address = address
        self.operation = operation
        self.output = output
        self.args = args if args is not None else []

    def __repr__(self):
        out_str = f"{self.output} = " if self.output else ""
        args_str = ", ".join(map(str, self.args))
        if self.operation in ("Assign", "Phi"):
            op_str = args_str if self.operation == "Assign" else f"𝛟({args_str})"
        elif not self.args:
            op_str = f"{self.operation}()"
        else:
            op_str = f"{self.operation}({args_str})"
        return f"Inst(id={self.id}, addr={self.address}): {out_str}{op_str}"



class Condition:
    def __init__(self, var, is_true=True):
        self.var = var
        self.is_true = is_true

    def __repr__(self):
        return f"{self.var}" if self.is_true else f"!{self.var}"

    def __eq__(self, other):
        if isinstance(other, Condition):
            return self.var == other.var and self.is_true == other.is_true
        return False

    def __hash__(self):
        return hash((self.var, self.is_true))


class ConditionalEquivalenceSet:


    def __init__(self):
        self.equivalences = defaultdict(set)

    def add(self, var1, var2, path_condition):
        condition_frozenset = frozenset(path_condition)

        self.equivalences[var1].add((var2, condition_frozenset))
        self.equivalences[var2].add((var1, condition_frozenset))

    def get_equivalences_for(self, var):
        return self.equivalences.get(var, set())

    def pretty_print(self):
        if not self.equivalences:
            print("ConditionalEquivalenceSet is empty.")
            return

        def sort_key(item):
            var = item[0]
            if hasattr(var, 'name'):
                return var.name
            else:
                return str(var)

        print("--- Conditional Equivalence Set ---")
        for var, relations in sorted(self.equivalences.items(), key=sort_key):
            if not relations:
                continue

            relations_str_parts = []

            def inner_sort_key(relation_item):
                eq_var = relation_item[0]
                if hasattr(eq_var, 'name'):
                    return eq_var.name
                return str(eq_var)

            for eq_var, cond_set in sorted(relations, key=inner_sort_key):
                cond_str = "{" + ", ".join(map(str, sorted(list(cond_set), key=lambda c: c.var.name))) + "}"
                if cond_str == "{}":
                    cond_str = "{unconditional}"
                relations_str_parts.append(f"{eq_var} under {cond_str}")

            print(f"  {var}:")
            for part in relations_str_parts:
                print(f"    - equals {part}")
        print("-----------------------------------")

