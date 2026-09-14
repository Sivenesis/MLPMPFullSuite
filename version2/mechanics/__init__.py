"""
MLPMP Full Suite - Modular Game Mechanics Registry
"""

from mechanics.level import level_mechanic
from mechanics.currency import currency_mechanic
from mechanics.profile import profile_mechanic
from mechanics.costumes import costumes_mechanic
from mechanics.group_quests import group_quests_mechanic
from mechanics.boosters import boosters_mechanic
from mechanics.find_a_pair import find_a_pair_mechanic
from mechanics.ferris_wheel import ferris_wheel_mechanic
from mechanics.fortune_shop import fortune_shop_mechanic
from mechanics.store import store_mechanic

MECHANICS = {
    "level": level_mechanic,
    "currency": currency_mechanic,
    "profile": profile_mechanic,
    "costumes": costumes_mechanic,
    "group_quests": group_quests_mechanic,
    "boosters": boosters_mechanic,
    "find_a_pair": find_a_pair_mechanic,
    "ferris_wheel": ferris_wheel_mechanic,
    "fortune_shop": fortune_shop_mechanic,
    "store": store_mechanic,
}

__all__ = [
    "level_mechanic",
    "currency_mechanic",
    "profile_mechanic",
    "costumes_mechanic",
    "group_quests_mechanic",
    "boosters_mechanic",
    "find_a_pair_mechanic",
    "ferris_wheel_mechanic",
    "fortune_shop_mechanic",
    "store_mechanic",
    "MECHANICS",
]
