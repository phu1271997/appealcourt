# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json


def _addr_str(addr: Address) -> str:
    try:
        return addr.as_hex
    except Exception:
        return str(addr)


class CreatorReputation(gl.Contract):
    admin: Address
    authorized_callers: TreeMap[str, bool]
    wins: TreeMap[str, u256]
    losses: TreeMap[str, u256]
    partials: TreeMap[str, u256]
    en_banc_wins: TreeMap[str, u256]
    platforms_used: TreeMap[str, str]

    def __init__(self):
        self.admin = gl.message.sender_address

    @gl.public.write
    def set_authorized(self, caller: Address, allowed: bool) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Only admin can authorize callers")
        self.authorized_callers[_addr_str(caller)] = allowed

    @gl.public.write
    def record_verdict(self, appellant: str, platform: str, result: str) -> None:
        sender_str = _addr_str(gl.message.sender_address)
        is_auth = self.authorized_callers.get(sender_str, False)
        if not is_auth and gl.message.sender_address != self.admin:
            raise gl.vm.UserError("Unauthorized caller")

        w = appellant.lower().strip()
        res_upper = result.upper().strip()

        if res_upper == "WIN":
            prev = int(self.wins.get(w, u256(0)))
            self.wins[w] = u256(prev + 1)
        elif res_upper == "LOSS":
            prev = int(self.losses.get(w, u256(0)))
            self.losses[w] = u256(prev + 1)
        elif res_upper == "PARTIAL":
            prev = int(self.partials.get(w, u256(0)))
            self.partials[w] = u256(prev + 1)
        elif res_upper == "EN_BANC_WIN":
            prev_eb = int(self.en_banc_wins.get(w, u256(0)))
            self.en_banc_wins[w] = u256(prev_eb + 1)
            prev_w = int(self.wins.get(w, u256(0)))
            self.wins[w] = u256(prev_w + 1)
        else:
            raise gl.vm.UserError("Invalid result type")

        # Track platforms used
        cur_plat = self.platforms_used.get(w, "")
        plist = [p.strip() for p in cur_plat.split(",") if p.strip()]
        plat_clean = platform.strip()
        if plat_clean and plat_clean not in plist:
            plist.append(plat_clean)
            self.platforms_used[w] = ",".join(plist)

    @gl.public.view
    def get_creator_reputation(self, appellant: str) -> str:
        w = appellant.lower().strip()
        w_cnt = int(self.wins.get(w, u256(0)))
        l_cnt = int(self.losses.get(w, u256(0)))
        p_cnt = int(self.partials.get(w, u256(0)))
        eb_cnt = int(self.en_banc_wins.get(w, u256(0)))
        total = w_cnt + l_cnt + p_cnt

        cur_plat = self.platforms_used.get(w, "")
        platforms = [p.strip() for p in cur_plat.split(",") if p.strip()]

        badges = []
        if total >= 1:
            badges.append({
                "id": "first_appeal",
                "name": "First Appeal",
                "description": "Filed at least 1 formal content appeal on GenLayer"
            })
        if w_cnt >= 1:
            badges.append({
                "id": "vindicated",
                "name": "Vindicated",
                "description": "Successfully overturned an improper platform ban"
            })
        if total >= 5:
            badges.append({
                "id": "serial_appellant",
                "name": "Serial Appellant",
                "description": "Defended content rights across 5+ moderation actions"
            })
        if w_cnt >= 10:
            badges.append({
                "id": "champion",
                "name": "Champion",
                "description": "Overturned 10+ unfair platform penalties"
            })
        if len(platforms) >= 3:
            badges.append({
                "id": "cross_platform",
                "name": "Cross-Platform",
                "description": "Active creator across 3+ distinct content platforms"
            })
        if eb_cnt >= 1:
            badges.append({
                "id": "persistent",
                "name": "Persistent",
                "description": "Won a full-court En Banc appellate review"
            })

        data = {
            "appellant": appellant,
            "wins": w_cnt,
            "losses": l_cnt,
            "partials": p_cnt,
            "en_banc_wins": eb_cnt,
            "total_appeals": total,
            "platforms": platforms,
            "badges": badges,
        }
        return json.dumps(data)
