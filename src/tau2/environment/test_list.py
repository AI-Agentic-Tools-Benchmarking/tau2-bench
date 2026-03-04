from tau2.environment.disk_dict import DiskList
from pydantic import BaseModel

class Person(BaseModel):
    name: str

lst = DiskList("test.sqlite", "persons", Person)
lst.clear()
lst.append(Person(name="Alice"))
lst.append(Person(name="Bob"))

print(len(lst))
print([p.name for p in lst])
