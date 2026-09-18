#!/usr/bin/env python3
"""Seed AppealCourt with 4 rich, diverse demo cases on GenLayer Studionet:
1. YouTube - OVERTURN (Creator wins full refund, Fair Use educational exemption)
2. X - REDUCE_SEVERITY (Suspension reduced to rate limit, 50% partial refund)
3. Reddit - UPHOLD_BAN (Stake forfeited, explicit harassment & doxxing violation confirmed)
4. Substack - EN BANC REVIEWED (Initial UPHOLD reversed to OVERTURN via full-court cross-check)

Usage:
    source ~/.genlayer/env.sh
    python3 scripts/seed_demo_data.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet

ROOT = Path(__file__).resolve().parent.parent
DEPLOYMENTS_PATH = ROOT / "deployments.json"


def retry_call(fn, max_retries=6, delay=3):
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if i == max_retries - 1:
                raise
            print(f"    [!] Network glitch ({e}). Retrying in {delay}s...", flush=True)
            time.sleep(delay)


def main() -> int:
    key = os.environ.get("GENLAYER_PRIVATE_KEY")
    if not key:
        print("ERROR: GENLAYER_PRIVATE_KEY not set. Run: source ~/.genlayer/env.sh", file=sys.stderr)
        return 1

    if not DEPLOYMENTS_PATH.exists():
        print("ERROR: deployments.json not found. Run scripts/deploy_studionet.py first.", file=sys.stderr)
        return 1

    dep = json.loads(DEPLOYMENTS_PATH.read_text())
    appeal_addr = dep["contracts"]["AppealCase"]["address"]
    enbanc_addr = dep["contracts"]["EnBanc"]["address"]

    account = create_account(key)
    client = create_client(chain=studionet, account=account)

    print("==================================================", flush=True)
    print("Seeding AppealCourt Demo Data on Studionet", flush=True)
    print(f"AppealCase Address: {appeal_addr}", flush=True)
    print(f"EnBanc Address:     {enbanc_addr}", flush=True)
    print(f"Admin Account:      {account.address}", flush=True)
    print("==================================================", flush=True)

    creator_alpha = account.address
    creator_beta = "0xFdc45874126A0580d9A9d034F2AA20d9bdad8235"
    creator_gamma = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

    # Check current case count
    cnt_res = retry_call(lambda: client.read_contract(address=appeal_addr, function_name="get_case_count"))
    cur_cnt = int(cnt_res) if cnt_res is not None else 0
    print(f"Current AppealCase count on chain: {cur_cnt}", flush=True)

    # Case 1: YouTube - OVERTURN (if cur_cnt < 1)
    if cur_cnt < 1:
        print("\n[+] Seeding Case #1: YouTube Fair-Use Demonetization (OVERTURN)...", flush=True)
        tx1 = retry_call(
            lambda: client.write_contract(
                address=appeal_addr,
                function_name="admin_seed_case",
                args=[
                    creator_alpha,
                    "YouTube",
                    "DEMONETIZATION",
                    "https://support.google.com/youtube/answer/6162278",
                    "https://en.wikipedia.org/wiki/Fair_use",
                    "In accordance with 17 U.S. Code § 107, this critique incorporates short archival news clips for educational critique.",
                    "Our 40-minute educational documentary was demonetized under 'sensitive events' despite adhering strictly to transformative fair use with zero graphic footage.",
                    1000,
                    "FINAL",
                    "OVERTURN",
                    "The content under review is transformative educational critique. Under YouTube Advertiser-friendly guidelines Section 3.2, educational commentary discussing public matters does not justify demonetization. Sanction is rescinded.",
                    ["Section 3.2: Objective documentary or educational discussions are suitable for advertising.", "Fair Use: Transformative non-profit commentary is protected."],
                    88,
                ],
                account=account,
            )
        )
        retry_call(lambda: client.wait_for_transaction_receipt(tx1, status="ACCEPTED", interval=2000, retries=30))
        print(f"    Case #1 seeded. Tx: {tx1}", flush=True)

    # Case 2: X - REDUCE_SEVERITY (if cur_cnt < 2)
    if cur_cnt < 2:
        print("\n[+] Seeding Case #2: X Account Suspension (REDUCE_SEVERITY)...", flush=True)
        tx2 = retry_call(
            lambda: client.write_contract(
                address=appeal_addr,
                function_name="admin_seed_case",
                args=[
                    creator_beta,
                    "X",
                    "SUSPENSION",
                    "https://help.twitter.com/en/rules-and-policies/twitter-rules",
                    "https://help.twitter.com/en/rules-and-policies/authenticity-terms",
                    "RT @OpenSourceIntel: Real-time satellite imagery update of global shipping lanes. Detailed methodology thread attached.",
                    "Account suspended for 'platform manipulation'. We operate an open research monitoring desk; no botting, commercial spam, or coordinated engagement groups.",
                    1000,
                    "FINAL",
                    "REDUCE_SEVERITY",
                    "While posting velocity exceeded standard thresholds, there is no evidence of artificial bot coordination. Outright account suspension is disproportionate. Recommended reduction to a temporary posting rate-limit.",
                    ["Platform Authenticity: Single manual accounts with high activity should receive tiered rate warnings prior to suspension."],
                    74,
                ],
                account=account,
            )
        )
        retry_call(lambda: client.wait_for_transaction_receipt(tx2, status="ACCEPTED", interval=2000, retries=30))
        print(f"    Case #2 seeded. Tx: {tx2}", flush=True)

    # Case 3: Reddit - UPHOLD_BAN (if cur_cnt < 3)
    if cur_cnt < 3:
        print("\n[+] Seeding Case #3: Reddit Community Guidelines Violation (UPHOLD_BAN)...", flush=True)
        tx3 = retry_call(
            lambda: client.write_contract(
                address=appeal_addr,
                function_name="admin_seed_case",
                args=[
                    creator_gamma,
                    "Reddit",
                    "BAN",
                    "https://www.redditinc.com/policies/content-policy",
                    "https://www.reddithelp.com/hc/en-us/articles/360043503951-What-are-Reddit-s-rules",
                    "Leaked personal residential documents and phone records of developer team.",
                    "Appellant claimed this was consumer fraud investigation into a failed project.",
                    1000,
                    "FINAL",
                    "UPHOLD_BAN",
                    "The post directly distributed unredacted personal home addresses and phone numbers. Reddit Rule 3 explicitly prohibits publishing private personally identifiable information (PII). Permanent ban is upheld and proportional.",
                    ["Rule 3: Respect the privacy of others. Instigating harassment or posting personal information is strictly prohibited."],
                    96,
                ],
                account=account,
            )
        )
        retry_call(lambda: client.wait_for_transaction_receipt(tx3, status="ACCEPTED", interval=2000, retries=30))
        print(f"    Case #3 seeded. Tx: {tx3}", flush=True)

    # Case 4: Substack - Seed initial case and En Banc Review (if cur_cnt < 4)
    if cur_cnt < 4:
        print("\n[+] Seeding Case #4: Substack Investigative Journalism (EN BANC REVERSED)...", flush=True)
        tx4 = retry_call(
            lambda: client.write_contract(
                address=appeal_addr,
                function_name="admin_seed_case",
                args=[
                    creator_alpha,
                    "Substack",
                    "BAN",
                    "https://substack.com/content-guidelines",
                    "https://en.wikipedia.org/wiki/Freedom_of_speech",
                    "In-depth investigative exposé into pharmaceutical lobbying expenditures across European regulatory bodies.",
                    "Banned for alleged defamatory hate speech. We cited official public registry audits and FOIA records.",
                    1000,
                    "FINAL",
                    "OVERTURN",
                    "[En Banc Appellate Review]: Full court multi-source review examined Substack Terms §4 and Help Center precedents alongside public interest doctrine. Primary reporting is protected investigative journalism.",
                    ["Substack Terms §4: Public interest reporting based on verified government audits is exempt from harassment clauses."],
                    91,
                ],
                account=account,
            )
        )
        retry_call(lambda: client.wait_for_transaction_receipt(tx4, status="ACCEPTED", interval=2000, retries=30))
        print(f"    Case #4 seeded on AppealCase. Tx: {tx4}", flush=True)

    # Seed En Banc review record for Case #4
    print("    Registering En Banc appellate record on EnBanc contract...", flush=True)
    tx5 = retry_call(
        lambda: client.write_contract(
            address=enbanc_addr,
            function_name="admin_seed_review",
            args=[
                "4",
                creator_alpha,
                "Substack",
                "BAN",
                "https://substack.com/content-guidelines",
                "https://en.wikipedia.org/wiki/Freedom_of_speech",
                "UPHOLD_BAN",
                [
                    "https://substack.com/terms",
                    "https://support.substack.com/hc/en-us/articles/360037834571-What-is-Substack-s-content-policy",
                    "https://en.wikipedia.org/wiki/Public_interest",
                ],
                "Appellant petitioned En Banc review arguing initial moderator failed to review Substack's published public interest exemption policies.",
                2000,
                "REVERSE",
                "OVERTURN",
                "Full-court appellate review confirms Section 4 public interest protections apply. Disputed publication represents legitimate public-record investigation.",
                92,
            ],
            account=account,
        )
    )
    retry_call(lambda: client.wait_for_transaction_receipt(tx5, status="ACCEPTED", interval=2000, retries=30))
    print(f"    En Banc review record seeded. Tx: {tx5}", flush=True)

    print("\n==================================================", flush=True)
    print("DEMO DATA SEEDING COMPLETE!", flush=True)
    print("1. Case #1: YouTube (OVERTURN) - 100% Refund", flush=True)
    print("2. Case #2: X (REDUCE_SEVERITY) - 50% Partial Refund", flush=True)
    print("3. Case #3: Reddit (UPHOLD_BAN) - Stake Forfeited", flush=True)
    print("4. Case #4: Substack (EN BANC REVERSED -> OVERTURN)", flush=True)
    print("==================================================", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
