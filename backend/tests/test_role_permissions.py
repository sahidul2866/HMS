"""Seeded roles must hold the permissions their routes demand for the work the role owns."""
from fastapi.routing import APIRoute

from app.main import app
from app.utils.seed_data import ROLE_CATALOG


def role(name: str) -> set[str]:
    return set(ROLE_CATALOG[name.upper().replace(' ', '_')])


def declared(path: str, method: str):
    route = next(r for r in app.routes if isinstance(r, APIRoute) and r.path == path and method in r.methods)
    all_of, any_of = set(), []
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        name = getattr(dep.call, "__qualname__", "")
        for cell in getattr(dep.call, "__closure__", None) or ():
            if isinstance(cell.cell_contents, tuple):
                if name.startswith("require_permissions"):
                    all_of.update(cell.cell_contents)
                elif name.startswith("require_any_permissions"):
                    any_of.append(set(cell.cell_contents))
        stack.extend(dep.dependencies)
    return all_of, any_of


def allows(path: str, method: str, perms: set[str]) -> bool:
    all_of, any_of = declared(path, method)
    return all_of <= perms and all(group & perms for group in any_of)


def test_doctor_role_can_admit_an_opd_patient_to_ipd():
    doctor = role("Doctor")
    assert allows("/api/v1/opd/visits/{visit_id}/convert-to-ipd", "POST", doctor)
    # Same right the ER conversion and the direct admission endpoints already require.
    assert allows("/api/v1/ipd/admissions", "POST", doctor)


def test_roles_without_admit_right_cannot_convert_opd_visit():
    for name in ("Receptionist", "Billing Staff", "Pharmacist", "Employee", "Lab Technician"):
        assert not allows("/api/v1/opd/visits/{visit_id}/convert-to-ipd", "POST", role(name)), name


def test_front_line_clinical_roles_see_every_doctors_opd_visits():
    # Without this right the OPD list and summary answer 403 and the dashboard shows empty numbers.
    for name in ("Receptionist", "Nurse", "Doctor Assistant", "Management"):
        assert "opd.view.doctor_wise" in role(name), name
    for name in ("Pharmacist", "Employee", "Lab Technician", "Billing Staff"):
        assert "opd.view.doctor_wise" not in role(name), name
