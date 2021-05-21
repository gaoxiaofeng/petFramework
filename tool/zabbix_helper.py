commands = []
command_template = "ssh-copy-id root@{};"
vms = """
clab045node01
clab045node02
clab045node03
clab045node04
clab045node05
clab045node06
clab045node07
clab045node08
clab045node09
clab045node10
clab045node11
clab045node12
clab045node13
clab045node14
clab045node15
clab045node16
clab045node17
clab045node18
clab045node19
clab045node20
clab045node21
clab045node25
clab045node26
clab045node27
clab045node28
"""
vm_list = vms.strip().split("\n")
for vm in vm_list:
    commands.append(command_template.format(vm))

print("".join(commands))