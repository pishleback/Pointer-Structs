import json




# str, int, bool
# list(type)
# name_of_defined_type




class TypePtr():
    def __init__(self, struct):
        assert type(struct) == dict
        self.ptr_type = struct["ptr_type"]
        if self.ptr_type == "defined":
            for key in struct:
                assert key in {"ptr_type", "type"}
            self.defined_type = struct["type"]
            assert type(self.defined_type) == str
            #this is checked for validity in the context class via validate_ptr_types
        elif self.ptr_type == "basic":
            for key in struct:
                assert key in {"ptr_type", "type"}
            self.builtin_type = struct["type"]
            assert self.builtin_type in {"bool", "int", "str", "float"}
        elif self.ptr_type == "list":
            for key in struct:
                assert key in {"ptr_type", "type"}
            self.listed_type = TypePtr(struct["type"])
        else:
            assert False

    def __str__(self):
        if self.ptr_type == "defined":
            return f"DefinedType({self.defined_type})"
        elif self.ptr_type == "basic":
            return f"BasicType({self.builtin_type})"
        elif self.ptr_type == "list":
            return f"List({self.listed_type})"
        else:
            assert False

    def validate_ptr_types(self, defined_type_names):
        if self.ptr_type == "defined":
            assert self.defined_type in defined_type_names
        elif self.ptr_type == "basic":
            pass
        elif self.ptr_type == "list":
            self.listed_type.validate_ptr_types(defined_type_names)
        else:
            assert False
        
        
    

class Type():
    def __init__(self, structure, super_types):
        assert type(structure) == dict
        for key in structure:
            assert key in {"type", "super", "content"}
        self.name = structure["type"]
        self.content = {} #name -> TypePtr
        structure["super"] = structure.get("super", [])
        assert type(structure["super"]) == list
        self._imm_super_types = [] #used to compute all the types we inherit from
        for super_type_name in structure["super"]:
            assert type(super_type_name) == str
            assert super_type_name in super_types
            super_type = super_types[super_type_name]
            self._imm_super_types.append(super_type)
            for n, t in super_type.content.items():
                assert not n in self.content
                self.content[n] = t
        structure["content"] = structure.get("content", {})
        assert type(structure["content"]) == dict
        for n, t_struct in structure["content"].items():
            assert not n in self.content
            self.content[n] = TypePtr(t_struct)

    #return all types which we inherit from
    @property
    def super_names(self):
        super_types = set()
        for imm_super_type in self._imm_super_types:
            super_types.add(imm_super_type.name)
            for super_type in imm_super_type.super_names:
                super_types.add(super_type)
        return super_types
    
    def __str__(self):
        return str(self.name) + "[" + ", ".join(str(st) for st in self.super_names) + "]" + "(" + ", ".join(n + ':' + str(t) for n, t in self.content.items()) + ")"

    def validate_ptr_types(self, defined_type_names):
        for t in self.content.values():
            t.validate_ptr_types(defined_type_names)


class Context():
    def __init__(self, structure):
        assert type(structure) == list

        self.types = {} #name -> Type
        for typedef in structure:
            name = typedef["type"]
            assert not name in self.types
            self.types[name] = Type(typedef, self.types)

        #check pointer types are valid
        for t in self.types.values():
            t.validate_ptr_types(set(self.types.keys()))

        for n, t in self.types.items():
            print(t)


    




with open("structure.json", "r") as f:
    structure = json.loads(f.read())
    ctx = Context(structure)












