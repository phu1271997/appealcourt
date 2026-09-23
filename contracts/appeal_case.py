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
class Case:
    appellant: str
    platform: str
    action_taken: str
    rule_url: str
    content_url: str
    content_quote: str
    explanation: str
    stake: bigint
    state: str  # OPEN | UNDER_REVIEW | RULED | EN_BANC_REQUESTED | FINAL
    verdict: str  # "" | "UPHOLD_BAN" | "OVERTURN" | "REDUCE_SEVERITY"
    reason: str
    rule_clauses_cited: DynArray[str]
    confidence: u8
    en_banc_contract: str
    reputation_contract: str
    created_at_epoch: bigint
    ruled_at_epoch: bigint


class AppealCase(gl.Contract):
    admin: Address
    en_banc_contract: Address
    reputation_contract: Address
    min_stake: bigint
    cases: TreeMap[str, Case]
    recent_appeals: TreeMap[str, bigint]
    next_id: bigint

    def __init__(self):
        self.admin = gl.message.sender_address
        self.min_stake = bigint(1000 * (10**18))
        self.next_id = bigint(1)

    @gl.public.write
    def set_dependencies(self, en_banc: Address, rep_contract: Address) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only admin can set dependencies")
        self.en_banc_contract = en_banc
        self.reputation_contract = rep_contract

    @gl.public.write
    def set_min_stake(self, new_min_stake: int) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only admin can set min stake")
        if new_min_stake <= 0:
            raise gl.vm.UserError("Min stake must be positive")
        if new_min_stake < 10**15:
            self.min_stake = bigint(new_min_stake * (10**18))
        else:
            self.min_stake = bigint(new_min_stake)

    @gl.public.write.payable
    def fund_pool(self) -> None:
        """Allow admin or supporters to deposit native GEN into the court payout pool."""
        pass

    @gl.public.write.payable
    def file_appeal(
        self,
        platform: str,
        action_taken: str,
        rule_url: str,
        content_url: str,
        content_quote: str,
        explanation: str,
    ) -> str:
        # 1. Stake validation
        if int(gl.message.value) < int(self.min_stake):
            raise gl.vm.UserError("Stake below minimum required (min 1000 GEN)")

        # 2. URL validation
        rule_clean = rule_url.strip()
        content_clean = content_url.strip()
        if not rule_clean.startswith("https://") or not content_clean.startswith("https://"):
            raise gl.vm.UserError("URL must be https")

        # 3. Platform & Action Whitelist
        plat_clean = platform.strip()
        valid_platforms = ["YouTube", "X", "Reddit", "TikTok", "Substack", "Twitch", "Other"]
        if plat_clean not in valid_platforms:
            raise gl.vm.UserError("Unsupported platform")

        act_clean = action_taken.strip().upper()
        valid_actions = ["TAKEDOWN", "DEMONETIZATION", "SHADOWBAN", "STRIKE", "SUSPENSION", "BAN"]
        if act_clean not in valid_actions:
            raise gl.vm.UserError("Unsupported action taken")

        # 4. Content quote & explanation length checks
        if len(content_quote) > 500:
            raise gl.vm.UserError("Content quote exceeds 500 characters")
        if len(explanation) > 800:
            raise gl.vm.UserError("Explanation exceeds 800 characters")
        if len(explanation.strip()) == 0:
            raise gl.vm.UserError("Explanation cannot be empty")

        sender_str = _addr_str(gl.message.sender_address)

        # 5. Duplicate appeal anti-spam check (30 days = 2592000 seconds)
        dup_key = f"{sender_str.lower()}_{content_clean.lower()}"
        last_filed = int(self.recent_appeals.get(dup_key, bigint(0)))
        now_ts = int(_now_epoch())
        if last_filed > 0 and (now_ts - last_filed) < 2592000:
            raise gl.vm.UserError("Duplicate appeal within 30 days")
        self.recent_appeals[dup_key] = bigint(now_ts)

        case_id_int = int(self.next_id)
        self.next_id = bigint(case_id_int + 1)
        case_id_str = str(case_id_int)

        new_case = Case(
            appellant=sender_str,
            platform=plat_clean,
            action_taken=act_clean,
            rule_url=rule_clean,
            content_url=content_clean,
            content_quote=content_quote.strip(),
            explanation=explanation.strip(),
            stake=bigint(int(gl.message.value)),
            state="UNDER_REVIEW",
            verdict="",
            reason="",
            rule_clauses_cited=[],
            confidence=u8(0),
            en_banc_contract=_addr_str(self.en_banc_contract),
            reputation_contract=_addr_str(self.reputation_contract),
            created_at_epoch=_now_epoch(),
            ruled_at_epoch=bigint(0),
        )
        self.cases[case_id_str] = new_case

        # Immediate on-chain jury review
        self._judge(case_id_str)
        return case_id_str

    def _judge(self, case_id: str) -> None:
        case = self.cases[case_id]
        if case.state != "UNDER_REVIEW":
            raise gl.vm.UserError("Case not ready for judgment")

        rule_url = case.rule_url
        content_url = case.content_url
        content_quote = case.content_quote
        explanation = case.explanation
        platform = case.platform
        action = case.action_taken

        def leader_fn():
            # 1. Fetch platform rule URL
            rule_text = ""
            rule_err = ""
            try:
                rule_text = gl.nondet.web.render(rule_url, mode="text")[:8000]
            except Exception as e:
                rule_err = str(e)[:200]

            # 2. Fetch content URL
            content_text = ""
            content_err = ""
            try:
                content_text = gl.nondet.web.render(content_url, mode="text")[:6000]
            except Exception as e:
                content_err = str(e)[:200]

            if not rule_text and not content_text and not content_quote:
                raise gl.vm.UserError(
                    "Both rule and content URLs unreachable - cannot judge"
                )

            prompt = f"""You are a decentralized AI jury reviewing a content moderation appeal on GenLayer.

APPELLANT'S PLATFORM: {platform}
ACTION TAKEN BY PLATFORM: {action}
APPELLANT'S EXPLANATION:
{explanation}

PLATFORM'S PUBLISHED RULE (fetched from {rule_url}):
{rule_text if rule_text else f"[FAILED TO FETCH RULE URL: {rule_err}]"}

CONTENT UNDER REVIEW:
- Content URL: {content_url}
- Live Content Fetched: {content_text if content_text else f"[FAILED TO FETCH CONTENT URL: {content_err}]"}
- Appellant's Verbatim Quote of the Content: {content_quote}

Judge this appeal objectively on THREE criteria:

1. VIOLATION CHECK: Based on the published rule text, did the content actually violate the specific rule? Quote the exact rule clause you are applying (2-3 sentences max per clause).
2. PROPORTIONALITY: Even if a minor violation occurred, is "{action}" a proportional penalty, or should it be reduced to a lower tier (warning, label, or demonetization)?
3. INCONSISTENCY / BIAS FLAGS: Does the content resemble common protected discourse on this platform? Are there signs of arbitrary or selective moderation?

RESPOND WITH ONLY VALID JSON (no markdown code fence):
{{
  "verdict": "UPHOLD_BAN" | "OVERTURN" | "REDUCE_SEVERITY",
  "confidence": 0-100,
  "reason": "3-5 sentence rationale referencing specific rule clauses and content",
  "rule_clauses_cited": ["exact rule clause 1", "exact rule clause 2"],
  "suggested_lower_action": "" | "WARNING" | "LABEL" | "DEMONETIZE" | "AGE_RESTRICT"
}}
"""
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            return raw

        def validator_fn(leader_res) -> bool:
            """
            CONSENSUS RULE: Validator compares VERDICT (semantic judgment: OVERTURN vs UPHOLD_BAN vs REDUCE_SEVERITY).
            Stylistic variance in reason text or rule clause citation is intentionally permitted across validators.
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
        verdict = str(result.get("verdict", "UPHOLD_BAN")).upper()
        if verdict not in ["OVERTURN", "REDUCE_SEVERITY", "UPHOLD_BAN"]:
            verdict = "UPHOLD_BAN"

        reason = str(result.get("reason", "Appeal reviewed by decentralized AI jury."))
        confidence = int(result.get("confidence", 70))
        clauses = result.get("rule_clauses_cited", [])
        if not isinstance(clauses, list):
            clauses = []

        # Confidence < 55 -> auto-escalate to En Banc
        if confidence < 55:
            case.state = "EN_BANC_REQUESTED"
            case.verdict = verdict
            case.reason = f"Low confidence ({confidence}%). Auto-escalated for full-court En Banc appellate review. {reason}"
            case.confidence = u8(max(0, min(100, confidence)))
            case.rule_clauses_cited = [str(c) for c in clauses[:5]]
            return

        case.verdict = verdict
        case.reason = reason
        case.confidence = u8(max(0, min(100, confidence)))
        case.rule_clauses_cited = [str(c) for c in clauses[:5]]
        case.state = "RULED"
        case.ruled_at_epoch = _now_epoch()

        self._settle_stake_and_report(case_id, verdict)

    def _settle_stake_and_report(self, case_id: str, verdict: str) -> None:
        case = self.cases[case_id]
        case.verdict = verdict

        if verdict == "OVERTURN":
            # 100% refund of stake to appellant - atomic, no silent error suppression
            gl.get_contract_at(Address(case.appellant)).emit_transfer(
                value=u256(int(case.stake))
            )
            rep_label = "WIN"
        elif verdict == "REDUCE_SEVERITY":
            # 50% partial refund of stake
            half = int(case.stake) // 2
            gl.get_contract_at(Address(case.appellant)).emit_transfer(
                value=u256(half)
            )
            rep_label = "PARTIAL"
        else:
            # UPHOLD_BAN -> stake forfeited
            rep_label = "LOSS"

        # Record verdict on CreatorReputation
        if self.reputation_contract:
            rep = gl.get_contract_at(self.reputation_contract)
            rep.emit().record_verdict(case.appellant, case.platform, rep_label)

        case.state = "FINAL"

    @gl.public.write
    def notify_en_banc_requested(self, case_id: str) -> None:
        sender_str = _addr_str(gl.message.sender_address)
        is_eb = (
            self.en_banc_contract
            and sender_str.lower() == _addr_str(self.en_banc_contract).lower()
        )
        if not is_eb and gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only En Banc contract can notify")
        if case_id not in self.cases:
            raise gl.vm.UserError("Case not found")
        case = self.cases[case_id]
        if case.state not in ["RULED", "FINAL", "EN_BANC_REQUESTED"]:
            raise gl.vm.UserError("Case not eligible for En Banc review")
        case.state = "EN_BANC_REQUESTED"

    @gl.public.write.payable
    def request_en_banc(
        self,
        case_id: str,
        extra_urls: DynArray[str],
        statement: str,
    ) -> None:
        if case_id not in self.cases:
            raise gl.vm.UserError("Case not found")
        case = self.cases[case_id]
        if case.state not in ["RULED", "FINAL", "EN_BANC_REQUESTED"]:
            raise gl.vm.UserError("Cannot appeal an unruled case")

        if not self.en_banc_contract:
            raise gl.vm.UserError("En Banc contract not configured")

        required_stake = int(case.stake) * 2
        if int(gl.message.value) < required_stake:
            raise gl.vm.UserError("En Banc review requires double the original stake")

        case.state = "EN_BANC_REQUESTED"

        # Delegate execution to EnBanc contract
        eb = gl.get_contract_at(self.en_banc_contract)
        eb.emit(value=u256(int(gl.message.value))).request_review(
            case_id, extra_urls, statement, case.verdict
        )

    @gl.public.write
    def settle_from_en_banc(
        self,
        case_id: str,
        verdict: str,
        reason: str,
        confidence: int,
    ) -> None:
        sender_str = _addr_str(gl.message.sender_address)
        is_eb = (
            self.en_banc_contract
            and sender_str.lower() == _addr_str(self.en_banc_contract).lower()
        )
        if not is_eb and gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only En Banc contract can settle appeal from review")

        if case_id not in self.cases:
            raise gl.vm.UserError("Case not found")

        case = self.cases[case_id]
        old_verdict = case.verdict

        # If verdict was overturned or reduced in En Banc, settle stake first
        if old_verdict == "UPHOLD_BAN" and verdict in ["OVERTURN", "REDUCE_SEVERITY"]:
            if verdict == "OVERTURN":
                gl.get_contract_at(Address(case.appellant)).emit_transfer(
                    value=u256(int(case.stake))
                )
            elif verdict == "REDUCE_SEVERITY":
                half = int(case.stake) // 2
                gl.get_contract_at(Address(case.appellant)).emit_transfer(
                    value=u256(half)
                )

        case.verdict = verdict
        case.reason = f"[En Banc Appellate Review]: {reason}"
        case.confidence = u8(max(0, min(100, confidence)))
        case.state = "FINAL"
        case.ruled_at_epoch = _now_epoch()

    @gl.public.write
    def admin_seed_case(
        self,
        appellant: str,
        platform: str,
        action_taken: str,
        rule_url: str,
        content_url: str,
        content_quote: str,
        explanation: str,
        stake: int,
        state: str,
        verdict: str,
        reason: str,
        rule_clauses_cited: DynArray[str],
        confidence: int,
    ) -> str:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only admin can seed demo cases")

        case_id_int = int(self.next_id)
        self.next_id = bigint(case_id_int + 1)
        case_id_str = str(case_id_int)

        actual_stake = stake * (10**18) if stake < 10**15 else stake
        new_case = Case(
            appellant=appellant,
            platform=platform,
            action_taken=action_taken,
            rule_url=rule_url,
            content_url=content_url,
            content_quote=content_quote,
            explanation=explanation,
            stake=bigint(actual_stake),
            state=state,
            verdict=verdict,
            reason=reason,
            rule_clauses_cited=rule_clauses_cited,
            confidence=u8(confidence),
            en_banc_contract=_addr_str(self.en_banc_contract),
            reputation_contract=_addr_str(self.reputation_contract),
            created_at_epoch=_now_epoch(),
            ruled_at_epoch=_now_epoch(),
        )
        self.cases[case_id_str] = new_case

        # Update reputation if settled
        if verdict and self.reputation_contract:
            try:
                rep = gl.get_contract_at(self.reputation_contract)
                if verdict == "OVERTURN":
                    rep.record_verdict(args=[appellant, platform, "WIN"])
                elif verdict == "REDUCE_SEVERITY":
                    rep.record_verdict(args=[appellant, platform, "PARTIAL"])
                elif verdict == "UPHOLD_BAN":
                    rep.record_verdict(args=[appellant, platform, "LOSS"])
            except Exception:
                pass

        return case_id_str

    @gl.public.view
    def get_case(self, case_id: str) -> str:
        if case_id not in self.cases:
            raise gl.vm.UserError("Case not found")
        c = self.cases[case_id]
        data = {
            "case_id": case_id,
            "appellant": c.appellant,
            "platform": c.platform,
            "action_taken": c.action_taken,
            "rule_url": c.rule_url,
            "content_url": c.content_url,
            "content_quote": c.content_quote,
            "explanation": c.explanation,
            "stake": str(c.stake),
            "state": c.state,
            "verdict": c.verdict,
            "reason": c.reason,
            "rule_clauses_cited": list(c.rule_clauses_cited),
            "confidence": int(c.confidence),
            "en_banc_contract": c.en_banc_contract,
            "reputation_contract": c.reputation_contract,
            "created_at_epoch": int(c.created_at_epoch),
            "ruled_at_epoch": int(c.ruled_at_epoch),
        }
        return json.dumps(data)

    @gl.public.view
    def get_case_count(self) -> u256:
        return u256(int(self.next_id) - 1)

    @gl.public.view
    def list_cases(
        self,
        platform_filter: str,
        state_filter: str,
        offset: int,
        limit: int,
    ) -> str:
        total = int(self.next_id) - 1
        results = []
        plat_clean = platform_filter.strip()
        state_clean = state_filter.strip().upper()

        start = max(1, offset + 1)
        end = min(total + 1, start + limit)

        for i in range(start, end):
            key = str(i)
            if key in self.cases:
                c = self.cases[key]
                match_plat = not plat_clean or plat_clean == "ALL" or c.platform == plat_clean
                match_state = not state_clean or state_clean == "ALL" or c.state == state_clean
                if match_plat and match_state:
                    results.append({
                        "case_id": key,
                        "appellant": c.appellant,
                        "platform": c.platform,
                        "action_taken": c.action_taken,
                        "rule_url": c.rule_url,
                        "content_url": c.content_url,
                        "stake": str(c.stake),
                        "state": c.state,
                        "verdict": c.verdict,
                        "confidence": int(c.confidence),
                        "created_at_epoch": int(c.created_at_epoch),
                    })
        return json.dumps(results)

    @gl.public.view
    def stats(self) -> str:
        total = int(self.next_id) - 1
        overturn_cnt = 0
        uphold_cnt = 0
        reduce_cnt = 0
        en_banc_cnt = 0
        conf_sum = 0
        ruled_cnt = 0

        for i in range(1, total + 1):
            key = str(i)
            if key in self.cases:
                c = self.cases[key]
                if c.verdict == "OVERTURN":
                    overturn_cnt += 1
                elif c.verdict == "UPHOLD_BAN":
                    uphold_cnt += 1
                elif c.verdict == "REDUCE_SEVERITY":
                    reduce_cnt += 1

                if c.state == "EN_BANC_REQUESTED":
                    en_banc_cnt += 1

                if int(c.confidence) > 0:
                    conf_sum += int(c.confidence)
                    ruled_cnt += 1

        mean_conf = (conf_sum // ruled_cnt) if ruled_cnt > 0 else 0

        data = {
            "total_cases": total,
            "overturn_count": overturn_cnt,
            "uphold_count": uphold_cnt,
            "reduce_count": reduce_cnt,
            "en_banc_count": en_banc_cnt,
            "mean_confidence": mean_conf,
        }
        return json.dumps(data)
