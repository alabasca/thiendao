"""Shared Embed Builders"""
from typing import Any
import discord

def e_loi(tieu_de: str, noi_dung: str) -> discord.Embed:
    return discord.Embed(title=f"❌ {tieu_de}", description=noi_dung, color=0xED4245)

def e_ok(tieu_de: str, noi_dung: str) -> discord.Embed:
    return discord.Embed(title=f"✅ {tieu_de}", description=noi_dung, color=0x57F287)

def e_warn(tieu_de: str, noi_dung: str) -> discord.Embed:
    return discord.Embed(title=f"⚠️ {tieu_de}", description=noi_dung, color=0xFEE75C)

def e_info(tieu_de: str, noi_dung: str = "") -> discord.Embed:
    return discord.Embed(title=tieu_de, description=noi_dung, color=0x5865F2)

def owner_only_check(owner_ids: int | set[int]):
    """App command check - chỉ owner(s)"""
    import discord.app_commands as ac
    ids = {owner_ids} if isinstance(owner_ids, int) else owner_ids
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id not in ids:
            await interaction.response.send_message(
                embed=e_loi("Không Có Quyền", "Lệnh này chỉ dành cho **Thiên Đế**!"),
                ephemeral=True
            )
            return False
        return True
    return ac.check(predicate)

import logging as _logging
_log_safe = _logging.getLogger("safe_followup")


async def safe_followup(inter: discord.Interaction, *args: Any, **kwargs: Any) -> discord.Message | None:
    """followup.send an toàn — bỏ qua nếu interaction token expire (404/10015/10062).
    Trả về discord.Message nếu thành công, None nếu thất bại.
    """
    try:
        return await inter.followup.send(*args, **kwargs)
    except discord.NotFound as e:
        if e.code in (10015, 10062):
            _log_safe.debug(f"safe_followup: interaction expired ({e.code}), skipping")
            return None
        raise
    except discord.HTTPException as e:
        if e.status == 401 or getattr(e, "code", 0) == 50027:
            _log_safe.debug("safe_followup: webhook token invalid, skipping")
            return None
        raise
    except Exception as e:
        _log_safe.debug(f"safe_followup: unexpected error: {e}")
        return None


async def safe_defer(inter, *, ephemeral: bool = False, thinking: bool = False) -> bool:
    """defer() an toàn — trả về False nếu interaction đã hết hạn (10062).
    Dùng thay cho bare await inter.response.defer() để tránh ERROR spam.

    Cách dùng:
        if not await safe_defer(inter, ephemeral=True):
            return
    """
    try:
        await inter.response.defer(ephemeral=ephemeral, thinking=thinking)
        return True
    except discord.InteractionResponded:
        # Interaction đã được ACK trước đó (vd: callback đã defer) -> vẫn tiếp tục flow.
        _log_safe.debug("safe_defer: interaction already responded, continue")
        return True
    except discord.NotFound:
        _log_safe.debug("safe_defer: interaction expired (10062), skipping")
        return False
    except discord.HTTPException as e:
        if e.status in (400, 401):
            _log_safe.debug(f"safe_defer: HTTPException {e.status}, skipping")
            return False
        raise
