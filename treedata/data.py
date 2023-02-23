import os
import random
import itertools
import fractions
from treedata import myxml


COLOURS = {"bad" : [196, 128, 128],
           "neutral" : [128, 128, 196],
           "good" : [128, 196, 128],
           "bg" : [32, 32, 32],
           "text" : [255, 255, 255]}


class Info():
    @staticmethod
    def LoadInfos(tag):
        assert tag.name == "infos"
        kinds = {"date" : Date, "subinfo" : SubInfo, "string" : String}
        for sub_tag in tag.sub_tags:
            assert sub_tag.name in kinds
        return [kinds[sub_tag.name].Load(sub_tag) for sub_tag in tag.sub_tags]
    
    @staticmethod
    def SaveInfos(infos):
        for info in infos:
            assert issubclass(type(info), Info)
        return myxml.Tag("infos", "", [info.save() for info in infos])

        
    def __init__(self):
        pass

    def to_json(self):
        return {"type" : "fundamental"}

    def to_obj_json(self, idt):
        return {"type" : "info",
                "id" : idt(self),
                "ref" : "unique",
                "content" : {}}




class String(Info):
    @staticmethod
    def Load(tag):
        assert tag.name == "string"
        assert len(tag.sub_tags) == 0
        return String(tag.string)
    
    def __init__(self, string):
        Info.__init__(self)
        assert type(string) == str
        self.string = string

    def save(self):
        return myxml.Tag("string", self.string, [])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "string"
        ans["string"] = self.string
        return ans

    def to_obj_json(self, idt):
        ans = super().to_obj_json(idt)
        ans["type"] = "string"
        ans["content"]["string"] = self.string
        return ans



class SubInfo(Info):
    @staticmethod
    def Load(tag):
        assert tag.name == "subinfo"
        return SubInfo(tag.get_sub_str("title"), Info.LoadInfos(tag.get_sub_tag("infos")))
    
    def __init__(self, title, infos):
        Info.__init__(self)
        for info in infos:
            assert issubclass(type(info), Info)
        assert type(title) == str
        self.title = title
        self.infos = infos

    def save(self):
        return myxml.Tag("subinfo", "", [myxml.Tag("title", self.title, []),
                                         Info.SaveInfos(self.infos)])

    def get_sub_infos(self, title):
        return [info for info in [info for info in self.infos if type(info) == SubInfo] if info.title == title]
    def get_info_dates(self):
        return [info for info in self.infos if type(info) == Date]
    def get_info_strings(self):
        return [info for info in self.infos if type(info) == String]

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "sub_info"
        ans["title"] = self.title
        ans["infos"] = [info.to_json() for info in self.infos]
        return ans

    def to_obj_json(self, idt):
        ans = super().to_obj_json(idt)
        ans["type"] = "subinfo"
        ans["content"]["title"] = self.title
        ans["content"]["infos"] = [idt(info) for info in self.infos]
        return ans



class Date(Info):
    @staticmethod
    def Load(tag):
        assert tag.name == "date"
        assert tag.string == ""
        return Date(tag.get_sub_str("day"),
                    tag.get_sub_str("month"),
                    tag.get_sub_str("year"),
                    tag.get_sub_strs("tag"))
    
    def __init__(self, day, month, year, tags):
        Info.__init__(self)
        for x in [day, month, year]:
            assert type(x) == str or x is None
        for tag in tags:
            assert type(tag) == str
        self.day = day
        self.month = month
        self.year = year
        self.tags = tags

    def get_date_string(self):
        tag_str = " ".join(self.tags)
        if self.day is None and self.month is None and not self.year is None:
            return (tag_str + " " + self.year).strip(" ")
        return (tag_str + " " + "-".join(["??" if self.day is None else self.day,
                                          "??" if self.month is None else self.month,
                                          "????" if self.year is None else self.year])).strip(" ")

    def save(self):
        sub_tags = []
        if not self.day is None:
            sub_tags.append(myxml.Tag("day", self.day, []))
        if not self.month is None:
            sub_tags.append(myxml.Tag("month", self.month, []))
        if not self.year is None:
            sub_tags.append(myxml.Tag("year", self.year, []))
        sub_tags.extend([myxml.Tag("tag", tag, []) for tag in self.tags])
        return myxml.Tag("date", "", sub_tags)

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "date"
        ans["day"] = self.day
        ans["month"] = self.month
        ans["year"] = self.year
        ans["tags"] = [tag for tag in self.tags]
        return ans

    def to_obj_json(self, idt):
        ans = super().to_obj_json(idt)
        ans["type"] = "date"
        if not self.day is None:
            ans["content"]["day"] = self.day
        if not self.month is None:
            ans["content"]["month"] = self.month
        if not self.year is None:
            ans["content"]["year"] = self.year
        ans["content"]["tags"] = self.tags
        return ans



