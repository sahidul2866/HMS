"""Real XLSX statements with numeric values and formula-safe account labels."""
from io import BytesIO
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill


def statements_xlsx(book):
    workbook=Workbook();sheet=workbook.active;sheet.title='Trial Balance'
    sheet.append(['Account','Name','Category','Debit BDT','Credit BDT','Debit minus credit BDT'])
    for row in book['trial_balance']:
        sheet.append([row['code'],row['name'],row['category'],Decimal(row['debit']),Decimal(row['credit']),Decimal(row['signed_balance'])])
        for column in range(1,4):sheet.cell(sheet.max_row,column).data_type='s'
    sheet.append(['','TOTAL','',Decimal(book['total_debit']),Decimal(book['total_credit']),Decimal(book['total_debit'])-Decimal(book['total_credit'])])
    sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
    for row in sheet.iter_rows(min_row=2,min_col=4):
        for cell in row:cell.number_format='#,##0.00;[Red](#,##0.00)'
    summary=workbook.create_sheet('Financial Statements')
    summary.append(['Statement','Measure','BDT'])
    for section in ['profit_and_loss','balance_sheet']:
        for key,value in book[section].items():summary.append([section,key,Decimal(value)])
    cash=workbook.create_sheet('Cash Flow');cash.append(['Measure','BDT']);cash.append(['Opening cash / bank',Decimal(book['cash_flow']['opening_balance'])]);
    for key,value in book['cash_flow']['movements'].items():cash.append([key,Decimal(value)])
    cash.append(['Closing cash / bank',Decimal(book['cash_flow']['closing_balance'])])
    metadata=workbook.create_sheet('Scope');metadata.append(['Currency','BDT']);metadata.append(['From',str(book.get('date_from') or 'Inception')]);metadata.append(['Through',str(book.get('date_to') or 'All posted dates')]);metadata.append(['Basis','Posted GL, including originals and their reversals. Unclosed earnings included in balance sheet equation.'])
    for key,value in book.get('company',{}).items():metadata.append([key,str(value)]);metadata.cell(metadata.max_row,2).data_type='s'
    for page in workbook:
        for cell in page[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17365D')
        for column in page.columns:page.column_dimensions[column[0].column_letter].width=min(65,max(18,max(len(str(cell.value or '')) for cell in column)+2))
        page.sheet_properties.pageSetUpPr.fitToPage=True;page.page_setup.orientation='landscape'
    data=BytesIO();workbook.save(data);return data.getvalue()


def analysis_xlsx(report,title):
    workbook=Workbook();sheet=workbook.active;sheet.title='Report'
    rows=report.get('rows',[]);columns=list(rows[0]) if rows else ['Result']
    sheet.append(columns)
    numeric={'amount','net_amount','gross','discount','net','cash_refunded','credit_amount','days_overdue'}
    for record in rows:
        sheet.append([Decimal(str(record.get(key,0))) if key in numeric and record.get(key) not in {None,''} else str(record.get(key,'')) for key in columns])
        for index,key in enumerate(columns,1):
            cell=sheet.cell(sheet.max_row,index)
            if key not in numeric:cell.data_type='s'
            else:cell.number_format='#,##0.00;[Red](#,##0.00)'
    scope=workbook.create_sheet('Scope');scope.append(['Report',title]);scope.append(['Basis',report.get('basis','')]);scope.append(['Currency','BDT'])
    if 'total' in report:scope.append(['Total',Decimal(report['total'])])
    for page in workbook:
        page.freeze_panes='A2'
        for cell in page[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17365D')
        for column in page.columns:page.column_dimensions[column[0].column_letter].width=min(65,max(15,max(len(str(cell.value or '')) for cell in column)+2))
    data=BytesIO();workbook.save(data);return data.getvalue()
