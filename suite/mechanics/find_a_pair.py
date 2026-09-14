"""
Find a Pair Minigame Mechanic for MLPMP Full Suite.
Manages:
- Live Timer input, application, and freeze toggle
- Multiplier input, application, and freeze toggle (with standard 'freeze' and 'deny decrease' modes)
- Background thread worker to enforce freezes without blocking the server
"""

import threading
import time
from typing import Dict, Any, Optional, Tuple
from core.memory import mem
from core.offsets import (
    RVA_STATE_MANAGER,
    PAIR_STATE_ID,
    OFF_PAIR_TIMER_FLOAT,
    OFF_PAIR_TIMER_INT,
    OFF_PAIR_MULT_OBJ,
    OFF_PAIR_SCORE_OBJ,
)
from mechanics.base import BaseMechanic


class FindAPairMechanic(BaseMechanic):
    name = "FindAPairMechanic"
    description = "Find a Pair Minigame Timer & Multiplier Manager"

    def __init__(self):
        super().__init__()
        self.timer_freeze: bool = False
        self.frozen_timer_value: float = 999.0

        self.multiplier_freeze: bool = False
        self.multiplier_mode: str = "freeze"  # "freeze" or "deny_decrease"
        self.target_multiplier: int = 10

        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running: bool = False
        self._ensure_worker_running()

    def _find_pair_state(self) -> Optional[int]:
        """Traverses StateManager active states to locate StateMinigameFindPair (ID 102)."""
        if not mem.is_attached() or not mem.module_base:
            return None

        sm_ptr = mem.module_base + RVA_STATE_MANAGER
        sm = mem.read_ptr(sm_ptr)
        if not sm or not mem.is_valid_user_ptr(sm):
            return None

        head = mem.read_ptr(sm + 8)
        if not head or not mem.is_valid_user_ptr(head):
            return None

        curr = mem.read_ptr(head)
        visited = set()
        while curr and curr != head and curr not in visited and len(visited) < 60:
            visited.add(curr)
            state_ptr = mem.read_ptr(curr + 0x10)
            if state_ptr and mem.is_valid_user_ptr(state_ptr):
                state_id = mem.read_u32(state_ptr + 0x28)
                if state_id == PAIR_STATE_ID:
                    return state_ptr
            curr = mem.read_ptr(curr)

        return None

    def _ensure_worker_running(self):
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_running = True
            self._worker_thread = threading.Thread(
                target=self._freeze_loop, name="PairFreezeWorker", daemon=True
            )
            self._worker_thread.start()

    def _freeze_loop(self):
        """High-frequency background worker enforcing timer and multiplier freezes."""
        while self._worker_running:
            try:
                if (self.timer_freeze or self.multiplier_freeze) and mem.is_attached():
                    state = self._find_pair_state()
                    if state:
                        # 1. Timer Freeze
                        if self.timer_freeze:
                            mem.write_float(state + OFF_PAIR_TIMER_FLOAT, float(self.frozen_timer_value))
                            mem.write_u32(state + OFF_PAIR_TIMER_INT, int(self.frozen_timer_value))

                        # 2. Multiplier Freeze
                        if self.multiplier_freeze:
                            obj_mult = mem.read_ptr(state + OFF_PAIR_MULT_OBJ)
                            if obj_mult and mem.is_valid_user_ptr(obj_mult):
                                p1 = mem.read_ptr(obj_mult + 8)
                                p2 = mem.read_ptr(obj_mult + 0x10)
                                if p1 and mem.is_valid_user_ptr(p1):
                                    cur_val = mem.read_u32(p1) or 1
                                    if self.multiplier_mode == "deny_decrease":
                                        # Natural growth allowed, ignore decreases
                                        if cur_val > self.target_multiplier:
                                            self.target_multiplier = cur_val
                                        elif cur_val < self.target_multiplier:
                                            mem.write_u32(p1, self.target_multiplier)
                                            if p2 and mem.is_valid_user_ptr(p2):
                                                mem.write_u32(p2, self.target_multiplier)
                                    else:
                                        # Strict lock
                                        if cur_val != self.target_multiplier:
                                            mem.write_u32(p1, self.target_multiplier)
                                            if p2 and mem.is_valid_user_ptr(p2):
                                                mem.write_u32(p2, self.target_multiplier)
            except Exception:
                pass
            time.sleep(0.08)

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": mem.is_attached(),
            "game_active": False,
            "timer": 0.0,
            "multiplier": 1,
            "score": 0,
            "timer_freeze": self.timer_freeze,
            "multiplier_freeze": self.multiplier_freeze,
            "multiplier_mode": self.multiplier_mode,
        }

        pair_state = self._find_pair_state()
        if pair_state:
            state["game_active"] = True
            t_val = mem.read_float(pair_state + OFF_PAIR_TIMER_FLOAT) or 0.0
            state["timer"] = round(t_val, 2)

            obj_mult = mem.read_ptr(pair_state + OFF_PAIR_MULT_OBJ)
            if obj_mult and mem.is_valid_user_ptr(obj_mult):
                p1 = mem.read_ptr(obj_mult + 8)
                if p1 and mem.is_valid_user_ptr(p1):
                    state["multiplier"] = mem.read_u32(p1) or 1

            obj_score = mem.read_ptr(pair_state + OFF_PAIR_SCORE_OBJ)
            if obj_score and mem.is_valid_user_ptr(obj_score):
                p1 = mem.read_ptr(obj_score + 8)
                if p1 and mem.is_valid_user_ptr(p1):
                    state["score"] = mem.read_u32(p1) or 0
        return state

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        if not mem.is_attached():
            return False, "Not attached to game process."

        self._ensure_worker_running()
        actions = []
        state = self._find_pair_state()

        # Handle Timer Apply
        if "timer" in payload and payload["timer"] is not None:
            t_val = max(0.0, min(float(payload["timer"]), 9999.0))
            self.frozen_timer_value = t_val
            if state:
                mem.write_float(state + OFF_PAIR_TIMER_FLOAT, t_val)
                mem.write_u32(state + OFF_PAIR_TIMER_INT, int(t_val))
            actions.append(f"Timer -> {t_val:.1f}s")

        # Handle Timer Freeze Toggle
        if "timer_freeze" in payload and payload["timer_freeze"] is not None:
            self.timer_freeze = bool(payload["timer_freeze"])
            if self.timer_freeze and "timer" in payload and payload["timer"] is not None:
                self.frozen_timer_value = float(payload["timer"])
            elif self.timer_freeze and state:
                cur_t = mem.read_float(state + OFF_PAIR_TIMER_FLOAT)
                if cur_t and cur_t > 0:
                    self.frozen_timer_value = cur_t
            status_str = f"ON ({self.frozen_timer_value:.0f}s)" if self.timer_freeze else "OFF"
            actions.append(f"Timer Freeze -> {status_str}")

        # Handle Multiplier Apply
        if "multiplier" in payload and payload["multiplier"] is not None:
            m_val = max(1, min(int(payload["multiplier"]), 999))
            self.target_multiplier = m_val
            if state:
                obj_mult = mem.read_ptr(state + OFF_PAIR_MULT_OBJ)
                if obj_mult and mem.is_valid_user_ptr(obj_mult):
                    p1 = mem.read_ptr(obj_mult + 8)
                    p2 = mem.read_ptr(obj_mult + 0x10)
                    if p1:
                        mem.write_u32(p1, m_val)
                    if p2:
                        mem.write_u32(p2, m_val)
            actions.append(f"Multiplier -> {m_val}x")

        # Handle Multiplier Mode ("freeze" vs "deny_decrease")
        if "multiplier_mode" in payload and payload["multiplier_mode"] in ("freeze", "deny_decrease"):
            self.multiplier_mode = payload["multiplier_mode"]
            mode_label = "Deny Decrease" if self.multiplier_mode == "deny_decrease" else "Strict Lock"
            actions.append(f"Multiplier Mode -> {mode_label}")

        # Handle Multiplier Freeze Toggle
        if "multiplier_freeze" in payload and payload["multiplier_freeze"] is not None:
            self.multiplier_freeze = bool(payload["multiplier_freeze"])
            if self.multiplier_freeze and "multiplier" in payload and payload["multiplier"] is not None:
                self.target_multiplier = int(payload["multiplier"])
            elif self.multiplier_freeze and state:
                obj_mult = mem.read_ptr(state + OFF_PAIR_MULT_OBJ)
                if obj_mult and mem.is_valid_user_ptr(obj_mult):
                    p1 = mem.read_ptr(obj_mult + 8)
                    if p1:
                        self.target_multiplier = mem.read_u32(p1) or 1
            status_str = f"ON ({self.target_multiplier}x, {self.multiplier_mode})" if self.multiplier_freeze else "OFF"
            actions.append(f"Multiplier Freeze -> {status_str}")

        if actions:
            msg = "; ".join(actions)
            mem.log("SUCCESS", f"[FindAPair] {msg}")
            return True, msg
        return False, "No Find a Pair parameters provided."


find_a_pair_mechanic = FindAPairMechanic()
