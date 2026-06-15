"""
COG: Admin Give
Commands: /give linhthach, /give tuvi, /give phapbao, /give linhcan, /give hp, /give dan, /give reset, /give all
Chỉ OWNER_ID mới dùng được
"""
import logging
log = logging.getLogger("give")
import discord
from discord import app_commands
from discord.ext import commands

import random
from utils.config import (
    OWNER_IDS, CANH_GIOI, PHAP_BAO, PHAP_BAO_BY_BASE, PHAP_BAO_BY_ID, LINH_CAN, LINH_CAN_BY_ID,
    THE_CHAT, THE_CHAT_BY_ID, DAN_DUOC,
    BOSS_THE_GIOI, BOSS_HP_BY_CG,
    LINH_QUA, LINH_QUA_BY_ID, MANH_LINH_CAN_EMOJI, DOTPHA_TC_NGUYEN_LIEU,
    SUNG_THU, SUNG_THU_BY_ID,
    NGUYEN_LIEU,
    hp_max_cong_thuc, cong_cong_thuc, thu_cong_thuc,
    get_cg, get_cg_ten, fmt, exp_can_thiet,
)
from utils.database import get_tu_si, update_tu_si, delete_tu_si, spawn_boss, the_luc_toi_da
from utils.embeds import e_loi, e_ok, owner_only_check
from utils.emoji_manager import get_stat_emoji
from utils.bot_emojis import (
    E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU,
    E_LINH_THACH, E_TT_LINH_THACH, E_TU_VI,
)
from utils.embeds import safe_followup


def _give_embed(target: discord.Member, loai: str, noi_dung: str) -> discord.Embed:
    embed = discord.Embed(
        title="⚡ THIÊN ĐẾ BAN THƯỞNG",
        description="```\n  ╔══════════════════════╗\n  ║  THIÊN ĐẠO SẮC PHONG  ║\n  ╚══════════════════════╝\n```",
        color=0xFFD700
    )
    embed.add_field(name="👤 Người Nhận", value=f"**{target.display_name}**", inline=True)
    embed.add_field(name=f"✦ {loai}", value=noi_dung, inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text="Thiên Đế ban ân, vạn dân quy phục.")
    return embed


give_group = app_commands.Group(name="give", description="[Admin] Ban thưởng cho tu sĩ")


@give_group.command(name="linhthach", description="Give linh thạch")
@app_commands.describe(nguoi_dung="Người nhận", so_luong="Số lượng (âm = trừ)")
@owner_only_check(OWNER_IDS)
async def give_lt(inter: discord.Interaction, nguoi_dung: discord.Member, so_luong: int):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts: return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    new_val = max(0, ts["linh_thach"] + so_luong)
    await update_tu_si(nguoi_dung.id, linh_thach=new_val)
    sign = "+" if so_luong >= 0 else ""
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Linh Thạch",
        f"**{sign}{fmt(so_luong)}** {E_LINH_THACH}\nTổng: **{fmt(new_val)}** {E_LINH_THACH}"))


@give_group.command(name="tuvi", description="Set cảnh giới")
@app_commands.describe(nguoi_dung="Người nhận", canh_gioi="0=Luyện Khí…9=Đăng Tiên", cap_nho="1-9")
@owner_only_check(OWNER_IDS)
async def give_tv(inter: discord.Interaction, nguoi_dung: discord.Member,
                  canh_gioi: app_commands.Range[int,0,9], cap_nho: app_commands.Range[int,1,9]):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts: return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    cap_nho = min(cap_nho, CANH_GIOI[canh_gioi]["cap"])
    new_hp  = hp_max_cong_thuc(canh_gioi, cap_nho)
    new_at  = cong_cong_thuc(canh_gioi, cap_nho)
    new_def = thu_cong_thuc(canh_gioi, cap_nho)
    await update_tu_si(nguoi_dung.id, canh_gioi=canh_gioi, cap_nho=cap_nho, exp=0,
                        hp=new_hp, hp_max=new_hp, cong=new_at, thu=new_def)
    cg = get_cg(canh_gioi)
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Tu Vi",
        f"{cg['emoji']} **{get_cg_ten(canh_gioi, cap_nho)}**\nHP:{new_hp} {E_CONG_KICH}{new_at} {E_PHONG_NGU}{new_def}"))


