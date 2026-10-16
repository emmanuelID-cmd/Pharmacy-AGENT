"""Generate an ignored local sender key. Never prints the private value."""
import base64
import os

from cryptography.hazmat.primitives.asymmetric import ec

from ..pharmacy_agent.config import ROOT


def generate(root=ROOT):
    key = ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value.to_bytes(32, "big")
    value = base64.urlsafe_b64encode(key).rstrip(b"=").decode()
    target = root / ".env.push"
    # Existing configuration is never overwritten. .env.* is already ignored.
    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as output:
        output.write("PHARMACY_PUSH_PRIVATE_KEY=" + value + "\n")
    return target


if __name__ == "__main__":
    try:
        print("Created server-only configuration:", generate())
    except FileExistsError:
        raise SystemExit(".env.push already exists; kept the existing key.") from None
