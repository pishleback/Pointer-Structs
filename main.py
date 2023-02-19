import json




BUILTIN_TYPES = {"bool" : bool, "int" : int, "str" : str, "float" : float}

REF_ROOT = "root"
REF_UNIQUE = "unique"
REF_SHARED = "shared"


def parse_assert(cond, reason = None):
    if reason is None:
        reason = "no reason provided"
    if not cond:
        raise Exception(reason)


##class Ref():
##    def __init__(self, target, unique):
##        assert type(target) == int
##        assert type(unique) == bool
##        self.target = target
##        self.unique = unique
##
##    def __str__(self):
##        if self.unique:
##            return f"UniqueRef({self.target})"
##        else:
##            return f"SharedRef({self.target})"

class TypeContext():
    def __init__(self, structure):
        assert type(structure) == list

        type_ctx = self
        class TypePtr():
            def __init__(self, struct):
                parse_assert(type(struct) == dict, "content type should be specified by a json object")
                self.kind = struct["kind"]
                if self.kind == "ptr":
                    parse_assert("unique" in struct, "a content type with kind=ptr should contain unique=true or unique=false")
                    self.unique = struct["unique"]
                    parse_assert(type(self.unique) == bool, "unique field should be a bool")
                    for key in struct:
                        parse_assert(key in {"kind", "unique", "type"}, f"invalid field \"{key}\" provided to content type")
                    self.ptr_type = struct["type"]
                    assert type(self.ptr_type) == str
                    #this is checked for validity in the context class via validate_kinds
                elif self.kind == "basic":
                    for key in struct:
                        parse_assert(key in {"kind", "type"}, f"invalid field \"{key}\" provided to content type")
                    self.builtin_type = struct["type"]
                    assert self.builtin_type in BUILTIN_TYPES
                elif self.kind == "list":
                    for key in struct:
                        parse_assert(key in {"kind", "type"}, f"invalid field \"{key}\" provided to content type")
                    self.listed_type = TypePtr(struct["type"])
                else:
                    parse_assert(False, f"unknown content type kind={self.kind}")

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

            def validate_object(self, obj_ctx, content):
                if self.kind == "ptr":
                    parse_assert(type(content) == int, "a pointer to an object should be an int containing the id of the object")
                    parse_assert(content in obj_ctx.objects, f"pointer to object with id \"{content}\" not found")
                    parse_assert(self.ptr_type in obj_ctx.objects[content].get_type().super_names, f"pointer to object of type \"{self.ptr_type}\" contains id of object of non super type \"{obj_ctx.objects[content].typename}\"")
                    if self.unique:
                        parse_assert(obj_ctx.objects[content].ref == REF_UNIQUE, "unique pointer must point to a unique with ref=unique")
                    else:
                        parse_assert(obj_ctx.objects[content].ref == REF_SHARED, "shared pointer must point to an object with ref=shared")
                elif self.kind == "basic":
                    parse_assert(type(content) == (BUILTIN_TYPES[self.builtin_type]), "basic type content has the wrong type")
                elif self.kind == "list":
                    parse_assert(type(content) == list, "list content should be provided as a list")
                    for item in content:
                        self.listed_type.validate_object(obj_ctx, item)
                else:
                    assert False

            def get_refs(self, obj_ctx, content):
                self.validate_object(obj_ctx, content)
                if self.kind == "ptr":
                    assert type(content) == int
                    yield content
                elif self.kind == "basic":
                    pass
                elif self.kind == "list":
                    for item in content:
                        yield from self.listed_type.get_refs(obj_ctx, item)
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
                parse_assert(type(structure["super"]) == list, "super types should be provided as a list")
                self._imm_super_types = [] #used to compute all the types we inherit from
                for super_type_name in structure["super"]:
                    parse_assert(type(super_type_name) == str, "super type names should be strings")
                    parse_assert(super_type_name in super_types, f"type of name \"{super_type_name}\" not found in definition of type \"{self.name}\"")
                    super_type = super_types[super_type_name]
                    self._imm_super_types.append(super_type)
                    for n, t in super_type.content.items():
                        parse_assert(not n in self.content, f"duplicate content key {n} not allowed in definition of type\"{self.name}\"")
                        self.content[n] = t
                structure["content"] = structure.get("content", {})
                assert type(structure["content"]) == dict
                for n, t_struct in structure["content"].items():
                    parse_assert(not n in self.content, f"duplicate content key {n} not allowed in definition of type\"{self.name}\"")
                    self.content[n] = TypePtr(t_struct)

            #return all types which we inherit from
            @property
            def super_names(self):
                super_types = set([self.name])
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

            def validate_object(self, obj_ctx, content):
                parse_assert((keys := content.keys()) == self.content.keys(), "objects content keys dont match the keys an object of its type should be")
                for key in keys:
                    self.content[key].validate_object(obj_ctx, content[key])
                

            

        self.types = {} #name -> Type
        for typedef in structure:
            name = typedef["type"]
            parse_assert(not name in self.types, f"multiples definitions of type with name \"{name}\" is not allowed")
            self.types[name] = Type(typedef, self.types)

        #check pointer types are valid
        for t in self.types.values():
            t.validate_kinds(set(self.types.keys()))

