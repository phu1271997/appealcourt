"""Test happy path file_appeal with OVERTURN verdict."""

from pathlib import Path
import json

from gltest.direct.vm import VMContext
from gltest.direct.loader import deploy_contract, create_address


CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
WEI_PER_GEN = 10**18


def test_file_appeal_overturn():
    ctx = VMContext()
    admin = create_address("admin")
    alice = create_address("alice")
    ctx.sender = admin

    ctx.mock_web(".*", {"status": 200, "body": "Mock published community guidelines with Section 3.2"})
    ctx.mock_llm(
        ".*",
        json.dumps({
            "verdict": "OVERTURN",
            "confidence": 82,
            "reason": "Content quotes public record information exempt under community guidelines.",
            "rule_clauses_cited": ["Section 3.2: Public interest commentary exemption."],
            "suggested_lower_action": "",
        }),
    )

    with ctx.activate():
        appeal = deploy_contract(CONTRACTS_DIR / "appeal_case.py", ctx)

        ctx.sender = alice
        ctx.value = 1000 * WEI_PER_GEN

        case_id = appeal.file_appeal(
            "YouTube",
            "DEMONETIZATION",
            "https://support.google.com/youtube/answer/6162278",
            "https://en.wikipedia.org/wiki/Fair_use",
            "Educational news quote",
            "This documentary video adhered to fair use commentary guidelines.",
        )

        raw = appeal.get_case(case_id)
        data = json.loads(raw)
        assert data["platform"] == "YouTube"
        assert data["verdict"] == "OVERTURN"
        assert data["state"] == "FINAL"
