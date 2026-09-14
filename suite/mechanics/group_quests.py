"""
Group Quests Keys Mechanic for MLPMP Full Suite.
Decoupled handler for reading and writing Group Quest bonus keys (Token_GQ_bonus).
"""

from typing import Dict, Any, Tuple
from core.memory import mem
from core.offsets import TOKEN_GQ_KEYS
from mechanics.base import BaseMechanic


class GroupQuestsMechanic(BaseMechanic):
    name = "GroupQuestsMechanic"
    description = "Group Quests Bonus Keys Manager"

    def get_state(self) -> Dict[str, Any]:
        val = self.read_token_value(TOKEN_GQ_KEYS)
        return {
            "available": mem.is_attached(),
            "keys": val if val is not None else 0,
        }

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        if not mem.is_attached():
            return False, "Not attached to game process."

        target_keys = payload.get("keys")
        if target_keys is None:
            return False, "Parameter 'keys' is required."

        keys_int = max(0, min(int(target_keys), 999999))
        ok = self.write_token_value(TOKEN_GQ_KEYS, keys_int)
        if ok:
            msg = f"Group Quest Keys set to {keys_int:,}."
            mem.log("SUCCESS", f"[GroupQuests] {msg}")
            return True, msg
        return False, "Failed writing Group Quest Keys token."


group_quests_mechanic = GroupQuestsMechanic()
