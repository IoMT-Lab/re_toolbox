from functools import total_ordering
from loguru import logger


@total_ordering
class Type:
    def __repr__(self):
        return self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(repr(self))

    def __lt__(self, other):
        return repr(self) < repr(other)

    def join(self, other, visited=None):
        if visited is None: visited = set()
        if (id(self), id(other)) in visited: return self
        visited.add((id(self), id(other)))

        if self == other: return self
        if isinstance(self, UnknownType): return other
        if isinstance(other, UnknownType): return self

        return UnionType([self, other]).simplify(visited)

    def to_c_string(self, var_name="", defined_structs=None) -> str:
        if defined_structs is None:
            defined_structs = set()
        return f"void".strip()

class UnknownType(Type):
    def to_c_string(self, var_name="", defined_structs=None) -> str:
        return f"undefined".strip()


class VoidType(Type):
    def to_c_string(self, var_name="", defined_structs=None) -> str:
        return f"void".strip()


class BaseType(Type):
    def __init__(self, name): self.name = name

    def __repr__(self): return self.name



class BoolType(Type):
    def __repr__(self): return "Bool"


class IntType(Type):
    def __init__(self, bits=64): self.bits = bits

    def __repr__(self): return f"Int({self.bits})"


class FloatType(Type):
    def __init__(self, bits=64): self.bits = bits

    def __repr__(self): return f"Float({self.bits})"


class PointerType(Type):
    def __init__(self, points_to: 'Type'):
        self.points_to = points_to

    def __repr__(self):
        return f"Pointer({repr(self.points_to)})"

    def join(self, other, visited=None):
        if visited is None: visited = set()
        if (id(self), id(other)) in visited: return self
        visited.add((id(self), id(other)))

        if not isinstance(other, (PointerType, UnknownType, BaseType, UnionType)): return self
        if self == other: return self
        if isinstance(other, UnknownType): return self
        if isinstance(other, PointerType):
            return PointerType(self.points_to.join(other.points_to, visited))
        if isinstance(other, BaseType): return self

        return UnionType([self, other]).simplify(visited)

    def to_c_string(self, var_name="", defined_structs=None) -> str:
        if defined_structs is None:
            defined_structs = set()

        return str(self.points_to) + f"   * {var_name}"

class ArrayType(Type):
    def __init__(self, element_type: 'Type'):
        self.element_type = element_type
    def __repr__(self): return f"Array({self.element_type!r})"
    def __eq__(self, other): return isinstance(other, ArrayType) and self.element_type == other.element_type
    def __hash__(self): return hash(("Array", self.element_type))
    def join(self, other, visited=None):
        if visited is None: visited = set()
        if (id(self), id(other)) in visited: return self
        visited.add((id(self), id(other)))
        if isinstance(other, ArrayType):
            return ArrayType(self.element_type.join(other.element_type, visited))
        return super().join(other, visited)


class StructType(Type):
    def __init__(self, name, fields={}, array_member: ArrayType = None):
        self.name = name
        self.fields = frozenset(fields.items())
        self.array_member = array_member

    def __repr__(self):
        parts = []
        if self.fields:
            sorted_fields = sorted(list(self.fields), key=lambda item: item[0])
            fields_str = ", ".join([f"{hex(o)}: {t!r}" for o, t in sorted_fields])
            parts.append(f"fields={{ {fields_str} }}")
        if self.array_member:
            parts.append(f"array_member={self.array_member!r}")

        content = ", ".join(parts)
        return f"Struct({self.name} {{ {content} }})"

    def __eq__(self, other):
        return (isinstance(other, StructType) and
                self.name == other.name and
                self.fields == other.fields and
                self.array_member == other.array_member)

    def __hash__(self):
        return hash(("Struct", self.name, self.fields, self.array_member))

    def join(self, other, visited=None):
        if visited is None: visited = set()
        if (id(self), id(other)) in visited: return self
        visited.add((id(self), id(other)))

        if isinstance(other, PointerType): return other
        if not isinstance(other, (StructType, UnknownType, BaseType, UnionType)): return self
        if self == other: return self
        if isinstance(other, UnknownType): return self

        if isinstance(other, StructType) and self.name == other.name:
            new_fields = dict(self.fields)
            for offset, other_type in other.fields:
                if offset in new_fields:
                    new_fields[offset] = new_fields[offset].join(other_type, visited)
                else:
                    new_fields[offset] = other_type

            new_array_member = self.array_member
            if other.array_member:
                if new_array_member:
                    new_array_member = new_array_member.join(other.array_member, visited)
                else:
                    new_array_member = other.array_member

            return StructType(self.name, new_fields, new_array_member)

        return UnionType([self, other]).simplify(visited)

    def to_c_string(self, var_name="", defined_structs=set()) -> str:

        defined_structs.add(self.name)
        body = []
        if self.fields:
            for offset, field_type in sorted(list(self.fields)):
                field_decl = field_type.to_c_string(f"field_{hex(offset)}", defined_structs)
                body.append(f"  {field_decl};")
        if self.array_member:
            array_decl = self.array_member.to_c_string("flex_array_member", defined_structs)
            body.append(f"  {array_decl};")

        struct_def = f"struct {self.name} {{\n" + "\n".join(body) + "\n};"


        if var_name:
            return f"{struct_def}\nstruct {self.name} {var_name}".strip()
        else:
            return struct_def

class RecursiveType(Type):
    def __init__(self, name: str): self.name = name

    def __repr__(self): return self.name
    def to_c_string(self, var_name="", defined_structs=None) -> str:
        return f"{self.name}".strip()

class UnionType(Type):
    def __init__(self, types):
        flattened = set()
        for t in types:
            if isinstance(t, UnionType):
                flattened.update(t.types)
            elif not isinstance(t, UnknownType):
                flattened.add(t)
        self.types = frozenset(flattened)

    def __repr__(self):
        if not self.types: return "UnknownType"
        if len(self.types) == 1: return repr(next(iter(self.types)))
        return "Union{{" + ", ".join(map(repr, sorted(list(self.types)))) + "}}"

    def simplify(self, visited):
        if len(self.types) <= 1:
            return next(iter(self.types)) if self.types else UNKNOWN

        pointers = {t for t in self.types if isinstance(t, PointerType)}
        if pointers:
            final_type = UNKNOWN
            for p in pointers: final_type = final_type.join(p, visited)
            return final_type

        structs_and_arrays = {t for t in self.types if isinstance(t, (StructType, ArrayType))}
        if structs_and_arrays:
            final_type = UNKNOWN
            for s in structs_and_arrays: final_type = final_type.join(s, visited)
            return final_type

        return self

    def join(self, other, visited=None):
        if visited is None: visited = set()
        if (id(self), id(other)) in visited: return self
        visited.add((id(self), id(other)))
        combined = set(self.types)
        if isinstance(other, UnionType):
            combined.update(other.types)
        else:
            combined.add(other)
        return UnionType(combined).simplify(visited)

    def to_c_string(self, var_name="", defined_structs={}) -> str:
        if defined_structs is None:
            defined_structs = set()
        if not self.types:
            return f"void /* empty_union */ {var_name}".strip()

        body = []
        for i, t in enumerate(sorted(list(self.types))):
            member_decl = t.to_c_string(f"member_{i}", defined_structs)
            body.append(f"  {member_decl};")

        union_def = "union {\n" + "\n".join(body) + "\n}"
        return f"{union_def} {var_name}".strip()

UNKNOWN = UnknownType()
VOID = VoidType()