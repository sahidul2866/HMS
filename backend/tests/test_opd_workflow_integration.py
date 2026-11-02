"""Real PostgreSQL workflow checks. Opt in with HMS_TEST_DATABASE_URL (local test DB only)."""
from __future__ import annotations

import os
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url

import app.models  # noqa: F401
from app.models.base import Base
from app.models.branch import Branch
from app.models.patient import Patient
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.encounter import Appointment, DoctorOPDSchedule, DoctorSlotBooking, OPDVisit, IPDAdmission
from app.models.queue import QueueToken, QueueCounter
from app.models.billing import BillingItemConfig
from app.modules.appointments.service import AppointmentsService
from app.modules.opd.service import OPDService
from app.modules.queue.service import QueueService
from app.modules.billing.service import BillingServiceManager
from app.schemas.appointment import AppointmentCreate, AppointmentCheckInRequest
from app.schemas.encounter import OPDVisitCreate, OPDVisitConsultationUpdate, OPDVisitOrderCreate, OPDConvertToIPD
from app.schemas.billing import BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate
from app.core.exceptions import AppException
from app.utils.seed_data import PERMISSION_CATALOG


@pytest.fixture(scope='module')
def database():
    url = os.getenv('HMS_TEST_DATABASE_URL')
    if not url:
        pytest.skip('HMS_TEST_DATABASE_URL is required for isolated PostgreSQL integration tests')
    parsed = make_url(url)
    if parsed.host not in {'localhost', '127.0.0.1'} or 'test' not in (parsed.database or ''):
        pytest.fail('Integration tests require a local database whose name contains test')
    engine = create_engine(url)
    schema = 'opd_test_' + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA {schema}'))
    test_engine = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(test_engine)
    yield test_engine
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
    engine.dispose()


@pytest.fixture
def db(database):
    connection = database.connect()
    transaction = connection.begin()
    session = Session(connection, expire_on_commit=False, autoflush=False, join_transaction_mode='create_savepoint')
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def seed(db):
    suffix = uuid4().hex[:8]
    branch = Branch(code='TEST-' + suffix, name='Test Hospital')
    permissions = [Permission(code=code + '', module=module, action=action) for code, module, action, _ in PERMISSION_CATALOG]
    # Each scenario uses a rolled-back outer transaction, so catalog codes are reusable.
    db.add_all([branch, *permissions])
    db.flush()
    admin = User(branch_id=branch.id, username='admin_' + suffix, email=suffix + '@example.test', full_name='Test Reception', hashed_password='unused', direct_permissions=permissions)
    role = Role(code='DOCTOR_' + suffix, name='Doctor', is_doctor_role=True, permissions=[p for p in permissions if p.code in {'opd.view', 'opd.prescribe', 'opd.visit.manage', 'opd.queue.view', 'opd.queue.call'}])
    doctors = [User(branch_id=branch.id, username=f'dr_{suffix}_{i}', email=f'{i}{suffix}@example.test', full_name=f'Doctor {i}', hashed_password='unused', opd_consultation_fee=Decimal('500'), roles=[role]) for i in range(2)]
    patient = Patient(branch_id=branch.id, patient_number='PAT-' + suffix, first_name='Test', last_name='Patient')
    db.add_all([admin, role, patient, *doctors])
    db.flush()
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    for doctor in doctors:
        db.add(DoctorOPDSchedule(branch_id=branch.id, doctor_user_id=doctor.id, weekday=tomorrow.weekday(), start_time='09:00', end_time='17:00', slot_duration_minutes=15, buffer_minutes=0))
    db.flush()
    return admin, doctors, patient, datetime.combine(tomorrow, time(10), tzinfo=UTC)


def visit(db, actor, doctor, patient, slot):
    return OPDService(db).create_visit(OPDVisitCreate(patient_id=patient.id, doctor_user_id=doctor.id, consulting_doctor_name=doctor.full_name, department_name='Medicine', visit_date=slot.date(), slot_start_at=slot), actor, {})


