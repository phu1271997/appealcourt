import { useState, useEffect } from 'react';
import { getGenLayerClient } from './lib/client';
import { connectWallet } from './lib/wallet';
import {
  APPEAL_CASE_ADDRESS,
  EN_BANC_ADDRESS,
  REPUTATION_ADDRESS,
} from './lib/addresses';
import {
  Scale,
  ShieldAlert,
  FileCheck,
  AlertOctagon,
  ExternalLink,
  PlusCircle,
  Award,
  ChevronRight,
  Info,
  Clock,
  Sparkles,
  Search,
  Filter,
  RefreshCw,
  Landmark,
  Gavel,
  BookOpen,
} from 'lucide-react';

interface CaseSummary {
  case_id: string;
  appellant: string;
  platform: string;
  action_taken: string;
  rule_url: string;
  content_url: string;
  stake: string;
  state: string;
  verdict: string;
  confidence: number;
  created_at_epoch: number;
}

interface CaseDetail extends CaseSummary {
  content_quote: string;
  explanation: string;
  reason: string;
  rule_clauses_cited: string[];
  en_banc_contract: string;
  reputation_contract: string;
  ruled_at_epoch: number;
}

interface EnBancReviewDetail {
  review_id: string;
  case_id: string;
  appellant: string;
  original_platform: string;
  original_action: string;
  original_rule_url: string;
  original_content_url: string;
  original_verdict: string;
  extra_urls: string[];
  request_statement: string;
  stake: string;
  state: string;
  verdict: string;
  new_appeal_verdict: string;
  reason: string;
  confidence: number;
  created_at_epoch: number;
  ruled_at_epoch: number;
}

interface BadgeItem {
  id: string;
  name: string;
  description: string;
}

interface CreatorReputationData {
  appellant: string;
  wins: number;
  losses: number;
  partials: number;
  en_banc_wins: number;
  total_appeals: number;
  platforms: string[];
  badges: BadgeItem[];
}

interface StatsData {
  total_cases: number;
  overturn_count: number;
  uphold_count: number;
  reduce_count: number;
  en_banc_count: number;
  mean_confidence: number;
}

const PLATFORMS = ['All', 'YouTube', 'X', 'Reddit', 'Substack', 'TikTok', 'Twitch', 'Other'];
const ACTIONS = ['TAKEDOWN', 'DEMONETIZATION', 'SHADOWBAN', 'STRIKE', 'SUSPENSION', 'BAN'];

const WEI_PER_GEN = 1000000000000000000n; // 10^18

function parseGen(amount: string | number): bigint {
  const val = String(amount).trim();
  if (!val) return 1000n * WEI_PER_GEN;
  const [whole, frac = ''] = val.split('.');
  const fracPad = frac.padEnd(18, '0').slice(0, 18);
  return BigInt(whole) * WEI_PER_GEN + BigInt(fracPad);
}

function formatGen(baseUnits: string | bigint | number): string {
  try {
    const b = BigInt(baseUnits);
    if (b < 1000000000000000n) {
      return b.toLocaleString();
    }
    const whole = b / WEI_PER_GEN;
    const remainder = b % WEI_PER_GEN;
    if (remainder === 0n) {
      return whole.toLocaleString();
    }
    const dec = (remainder / 100000000000000n).toString().padStart(4, '0');
    return `${whole.toLocaleString()}.${dec.replace(/0+$/, '')}`;
  } catch {
    return String(baseUnits);
  }
}

