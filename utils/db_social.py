from __future__ import annotations
import logging
import json
import time
import datetime as _dt
from utils.database import get_pool

log = logging.getLogger("database")


# ══════════════════════════════════════════════════════
#  WORLD CHAT
# ══════════════════════════════════════════════════════

async def get_world_chat_channels() -> list:
    """Lấy tất cả channel đăng ký world chat (kể cả inactive)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT guild_id, channel_id, webhook_url, active, thread_id FROM world_chat_channels ORDER BY created_at"
        )
        return [dict(r) for r in rows]


async def get_world_chat_by_guild(guild_id: int) -> dict | None:
    """Lấy config world chat của 1 guild."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT guild_id, channel_id, webhook_url, active, thread_id FROM world_chat_channels WHERE guild_id=$1",
            guild_id
        )
        return dict(row) if row else None


async def set_world_chat_channel(guild_id: int, channel_id: int, webhook_url: str, thread_id: int | None = None):
    """Đăng ký hoặc cập nhật world chat channel cho guild."""
    import time as _time
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO world_chat_channels (guild_id, channel_id, webhook_url, active, created_at, thread_id)
            VALUES ($1, $2, $3, 1, $4, $5)
            ON CONFLICT (guild_id) DO UPDATE SET
                channel_id  = EXCLUDED.channel_id,
                webhook_url = EXCLUDED.webhook_url,
                active      = 1,
                created_at  = EXCLUDED.created_at,
                thread_id   = EXCLUDED.thread_id
        """, guild_id, channel_id, webhook_url, int(_time.time()), thread_id)


async def disable_world_chat(guild_id: int):
    """Tắt world chat cho guild (giữ record để có thể bật lại)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE world_chat_channels SET active=0 WHERE guild_id=$1",
            guild_id
        )


async def mark_webhook_inactive(guild_id: int):
    """Đánh dấu webhook dead (404/401) — tự động khi forward thất bại."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE world_chat_channels SET active=0 WHERE guild_id=$1",
            guild_id
        )


# ══════════════════════════════════════════════════════
#  CROSS PvP CHALLENGES
# ══════════════════════════════════════════════════════
async def create_cross_challenge(
    challenger_id: int, challenger_guild: int, target_id: int, cuoc_lt: int
) -> int:
    """Tạo lời thách đấu liên server. Trả về challenge ID."""
    now = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO cross_pvp_challenges
               (challenger_id, challenger_guild, target_id, cuoc_lt, created_at, status)
               VALUES ($1, $2, $3, $4, $5, 'pending')
               RETURNING id""",
            challenger_id, challenger_guild, target_id, cuoc_lt, now,
        )
        return row["id"]


async def get_cross_challenge(challenge_id: int) -> dict | None:
    """Lấy thông tin 1 challenge theo ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM cross_pvp_challenges WHERE id=$1", challenge_id
        )
        return dict(row) if row else None


async def get_pending_cross_challenge(target_id: int) -> dict | None:
    """Lấy lời thách đấu pending đầu tiên dành cho target_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM cross_pvp_challenges
               WHERE target_id=$1 AND status='pending'
               ORDER BY created_at ASC LIMIT 1""",
            target_id,
        )
        return dict(row) if row else None


async def get_pending_by_challenger(challenger_id: int) -> dict | None:
    """Kiểm tra challenger đang có thách đấu pending không."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM cross_pvp_challenges
               WHERE challenger_id=$1 AND status='pending'
               ORDER BY created_at DESC LIMIT 1""",
            challenger_id,
        )
        return dict(row) if row else None


async def resolve_cross_challenge(challenge_id: int, status: str):
    """Đổi status challenge: 'accepted' | 'declined' | 'expired'."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE cross_pvp_challenges SET status=$1 WHERE id=$2",
            status, challenge_id,
        )


