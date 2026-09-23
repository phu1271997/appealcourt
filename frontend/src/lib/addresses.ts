export const APPEAL_CASE_ADDRESS = (import.meta.env.VITE_APPEAL_CONTRACT ||
  '0xb727deE03260539af5D35F214c0671Ea6C5a5f8B') as `0x${string}`;

export const EN_BANC_ADDRESS = (import.meta.env.VITE_ENBANC_CONTRACT ||
  '0x3C89E1aBDEADf87a344434dd45B2Ac062A59f4d0') as `0x${string}`;

export const REPUTATION_ADDRESS = (import.meta.env.VITE_REPUTATION_CONTRACT ||
  '0x79Bc835E8354820868396e06cA5e529Bb6b83779') as `0x${string}`;

export const STUDIO_RPC =
  import.meta.env.VITE_STUDIO_RPC || 'https://studio.genlayer.com/api';
