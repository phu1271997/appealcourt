"""Test suite for CreatorReputation contract."""

from pathlib import Path
import json
import sys

from gltest.direct.vm import VMContext
from gltest.direct.loader import deploy_contract, create_address


CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"


def to_address(val):
    AddrCls = sys.modules["genlayer"].Address
    if isinstance(val, AddrCls):
        return val
    return AddrCls(val)


def test_creator_reputation_badges():
    ctx = VMContext()
    admin = create_address("admin")
    alice = create_address("alice")
    ctx.sender = admin

    with ctx.activate():
        rep = deploy_contract(CONTRACTS_DIR / "creator_reputation.py", ctx)
        alice_addr = to_address(alice)
        admin_addr = to_address(admin)

        # 1. Initially 0 appeals
        res_str = rep.get_creator_reputation(alice_addr.as_hex)
        data = json.loads(res_str)
        assert data["total_appeals"] == 0
        assert len(data["badges"]) == 0

        # 2. Authorize admin to record verdicts
        rep.set_authorized(admin_addr, True)

        # 3. Record a WIN on YouTube
        rep.record_verdict(alice_addr.as_hex, "YouTube", "WIN")
        data = json.loads(rep.get_creator_reputation(alice_addr.as_hex))
        assert data["wins"] == 1
        assert data["total_appeals"] == 1
        badge_ids = [b["id"] for b in data["badges"]]
        assert "first_appeal" in badge_ids
        assert "vindicated" in badge_ids

        # 4. Record appeals on X and Reddit to earn Cross-Platform badge
        rep.record_verdict(alice_addr.as_hex, "X", "PARTIAL")
        rep.record_verdict(alice_addr.as_hex, "Reddit", "LOSS")
        data = json.loads(rep.get_creator_reputation(alice_addr.as_hex))
        assert data["total_appeals"] == 3
        badge_ids = [b["id"] for b in data["badges"]]
        assert "cross_platform" in badge_ids

        # 5. Record En Banc win to earn Persistent badge
        rep.record_verdict(alice_addr.as_hex, "Substack", "EN_BANC_WIN")
        data = json.loads(rep.get_creator_reputation(alice_addr.as_hex))
        badge_ids = [b["id"] for b in data["badges"]]
        assert "persistent" in badge_ids
