with open("../ccn_sender/napet_lte_model_for_n20_core_ran.csv", "r") as f:
    lines = f.readlines()


with open("sueman.csv", "wb") as f:
    f.write("\n".join(
        list(map(lambda line: ",".join([line.strip().split(",")[0].replace("-", "-{}".format("0123456789"*7)),line.strip().split(",")[1]]), lines)
    )).encode('utf-8'))