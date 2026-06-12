#!/usr/bin/env python3
"""Создать или обновить аккаунт владельца проекта."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from room.user_auth import ensure_owner


def main():
    parser = argparse.ArgumentParser(description="Создать аккаунт владельца с полными привилегиями")
    parser.add_argument("--email", required=True, help="Email владельца")
    parser.add_argument("--password", required=True, help="Пароль (мин. 6 символов)")
    parser.add_argument("--name", default="Owner", help="Отображаемое имя")
    args = parser.parse_args()

    user = ensure_owner(args.email, args.password, args.name)
    print(f"OK: owner {user['email']} (id={user['id']}, privileges={len(user['privileges'])})")


if __name__ == "__main__":
    main()