class EntityPointer(Info):
    def __init__(self, to_entity):
        Info.__init__(self)
        assert issubclass(type(to_entity), Entity)
        self.from_entity = None
        self.to_entity = to_entity

    def replace_entity(self, old_entity, new_entity):
        assert (t := type(old_entity)) == type(new_entity)
        assert issubclass(t, Entity)
        if self.from_entity == old_entity:
            self.from_entity = new_entity
        if self.to_entity == old_entity:
            self.to_entity = new_entity
    
    def delete(self):
        raise NotImplementedError()

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "entity"
        ans["from_entity"] = self.from_entity.ident
        ans["to_entity"] = self.to_entity.ident
        return ans

    def to_obj_json(self, idt):
        raise Exception("EntityPointer should not be obj_json_ified")



class ParentPointer(EntityPointer):
    @staticmethod
    def Load(tag, entity_lookup):
        return ParentPointer(entity_lookup[int(tag.get_sub_str("id"))])
        
    def __init__(self, parent):
        assert issubclass(type(parent), Person)
        EntityPointer.__init__(self, parent)
        parent.parent_pointers.append(self)

    def delete(self):
        self.from_entity.parents.remove(self)
        self.to_entity.parent_pointers.remove(self)

    def save(self, ident_lookup):
        return myxml.Tag("parent", "", [myxml.Tag("id", ident_lookup[self.to_entity], [])])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "parent"
        return ans

    def to_obj_json(self, idt):
        ans = {}
        ans["type"] = "parent_ptr"
        ans["id"] = idt(self)
        ans["ref"] = "unique"
        ans["content"] = {}
        ans["content"]["target"] = idt(self.to_entity)
        return ans



class ChildPointer(EntityPointer):
    @staticmethod
    def Load(tag, entity_lookup):
        return ChildPointer(entity_lookup[int(tag.get_sub_str("id"))],
                            {"yes" : True, "no" : False}[tag.get_sub_str("adoption")])
    
    def __init__(self, child, adopted):
        EntityPointer.__init__(self, child)
        assert issubclass(type(child), Person)
        assert type(adopted) == bool
        self.adopted = adopted
        child.child_pointers.append(self)

    def delete(self):
        self.from_entity.children.remove(self)
        self.to_entity.child_pointers.remove(self)

    def save(self, ident_lookup):
        return myxml.Tag("child", "", [myxml.Tag("id", ident_lookup[self.to_entity], []),
                                       myxml.Tag("adoption", {True : "yes", False : "no"}[self.adopted], [])])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "child"
        ans["adopted"] = self.adopted
        return ans

    def to_obj_json(self, idt):
        ans = {}
        ans["type"] = "child_ptr"
        ans["id"] = idt(self)
        ans["ref"] = "unique"
        ans["content"] = {}
        ans["content"]["target"] = idt(self.to_entity)
        ans["content"]["adopted"] = self.adopted
        return ans

        

