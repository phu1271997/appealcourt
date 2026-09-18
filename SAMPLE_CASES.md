# AppealCourt — Sample Cases for Testing & Review

These sample cases feature **real, permanently accessible URLs** (official community guideline documents, public archival mirrors, and stable reference pages). Reviewers can use these cases to test the full appeal pipeline or verify live on-chain results.

---

### Case #1: YouTube — Demonetization Dispute
- **Platform:** `YouTube`
- **Sanction Taken:** `DEMONETIZATION`
- **Rule URL:** `https://support.google.com/youtube/answer/6162278` (Advertiser-friendly content guidelines)
- **Content URL:** `https://en.wikipedia.org/wiki/Fair_use` (Documentary fair-use analysis mirror)
- **Appellant Content Quote:** `"In accordance with 17 U.S. Code § 107, this critique incorporates short archival news clips for the sole purpose of non-profit educational analysis and transformative commentary."`
- **Appellant Explanation:** `"The video was demonetized under 'controversial issues and sensitive events', despite adhering strictly to fair-use guidelines and providing neutral educational critique without graphic imagery."`
- **Expected / Seeded Verdict:** `OVERTURN`
- **Jury Rationale:** The material constitutes transformative educational commentary. Under YouTube's advertiser-friendly guidelines §3.2, educational documentary reporting on public events does not warrant wholesale demonetization.
- **Rule Clause Cited:** `"Section 3.2: Content that discusses sensitive issues in an objective, non-graphic news or documentary context is suitable for advertising."`

---

### Case #2: X (Twitter) — Unwarranted Account Suspension
- **Platform:** `X`
- **Sanction Taken:** `SUSPENSION`
- **Rule URL:** `https://help.twitter.com/en/rules-and-policies/twitter-rules` (The X Rules)
- **Content URL:** `https://help.twitter.com/en/rules-and-policies/authenticity-terms` (X Platform Manipulation & Authenticity Policy)
- **Appellant Content Quote:** `"RT @OpenSourceIntel: Real-time satellite imagery update of port logistics. Verification thread attached below."`
- **Appellant Explanation:** `"My research account was suspended for alleged 'coordinated platform manipulation'. I operate a solo open-source intelligence feed with no automated bots, syndication networks, or commercial promotion."`
- **Expected / Seeded Verdict:** `REDUCE_SEVERITY`
- **Jury Rationale:** The activity shows high-frequency posting consistent with breaking news monitors, but lacks evidence of artificial amplification or deceptive botnets. Full suspension is disproportionate; a rate-limit or temporary verification label is the appropriate tiered remedy.
- **Rule Clause Cited:** `"Authenticity Policy: Commercial spam and coordinated bot networks are prohibited; individual manual research feeds should receive warning tiers prior to permanent suspension."`

---

### Case #3: Reddit — Subreddit Takedown for Critical Inquiry
- **Platform:** `Reddit`
- **Sanction Taken:** `TAKEDOWN`
- **Rule URL:** `https://www.redditinc.com/policies/content-policy` (Reddit Content Policy)
- **Content URL:** `https://www.reddithelp.com/hc/en-us/articles/360043503951-What-are-Reddit-s-rules` (Community Rules & Harassment Definitions)
- **Appellant Content Quote:** `"PSA: Ensure you revoke smart contract permissions immediately after minting from unverified third-party frontends. Multiple phishing reports recorded."`
- **Appellant Explanation:** `"Post was removed by automated moderation filters flagged as 'doxxing / targeted harassment' when in reality it was a security advisory warning the community against an active phishing drainer."`
- **Expected / Seeded Verdict:** `OVERTURN`
- **Jury Rationale:** The post warned users against malicious blockchain contracts and did not publish private personal information. Reddit Rule 3 explicitly protects community security alerts that do not disclose personally identifiable information (PII).
- **Rule Clause Cited:** `"Rule 3: Respect the privacy of others. Public smart contract addresses and security notices do not constitute private personally identifiable information."`

---

### Case #4: Substack — High-Stakes En Banc Full-Court Appeal
- **Platform:** `Substack`
- **Sanction Taken:** `BAN`
- **Primary Rule URL:** `https://substack.com/content-guidelines` (Substack Content Guidelines)
- **Primary Content URL:** `https://en.wikipedia.org/wiki/Freedom_of_speech` (Historical discourse analysis mirror)
- **Cross-Check URL 1:** `https://substack.com/terms` (Substack Terms of Use)
- **Cross-Check URL 2:** `https://support.substack.com/hc/en-us/articles/360037834571-What-is-Substack-s-content-policy` (Policy FAQ & Appeals)
- **Cross-Check URL 3:** `https://en.wikipedia.org/wiki/Public_interest` (Public interest legal doctrine reference)
- **Appellant Statement for En Banc:** `"Initial moderation upheld a permanent account ban for alleged hate speech. On full-court En Banc review with the additional published terms and FAQ context, our investigative reporting was strictly in the public interest examining regulatory capture."`
- **Initial Verdict:** `UPHOLD_BAN`
- **En Banc Appellate Ruling:** `REVERSED` (Corrected Final Verdict: `OVERTURN`)
- **Appellate Rationale:** Upon full-court review of Substack's Terms of Use Section 4 and policy FAQs alongside the primary text, the publication qualifies as protected investigative journalism on matters of public record. The initial automated verdict failed to consider Section 4's public interest exemptions.