async def expire_old_cross_challenges():
    """Đánh dấu expired các challenge quá 5 phút."""
    cutoff = int(time.time()) - 300
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE cross_pvp_challenges
               SET status='expired'
               WHERE status='pending' AND created_at < $1""",
            cutoff,
        )


# ══════════════════════════════════════════════════════
#  QUAN HỆ
# ══════════════════════════════════════════════════════
def _qh_key(a: int, b: int) -> tuple[int, int]:
    return (min(a, b), max(a, b))


async def get_quan_he(user_a: int, user_b: int) -> dict | None:
    pool = await get_pool()
    a, b = _qh_key(user_a, user_b)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM quan_he WHERE user_a=$1 AND user_b=$2", a, b
        )
        return dict(row) if row else None


async def upsert_quan_he(user_a: int, user_b: int, diem_delta: int = 0, loai: str = None):
    a, b = _qh_key(user_a, user_b)
    now = int(time.time())
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM quan_he WHERE user_a=$1 AND user_b=$2", a, b
        )
        if not existing:
            await conn.execute(
                "INSERT INTO quan_he (user_a, user_b, diem, loai, ngay_tao) VALUES ($1,$2,$3,$4,$5)",
                a, b, diem_delta, loai or "", now
            )
        else:
            new_diem = existing["diem"] + diem_delta
            new_loai = loai if loai is not None else existing["loai"]
            await conn.execute(
                "UPDATE quan_he SET diem=$1, loai=$2 WHERE user_a=$3 AND user_b=$4",
                new_diem, new_loai, a, b
            )
    return await get_quan_he(a, b)


async def set_quan_he_loai(user_a: int, user_b: int, loai: str):
    a, b = _qh_key(user_a, user_b)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE quan_he SET loai=$1 WHERE user_a=$2 AND user_b=$3", loai, a, b
        )


async def get_danh_sach_quan_he(user_id: int) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM quan_he WHERE user_a=$1 OR user_b=$1 ORDER BY diem DESC", user_id
        )
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  TẶNG QUÀ LOG
# ══════════════════════════════════════════════════════
def _today_str() -> str:
    return _dt.date.today().isoformat()


async def get_tang_qua_hom_nay(user_id: int, target_id: int) -> int:
    pool = await get_pool()
    ngay = _today_str()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT diem_tang FROM tang_qua_log WHERE user_id=$1 AND target_id=$2 AND ngay=$3",
            user_id, target_id, ngay
        )
        return row["diem_tang"] if row else 0


async def add_tang_qua_log(user_id: int, target_id: int, diem: int):
    ngay = _today_str()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tang_qua_log (user_id, target_id, ngay, diem_tang)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (user_id, target_id, ngay) DO UPDATE SET
                diem_tang = tang_qua_log.diem_tang + $4
        """, user_id, target_id, ngay, diem)


# ══════════════════════════════════════════════════════
#  RESET LOG
# ══════════════════════════════════════════════════════
async def _ensure_reset_log(conn) -> None:
    """Tạo bảng reset_log nếu chưa tồn tại."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS reset_log (
            user_id      BIGINT  PRIMARY KEY,
            so_lan_reset INTEGER DEFAULT 0
        );
    """)


async def get_reset_count(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await _ensure_reset_log(conn)
        row = await conn.fetchrow(
            "SELECT so_lan_reset FROM reset_log WHERE user_id=$1", user_id)
    return row["so_lan_reset"] if row else 0


async def increment_reset_count(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await _ensure_reset_log(conn)
        row = await conn.fetchrow("""
            INSERT INTO reset_log (user_id, so_lan_reset)
            VALUES ($1, 1)
            ON CONFLICT (user_id) DO UPDATE
              SET so_lan_reset = reset_log.so_lan_reset + 1
            RETURNING so_lan_reset
        """, user_id)
    return row["so_lan_reset"] if row else 1


# ══════════════════════════════════════════════════════════════
#  ACTIVE VOTE
# ══════════════════════════════════════════════════════════════

async def save_active_vote(question: str, start_ts: int, end_ts: int,
                           votes: dict, messages: dict) -> None:
    """Upsert trạng thái vote đang mở vào DB."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO active_vote (id, question, start_ts, end_ts, votes_json, msgs_json)
            VALUES (1, $1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET
                question   = EXCLUDED.question,
                start_ts   = EXCLUDED.start_ts,
                end_ts     = EXCLUDED.end_ts,
                votes_json = EXCLUDED.votes_json,
                msgs_json  = EXCLUDED.msgs_json
        """, question, start_ts, end_ts,
             json.dumps(votes, ensure_ascii=False),
             json.dumps(messages, ensure_ascii=False))


async def update_active_vote_data(votes: dict, messages: dict) -> None:
    """Cập nhật phiếu bầu và danh sách message vào DB."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE active_vote SET votes_json=$1, msgs_json=$2 WHERE id=1
        """, json.dumps(votes, ensure_ascii=False),
             json.dumps(messages, ensure_ascii=False))


