import re

left_file = r"C:\RMB\restda\PET_TOOL\py3\simulator\lab.properties"
right_file = r"C:\RMB\restda\PET_TOOL\py3\simulator\lab.properties045"


with open(left_file, "rb") as f:
    left_content = f.read().decode("utf-8")
with open(right_file, "rb") as f:
    right_content = f.read().decode("utf-8")

pattern = re.compile(r"^[^#]*=.*", re.I)
left_kv = dict()
right_kv = dict()
for line in left_content.split("\n"):
    match = pattern.match(line)
    if match:
        key = line.split("=")[0].strip()
        value = line.split("=")[1].strip()
        left_kv.update({key:value})
for line in right_content.split("\n"):
    match = pattern.match(line)
    if match:
        key = line.split("=")[0].strip()
        value = line.split("=")[1].strip()
        right_kv.update({key:value})

for left_key in left_kv:
    if left_key in right_kv and left_kv[left_key] == right_kv[left_key]:
        pass
    else:
        if left_key in right_kv:
            print("{}={} >> {}={}".format(left_key, left_kv[left_key], left_key, right_kv[left_key]))
        else:
            print("{}={} >> missing".format(left_key, left_kv[left_key]))