def test_appointment_to_prescription_billing_and_ipd(db):
    actor, doctors, patient, slot = seed(db)
    appointments = AppointmentsService(db)
    booked = appointments.create_appointment(AppointmentCreate(patient_id=patient.id, doctor_user_id=doctors[0].id, appointment_at=slot, slot_start_at=slot, reason='Test complaint'), actor)
    current = appointments.check_in_to_opd(booked.id, AppointmentCheckInRequest(department_name='Medicine'), actor, {})
    assert db.get(Appointment, booked.id).status == 'checked_in'
    booking = db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.appointment_id == booked.id))
    assert booking.opd_visit_id == current.id
    serial = current.queue_number
    assert serial and current.consultation_fee == Decimal('500')
    queue = QueueService(db)
    called = queue.call_next(doctors[0], queue_scope='opd', doctor_user_id=doctors[0].id)
    assert called.visit_id == current.id and called.token_sequence == 1
    OPDService(db).update_status(current.id, 'in_consultation', doctors[0], {})
    OPDService(db).update_consultation(current.id, OPDVisitConsultationUpdate(final_diagnosis='Test diagnosis', vital_signs='Test vitals'), doctors[0], {})
    OPDService(db).create_order(current.id, OPDVisitOrderCreate(order_type='prescription', item_name='Test medicine', instructions='Test instructions'), doctors[0], {})
    OPDService(db).create_order(current.id, OPDVisitOrderCreate(order_type='investigation', service_area='laboratory', item_name='Test laboratory order'), doctors[0], {})
    assert OPDService(db).get_visit(current.id, actor).queue_number == serial
    OPDService(db).update_status(current.id, 'prescribed', doctors[0], {})
    assert db.get(OPDVisit, current.id).queue_number == serial
    token = db.scalar(select(QueueToken).where(QueueToken.queue_scope == 'opd', QueueToken.visit_id == current.id))
    assert token.status == 'completed'
    assert db.scalar(select(QueueToken).where(QueueToken.queue_scope == 'pharmacy', QueueToken.visit_id == current.id))
    billing = BillingServiceManager(db)
    billing.list_services(actor)  # Synchronize the doctor consultation catalog.
    config = db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module == 'opd', BillingItemConfig.unit_price == 500))
    assert config
    invoice = billing.create_invoice(BillingInvoiceCreate(patient_id=patient.id, source_opd_visit_id=current.id, source_module='opd', billing_stage='opd', items=[BillingInvoiceItemCreate(billing_service_id=config.id, quantity=1)]), actor, {})
    invoice = billing.create_payment(invoice.id, BillingPaymentCreate(amount=invoice.total_amount, payment_method='cash'), actor, {})
    assert invoice.payment_status == 'paid'
    assert db.get(OPDVisit, current.id).consultation_payment_status == 'paid'
    assert db.get(OPDVisit, current.id).status == 'prescribed'
    admission = OPDService(db).convert_to_ipd(current.id, OPDConvertToIPD(admitted_at=datetime.now(UTC), admission_type='General', ward_name='Test Ward', bed_number='B1', attending_doctor_name=doctors[0].full_name), actor, {})
    assert admission.attending_doctor_user_id == doctors[0].id
    assert admission.diagnosis == 'Test diagnosis'
    assert db.get(OPDVisit, current.id).converted_ipd_admission_id == admission.id
    with pytest.raises(AppException, match='already converted'):
        OPDService(db).convert_to_ipd(current.id, OPDConvertToIPD(admitted_at=datetime.now(UTC), admission_type='General', ward_name='Test Ward', bed_number='B1', attending_doctor_name=doctors[0].full_name), actor, {})


def test_doctor_isolation_and_serial_lifecycle(db):
    actor, doctors, patient, slot = seed(db)
    first = visit(db, actor, doctors[0], patient, slot)
    second = visit(db, actor, doctors[0], patient, slot + timedelta(minutes=15))
    other = visit(db, actor, doctors[1], patient, slot)
    queue = QueueService(db)
    assert [token.token_sequence for token in queue.list_tokens(doctors[0], queue_scope='opd')] == [1, 2]
    assert queue.list_tokens(doctors[1], queue_scope='opd')[0].token_sequence == 1
    with pytest.raises(AppException, match='own doctor queue'):
        queue.call_next(doctors[0], queue_scope='opd', doctor_user_id=doctors[1].id)
    called = queue.call_next(doctors[0], queue_scope='opd', doctor_user_id=doctors[0].id)
    assert called.visit_id == first.id
    with pytest.raises(AppException, match='current patient'):
        queue.call_next(doctors[0], queue_scope='opd', doctor_user_id=doctors[0].id)
    queue.update_status(called.id, 'skipped', doctors[0])
    recalled = queue.update_status(called.id, 'recalled', doctors[0])
    assert recalled.called_at and recalled.recalled_at
    queue.update_status(called.id, 'in_progress', doctors[0])
    queue.update_status(called.id, 'completed', doctors[0])
    tokens = queue.list_tokens(doctors[0], queue_scope='opd')
    assert next(token for token in tokens if token.visit_id == second.id).status == 'called'
    assert db.get(OPDVisit, other.id).queue_status == 'waiting'


