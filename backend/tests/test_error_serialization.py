from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.exceptions import install_exception_handlers
from app.schemas.billing import BillingPaymentCreate


def test_decimal_validation_errors_remain_actionable_422_responses():
    app=FastAPI();install_exception_handlers(app)
    @app.post('/payment')
    def payment(payload:BillingPaymentCreate):return {'ok':True}
    response=TestClient(app).post('/payment',json={'amount':0,'payment_method':'cash'})
    assert response.status_code==422
    detail=response.json()['error']['details'][0]
    assert detail['loc']==['body','amount'] and detail['ctx']['gt']==0
