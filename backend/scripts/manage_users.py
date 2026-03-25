#!/usr/bin/env python3
"""
CLI tool for managing host user accounts in Open Karaoke Studio.

Usage:
    python scripts/manage_users.py create --username admin --password secret123 --admin
    python scripts/manage_users.py create --username dj_mike --password karaoke2025
    python scripts/manage_users.py list
    python scripts/manage_users.py delete --username old_host

Must be run from the backend/ directory with venv activated.
"""

import argparse
import sys

# Ensure app is importable
sys.path.insert(0, ".")

from app.db.database import SessionLocal
from app.db.models import User


def create_user(args):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == args.username).first()
        if existing:
            print(f"Error: Username '{args.username}' already exists.")
            sys.exit(1)

        user = User(
            username=args.username,
            display_name=args.display_name or args.username,
            is_admin=args.admin,
        )
        user.set_password(args.password)
        db.add(user)
        db.commit()

        role = "admin" if args.admin else "host"
        print(f"Created {role} user '{args.username}' (id={user.id})")
    finally:
        db.close()


def list_users(args):
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("No users found.")
            return

        print(f"{'ID':<6} {'Username':<20} {'Display Name':<20} {'Admin':<6}")
        print("-" * 52)
        for user in users:
            admin = "Yes" if user.is_admin else "No"
            display = user.display_name or "-"
            print(f"{user.id:<6} {user.username:<20} {display:<20} {admin:<6}")
    finally:
        db.close()


def delete_user(args):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == args.username).first()
        if not user:
            print(f"Error: User '{args.username}' not found.")
            sys.exit(1)

        db.delete(user)
        db.commit()
        print(f"Deleted user '{args.username}'.")
    finally:
        db.close()


def reset_password(args):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == args.username).first()
        if not user:
            print(f"Error: User '{args.username}' not found.")
            sys.exit(1)

        user.set_password(args.password)
        db.commit()
        print(f"Password reset for '{args.username}'.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Manage Open Karaoke Studio users")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--username", required=True)
    create_parser.add_argument("--password", required=True)
    create_parser.add_argument("--display-name")
    create_parser.add_argument(
        "--admin", action="store_true", help="Grant admin privileges"
    )
    create_parser.set_defaults(func=create_user)

    # list
    list_parser = subparsers.add_parser("list", help="List all users")
    list_parser.set_defaults(func=list_users)

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a user")
    delete_parser.add_argument("--username", required=True)
    delete_parser.set_defaults(func=delete_user)

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("--username", required=True)
    reset_parser.add_argument("--password", required=True)
    reset_parser.set_defaults(func=reset_password)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
