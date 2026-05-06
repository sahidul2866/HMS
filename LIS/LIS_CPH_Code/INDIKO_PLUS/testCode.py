d = {}
d["ETOH1"]="QALC"
d["BENZ"]="QBEN"
d["CANNAB"]="QT50"
d["OPIATES"]="QOP3"
d["6AM"]="Q6AM"
d["ECSTASY"]="QEX5"
d["AMPH1"]="QAM3"


def get_test_code(testCode):
    if testCode in d:
        return d[testCode]
    else:
        return ""