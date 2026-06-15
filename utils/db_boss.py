from __future__ import annotations
import logging
import json
from utils.database import get_pool

log = logging.getLogger("database")


# ══════════════════════════════════════════════════════
#  BOSS STATE
# ══════════════════════════════════════════════════════
async def get_boss_state(boss_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM boss_state WHERE boss_id=$1", boss_id)
        if row:
            d = dict(row)
            d["nguoi_tan_cong"] = json.loads(d["nguoi_tan_cong"] or "{}")
            return d
    return None


async def upsert_boss(boss_id: int, hp_hien: int, spawn_time: int, nguoi_tan_cong: dict,
                      canh_gioi: int = 3, message_id: int = 0, channel_id: int = 0):
    ntc_json = json.dumps(nguoi_tan_cong, ensure_ascii=False)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_state (boss_id, hp_hien, spawn_time, nguoi_tan_cong, canh_gioi, message_id, channel_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (boss_id) DO UPDATE SET
                hp_hien         = EXCLUDED.hp_hien,
                nguoi_tan_cong  = EXCLUDED.nguoi_tan_cong,
                message_id      = CASE WHEN EXCLUDED.message_id != 0 THEN EXCLUDED.message_id ELSE boss_state.message_id END,
                channel_id      = CASE WHEN EXCLUDED.channel_id != 0 THEN EXCLUDED.channel_id ELSE boss_state.channel_id END
        """, boss_id, hp_hien, spawn_time, ntc_json, canh_gioi, message_id, channel_id)


async def spawn_boss(boss_id: int, hp_hien: int, spawn_time: int, nguoi_tan_cong: dict,
                     canh_gioi: int = 3, message_id: int = 0, channel_id: int = 0):
    ntc_json = json.dumps(nguoi_tan_cong, ensure_ascii=False)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_state (boss_id, hp_hien, spawn_time, nguoi_tan_cong, canh_gioi, message_id, channel_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (boss_id) DO UPDATE SET
                hp_hien        = EXCLUDED.hp_hien,
                spawn_time     = EXCLUDED.spawn_time,
                nguoi_tan_cong = EXCLUDED.nguoi_tan_cong,
                canh_gioi      = EXCLUDED.canh_gioi,
                message_id     = EXCLUDED.message_id,
                channel_id     = EXCLUDED.channel_id
        """, boss_id, hp_hien, spawn_time, ntc_json, canh_gioi, message_id, channel_id)


async def save_boss_guild_message(boss_id: int, guild_id: int, msg_id: int, channel_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_guild_messages (boss_id, guild_id, msg_id, channel_id)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (boss_id, guild_id) DO UPDATE SET
                msg_id     = EXCLUDED.msg_id,
                channel_id = EXCLUDED.channel_id
        """, boss_id, guild_id, msg_id, channel_id)


async def get_boss_guild_messages(boss_id: int) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT guild_id, msg_id, channel_id FROM boss_guild_messages WHERE boss_id=$1", boss_id
        )
        return [(r["guild_id"], r["msg_id"], r["channel_id"]) for r in rows]


async def clear_boss_guild_messages(boss_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM boss_guild_messages WHERE boss_id=$1", boss_id)


async def save_boss_message_id(boss_id: int, message_id: int, channel_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE boss_state SET message_id=$1, channel_id=$2 WHERE boss_id=$3",
            message_id, channel_id, boss_id
        )


async def set_boss_end_time(boss_id: int, end_time: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE boss_state SET end_time=$1 WHERE boss_id=$2", end_time, boss_id
        )
        # Lưu spawn_time đã kết thúc vào boss_ended_spawns để tra cứu sau khi boss_state bị reset
        row = await conn.fetchrow("SELECT spawn_time FROM boss_state WHERE boss_id=$1", boss_id)
        if row and row["spawn_time"] and row["spawn_time"] > 0:
            await conn.execute("""
                INSERT INTO boss_ended_spawns (boss_id, spawn_time, end_time)
                VALUES ($1, $2, $3)
                ON CONFLICT (boss_id, spawn_time) DO UPDATE SET end_time = EXCLUDED.end_time
            """, boss_id, row["spawn_time"], end_time)


async def set_boss_killer_atomic(boss_id: int, killer_uid: int, total_dmg: int,
                                  spawn_time: int, log_entry: str) -> bool:
    """Cập nhật HP boss, set _killer, và thêm log entry — atomic với row-level lock.

    Trả về True nếu đây là người đánh hạ boss (hp sau <= 0),
    False nếu boss đã chết trước (bởi người khác) hoặc vẫn còn sống.

    Dùng FOR UPDATE để tránh race condition: chỉ 1 request thắng cuộc đua set _killer.
    """
    import json as _j
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT hp_hien, nguoi_tan_cong, spawn_time FROM boss_state WHERE boss_id=$1 FOR UPDATE",
                boss_id
            )
            if not row:
                return False

            hp_hien   = row["hp_hien"]
            spawn_db  = row["spawn_time"]
            ntc       = _j.loads(row["nguoi_tan_cong"] or "{}")

            # Nếu spawn_time không khớp → spawn đã reset (boss đã chết, spawn mới)
            if spawn_db != spawn_time:
                return False

            uid_str = str(killer_uid)
            ntc[uid_str] = ntc.get(uid_str, 0) + total_dmg

            hp_new   = max(0, hp_hien - total_dmg)
            is_kill  = hp_new <= 0

            if is_kill and "_killer" not in ntc:
                ntc["_killer"] = killer_uid

            # Cập nhật log (5 entries cuối)
            prev_log = ntc.get("_log", [])
            if not isinstance(prev_log, list):
                prev_log = []
            ntc["_log"] = (prev_log + [log_entry])[-5:]

            await conn.execute(
                "UPDATE boss_state SET hp_hien=$1, nguoi_tan_cong=$2 WHERE boss_id=$3",
                hp_new, _j.dumps(ntc, ensure_ascii=False), boss_id
            )

    return is_kill


async def get_boss_message_id(boss_id: int) -> tuple[int, int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT message_id, channel_id FROM boss_state WHERE boss_id=$1", boss_id
        )
        return (row["message_id"] or 0, row["channel_id"] or 0) if row else (0, 0)


async def add_boss_damage(boss_id: int, user_id: int, damage: int, spawn_time: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO boss_tham_gia (boss_id, user_id, spawn_time, tong_damage)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (boss_id, user_id, spawn_time) DO UPDATE SET
                tong_damage = boss_tham_gia.tong_damage + $4
        """, boss_id, user_id, spawn_time, damage)


async def has_nhan_thuong(boss_id: int, user_id: int, spawn_time: int = 0) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT da_nhan FROM boss_tham_gia WHERE boss_id=$1 AND user_id=$2 AND spawn_time=$3",
            boss_id, user_id, spawn_time
        )
        return bool(row and row["da_nhan"])


