"""Create an administrator locally; there is no public role-escalation endpoint."""
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_engine
from .models import User
from .schemas import RegisterInput
from .security import password_hasher


def main(only_if_missing=False):
    with Session(get_engine()) as db:
        if only_if_missing and db.scalar(select(User.id).where(User.role == "admin", User.is_active)):
            print("An active administrator already exists. Its account was kept unchanged.")
            return
        print("Create the helpdesk administrator (this is separate from PostgreSQL's account).")
        name = input("Full name: ").strip()
        email = input("Admin email: ").strip()
        password = getpass.getpass("Admin password (12-128 characters): ")
        confirmation = getpass.getpass("Confirm admin password: ")
        if password != confirmation:
            raise ValueError("Passwords did not match. Run setup again.")
        try:
            data = RegisterInput(name=name, email=email, password=password)
        except ValidationError as exc:
            # Never print Pydantic's input values (they could include the password).
            messages = [str(e["loc"][0]) + ": " + e["msg"] for e in exc.errors(include_input=False)]
            raise ValueError("; ".join(messages)) from None
        if db.scalar(select(User.id).where(User.email == str(data.email).lower())):
            raise ValueError("This email already belongs to an account. No role or password was changed.")
        db.add(User(name=data.name, email=str(data.email).lower(), role="admin",
                    password_hash=password_hasher.hash(data.password)))
        db.commit()
        print("Administrator created. Sign in with the email and password you just entered.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        sys.exit(str(exc))
