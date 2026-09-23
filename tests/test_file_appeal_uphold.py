"""Test file_appeal with UPHOLD_BAN verdict and stake forfeiture."""

from pathlib import Path
import json

from gltest.direct.vm import VMContext
from gltest.direct.loader import deploy_contract, create_address


CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
WEI_PER_GEN = 10**18


def test_file_appeal_uphold():
    ctx = VMContext()
    admin = create_address("admin")
    alice = create_address("alice")
    ctx.sender = admin

    ctx.mock_web(".*", {"status": 200, "body": "Rule 3: Privacy & anti-harassment policy"})
    ctx.mock_llm(
        ".*",
        json.dumps({
            "verdict": "UPHOLD_BAN",
            "confidence": 94,
            "reason": "Content contains explicit doxxing and private residential addresses.",
            "rule_clauses_cited": ["Rule 3: Privacy & anti-harassment"],
            "suggested_lower_action": "",
        }),
    )

    with ctx.activate():
        appeal = deploy_contract(CONTRACTS_DIR / "appeal_case.py", ctx)

        ctx.sender = alice
        ctx.value = 1000 * WEI_PER_GEN

        case_id = appeal.file_appeal(
            "Reddit",
            "BAN",
            "https://www.redditinc.com/policies/content-policy",
            "https://www.reddithelp.com/hc/en-us/articles/360043503951-What-are-Reddit-s-rules",
            "Doxxed content",
            "Claiming this was public interest",
        )

        raw = appeal.get_case(case_id)
        data = json.loads(raw)
        assert data["platform"] == "Reddit"
        assert data["verdict"] == "UPHOLD_BAN"
        assert data["state"] == "FINAL"