async def load_active_vote() -> dict | None:
    """Lấy vote đang mở từ DB. Trả về None nếu không có."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM active_vote WHERE id=1")
        if not row:
            return None
        return {
            "question":   row["question"],
            "start_ts":   row["start_ts"],
            "end_ts":     row["end_ts"],
            "votes":      json.loads(row["votes_json"] or "{}"),
            "messages":   json.loads(row["msgs_json"]  or "{}"),
        }


async def clear_active_vote() -> None:
    """Xóa vote khỏi DB sau khi đã đóng."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM active_vote WHERE id=1")


# ══════════════════════════════════════════════════════
#  PROMO CODES (Shop)
# ══════════════════════════════════════════════════════

async def create_promo_code(code: str, goi: str, nguoi_tao: int) -> bool:
    """Tạo promo code mới. Trả về True nếu thành công."""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO promo_codes (code, goi, nguoi_tao, ngay_tao) VALUES ($1,$2,$3,$4)",
                code, goi, nguoi_tao, int(time.time())
            )
        return True
    except Exception:
        return False


async def redeem_promo_code(code: str, user_id: int) -> dict | None:
    """Đổi promo code. Trả về dict {code, goi} nếu thành công, None nếu code không hợp lệ/đã dùng."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT code, goi, nguoi_dung FROM promo_codes WHERE code=$1", code
        )
        if not row:
            return None
        if row["nguoi_dung"] and row["nguoi_dung"] != 0:
            return None  # đã dùng
        await conn.execute(
            "UPDATE promo_codes SET nguoi_dung=$1, ngay_dung=$2 WHERE code=$3",
            user_id, int(time.time()), code
        )
        return {"code": row["code"], "goi": row["goi"]}


async def get_promo_code_owner(code: str) -> int | None:
    """Lấy người tạo promo code."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT nguoi_tao FROM promo_codes WHERE code=$1", code
        )
        return row["nguoi_tao"] if row else None


# ══════════════════════════════════════════════════════
#  TRÙNG SINH / VẤN ĐỈNH TIÊN TÔN
# ══════════════════════════════════════════════════════

