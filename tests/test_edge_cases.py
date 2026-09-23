"""Edge cases testing for AppealCourt contracts."""

from pathlib import Path
import pytest

from gltest.direct.vm import VMContext
from gltest.direct.loader import deploy_contract, create_address


CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
WEI_PER_GEN = 10**18


def test_stake_below_minimum():
    ctx = VMContext()
    admin = create_address("admin")
    alice = create_address("alice")
    ctx.sender = admin

    with ctx.activate():
        appeal = deploy_contract(CONTRACTS_DIR / "appeal_case.py", ctx)

        # Min stake is 1000 GEN in base units, sending only 500 should fail
        ctx.sender = alice
        ctx.value = 500 * WEI_PER_GEN
        with pytest.raises(Exception):
            appeal.file_appeal(
                "YouTube",
                "DEMONETIZATION",
                "https://support.google.com/youtube/answer/6162278",
                "https://en.wikipedia.org/wiki/Fair_use",
                "Short quote",
                "Explanation of fair use",
            )


def test_url_must_be_https():
    ctx = VMContext()
    admin = create_address("admin")
    alice = create_address("alice")
    ctx.sender = admin

    with ctx.activate():
        appeal = deploy_contract(CONTRACTS_DIR / "appeal_case.py", ctx)

        # HTTP URL should be rejected
        ctx.sender = alice
        ctx.value = 1000 * WEI_PER_GEN
        with pytest.raises(Exception):
            appeal.file_appeal(
                "YouTube",
                "DEMONETIZATION",
                "http://insecure-rules.com",
                "https://en.wikipedia.org/wiki/Fair_use",
                "Short quote",
                "Explanation",
            )


def test_unsupported_platform():
    ctx = VMContext()
    admin = create_address("admin")
    alice = create_address("alice")
    ctx.sender = admin

    with ctx.activate():
        appeal = deploy_contract(CONTRACTS_DIR / "appeal_case.py", ctx)

        ctx.sender = alice
        ctx.value = 1000 * WEI_PER_GEN
        with pytest.raises(Exception):
            appeal.file_appeal(
                "FakePlatformXYZ",
                "DEMONETIZATION",
                "https://example-guidelines.com",
                "https://example-content.com",
                "Short quote",
                "Explanation",
            )
