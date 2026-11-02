"""Dedicated support-service roles and HR payroll reviewer permission."""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4
revision = '20261101_0073'
down_revision = '20261101_0072'
branch_labels = None
depends_on = None
ROLES = {'TRANSPORT_MANAGER': ['dashboard.view', 'patient.view', 'hr.view', 'transport.view', 'transport.dashboard.view', 'transport.vehicle.create', 'transport.vehicle.edit', 'transport.vehicle.status.update', 'transport.driver.manage', 'transport.request.create', 'transport.request.approve', 'transport.dispatch', 'transport.trip.update', 'transport.trip.complete', 'transport.trip.cancel', 'transport.maintenance.manage', 'transport.fuel.manage', 'transport.billing.manage', 'transport.report.view', 'transport.report.export', 'transport.settings.manage', 'scanner.use', 'ai.assistant.use', 'notification.view', 'notification.action', 'queue.view', 'patient.id_card.view', 'patient.id_card.generate', 'patient.id_card.print', 'patient.id_card.reprint'], 'TRANSPORT_DRIVER': ['dashboard.view', 'transport.view', 'transport.trip.update', 'transport.trip.complete', 'scanner.use', 'ai.assistant.use', 'notification.view', 'notification.action', 'queue.view'], 'CATERING_MANAGER': ['dashboard.view', 'catering.view', 'catering.dashboard.view', 'catering.kitchen_queue.view', 'catering.meal.prepare', 'catering.meal.deliver', 'catering.meal.cancel', 'catering.staff_meal.manage', 'catering.report.view', 'catering.report.export', 'catering.settings.manage', 'scanner.use', 'ai.assistant.use', 'notification.view', 'notification.action', 'queue.view']}

def upgrade():
    bind = op.get_bind()
    for code, permissions in ROLES.items():
        bind.execute(sa.text("INSERT INTO roles(id,code,name,is_active,is_doctor_role,is_referral_role) VALUES (:id,:code,:name,true,false,false) ON CONFLICT(code) DO NOTHING"), {'id':uuid4(),'code':code,'name':code.replace('_',' ').title()})
        for permission in permissions:
            bind.execute(sa.text("INSERT INTO role_permissions(role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code=:role AND p.code=:permission ON CONFLICT DO NOTHING"), {'role':code,'permission':permission})
    op.execute("INSERT INTO role_permissions(role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code='HR_MANAGER' AND p.code='hr.payroll.approve' ON CONFLICT DO NOTHING")

def downgrade():
    pass  # Preserve administered roles and permission assignments.