export default function App() {
  const [account, setAccount] = useState<string | null>(null);
  const [balance, setBalance] = useState<string>('0');
  const [activeTab, setActiveTab] = useState<'browse' | 'wizard' | 'stats' | 'reputation'>('browse');

  // Case lists & selection
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseDetail | null>(null);
  const [selectedEnBanc, setSelectedEnBanc] = useState<EnBancReviewDetail | null>(null);
  const [platformFilter, setPlatformFilter] = useState('All');
  const [verdictFilter, setVerdictFilter] = useState('ALL');

  // Stats & Reputation
  const [stats, setStats] = useState<StatsData | null>(null);
  const [repQuery, setRepQuery] = useState('');
  const [reputation, setReputation] = useState<CreatorReputationData | null>(null);

  // Loading & consensus UX
  const [loading, setLoading] = useState(false);
  const [consensusMsg, setConsensusMsg] = useState<string | null>(null);
  const [lastTxHash, setLastTxHash] = useState<string | null>(null);

  // 3-Step Wizard Form State
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);
  const [formPlatform, setFormPlatform] = useState('YouTube');
  const [formAction, setFormAction] = useState('DEMONETIZATION');
  const [formRuleUrl, setFormRuleUrl] = useState('');
  const [formContentUrl, setFormContentUrl] = useState('');
  const [formQuote, setFormQuote] = useState('');
  const [formExplanation, setFormExplanation] = useState('');
  const [formStake, setFormStake] = useState('1000');

  // En Banc Modal
  const [showEnBancModal, setShowEnBancModal] = useState(false);
  const [enBancUrl1, setEnBancUrl1] = useState('');
  const [enBancUrl2, setEnBancUrl2] = useState('');
  const [enBancStatement, setEnBancStatement] = useState('');

  // Sample Case Loader for Easy Testing
  const loadSampleCase = (type: 'youtube' | 'x' | 'reddit' | 'substack') => {
    setActiveTab('wizard');
    setWizardStep(1);
    if (type === 'youtube') {
      setFormPlatform('YouTube');
      setFormAction('DEMONETIZATION');
      setFormRuleUrl('https://support.google.com/youtube/answer/6162278');
      setFormContentUrl('https://en.wikipedia.org/wiki/Fair_use');
      setFormQuote('In accordance with 17 U.S. Code § 107, this critique incorporates short archival news clips for educational critique.');
      setFormExplanation('Our 40-minute educational documentary was demonetized under sensitive events despite adhering strictly to transformative fair use with zero graphic footage.');
      setFormStake('1000');
    } else if (type === 'x') {
      setFormPlatform('X');
      setFormAction('SUSPENSION');
      setFormRuleUrl('https://help.twitter.com/en/rules-and-policies/twitter-rules');
      setFormContentUrl('https://help.twitter.com/en/rules-and-policies/authenticity-terms');
      setFormQuote('RT @OpenSourceIntel: Real-time satellite imagery update of global shipping lanes. Detailed methodology thread attached.');
      setFormExplanation('Account suspended for platform manipulation. We operate an open research monitoring desk; no botting, commercial spam, or coordinated engagement groups.');
      setFormStake('1000');
    } else if (type === 'reddit') {
      setFormPlatform('Reddit');
      setFormAction('BAN');
      setFormRuleUrl('https://www.redditinc.com/policies/content-policy');
      setFormContentUrl('https://www.reddithelp.com/hc/en-us/articles/360043503951-What-are-Reddit-s-rules');
      setFormQuote('PSA: Ensure you revoke smart contract permissions immediately after minting from unverified third-party frontends. Multiple phishing reports recorded.');
      setFormExplanation('Post was removed by automated moderation filters flagged as doxxing / targeted harassment when in reality it was a security advisory warning the community against an active phishing drainer.');
      setFormStake('1000');
    } else {
      setFormPlatform('Substack');
      setFormAction('BAN');
      setFormRuleUrl('https://substack.com/content-guidelines');
      setFormContentUrl('https://en.wikipedia.org/wiki/Freedom_of_speech');
      setFormQuote('In-depth investigative exposé into pharmaceutical lobbying expenditures across European regulatory bodies.');
      setFormExplanation('Banned for alleged defamatory hate speech. We cited official public registry audits and FOIA records.');
      setFormStake('1000');
    }
  };

  // Wallet Connection
  const handleConnect = async () => {
    try {
      setLoading(true);
      const addr = await connectWallet();
      setAccount(addr);
      setRepQuery(addr);
      fetchBalance(addr);
    } catch (err: any) {
      alert(err.message || 'Failed to connect wallet');
    } finally {
      setLoading(false);
    }
  };

  const fetchBalance = async (addr: string) => {
    try {
      if (typeof window !== 'undefined' && window.ethereum) {
        const res: any = await window.ethereum.request({
          method: 'eth_getBalance',
          params: [addr, 'latest'],
        });
        if (res) {
          const balWei = BigInt(res);
          const balGen = Number(balWei) / 1e18;
          setBalance(balGen.toFixed(2));
        }
      }
    } catch (e) {
      console.error('Balance error:', e);
    }
  };

  // Read Contracts
  const fetchCases = async () => {
    try {
      setLoading(true);
      const client = getGenLayerClient();
      const raw: any = await client.readContract({
        address: APPEAL_CASE_ADDRESS,
        functionName: 'list_cases',
        args: [platformFilter === 'All' ? '' : platformFilter, verdictFilter, 0, 50],
      });
      if (raw) {
        const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
        setCases(parsed || []);
      }
    } catch (e) {
      console.error('Fetch cases error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const client = getGenLayerClient();
      const raw: any = await client.readContract({
        address: APPEAL_CASE_ADDRESS,
        functionName: 'stats',
        args: [],
      });
      if (raw) {
        const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
        setStats(parsed);
      }
    } catch (e) {
      console.error('Fetch stats error:', e);
    }
  };

  const fetchCaseDetail = async (id: string) => {
    try {
      setLoading(true);
      const client = getGenLayerClient();
      const raw: any = await client.readContract({
        address: APPEAL_CASE_ADDRESS,
        functionName: 'get_case',
        args: [id],
      });
      if (raw) {
        const parsed: CaseDetail = typeof raw === 'string' ? JSON.parse(raw) : raw;
        setSelectedCase(parsed);

        // Also check if an En Banc review exists for this case
        try {
          const ebRaw: any = await client.readContract({
            address: EN_BANC_ADDRESS,
            functionName: 'get_review_by_case',
            args: [id],
          });
          if (ebRaw) {
            const ebParsed = typeof ebRaw === 'string' ? JSON.parse(ebRaw) : ebRaw;
            setSelectedEnBanc(ebParsed);
          } else {
            setSelectedEnBanc(null);
          }
        } catch {
          setSelectedEnBanc(null);
        }
      }
    } catch (e) {
      console.error('Fetch case detail error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchReputation = async (addr: string) => {
    if (!addr) return;
    try {
      setLoading(true);
      const client = getGenLayerClient();
      const raw: any = await client.readContract({
        address: REPUTATION_ADDRESS,
        functionName: 'get_creator_reputation',
        args: [addr],
      });
      if (raw) {
        const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
        setReputation(parsed);
      }
    } catch (e) {
      console.error('Fetch reputation error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
    fetchStats();
  }, [platformFilter, verdictFilter]);

  // Submit New Appeal via Wizard
  const handleFileAppeal = async () => {
    if (!account) {
      alert('Please connect your MetaMask wallet first.');
      return;
    }
    if (!formRuleUrl.startsWith('https://') || !formContentUrl.startsWith('https://')) {
      alert('Both Rule URL and Content URL must start with https://');
      return;
    }
    if (!formExplanation.trim()) {
      alert('Please provide an explanation of why the action was unfair.');
      return;
    }

    try {
      setLoading(true);
      setConsensusMsg('AI Jury is reading the platform rule URL and content URL on-chain... (typically 20-40s)');
      const client = getGenLayerClient(account as `0x${string}`);

      const stakeWei = parseGen(formStake || '1000');
      const tx = await client.writeContract({
        address: APPEAL_CASE_ADDRESS,
        functionName: 'file_appeal',
        args: [
          formPlatform,
          formAction,
          formRuleUrl.trim(),
          formContentUrl.trim(),
          formQuote.trim(),
          formExplanation.trim(),
        ],
        value: stakeWei,
      });

      setLastTxHash(tx);
      setConsensusMsg('Consensus reached! Finalizing verdict on GenLayer Studionet...');
      await (client as any).waitForTransactionReceipt({ hash: tx as any });

      alert('Appeal successfully filed and adjudicated by AI jury consensus!');
      setWizardStep(1);
      setActiveTab('browse');
      fetchCases();
      fetchStats();
    } catch (err: any) {
      console.error('File appeal error:', err);
      alert('Transaction failed: ' + (err.message || err));
    } finally {
      setLoading(false);
      setConsensusMsg(null);
    }
  };

  // Petition En Banc Review
  const handleRequestEnBanc = async () => {
    if (!account || !selectedCase) {
      alert('Connect wallet and select a case.');
      return;
    }
    const extraUrls = [enBancUrl1.trim(), enBancUrl2.trim()].filter((u) => u.length > 0);
    if (extraUrls.length === 0) {
      alert('Provide at least 1 cross-check URL (e.g. Terms, Help Center, Precedent).');
      return;
    }
    for (const u of extraUrls) {
      if (!u.startsWith('https://')) {
        alert('All cross-check URLs must start with https://');
        return;
      }
    }
    if (!enBancStatement.trim()) {
      alert('Provide a petition statement explaining why the initial verdict should be reversed.');
      return;
    }

    try {
      setLoading(true);
      setConsensusMsg('En Banc appellate court is reading multi-source cross-check documents... (typically 25-45s)');
      const client = getGenLayerClient(account as `0x${string}`);

      const origStakeWei = selectedCase.stake
        ? BigInt(selectedCase.stake) < 1000000000000000n
          ? BigInt(selectedCase.stake) * WEI_PER_GEN
          : BigInt(selectedCase.stake)
        : 1000n * WEI_PER_GEN;
      const doubleStakeWei = origStakeWei * 2n;

      const tx = await client.writeContract({
        address: EN_BANC_ADDRESS,
        functionName: 'request_review',
        args: [selectedCase.case_id, extraUrls, enBancStatement.trim(), selectedCase.verdict],
        value: doubleStakeWei,
      });

      setLastTxHash(tx);
      await (client as any).waitForTransactionReceipt({ hash: tx as any });

      alert('En Banc appellate review completed on-chain!');
      setShowEnBancModal(false);
      fetchCaseDetail(selectedCase.case_id);
      fetchCases();
      fetchStats();
    } catch (err: any) {
      console.error('En Banc error:', err);
      alert('En Banc petition failed: ' + (err.message || err));
    } finally {
      setLoading(false);
      setConsensusMsg(null);
    }
  };

  // Helper formatting
  const getVerdictBadge = (verdict: string) => {
    if (verdict === 'OVERTURN') {
      return (
        <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full font-semibold text-xs flex items-center gap-1.5">
          <FileCheck className="w-3.5 h-3.5" /> OVERTURN (100% Refund)
        </span>
      );
    }
    if (verdict === 'REDUCE_SEVERITY') {
      return (
        <span className="px-3 py-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-full font-semibold text-xs flex items-center gap-1.5">
          <AlertOctagon className="w-3.5 h-3.5" /> REDUCE SEVERITY (50% Refund)
        </span>
      );
    }
    if (verdict === 'UPHOLD_BAN') {
      return (
        <span className="px-3 py-1 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-full font-semibold text-xs flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5" /> UPHOLD BAN (Forfeited)
        </span>
      );
    }
    return (
      <span className="px-3 py-1 bg-slate-800 text-slate-400 border border-slate-700 rounded-full font-semibold text-xs flex items-center gap-1.5">
        <Clock className="w-3.5 h-3.5" /> PENDING REVIEW
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-[#080b11] text-slate-100 flex flex-col">
      {/* 0 GEN Warning Banner */}
      {account && balance === '0.00' && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 text-amber-300 px-4 py-2.5 text-xs sm:text-sm text-center flex items-center justify-center gap-2">
          <Info className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            Wallet has 0 GEN. Open{' '}
            <a
              href="https://studio.genlayer.com"
              target="_blank"
              rel="noreferrer"
              className="underline font-semibold text-amber-200 hover:text-white"
            >
              Studio &rarr; Accounts panel
            </a>{' '}
            to fund this address from a pre-funded account. Do NOT use the testnet faucet.
          </span>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-slate-800/80 bg-[#0d131f]/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                  AppealCourt
                </span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Studionet 61999
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Decentralized Content Moderation Tribunal on GenLayer
              </p>
            </div>
          </div>

          <nav className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => setActiveTab('browse')}
              className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition ${
                activeTab === 'browse'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              Browse Cases
            </button>
            <button
              onClick={() => setActiveTab('wizard')}
              className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-1.5 ${
                activeTab === 'wizard'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <PlusCircle className="w-3.5 h-3.5" /> File Appeal
            </button>
            <button
              onClick={() => setActiveTab('reputation')}
              className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-1.5 ${
                activeTab === 'reputation'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Award className="w-3.5 h-3.5" /> Creator Badges
            </button>
          </nav>

          <div className="flex items-center gap-3">
            {account ? (
              <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-mono text-slate-300">
                  {account.slice(0, 6)}...{account.slice(-4)}
                </span>
                <span className="text-xs text-indigo-400 font-semibold pl-1 border-l border-slate-700">
                  {balance} GEN
                </span>
              </div>
            ) : (
              <button
                onClick={handleConnect}
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-medium px-4 py-2 rounded-lg transition shadow-md shadow-indigo-600/20"
              >
                Connect Wallet
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Consensus Waiting Modal / Toast */}
      {consensusMsg && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111726] border border-indigo-500/40 rounded-2xl p-6 max-w-md w-full text-center shadow-2xl space-y-4">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 animate-spin">
              <RefreshCw className="w-7 h-7" />
            </div>
            <h3 className="text-lg font-bold text-white">AI Jury In Session</h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {consensusMsg}
            </p>
            <div className="text-[11px] text-slate-500 font-mono">
              Fetching web guidelines & verifying semantic consensus on Studionet
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {lastTxHash && (
          <div className="bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 px-4 py-3 rounded-xl flex items-center justify-between text-xs mb-6">
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              Latest On-Chain Transaction:
              <span className="font-mono text-white">{lastTxHash.slice(0, 10)}...{lastTxHash.slice(-8)}</span>
            </span>
            <a
              href={`https://genlayer-explorer.vercel.app/tx/${lastTxHash}`}
              target="_blank"
              rel="noreferrer"
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3 py-1 rounded-lg flex items-center gap-1 transition"
            >
              View on Explorer <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}

        {/* TAB 1: BROWSE CASES */}
        {activeTab === 'browse' && (
          <div className="space-y-6">
            {/* Top stats bar */}
            {stats && (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="bg-[#111726] border border-slate-800 p-3.5 rounded-xl">
                  <div className="text-xs text-slate-400 font-medium">Total Cases</div>
                  <div className="text-xl font-bold text-white mt-1">{stats.total_cases}</div>
                </div>
                <div className="bg-[#111726] border border-slate-800 p-3.5 rounded-xl">
                  <div className="text-xs text-emerald-400 font-medium">Overturned (Wins)</div>
                  <div className="text-xl font-bold text-emerald-300 mt-1">{stats.overturn_count}</div>
                </div>
                <div className="bg-[#111726] border border-slate-800 p-3.5 rounded-xl">
                  <div className="text-xs text-amber-400 font-medium">Reduced Severity</div>
                  <div className="text-xl font-bold text-amber-300 mt-1">{stats.reduce_count}</div>
                </div>
                <div className="bg-[#111726] border border-slate-800 p-3.5 rounded-xl">
                  <div className="text-xs text-rose-400 font-medium">Upheld Bans</div>
                  <div className="text-xl font-bold text-rose-300 mt-1">{stats.uphold_count}</div>
                </div>
                <div className="bg-[#111726] border border-slate-800 p-3.5 rounded-xl">
                  <div className="text-xs text-purple-400 font-medium">En Banc Reviews</div>
                  <div className="text-xl font-bold text-purple-300 mt-1">{stats.en_banc_count}</div>
                </div>
                <div className="bg-[#111726] border border-slate-800 p-3.5 rounded-xl">
                  <div className="text-xs text-indigo-400 font-medium">Mean Jury Confidence</div>
                  <div className="text-xl font-bold text-indigo-300 mt-1">{stats.mean_confidence}%</div>
                </div>
              </div>
            )}

            {/* Quick Demo Pre-Fill Action Bar */}
            <div className="bg-gradient-to-r from-indigo-950/40 via-slate-900 to-indigo-950/40 border border-indigo-500/20 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" /> Test Live On-Chain Sample Cases
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Pre-load real platform rules and live web URLs to file a new appeal:
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => loadSampleCase('youtube')}
                  className="text-xs font-medium px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
                >
                  YouTube Fair-Use
                </button>
                <button
                  onClick={() => loadSampleCase('x')}
                  className="text-xs font-medium px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
                >
                  X Suspension
                </button>
                <button
                  onClick={() => loadSampleCase('reddit')}
                  className="text-xs font-medium px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
                >
                  Reddit Takedown
                </button>
                <button
                  onClick={() => loadSampleCase('substack')}
                  className="text-xs font-medium px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
                >
                  Substack Ban
                </button>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-[#111726] border border-slate-800 p-4 rounded-xl">
              <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
                <span className="text-xs text-slate-400 font-semibold uppercase flex items-center gap-1">
                  <Filter className="w-3.5 h-3.5" /> Platform:
                </span>
                {PLATFORMS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPlatformFilter(p)}
                    className={`text-xs px-2.5 py-1 rounded-md font-medium transition ${
                      platformFilter === p
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-slate-200 bg-slate-800/60'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-slate-400 font-semibold uppercase">Verdict:</span>
                <select
                  value={verdictFilter}
                  onChange={(e) => setVerdictFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Verdicts</option>
                  <option value="OVERTURN">OVERTURN</option>
                  <option value="REDUCE_SEVERITY">REDUCE SEVERITY</option>
                  <option value="UPHOLD_BAN">UPHOLD BAN</option>
                  <option value="EN_BANC_REQUESTED">EN BANC REQUESTED</option>
                </select>
              </div>
            </div>

            {/* Cases Grid */}
            {cases.length === 0 ? (
              <div className="bg-[#111726] border border-slate-800 rounded-2xl p-12 text-center space-y-4">
                <Gavel className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-lg font-bold text-white">
                  No cases found for {platformFilter !== 'All' ? platformFilter : 'the selected criteria'}
                </h3>
                <p className="text-sm text-slate-400 max-w-md mx-auto">
                  Be the first creator to file an appeal for {platformFilter !== 'All' ? platformFilter : 'this platform'} and receive an immutable third-party on-chain ruling.
                </p>
                <button
                  onClick={() => {
                    if (platformFilter !== 'All') setFormPlatform(platformFilter);
                    setActiveTab('wizard');
                  }}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs sm:text-sm px-5 py-2.5 rounded-xl transition inline-flex items-center gap-2"
                >
                  <PlusCircle className="w-4 h-4" /> Be the first to file an appeal
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {cases.map((c) => (
                  <div
                    key={c.case_id}
                    onClick={() => fetchCaseDetail(c.case_id)}
                    className="bg-[#111726] border border-slate-800/90 hover:border-indigo-500/50 rounded-2xl p-5 cursor-pointer transition shadow-sm hover:shadow-md space-y-3.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 text-xs font-bold rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {c.platform}
                        </span>
                        <span className="text-xs font-mono text-slate-400">
                          Case #{c.case_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-500/20">
                          {formatGen(c.stake)} GEN
                        </span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          Sanction: {c.action_taken}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-xs text-slate-400 flex items-center gap-1.5 truncate">
                        <span className="font-semibold text-slate-300">Rule:</span>{' '}
                        <span className="truncate text-indigo-400 font-mono">{c.rule_url}</span>
                      </div>
                      <div className="text-xs text-slate-400 flex items-center gap-1.5 truncate">
                        <span className="font-semibold text-slate-300">Content:</span>{' '}
                        <span className="truncate text-slate-400 font-mono">{c.content_url}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <div>{getVerdictBadge(c.verdict)}</div>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>Confidence: {c.confidence}%</span>
                        <ChevronRight className="w-4 h-4 text-slate-500 group-hover:translate-x-0.5 transition" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: FILE APPEAL WIZARD */}
        {activeTab === 'wizard' && (
          <div className="max-w-2xl mx-auto space-y-6">
            {/* Wizard Steps indicator */}
            <div className="flex items-center justify-between bg-[#111726] border border-slate-800 p-4 rounded-2xl">
              <div className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                    wizardStep === 1 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  1
                </div>
                <span className={`text-xs sm:text-sm font-medium ${wizardStep === 1 ? 'text-white' : 'text-slate-400'}`}>
                  Platform & Sanction
                </span>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-600" />
              <div className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                    wizardStep === 2 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  2
                </div>
                <span className={`text-xs sm:text-sm font-medium ${wizardStep === 2 ? 'text-white' : 'text-slate-400'}`}>
                  Evidence URLs
                </span>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-600" />
              <div className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${
                    wizardStep === 3 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  3
                </div>
                <span className={`text-xs sm:text-sm font-medium ${wizardStep === 3 ? 'text-white' : 'text-slate-400'}`}>
                  Explanation & Stake
                </span>
              </div>
            </div>

            {/* Form Card */}
            <div className="bg-[#111726] border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
              {/* Step 1 */}
              {wizardStep === 1 && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-lg font-bold text-white">Step 1: Select Platform & Sanction</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Identify where the content moderation enforcement occurred.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">Platform</label>
                    <select
                      value={formPlatform}
                      onChange={(e) => setFormPlatform(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500"
                    >
                      {PLATFORMS.filter((p) => p !== 'All').map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">Action Taken by Platform</label>
                    <select
                      value={formAction}
                      onChange={(e) => setFormAction(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500"
                    >
                      {ACTIONS.map((a) => (
                        <option key={a} value={a}>
                          {a}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="pt-4 flex justify-end">
                    <button
                      onClick={() => setWizardStep(2)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition flex items-center gap-2"
                    >
                      Next Step <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2 */}
              {wizardStep === 2 && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-lg font-bold text-white">Step 2: Platform Rule & Content URLs</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      GenLayer Intelligent Contracts fetch both URLs live on-chain using web.render.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">
                      Platform Published Rule URL (must be https://)
                    </label>
                    <input
                      type="url"
                      value={formRuleUrl}
                      onChange={(e) => setFormRuleUrl(e.target.value)}
                      placeholder="https://support.google.com/youtube/answer/6162278"
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500 font-mono text-xs"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">
                      Content URL (must be https:// — live, archive.org, or IPFS mirror)
                    </label>
                    <input
                      type="url"
                      value={formContentUrl}
                      onChange={(e) => setFormContentUrl(e.target.value)}
                      placeholder="https://en.wikipedia.org/wiki/Fair_use"
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500 font-mono text-xs"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">
                      Verbatim Content Quote (Optional, max 500 chars)
                    </label>
                    <textarea
                      rows={3}
                      maxLength={500}
                      value={formQuote}
                      onChange={(e) => setFormQuote(e.target.value)}
                      placeholder="Paste the disputed sentence or excerpt..."
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500 text-xs"
                    />
                    <div className="text-[11px] text-slate-500 text-right">{formQuote.length}/500 chars</div>
                  </div>

                  <div className="pt-4 flex items-center justify-between">
                    <button
                      onClick={() => setWizardStep(1)}
                      className="text-slate-400 hover:text-slate-200 text-sm font-semibold px-4 py-2"
                    >
                      Back
                    </button>
                    <button
                      onClick={() => {
                        if (!formRuleUrl.startsWith('https://') || !formContentUrl.startsWith('https://')) {
                          alert('Both URLs must start with https://');
                          return;
                        }
                        setWizardStep(3);
                      }}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition flex items-center gap-2"
                    >
                      Next Step <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3 */}
              {wizardStep === 3 && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-lg font-bold text-white">Step 3: Defense Explanation & Stake</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Explain why the penalty was disproportionate, selective, or mistaken.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">
                      Explanation / Argument (max 800 chars)
                    </label>
                    <textarea
                      rows={4}
                      maxLength={800}
                      value={formExplanation}
                      onChange={(e) => setFormExplanation(e.target.value)}
                      placeholder="Explain how the content adheres to guidelines or meets fair use / public interest exemptions..."
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500 text-xs"
                    />
                    <div className="text-[11px] text-slate-500 text-right">{formExplanation.length}/800 chars</div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">
                      GEN Stake (Min 1,000 GEN)
                    </label>
                    <input
                      type="number"
                      min="1000"
                      value={formStake}
                      onChange={(e) => setFormStake(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-xl p-3 focus:outline-none focus:border-indigo-500 font-mono text-xs"
                    />
                    <p className="text-[11px] text-slate-400">
                      100% refunded if OVERTURNED; 50% refunded if REDUCE_SEVERITY; forfeited if UPHOLD_BAN.
                    </p>
                  </div>

                  <div className="pt-4 flex items-center justify-between">
                    <button
                      onClick={() => setWizardStep(2)}
                      className="text-slate-400 hover:text-slate-200 text-sm font-semibold px-4 py-2"
                    >
                      Back
                    </button>
                    <button
                      onClick={handleFileAppeal}
                      disabled={loading}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-8 py-3 rounded-xl transition shadow-lg shadow-indigo-600/30 flex items-center gap-2"
                    >
                      <Scale className="w-4 h-4" /> Submit Appeal & Run Jury
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: CREATOR REPUTATION */}
        {activeTab === 'reputation' && (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="bg-[#111726] border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-indigo-400" /> Creator Reputation & On-Chain Badges
              </h3>
              <p className="text-xs text-slate-400">
                Creators earn immutable merit badges by defending legitimate content rights across platforms.
              </p>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={repQuery}
                  onChange={(e) => setRepQuery(e.target.value)}
                  placeholder="Enter creator address (0x...)"
                  className="flex-1 bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-2.5 font-mono focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={() => fetchReputation(repQuery)}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition flex items-center gap-1.5"
                >
                  <Search className="w-3.5 h-3.5" /> Lookup
                </button>
              </div>
            </div>

            {reputation && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-[#111726] border border-slate-800 p-4 rounded-xl text-center">
                    <div className="text-xs text-slate-400 font-medium">Wins (Overturned)</div>
                    <div className="text-2xl font-bold text-emerald-400 mt-1">{reputation.wins}</div>
                  </div>
                  <div className="bg-[#111726] border border-slate-800 p-4 rounded-xl text-center">
                    <div className="text-xs text-slate-400 font-medium">Partials (Reduced)</div>
                    <div className="text-2xl font-bold text-amber-400 mt-1">{reputation.partials}</div>
                  </div>
                  <div className="bg-[#111726] border border-slate-800 p-4 rounded-xl text-center">
                    <div className="text-xs text-slate-400 font-medium">Losses (Upheld)</div>
                    <div className="text-2xl font-bold text-rose-400 mt-1">{reputation.losses}</div>
                  </div>
                  <div className="bg-[#111726] border border-slate-800 p-4 rounded-xl text-center">
                    <div className="text-xs text-slate-400 font-medium">En Banc Wins</div>
                    <div className="text-2xl font-bold text-purple-400 mt-1">{reputation.en_banc_wins}</div>
                  </div>
                </div>

                <div className="bg-[#111726] border border-slate-800 rounded-2xl p-6 space-y-4">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Award className="w-4 h-4 text-amber-400" /> Earned Badges ({reputation.badges.length})
                  </h4>

                  {reputation.badges.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No badges earned yet. File an appeal to begin.</p>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {reputation.badges.map((b) => (
                        <div
                          key={b.id}
                          className="bg-slate-900 border border-indigo-500/20 p-4 rounded-xl space-y-1 hover:border-indigo-500/40 transition"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-md bg-amber-500/20 text-amber-300 flex items-center justify-center text-xs">
                              🏆
                            </div>
                            <span className="font-semibold text-sm text-white">{b.name}</span>
                          </div>
                          <p className="text-xs text-slate-400 leading-relaxed pl-8">{b.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Case Detail Modal */}
      {selectedCase && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-[#111726] border border-slate-700 rounded-2xl max-w-2xl w-full p-6 sm:p-8 space-y-5 shadow-2xl my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 rounded-lg text-xs font-bold">
                  {selectedCase.platform}
                </span>
                <span className="text-sm font-mono text-slate-300">Case #{selectedCase.case_id}</span>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                className="text-slate-400 hover:text-white text-lg font-bold px-2 py-1"
              >
                &times;
              </button>
            </div>

            {/* Verdict header banner */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[11px] text-slate-400 uppercase font-semibold">Jury Verdict:</span>
                <div className="mt-1">{getVerdictBadge(selectedCase.verdict)}</div>
              </div>

              {/* Confidence Gradient Bar */}
              <div className="w-full sm:w-48 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Confidence</span>
                  <span className="font-bold text-white">{selectedCase.confidence}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-rose-500 via-amber-500 to-emerald-500 transition-all duration-500"
                    style={{ width: `${selectedCase.confidence}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Platform Sanction & URLs */}
            <div className="space-y-2 text-xs">
              <div className="bg-slate-900 p-3 rounded-lg flex items-center justify-between">
                <span className="text-slate-400 font-semibold">Stake Locked:</span>
                <span className="font-mono text-emerald-400 font-bold">{formatGen(selectedCase.stake)} GEN</span>
              </div>
              <div className="bg-slate-900 p-3 rounded-lg flex items-center justify-between">
                <span className="text-slate-400 font-semibold">Action Contested:</span>
                <span className="font-mono text-rose-300 font-bold">{selectedCase.action_taken}</span>
              </div>
              <div className="bg-slate-900 p-3 rounded-lg flex items-center justify-between">
                <span className="text-slate-400 font-semibold">Rule Guideline URL:</span>
                <a
                  href={selectedCase.rule_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-400 hover:underline flex items-center gap-1 font-mono truncate max-w-xs sm:max-w-md"
                >
                  {selectedCase.rule_url} <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              </div>
              <div className="bg-slate-900 p-3 rounded-lg flex items-center justify-between">
                <span className="text-slate-400 font-semibold">Content URL:</span>
                <a
                  href={selectedCase.content_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-300 hover:underline flex items-center gap-1 font-mono truncate max-w-xs sm:max-w-md"
                >
                  {selectedCase.content_url} <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              </div>
            </div>

            {/* Explanation & Quote */}
            {selectedCase.content_quote && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-slate-400">Content Quote Under Review:</span>
                <blockquote className="border-l-2 border-indigo-500/50 pl-3 py-1 italic text-xs text-slate-300 bg-slate-900/40 rounded-r">
                  &ldquo;{selectedCase.content_quote}&rdquo;
                </blockquote>
              </div>
            )}

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-slate-400">Appellant's Defense Statement:</span>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/50 p-3 rounded-lg">
                {selectedCase.explanation}
              </p>
            </div>

            {/* Rationale & Rule Clauses Cited */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <span className="text-xs font-semibold text-indigo-400 flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5" /> AI Jury Consensus Rationale:
              </span>
              <p className="text-xs sm:text-sm text-slate-200 leading-relaxed bg-indigo-950/20 border border-indigo-500/20 p-3.5 rounded-xl">
                {selectedCase.reason}
              </p>
            </div>

            {selectedCase.rule_clauses_cited && selectedCase.rule_clauses_cited.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5" /> Rule Clauses Cited by Jury:
                </span>
                <div className="space-y-1.5">
                  {selectedCase.rule_clauses_cited.map((clause, idx) => (
                    <blockquote
                      key={idx}
                      className="border-l-2 border-amber-500/70 pl-3 py-1.5 text-xs text-amber-200/90 bg-amber-500/5 rounded-r"
                    >
                      {clause}
                    </blockquote>
                  ))}
                </div>
              </div>
            )}

            {/* En Banc Appellate Section (If requested or eligible) */}
            {selectedEnBanc ? (
              <div className="bg-purple-950/20 border border-purple-500/30 rounded-xl p-4 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
                    <Landmark className="w-4 h-4" /> Full-Court En Banc Review
                  </span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                    Status: {selectedEnBanc.verdict || 'REVIEWING'}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{selectedEnBanc.reason}</p>
                <div className="text-[11px] text-slate-400 space-y-1">
                  <span className="font-semibold text-slate-300">Cross-Check Evidence Sources:</span>
                  <ul className="list-disc pl-4 space-y-0.5 font-mono text-[10px]">
                    {selectedEnBanc.extra_urls.map((u, i) => (
                      <li key={i} className="truncate">
                        <a href={u} target="_blank" rel="noreferrer" className="text-purple-400 hover:underline">
                          {u}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                {selectedCase.state === 'UNDER_REVIEW' ? (
                  <span className="text-xs text-slate-400 italic">Case is currently under primary review...</span>
                ) : (
                  <button
                    onClick={() => setShowEnBancModal(true)}
                    className="bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
                  >
                    <Landmark className="w-3.5 h-3.5" /> Petition En Banc Full-Court Review
                  </button>
                )}
                <button
                  onClick={() => setSelectedCase(null)}
                  className="text-xs text-slate-400 hover:text-white font-medium"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* En Banc Petition Modal */}
      {showEnBancModal && selectedCase && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111726] border border-purple-500/40 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Landmark className="w-5 h-5 text-purple-400" /> Petition En Banc Appellate Review
              </h3>
              <button
                onClick={() => setShowEnBancModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              En Banc conducts a multi-source review of Case #{selectedCase.case_id}. Provide 1–2 additional published evidence URLs (platform terms, help center FAQ, public precedent). Double stake required (
              {formatGen(
                (selectedCase.stake
                  ? BigInt(selectedCase.stake) < 1000000000000000n
                    ? BigInt(selectedCase.stake) * WEI_PER_GEN
                    : BigInt(selectedCase.stake)
                  : 1000n * WEI_PER_GEN) * 2n
              )}{' '}
              GEN), refunded if reversed.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-semibold block mb-1">
                  Cross-Check Evidence URL 1 (must be https://)
                </label>
                <input
                  type="url"
                  value={enBancUrl1}
                  onChange={(e) => setEnBancUrl1(e.target.value)}
                  placeholder="https://substack.com/terms"
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg p-2.5 font-mono text-[11px] focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">
                  Cross-Check Evidence URL 2 (Optional, must be https://)
                </label>
                <input
                  type="url"
                  value={enBancUrl2}
                  onChange={(e) => setEnBancUrl2(e.target.value)}
                  placeholder="https://support.substack.com/hc/en-us/articles/..."
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg p-2.5 font-mono text-[11px] focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">
                  Petition Statement (Why initial ruling erred)
                </label>
                <textarea
                  rows={3}
                  value={enBancStatement}
                  onChange={(e) => setEnBancStatement(e.target.value)}
                  placeholder="Explain why the primary sources support an exemption or lesser sanction..."
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded-lg p-2.5 text-xs focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowEnBancModal(false)}
                className="text-xs text-slate-400 hover:text-slate-200 font-medium px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={handleRequestEnBanc}
                disabled={loading}
                className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition"
              >
                Submit Petition (Double Stake)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0a0d14] text-xs text-slate-500 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            <p className="text-slate-400">
              AppealCourt &copy; 2026 — Built on GenLayer Studionet (Chain ID 61999).
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Disclaimer: Independent decentralized tribunal. Rulings constitute immutable third-party evidentiary records.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <a
              href={`https://genlayer-explorer.vercel.app/address/${APPEAL_CASE_ADDRESS}`}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 hover:underline flex items-center gap-1"
            >
              AppealCase Contract <ExternalLink className="w-3 h-3" />
            </a>
            <a
              href={`https://genlayer-explorer.vercel.app/address/${EN_BANC_ADDRESS}`}
              target="_blank"
              rel="noreferrer"
              className="text-purple-400 hover:underline flex items-center gap-1"
            >
              EnBanc <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