@give_group.command(name="phapbao", description="[Admin] Give pháp bảo (id 0-89, id_base 0-9, canh_gioi 0-8)")
@app_commands.describe(
    pb_id="ID pháp bảo (0-89) — hoặc dùng id_base + canh_gioi",
    id_base="Loại pháp bảo (0=Hiệu Giác … 9=Cổ Cầm)",
    canh_gioi="Cảnh giới pháp bảo (0-8)")
@owner_only_check(OWNER_IDS)
async def give_pb(inter: discord.Interaction, nguoi_dung: discord.Member,
                  pb_id: int = -1, id_base: int = -1, canh_gioi: int = -1):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts: return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    # Resolve pb_id
    if pb_id < 0:
        if id_base < 0 or canh_gioi < 0:
            return await safe_followup(inter, embed=e_loi("Lỗi", "Nhập pb_id (0-89) hoặc id_base + canh_gioi!"))
        pool = PHAP_BAO_BY_BASE.get(id_base, [])
        pb = next((p for p in pool if p["canh_gioi"] == canh_gioi), None)
        if not pb:
            return await safe_followup(inter, embed=e_loi("Lỗi", f"Không tìm thấy pháp bảo id_base={id_base} CG{canh_gioi}!"))
        pb_id = pb["id"]
    pb = PHAP_BAO_BY_ID.get(pb_id)
    if not pb:
        return await safe_followup(inter, embed=e_loi("Lỗi", f"ID {pb_id} không tồn tại (0-89)!"))
    await update_tu_si(nguoi_dung.id, phap_bao=ts["phap_bao"] + [pb_id])
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Pháp Bảo",
        f"{pb['emoji']} **{pb['ten']}** (CG{pb['canh_gioi']})\n{E_CONG_KICH}+{pb['at']} {E_PHONG_NGU}+{pb['df']}"))


@give_group.command(name="linhcan", description="Thêm linh căn cho người chơi")
@app_commands.choices(linh_can=[
    app_commands.Choice(name=f"{lc['emoji']} {lc['ten']} ({lc['loai']})", value=lc["id"])
    for lc in LINH_CAN
])
@owner_only_check(OWNER_IDS)
async def give_lc(inter: discord.Interaction, nguoi_dung: discord.Member, linh_can: str):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts: return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    lc = LINH_CAN_BY_ID.get(linh_can)
    if not lc:
        return await safe_followup(inter, embed=e_loi("Lỗi", f"Linh căn không hợp lệ!"))
    so_huu = ts.get("linh_can_so_huu", [])
    if linh_can in so_huu:
        return await safe_followup(inter, embed=e_loi("Đã Có", f"Đã sở hữu **{lc['ten']}**!"))
    so_huu = so_huu + [linh_can]
    diem = ts.get("linh_can_diem", {}).copy()
    diem[linh_can] = diem.get(linh_can, 0)
    await update_tu_si(nguoi_dung.id, linh_can_so_huu=so_huu, linh_can_diem=diem)
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Linh Căn",
        f"{lc['emoji']} **{lc['ten']}** đã được thêm vào!"))


@give_group.command(name="dan", description="Give đan dược")
@app_commands.describe(nguoi_dung="Người nhận", dan_id="ID đan dược", so_luong="Số lượng")
@owner_only_check(OWNER_IDS)
async def give_dan(inter: discord.Interaction, nguoi_dung: discord.Member,
                   dan_id: app_commands.Range[int,0,9],
                   so_luong: app_commands.Range[int,1,999] = 1):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts: return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    dd = ts["dan_duoc"].copy()
    dd[str(dan_id)] = dd.get(str(dan_id), 0) + so_luong
    await update_tu_si(nguoi_dung.id, dan_duoc=dd)
    dan = DAN_DUOC[dan_id]
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Đan Dược",
        f"{dan['emoji']} **{dan['ten']}** ×{so_luong}"))





