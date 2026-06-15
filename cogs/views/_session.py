"""
BiCanhSession — in-memory session data cho bí cảnh combat.
Tách ra khỏi hoso_utils.py để break circular import.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class BiCanhSession:
    user_id:    int
    bc_id:      int
    ts:         dict
    phong_list: list
    phong_hien: int   = 0
    hp_hien:    int   = 0
    ll_hien:    int   = 0
    exp_tich:   int   = 0
    lt_tich:    int   = 0
    skill_cd:   dict | None = field(default=None)
    skill_names:dict | None = field(default=None)
    nl_tich:           dict = field(default_factory=dict)
    dan_tich:          dict = field(default_factory=dict)
    linh_qua_tich:     dict = field(default_factory=dict)
    manh_tich:         dict = field(default_factory=dict)
    dotpha_tc_nl_tich: dict = field(default_factory=dict)
    sung_thu_drop:     list = field(default_factory=list)
    logs:       list  = field(default_factory=list)
    ket_thuc:   bool  = False
    created_at: int   = 0
    last_lt:    int   = 0
    last_exp:   int   = 0
    he_so:      float = 1.0


_bc_sessions: dict[tuple[int, int], BiCanhSession] = {}
SESSION_TIMEOUT_SECS = 1800


def _cleanup_stale_sessions() -> int:
    now = int(time.time())
    stale = [key for key, s in _bc_sessions.items()
             if now - s.created_at > SESSION_TIMEOUT_SECS and not s.ket_thuc]
    for key in stale:
        _bc_sessions.pop(key, None)
    return len(stale)
