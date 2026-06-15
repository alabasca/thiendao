from __future__ import annotations
from typing import Any

from cogs.views._common import *
from utils.embeds import e_loi, e_ok, e_warn, e_info
import os
import re as _re
import logging
from typing import TYPE_CHECKING
from utils.emoji_manager import get_stat_emoji
log = logging.getLogger("hoso")

if TYPE_CHECKING:
    from cogs.hoso import HoSoView

class DungDanView(discord.ui.View):
    def __init__(self, parent: HoSoView, ts: dict[str, Any], opts: list, actor_id: int = None):
        super().__init__(timeout=60)
        self.parent   = parent
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id
        sel = discord.ui.Select(placeholder="Chọn đan dược...", options=opts[:25], row=0)
        sel.callback = self._on_select
        self.add_item(sel)
        back = discord.ui.Button(label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=1)
        async def _do_back_1434(inter): await _back_to_hoso(inter, self.parent)
        back.callback = _do_back_1434
        self.add_item(back)

    async def _on_select(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.send_modal(DungDanModal(self.parent, int(inter.data["values"][0]), actor_id=self.actor_id))


class DungDanModal(discord.ui.Modal, title="Dùng Đan Dược"):
    so_luong = discord.ui.TextInput(
        label="Số lượng muốn dùng", placeholder="1", default="1",
        min_length=1, max_length=3)
    def __init__(self, parent: HoSoView, dan_id: int, actor_id: int = None):
        super().__init__()
        self.parent   = parent
        self.dan_id   = dan_id
        self.actor_id = actor_id or parent.owner_id

    async def on_submit(self, inter: discord.Interaction):
        try:    n = max(1, int(self.so_luong.value))
        except ValueError: return await inter.response.send_message("❌ Số không hợp lệ!", ephemeral=True)
        ts  = await get_tu_si(inter.user.id)
        dan = DAN_DUOC[self.dan_id]
        have = ts["dan_duoc"].get(str(self.dan_id), 0)
        n    = min(n, have)
        if n <= 0:
            return await inter.response.send_message("❌ Không đủ đan!", ephemeral=True)
        dd = ts["dan_duoc"].copy()
        dd[str(self.dan_id)] = have - n
        if dd[str(self.dan_id)] <= 0: del dd[str(self.dan_id)]
        await update_tu_si_wait(inter.user.id, exp=ts["exp"] + dan["exp"] * n, dan_duoc=dd)
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi tu_luyen")
        await safe_followup(inter, 
            embed=e_ok(f"{dan['emoji']} Dùng Đan!", f"{E_TU_VI} +{fmt(dan['exp'] * n)} tu vi  |  Còn {have - n} viên"),
            ephemeral=True)
        is_own = (inter.user.id == self.actor_id)
        if is_own:
            await self.parent._reload(inter.user.id)
            self.parent._rebuild()
            try:
                await inter.edit_original_response(embed=self.parent._current_embed(), view=self.parent)
            except Exception:
                log.exception("Lỗi tu_luyen")


# ══════════════════════════════════════════════════════════════
#  DÙNG ĐAN ĐỘT PHÁ VIEW
# ══════════════════════════════════════════════════════════════
class DungDotPhaView(discord.ui.View):
    """Dropdown dùng đan tu luyện (tiểu cảnh từ bí cảnh drop).
    Đột phá đại cảnh chỉ được thực hiện qua nút ⚡ Đột Phá trong tab Tu Luyện.
    """
    def __init__(self, parent: HoSoView, ts: dict[str, Any], opts: list, actor_id: int = None):
        super().__init__(timeout=60)
        self.parent   = parent
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id
        sel = discord.ui.Select(placeholder="Chọn đan tu luyện...", options=opts[:25], row=0)
        sel.callback = self._on_select
        self.add_item(sel)
        back = discord.ui.Button(label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=1)
        async def _do_back(inter): await _back_to_hoso(inter, self.parent)
        back.callback = _do_back
        self.add_item(back)

    async def _on_select(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        raw_key = inter.data["values"][0]
        ts = await get_tu_si(self.actor_id)
        if not ts:
            return await inter.response.send_message(
                embed=e_loi("❌ Lỗi", "Không tìm thấy dữ liệu tu sĩ."), ephemeral=True)

        # Chỉ xử lý đan tu luyện (tiểu cảnh)
        if not raw_key.startswith("dtl:"):
            return await inter.response.send_message(
                embed=e_warn("⚡ Đột Phá Đại Cảnh",
                    "Đột phá cảnh giới lớn chỉ thực hiện được qua nút **⚡ Đột Phá** "
                    "trong tab **Tu Luyện** của Hồ Sơ."),
                ephemeral=True)

        parts = raw_key[4:].split(":", 2)
        if len(parts) != 3:
            return await inter.response.send_message("❌ Đan không hợp lệ!", ephemeral=True)
        cg_id, cap_nho_sau, ten = int(parts[0]), int(parts[1]), parts[2]

        # Lấy thông tin đan
        dan_info = None
        if 0 <= cg_id < len(DAN_TU_LUYEN):
            for d in DAN_TU_LUYEN[cg_id]:
                if d["ten"] == ten and d["cap_nho_sau"] == cap_nho_sau:
                    dan_info = d; break
        if dan_info is None:
            return await inter.response.send_message("❌ Đan không hợp lệ!", ephemeral=True)

        # Kiểm tra cảnh giới
        if ts["canh_gioi"] != cg_id:
            cg_ten = CANH_GIOI[cg_id]["ten"] if 0 <= cg_id < len(CANH_GIOI) else "?"
            return await inter.response.send_message(
                embed=e_loi("❌ Sai Cảnh Giới!", f"Đan này dành cho tu sĩ **{cg_ten}**."), ephemeral=True)

        # Kiểm tra cap_nho: đan Trung Kì chỉ dùng khi đang Sơ Kì
        if ts["cap_nho"] != cap_nho_sau - 1:
            ki_names = {1: "Sơ Kì", 2: "Trung Kì", 3: "Hậu Kì"}
            ki_can   = ki_names.get(cap_nho_sau - 1, "?")
            ki_sau   = ki_names.get(cap_nho_sau, "?")
            cg_ten   = CANH_GIOI[cg_id]["ten"] if 0 <= cg_id < len(CANH_GIOI) else "?"
            return await inter.response.send_message(
                embed=e_loi("Không Thể Dùng!", (
                    f"Đan này chỉ dùng được khi đang ở **{ki_can} {cg_ten}**\n"
                    f"để thăng lên **{ki_sau} {cg_ten}**.")), ephemeral=True)

        # Kiểm tra đủ tu vi
        exp_yc = exp_can_thiet(cg_id, ts["cap_nho"])
        if ts["exp"] < exp_yc:
            return await inter.response.send_message(
                embed=e_loi("Tu Vi Chưa Đủ!", (
                    f"Cần **{fmt(exp_yc)}** tu vi để dùng đan này.\n"
                    f"Hiện có: **{fmt(ts['exp'])}** tu vi.")), ephemeral=True)

        # Kiểm tra số lượng
        have = ts["dan_duoc"].get(raw_key, 0)
        if have <= 0:
            return await inter.response.send_message("❌ Không còn đan trong túi!", ephemeral=True)

        # Dùng đan — thăng tiểu cảnh
        new_cap = cap_nho_sau
        new_hp  = hp_max_cong_thuc(cg_id, new_cap)
        new_at  = cong_cong_thuc(cg_id, new_cap)
        new_def = thu_cong_thuc(cg_id, new_cap)
        dd = ts["dan_duoc"].copy()
        dd[raw_key] = have - 1
        if dd[raw_key] <= 0: del dd[raw_key]

        ll_tl = int((200 + cg_id**2 * 2300 + new_cap * 230) * 0.8 * 0.7)
        await update_tu_si(self.actor_id,
            cap_nho=new_cap, exp=0,
            hp=new_hp, hp_max=new_hp,
            linh_luc=ll_tl,
            dan_duoc=dd, tong_tu_vi=ts.get("tong_tu_vi", 0) + ts["exp"])

        cg_obj   = get_cg(cg_id)
        ki_names = {1: "Sơ Kì", 2: "Trung Kì", 3: "Hậu Kì"}
        ki_sau   = ki_names.get(new_cap, "?")
        ts_new   = await get_tu_si(inter.user.id)
        dao_hieu = ts_new.get("dao_hieu", inter.user.display_name)
        linh_luc2 = int((200 + cg_id**2 * 2300 + new_cap * 230) * 0.8 * 0.7)
        embed = e_ok("✨ THĂNG TIẾN THÀNH CÔNG!",
            f"**{dao_hieu}** đã bước vào {cg_obj['emoji']} **{ki_sau} {cg_obj['ten']}**!")
        embed.add_field(name=f"{E_SINH_LUC} Sinh Lực", value=fmt(new_hp),     inline=True)
        embed.add_field(name=f"{E_LINH_LUC} Linh Lực",  value=fmt(linh_luc2), inline=True)
        embed.set_footer(text=f"Còn {have - 1} viên {ten}")
        await inter.response.send_message(embed=embed, ephemeral=True)
        # Chỉ refresh hồ sơ gốc nếu là chủ hồ sơ
        if self.actor_id == self.parent.owner_id:
            await self.parent._reload()
            self.parent._rebuild()


class TuLuyenView(discord.ui.View):
    def __init__(self, parent: HoSoView, user: discord.User, ts: dict[str, Any], actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.user     = user
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        now = int(time.time())
        # Apply THE_CHAT cd_tu_luyen_pct (âm = giảm CD)
        st_cd  = _calc_stats(self.ts)
        cd_pct = st_cd.get("cd_tl_pct", 0.0)
        cd_tl_base = max(1, int(CD_TU_LUYEN * (1 + cd_pct / 100)))
        cd_tl = self.ts["cd_tu_luyen"] + cd_tl_base - now
        cd_dp = self.ts["cd_dot_pha"]  + CD_DOT_PHA  - now

        btn_be_quan = discord.ui.Button(
            label="🌙 Bế Quan" if cd_tl <= 0 else f"🌙 Bế Quan ({fmt_cd(cd_tl)})",
            style=discord.ButtonStyle.primary, row=0,
            disabled=(cd_tl > 0))
        btn_dot_pha = discord.ui.Button(
            label="⚡ Đột Phá" if cd_dp <= 0 else f"⚡ Đột Phá ({fmt_cd(cd_dp)})",
            style=discord.ButtonStyle.success, row=0,
            disabled=(cd_dp > 0))
        btn_back = discord.ui.Button(label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=1)

        btn_be_quan.callback = self._on_be_quan
        btn_dot_pha.callback = self._on_dot_pha
        btn_back.callback    = self._on_back

        self.add_item(btn_be_quan)
        self.add_item(btn_dot_pha)
        self.add_item(btn_back)

    async def _reload_embed(self, inter: discord.Interaction):
        self.ts = await get_tu_si(self.actor_id)
        self._build_buttons()
        await inter.response.edit_message(
            embed=_embed_tu_luyen(self.ts, self.user), view=self)

    async def _on_be_quan(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        ts  = await get_tu_si(self.actor_id)
        if not ts:
            return await inter.response.send_message(
                embed=e_loi("❌ Lỗi", "Không tìm thấy dữ liệu tu sĩ. Hãy dùng /hoso để khởi tạo."),
                ephemeral=True)
        now    = int(time.time())
        st_bq  = _calc_stats(ts)
        cd_pct_bq = st_bq.get("cd_tl_pct", 0.0)
        cd_tl_eff = max(1, int(CD_TU_LUYEN * (1 + cd_pct_bq / 100)))
        cd  = ts["cd_tu_luyen"] + cd_tl_eff - now
        if cd > 0:
            return await inter.response.send_message(
                embed=e_warn("Chưa Đến Lúc", fmt_cd(cd)),
                ephemeral=True)

        st       = _calc_stats(ts)
        base_e   = int(200 * (ts["canh_gioi"] + 1) * st["exp_m"])
        exp_nhan = random.randint(int(base_e * 0.8), int(base_e * 1.2))
        lt_base  = random.randint(10 * (ts["canh_gioi"] + 1), 50 * (ts["canh_gioi"] + 1))
        lt_nhan  = int(lt_base * st["lt_m"])
        hp_hoi   = min(ts["hp"] + int(ts["hp_max"] * 0.1), ts["hp_max"])

        await update_tu_si(self.actor_id,
            exp=ts["exp"] + exp_nhan, hp=hp_hoi,
            linh_thach=ts["linh_thach"] + lt_nhan,
            cd_tu_luyen=now, tong_tu_luyen=ts["tong_tu_luyen"] + 1)

        self.ts = await get_tu_si(self.actor_id)
        self._build_buttons()

        cg_ten = get_cg(ts["canh_gioi"])["ten"]
        be_quan_embed = discord.Embed(title="🌙 BẾ QUAN THÀNH CÔNG", color=0x57F287)
        be_quan_embed.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        be_quan_embed.description = (
            f"Đạo hữu vừa kết thúc một vò bế quan, nhận được **{fmt(exp_nhan)}** Tu vi"
            f" và **{fmt(lt_nhan)}** {E_LINH_THACH}."
        )
        be_quan_embed.add_field(name="Tổng Tu Vi hiện có", value=fmt(self.ts["exp"]), inline=True)
        be_quan_embed.add_field(name="Cảnh Giới",          value=cg_ten,              inline=True)
        be_quan_embed.set_footer(text="Tu hành như lội nước ngược dòng, không tiến ắt lùi.")

        await inter.response.edit_message(embed=be_quan_embed, view=self)
        if self.actor_id == self.parent.owner_id:
            await self.parent._reload()

    async def _on_dot_pha(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        ts      = await get_tu_si(self.actor_id)
        max_cap = CANH_GIOI[ts["canh_gioi"]]["cap"]
        la_dai  = ts["cap_nho"] >= max_cap  # True = đại cảnh, False = tiểu cảnh

        if la_dai:
            # ── Đại cảnh: check đan yêu cầu trong túi, gọi thẳng _cb_dot_pha ──
            dan_yc = None
            for d in DAN_DUOC:
                if not d.get("dot_pha"): continue
                if d.get("cg_yeu_cau") != ts["canh_gioi"]: continue
                if d.get("cap_nho_yeu_cau") is not None: continue  # skip đan tiểu cảnh
                dan_yc = d; break

            if dan_yc:
                so_luong = ts["dan_duoc"].get(str(dan_yc["id"]), 0)
                if so_luong <= 0:
                    return await inter.response.send_message(
                        embed=e_loi("Thiếu Đan Dược", (
                                f"Cần **{dan_yc['emoji']} {dan_yc['ten']}** để đột phá đại cảnh.\n"
                                f"Hiện có: **0 viên** — kiếm qua Bí Cảnh hoặc trao đổi Phường Thị!"
                            )),
                        ephemeral=True)
            # Gọi _cb_dot_pha của HoSoView (xử lý tỉ lệ, GIF, etc.)
            await self.parent._cb_dot_pha(inter)

        else:
            # ── Tiểu cảnh: chọn đan tu luyện qua dropdown ──
            opts = []
            for k, v in ts["dan_duoc"].items():
                if not k.startswith("dtl:") or v <= 0:
                    continue
                parts = k[4:].split(":", 2)
                if len(parts) != 3:
                    continue
                cg_id, cap_nho_sau, ten = int(parts[0]), int(parts[1]), parts[2]
                emoji = ""
                if 0 <= cg_id < len(DAN_TU_LUYEN):
                    for d in DAN_TU_LUYEN[cg_id]:
                        if d["ten"] == ten and d["cap_nho_sau"] == cap_nho_sau:
                            emoji = d["emoji"]; break
                cg_ten = CANH_GIOI[cg_id]["ten"] if 0 <= cg_id < len(CANH_GIOI) else "?"
                ki_sau = "Trung Kì" if cap_nho_sau == 2 else "Hậu Kì"
                opts.append(discord.SelectOption(
                    label=f"{ten} ×{v}",
                    value=k,
                    emoji=_parse_emoji(emoji),
                    description=f"{cg_ten} → {ki_sau}"))

            if not opts:
                return await inter.response.send_message(
                    embed=e_loi("❌ Không Có Đan Tu Luyện", "Chinh phục bí cảnh để thu thập đan tu luyện!"),
                    ephemeral=True)

            embed = discord.Embed(title="💊 CHỌN ĐAN TU LUYỆN", color=0xFFD700,
                description="Chọn đan để thăng tiểu cảnh\n⚠️ Chỉ dùng được khi đang ở đúng cảnh giới yêu cầu!")
            await inter.response.send_message(embed=embed, view=DungDotPhaView(self.parent, ts, opts, actor_id=self.actor_id), ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        await _back_to_hoso(inter, self.parent)


# ══════════════════════════════════════════════════════════════
#  KHO ĐỒ VIEW — Phân trang
# ══════════════════════════════════════════════════════════════