@give_group.command(name="theluc", description="Set/cộng thể lực (0 = full 250)")
@app_commands.describe(nguoi_dung="Người nhận", so_luong="Số lượng cộng thêm (0 = full)")
@owner_only_check(OWNER_IDS)
async def give_tl(inter: discord.Interaction, nguoi_dung: discord.Member,
                  so_luong: int = 0):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts: return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    tl_max = the_luc_toi_da(ts.get("canh_gioi", 0))
    new_tl = tl_max if so_luong == 0 else min(tl_max, ts["the_luc"] + so_luong)
    now_ts = int(__import__("time").time())
    await update_tu_si(nguoi_dung.id, the_luc=new_tl, the_luc_cap_nhat=now_ts)
    sign = "→ Full" if so_luong == 0 else f"+{so_luong}"
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Thể Lực",
        f"⚡ **{sign}** → **{new_tl}/{tl_max} ⚡**"))


@give_group.command(name="reset", description="Xóa hoàn toàn nhân vật — user tạo lại bằng /hoso")
@owner_only_check(OWNER_IDS)
async def give_reset(inter: discord.Interaction, nguoi_dung: discord.Member):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, embed=e_loi("Lỗi", "User chưa có nhân vật!"), ephemeral=True)
    dao_hieu = ts["dao_hieu"]
    await delete_tu_si(nguoi_dung.id)
    embed = discord.Embed(
        title="🗑️ ĐÃ XÓA NHÂN VẬT",
        description=(
            f"Nhân vật **{dao_hieu}** của {nguoi_dung.mention} đã bị xóa hoàn toàn.\n"
            f"User có thể dùng **/hoso** để tạo nhân vật mới."
        ),
        color=0xED4245)
    embed.set_thumbnail(url=nguoi_dung.display_avatar.url)
    await safe_followup(inter, embed=embed, ephemeral=True)


@give_group.command(name="world_boss", description="[Admin] Spawn boss thế giới để test")
@app_commands.describe(boss_id="0=Hình Thiên 1=Trường Thừa 2=Đào Ngột 3=Kế Mông (-1=random)", canh_gioi="Cảnh giới boss (3-6, -1=random)")
@owner_only_check(OWNER_IDS)
async def give_world_boss(inter: discord.Interaction, boss_id: int = -1, canh_gioi: int = -1):
    await inter.response.defer(ephemeral=True)
    if boss_id < 0 or boss_id >= len(BOSS_THE_GIOI):
        boss_id = random.randint(0, len(BOSS_THE_GIOI) - 1)
    boss_cfg = BOSS_THE_GIOI[boss_id]
    # Chỉ cho phép canh_gioi trong pool của boss đó
    if canh_gioi not in boss_cfg["canh_gioi_pool"]:
        canh_gioi = random.choice(boss_cfg["canh_gioi_pool"])
    hp_max   = BOSS_HP_BY_CG.get(canh_gioi, boss_cfg["hp_max"])
    now_ts   = int(__import__("time").time())
    # Clear trước — reset hoàn toàn, không giữ data cũ
    from utils.database import clear_boss_data as _cbd_give
    for _b_g in BOSS_THE_GIOI:
        await _cbd_give(_b_g["id"], purge_rewards=True)
    # Ghi vào DB: spawn ngay, hp full, cảnh giới đã chọn
    await spawn_boss(boss_id, hp_max, now_ts, {}, canh_gioi=canh_gioi)
    cg_obj = CANH_GIOI[canh_gioi]

    # Lấy boss channel đã setup — bắt buộc phải có
    from cogs.views.boss import _build_initial_boss_message
    from utils.database import get_boss_channel as _get_bc
    boss_ch = None
    if inter.guild:
        ch_id = await _get_bc(inter.guild.id)
        if ch_id:
            boss_ch = inter.guild.get_channel(ch_id) or inter.guild.get_thread(ch_id)

    if boss_ch is None:
        return await safe_followup(inter, 
            "❌ Chưa set boss channel! Dùng `/setbosschannel` trước.", ephemeral=True)

    # Confirm cho admin (ephemeral)
    await safe_followup(inter, 
        f"✅ Đã spawn **{boss_cfg['emoji']} {boss_cfg['ten']}** "
        f"CG **{cg_obj['emoji']} {cg_obj['ten']}** HP **{fmt(hp_max)}** "
        f"→ {boss_ch.mention}",
        ephemeral=True)

    # Gửi message boss public — tất cả guild có set channel
    from utils.database import get_boss_channel as _get_bc2
    for _g in inter.client.guilds:
        _cid = await _get_bc2(_g.id)
        _ch  = _g.get_channel(_cid) or _g.get_thread(_cid) if _cid else None
        if _ch:
            try:
                await _build_initial_boss_message(
                    inter.client, _ch, boss_cfg, canh_gioi, hp_max, now_ts,
                    is_new_spawn=False)  # clear đã thực hiện trước spawn_boss
            except Exception:
                log.exception("Lỗi give")


