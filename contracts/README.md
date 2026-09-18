# AppealCourt Contracts

This directory contains the Intelligent Contracts powering **AppealCourt** on GenLayer Studionet.

## Contract Architecture

```
                       +-------------------------+
                       |       AppealCase        |
                       | (Core Dispute Tribunal) |
                       +------------+------------+
                                    |
          +-------------------------+-------------------------+
          | (On Appeal Escalation)                            | (Record Verdict)
          v                                                   v
+-------------------------+                       +-------------------------+
|         EnBanc          |                       |    CreatorReputation    |
| (Full-Court Cross-Check)|---------------------->| (Wins, Losses, Badges)  |
+-------------------------+  (En Banc Verdict)    +-------------------------+
```

### 1. `AppealCase` (`contracts/appeal_case.py`)
- **Role:** Primary intake and initial adjudication tribunal.
- **Workflow:**
  1. Creator stakes native `GEN` (>= 1,000 GEN) and files an appeal (`file_appeal`) with platform name, sanction type, public rule URL, and content URL.
  2. Runs GenLayer non-deterministic consensus (`gl.vm.run_nondet`):
     - Leader reads both the published platform guidelines and the flagged content on-chain using `gl.nondet.web.render`.
     - AI jury evaluates 3 core criteria:
       - **Violation Check:** Quotes exact rule clauses.
       - **Proportionality:** Evaluates whether the sanction fits or requires a lesser penalty.
       - **Consistency / Bias:** Assesses selective enforcement against typical platform norms.
     - Semantic consensus: Validators evaluate agreement on the ultimate `VERDICT` (`OVERTURN`, `REDUCE_SEVERITY`, `UPHOLD_BAN`).
  3. **Settlement:**
     - `OVERTURN`: 100% stake refunded to appellant; reported as `WIN`.
     - `REDUCE_SEVERITY`: 50% partial refund; reported as `PARTIAL`.
     - `UPHOLD_BAN`: Stake forfeited; reported as `LOSS`.
  4. **Auto-Escalation:** If jury confidence is below 55%, the case state transitions to `EN_BANC_REQUESTED`.

### 2. `EnBanc` (`contracts/en_banc.py`)
- **Role:** Full-court appellate review for contested or low-confidence rulings.
- **Multi-Source Cross-Check:**
  - In addition to original rule and content URLs, En Banc fetches 1–3 external cross-check URLs (e.g., official help center articles, similar precedent rulings, transparency reports).
  - Enhanced jury prompt conducts a rigorous appellate examination.
  - Verdicts: `UPHOLD` (affirm original penalty) or `REVERSE` (overturn or reduce severity).
  - On `REVERSE`: Refunds appellant's double stake and calls back to `AppealCase.settle_from_en_banc` to update on-chain status and credit creator reputation.

### 3. `CreatorReputation` (`contracts/creator_reputation.py`)
- **Role:** Immutable on-chain track record of creator dispute resolution.
- **Badges:**
  - **First Appeal:** Creator filed 1+ formal appeal.
  - **Vindicated:** Overturned an unfair ban (`OVERTURN`).
  - **Serial Appellant:** Defended content rights across 5+ actions.
  - **Champion:** Successfully overturned 10+ unfair penalties.
  - **Cross-Platform:** Defended rights across 3+ distinct platforms.
  - **Persistent:** Successfully overturned a penalty through full-court En Banc review.
