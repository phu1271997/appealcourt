#!/usr/bin/env python3
"""Deploy AppealCourt contracts (CreatorReputation, EnBanc, AppealCase) to GenLayer studionet.

Usage:
    source ~/.genlayer/env.sh
    python3 scripts/deploy_studionet.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"


def retry_call(fn, max_retries=6, delay=3):
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if i == max_retries - 1:
                raise
            print(f"    [!] Network glitch ({e}). Retrying in {delay}s...")
            time.sleep(delay)


def get_address_from_receipt(receipt):
    if not receipt:
        return None
    addr = None
    if isinstance(receipt, dict):
        addr = (
            receipt.get("data", {}).get("contract_address")
            or receipt.get("contract_address")
            or receipt.get("contractAddress")
            or receipt.get("recipient")
            or receipt.get("tx_data_decoded", {}).get("contract_address")
        )
    else:
        addr = getattr(receipt, "contract_address", None) or getattr(
            receipt, "contractAddress", None
        ) or getattr(receipt, "recipient", None)
    return addr


def deploy_contract(client, account, contract_path: Path, name: str):
    code = contract_path.read_text()
    print(f"\n[+] Deploying {name} ({contract_path.name})...")

    # Schema pre-flight
    try:
        client.get_contract_schema_for_code(code.encode())
        print("    Schema check: PASSED")
    except Exception as e:
        print(f"    Schema check FAILED: {e}", file=sys.stderr)
        raise

    tx_hash = retry_call(lambda: client.deploy_contract(code=code, account=account))
    print(f"    Tx hash: {tx_hash}")

    receipt = retry_call(
        lambda: client.wait_for_transaction_receipt(
            transaction_hash=tx_hash, status="ACCEPTED", interval=3000, retries=60
        )
    )
    addr = get_address_from_receipt(receipt)
    if not addr:
        # Retry with finalized if recipient not in accepted
        receipt = retry_call(
            lambda: client.wait_for_transaction_receipt(
                transaction_hash=tx_hash, status="FINALIZED", interval=3000, retries=60
            )
        )
        addr = get_address_from_receipt(receipt)

    if not addr:
        raise RuntimeError(f"Could not extract deployed address for {name}")

    print(f"    --> {name} deployed at: {addr}")
    return addr, tx_hash


def main() -> int:
    key = os.environ.get("GENLAYER_PRIVATE_KEY")
    if not key or "REPLACE_ME" in key:
        print(
            "ERROR: GENLAYER_PRIVATE_KEY not set. Run: source ~/.genlayer/env.sh",
            file=sys.stderr,
        )
        return 1

    account = create_account(key)
    client = create_client(chain=studionet, account=account)

    print("==================================================")
    print("AppealCourt Deployment - GenLayer Studionet")
    print(f"Deployer: {account.address}")
    print(f"Chain:    {studionet.name} (id={studionet.id})")
    print("==================================================")

    # 1. Deploy CreatorReputation
    rep_addr, rep_tx = deploy_contract(
        client, account, CONTRACTS / "creator_reputation.py", "CreatorReputation"
    )

    # 2. Deploy EnBanc
    enbanc_addr, enbanc_tx = deploy_contract(
        client, account, CONTRACTS / "en_banc.py", "EnBanc"
    )

    # 3. Deploy AppealCase
    appeal_addr, appeal_tx = deploy_contract(
        client, account, CONTRACTS / "appeal_case.py", "AppealCase"
    )

    print("\n[+] Linking contract permissions & dependencies...")

    # Authorize AppealCase on CreatorReputation
    tx1 = retry_call(
        lambda: client.write_contract(
            address=rep_addr,
            function_name="set_authorized",
            args=[appeal_addr, True],
            account=account,
        )
    )
    retry_call(lambda: client.wait_for_transaction_receipt(tx1, status="ACCEPTED", interval=2000, retries=30))
    print("    Authorized AppealCase on CreatorReputation.")

    # Authorize EnBanc on CreatorReputation
    tx2 = retry_call(
        lambda: client.write_contract(
            address=rep_addr,
            function_name="set_authorized",
            args=[enbanc_addr, True],
            account=account,
        )
    )
    retry_call(lambda: client.wait_for_transaction_receipt(tx2, status="ACCEPTED", interval=2000, retries=30))
    print("    Authorized EnBanc on CreatorReputation.")

    # Set dependencies on EnBanc
    tx3 = retry_call(
        lambda: client.write_contract(
            address=enbanc_addr,
            function_name="set_dependencies",
            args=[appeal_addr, rep_addr],
            account=account,
        )
    )
    retry_call(lambda: client.wait_for_transaction_receipt(tx3, status="ACCEPTED", interval=2000, retries=30))
    print("    Linked dependencies on EnBanc.")

    # Set dependencies on AppealCase
    tx4 = retry_call(
        lambda: client.write_contract(
            address=appeal_addr,
            function_name="set_dependencies",
            args=[enbanc_addr, rep_addr],
            account=account,
        )
    )
    retry_call(lambda: client.wait_for_transaction_receipt(tx4, status="ACCEPTED", interval=2000, retries=30))
    print("    Linked dependencies on AppealCase.")

    # Fund initial payout pools with native GEN
    print("\n[+] Funding contract refund pools with native GEN...")
    try:
        tx5 = retry_call(
            lambda: client.write_contract(
                address=appeal_addr,
                function_name="fund_pool",
                args=[],
                value=5000 * (10**18),
                account=account,
            )
        )
        retry_call(lambda: client.wait_for_transaction_receipt(tx5, status="ACCEPTED", interval=2000, retries=30))
        print("    Funded AppealCase pool with 5,000 GEN.")
    except Exception as e:
        print(f"    [!] AppealCase funding note: {e}")

    try:
        tx6 = retry_call(
            lambda: client.write_contract(
                address=enbanc_addr,
                function_name="fund_pool",
                args=[],
                value=10000 * (10**18),
                account=account,
            )
        )
        retry_call(lambda: client.wait_for_transaction_receipt(tx6, status="ACCEPTED", interval=2000, retries=30))
        print("    Funded EnBanc pool with 10,000 GEN.")
    except Exception as e:
        print(f"    [!] EnBanc funding note: {e}")

    deployments = {
        "network": "studionet",
        "chainId": studionet.id,
        "deployer": account.address,
        "contracts": {
            "CreatorReputation": {
                "address": rep_addr,
                "tx": rep_tx,
                "explorer": f"https://genlayer-explorer.vercel.app/address/{rep_addr}",
            },
            "EnBanc": {
                "address": enbanc_addr,
                "tx": enbanc_tx,
                "explorer": f"https://genlayer-explorer.vercel.app/address/{enbanc_addr}",
            },
            "AppealCase": {
                "address": appeal_addr,
                "tx": appeal_tx,
                "explorer": f"https://genlayer-explorer.vercel.app/address/{appeal_addr}",
            },
        },
    }

    dep_file = ROOT / "deployments.json"
    dep_file.write_text(json.dumps(deployments, indent=2))
    print(f"\n[v] Saved deployments to {dep_file}")

    # Write frontend .env
    frontend_env = ROOT / "frontend" / ".env"
    frontend_env.parent.mkdir(parents=True, exist_ok=True)
    env_content = f"""VITE_APPEAL_CONTRACT={appeal_addr}
VITE_ENBANC_CONTRACT={enbanc_addr}
VITE_REPUTATION_CONTRACT={rep_addr}
VITE_STUDIO_RPC=https://studio.genlayer.com/api
VITE_CHAIN_ID=61999
"""
    frontend_env.write_text(env_content)
    (ROOT / "frontend" / ".env.example").write_text(
        env_content.replace(appeal_addr, "0x...").replace(enbanc_addr, "0x...").replace(rep_addr, "0x...")
    )
    print(f"[v] Updated {frontend_env}")

    print("\n==================================================")
    print("APPEALCOURT DEPLOYMENT COMPLETE!")
    print(f"AppealCase:        {appeal_addr}")
    print(f"EnBanc:            {enbanc_addr}")
    print(f"CreatorReputation: {rep_addr}")
    print("==================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