@give_group.command(name="thechat", description="[Owner] Đổi/xóa thể chất cho người chơi")
@app_commands.describe(
    nguoi_dung="Người chơi cần đổi thể chất",
    the_chat_id="ID thể chất (để trống để xem danh sách)",
    xoa="True = xóa thể chất hiện tại (về chưa có)"
)
@owner_only_check(OWNER_IDS)
async def give_the_chat(inter: discord.Interaction, nguoi_dung: discord.Member,
                        the_chat_id: str = "", xoa: bool = False):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, "❌ Người chơi chưa có hồ sơ!", ephemeral=True)
    old_tc   = THE_CHAT_BY_ID.get(ts.get("the_chat", ""))
    old_name = f"{old_tc['emoji']} {old_tc['ten']}" if old_tc else "*(chưa có)*"
    # Xóa thể chất
    if xoa:
        await update_tu_si(nguoi_dung.id, the_chat="")
        embed = _give_embed(nguoi_dung, "Xóa Thể Chất", f"{old_name} → *(chưa có)*")
        return await safe_followup(inter, embed=embed, ephemeral=True)
    # Liệt kê danh sách nếu không nhập id
    if not the_chat_id:
        lines = [f"`{tc['id']}` — {tc['emoji']} {tc['ten']} [{tc['rate']}%]" for tc in THE_CHAT]
        embed = discord.Embed(title="🧬 Danh Sách Thể Chất", description="\n".join(lines), color=0x5865F2)
        return await safe_followup(inter, embed=embed, ephemeral=True)
    tc = THE_CHAT_BY_ID.get(the_chat_id)
    if not tc:
        ids = ", ".join(f"`{t['id']}`" for t in THE_CHAT)
        return await safe_followup(inter, f"❌ Không tìm thấy thể chất `{the_chat_id}`.\nCác ID hợp lệ: {ids}", ephemeral=True)
    await update_tu_si(nguoi_dung.id, the_chat=the_chat_id)
    embed = _give_embed(nguoi_dung, "Đổi Thể Chất",
        f"{old_name} → {tc['emoji']} **{tc['ten']}**")
    await safe_followup(inter, embed=embed, ephemeral=True)


@give_group.command(name="removelinhcan", description="[Owner] Xóa linh căn khỏi người chơi")
@app_commands.describe(nguoi_dung="Người chơi", linh_can="ID linh căn cần xóa (để trống = xóa tất cả)")
@app_commands.choices(linh_can=[
    app_commands.Choice(name=f"{lc['emoji']} {lc['ten']}", value=lc["id"])
    for lc in LINH_CAN
])
@owner_only_check(OWNER_IDS)
async def remove_lc(inter: discord.Interaction, nguoi_dung: discord.Member, linh_can: str = ""):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, "❌ Người chơi chưa có hồ sơ!", ephemeral=True)
    so_huu = ts.get("linh_can_so_huu", [])
    diem   = ts.get("linh_can_diem", {}).copy()
    if not linh_can:
        # Xóa tất cả
        if not so_huu:
            return await safe_followup(inter, "❌ Người chơi không có linh căn nào!", ephemeral=True)
        old_names = ", ".join(LINH_CAN_BY_ID[i]["ten"] for i in so_huu if i in LINH_CAN_BY_ID)
        await update_tu_si(nguoi_dung.id, linh_can_so_huu=[], linh_can_diem={})
        return await safe_followup(inter, 
            f"✅ Đã xóa tất cả linh căn của **{nguoi_dung.display_name}**:\n{old_names}", ephemeral=True)
    # Xóa 1 linh căn cụ thể
    if linh_can not in so_huu:
        return await safe_followup(inter, f"❌ Người chơi không sở hữu linh căn này!", ephemeral=True)
    so_huu = [i for i in so_huu if i != linh_can]
    diem.pop(linh_can, None)
    await update_tu_si(nguoi_dung.id, linh_can_so_huu=so_huu, linh_can_diem=diem)
    lc = LINH_CAN_BY_ID[linh_can]
    await safe_followup(inter, 
        f"✅ Đã xóa {lc['emoji']} **{lc['ten']}** khỏi **{nguoi_dung.display_name}**.", ephemeral=True)


