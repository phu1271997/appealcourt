# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

from dataclasses import dataclass
import json


def _run_nondet(leader_fn, validator_fn):
    fn = (
        getattr(gl.vm, "run_nondet_default", None)
        or getattr(gl.vm, "run_nondet", None)
        or gl.vm.run_nondet_unsafe
    )
    return fn(leader_fn, validator_fn)


def _addr_str(addr: Address) -> str:
    try:
        return addr.as_hex
    except Exception:
        return str(addr)


def _now_epoch() -> bigint:
    try:
        return bigint(int(gl.vm.get_timestamp().timestamp()))
    except Exception:
        return bigint(0)


@allow_storage
@dataclass
class EnBancReview:
    case_id: str
    appellant: str
    original_platform: str
    original_action: str
    original_rule_url: str
    original_content_url: str
    original_verdict: str
    extra_urls: DynArray[str]
    request_statement: str
    stake: bigint
    state: str  # "PENDING" | "RULED" | "FINAL"
    verdict: str  # "" | "UPHOLD" | "REVERSE"
    new_appeal_verdict: str  # "OVERTURN" | "REDUCE_SEVERITY" | "UPHOLD_BAN"
    reason: str
    confidence: u8
    created_at_epoch: bigint
    ruled_at_epoch: bigint