def test_cancelled_appointment_and_duplicate_checkin_are_rejected(db):
    actor, doctors, patient, slot = seed(db)
    appointments = AppointmentsService(db)
    booked = appointments.create_appointment(AppointmentCreate(patient_id=patient.id, doctor_user_id=doctors[0].id, appointment_at=slot, slot_start_at=slot), actor)
    appointments.update_status(booked.id, 'cancelled', actor)
    with pytest.raises(AppException, match='Only scheduled'):
        appointments.check_in_to_opd(booked.id, AppointmentCheckInRequest(department_name='Medicine'), actor, {})
    booked = appointments.create_appointment(AppointmentCreate(patient_id=patient.id, doctor_user_id=doctors[0].id, appointment_at=slot, slot_start_at=slot), actor)
    appointments.check_in_to_opd(booked.id, AppointmentCheckInRequest(department_name='Medicine'), actor, {})
    with pytest.raises(AppException, match='already checked in'):
        appointments.check_in_to_opd(booked.id, AppointmentCheckInRequest(department_name='Medicine'), actor, {})


def test_simultaneous_calls_have_one_winner(database):
    # Committed data is required for independent concurrent connections.
    # This scenario runs in its own schema to avoid affecting other tests.
    schema = 'opd_race_' + uuid4().hex
    with database.engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA {schema}'))
    engine = database.engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as db:
            actor, doctors, patient, slot = seed(db)
            doctor_id = doctors[0].id
            actor_id = actor.id
            actor.branch_id = None  # A hospital-wide operator must share the doctor's queue lock.
            visit(db, actor, doctors[0], patient, slot)
            visit(db, actor, doctors[0], patient, slot + timedelta(minutes=15))
            db.commit()
        barrier = Barrier(2)
        def call(index):
            with Session(engine, expire_on_commit=False) as db:
                doctor = db.get(User, doctor_id if index == 0 else actor_id)
                barrier.wait(timeout=10)
                try:
                    return QueueService(db).call_next(doctor, queue_scope='opd', doctor_user_id=doctor_id).status
                except AppException as error:
                    db.rollback()
                    return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(call, range(2)))
        assert sorted(results) == ['called', 'queue_active_patient_exists']
    finally:
        with database.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_http_appointment_to_prescription_payment_and_admission(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    actor, doctors, patient, slot = seed(db)
    acting = [actor]
    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: acting[0]
    client = TestClient(app)
    def request(method, path, **kwargs):
        response = client.request(method, '/api/v1' + path, **kwargs)
        assert response.status_code == 200, response.text
        return response.json()
    try:
        booked = request('POST', '/appointments', json={'patient_id': str(patient.id), 'doctor_user_id': str(doctors[0].id), 'slot_start_at': slot.isoformat()})
        current = request('POST', f'/appointments/{booked["id"]}/check-in', json={'department_name': 'Medicine'})
        acting[0] = doctors[0]
        called = request('POST', '/queue/call-next', params={'queue_scope': 'opd', 'doctor_user_id': str(doctors[0].id)})
        assert called['visit_id'] == current['id']
        current = request('PUT', f'/opd/visits/{current["id"]}/status', json={'status': 'in_consultation'})
        request('PUT', f'/opd/visits/{current["id"]}/consultation', json={'final_diagnosis': 'Recorded test diagnosis'})
        request('POST', f'/opd/visits/{current["id"]}/orders', json={'order_type': 'prescription', 'item_name': 'Test item', 'instructions': 'Test instructions'})
        current = request('POST', f'/opd/visits/{current["id"]}/finalize', json={'final_diagnosis': 'Recorded test diagnosis'})
        assert current['queue_status'] == 'completed'
        assert len(current['orders']) == 1
        acting[0] = actor
        BillingServiceManager(db).list_services(actor)
        config = db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module == 'opd', BillingItemConfig.unit_price == 500))
        invoice = request('POST', '/billing/invoices', json={'patient_id': str(patient.id), 'source_opd_visit_id': current['id'], 'source_module': 'opd', 'billing_stage': 'opd', 'items': [{'billing_service_id': str(config.id), 'quantity': 1}]})
        invoice = request('POST', f'/billing/invoices/{invoice["id"]}/payments', json={'amount': invoice['total_amount'], 'payment_method': 'cash'})
        assert invoice['payment_status'] == 'paid'
        current = request('GET', f'/opd/visits/{current["id"]}')
        assert current['consultation_payment_status'] == 'paid'
        admission = request('POST', f'/opd/visits/{current["id"]}/convert-to-ipd', json={'admitted_at': datetime.now(UTC).isoformat(), 'admission_type': 'General', 'ward_name': 'Test Ward', 'bed_number': 'B1', 'attending_doctor_name': doctors[0].full_name})
        assert admission['diagnosis'] == 'Recorded test diagnosis'
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
        client.close()


