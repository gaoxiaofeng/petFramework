def filter_rule(lines, rule):
    return list(filter(lambda line: rule not in line.split(",")[0], lines))

def filter_rule2(lines):
    return list(filter(lambda line: "mcc" in line.split(",")[1] or "mnc" in line.split(",")[1] or "longitude" in line.split(",")[1] or "latitude" in line.split(",")[1], lines))


with open("napet_lte_model_for_n20_core_ran.csv", "rb") as f:
    lines = f.readlines()
lines = list(map(lambda line: line.decode('utf-8'),lines))
    
# lines = filter_rule(lines, "MNL")
# lines = filter_rule(lines, "LNADJ")
# lines = filter_rule(lines, "LNADJL")
# lines = filter_rule(lines, "LNADJG")
# lines = filter_rule(lines, "LNADJW")
# lines = filter_rule(lines, "TNL")
# lines = filter_rule(lines, "EQM")
# lines = filter_rule(lines, "LNREL")
# lines = filter_rule(lines, "ANR")
lines = filter_rule(lines, "EQM_R")
# lines = filter_rule(lines, "LNMME")

lines = filter_rule2(lines)

lines = list(map(lambda line: line.strip(), lines))
lines = list(filter(lambda line: line, lines))

with open("napet_lte_model_for_n20_core_ran_filtered.csv", "wb") as f:
    f.write("\n".join(lines).encode('utf-8'))



