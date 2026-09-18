"""Edge cases testing for AppealCourt contracts."""

import pytest
from gltest import get_contract_factory


def test_stake_below_minimum(admin, appellant):
    factory = get_contract_factory("AppealCase")
    case_contract = factory.deploy(account=admin)

    # Min stake is 1000 GEN, sending only 500 should fail
    with pytest.raises(Exception):
        case_contract.connect(appellant).file_appeal(
            args=[
                "YouTube",
                "DEMONETIZATION",
                "https://support.google.com/youtube/answer/6162278",
                "https://en.wikipedia.org/wiki/Fair_use",
                "Short quote",
                "Explanation of fair use",
            ]
        ).transact(value=500)


def test_url_must_be_https(admin, appellant):
    factory = get_contract_factory("AppealCase")
    case_contract = factory.deploy(account=admin)

    # HTTP URL should be rejected
    with pytest.raises(Exception):
        case_contract.connect(appellant).file_appeal(
            args=[
                "YouTube",
                "DEMONETIZATION",
                "http://insecure-rules.com",
                "https://en.wikipedia.org/wiki/Fair_use",
                "Short quote",
                "Explanation",
            ]
        ).transact(value=1000)


def test_unsupported_platform(admin, appellant):
    factory = get_contract_factory("AppealCase")
    case_contract = factory.deploy(account=admin)

    with pytest.raises(Exception):
        case_contract.connect(appellant).file_appeal(
            args=[
                "FakePlatformXYZ",
                "DEMONETIZATION",
                "https://example-guidelines.com",
                "https://example-content.com",
                "Short quote",
                "Explanation",
            ]
        ).transact(value=1000)
