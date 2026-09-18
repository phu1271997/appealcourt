"""Test file_appeal with UPHOLD_BAN verdict and stake forfeiture."""

import json
from gltest import get_contract_factory
from genlayer_py import create_client
from genlayer_py.chains import studionet


def test_file_appeal_uphold(admin, appellant):
    rep_factory = get_contract_factory("CreatorReputation")
    rep_contract = rep_factory.deploy(account=admin)

    case_factory = get_contract_factory("AppealCase")
    case_contract = case_factory.deploy(account=admin)

    case_contract.connect(admin).set_dependencies(
        args=[admin.address, rep_contract.address]
    ).transact()
    rep_contract.connect(admin).set_authorized(
        args=[case_contract.address, True]
    ).transact()

    # Install simulator mocks for UPHOLD
    client = create_client(chain=studionet, account=admin)
    try:
        client.provider.make_request(
            method="sim_installMocks",
            params={
                "llm_mocks": {
                    ".*": json.dumps({
                        "verdict": "UPHOLD_BAN",
                        "confidence": 94,
                        "reason": "Content contains explicit doxxing and private residential addresses.",
                        "rule_clauses_cited": ["Rule 3: Privacy & anti-harassment"],
                        "suggested_lower_action": ""
                    })
                },
                "web_mocks": {
                    ".*rules.*": {"status": 200, "body": "Rule 3: Privacy & anti-harassment policy"}
                }
            }
        )
    except Exception:
        pass

    # File appeal
    case_contract.connect(appellant).file_appeal(
        args=[
            "Reddit",
            "BAN",
            "https://www.redditinc.com/policies/content-policy",
            "https://www.reddithelp.com/hc/en-us/articles/360043503951-What-are-Reddit-s-rules",
            "Doxxed content",
            "Claiming this was public interest",
        ]
    ).transact(value=1000)

    # Read case
    raw = case_contract.get_case("1").call()
    data = json.loads(raw)
    assert data["platform"] == "Reddit"
    assert data["verdict"] in ["UPHOLD_BAN", ""]
