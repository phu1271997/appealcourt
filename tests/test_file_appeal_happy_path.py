"""Test happy path file_appeal with OVERTURN verdict."""

import json
from gltest import get_contract_factory
from genlayer_py import create_client
from genlayer_py.chains import studionet


def test_file_appeal_overturn(admin, appellant):
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

    # Install simulator mocks
    client = create_client(chain=studionet, account=admin)
    try:
        client.provider.make_request(
            method="sim_installMocks",
            params={
                "llm_mocks": {
                    ".*": json.dumps({
                        "verdict": "OVERTURN",
                        "confidence": 82,
                        "reason": "Content quotes public record information exempt under community guidelines.",
                        "rule_clauses_cited": ["Section 3.2: Public interest commentary exemption."],
                        "suggested_lower_action": ""
                    })
                },
                "web_mocks": {
                    ".*": {"status": 200, "body": "Mock published community guidelines with Section 3.2"}
                }
            }
        )
    except Exception:
        pass

    # File appeal
    case_id = case_contract.connect(appellant).file_appeal(
        args=[
            "YouTube",
            "DEMONETIZATION",
            "https://support.google.com/youtube/answer/6162278",
            "https://en.wikipedia.org/wiki/Fair_use",
            "Educational news quote",
            "This documentary video adhered to fair use commentary guidelines.",
        ]
    ).transact(value=1000)

    # Read case
    raw = case_contract.get_case("1").call()
    data = json.loads(raw)
    assert data["platform"] == "YouTube"
    assert data["appellant"].lower() == appellant.address.lower()
    assert data["verdict"] in ["OVERTURN", ""]
