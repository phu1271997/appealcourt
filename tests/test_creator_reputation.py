"""Test suite for CreatorReputation contract."""

import json
import pytest
from gltest import get_contract_factory


def test_creator_reputation_badges(admin, appellant):
    factory = get_contract_factory("CreatorReputation")
    rep = factory.deploy(account=admin)

    # 1. Initially 0 appeals
    res_str = rep.get_creator_reputation(args=[appellant.address]).call()
    data = json.loads(res_str)
    assert data["total_appeals"] == 0
    assert len(data["badges"]) == 0

    # 2. Authorize admin to record verdicts
    rep.connect(admin).set_authorized(args=[admin.address, True]).transact()

    # 3. Record a WIN on YouTube
    rep.connect(admin).record_verdict(args=[appellant.address, "YouTube", "WIN"]).transact()
    data = json.loads(rep.get_creator_reputation(args=[appellant.address]).call())
    assert data["wins"] == 1
    assert data["total_appeals"] == 1
    badge_ids = [b["id"] for b in data["badges"]]
    assert "first_appeal" in badge_ids
    assert "vindicated" in badge_ids

    # 4. Record appeals on X and Reddit to earn Cross-Platform badge
    rep.connect(admin).record_verdict(args=[appellant.address, "X", "PARTIAL"]).transact()
    rep.connect(admin).record_verdict(args=[appellant.address, "Reddit", "LOSS"]).transact()
    data = json.loads(rep.get_creator_reputation(args=[appellant.address]).call())
    assert data["total_appeals"] == 3
    badge_ids = [b["id"] for b in data["badges"]]
    assert "cross_platform" in badge_ids

    # 5. Record En Banc win to earn Persistent badge
    rep.connect(admin).record_verdict(args=[appellant.address, "Substack", "EN_BANC_WIN"]).transact()
    data = json.loads(rep.get_creator_reputation(args=[appellant.address]).call())
    badge_ids = [b["id"] for b in data["badges"]]
    assert "persistent" in badge_ids