class ImageEntity(EntityPointer):
    class Rect():
        @staticmethod
        def Load(tag):
            assert tag.name == "rect"
            assert tag.string == ""
            return ImageEntity.Rect([float(tag.get_sub_str("x")),
                                     float(tag.get_sub_str("y")),
                                     float(tag.get_sub_str("w")),
                                     float(tag.get_sub_str("h"))])
        
        def __init__(self, rect):
            assert len(rect) == 4 and all([type(n) == float and 0 <= n <= 1 for n in rect]) and rect[0] + rect[2] <= 1 and rect[1] + rect[3] <= 1
            self.rect = rect

        def save(self):
            return myxml.Tag("rect", "", [myxml.Tag("x", repr(self.rect[0]), []),
                                          myxml.Tag("y", repr(self.rect[1]), []),
                                          myxml.Tag("w", repr(self.rect[2]), []),
                                          myxml.Tag("h", repr(self.rect[3]), [])])

        def to_json(self):
            assert len(self.rect) == 4
            for n in self.rect:
                assert type(n) == float
            return [n for n in self.rect]

        
                        
    

    @staticmethod
    def Load(tag, entity_lookup):
        assert tag.name == "image_entity"
        assert tag.string == ""

        def load_rect():
            rect_tags = tag.get_sub_tags("rect")
            if len(rect_tags) == 0:
                return ImageEntity.Rect([0.0, 0.0, 1.0, 1.0])
            elif len(rect_tags) == 1:
                return ImageEntity.Rect.Load(rect_tags[0])
            else:
                raise Exception()
        
        return ImageEntity(entity_lookup[int(tag.get_sub_str("id"))], load_rect(), {"yes" : True, "no" : False}[tag.get_sub_str("usable")])
        
    def __init__(self, entity, rect, usable):
        EntityPointer.__init__(self, entity)
        assert type(rect) == ImageEntity.Rect
        assert type(usable) == bool
        self.rect = rect
        self.usable = usable
        entity.image_pointers.append(self)
        self.surface = None


    def delete(self):
        self.from_entity.image_entities.remove(self)
        self.to_entity.image_pointers.remove(self)


    def save(self, ident_lookup):
        return myxml.Tag("image_entity", "", [myxml.Tag("id", ident_lookup[self.to_entity], []),
                                              myxml.Tag("usable", {True : "yes", False : "no"}[self.usable], []),
                                              self.rect.save()])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "image"
        ans["rect"] = self.rect.to_json()
        ans["usable"] = self.usable
        return ans

    def to_obj_json(self, idt):
        return {"type" : "subimage",
                "id" : idt(self),
                "ref" : "unique",
                "content" : {"entity" : idt(self.to_entity),
                             "x" : self.rect.rect[0],
                             "y" : self.rect.rect[1],
                             "w" : self.rect.rect[2],
                             "h" : self.rect.rect[3],
                             "usable" : self.usable}}
        


class Entity(): 
    def __init__(self, ident, infos):
        assert type(ident) == int
        self.ident = ident
        for info in infos:
            assert issubclass(type(info), Info)
        self.infos = infos #list of info objects
        self.image_pointers = []

    def get_sub_infos(self, title):
        return [info for info in [info for info in self.infos if type(info) == SubInfo] if info.title == title]
    def get_info_dates(self):
        return [info for info in self.infos if type(info) == Date]
    def get_info_strings(self):
        return [info for info in self.infos if type(info) == String]

    def delete(self):
        for pointer in self.image_pointers[:]:
            pointer.delete()

    def get_event_strings(self, event_names):
        def get_event_string(info):
            dates = info.get_info_dates()
            strings = [info.title[0] + "." + date.get_date_string() for date in dates]
            if len(dates) == 0:
                return [info.title[0] + "."]
            else:
                return strings
        return sum([get_event_string(info) for info in [info for info in self.infos if type(info) == SubInfo] if info.title in event_names], [])


    def get_colour(self):
        raise NotImplementedError()

    def to_json(self):
        ans = {}
        ans["type"] = "entity"
        ans["ident"] = self.ident
        ans["image_ptrs"] = [ptr.to_json() for ptr in self.image_pointers]
        ans["infos"] = [info.to_json() for info in self.infos]
        return ans

    def to_obj_json(self, idt):
        return {"type" : "entity",
                "id" : idt(self),
                "ref" : "shared",
                "content" : {"infos" : [idt(info) for info in self.infos]}}