##        for n, t in self.types.items():
##            print(t)

    def __str__(self):
        return "TypeContext(" + ", ".join(self.types.keys()) + ")"




class ObjectContext():
    def __init__(self, type_ctx, objects):
        assert type(objects) == list

        obj_ctx = self
        class Object():
            def __init__(self, data):
                parse_assert(type(data) == dict, "objects shold be dicts")
                for key in data.keys():
                    parse_assert(key in {"type", "id", "ref", "content"}, f"invalid object key \"{key}\"")
                #validate type
                parse_assert(data["type"] in type_ctx.types, "unknown type \"{data['type']}\"")
                self.typename = data["type"]
                
                #validate id
                parse_assert(type(data["id"]) == int, "object id should be an int")
                self.ident = data["id"]

                #validate ref
                parse_assert(data["ref"] in {REF_ROOT, REF_UNIQUE, REF_SHARED}, "object ref should be one of \"{REF_ROOT}\", \"{REF_UNIQUE}\", \"{REF_SHARED}\"")
                self.ref = data["ref"]

                #validate content is done after all objects are created
                self.content = data["content"]

            def get_type(self):
                return type_ctx.types[self.typename]

            @property
            def content_keys(self):
                assert self.content.keys() == self.get_type().content.keys()
                return set(self.content.keys())

            def get_refs(self):
                #yield a sequence of [unique : bool, target : int] of objects we point at
                t = self.get_type()
                for key in self.content_keys:
                    yield from t.content[key].get_refs(obj_ctx, self.content[key])
                    
        self.Object = Object

        self.root_ident = None
        self.objects = {} #ident -> objects
        for data in objects:
            obj = Object(data)
            parse_assert(not obj.ident in self.objects, f"multiple objects with id {obj.ident} found")
            self.objects[obj.ident] = obj
            if obj.ref == "root":
                parse_assert(self.root_ident is None, "more than one root object present")
                self.root_ident = obj.ident
        parse_assert(not self.root_ident is None, "no root object present")
        assert type(self.root_ident) == int
        assert self.root_ident in self.objects

        self.validate()

    def validate(self):
        #validate contents
        for ident, obj in self.objects.items():
            assert type(ident) == int
            assert type(obj) == self.Object
            assert obj.ident == ident
            obj.get_type().validate_object(self, obj.content)

        #validate reference counts
        # - should be a unique root with no references
        # - exactly one refernece from a unique ptr to unique objects
        # - arbitrarily many referneces from shared ptrs to shared objects
        ref_count = {ident : 0 for ident in self.objects}
        for ident, obj in self.objects.items():
            for ref in obj.get_refs():
                ref_count[ref] += 1

        for ident, count in ref_count.items():
            ref = self.objects[ident].ref
            if ref == REF_ROOT:
                assert count == 0 #should be impossible to be non-zero as unique pointers only point at unique objects and same for shared points and shared objects
            elif ref == REF_UNIQUE:
                parse_assert(count == 1, f"unique objects should have exactly one reference, but unique object {ident} has {count} references")
            elif ref == REF_SHARED:
                pass
            else:
                assert False

        #validate reference reachability (everything should be reachable from the root element)
        reachable_idents = set([self.root_ident])
        boundary = set([self.root_ident])
        while len(boundary) != 0:
            new_boundary = set()
            for b_ident in boundary:
                for a_ident in self.objects[b_ident].get_refs():
                    if not a_ident in reachable_idents:
                        reachable_idents.add(a_ident)
                        new_boundary.add(a_ident)
            boundary = new_boundary

        for ident in self.objects:
            parse_assert(ident in reachable_idents, f"object with id {ident} is not reachable from the root object")




with open("structure.json", "r") as f:
    structure = json.loads(f.read())
    type_ctx = TypeContext(structure)

with open("objects.json", "r") as f:
    objects = json.loads(f.read())
    obj_ctx = ObjectContext(type_ctx, objects)
    
    










