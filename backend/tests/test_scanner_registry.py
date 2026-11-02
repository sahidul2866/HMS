"""Registered codes preserve identity; shared batch labels never select an arbitrary record."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import re

from test_opd_workflow_integration import database, db, seed  # noqa: F401
from app.models.inventory import InventoryItem, StockBatch
from app.models.branch import Branch
from app.models.scanner import ScanCode
from app.modules.scanner.service import ScannerService
from app.schemas.scanner import ScanCodeCreate, ScanResolveRequest


def test_registered_codes_are_exact_case_and_code39_labels_are_encodable(db):
    actor, _, patient, _ = seed(db)
    service = ScannerService(db)
    token=service.create_code(ScanCodeCreate(record_type='patient',record_id=patient.id,purpose='patient_card'),actor)
    assert service.resolve(ScanResolveRequest(code=token.code_value,expected_patient_id=patient.id),actor).success
    # Force a case change even if a random token happens to contain only digits.
    assert not service.resolve(ScanResolveRequest(code=token.code_value.swapcase()),actor).success
    token39=service.create_code(ScanCodeCreate(record_type='patient',record_id=patient.id,purpose='patient_card',code_type='code39'),actor)
    assert re.fullmatch(r'[A-Z0-9 -]+', token39.code_value)
    assert len(token39.code_value)<=30
    assert service.resolve(ScanResolveRequest(code=token39.code_value),actor).success
    token.expires_at=datetime.now(UTC)-timedelta(seconds=1);db.commit()
    assert not service.resolve(ScanResolveRequest(code=token.code_value),actor).success


def test_shared_batch_numbers_return_all_accessible_matches_without_cross_branch_leaks(db):
    actor, _, _, _ = seed(db)
    other=Branch(code='OTHER-'+uuid4().hex[:8],name='Other hospital');db.add(other);db.flush()
    inaccessible=InventoryItem(branch_id=other.id,name='Other branch stock')
    local=InventoryItem(branch_id=actor.branch_id,name='Local stock')
    db.add_all([inaccessible,local]);db.flush()
    # The out-of-scope row is deliberately inserted first.
    batches=[StockBatch(item_id=inaccessible.id,batch_no='SAME-BATCH',quantity=1),StockBatch(item_id=local.id,batch_no='SAME-BATCH',quantity=2),StockBatch(item_id=local.id,batch_no='SAME-BATCH',quantity=3)]
    db.add_all(batches);db.commit()
    result=ScannerService(db).resolve(ScanResolveRequest(code='SAME-BATCH'),actor)
    assert result.success and result.match_count==2
    assert {r.record_id for r in result.records}=={batches[1].id,batches[2].id}
    assert all(r.query_params['itemId']==str(local.id) for r in result.records)
    assert all(r.query_params['batchId']==str(r.record_id) for r in result.records)


def test_inventory_registry_supports_secure_item_labels_and_respects_inactive_records(db):
    actor, _, _, _ = seed(db)
    item=InventoryItem(branch_id=actor.branch_id,name='Labelled product',item_code='REG-'+uuid4().hex[:8]);db.add(item);db.commit()
    service=ScannerService(db)
    token=service.create_code(ScanCodeCreate(record_type='inventory_item',record_id=item.id,purpose='stock_label'),actor)
    result=service.resolve(ScanResolveRequest(code=token.code_value),actor)
    assert result.success and result.records[0].query_params['itemId']==str(item.id)
    item.is_active=False;db.commit()
    assert not service.resolve(ScanResolveRequest(code=token.code_value),actor).success
