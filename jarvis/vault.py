"""An encrypted local vault for your portal logins.

Credentials are stored AES-encrypted (via Fernet) in ~/.jarvis/vault.enc. The
encryption key is derived from a master password you choose — the master
password is NEVER stored, so only you (and JARVIS, when you unlock it) can read
the vault. Lose the master password and the data is unrecoverable.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path.home() / ".jarvis" / "vault.enc"


class Vault:
    def __init__(self, master_password: str, path: str | Path | None = None):
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        self.path = Path(path) if path else DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.salt_path = self.path.with_suffix(".salt")

        salt = self._load_or_create_salt()
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                         iterations=390000)
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self._fernet = Fernet(key)
        # Validate the password by attempting a read (raises on wrong password).
        self._read()

    def _load_or_create_salt(self) -> bytes:
        if self.salt_path.exists():
            return self.salt_path.read_bytes()
        salt = os.urandom(16)
        self.salt_path.write_bytes(salt)
        return salt

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        from cryptography.fernet import InvalidToken

        try:
            data = self._fernet.decrypt(self.path.read_bytes())
        except InvalidToken as exc:
            raise ValueError(
                "Wrong master password (or the vault is corrupted)."
            ) from exc
        return json.loads(data.decode())

    def _write(self, data: dict[str, Any]) -> None:
        token = self._fernet.encrypt(json.dumps(data).encode())
        self.path.write_bytes(token)
        try:
            os.chmod(self.path, 0o600)  # owner read/write only
        except OSError:
            pass

    # -- public API --------------------------------------------------------
    def set_credential(self, site: str, username: str, password: str) -> None:
        data = self._read()
        data[site.lower()] = {"username": username, "password": password}
        self._write(data)

    def get_credential(self, site: str) -> dict[str, str] | None:
        return self._read().get(site.lower())

    def find_for(self, url_or_domain: str) -> dict[str, str] | None:
        """Best-effort match: a stored site that appears in the given URL."""
        target = url_or_domain.lower()
        for site, cred in self._read().items():
            if site in target or target in site:
                return {"site": site, **cred}
        return None

    def list_sites(self) -> list[str]:
        return sorted(self._read().keys())

    def delete(self, site: str) -> bool:
        data = self._read()
        if site.lower() in data:
            data.pop(site.lower())
            self._write(data)
            return True
        return False