class Person(Entity):
    @staticmethod
    def Load(tag):
        assert tag.name == "person"
        return Person(int(tag.get_sub_str("id")), Info.LoadInfos(tag.get_sub_tag("infos")))

    @staticmethod
    def merge(p1, p2):
        assert type(p1) == type(p2) == Person
        new_person = Person(p1.infos + p2.infos)
        new_person.parent_pointers = p1.parent_pointers + p2.parent_pointers
        new_person.child_pointers = p1.child_pointers + p2.child_pointers
        new_person.image_pointers = p1.image_pointers + p2.image_pointers
        for pointer in new_person.parent_pointers + new_person.child_pointers + new_person.image_pointers:
            pointer.to_entity = new_person
        return new_person

    
    def __init__(self, ident, infos):
        Entity.__init__(self, ident, infos)
        self.parent_pointers = [] #pointers of partnerships for which this person is a parent
        self.child_pointers = [] #pointers of partnerships for which this person is a child

    def __str__(self):
        return "Person(" + self.name() + ")"
    def name(self):
        return " ".join(itertools.chain(self.get_first_names(), ((n[0] if len(n) >= 1 else "") for n in self.get_last_names())))

    def delete(self):
        super().delete()
        for pointer in self.parent_pointers[:]:
            pointer.delete()
        for pointer in self.child_pointers[:]:
            pointer.delete()


    def get_parents(self):
        for pointer in self.child_pointers:
            part = pointer.from_entity
            for person_pointer in part.parents:
                yield person_pointer.to_entity

    def get_children(self):
        for pointer in self.parent_pointers:
            part = pointer.from_entity
            for person_pointer in part.children:
                yield person_pointer.to_entity

    def get_siblings(self):
        sibligs = set([])
        for parent in self.get_parents():
            for child in parent.get_children():
                sibligs.add(child)
        for pointer in self.child_pointers:
            part = pointer.from_entity
            for person_pointer in part.children:
                sibligs.add(person_pointer.to_entity)
        return sibligs

    def get_partners(self):
        for pointer in self.parent_pointers:
            part = pointer.from_entity
            for person_pointer in part.parents:
                yield person_pointer.to_entity

    def get_parent_parts(self):
        for pointer in self.parent_pointers:
            yield pointer.from_entity


    def get_child_parts(self):
        for pointer in self.child_pointers:
            yield pointer.from_entity


    def get_decedents(self, found = None):
        if found is None:
            found = set([])
        if not self in found:
            found |= set([self])
        for person in self.get_children():
            if not person in found:
                found |= person.get_decedents(found)
        return found

    def get_ancestors(self, found = None):
        if found is None:
            found = set([])
        if not self in found:
            found |= set([self])
        for person in self.get_parents():
            if not person in found:
                found |= person.get_ancestors(found)
        return found
        

    def get_name_infos(self):
        return sum([info.infos for info in self.get_sub_infos("name")], [])
    def get_first_names(self):
        return [info.string for info in sum([info.get_info_strings() for info in [info for info in self.get_name_infos() if type(info) == SubInfo] if info.title == "first"], []) if info.string != ""]
    def get_middle_names(self):
        return [info.string for info in sum([info.get_info_strings() for info in [info for info in self.get_name_infos() if type(info) == SubInfo] if info.title == "middle"], []) if info.string != ""]
    def get_last_names(self):
        return [info.string for info in sum([info.get_info_strings() for info in [info for info in self.get_name_infos() if type(info) == SubInfo] if info.title == "last"], []) if info.string != ""]
    def get_known_as_names(self):
        return [info.string for info in sum([info.get_info_strings() for info in [info for info in self.get_name_infos() if type(info) == SubInfo] if info.title == "known as"], []) if info.string != ""]

    def get_sex(self):
        sex_infos = self.get_sub_infos("sex")
        if len(sex_infos) != 1:
            return None
        else:
            sexes = [info.string for info in sex_infos[0].get_info_strings()]
            if len(sexes) != 1:
                return None
            else:
                return sexes[0]

    def get_colour(self):
        sex = self.get_sex()
        if sex is None:
            return [128, 128, 128]
        elif sex == "male":
            return [64, 160, 255]
        elif sex == "female":
            return [255, 64, 255]
        else:
            return [112, 64, 255]
            

    def save(self, ident_lookup):
        return myxml.Tag("person", "", [myxml.Tag("id", str(ident_lookup[self]), []),
                                        Info.SaveInfos(self.infos)])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "person"
        ans["parent_ptrs"] = [ptr.to_json() for ptr in self.parent_pointers]
        ans["child_ptrs"] = [ptr.to_json() for ptr in self.child_pointers]
        return ans

    def to_obj_json(self, idt):
        ans = super().to_obj_json(idt)
        ans["type"] = "person"
        return ans



