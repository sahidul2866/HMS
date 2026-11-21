"""Asset register ties to capitalized journals; depreciation/disposal share GL controls."""
import calendar
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
from sqlalchemy import select,func
from app.core.exceptions import AppException
from app.models.accounting_control import FixedAsset
from app.models.accounting import JournalEntry
from app.modules.accounting.service import AccountingService
from app.modules.accounting.management import AccountingManagement
from app.modules.support_posting.service import lock_branch


class Assets:
    def __init__(self,db):self.db=db
    def get(self,identity,actor):
        lock_branch(self.db,actor)
        asset=self.db.scalar(select(FixedAsset).where(FixedAsset.id==identity,FixedAsset.branch_id==actor.branch_id).with_for_update())
        if not asset:raise AppException(404,'fixed_asset_not_found','Asset not found')
        return asset
    def register(self,payload,actor):
        lock_branch(self.db,actor)
        if self.db.scalar(select(FixedAsset.id).where(FixedAsset.branch_id==actor.branch_id,FixedAsset.asset_code==payload.asset_code)):raise AppException(409,'asset_code_exists','Asset code already exists')
        entry=self.db.get(JournalEntry,payload.acquisition_journal_id)
        if not entry or entry.branch_id!=actor.branch_id or entry.status!='posted':raise AppException(422,'asset_acquisition_journal','Choose a posted branch acquisition / opening voucher')
        capitalized=sum((line.debit_amount-line.credit_amount for line in entry.lines if line.account_code=='1500'),Decimal(0))
        assigned=self.db.scalar(select(func.coalesce(func.sum(FixedAsset.cost),0)).where(FixedAsset.acquisition_journal_id==entry.id)) or Decimal(0)
        if payload.cost>capitalized-assigned:raise AppException(422,'asset_acquisition_amount','Cost exceeds unassigned capitalized value in this voucher')
        row=FixedAsset(**payload.model_dump(),branch_id=actor.branch_id,accumulated_depreciation=0,status='active',created_by=actor.id,updated_by=actor.id)
        self.db.add(row);self.db.flush();AccountingManagement(self.db).audit(actor,'asset.register',row.id,{'cost':str(row.cost),'journal_id':str(entry.id)});self.db.commit();return row
    def depreciate(self,identity,payload,actor):
        asset=self.get(identity,actor)
        year,month=map(int,payload.month.split('-'));on=date(year,month,calendar.monthrange(year,month)[1])
        service=AccountingService(self.db);reference=str(asset.id)+':'+payload.month
        if service._source_entry_exists(actor.branch_id,'asset_depreciation',reference):return asset
        if asset.status!='active' or (asset.last_depreciation_month and payload.month<asset.last_depreciation_month):raise AppException(409,'asset_depreciation_state','Only an active asset can be depreciated forward')
        elapsed=(year-asset.depreciation_start.year)*12+month-asset.depreciation_start.month+1
        if elapsed<=0:raise AppException(422,'asset_depreciation_start','Depreciation month precedes the configured start')
        target=((asset.cost-asset.residual_value)*min(elapsed,asset.useful_life_months)/asset.useful_life_months).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        amount=target-asset.accumulated_depreciation
        if amount>0:service._create_auto_entry(actor,'asset_depreciation',reference,on,'Straight-line depreciation '+asset.asset_code,[('5150','Depreciation',amount,0),('1590','Accumulated Depreciation',0,amount)])
        asset.accumulated_depreciation=target;asset.last_depreciation_month=payload.month;asset.updated_by=actor.id
        AccountingManagement(self.db).audit(actor,'asset.depreciation',asset.id,{'month':payload.month,'amount':str(amount)});self.db.commit();return asset
    def dispose(self,identity,payload,actor):
        asset=self.get(identity,actor)
        if asset.status!='active':raise AppException(409,'asset_disposed','Asset already disposed')
        net=asset.cost-asset.accumulated_depreciation;difference=payload.proceeds-net
        lines=[('1500','Asset disposal',0,asset.cost)]
        if asset.accumulated_depreciation:lines.append(('1590','Accumulated depreciation disposal',asset.accumulated_depreciation,0))
        if payload.proceeds:lines.append((payload.receipt_account,'Actual asset disposal receipt',payload.proceeds,0))
        if difference<0:lines.append(('5190','Loss on disposal',-difference,0))
        if difference>0:lines.append(('4090','Gain on disposal',0,difference))
        AccountingService(self.db)._create_auto_entry(actor,'asset_disposal',str(asset.id),payload.disposal_date,payload.reason,lines)
        asset.status='disposed';asset.updated_by=actor.id;AccountingManagement(self.db).audit(actor,'asset.dispose',asset.id,{'proceeds':str(payload.proceeds),'reason':payload.reason});self.db.commit();return asset