def test_admission_failure_rolls_back_the_entire_opd_handoff(db, monkeypatch):
    from app.modules.audit.service import AuditService
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    OPDService(db).update_status(current.id, 'in_consultation', doctors[0], {})
    visit_id = current.id
    log = AuditService.log
    def fail_opd_audit(self, **kwargs):
        if kwargs.get('module') == 'opd':
            raise RuntimeError('Simulated final handoff failure')
        return log(self, **kwargs)
    monkeypatch.setattr(AuditService, 'log', fail_opd_audit)
    with pytest.raises(RuntimeError, match='final handoff'):
        OPDService(db).convert_to_ipd(visit_id, OPDConvertToIPD(admitted_at=datetime.now(UTC), admission_type='General', ward_name='Test Ward', bed_number='B1', attending_doctor_name=doctors[0].full_name), actor, {})
    db.rollback()
    assert db.scalar(select(IPDAdmission.id).where(IPDAdmission.patient_id == patient.id)) is None
    assert db.get(OPDVisit, visit_id).converted_ipd_admission_id is None
    assert db.get(OPDVisit, visit_id).status == 'in_consultation'


def test_payment_before_consultation_partial_receipts_and_refund(db):
    from app.schemas.billing import BillingRefundCreate
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    billing = BillingServiceManager(db)
    billing.list_services(actor)
    config = db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module == 'opd', BillingItemConfig.unit_price == 500))
    invoice = billing.create_invoice(BillingInvoiceCreate(patient_id=patient.id, source_opd_visit_id=current.id, source_module='opd', billing_stage='opd', items=[BillingInvoiceItemCreate(billing_service_id=config.id, quantity=1)]), actor, {})
    billing.create_payment(invoice.id, BillingPaymentCreate(amount=200, payment_method='cash'), actor, {})
    assert db.get(OPDVisit, current.id).consultation_payment_status == 'partial'
    billing.create_payment(invoice.id, BillingPaymentCreate(amount=300, payment_method='cash'), actor, {})
    assert db.get(OPDVisit, current.id).status == 'waiting'
    assert db.get(OPDVisit, current.id).consultation_payment_status == 'paid'
    OPDService(db).update_status(current.id, 'in_consultation', doctors[0], {})
    billing.create_refund(invoice.id, BillingRefundCreate(amount=100, reason='Test refund'), actor, {})
    assert db.get(OPDVisit, current.id).consultation_payment_status == 'partial'
    assert db.get(OPDVisit, current.id).status == 'in_consultation'


def test_finalization_is_idempotent_and_keeps_unedited_history(db):
    actor, doctors, patient, slot = seed(db)
    first = visit(db, actor, doctors[0], patient, slot)
    second = visit(db, actor, doctors[0], patient, slot + timedelta(minutes=15))
    OPDService(db).update_status(first.id, 'in_consultation', doctors[0], {})
    OPDService(db).update_consultation(first.id, OPDVisitConsultationUpdate(past_history='Existing history', note='Existing note'), doctors[0], {})
    # Prescribing permission is enough to finalize an assigned patient's consultation.
    doctors[0].roles[0].permissions = [permission for permission in doctors[0].roles[0].permissions if permission.code != 'opd.queue.call']
    OPDService(db).finalize_prescription(first.id, OPDVisitConsultationUpdate(final_diagnosis='Test diagnosis'), doctors[0], {})
    OPDService(db).finalize_prescription(first.id, OPDVisitConsultationUpdate(final_diagnosis='Should not replace a finalized diagnosis'), doctors[0], {})
    stored = db.get(OPDVisit, first.id)
    assert stored.past_history == 'Existing history'
    assert stored.note == 'Existing note'
    assert stored.final_diagnosis == 'Test diagnosis'
    assert db.get(OPDVisit, second.id).queue_status == 'called'