class Partnership(Entity):
    @staticmethod
    def Load(tag, entity_lookup):
        assert tag.name == "partnership"
        return Partnership(int(tag.get_sub_str("id")),
                           Info.LoadInfos(tag.get_sub_tag("infos")),
                           [ParentPointer.Load(sub_tag, entity_lookup) for sub_tag in tag.get_sub_tag("parents").get_sub_tags("parent")],
                           [ChildPointer.Load(sub_tag, entity_lookup) for sub_tag in tag.get_sub_tag("children").get_sub_tags("child")])

    @staticmethod
    def merge(p1, p2):
        assert type(p1) == type(p2) == Partnership
        new_part = Partnership(p1.infos + p2.infos, p1.parents + p2.parents, p1.children + p2.children)
        new_part.image_pointers = p1.image_pointers + p2.image_pointers
        for pointer in new_part.image_pointers:
            pointer.to_entity = new_part
        return new_part
    
    def __init__(self, ident, infos, parents, children):
        Entity.__init__(self, ident, infos)
        for parent in parents:
            assert issubclass(type(parent), ParentPointer)
        for child in children:
            assert issubclass(type(child), ChildPointer)
        self.parents = parents
        self.children = children
        for parent_pointer in self.parents:
            parent_pointer.from_entity = self
        for child_pointer in self.children:
            child_pointer.from_entity = self

    def __str__(self):
        return "Partnership(" + ", ".join(parent.to_entity.name() for parent in self.parents) + " -> " + ", ".join(child.to_entity.name() for child in self.children) + ")"
    
    def get_colour(self):
        return [207, 137, 41]
        

    def delete(self):
        super().delete()
        for pointer in self.parents + self.children:
            pointer.delete()

    def get_married(self):
        return len([info for info in [info for info in self.infos if type(info) == SubInfo] if info.title == "marriage"]) >= 1
    def get_divorced(self):
        return len([info for info in [info for info in self.infos if type(info) == SubInfo] if info.title == "divorce"]) >= 1

    def is_child(self, person):
        assert issubclass(type(person), Person)
        return any([child_pointer.to_entity == person for child_pointer in self.children])

    def is_parent(self, person):
        assert issubclass(type(person), Person)
        return any([parent_pointer.to_entity == person for parent_pointer in self.parents])

    def add_child(self, person):
        assert not self.is_child(person)
        child_pointer = ChildPointer(person, False)
        child_pointer.from_entity = self
        self.children.append(child_pointer)

    def add_parent(self, person):
        assert not self.is_parent(person)
        parent_pointer = ParentPointer(person)
        parent_pointer.from_entity = self
        self.parents.append(parent_pointer)

    def remove_child(self, person):
        assert self.is_child(person)
        for child_pointer in self.children[:]:
            if child_pointer.to_entity == person:
                child_pointer.delete()

    def remove_parent(self, person):
        assert self.is_parent(person)
        for parent_pointer in self.parents[:]:
            if parent_pointer.to_entity == person:
                parent_pointer.delete()
                

    def save(self, ident_lookup):
        return myxml.Tag("partnership", "", [myxml.Tag("id", str(ident_lookup[self]), []),
                                             Info.SaveInfos(self.infos),
                                             myxml.Tag("parents", "", [parent.save(ident_lookup) for parent in self.parents if parent.to_entity in ident_lookup]),
                                             myxml.Tag("children", "", [child.save(ident_lookup) for child in self.children if child.to_entity in ident_lookup])])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "partnership"
        ans["parent_ptrs"] = [ptr.to_json() for ptr in self.parents]
        ans["child_ptrs"] = [ptr.to_json() for ptr in self.children]
        return ans


    def to_obj_json(self, idt):
        ans = super().to_obj_json(idt)
        ans["type"] = "partnership"
        ans["content"]["parents"] = [idt(ptr) for ptr in self.parents]
        ans["content"]["children"] = [idt(ptr) for ptr in self.children]
        return ans


