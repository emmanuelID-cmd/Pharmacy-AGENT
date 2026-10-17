"""Generate one private recovery link for an existing teammate; sends no email.

Run only after /account/setup is deployed. Admin credentials stay in process;
the bearer setup link goes only to a new ignored local file, never stdout.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "xrptinavijhwvydoqdni"
ACCOUNTS = {
    "kerrian": ("14973943-cf2d-4632-8e1a-15b414628092", "kerrian.gordon@pursuit.org"),
    "brahim": ("868efbeb-aed0-472e-8ebf-d2270687c523", "brahim.maouloud@pursuit.org"),
}


def checked_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or not re.fullmatch(r"pharmacy-agent-[a-z0-9-]+-professionalportfoliowebsites\.vercel\.app", parsed.hostname or "")):
        raise ValueError("Use a verified Pharmacy Vercel preview origin.")
    return "https://" + parsed.hostname


def generate_link(who, origin, key, *, transport=None):
    origin = checked_origin(origin)
    uid, email = ACCOUNTS[who]
    endpoint = "https://" + PROJECT + ".supabase.co/auth/v1/admin/"
    with httpx.Client(timeout=10, follow_redirects=False, trust_env=False, transport=transport,
                      headers={"apikey": key, "Authorization": "Bearer " + key}) as client:
        user = client.get(endpoint + "users/" + uid)
        if user.status_code != 200 or user.json().get("id") != uid or user.json().get("email", "").casefold() != email:
            raise ValueError("Existing account identity could not be verified.")
        response = client.post(endpoint + "generate_link", json={"type": "recovery", "email": email})
        if response.status_code != 200:
            raise ValueError("Recovery link generation was not confirmed.")
        data = response.json()
        if data.get("id") != uid or data.get("email", "").casefold() != email:
            raise ValueError("Recovery account identity mismatch.")
        proof = data.get("hashed_token")
        if not isinstance(proof, str) or not re.fullmatch(r"[a-f0-9]{40,128}", proof):
            raise ValueError("Recovery link format was not recognized.")
        return origin + "/account/setup#token_hash=" + proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", choices=ACCOUNTS, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--output", required=True, help="New ignored .env.account-setup-* filename in repository root")
    args = parser.parse_args()
    try:
        origin = checked_origin(args.origin)
        if not re.fullmatch(r"\.env\.account-setup-[A-Za-z0-9_-]+", args.output):
            raise ValueError("Output must be a new ignored .env.account-setup-* file.")
        output = ROOT / args.output
        if output.exists() or subprocess.run(["git", "check-ignore", "-q", str(output)], cwd=ROOT).returncode:
            raise ValueError("Refusing existing or unignored output file.")
        cli = shutil.which("supabase") or str(Path.home()/"AppData/Local/Programs/SupabaseCLI/supabase.exe")
        with tempfile.TemporaryDirectory(prefix="pharmacy-setup-admin-") as work:
            result = subprocess.run([cli, "projects", "api-keys", "--project-ref", PROJECT, "--output", "json"],
                                    cwd=work, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError("Authenticated project management access unavailable.")
        keys = json.loads(result.stdout)
        key = next(row["api_key"] for row in keys if row.get("name") == "service_role" and row.get("api_key", "").startswith("eyJ"))
        # Reserve the ignored output before changing the existing recovery proof.
        with output.open("x", encoding="utf-8") as file:
            link = generate_link(args.account, origin, key)
            file.write("Recipient: " + ACCOUNTS[args.account][1] + "\nPrivate one-use setup link; never commit or forward to another person.\n" + link + "\n")
        print("Private setup link saved to " + args.output + "; no email sent. Share only with its named recipient.")
        return 0
    except Exception:
        # Never serialize CLI output, Auth errors, keys, response bodies or links.
        print("Setup link creation was not confirmed. No password was assigned. Inspect configuration and use a new output filename before retrying.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
