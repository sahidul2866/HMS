"""Write short-lived access tokens for one seeded user per role (local dev only) to a JSON file."""
import json
import os
import sys
from datetime import timedelta

from sqlalchemy import select

import app.main  # noqa: F401  (registers every model)
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User
from app.modules.auth.service import AuthService

out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/hms-role-tokens.json"
db = SessionLocal()
roles = {}
for user in db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.username)):
    for role in user.roles:
        if role.name in roles:
            continue
        perms = sorted(AuthService(db).get_effective_permissions(user))
        token, _ = create_access_token(str(user.id), perms, expires_delta=timedelta(hours=4))
        roles[role.name] = {"username": user.username, "token": token, "permissions": perms}
json.dump(roles, open(out, "w"))
os.chmod(out, 0o600)
print(f"{len(roles)} roles -> {out}")
