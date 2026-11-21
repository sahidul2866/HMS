"""Safe declarative prescription forms. No scripts, executable expressions or HTML."""
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class FormField(BaseModel):
    model_config = {'extra': 'forbid', 'allow_inf_nan': False}
    key: str = Field(pattern=r'^[a-z][a-z0-9_]{0,59}$')
    label: str = Field(min_length=1, max_length=150)
    type: Literal['text','textarea','rich_text','number','date','select','searchable_select','checkbox','radio','medicine','investigation','diagnosis','vitals','notes','medicine_rows','investigation_rows','section','header','footer','table','columns'] = 'text'
    required: bool = False
    visible: bool = True
    print_visible: bool = True
    default: str | int | float | bool | None = None
    options: list[str] = Field(default_factory=list, max_length=200)
    min: Decimal | None = None
    max: Decimal | None = None
    max_length: int = Field(default=10000, ge=1, le=100000)
    column: Literal['full','left','right'] = 'full'
    show_when: dict[str, str | bool | int | float] | None = None

    @model_validator(mode='after')
    def safe_field(self):
        if any(token in self.label.lower() for token in ['<script','javascript:','<iframe','onerror=']):
            raise ValueError('Executable markup is prohibited')
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError('Minimum exceeds maximum')
        if self.type=='checkbox' and self.default is not None and not isinstance(self.default,bool):
            if str(self.default).lower() not in {'true','false'}:raise ValueError('Checkbox defaults must be true or false')
            self.default=str(self.default).lower()=='true'
        if self.type=='number' and self.default is not None:
            try:number=Decimal(str(self.default))
            except Exception:raise ValueError('Number fields require numeric defaults')
            if not number.is_finite():raise ValueError('Number defaults must be finite')
        if self.show_when and (len(self.show_when) != 1 or self.key in self.show_when):
            raise ValueError('Conditional visibility requires one other field')
        return self


def validate_layout(payload):
    if not isinstance(payload, dict): raise ValueError('Template must be an object')
    import json
    serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False).lower()
    if len(serialized)>250000 or any(token in serialized for token in ['<script','javascript:','<iframe','onerror=','<style','@import','expression(']):
        raise ValueError('Unsafe or excessively large template')
    logo=payload.get('hospital_logo')
    if logo:
        import base64,re
        if not isinstance(logo,str) or len(logo)>180000 or not re.fullmatch(r'data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+',logo):raise ValueError('Logo must be a small PNG/JPEG data image')
        try:raw=base64.b64decode(logo.split(',',1)[1],validate=True)
        except Exception:raise ValueError('Invalid logo image')
        if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):raise ValueError('Logo must contain PNG or JPEG bytes')
    if payload.get('paper_size','A5') not in {'A4','A5','custom'}: raise ValueError('Unsupported paper size')
    for key, low, high in [('font_size',8,24),('left_column_width',25,65),('margin_mm',0,30),('paper_width_mm',50,500),('paper_height_mm',50,700)]:
        if key in payload and not low <= float(payload[key]) <= high: raise ValueError('Invalid print dimensions')
    fields=[FormField.model_validate(field) for field in payload.get('fields',[])]
    keys=[field.key for field in fields]
    if len(keys)>100 or len(keys)!=len(set(keys)): raise ValueError('Field keys must be unique; maximum 100 fields')
    for field in fields:
        if field.show_when and not set(field.show_when).issubset(set(keys)): raise ValueError('Conditional field not found')
    allowed=set(keys)
    # Cyclic conditions cannot make required fields disappear unpredictably.
    edges={f.key:next(iter(f.show_when)) for f in fields if f.show_when}
    for key in edges:
        visited=set()
        while key in edges:
            if key in visited: raise ValueError('Cyclic visibility conditions')
            visited.add(key);key=edges[key]
    for section in payload.get('section_labels',[]):
        if section.get('placement','full') not in {'left','right','full'}: raise ValueError('Invalid section placement')
    return payload


class PrescriptionAction(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    expected_version: int = Field(ge=0)


class DirectConsultationPayment(BaseModel):
    kind: Literal['doctor_direct','pending','waived','free']
    amount: Decimal = Field(default=0, ge=0, decimal_places=2)
    reason: str = Field(min_length=3, max_length=1000)
    request_key: str = Field(min_length=8, max_length=100)


class ClinicalShortcut(BaseModel):
    kind: Literal['medicine','investigation','advice','snippet','combination','diagnosis']
    name: str = Field(min_length=1, max_length=150)
    content: dict[str, Any] = Field(default_factory=dict)


class ExternalPaymentReview(BaseModel):
    decision: Literal['verified','rejected']
    evidence: str = Field(min_length=3, max_length=1000)
    request_key: str = Field(min_length=8, max_length=100)


class ExternalRemittanceLink(BaseModel):
    journal_id: UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    evidence: str = Field(min_length=3, max_length=1000)
    request_key: str = Field(min_length=8, max_length=100)
