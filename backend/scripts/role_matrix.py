"""Call every parameterless GET route as each seeded role and compare with the route's declared permissions.

Run against a local dev backend: PYTHONPATH=. .venv/bin/python scripts/role_matrix.py
Mints short-lived access tokens for existing dev users; changes no passwords. GETs only.
"""
import json
import os
import sys
from collections import defaultdict

import httpx
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.modules.auth.service import AuthService

BASE = os.environ.get("HMS_API_BASE", "http://127.0.0.1:8000")
if not BASE.startswith(("http://127.0.0.1", "http://localhost")):
    raise SystemExit("local only")


def declared(route):
    """Return (all_of, any_of) permission sets found in the route's dependency closures."""
    all_of, any_of = set(), []
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        call = dep.call
        if getattr(call, "__qualname__", "").startswith("require_permissions"):
            for c in call.__closure__:
                if isinstance(c.cell_contents, tuple):
                    all_of.update(c.cell_contents)
        elif getattr(call, "__qualname__", "").startswith("require_any_permissions"):
            for c in call.__closure__:
                if isinstance(c.cell_contents, tuple):
                    any_of.append(set(c.cell_contents))
        stack.extend(dep.dependencies)
    return all_of, any_of


routes = []
for route in app.routes:
    if "GET" in getattr(route, "methods", ()) and "{" not in route.path and route.path.startswith("/api/v1"):
        all_of, any_of = declared(route)
        routes.append((route.path, all_of, any_of))

db = SessionLocal()
users = list(db.scalars(select(User).where(User.is_active.is_(True))))
by_role = {}
for user in users:
    for role in user.roles:
        by_role.setdefault(role.name, user)

result, problems, scoped = {}, [], []
with httpx.Client(base_url=BASE, timeout=30) as client:
    for role, user in sorted(by_role.items()):
        perms = set(AuthService(db).get_effective_permissions(user))
        token, _ = create_access_token(str(user.id), sorted(perms))
        headers = {"Authorization": f"Bearer {token}"}
        stats = defaultdict(int)
        for path, all_of, any_of in routes:
            allowed = all_of <= perms and all(s & perms for s in any_of)
            guarded = bool(all_of or any_of)
            response = client.get(path, headers=headers)
            code = response.status_code
            stats[code] += 1
            if code >= 500:
                problems.append((role, path, code, "server error"))
            elif guarded and not allowed and code != 403:
                problems.append((role, path, code, f"should be 403 (needs {sorted(all_of)} {[sorted(s) for s in any_of]})"))
            elif guarded and allowed and code == 403:
                message = response.json().get("error", {}).get("message", "") if response.content else ""
                if message.startswith(("Missing permissions", "Requires any of")):
                    problems.append((role, path, code, "unexpected 403 despite permissions"))
                else:
                    scoped.append((role, path, message))  # data-scope rule (for example doctor-wise OPD), not a permission gap
        result[role] = {"user": user.username, "permissions": len(perms), "statuses": dict(stats)}

print(f"routes checked per role: {len(routes)}")
for role, info in result.items():
    print(f"{role:22} {info['user']:18} perms={info['permissions']:3} {info['statuses']}")
print(f"\nscope-restricted reads (permission held, data scope refused): {len(scoped)}")
for item in scoped:
    print("  ", item)
print(f"\nproblems: {len(problems)}")
for item in problems:
    print(item)
json.dump({"roles": result, "problems": problems, "scoped": scoped}, open("/tmp/hms-role-matrix.json", "w"), indent=1, default=str)
sys.exit(1 if problems else 0)
