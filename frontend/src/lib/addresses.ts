export const APPEAL_CASE_ADDRESS = (import.meta.env.VITE_APPEAL_CONTRACT ||
  '0x5594e5317e0fc5Fd17Eac1F2D0B0Fe0C66dA61D9') as `0x${string}`;

export const EN_BANC_ADDRESS = (import.meta.env.VITE_ENBANC_CONTRACT ||
  '0x07cFBD3ec3Dad67D0Ae8016aC44E39fF59039D22') as `0x${string}`;

export const REPUTATION_ADDRESS = (import.meta.env.VITE_REPUTATION_CONTRACT ||
  '0x0AfBD8B0A8d2795CE979334cF76E9d8707C224F8') as `0x${string}`;

export const STUDIO_RPC =
  import.meta.env.VITE_STUDIO_RPC || 'https://studio.genlayer.com/api';