@give_group.command(name="nguyenlieu", description="[Owner] Give nguyên liệu")
@app_commands.describe(nguoi_dung="Người nhận", nl_id="ID nguyên liệu (0-5)", so_luong="Số lượng")
@owner_only_check(OWNER_IDS)
async def give_nl(inter: discord.Interaction, nguoi_dung: discord.Member,
                  nl_id: app_commands.Range[int,0,5],
                  so_luong: app_commands.Range[int,1,9999] = 1):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, embed=e_loi("Loi", f"Chua tu tien!"), ephemeral=True)
    nl = NGUYEN_LIEU[nl_id]
    kho = ts.get("nguyen_lieu", {}).copy()
    kho[str(nl_id)] = kho.get(str(nl_id), 0) + so_luong
    await update_tu_si(nguoi_dung.id, nguyen_lieu=kho)
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Nguyen Lieu",
        f"{nl['emoji']} **{nl['ten']}** x{so_luong}"), ephemeral=True)

@give_group.command(name="dotphatcnl", description="[Owner] Give tai nguyen dot pha the chat")
@app_commands.describe(nguoi_dung="Nguoi nhan", so_luong="So luong moi loai (1-99)")
@owner_only_check(OWNER_IDS)
async def give_dtc_nl(inter: discord.Interaction, nguoi_dung: discord.Member,
                      so_luong: app_commands.Range[int,1,99] = 1):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, "Chua co ho so!", ephemeral=True)
    import json as _json
    raw = ts.get("dotpha_tc_nl", {})
    kho = raw if isinstance(raw, dict) else (_json.loads(raw) if raw else {})
    kho = kho.copy()
    for nl in DOTPHA_TC_NGUYEN_LIEU:
        kho[nl["id"]] = kho.get(nl["id"], 0) + so_luong
    await update_tu_si(nguoi_dung.id, dotpha_tc_nl=kho)
    lines = "\n".join(f"{nl['emoji']} {nl['ten']} x{so_luong}" for nl in DOTPHA_TC_NGUYEN_LIEU)
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Tai nguyen dot pha TC", lines), ephemeral=True)

@give_group.command(name="manhlinh", description="[Owner] Give manh linh can")
@app_commands.describe(nguoi_dung="Nguoi nhan", so_luong="So luong moi loai")
@owner_only_check(OWNER_IDS)
async def give_manh(inter: discord.Interaction, nguoi_dung: discord.Member,
                    so_luong: app_commands.Range[int,1,999] = 1):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, "Chua co ho so!", ephemeral=True)
    manh = ts.get("manh_linh_can", {}).copy()
    for k in MANH_LINH_CAN_EMOJI:
        manh[k] = manh.get(k, 0) + so_luong
    await update_tu_si(nguoi_dung.id, manh_linh_can=manh)
    lines = " ".join(f"{v} x{so_luong}" for v in MANH_LINH_CAN_EMOJI.values())
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Manh Linh Can", lines), ephemeral=True)

@give_group.command(name="linhqua", description="[Owner] Give linh qua")
@app_commands.describe(nguoi_dung="Nguoi nhan", so_luong="So luong moi loai")
@owner_only_check(OWNER_IDS)
async def give_lq(inter: discord.Interaction, nguoi_dung: discord.Member,
                  so_luong: app_commands.Range[int,1,999] = 1):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, "Chua co ho so!", ephemeral=True)
    lq = ts.get("linh_qua", {}).copy()
    for q in LINH_QUA:
        lq[q["id"]] = lq.get(q["id"], 0) + so_luong
    await update_tu_si(nguoi_dung.id, linh_qua=lq)
    lines = " ".join(f"{q['emoji']} x{so_luong}" for q in LINH_QUA)
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Linh Qua", lines), ephemeral=True)

