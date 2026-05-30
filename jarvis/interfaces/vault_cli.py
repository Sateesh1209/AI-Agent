"""Manage your encrypted login vault.

Run:  python main.py vault

Unlock with your master password, then add / list / remove the logins JARVIS
should use for company portals. Set the master password once and remember it —
it can't be recovered.
"""

from __future__ import annotations

import os
from getpass import getpass


def run() -> None:
    from ..vault import Vault

    master = os.getenv("JARVIS_VAULT_PASSWORD") or getpass(
        "Master password for your vault (you choose it the first time): "
    )
    if not master:
        print("No master password entered. Aborting.")
        return
    try:
        vault = Vault(master)
    except ValueError as exc:
        print(f"❌ {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Couldn't open the vault: {exc}")
        print("Install support with:  pip install cryptography")
        return

    print("\n🔐 Vault unlocked. Commands: add | list | remove | quit\n")
    while True:
        try:
            cmd = input("vault> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd in {"quit", "exit", "q"}:
            break
        elif cmd == "add":
            site = input("  Site (e.g. udr.com / workday / ultipro): ").strip()
            if not site:
                continue
            username = input("  Username / email: ").strip()
            password = getpass("  Password (hidden): ")
            vault.set_credential(site, username, password)
            print(f"  ✅ Saved login for '{site.lower()}'.\n")
        elif cmd == "list":
            sites = vault.list_sites()
            if not sites:
                print("  (no logins saved yet)\n")
            else:
                print("  Saved logins for:")
                for s in sites:
                    print(f"    • {s}")
                print()
        elif cmd == "remove":
            site = input("  Site to remove: ").strip()
            print("  ✅ Removed.\n" if vault.delete(site) else "  Not found.\n")
        else:
            print("  Commands: add | list | remove | quit\n")

    print("Vault locked. 🔒")