class EnBanc(gl.Contract):
    admin: Address
    appeal_case_contract: Address
    reputation_contract: Address
    reviews: TreeMap[str, EnBancReview]
    case_to_review_id: TreeMap[str, str]
    next_id: bigint

    def __init__(self):
        self.admin = gl.message.sender_address
        self.next_id = bigint(1)

    @gl.public.write
    def set_dependencies(self, appeal_case: Address, rep_contract: Address) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only admin can set dependencies")
        self.appeal_case_contract = appeal_case
        self.reputation_contract = rep_contract

    @gl.public.write.payable
    def fund_pool(self) -> None:
        """Allow admin or supporters to deposit native GEN into the En Banc refund pool."""
        pass

    @gl.public.write.payable
    def request_review(
        self,
        case_id: str,
        extra_urls: DynArray[str],
        statement: str,
        proposed_verdict: str,
    ) -> str:
        if not self.appeal_case_contract:
            raise gl.vm.UserError("AppealCase contract not configured")

        if len(extra_urls) == 0 or len(extra_urls) > 3:
            raise gl.vm.UserError("Provide 1 to 3 cross-check evidence URLs")

        for u in extra_urls:
            if not u.startswith("https://"):
                raise gl.vm.UserError("All cross-check URLs must be https")

        if not statement or len(statement.strip()) == 0:
            raise gl.vm.UserError("Statement cannot be empty")
        if len(statement) > 1000:
            raise gl.vm.UserError("Statement exceeds 1000 characters")

        if case_id in self.case_to_review_id:
            raise gl.vm.UserError("Case already has an En Banc review")

        # Fetch case data from AppealCase
        appeal_contract = gl.get_contract_at(self.appeal_case_contract)
        case_json_str = appeal_contract.view().get_case(case_id)
        case_data = json.loads(case_json_str)

        orig_state = case_data.get("state", "")
        if orig_state not in ["RULED", "FINAL", "EN_BANC_REQUESTED"]:
            raise gl.vm.UserError("Case is not eligible for En Banc review")

        original_stake = int(case_data.get("stake", "0"))
        required_stake = original_stake * 2
        if int(gl.message.value) < required_stake:
            raise gl.vm.UserError("En Banc review requires double the original stake")

        # Ensure AppealCase transitions to EN_BANC_REQUESTED
        if orig_state != "EN_BANC_REQUESTED":
            appeal_contract.emit().notify_en_banc_requested(case_id)

        sender_str = _addr_str(gl.message.sender_address)
        review_id_int = int(self.next_id)
        self.next_id = bigint(review_id_int + 1)
        review_id_str = str(review_id_int)

        review = EnBancReview(
            case_id=case_id,
            appellant=case_data.get("appellant", sender_str),
            original_platform=case_data.get("platform", ""),
            original_action=case_data.get("action_taken", ""),
            original_rule_url=case_data.get("rule_url", ""),
            original_content_url=case_data.get("content_url", ""),
            original_verdict=case_data.get("verdict", ""),
            extra_urls=extra_urls,
            request_statement=statement.strip(),
            stake=bigint(int(gl.message.value)),
            state="PENDING",
            verdict="",
            new_appeal_verdict="",
            reason="",
            confidence=u8(0),
            created_at_epoch=_now_epoch(),
            ruled_at_epoch=bigint(0),
        )
        self.reviews[review_id_str] = review
        self.case_to_review_id[case_id] = review_id_str

        self._judge_en_banc(review_id_str)
        return review_id_str

    def _judge_en_banc(self, review_id: str) -> None:
        rev = self.reviews[review_id]
        urls_snapshot = list(rev.extra_urls)
        rule_url = rev.original_rule_url
        content_url = rev.original_content_url
        platform = rev.original_platform
        action = rev.original_action
        orig_verdict = rev.original_verdict
        statement = rev.request_statement
        case_id = rev.case_id
        appellant = rev.appellant

        def leader_fn():
            # 1. Fetch original rule URL
            rule_text = ""
            rule_err = ""
            try:
                rule_text = gl.nondet.web.render(rule_url, mode="text")[:6000]
            except Exception as e:
                rule_err = str(e)[:200]

            # 2. Fetch content URL
            content_text = ""
            content_err = ""
            try:
                content_text = gl.nondet.web.render(content_url, mode="text")[:5000]
            except Exception as e:
                content_err = str(e)[:200]

            # 3. Fetch 2-3 cross-check URLs (help center, similar precedent, policy clarification)
            cross_checks = []
            for u in urls_snapshot:
                try:
                    txt = gl.nondet.web.render(u, mode="text")[:4000]
                    cross_checks.append({"url": u, "content": txt})
                except Exception as e:
                    cross_checks.append({"url": u, "error": str(e)[:200]})

            prompt = f"""You are the highest En Banc Appellate Court on GenLayer, reviewing a contested content moderation appeal.

ORIGINAL DISPUTE:
- Platform: {platform}
- Action Taken: {action}
- Original Verdict Under Review: {orig_verdict}
- Appellant Statement / Petition for En Banc:
{statement}

PRIMARY SOURCES FETCHED ON-CHAIN:
- Platform Rule URL: {rule_url}
  Live Content: {rule_text if rule_text else f"[Fetch Error: {rule_err}]"}

- Content URL Under Review: {content_url}
  Live Content: {content_text if content_text else f"[Fetch Error: {content_err}]"}

MULTI-SOURCE CROSS-CHECK EVIDENCE ({len(cross_checks)} sources):
{json.dumps(cross_checks, indent=2)[:8000]}

APPELLATE REVIEW DIRECTIVE:
Conduct a comprehensive multi-source review. Re-evaluate whether the original decision ({orig_verdict}) was legally sound, proportional, and consistent with the platform's public precedent and help documentation.

Determine:
1. Should the original verdict be UPHELD or REVERSED?
2. If REVERSED, what should the corrected final appeal verdict be ("OVERTURN" or "REDUCE_SEVERITY")?
3. Provide a rigorous, legally sound rationale referencing the specific multi-source evidence.

RESPOND WITH ONLY VALID JSON (no markdown fences):
{{
  "verdict": "UPHOLD" | "REVERSE",
  "new_appeal_verdict": "OVERTURN" | "REDUCE_SEVERITY" | "UPHOLD_BAN",
  "confidence": 0-100,
  "reason": "Detailed legal rationale citing multi-source cross-check evidence"
}}
"""
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            return raw

        def validator_fn(leader_res) -> bool:
            """
            CONSENSUS RULE: Compares semantic VERDICT ('UPHOLD' vs 'REVERSE').
            Reasoning style and phrasing are not compared directly.
            """
            if not isinstance(leader_res, gl.vm.Return):
                return False
            leader = leader_res.calldata
            if not isinstance(leader, dict) or "verdict" not in leader:
                return False
            mine = leader_fn()
            if not isinstance(mine, dict) or "verdict" not in mine:
                return False
            return mine["verdict"] == leader["verdict"]

        result = _run_nondet(leader_fn, validator_fn)
        verdict = str(result.get("verdict", "UPHOLD")).upper()
        if verdict not in ["UPHOLD", "REVERSE"]:
            verdict = "UPHOLD"

        new_appeal_verdict = str(
            result.get("new_appeal_verdict", orig_verdict)
        ).upper()
        if new_appeal_verdict not in ["OVERTURN", "REDUCE_SEVERITY", "UPHOLD_BAN"]:
            new_appeal_verdict = (
                "OVERTURN" if verdict == "REVERSE" else orig_verdict
            )

        reason = str(result.get("reason", "En Banc review concluded."))
        confidence = int(result.get("confidence", 80))

        rev.verdict = verdict
        rev.new_appeal_verdict = new_appeal_verdict
        rev.reason = reason
        rev.confidence = u8(max(0, min(100, confidence)))
        rev.state = "RULED"
        rev.ruled_at_epoch = _now_epoch()

        # Execute En Banc settlement - atomic, no silent error suppression
        if verdict == "REVERSE":
            # Refund En Banc stake to appellant
            gl.get_contract_at(Address(appellant)).emit_transfer(
                value=u256(int(rev.stake))
            )

            # Notify AppealCase contract to settle with overturned verdict
            appeal_contract = gl.get_contract_at(self.appeal_case_contract)
            appeal_contract.emit().settle_from_en_banc(
                case_id, new_appeal_verdict, reason, confidence
            )

            # Notify CreatorReputation of En Banc win
            if self.reputation_contract:
                rep = gl.get_contract_at(self.reputation_contract)
                rep.emit().record_verdict(appellant, platform, "EN_BANC_WIN")
        else:
            # UPHOLD: Notify AppealCase that En Banc affirmed original ruling
            appeal_contract = gl.get_contract_at(self.appeal_case_contract)
            appeal_contract.emit().settle_from_en_banc(
                case_id, orig_verdict, reason, confidence
            )

        rev.state = "FINAL"

    @gl.public.write
    def admin_seed_review(
        self,
        case_id: str,
        appellant: str,
        platform: str,
        action: str,
        rule_url: str,
        content_url: str,
        orig_verdict: str,
        extra_urls: DynArray[str],
        statement: str,
        stake: int,
        verdict: str,
        new_appeal_verdict: str,
        reason: str,
        confidence: int,
    ) -> str:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only admin can seed demo en banc reviews")

        review_id_int = int(self.next_id)
        self.next_id = bigint(review_id_int + 1)
        review_id_str = str(review_id_int)

        actual_stake = stake * (10**18) if stake < 10**15 else stake

        review = EnBancReview(
            case_id=case_id,
            appellant=appellant,
            original_platform=platform,
            original_action=action,
            original_rule_url=rule_url,
            original_content_url=content_url,
            original_verdict=orig_verdict,
            extra_urls=extra_urls,
            request_statement=statement,
            stake=bigint(actual_stake),
            state="FINAL",
            verdict=verdict,
            new_appeal_verdict=new_appeal_verdict,
            reason=reason,
            confidence=u8(confidence),
            created_at_epoch=_now_epoch(),
            ruled_at_epoch=_now_epoch(),
        )
        self.reviews[review_id_str] = review
        self.case_to_review_id[case_id] = review_id_str

        # Update reputation if reversed
        if verdict == "REVERSE" and self.reputation_contract:
            try:
                rep = gl.get_contract_at(self.reputation_contract)
                rep.emit().record_verdict(appellant, platform, "EN_BANC_WIN")
            except Exception:
                pass

        return review_id_str

    @gl.public.view
    def get_review(self, review_id: str) -> str:
        if review_id not in self.reviews:
            raise gl.vm.UserError("Review not found")
        r = self.reviews[review_id]
        data = {
            "review_id": review_id,
            "case_id": r.case_id,
            "appellant": r.appellant,
            "original_platform": r.original_platform,
            "original_action": r.original_action,
            "original_rule_url": r.original_rule_url,
            "original_content_url": r.original_content_url,
            "original_verdict": r.original_verdict,
            "extra_urls": list(r.extra_urls),
            "request_statement": r.request_statement,
            "stake": str(r.stake),
            "state": r.state,
            "verdict": r.verdict,
            "new_appeal_verdict": r.new_appeal_verdict,
            "reason": r.reason,
            "confidence": int(r.confidence),
            "created_at_epoch": int(r.created_at_epoch),
            "ruled_at_epoch": int(r.ruled_at_epoch),
        }
        return json.dumps(data)

    @gl.public.view
    def get_review_by_case(self, case_id: str) -> str:
        if case_id not in self.case_to_review_id:
            return json.dumps(None)
        rid = self.case_to_review_id[case_id]
        return self.get_review(rid)

    @gl.public.view
    def list_reviews(self, offset: int, limit: int) -> str:
        total = int(self.next_id) - 1
        results = []
        start = max(1, offset + 1)
        end = min(total + 1, start + limit)

        for i in range(start, end):
            key = str(i)
            if key in self.reviews:
                r = self.reviews[key]
                results.append({
                    "review_id": key,
                    "case_id": r.case_id,
                    "appellant": r.appellant,
                    "original_platform": r.original_platform,
                    "original_verdict": r.original_verdict,
                    "verdict": r.verdict,
                    "new_appeal_verdict": r.new_appeal_verdict,
                    "confidence": int(r.confidence),
                    "state": r.state,
                })
        return json.dumps(results)