@give_group.command(name="sungthuu", description="[Owner] Give sủng thú cho người chơi")
@app_commands.describe(nguoi_dung="Người nhận", sung_thu_id="ID sủng thú (0-17)")
@owner_only_check(OWNER_IDS)
async def give_st(inter: discord.Interaction, nguoi_dung: discord.Member,
                  sung_thu_id: app_commands.Range[int, 0, 17]):
    await inter.response.defer(ephemeral=False)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter, embed=e_loi("Lỗi", f"**{nguoi_dung.display_name}** chưa tu tiên!"))
    st = SUNG_THU_BY_ID.get(sung_thu_id)
    if not st:
        return await safe_followup(inter, embed=e_loi("Lỗi", f"ID {sung_thu_id} không tồn tại (0-17)!"))
    import json as _j, time as _t
    raw = ts.get("sung_thu", {})
    kho = raw if isinstance(raw, dict) else (_j.loads(raw) if raw else {})
    kho = kho.copy()
    if str(sung_thu_id) in kho:
        return await safe_followup(inter, embed=e_loi("Đã Có", f"Đã sở hữu **{st['ten']}** rồi!"))
    kho[str(sung_thu_id)] = {"level": 1, "obtained_at": int(_t.time())}
    await update_tu_si(nguoi_dung.id, sung_thu=kho)
    tier_str = "⭐ Thường" if st["tier"] == 1 else "💫 Huyền Thoại"
    await safe_followup(inter, embed=_give_embed(nguoi_dung, "Sủng Thú",
        f"{st['emoji']} **{st['ten']}** [{tier_str}]\nHệ: {st['he'].upper()}"))


# Thêm vào give.py trước class GiveCog

@give_group.command(name="wipe_server", description="[Owner] Xóa toàn bộ data nhân vật, giữ lại guild config & boss state")
@app_commands.describe(xac_nhan="Nhập 'XAC NHAN WIPE' để xác nhận (không thể hoàn tác!)")
@owner_only_check(OWNER_IDS)
async def give_wipe_server(inter: discord.Interaction, xac_nhan: str):
    await inter.response.defer(ephemeral=True)

    if xac_nhan.strip() != "XAC NHAN WIPE":
        return await safe_followup(inter, 
            "❌ Nhập sai xác nhận. Phải nhập chính xác: `XAC NHAN WIPE`",
            ephemeral=True)

    from utils.database import get_pool as _get_pool
    import json as _json

    pool = await _get_pool()
    async with pool.acquire() as conn:
        # Đếm trước khi xóa
        count_ts    = await conn.fetchval("SELECT COUNT(*) FROM tu_si")
        count_quan  = await conn.fetchval("SELECT COUNT(*) FROM quan_he")
        count_cho   = await conn.fetchval("SELECT COUNT(*) FROM phien_cho")
        count_boss  = await conn.fetchval("SELECT COUNT(*) FROM boss_tham_gia")
        count_tang  = await conn.fetchval("SELECT COUNT(*) FROM tang_qua_log")
        count_tong  = await conn.fetchval("SELECT COUNT(*) FROM tong_mon_thanh_vien")

        # Xóa data nhân vật
        await conn.execute("DELETE FROM tu_si")
        await conn.execute("DELETE FROM quan_he")
        await conn.execute("DELETE FROM phien_cho")
        await conn.execute("DELETE FROM boss_tham_gia")
        await conn.execute("DELETE FROM tang_qua_log")
        await conn.execute("DELETE FROM tong_mon_thanh_vien")
        await conn.execute("DELETE FROM reset_log")

        # Reset boss_state: clear damage data nhưng GIỮ cấu hình channel
        await conn.execute(
            "UPDATE boss_state SET hp_hien=0, nguoi_tan_cong='{}', spawn_time=0, end_time=0"
        )
        # GIỮ NGUYÊN: guild_config (boss channel), boss_guild_messages

    embed = discord.Embed(
        title="🗑️ WIPE SERVER HOÀN TẤT",
        color=0xED4245,
        description=(
            "Toàn bộ data nhân vật đã bị xóa sạch.\n"
            "Guild config & boss channel vẫn được giữ nguyên."
        )
    )
    embed.add_field(
        name="📊 Đã xóa",
        value=(
            f"👤 Tu sĩ: **{count_ts}** hồ sơ\n"
            f"💕 Quan hệ: **{count_quan}** cặp\n"
            f"🏪 Phiên chợ: **{count_cho}** item\n"
            f"⚔️ Boss tham gia: **{count_boss}** records\n"
            f"🎁 Tặng quà log: **{count_tang}** records\n"
            f"🏛️ Tông môn thành viên: **{count_tong}** records"
        ),
        inline=False
    )
    embed.add_field(
        name="✅ Giữ nguyên",
        value="Guild config (boss channel) • Boss state cơ bản • Boss guild messages",
        inline=False
    )
    embed.set_footer(text=f"Thực hiện bởi {inter.user} — không thể hoàn tác!")
    await safe_followup(inter, embed=embed, ephemeral=True)



