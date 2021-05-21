with open("../ccn_sender/napet_lte_model_for_n20_core_ran.csv", "r") as f:
    lines = f.readlines()

hierachy_all = map(lambda line: line.strip().split(",")[0], lines)
hierachy_all = ["/".join(map(lambda _hierachy: _hierachy.split("-")[0], dn.split("/"))) for dn in hierachy_all]
hierachy_all = list(set(hierachy_all))
hierachy_all.sort()

def has_child_hierachy(hierachy, hierachy_all):
    for _hierachy in hierachy_all:
        if hierachy != _hierachy and _hierachy.startswith("{}/".format(hierachy)):
            return True
    return False

for hierachy in hierachy_all:
    if has_child_hierachy(hierachy, hierachy_all):
        # print("#{}".format(hierachy))
        pass
    else:
        print(hierachy)