def test_counter_mismatch_and_paused_counter_are_rejected(db):
    actor, doctors, patient, slot = seed(db)
    visit(db, actor, doctors[0], patient, slot)
    counter = QueueCounter(branch_id=actor.branch_id, code='ROOM1', name='Room One', module='opd', doctor_user_id=doctors[0].id, status='paused')
    db.add(counter)
    db.flush()
    queue = QueueService(db)
    with pytest.raises(AppException, match='assigned to this queue'):
        queue.call_next(actor, queue_scope='opd', counter_id=counter.id, doctor_user_id=doctors[1].id)
    with pytest.raises(AppException, match='paused'):
        queue.call_next(actor, queue_scope='opd', counter_id=counter.id, doctor_user_id=doctors[0].id)


def test_reassigning_a_waiting_visit_moves_its_doctor_serial(db):
    from app.schemas.encounter import OPDVisitUpdate
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    original_serial = current.queue_number
    updated = OPDService(db).update_visit(current.id, OPDVisitUpdate(visit_date=slot.date(), slot_start_at=slot, department_name='Medicine', doctor_user_id=doctors[1].id, consulting_doctor_name=doctors[1].full_name, consultation_fee=500), actor, {})
    assert updated.queue_number != original_serial
    assert not QueueService(db).list_tokens(doctors[0], queue_scope='opd')
    assert QueueService(db).list_tokens(doctors[1], queue_scope='opd')[0].visit_id == current.id


def test_transfer_to_billing_preserves_the_original_opd_serial(db):
    from app.schemas.queue import QueueTransferRequest
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    original_serial = current.queue_number
    token = QueueService(db).call_next(actor, queue_scope='opd', doctor_user_id=doctors[0].id)
    QueueService(db).update_status(token.id, 'in_progress', actor)
    destination = QueueService(db).transfer(token.id, QueueTransferRequest(queue_scope='billing', module='billing', service_area='payment'), actor)
    assert destination.queue_scope == 'billing'
    assert destination.id != token.id
    assert db.get(OPDVisit, current.id).queue_number == original_serial
    assert db.get(QueueToken, token.id).queue_scope == 'opd'
    assert db.get(QueueToken, token.id).status == 'sent_to_billing'
    OPDService(db).finalize_prescription(current.id, OPDVisitConsultationUpdate(final_diagnosis='Test diagnosis'), doctors[0], {})
    assert db.get(QueueToken, token.id).status == 'completed'


def test_finalization_failure_preserves_the_previous_consultation(db, monkeypatch):
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    OPDService(db).update_status(current.id, 'in_consultation', doctors[0], {})
    OPDService(db).create_order(current.id, OPDVisitOrderCreate(order_type='prescription', item_name='Test medicine'), doctors[0], {})
    visit_id = current.id
    ensure = QueueService.ensure_token
    def fail_pharmacy(self, payload, user, **kwargs):
        if payload.queue_scope == 'pharmacy':
            raise RuntimeError('Pharmacy queue unavailable')
        return ensure(self, payload, user, **kwargs)
    monkeypatch.setattr(QueueService, 'ensure_token', fail_pharmacy)
    with pytest.raises(RuntimeError, match='Pharmacy queue'):
        OPDService(db).finalize_prescription(visit_id, OPDVisitConsultationUpdate(final_diagnosis='Uncommitted diagnosis'), doctors[0], {})
    db.rollback()
    stored = db.get(OPDVisit, visit_id)
    assert stored.status == 'in_consultation'
    assert stored.final_diagnosis is None
    assert stored.queue_status == 'in_progress'


def test_duplicate_slot_is_rejected_without_creating_an_extra_visit(db):
    actor, doctors, patient, slot = seed(db)
    visit(db, actor, doctors[0], patient, slot)
    with pytest.raises(AppException, match='already booked'):
        visit(db, actor, doctors[0], patient, slot)
    db.rollback()
    assert len(OPDService(db).list_visits(actor)) == 1


def test_follow_up_requires_a_finished_consultation_with_the_same_doctor(db):
    actor, doctors, patient, slot = seed(db)
    current = visit(db, actor, doctors[0], patient, slot)
    follow_up = OPDVisitCreate(patient_id=patient.id, doctor_user_id=doctors[0].id, consulting_doctor_name=doctors[0].full_name, department_name='Medicine', visit_date=slot.date(), slot_start_at=slot + timedelta(minutes=15), visit_type='follow_up')
    with pytest.raises(AppException, match='No previous visit'):
        OPDService(db).create_visit(follow_up, actor, {})
    OPDService(db).update_status(current.id, 'in_consultation', doctors[0], {})
    OPDService(db).finalize_prescription(current.id, OPDVisitConsultationUpdate(final_diagnosis='Test diagnosis'), doctors[0], {})
    result = OPDService(db).create_visit(follow_up, actor, {})
    assert result.consultation_fee == doctors[0].opd_follow_up_fee