async def mark_nhan_thuong(boss_id: int, user_id: int, spawn_time: int = 0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE boss_tham_gia SET da_nhan=1 WHERE boss_id=$1 AND user_id=$2 AND spawn_time=$3",
            boss_id, user_id, spawn_time
        )


async def get_boss_leaderboard(boss_id: int, spawn_time: int = 0) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, SUM(tong_damage) as tong_damage
            FROM boss_tham_gia
            WHERE boss_id=$1 AND spawn_time=$2
            GROUP BY user_id
            ORDER BY tong_damage DESC
        """, boss_id, spawn_time)
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════
#  GUILD CONFIG
# ══════════════════════════════════════════════════════
async def get_boss_channel(guild_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT boss_channel_id FROM guild_config WHERE guild_id=$1", guild_id
        )
        return row["boss_channel_id"] if row else 0


async def set_boss_channel(guild_id: int, channel_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_config (guild_id, boss_channel_id)
            VALUES ($1,$2)
            ON CONFLICT (guild_id) DO UPDATE SET boss_channel_id = EXCLUDED.boss_channel_id
        """, guild_id, channel_id)


# ══════════════════════════════════════════════════════
#  BOSS DATA CLEANUP
# ══════════════════════════════════════════════════════


async def is_boss_spawn_ended(boss_id: int, spawn_time: int) -> bool:
    """Kiểm tra spawn_time này đã kết thúc chưa (dùng boss_ended_spawns, không phụ thuộc boss_state)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT end_time FROM boss_ended_spawns WHERE boss_id=$1 AND spawn_time=$2",
            boss_id, spawn_time)
        return bool(row)

async def get_unclaimed_boss_spawns(user_id: int) -> list:
    """Trả về list các (boss_id, spawn_time, tong_damage) mà user đã tham gia nhưng chưa nhận thưởng.
    Query trực tiếp boss_tham_gia — không phụ thuộc vào boss_state.spawn_time (có thể đã bị reset).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT boss_id, spawn_time, tong_damage
            FROM boss_tham_gia
            WHERE user_id=$1 AND da_nhan=0 AND spawn_time > 0
            ORDER BY spawn_time DESC
        """, user_id)
        return [dict(r) for r in rows]

async def cleanup_old_boss_data(days: int = 2):
    """Xóa boss_tham_gia của các lần spawn cũ hơn N ngày — chạy định kỳ."""
    import time as _t
    cutoff = int(_t.time()) - days * 86400
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM boss_tham_gia WHERE spawn_time < $1", cutoff)
    log.info(f"[BossClean] Đã xóa boss_tham_gia cũ hơn {days} ngày (cutoff={cutoff})")


async def clear_boss_data(boss_id: int, purge_rewards: bool = True):
    """Reset boss state để spawn mới.
    purge_rewards=True (default): XÓA boss_tham_gia — reset hoàn toàn mỗi spawn.
    purge_rewards=False: GIỮ boss_tham_gia (legacy path — không dùng nữa).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if purge_rewards:
            await conn.execute("DELETE FROM boss_tham_gia WHERE boss_id=$1", boss_id)
        await conn.execute(
            "UPDATE boss_state SET nguoi_tan_cong='{}', message_id=0, channel_id=0, hp_hien=0, spawn_time=0 WHERE boss_id=$1",
            boss_id
        )
    log.info(f"[BossClean] Reset boss_id={boss_id} (purge_rewards={purge_rewards})")


async def claim_first_hit_reward(boss_id: int, user_id: int, spawn_time: int,
                                  lt: int, exp: int) -> bool:
    """Trao thưởng first-hit atomic — chỉ thành công 1 lần duy nhất per user/boss/spawn.
    Dùng INSERT ON CONFLICT DO NOTHING: nếu row đã có → trả False (đã nhận rồi).
    Trả về True nếu vừa insert (= first hit thực sự), False nếu đã tồn tại."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            result = await conn.execute("""
                INSERT INTO boss_tham_gia (boss_id, user_id, spawn_time, tong_damage, da_nhan)
                VALUES ($1,$2,$3,0,1)
                ON CONFLICT (boss_id, user_id, spawn_time) DO NOTHING
            """, boss_id, user_id, spawn_time)
            # rowcount=1 nghĩa là vừa INSERT thành công = first hit
            inserted = result == "INSERT 0 1"
            if inserted:
                await conn.execute(
                    "UPDATE tu_si SET linh_thach=linh_thach+$1, exp=exp+$2 WHERE user_id=$3",
                    lt, exp, user_id)
    return inserted
