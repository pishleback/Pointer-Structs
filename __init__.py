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


class TypeContext():
    def __init__(self, structure):
        assert type(structure) == list

        type_ctx = self
        class TypePtr():
            def __str__(self):
                raise NotImplementedError()
            def validate_kinds(self, ptr_type_names):
                raise NotImplementedError()
            def validate_object(self, obj_ctx, ident, content):
                raise NotImplementedError()
            def get_refs(self, obj_ctx, content):
                raise NotImplementedError()
            def change_content(self, obj_ctx, ident, content, action):
                parse_assert("opp" in action, "change objects need an \"opp\" field")
                opp = action["opp"]
                if opp == "replace":
                    for key in action:
                        parse_assert(key in {"opp", "value"}, "invalid field \"{key}\"")
                    return action["value"]
                return None #None is a signal to the calling object to try applying type-specific changes

        class RefTypePtr(TypePtr):
            def __init__(self, struct):
                parse_assert(type(struct) == dict, "content type should be specified by a json object")
                assert struct["kind"] == "ptr"
                parse_assert("unique" in struct, "a content type with kind=ptr should contain unique=true or unique=false")
                self.unique = struct["unique"]
                parse_assert(type(self.unique) == bool, "unique field should be a bool")
                for key in struct:
                    parse_assert(key in {"kind", "unique", "type"}, f"invalid field \"{key}\" provided to content type")
                self.ptr_type = struct["type"]
                assert type(self.ptr_type) == str

            def __str__(self):
                return f"PtrType({self.ptr_type})"

            def validate_kinds(self, ptr_type_names):
                assert self.ptr_type in ptr_type_names

            def validate_object(self, obj_ctx, ident, content):
                parse_assert(type(content) == int, "a pointer to an object should be an int containing the id of the object")
                parse_assert(content in obj_ctx.objects, f"pointer to object with id \"{content}\" not found")
                target_object = obj_ctx.objects[content]
                parse_assert(self.ptr_type in target_object.get_type().super_names, f"pointer to object of type \"{self.ptr_type}\" contains id of object of non super type \"{obj_ctx.objects[content].typename}\"")
                if self.unique:
                    parse_assert(target_object.reftypestr() == REF_UNIQUE, "unique pointer must point to a unique with ref=unique")
                    assert ident == target_object.owner
                else:
                    parse_assert(target_object.reftypestr() == REF_SHARED, "shared pointer must point to an object with ref=shared")
                    assert ident in target_object.owners

            def get_refs(self, obj_ctx, content):
                assert type(content) == int
                yield content

            def change_content(self, obj_ctx, ident, content, action):
                changed_content = super().change_content(obj_ctx, ident, content, action)
                if changed_content is None:
                    parse_assert(False, f"unknown basic type action {action['opp']}")
                #self.validate_object(obj_ctx, ident, changed_content)
                return changed_content

        class BasicTypePtr(TypePtr):
            def __init__(self, struct):
                parse_assert(type(struct) == dict, "content type should be specified by a json object")
                assert struct["kind"] == "basic"
                for key in struct:
                    parse_assert(key in {"kind", "type"}, f"invalid field \"{key}\" provided to content type")
                self.builtin_type = struct["type"]
                assert self.builtin_type in BUILTIN_TYPES

            def __str__(self):
                return f"BasicType({self.builtin_type})"

            def validate_kinds(self, ptr_type_names):
                pass

            def validate_object(self, obj_ctx, ident, content):
                parse_assert(type(content) == BUILTIN_TYPES[self.builtin_type], f"basic type {self.builtin_type} content has the wrong type {type(content)}")
                
            def get_refs(self, obj_ctx, content):
                return; yield

            def change_content(self, obj_ctx, ident, content, action):
                changed_content = super().change_content(obj_ctx, ident, content, action)
                if changed_content is None:
                    parse_assert(False, f"unknown basic type action {action['opp']}")
                #self.validate_object(obj_ctx, ident, changed_content)
                return changed_content

        class ListTypePtr(TypePtr):
            def __init__(self, struct):
                parse_assert(type(struct) == dict, "content type should be specified by a json object")
                assert struct["kind"] == "list"
                for key in struct:
                    parse_assert(key in {"kind", "type"}, f"invalid field \"{key}\" provided to content type")
                self.listed_type = make_type_ptr(struct["type"])

            def __str__(self):
                return f"List({self.listed_type})"

            def validate_kinds(self, ptr_type_names):
                self.listed_type.validate_kinds(ptr_type_names)

            def validate_object(self, obj_ctx, ident, content):
                parse_assert(type(content) == list, "list content should be provided as a list")
                for item in content:
                    self.listed_type.validate_object(obj_ctx, ident, item)

            def get_refs(self, obj_ctx, content):
                for item in content:
                    yield from self.listed_type.get_refs(obj_ctx, item)

            def change_content(self, obj_ctx, ident, content, action):
                changed_content = super().change_content(obj_ctx, ident, content, action)
                if changed_content is None:
                    opp = action["opp"]
                    changed_content = list(content)
                    if opp == "append":
                        for key in action:
                            parse_assert(key in {"opp", "value"}, f"unknown field \"{key}\" in list append action")
                        changed_content.append(action["value"])
                    elif opp == "modify":
                        for key in action:
                            parse_assert(key in {"opp", "idx", "action"}, f"unknown field \"{key}\" in list modify action")
                        parse_assert(type(action["idx"]) == int, "list idx should be an int")
                        parse_assert(0 <= action["idx"] < len(changed_content), "list idx out of range")
                        changed_content[action["idx"]] = self.listed_type.change_content(obj_ctx, ident, changed_content[action["idx"]], action["action"])
                    elif opp == "remove":
                        for key in action:
                            parse_assert(key in {"opp", "idx"}, f"unknown field \"{key}\" in list modify action")
                        parse_assert(type(action["idx"]) == int, "list idx should be an int")
                        parse_assert(0 <= action["idx"] < len(changed_content), "list idx out of range")
                        del changed_content[action["idx"]]
                    else:
                        parse_assert(False, f"unknown list opperation \"{opp}\"")
                #self.validate_object(obj_ctx, ident, changed_content)
                return changed_content

        def make_type_ptr(struct):
            if struct["kind"] == "ptr":
                return RefTypePtr(struct)
            elif struct["kind"] == "basic":
                return BasicTypePtr(struct)
            elif struct["kind"] == "list":
                return ListTypePtr(struct)
            else:
                parse_assert(False, "unknown ptr type kind \"{struct['kind']}\"")
            

        class Type():
            def __init__(self, structure, super_types):
                assert type(structure) == dict
                for key in structure:
                    assert key in {"type", "super", "content"}
                self.name = structure["type"]
                self.keys = set([])
                self.content = {} #name -> TypePtr
                self.optional = {} #name -> bool
                structure["super"] = structure.get("super", [])
                parse_assert(type(structure["super"]) == list, "super types should be provided as a list")
                self._imm_super_types = [] #used to compute all the types we inherit from
                for super_type_name in structure["super"]:
                    parse_assert(type(super_type_name) == str, "super type names should be strings")
                    parse_assert(super_type_name in super_types, f"type of name \"{super_type_name}\" not found in definition of type \"{self.name}\"")
                    super_type = super_types[super_type_name]
                    self._imm_super_types.append(super_type)
                    for n in super_type.keys:
                        
                        parse_assert(not n in self.content, f"duplicate content key {n} not allowed in definition of type\"{self.name}\"")
                        self.content[n] = super_type.content[n]
                        self.optional[n] = super_type.optional[n]
                        self.keys.add(n)
                structure["content"] = structure.get("content", {})
                assert type(structure["content"]) == dict
                for n, t_struct in structure["content"].items():
                    parse_assert(not n in self.content, f"duplicate content key {n} not allowed in definition of type\"{self.name}\"")
                    assert "optional" in t_struct
                    self.optional[n] = t_struct["optional"]
                    del t_struct["optional"]
                    self.content[n] = make_type_ptr(t_struct)
                    self.keys.add(n)

                assert self.keys == self.content.keys() == self.optional.keys()

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

            def validate_object(self, obj_ctx, ident, content):
                for key in content.keys():
                    parse_assert(key in self.keys, f"content has an unknown key {key}")
                for key, opt in self.optional.items():
                    if not opt:
                        parse_assert(key in content, f"content is missing non-optional key {key}")
                for key in content.keys():
                    self.content[key].validate_object(obj_ctx, ident, content[key])
                

            

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
            @classmethod
            def reftypestr(cls):
                assert False
            
            def __init__(self, data):
                parse_assert(type(data) == dict, "objects shold be dicts")
                for key in data.keys():
                    parse_assert(key in {"type", "id", "ref", "content"}, f"invalid object key \"{key}\"")
                #validate type
                parse_assert(data["type"] in type_ctx.types, f"unknown type \"{data['type']}\"")
                self.typename = data["type"]
                
                #validate id
                parse_assert(type(data["id"]) == int, "object id should be an int")
                self.ident = data["id"]