@give_group.command(name="backup", description="[Owner] Backup toàn bộ DB → file JSON gửi lên Discord")
@owner_only_check(OWNER_IDS)
async def give_backup(inter: discord.Interaction):
    """Dump toàn bộ dữ liệu PostgreSQL ra file JSON và gửi lên channel hiện tại."""
    import json
    import io
    from datetime import datetime
    from utils.database import get_pool

    await inter.response.defer(ephemeral=True)

    BACKUP_TABLES = [
        "tu_si",
        "tong_mon_thanh_vien",
        "phien_cho",
        "boss_state",
        "boss_tham_gia",
        "boss_ended_spawns",
        "boss_guild_messages",
        "quan_he",
        "tang_qua_log",
        "giao_dich_log",
        "guild_config",
        "reset_log",
        "world_chat_channels",
        "cross_pvp_challenges",
        "active_vote",
    ]

    def _serialize(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return str(obj)

    try:
        pool = await get_pool()
        data = {}
        total_rows = 0
        skipped = []

        async with pool.acquire() as conn:
            existing = {
                r["tablename"]
                for r in await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                )
            }
            for table in BACKUP_TABLES:
                if table not in existing:
                    skipped.append(table)
                    continue
                rows = await conn.fetch(f"SELECT * FROM {table}")
                data[table] = [dict(r) for r in rows]
                total_rows += len(rows)

    except Exception as e:
        return await safe_followup(inter, embed=e_loi("❌ Lỗi Backup", str(e)), ephemeral=True)

    # Serialize sang JSON
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2, default=_serialize).encode("utf-8")
    size_kb = len(json_bytes) / 1024

    # Tên file theo thời gian
    ts = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"backup_{ts}.json"

    # Gửi file — nếu > 8MB thì Discord từ chối
    if len(json_bytes) > 8 * 1024 * 1024:
        return await safe_followup(inter,
            embed=e_loi("❌ File Quá Lớn",
                f"File backup {size_kb:.0f} KB vượt giới hạn 8MB của Discord.\n"
                "Dùng script backup_pg.py trực tiếp."),
            ephemeral=True)

    file_obj = discord.File(io.BytesIO(json_bytes), filename=filename)

    lines = [f"✅ Backup xong — **{total_rows}** rows — **{size_kb:.1f} KB**"]
    if skipped:
        lines.append(f"Bỏ qua (chưa có bảng): {', '.join(skipped)}")

    embed = discord.Embed(
        title="💾 Backup Hoàn Tất",
        description="\n".join(lines),
        color=0x2ECC71,
    )
    embed.set_footer(text=f"File: {filename}")

    # Gửi file ra channel (không ephemeral để có thể tải về)
    try:
        await inter.channel.send(
            content=f"📦 Backup DB — {inter.user.mention}",
            embed=embed,
            file=file_obj,
        )
        await safe_followup(inter, "✅ Đã gửi file backup ra channel!", ephemeral=True)
    except discord.Forbidden:
        # Nếu không gửi được channel thì fallback về followup (ephemeral, chỉ tải được 15 phút)
        file_obj2 = discord.File(io.BytesIO(json_bytes), filename=filename)
        await safe_followup(inter, content="✅ Backup xong (ephemeral — tải trong 15 phút):",
                            file=file_obj2, ephemeral=True)


@give_group.command(name="skipcddotpha", description="[Owner] Xóa cooldown đột phá cho người chơi")
@app_commands.describe(nguoi_dung="Tu sĩ cần skip cooldown đột phá")
@owner_only_check(OWNER_IDS)
async def give_skip_cd_dotpha(inter: discord.Interaction, nguoi_dung: discord.Member):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter,
            embed=e_loi("❌ Không Tìm Thấy", f"**{nguoi_dung.display_name}** chưa có hồ sơ tu tiên."),
            ephemeral=True)
    await update_tu_si(nguoi_dung.id, cd_dot_pha=0)
    embed = _give_embed(nguoi_dung, "Skip CD Đột Phá",
        f"✅ Cooldown đột phá của **{nguoi_dung.display_name}** đã được xóa!")
    await safe_followup(inter, embed=embed, ephemeral=True)


