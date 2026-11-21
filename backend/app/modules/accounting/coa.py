"""Editable starting accounts. Codes preserve existing operational mappings."""
GROUPS = {'assets':('1000','Assets','debit'),'liabilities':('2000','Liabilities','credit'),'equity':('3000','Equity','credit'),'income':('400','Revenue','credit'),'expenses':('500','Expenses','debit')}
ACCOUNTS = {
 '1001':('Cash in Hand','assets'), '1011':('Cash at Reception','assets'), '1012':('Cash at Pharmacy','assets'),
 '1013':('Petty Cash','assets'), '1020':('Bank Accounts','assets'), '1031':('bKash Clearing','assets'),
 '1032':('Nagad Clearing','assets'), '1033':('Rocket Clearing','assets'), '1034':('Card Payment Clearing','assets'),
 '1100':('Patient Accounts Receivable','assets'), '1110':('Corporate Accounts Receivable','assets'),
 '1120':('Insurance Receivable','assets'), '1150':('Employee Advances / Meal Receivable','assets'),
 '1160':('Doctor Receivable','assets'), '1180':('Input VAT','assets'), '1170':('Supplier Advances','assets'), '1300':('Inventory / Supplies','assets'),
 '1310':('Pharmacy Inventory','assets'), '1320':('Medical Consumables Inventory','assets'),
 '1500':('Fixed Assets','assets'), '1590':('Accumulated Depreciation','assets'),
 '2100':('Accounts Payable','liabilities'), '2110':('Doctor Payable','liabilities'),
 '2120':('Referral Commission Payable','liabilities'), '2200':('Employee Salary Payable','liabilities'),
 '2210':('Patient Advance Deposits','liabilities'), '2220':('Refund Payable','liabilities'),
 '2230':('Tax Payable','liabilities'), '2240':('VAT Payable','liabilities'), '2250':('Withholding Tax Payable','liabilities'),
 '2300':('Payroll Deductions Clearing','liabilities'), '2400':('Goods Received Clearing','liabilities'),
 '2450':('Vehicle Expense Payable','liabilities'), '2500':('Accrued Expenses','liabilities'), '2600':('Bank Loans','liabilities'),
 '3100':("Owner's Capital",'equity'), '3200':('Retained Earnings','equity'), '3300':('Current Year Earnings','equity'),
 '3400':("Owner's Drawings",'equity'), '3900':('Opening Balance Clearing','equity'),
 '4000':('Hospital Service Revenue','income'), '4010':('OPD Consultation Revenue','income'),
 '4020':('IPD Revenue','income'), '4030':('Laboratory Revenue','income'), '4040':('Radiology Revenue','income'),
 '4050':('Diagnostic Procedure Revenue','income'), '4060':('Surgery Revenue','income'),
 '4070':('Bed and Cabin Revenue','income'), '4080':('Nursing Service Revenue','income'),
 '4090':('Other Service Revenue','income'), '4100':('Refunds and Adjustments','expenses'), '4200':('Pharmacy Sales','income'),
 '4300':('Catering Revenue','income'), '4400':('Transport Revenue','income'),
 '5010':('Doctor Professional Fees','expenses'), '5020':('Referral Commission Expense','expenses'),
 '5030':('Medicine Cost of Goods Sold','expenses'), '5040':('Medical Consumables Expense','expenses'),
 '5100':('Salary and Wages','expenses'), '5110':('Rent','expenses'), '5120':('Electricity','expenses'),
 '5130':('Internet and Communication','expenses'), '5140':('Equipment Maintenance','expenses'),
 '5150':('Depreciation','expenses'), '5160':('Bank Charges','expenses'), '5170':('Mobile Financial Service Charges','expenses'),
 '5180':('Administrative Expenses','expenses'), '5190':('Other Operating Expenses','expenses'),
 '5200':('Kitchen Consumption','expenses'), '5300':('Generator and Fuel','expenses'), '5310':('Vehicle Maintenance Expense','expenses'),
}


def ensure_account(db,actor,code):
    from sqlalchemy import select
    from app.models.accounting import Account
    from app.core.exceptions import AppException
    row=db.scalar(select(Account).where(Account.branch_id==actor.branch_id,Account.account_code==code).with_for_update())
    if row:return row
    if code not in ACCOUNTS:raise AppException(422,'account_not_found','Configure the posting account before using it: '+code)
    name,category=ACCOUNTS[code]
    normal='credit' if category in {'income','liabilities','equity'} else 'debit'
    if code in {'1590'}:normal='credit'
    if code=='3400':normal='debit'
    row=Account(branch_id=actor.branch_id,account_code=code,name=name,category=category,normal_balance=normal,opening_balance=0,current_balance=0,created_by=actor.id,updated_by=actor.id)
    db.add(row);db.flush([row]);return row


def install_template(db,actor):
    from sqlalchemy import select
    from app.models.accounting import Account
    roots={}
    for category,(code,name,normal) in GROUPS.items():
        row=db.scalar(select(Account).where(Account.branch_id==actor.branch_id,Account.account_code==code))
        if not row:
            row=Account(branch_id=actor.branch_id,account_code=code,name=name,category=category,normal_balance=normal,is_control=True,current_balance=0,opening_balance=0,created_by=actor.id,updated_by=actor.id);db.add(row);db.flush()
        roots[category]=row
    for code in ACCOUNTS:
        row=ensure_account(db,actor,code)
        if not row.parent_id:row.parent_id=roots[row.category].id if row.category in roots else None
    db.commit()
    return {'accounts':len(ACCOUNTS),'groups':len(roots)}