##                self.ref = data["ref"]
##                assert type(self) == Object[self.ref]

                #validate content is done after all objects are created
                self.content = data["content"]

                self.refs = set()
                #gets filled by self.update_refs()
                #empty indicates that none of our actual references have referse references yet
                #self.refs can be seen as a record of which of self._get_refs() have referse references

            def to_json(self):
                return {"type" : self.typename,
                        "id" : self.ident,
                        "ref" : type(self).reftypestr(),
                        "content" : self.content}

            def get_type(self):
                return type_ctx.types[self.typename]

            def _get_refs(self):
                #yield a sequence of [unique : bool, target : int] of objects we point at
                refs = set([])
                t = self.get_type()
                for key in self.content.keys():
                    for r in t.content[key].get_refs(obj_ctx, self.content[key]):
                        refs.add(r)
                return refs

            def add_reverse_ref(self, ident):
                raise NotImplementedError()
            def remove_reverse_ref(self, ident):
                raise NotImplementedError()

            def update_refs(self):
                #update self.refs and all reverse references of objects we point to
                now_refs = self._get_refs()

                #add new reverse references
                add_refs = set(now_refs)
                for r in self.refs:
                    if r in add_refs:
                        add_refs.remove(r)

                for r in add_refs:
                    obj_ctx.objects[r].add_reverse_ref(self.ident)

                #remove old reverse references 
                rem_refs = set(self.refs)
                for r in now_refs:
                    if r in rem_refs:
                        rem_refs.remove(r)

                for r in rem_refs:
                    obj_ctx.objects[r].remove_reverse_ref(self.ident)

                self.refs = now_refs

            def validate(self):
                #move validate_object code into here
                self.get_type().validate_object(obj_ctx, self.ident, self.content)
                    
                    
        self.Object = Object

        class RootObject(Object):
            @classmethod
            def reftypestr(cls):
                return "root"
                
            def __init__(self, data):
                super().__init__(data)

            def add_reverse_ref(self, ident):
                parse_assert(False, "The root object cannot be referenced")
            def remove_reverse_ref(self, ident):
                assert False
                
            def validate(self):
                super().validate()


        class UniqueObject(Object):
            @classmethod
            def reftypestr(cls):
                return "unique"
                
            def __init__(self, data):
                super().__init__(data)
                self.owner = None

            def add_reverse_ref(self, ident):
                parse_assert(self.owner is None, f"unique objects should have exactly one reference, but unique object {ident} has more than one")
                self.owner = ident
            def remove_reverse_ref(self, ident):
                assert self.owner == ident
                self.owner = None
                
            def validate(self):
                super().validate()
                assert not self.owner is None
                assert self.refs == self._get_refs()
                assert self.ident in obj_ctx.objects[self.owner].refs


        class SharedObject(Object):
            @classmethod
            def reftypestr(cls):
                return "shared"
                
            def __init__(self, data):
                super().__init__(data)
                self.owners = set([])

            def add_reverse_ref(self, ident):
                self.owners.add(ident)
            def remove_reverse_ref(self, ident):
                assert ident in self.owners
                self.owners.remove(ident)

            def validate(self):
                super().validate()
                assert self.refs == self._get_refs()
                for owner in self.owners:
                    assert self.ident in obj_ctx.objects[owner].refs
            

                    
        def make_object(data):
            parse_assert("ref" in data, "object json should contain a ref field")
            ref = data["ref"]
            for obj_t in [RootObject, UniqueObject, SharedObject]:
                if ref == obj_t.reftypestr():
                    return obj_t(data)
            parse_assert(False, "invalide ref value. Should be one of: \"root\", \"unique\", \"shared\".")
                    
        self.make_object = make_object

        self.root = None
        self.objects = {} #ident -> objects
        self.add_objects(objects)
        parse_assert(not self.root is None, "no root object present")
        assert type(self.root) == int
        assert self.root in self.objects

        self.validate()

    def add_objects(self, objects):
        #must be done with lists of objects so that circular references can occur within the provided objects
        
        #add objects
        new_idents = []
        for data in objects:
            obj = self.make_object(data)
            parse_assert(not obj.ident in self.objects, f"multiple objects with id {obj.ident} found")
            ident = obj.ident
            self.objects[ident] = obj
            if type(obj).reftypestr() == "root":
                parse_assert(self.root is None, "more than one root object present")
                self.root = ident
            new_idents.append(ident)

        #add reverse pointers
        for ident in new_idents:
            self.objects[ident].update_refs()

    def __str__(self):
        return json.dumps(self.to_json(), indent = 2)

    def to_json(self):
        return [obj.to_json() for obj in self.objects.values()]

    def validate(self):
        #validate contents
        for ident, obj in self.objects.items():
            assert type(ident) == int
            assert isinstance(obj, self.Object)
            assert obj.ident == ident
            obj.validate()

        #validate reference reachability (everything should be reachable from the root element)
        reachable_idents = set([self.root])
        boundary = set([self.root])
        while len(boundary) != 0:
            new_boundary = set()
            for b_ident in boundary:
                for a_ident in self.objects[b_ident].refs:
                    if not a_ident in reachable_idents:
                        reachable_idents.add(a_ident)
                        new_boundary.add(a_ident)
            boundary = new_boundary

        for ident in self.objects:
            parse_assert(ident in reachable_idents, f"object with id {ident} is not reachable from the root object")

    def get_content(self, ident):
        return self.objects[ident].content

        

    def apply_changes(self, changes):
        parse_assert(type(changes) == list, "changes should be a list of change blocks")
        for change_block in changes:
            parse_assert(type(change_block) == list, "change block should be a list of atomic change objects")
            for atomic_change in change_block:
                parse_assert("opp" in atomic_change, "a change object should have an \"opp\" field")
                opp = atomic_change["opp"]
                if opp == "add":
                    for key in atomic_change:
                        parse_assert(key in {"opp", "object"}, f"invalid {opp} opp field \"{key}\"")
                    self.add_objects([atomic_change["object"]])
                elif opp == "remove":
                    for key in atomic_change:
                        parse_assert(key in {"opp", "id"}, f"invalid {opp} opp field \"{key}\"")
                    ident = atomic_change["id"]
                    parse_assert(type(ident) == int, "object id should be an int")
                    parse_assert(ident in self.objects, "object with id {ident} does not exist")
                    obj = self.objects[ident]
                    del self.objects[ident]
                    obj.remove_reverse_refs()
                elif opp == "modify":
                    for key in atomic_change:
                        parse_assert(key in {"opp", "id", "field", "action"}, f"invalid {opp} opp field \"{key}\"")
                    ident = atomic_change["id"]
                    parse_assert(type(ident) == int, "object id should be an int")
                    parse_assert(ident in self.objects, "object with id {ident} does not exist")
                    obj = self.objects[ident]
                    key = atomic_change["field"]
                    parse_assert(key in obj.get_type().content.keys(), "object of type \"{obj.typename}\" has no field \"{key}\"")
                    #TODO: move change content into object class
                    obj.content[key] = obj.get_type().content[key].change_content(self, ident, obj.content[key], atomic_change["action"])
                    obj.update_refs()
                else:
                    parse_assert(False, f"invalid \"opp\" field")

            self.validate()



if __name__ == "__main__":
    with open("structure.json", "r") as f:
        structure = json.loads(f.read())
        type_ctx = TypeContext(structure)

    with open("objects.json", "r") as f:
        objects = json.loads(f.read())
        obj_ctx = ObjectContext(type_ctx, objects)
        print(obj_ctx)

    with open("changes.json", "r") as f:
        changes = json.loads(f.read())
        obj_ctx.apply_changes(changes)
        print(obj_ctx)
    










