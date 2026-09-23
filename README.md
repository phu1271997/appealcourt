# ⚖️ AppealCourt — Decentralized Content Moderation Tribunal

> A decentralized appeal court on **GenLayer Studionet** where creators facing bans, demonetization, strikes, or takedowns on YouTube, X, Reddit, Substack, and TikTok stake native `GEN` for an on-chain AI jury to read published platform rules and contested content, ruling whether penalties should be overturned with specific rule clause citations.

---

## 1. Problem Statement
Content moderation across major Web2 platforms operates as an opaque, unaccountable black box:
- **Zero Transparency:** Creators are rarely informed which exact clause or sentence triggered an enforcement action.
- **Internal Kangaroo Courts:** Moderation appeals are resolved internally by single contractors or uncalibrated ML filters with zero binding deadlines or public accountability.
- **No Independent Second Opinion:** Creators operate in a digital feudal state with no recourse for neutral adjudication.
- **Arbitrary & Selective Enforcement:** Boundary discourse (investigative journalism, public health discussions, controversial political critique) is disproportionately penalized depending on geography and external advertiser pressure.

**AppealCourt** establishes an open, objective third-party tribunal:
Creators submit the published platform rule URL, the content URL (or archival mirror), a verbatim quote, an explanation, and a refundable `GEN` stake. An on-chain AI jury renders an immutable ruling evaluating violation, proportionality, and selective bias, producing an on-chain evidentiary record citing the exact rule clauses applied.

---

## 2. Why GenLayer is Strictly Required
Without GenLayer, this protocol is mathematically impossible:
- **On-Chain Web Ingestion (`web.render`):** The contract directly fetches and interprets natural language text from live community guidelines and contested content. Traditional smart contract blockchains (Solidity/EVM) require brittle oracles that cannot parse unstructured human language.
- **Subjective Natural Language Consensus (`exec_prompt`):** Evaluating whether a paragraph breaches a harassment guideline or constitutes protected transformative fair-use requires semantic understanding that cannot be encoded in deterministic boolean statements.
- **Multi-Validator Consensus with Semantic Agreement:** GenLayer's non-deterministic execution model ensures multiple independent validators verify the ultimate judicial **VERDICT** (`OVERTURN`, `REDUCE_SEVERITY`, `UPHOLD_BAN`), preventing single-model bias.
- **Immutable On-Chain Evidence:** Creators receive an immutable, cryptographic record on GenLayer Studionet to cite in public appeals or formal communications.

---

## 3. Architecture & Authority Model

AppealCourt consists of three interconnected Intelligent Contracts:

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

1. **`AppealCase` (`contracts/appeal_case.py`):**
   - Ingests dispute parameters and locks `min_stake` (1,000 GEN).
   - Executes `gl.nondet.web.render` on rule and content URLs.
   - AI jury evaluates **Violation**, **Proportionality**, and **Consistency/Bias**.
   - Validators compare semantic `VERDICT` (`OVERTURN`, `REDUCE_SEVERITY`, `UPHOLD_BAN`).
   - Settle funds: `OVERTURN` (100% refund), `REDUCE_SEVERITY` (50% refund), `UPHOLD_BAN` (forfeited).
   - Auto-escalates if jury confidence is below 55%.

2. **`EnBanc` (`contracts/en_banc.py`):**
   - Full-court appellate tribunal reading 1–3 additional cross-check URLs (platform Terms of Service, Help Center precedents, policy FAQs).
   - Requires double stake (`stake * 2`), refunded upon reversal.
   - Callback to `AppealCase.settle_from_en_banc` to update case status and creator standing.

3. **`CreatorReputation` (`contracts/creator_reputation.py`):**
   - Persistent on-chain ledger recording creator wins, losses, partial refunds, and En Banc victories.
   - Issues merit badges: `First Appeal`, `Vindicated`, `Serial Appellant`, `Champion`, `Cross-Platform`, and `Persistent`.

---

## 4. Deploying to Studionet Step-by-Step

### Prerequisites
- Python 3.11+
- Installed `genlayer-py` and `gltest`
- Funded private key in `~/.genlayer/env.sh`

### Step 1: Fund Your Account
Open the [GenLayer Studio Accounts Panel](https://studio.genlayer.com) and transfer native `GEN` from a pre-funded studio account to your address (`0x8b563A8c9eeF530300e92E26457D1AB001daEcC7`). **Do NOT use the public testnet faucet.**

### Step 2: Deploy Contracts
```bash
source ~/.genlayer/env.sh
python3 scripts/deploy_studionet.py
```
This script validates contract schemas, deploys `CreatorReputation`, `EnBanc`, and `AppealCase`, authorizes cross-contract calls, and writes `deployments.json` and `frontend/.env`.

### Step 3: Seed Demo Data
```bash
python3 scripts/seed_demo_data.py
```
Seeds 4 comprehensive real-world cases on-chain (YouTube, X, Reddit, Substack En Banc).

---

## 5. Running the Frontend Locally

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5174` in your browser.

---

## 6. Live Application URL
- **Production Web Application:** [https://appealcourt.vercel.app](https://appealcourt.vercel.app) *(or active Vercel alias)*
- Compatible with desktop and mobile MetaMask. Full anonymous browsing supported without wallet connection.

---

## 7. Video Demonstration
- **Walkthrough Video:** *[Demo video link to be attached]*

---

## 8. Deployed Contract Addresses (GenLayer Studionet — Chain ID 61999)

| Contract | Address | Explorer Link |
|---|---|---|
| **AppealCase** | `0xb727deE03260539af5D35F214c0671Ea6C5a5f8B` | [View on Explorer](https://genlayer-explorer.vercel.app/address/0xb727deE03260539af5D35F214c0671Ea6C5a5f8B) |
| **EnBanc** | `0x3C89E1aBDEADf87a344434dd45B2Ac062A59f4d0` | [View on Explorer](https://genlayer-explorer.vercel.app/address/0x3C89E1aBDEADf87a344434dd45B2Ac062A59f4d0) |
| **CreatorReputation** | `0x79Bc835E8354820868396e06cA5e529Bb6b83779` | [View on Explorer](https://genlayer-explorer.vercel.app/address/0x79Bc835E8354820868396e06cA5e529Bb6b83779) |

- **Deployer Wallet:** `0x8b563A8c9eeF530300e92E26457D1AB001daEcC7`
- **RPC Endpoint:** `https://studio.genlayer.com/api`

---

## 9. Sample Cases for Reviewers
See [SAMPLE_CASES.md](./SAMPLE_CASES.md) for 4 verified permanent URLs ready to test:
1. **YouTube Demonetization:** Fair-use educational documentary (Section 3.2 exemption) &rarr; `OVERTURN`
2. **X Account Suspension:** Breaking news research desk flagged for manipulation &rarr; `REDUCE_SEVERITY`
3. **Reddit Community Ban:** Residential address leak confirmed &rarr; `UPHOLD_BAN`
4. **Substack Investigative Journalism:** Full-court En Banc review citing Terms §4 public interest doctrine &rarr; `REVERSED (OVERTURN)`

---

## 10. Legal & Operational Disclaimer
AppealCourt is an independent, decentralized adjudication protocol. The protocol **does NOT claim legal authority to compel private platforms to restore user accounts or remove strikes**. Rather, AppealCourt provides an immutable, decentralized, third-party evidentiary record proving whether an action complied with published community standards. Creators may use these cryptographic certificates in formal appeals, arbitration, or public advocacy.
