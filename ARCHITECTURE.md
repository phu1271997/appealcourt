# AppealCourt System Architecture

AppealCourt is a decentralized content moderation adjudication protocol built on GenLayer Intelligent Contracts. It provides an objective, immutable on-chain tribunal where creators facing opaque platform penalties (takedowns, demonetization, strikes, bans) can stake native tokens (`GEN`) for an AI jury consensus review that reads live platform guidelines and published content on-chain.

---

## 1. Multi-Contract System Topology

```mermaid
flowchart TD
    subgraph Client Layer
        User["Creator / Appellant"]
        MetaMask["MetaMask (Studionet 61999)"]
        UI["AppealCourt Web App (React + Vite)"]
    end

    subgraph GenLayer Intelligent Contracts
        AC["AppealCase Contract\n- Dispute Intake\n- Non-det Web Reading\n- AI Jury Consensus\n- Stake Settlement"]
        EB["EnBanc Contract\n- Appellate Tribunal\n- Multi-Source Cross-Check (3+ URLs)\n- Reversal & Remand"]
        CR["CreatorReputation Contract\n- Win / Loss / Partial Ledger\n- Merit Badges\n- Cross-Platform Index"]
    end

    subgraph External Public Web
        RuleURL["Platform Guidelines\n(Google/X/Reddit/Substack)"]
        ContentURL["Disputed Content\n(Archive.org / Live Web)"]
        CrossCheckURLs["Cross-Check Evidence\n(Help Center / Precedents)"]
    end

    User -->|Connect & Sign| MetaMask
    MetaMask -->|EIP-1193 JSON-RPC| UI
    UI -->|file_appeal / request_en_banc| AC
    AC -->|gl.nondet.web.render| RuleURL
    AC -->|gl.nondet.web.render| ContentURL
    AC -->|Escalate / Forward| EB
    EB -->|gl.nondet.web.render| CrossCheckURLs
    EB -->|settle_from_en_banc callback| AC
    AC -->|record_verdict| CR
    EB -->|record_verdict| CR
```

---

## 2. Adjudication State Machine

```mermaid
stateDiagram-v2
    [*] --> OPEN: file_appeal() + Stake (>= 1000 GEN)
    OPEN --> UNDER_REVIEW: Initiated by Consensus Leader
    UNDER_REVIEW --> RULED: AI Jury Consensus Reached (Confidence >= 55)
    UNDER_REVIEW --> EN_BANC_REQUESTED: Low Jury Confidence (Confidence < 55)
    
    RULED --> FINAL: Stake Settled (OVERTURN refund 100%, REDUCE 50%, UPHOLD 0%)
    RULED --> EN_BANC_REQUESTED: Appellant Files Appeal within Window (Double Stake)
    
    EN_BANC_REQUESTED --> PENDING_REVIEW: EnBanc.request_review()
    PENDING_REVIEW --> FINAL: En Banc Multi-Source Ruling (REVERSE or UPHOLD)
    FINAL --> [*]
```

---

## 3. Decision Tree: Non-Deterministic AI Jury Adjudication

```mermaid
flowchart TD
    Start["Dispute Ingested (rule_url, content_url, explanation, quote)"] --> FetchWeb["Leader fetches rule_url & content_url via gl.nondet.web.render"]
    
    FetchWeb --> CheckWeb{"Did fetches succeed?"}
    CheckWeb -->|Both Failed & No Quote| Err["UserError: Both URLs unreachable"]
    CheckWeb -->|Partial Success / Quote Available| Eval3["Evaluate 3 Core Judicial Checkpoints"]
    
    subgraph "Three Judicial Criteria"
        Eval3 --> C1["1. Violation Check: Direct quote from rule clause"]
        Eval3 --> C2["2. Proportionality: Is sanction excessive?"]
        Eval3 --> C3["3. Bias / Inconsistency: Selective enforcement flags"]
    end
    
    C1 & C2 & C3 --> ConsensusCheck["Validators evaluate: mine.verdict == leader.verdict"]
    
    ConsensusCheck -->|Consensus Formed| ConfidenceCheck{"Jury Confidence Level"}
    ConfidenceCheck -->|Confidence < 55%| AutoEscalate["State = EN_BANC_REQUESTED\nTrigger Appellate Review"]
    ConfidenceCheck -->|Confidence >= 55%| ApplyVerdict{"Verdict Formulation"}
    
    ApplyVerdict -->|OVERTURN| Win["100% Stake Refunded\nReputation: WIN (+1)"]
    ApplyVerdict -->|REDUCE_SEVERITY| Partial["50% Stake Refunded\nReputation: PARTIAL (+1)"]
    ApplyVerdict -->|UPHOLD_BAN| Loss["Stake Forfeited to Protocol\nReputation: LOSS (+1)"]
```

---

## 4. Contract Authority & Security Model

| Contract | State Mutation Method | Access Control / Authority |
|---|---|---|
| `CreatorReputation` | `set_authorized(caller, allowed)` | Only Admin |
| `CreatorReputation` | `record_verdict(appellant, platform, result)` | Only Authorized Contracts (`AppealCase`, `EnBanc`) or Admin |
| `EnBanc` | `set_dependencies(appeal_case, rep_contract)` | Only Admin |
| `EnBanc` | `request_review(...)` | Public Payable (requires `stake * 2`) |
| `EnBanc` | `admin_seed_review(...)` | Only Admin |
| `AppealCase` | `set_dependencies(en_banc, rep_contract)` | Only Admin |
| `AppealCase` | `file_appeal(...)` | Public Payable (requires `msg.value >= min_stake`, https URLs) |
| `AppealCase` | `request_en_banc(...)` | Public Payable (requires double stake) |
| `AppealCase` | `settle_from_en_banc(...)` | Only `EnBanc` Contract or Admin |
| `AppealCase` | `admin_seed_case(...)` | Only Admin |

---

## 5. Storage Optimization & GenVM Type Safety

- **Storage Layout:** All dynamic mappings utilize `TreeMap[str, T]` with strictly stringified keys (`appellant_addr`, `case_id`).
- **Numeric Precision:** Monetary stakes utilize native `bigint` to prevent numeric overflow. Bounded counters and metrics (`round`, `confidence`) use sized types (`u8`, `u256`).
- **Zero Raw Primitives in Storage:** Storage classes (`Case`, `EnBancReview`) are decorated with `@allow_storage @dataclass`. Bare `int`, `dict`, and `list` are completely prohibited within contract storage fields.