class Image(Entity):
    @staticmethod
    def Load(tag, entity_lookup):
        assert tag.name == "image"
        return Image(int(tag.get_sub_str("id")), Info.LoadInfos(tag.get_sub_tag("infos")), tag.get_sub_str("file"), [ImageEntity.Load(sub_tag, entity_lookup) for sub_tag in tag.get_sub_tag("image_entities").get_sub_tags("image_entity")])
    
    def __init__(self, ident, infos, path, image_entities):
        Entity.__init__(self, ident, infos)
        assert type(path) == str
        for image_entity in image_entities:
            assert issubclass(type(image_entity), ImageEntity)
        self.path = path
        self.image_entities = image_entities
        for image_entity in image_entities:
            image_entity.from_entity = self
            
        self.surface = None

    def __str__(self):
        return "Image(" + self.path + ")"

    def is_pictured(self, entity):
        assert issubclass(type(entity), Entity)
        return any([pointer.to_entity == entity for pointer in self.image_entities])

    def add_pictured(self, entity):
        assert not self.is_pictured(entity)
        image_pointer = ImageEntity(entity, ImageEntity.Rect([0.0, 0.0, 1.0, 1.0]), False)
        image_pointer.from_entity = self
        self.image_entities.append(image_pointer)

    def remove_pictured(self, entity):
        assert self.is_pictured(entity)
        for pointer in self.image_entities[:]:
            if pointer.to_entity == entity:
                pointer.delete()


    def save(self, ident_lookup):
        return myxml.Tag("image", "", [myxml.Tag("id", str(ident_lookup[self]), []),
                                       myxml.Tag("file", self.path, []),
                                       Info.SaveInfos(self.infos),
                                       myxml.Tag("image_entities", "", [image_entity.save(ident_lookup) for image_entity in self.image_entities if image_entity.to_entity in ident_lookup])])

    def to_json(self):
        ans = super().to_json()
        ans["type"] = "image"
        ans["path"] = self.path
        ans["entities"] = [ptr.to_json() for ptr in self.image_entities]
        return ans

    def to_obj_json(self, idt):
        ans = super().to_obj_json(idt)
        ans["type"] = "image"
        ans["content"]["path"] = self.path
        ans["content"]["subimages"] = [idt(img_ent) for img_ent in self.image_entities]
        return ans



class Tree():
    @staticmethod
    def Load(tag):
        assert tag.name == "tree"
        entity_lookup = {}
        for sub_tag in tag.get_sub_tags("person"):
            entitiy = Person.Load(sub_tag)
            assert not entitiy.ident in entity_lookup
            entity_lookup[entitiy.ident] = entitiy
        for sub_tag in tag.get_sub_tags("partnership"):
            entitiy = Partnership.Load(sub_tag, entity_lookup)
            assert not entitiy.ident in entity_lookup
            entity_lookup[entitiy.ident] = entitiy
        for sub_tag in tag.get_sub_tags("image"):
            entitiy = Image.Load(sub_tag, entity_lookup)
            assert not entitiy.ident in entity_lookup
            entity_lookup[entitiy.ident] = entitiy
        return Tree(entity_lookup)
    
    def __init__(self, entity_lookup = {}):
        assert type(entity_lookup) == dict
        for ident, entity in entity_lookup.items():
            assert type(ident) == int
            assert issubclass(type(entity), Entity)
        self.entity_lookup = entity_lookup

    def new_ident(self):
        for x in itertools.count():
            if not str(x) in self.entity_lookup:
                return x

    @property
    def people(self):
        return tuple(entity for entity in self.entity_lookup.values() if type(entity) == Person)

    def save(self):
        return myxml.Tag("tree", "", [entity.save(self.entity_lookup) for entity in self.entities])

    def to_json(self):
        ans = [entity.to_json() for ident, entity in self.entity_lookup.items()]
        return ans

    def to_obj_json(self, idt):
        return {"type" : "tree",
                 "ref" : "root",
                 "id" : idt(self),
                 "content" : {"entities" : [idt(ent) for ent in self.entity_lookup.values()]}}


