import json




# str, int, bool
# list(type)

class TypePtr():
    def __init__(self, struct):
        assert type(struct) == dict
        self.kind = struct["kind"]
        if self.kind == "ptr":
            assert "unique" in struct
            self.unique = struct["unique"]
            assert type(self.unique) == bool
            for key in struct:
                assert key in {"kind", "unique", "type"}
            self.ptr_type = struct["type"]
            assert type(self.ptr_type) == str
            #this is checked for validity in the context class via validate_kinds
        elif self.kind == "basic":
            for key in struct:
                assert key in {"kind", "type"}
            self.builtin_type = struct["type"]
            assert self.builtin_type in {"bool", "int", "str", "float"}
        elif self.kind == "list":
            for key in struct:
                assert key in {"kind", "type"}
            self.listed_type = TypePtr(struct["type"])
        else:
            assert False

    def __str__(self):
        if self.kind == "ptr":
            return f"PtrType({self.ptr_type})"
        elif self.kind == "basic":
            return f"BasicType({self.builtin_type})"
        elif self.kind == "list":
            return f"List({self.listed_type})"
        else:
            assert False

    def validate_kinds(self, ptr_type_names):
        if self.kind == "ptr":
            assert self.ptr_type in ptr_type_names
        elif self.kind == "basic":
            pass
        elif self.kind == "list":
            self.listed_type.validate_kinds(ptr_type_names)
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

    def validate_kinds(self, ptr_type_names):
        for t in self.content.values():
            t.validate_kinds(ptr_type_names)
            


class TypeContext():
    def __init__(self, structure):
        assert type(structure) == list

        self.types = {} #name -> Type
        for typedef in structure:
            name = typedef["type"]
            assert not name in self.types
            self.types[name] = Type(typedef, self.types)

        #check pointer types are valid
        for t in self.types.values():
            t.validate_kinds(set(self.types.keys()))

        for n, t in self.types.items():
            print(t)

    def __str__(self):
        return "TypeContext(" + ", ".join(self.types.keys()) + ")"




class ObjectContext():
    def __init__(self, type_ctx, objects):
        assert type(objects) == list
        for obj in objects:
            print(obj)
            assert type(obj) == dict
            for key in obj.keys():
                print(key)









with open("structure.json", "r") as f:
    structure = json.loads(f.read())
    type_ctx = TypeContext(structure)

with open("objects.json", "r") as f:
    objects = json.loads(f.read())
    obj_ctx = ObjectContext(type_ctx, objects)
    
    