async def thuc_hien_trung_sinh(user_id: int, bonus_all_stat_pct: float = 0.0) -> dict:
    """
    Thực hiện trùng sinh nhân vật.

    Giữ lại : dao_hieu, the_chat, sung_thu, sung_thu_active,
               linh_can_so_huu (điểm về 0), dotpha_tc_nl,
               so_lan_trung_sinh, ti_le_van_dinh, van_dinh_all_stat_pct
    Xóa sạch của acc này: linh_thach, phap_bao, dan_duoc, nguyen_lieu, linh_qua,
            manh_linh_can, linh_can_diem, cong_phap, phien_cho,
      giao_dich_log 36h.

    Rollback đúng số lượng đã nhận từ acc trùng sinh (private_trade, 36h):
      - Linh Quả      → trừ đúng so_luong × diem_per_qua khỏi linh_can_diem
      - Mảnh Linh Căn → trừ đúng so_luong khỏi manh_linh_can
                        nếu đã ghép thành căn → xóa căn, trả lại số mảnh trước khi ghép
    """
    import time as _time

    try:
        from utils.config import LINH_QUA_BY_ID as _LINH_QUA_BY_ID
    except Exception:
        _LINH_QUA_BY_ID = {}

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            ts = await conn.fetchrow(
                "SELECT * FROM tu_si WHERE user_id=$1 FOR UPDATE", user_id)
            if not ts:
                return {}
            ts = dict(ts)

            # ── Tăng số lần trùng sinh + tỉ lệ Vấn Đỉnh mới ───────────────
            so_lan_moi = ts.get("so_lan_trung_sinh", 0) + 1
            ti_le_moi  = round(0.01 + so_lan_moi * 0.015, 4)
            bonus_all_stat_pct = max(0.0, float(bonus_all_stat_pct or 0.0))
            vd_bonus_moi = round(float(ts.get("van_dinh_all_stat_pct", 0.0) or 0.0) + bonus_all_stat_pct, 4)

            # ── Giữ lại linh căn sở hữu, reset điểm về 0 ───────────────────
            lc_ids = ts.get("linh_can_so_huu", [])
            if isinstance(lc_ids, str):
                try:    lc_ids = json.loads(lc_ids) if lc_ids else []
                except: lc_ids = []
            lc_diem_reset = {lc_id: 0 for lc_id in set(lc_ids)}

            # ── Lấy giao dịch private_trade gửi đi trong 36h ────────────────
            now_ts = int(_time.time())
            cutoff = now_ts - 36 * 3600
            recent_trades = await conn.fetch(
                """SELECT receiver_id, item_loai, item_key, so_luong
                   FROM giao_dich_log
                   WHERE loai='private_trade' AND sender_id=$1 AND thoi_gian >= $2
                     AND receiver_id IS NOT NULL AND receiver_id != $1
                   ORDER BY thoi_gian ASC""",
                user_id, cutoff
            )

            # Gom theo receiver
            from collections import defaultdict
            recv_trades = defaultdict(list)
            for row in recent_trades:
                recv_trades[row["receiver_id"]].append({
                    "item_loai": row["item_loai"] or "",
                    "item_key":  row["item_key"]  or "",
                    "so_luong":  row["so_luong"]  or 0,
                })

            # ── Rollback từng receiver (sort để tránh deadlock) ──────────────
            for recv_id in sorted(recv_trades.keys()):
                recv_row = await conn.fetchrow(
                    "SELECT * FROM tu_si WHERE user_id=$1 FOR UPDATE", recv_id)
                if not recv_row:
                    continue

                def _pj(d, f):
                    raw = d.get(f, {})
                    if isinstance(raw, dict): return raw.copy()
                    try: return json.loads(raw) if raw else {}
                    except: return {}

                def _pl(d, f):
                    raw = d.get(f, [])
                    if isinstance(raw, list): return raw.copy()
                    try: return json.loads(raw) if raw else []
                    except: return []

                recv_ts     = dict(recv_row)
                manh        = _pj(recv_ts, "manh_linh_can")
                lc_diem_r   = _pj(recv_ts, "linh_can_diem")
                lc_so_huu_r = _pl(recv_ts, "linh_can_so_huu")
                changed     = False

                for trade in recv_trades[recv_id]:
                    loai     = trade["item_loai"]
                    key      = trade["item_key"]
                    so_luong = trade["so_luong"]
                    if not key or so_luong <= 0:
                        continue

                    if loai == "Linh Quả":
                        # Trừ đúng số điểm đã nhận
                        diem_per = _LINH_QUA_BY_ID.get(key, {}).get("diem", 3)
                        lc_diem_r[key] = max(0, lc_diem_r.get(key, 0) - so_luong * diem_per)
                        changed = True

                    elif loai == "Mảnh Linh Căn":
                        manh_hien   = manh.get(key, 0)
                        so_lan_ghep = lc_so_huu_r.count(key)

                        if so_lan_ghep == 0:
                            # Chưa ghép: trừ thẳng số mảnh đã nhận
                            new_manh = manh_hien - so_luong
                            if new_manh <= 0:
                                manh.pop(key, None)
                            else:
                                manh[key] = new_manh
                        else:
                            # Đã ghép: tính lại số mảnh trước khi nhận từ acc trùng sinh
                            tong_truoc = manh_hien + 100 * so_lan_ghep - so_luong
                            if tong_truoc < 0: tong_truoc = 0
                            lan_ghep_truoc     = tong_truoc // 100
                            manh_con_lai_truoc = tong_truoc % 100
                            # Xóa số lớp linh căn thừa (từ phía cuối)
                            lan_xoa = so_lan_ghep - lan_ghep_truoc
                            if lan_xoa > 0:
                                new_lc = list(lc_so_huu_r)
                                for _ in range(lan_xoa):
                                    try:
                                        i = len(new_lc) - 1 - new_lc[::-1].index(key)
                                        new_lc.pop(i)
                                    except ValueError:
                                        break
                                lc_so_huu_r = new_lc
                                if key not in lc_so_huu_r:
                                    lc_diem_r.pop(key, None)
                            # Trả lại số mảnh đúng trước khi nhận
                            if manh_con_lai_truoc > 0:
                                manh[key] = manh_con_lai_truoc
                            else:
                                manh.pop(key, None)
                        changed = True

                if changed:
                    await conn.execute(
                        """UPDATE tu_si SET
                               manh_linh_can=$1, linh_can_diem=$2, linh_can_so_huu=$3
                           WHERE user_id=$4""",
                        json.dumps(manh), json.dumps(lc_diem_r),
                        json.dumps(lc_so_huu_r), recv_id)

            # ── Xóa phiên chợ của acc này ────────────────────────────────────
            await conn.execute("DELETE FROM phien_cho WHERE nguoi_ban=$1", user_id)

            # ── Xóa giao dịch log 36h của acc này ───────────────────────────
            await conn.execute(
                """DELETE FROM giao_dich_log
                   WHERE (sender_id=$1 OR receiver_id=$1) AND thoi_gian >= $2""",
                user_id, cutoff)

            # ── Reset nhân vật về Luyện Khí Sơ Kỳ ───────────────────────────
            await conn.execute("""
                UPDATE tu_si SET
                    canh_gioi=0, cap_nho=1, exp=0,
                    hp=100, hp_max=100, cong=10, thu=5,
                    linh_thach=0,
                    phap_bao='[]', phap_bao_active=-1,
                    yeu_thu='[]', yeu_thu_active=-1,
                    dan_duoc='{}', nguyen_lieu='{}',
                    thang_pvp=0, thua_pvp=0,
                    cd_tu_luyen=0, cd_dot_pha=0, cd_khai_hoang=0,
                    cd_bi_canh=0, cd_diem_danh=0, chuoi_diem_danh=0,
                    tong_tu_luyen=0, danh_hieu_hien='',
                    the_luc=250, the_luc_cap_nhat=0,
                    tran_the_luc=0, tran_the_luc_cap_nhat=0,
                    cong_phap_so_huu='[]', cong_phap_trang_bi='{}',
                    cong_phap_tang='{}', cong_phap_hoc='[]', cong_phap_active=-1,
                    bc_thua_lan_truoc=0, tong_tu_vi=0,
                    linh_luc=0, hoi_tam=0, ho_tam=0, bao_kich=0, khang_bao=0,
                    linh_can_diem=$1, manh_linh_can='{}',
                    linh_qua='{}', linh_can_lop2='{}',
                    banner_id=0,
                    so_lan_trung_sinh=$2, ti_le_van_dinh=$3,
                    van_dinh_all_stat_pct=$4
                WHERE user_id=$5
            """, json.dumps(lc_diem_reset), so_lan_moi, ti_le_moi, vd_bonus_moi, user_id)

            ts_new = await conn.fetchrow("SELECT * FROM tu_si WHERE user_id=$1", user_id)
            return dict(ts_new) if ts_new else {}