def to_obj_json(tree):
    class IdTrack():
        def __init__(self):
            self.id_assignments = {}
            self.objs = []

        def __call__(self, inst):
            if not inst in self.id_assignments:
                self.id_assignments[inst] = len(self.id_assignments)
                self.objs.append(inst.to_obj_json(self))
            return self.id_assignments[inst]
                
    idt = IdTrack()
    idt(tree)
    return idt.objs
        
        


def load_ged(path):
    def multisplit(string, splits):
        strings = [string]
        for split in splits:
            strings = sum([string.split(split) for string in strings], [])
        return strings


    f = open(path)
    text = "\n" + "\n".join(f.read().split("\n")[1:])
    f.close()

    people = {}
    partnerships = {}

    def load_event(layer1):
        infos = []
        for layer2 in layer1.split("\n2")[1:]:
            title = layer2.split("\n")[0][1:]
            if title.split(" ")[0] == "DATE":
                date = title.split(" ")[1:]

                def add_date(date):
                    if date[0] == "ABT":
                        tags = ["Circa"]
                        date = date[1:]
                    elif date[0] == "TO":
                        tags = ["To"]
                        date = date[1:]
                    elif date[0] == "FROM":
                        tags = ["From"]
                        date = date[1:]
                    elif date[0] == "BEF":
                        tags = ["Before"]
                        date = date[1:]
                    elif date[0] == "AFT":
                        tags = ["After"]
                        date = date[1:]
                    elif date[0] == "EST":
                        tags = ["Circa"]
                        date = date[1:]
                    else:
                        tags = []

                    while "" in date:
                        date.remove("")

                    def parse_month(month):
                        if month == "June":
                            month = "JUN"

                        try:
                            month = int(month)
                        except ValueError:
                            pass
                        else:
                            return str(month)
                        
                        month_strs = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
                        if not month in month_strs:
                            raise Exception(month)
                                                
                        return str(month_strs.index(month) + 1)
                        
                    if len(date) == 1:
                        infos.append(Date(None, None, date[0], tags))
                    elif len(date) == 2:
                        if date[0][-2:] in ["st", "nd", "rd", "th"]:
                            if date[1] == "June":
                                date[1] = "JUN"
                            infos.append(Date(date[0][:-2], parse_month(date[1]), None, tags))
                        else:
                            infos.append(Date(None, parse_month(date[0]), date[1], tags))
                    elif len(date) == 3:
                        infos.append(Date(date[0], parse_month(date[1]), date[2], tags))
                    else:
                        raise Exception(date)

                if "AND" in date and date[0] == "BET":
                    date_1, date_2 = [x.split(" ") for x in " ".join(date[1:]).split(" AND ")]
                    date_1 = ["AFT"] + date_1
                    date_2 = ["BEF"] + date_2
                    add_date(date_1)
                    add_date(date_2)
                else:
                    add_date(date)
                    
            elif title.split(" ")[0] == "PLAC":
                infos.append(SubInfo("location", [String(" ".join(title.split(" ")[1:]))]))
            elif title.split(" ")[0] == "NOTE":
                infos.append(SubInfo("note", [String(" ".join(title.split(" ")[1:]))]))
            elif title.split(" ")[0] == "EMAIL":
                infos.append(SubInfo("email", [String(" ".join(title.split(" ")[1:]).replace("@@", "@"))]))
            elif title.split(" ")[0] == "ADDR":
                infos.append(SubInfo("address", [String(layer2)]))
            elif title.split(" ")[0] == "AGE":
                infos.append(SubInfo("age", [String(" ".join(title.split(" ")[1:]))]))
            elif title.split(" ")[0] == "CAUS":
                infos.append(SubInfo("cause", [String(" ".join(title.split(" ")[1:]))]))
            else:
                raise Exception(title)
        return infos
   

    class IdentLoader():
        def __init__(self):
           self.lookup = {}
           
        def __call__(self, ident):
            if not ident in self.lookup:
                self.lookup[ident] = len(self.lookup)
            return self.lookup[ident]
    load_ident = IdentLoader()
       

    def load_partnership(ident, layer0):
        children = []
        parents = []
        infos = []
        for layer1 in layer0.split("\n1")[1:]:
            title = layer1.split("\n")[0][1:]
            if title.split(" ")[0] == "CHIL":
                ident = title.split(" ")[1]
                children.append(ChildPointer(people[load_ident(ident)], False))
            elif title.split(" ")[0] in ["HUSB", "WIFE"]:
                ident = title.split(" ")[1]
                parents.append(ParentPointer(people[load_ident(ident)]))
            elif title == "MARR":
                infos.append(SubInfo("marriage", load_event(layer1)))
            elif title[0] == "DIV":
                infos.append(SubInfo("divorce", load_event(layer1)))

        return Partnership(load_ident(ident), infos, parents, children)


    def load_person(ident, layer0):
        def load_name(text):
            names = [word for word in text.split(" ")]
            first = []
            middle = []
            last = []
            for idx, name in enumerate(names):
                if name.strip("/") == name:
                    if idx == 0:
                        first.append(name)
                    else:
                        middle.append(name)
                else:
                    last.append(name.strip("/"))
            return first, middle, last

        first, middle, last, titles = [], [], [], []
        infos = []
        for layer1 in layer0.split("\n1")[1:]:
            title = layer1.split("\n")[0][1:]

            if title.split(" ")[0] == "NAME":
                first, middle, last = load_name(" ".join(title.split(" ")[1:]))
            elif title.split(" ")[0] == "TITL":
                titles.append(" ".join(title.split(" ")[1:]))
            elif title == "BIRT":
                infos.append(SubInfo("birth", load_event(layer1)))
            elif title == "DEAT Y":
                infos.append(SubInfo("death", load_event(layer1)))
            elif title == "DEAT":
                infos.append(SubInfo("death", load_event(layer1)))
            elif title == "BURI":
                infos.append(SubInfo("burial", load_event(layer1)))
            elif title == "CHR":
                infos.append(SubInfo("christening", load_event(layer1)))
            elif title == "RESI":
                infos.append(SubInfo("residence", load_event(layer1)))
            elif title == "SEX F":
                infos.append(SubInfo("sex", [String("female")]))
            elif title == "SEX M":
                infos.append(SubInfo("sex", [String("male")]))
            elif title.split(" ")[0] == "NOTE":
                infos.append(SubInfo("note", [String(" ".join(title.split(" ")[0][1:]))]))
            else:
                pass
                #print("unknown title", title)

        #filtering specific to royal92.ged
        name = " ".join(titles + first + middle + last)
        if "son" in name.lower() or "dau" in name.lower() or "unknown" in name.lower() or "child" in name.lower():
            print(name)

        return Person(load_ident(ident), [SubInfo("name", [SubInfo("title", [String(x)]) for x in titles] + [SubInfo("first", [String(x)]) for x in first] + [SubInfo("middle", [String(x)]) for x in middle] + [SubInfo("last", [String(x)]) for x in last])] + infos)

    for layer0 in text.split("\n0")[1:]:
        title = layer0.split("\n")[0][1:]
        if title == "HEAD":
            pass
        elif title == "TRLR":
            pass
        else:
            ident, kind = title.split(" ")
            if kind == "INDI":
                #add a person
                people[load_ident(ident)] = load_person(ident, layer0)
            elif kind == "FAM":
                #add a fam
                partnerships[load_ident(ident)] = load_partnership(ident, layer0)
            else:
                pass

    return Tree(people | partnerships)
           

   










        




if __name__ == "__main__":
    with open("main0.txt", "r") as f:
        tree = Tree.Load(myxml.Tag.Load(f.read()))
    print(tree)
