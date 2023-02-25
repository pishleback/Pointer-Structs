import json


with open("ft0.json", "r") as f:
    thing = json.loads(f.read())

def int_to_str(thing):
    if type(thing) == dict:
        return {key : int_to_str(val) for key, val in thing.items()}
    elif type(thing) == list:
        return [int_to_str(val) for val in thing]
    elif type(thing) == str:
        return thing
    elif type(thing) == int:
        return str(thing)
    elif type(thing) == bool:
        return thing
    elif type(thing) == float:
        return thing
    raise NotImplementedError(f"{type(thing)}")

thing = int_to_str(thing)

def extract_id(obj):
    ident = obj["id"]
    del obj["id"]
    return ident, obj

thing = dict(extract_id(obj) for obj in thing)

with open("ft1.json", "w") as f:
    f.write(json.dumps(thing, indent = 4))