@give_group.command(name="fulltuvi", description="[Owner] Set tu vi đầy đủ để đột phá (đúng ngưỡng cảnh giới hiện tại)")
@app_commands.describe(nguoi_dung="Tu sĩ cần fill tu vi")
@owner_only_check(OWNER_IDS)
async def give_full_tuvi(inter: discord.Interaction, nguoi_dung: discord.Member):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter,
            embed=e_loi("❌ Không Tìm Thấy", f"**{nguoi_dung.display_name}** chưa có hồ sơ tu tiên."),
            ephemeral=True)
    ec = exp_can_thiet(ts["canh_gioi"], ts["cap_nho"])
    await update_tu_si(nguoi_dung.id, exp=ec)
    cg_ten = get_cg_ten(ts["canh_gioi"], ts["cap_nho"])
    embed = _give_embed(nguoi_dung, "Full Tu Vi",
        f"✅ Tu vi đã được set đầy đủ!\n**{cg_ten}**: **{fmt(ec)}** tu vi (đúng ngưỡng đột phá)")
    await safe_followup(inter, embed=embed, ephemeral=True)


@give_group.command(name="maxtuvi", description="[Owner] Tăng tu vi lên max 1 cảnh giới (hậu kì)")
@app_commands.describe(nguoi_dung="Tu sĩ cần tăng tu vi")
@owner_only_check(OWNER_IDS)
async def give_max_tuvi(inter: discord.Interaction, nguoi_dung: discord.Member):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter,
            embed=e_loi("❌ Không Tìm Thấy", f"**{nguoi_dung.display_name}** chưa có hồ sơ tu tiên."),
            ephemeral=True)
    cg    = ts["canh_gioi"]
    max_cap = CANH_GIOI[cg]["cap"]
    ec_max = exp_can_thiet(cg, max_cap)
    await update_tu_si(nguoi_dung.id, cap_nho=max_cap, exp=ec_max)
    cg_ten = get_cg_ten(cg, max_cap)
    embed = _give_embed(nguoi_dung, "Max Tu Vi Cảnh",
        f"✅ Đã tăng lên **{cg_ten}** với tu vi đầy đủ!\nTu vi: **{fmt(ec_max)}** (đỉnh cảnh giới {CANH_GIOI[cg]['ten']})")
    await safe_followup(inter, embed=embed, ephemeral=True)


@give_group.command(name="tongtuvi", description="[Owner] Cộng/trừ tổng tu vi tích lũy cho người chơi")
@app_commands.describe(nguoi_dung="Tu sĩ cần chỉnh tổng tu vi", so_luong="Số lượng (âm = trừ)")
@owner_only_check(OWNER_IDS)
async def give_tong_tuvi(inter: discord.Interaction, nguoi_dung: discord.Member, so_luong: int):
    await inter.response.defer(ephemeral=True)
    ts = await get_tu_si(nguoi_dung.id)
    if not ts:
        return await safe_followup(inter,
            embed=e_loi("❌ Không Tìm Thấy", f"**{nguoi_dung.display_name}** chưa có hồ sơ tu tiên."),
            ephemeral=True)
    cu = ts.get("tong_tu_vi", 0)
    moi = max(0, cu + so_luong)
    await update_tu_si(nguoi_dung.id, tong_tu_vi=moi)
    dau = "+" if so_luong >= 0 else ""
    embed = _give_embed(nguoi_dung, "Tổng Tu Vi",
        f"{dau}{fmt(so_luong)} tổng tu vi\n{fmt(cu)} → **{fmt(moi)}**")
    await safe_followup(inter, embed=embed, ephemeral=True)


class GiveCog(commands.Cog, name="Admin Give"):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.add_command(give_group)

        @give_group.error
        async def _give_error(inter: discord.Interaction, error: app_commands.AppCommandError):
            if not isinstance(error, app_commands.CheckFailure):
                try:
                    await safe_followup(inter, embed=e_loi("Loi", str(error)), ephemeral=True)
                except Exception:
                    log.exception("Lỗi give")

    async def cog_unload(self):
        self.bot.tree.remove_command("give")


async def setup(bot):
    await bot.add_cog(GiveCog(bot))
