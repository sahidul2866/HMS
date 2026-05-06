GETEIN1600={}
GETEIN1600["PCT"]="PCT.DOSE"
GETEIN1600["NT-proBNP"]="PBNP.DOSE"
GETEIN1600["D-Dimer"]="D-Dimer"
GETEIN1600["HbA1c"]="ADAMS_A1C_P"
#GETEIN1600["RCRP"]="RCRP"   # Vul ase
GETEIN1600["cTnI"]="TnIH.DOSE"

GETEIN1600["hs-CRP^CRP"]="RCRP"

def getServerTestCode(machineTestCode):
    return GETEIN1600[machineTestCode]







