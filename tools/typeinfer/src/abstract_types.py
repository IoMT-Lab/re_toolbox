from functools import total_ordering
from type_definitions import StructType


@total_ordering
class AbstractType:
    def __repr__(self): return self.__class__.__name__

    def __eq__(self, other): return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __hash__(self): return hash(repr(self))

    def __lt__(self, other): return repr(self) < repr(other)


class AbsUnknown(AbstractType):
    pass


class BaseAbstractType(AbstractType):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Base({self.name})"


class StructFieldType(AbstractType):
    def __init__(self, parent_struct: StructType, offset: int):
        self.parent_struct = parent_struct
        self.offset = offset

    def __repr__(self):
        return f"Field({self.parent_struct.name}, {hex(self.offset)})"

    def __eq__(self, other):
        return (isinstance(other, StructFieldType) and
                self.parent_struct.name == other.parent_struct.name and
                self.offset == other.offset)

    def __hash__(self):
        return hash(("StructField", self.parent_struct.name, self.offset))


ABS_UNKNOWN = AbsUnknown()