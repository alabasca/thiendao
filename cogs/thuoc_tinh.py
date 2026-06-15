"""
╔══════════════════════════════════════════════════════╗
║  QCBH TU TIÊN BOT  —  Thuộc Tính                   ║
║  Bảng thuộc tính đầy đủ — sync mọi loại buff        ║
╚══════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from typing import Any

import discord

from utils.config import (
    LINH_CAN_BY_ID, PHAP_BAO_BY_ID,
    BUFF_LABELS, get_cg, get_cg_ten, fmt, bar,
    exp_can_thiet,
    SUNG_THU_BY_ID, SUNG_THU_SKILL,
    SUNG_THU_LEVEL_MULT, SUNG_THU_TIER2_MULT,
    DIEM_DANH_HE_SO,
)
from utils.bot_emojis import (
    E_TU_VI, E_CONG_KICH, E_PHONG_NGU, E_SINH_LUC, E_LINH_LUC,
    E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO, E_LINH_THACH,
)
from cogs.hoso_utils import _calc_full_stats, _calc_linh_can_lop2


def _build_embed_thuoc_tinh(ts: dict[str, Any], user: discord.User) -> discord.Embed:
    cg  = get_cg(ts["canh_gioi"])
    st  = _calc_full_stats(ts)
    ec  = exp_can_thiet(ts["canh_gioi"], ts["cap_nho"])

    lc_p  = st.get("lc_p", {})
    cp_b  = st.get("cp_b", {})
    tc_d  = st.get("tc")
    tm    = st.get("tm")
    st_b  = st.get("st_b", {})
    lc2   = st.get("lc2", {}) or {}
    pb_at     = st.get("pb_at", 0)
    pb_df     = st.get("pb_df", 0)
    pb_at_pct = st.get("pb_at_pct", 0.0)
    pb_df_pct = st.get("pb_df_pct", 0.0)
    pb_hp_pct = st.get("pb_hp_pct", 0.0)
    tc_b  = tc_d.get("buff", {}) if tc_d else {}

    embed = discord.Embed(title="📊 THUỘC TÍNH CHI TIẾT", color=cg["mau"])
    embed.set_author(name=ts["dao_hieu"], icon_url=user.display_avatar.url)
    embed.set_thumbnail(url=user.display_avatar.url)

    # ── Cảnh giới & Tu vi ────────────────────────────────────────
    embed.add_field(
        name="🌟 Cảnh Giới",
        value=(
            f"{cg['emoji']} **{get_cg_ten(ts['canh_gioi'], ts['cap_nho'])}**\n"
            f"`{bar(ts['exp'], ec)}` {fmt(ts['exp'])}/{fmt(ec)}"
        ),
        inline=False,
    )
    embed.add_field(name="🔥 Chiến Lực", value=f"**{fmt(st['cl'])}**", inline=True)

    # ── HP ───────────────────────────────────────────────────────
    hp_parts = [f"Gốc **{ts['hp_max']}**"]
    if lc_p.get("hp_flat"):  hp_parts.append(f"LC **+{lc_p['hp_flat']}**")
    if cp_b.get("hp_flat"):  hp_parts.append(f"CP **+{cp_b['hp_flat']}**")
    if lc_p.get("hp_pct"):   hp_parts.append(f"LC **{lc_p['hp_pct']:+.1f}%**")
    if cp_b.get("hp_pct"):   hp_parts.append(f"CP **{cp_b['hp_pct']:+.1f}%**")
    if pb_hp_pct:             hp_parts.append(f"PB **{pb_hp_pct:+.1f}%**")
    if tc_b.get("hp_pct"):   hp_parts.append(f"TC **{tc_b['hp_pct']:+.0f}%**")
    if st_b.get("hp_pct"):   hp_parts.append(f"ST **{st_b['hp_pct']:+.1f}%**")
    if tm and tm["buff"] == "hp": hp_parts.append(f"TM **×{tm['buff_val']}**")
    hp_parts.append(f"= **{st['hp_eff']}**")
    embed.add_field(
        name=f"{E_SINH_LUC} HP Hiệu Dụng",
        value=(
            f"`{bar(ts['hp'], st['hp_eff'])}` **{ts['hp']}** / {st['hp_eff']}\n"
            + " → ".join(hp_parts)
        ),
        inline=False,
    )

    # ── Tấn Công ─────────────────────────────────────────────────
    at_parts = [f"Gốc **{ts['cong']}**"]
    if pb_at:                 at_parts.append(f"PB **+{pb_at}**")
    if lc_p.get("at_flat"):   at_parts.append(f"LC **+{lc_p['at_flat']}**")
    if cp_b.get("at_flat"):   at_parts.append(f"CP **+{cp_b['at_flat']}**")
    if pb_at_pct:             at_parts.append(f"PB **{pb_at_pct:+.1f}%**")
    if lc_p.get("at_pct"):    at_parts.append(f"LC **{lc_p['at_pct']:+.1f}%**")
    if cp_b.get("at_pct"):    at_parts.append(f"CP **{cp_b['at_pct']:+.1f}%**")
    if tc_b.get("at_pct"):    at_parts.append(f"TC **{tc_b['at_pct']:+.0f}%**")
    if st_b.get("at_pct"):    at_parts.append(f"ST **{st_b['at_pct']:+.1f}%**")
    if tm and tm["buff"] == "cong": at_parts.append(f"TM **×{tm['buff_val']}**")
    at_parts.append(f"= **{st['at']}**")
    embed.add_field(name=f"{E_CONG_KICH} Tấn Công", value=" → ".join(at_parts), inline=False)

    # ── Phòng Thủ ────────────────────────────────────────────────
    df_parts = [f"Gốc **{ts['thu']}**"]
    if pb_df:                 df_parts.append(f"PB **+{pb_df}**")
    if lc_p.get("df_flat"):   df_parts.append(f"LC **+{lc_p['df_flat']}**")
    if cp_b.get("df_flat"):   df_parts.append(f"CP **+{cp_b['df_flat']}**")
    if pb_df_pct:             df_parts.append(f"PB **{pb_df_pct:+.1f}%**")
    if lc_p.get("def_pct"):   df_parts.append(f"LC **{lc_p['def_pct']:+.1f}%**")
    if cp_b.get("def_pct"):   df_parts.append(f"CP **{cp_b['def_pct']:+.1f}%**")
    if tc_b.get("def_pct"):   df_parts.append(f"TC **{tc_b['def_pct']:+.0f}%**")
    if st_b.get("def_pct"):   df_parts.append(f"ST **{st_b['def_pct']:+.1f}%**")
    df_parts.append(f"= **{st['df']}**")
    embed.add_field(name=f"{E_PHONG_NGU} Phòng Thủ", value=" → ".join(df_parts), inline=False)

    # ── Chỉ Số Phụ (breakdown nguồn) ─────────────────────────────
    hoi_tam   = st.get("hoi_tam", 0)
    ho_tam    = st.get("ho_tam", 0)
    bao_kich  = st.get("bao_kich", 0)
    khang_bao = st.get("khang_bao", 0)
    linh_luc  = st.get("linh_luc", 0)
    lv = ts["canh_gioi"] * 9 + ts["cap_nho"]
    ht_base  = int(st["at"] * 0.08 + lv * 3)
    hot_base = int(st["df"] * 0.15 + lv * 2)
    bk_base  = min(5 + ts["canh_gioi"] * 3 + ts["cap_nho"], 75)
    kb_base  = min(3 + ts["canh_gioi"] * 2 + ts["cap_nho"] // 2, 50)

    def _src(base, cp_k, lc_k, tc_k, st_k, lc2_k, is_pct=False):
        u = "%" if is_pct else ""
        parts = [f"CG **{base}{u}**"]
        if cp_b.get(cp_k):   parts.append(f"CP **+{round(cp_b[cp_k],1)}{u}**")
        if lc_p.get(lc_k):   parts.append(f"LC **+{round(lc_p[lc_k],1)}{u}**")
        if tc_b.get(tc_k):   parts.append(f"TC **+{round(tc_b[tc_k],1)}{u}**")
        if st_b.get(st_k):   parts.append(f"ST **+{round(st_b[st_k],1)}{u}**")
        if lc2.get(lc2_k):   parts.append(f"LC2 **+{round(lc2[lc2_k],1)}{u}**")
        return "  ".join(parts)

    phu_val = (
        f"{E_HOI_TAM} **Hội Tâm** {hoi_tam}  ←  "
        + _src(ht_base, "hoi_tam", "hoi_tam", "hoi_tam", "hoi_tam", "hoi_tam") + "\n"
        + f"{E_HO_TAM} **Hộ Tâm** {ho_tam}  ←  "
        + _src(hot_base, "ho_tam", "ho_tam", "ho_tam", "ho_tam", "ho_tam") + "\n"
        + f"{E_BAO_KICH} **Bạo Kích** {bao_kich*100:.1f}%  ←  "
        + _src(bk_base, "bao_kich", "bao_kich", "bao_kich", "bao_kich", "bao_kich", True) + "\n"
        + f"{E_KHANG_BAO} **Kháng Bạo** {khang_bao*100:.1f}%  ←  "
        + _src(kb_base, "khang_bao", "khang_bao", "khang_bao", "khang_bao", "khang_bao", True) + "\n"
        + f"{E_LINH_LUC} **Linh Lực** {linh_luc}"
    )
    if cp_b.get("linh_luc"): phu_val += f"  ←  CG + CP **+{cp_b['linh_luc']}**"
    if st.get("cd_tl_pct"):  phu_val += f"\n⏱️ CD Tu luyện **{st['cd_tl_pct']:+.0f}%** (TC)"
    embed.add_field(name="⚔️ Chỉ Số Phụ", value=phu_val, inline=False)

    # ── Công Pháp tổng passive ───────────────────────────────────
    cp_owned = ts.get("cong_phap_hoc", [])
    if not isinstance(cp_owned, list): cp_owned = []
    if cp_owned:
        cp_lines = []
        if cp_b.get("at_pct"):    cp_lines.append(f"{E_CONG_KICH} ATK **{cp_b['at_pct']:+.1f}%**")
        if cp_b.get("at_flat"):   cp_lines.append(f"{E_CONG_KICH} ATK **+{cp_b['at_flat']}**")
        if cp_b.get("def_pct"):   cp_lines.append(f"{E_PHONG_NGU} DEF **{cp_b['def_pct']:+.1f}%**")
        if cp_b.get("df_flat"):   cp_lines.append(f"{E_PHONG_NGU} DEF **+{cp_b['df_flat']}**")
        if cp_b.get("hp_pct"):    cp_lines.append(f"{E_SINH_LUC} HP **{cp_b['hp_pct']:+.1f}%**")
        if cp_b.get("hp_flat"):   cp_lines.append(f"{E_SINH_LUC} HP **+{cp_b['hp_flat']}**")
        if cp_b.get("linh_luc"):  cp_lines.append(f"{E_LINH_LUC} LL **+{cp_b['linh_luc']}**")
        if cp_b.get("hoi_tam"):   cp_lines.append(f"{E_HOI_TAM} HT **+{round(cp_b['hoi_tam'],1)}**")
        if cp_b.get("ho_tam"):    cp_lines.append(f"{E_HO_TAM} HoT **+{round(cp_b['ho_tam'],1)}**")
        if cp_b.get("bao_kich"):  cp_lines.append(f"{E_BAO_KICH} BK **+{round(cp_b['bao_kich'],1)}%**")
        if cp_b.get("khang_bao"): cp_lines.append(f"{E_KHANG_BAO} KB **+{round(cp_b['khang_bao'],1)}%**")
        cp_val = (
            f"**{len(cp_owned)} công pháp** đang cộng dồn (có decay theo CG chênh lệch)\n"
            + ("  ".join(cp_lines) if cp_lines else "*(chưa có passive)*")
        )
        embed.add_field(name="📚 Công Pháp (Tổng Passive)", value=cp_val, inline=False)

    # ── Hệ số EXP / LT / Drop ────────────────────────────────────
    exp_m  = round(st.get("exp_m", 1.0), 3)
    lt_m   = round(st.get("lt_m",  1.0), 3)
    drop_m = round(st.get("drop_m", 1.0), 3)
    cg_he_so = DIEM_DANH_HE_SO[min(ts.get("canh_gioi", 0), len(DIEM_DANH_HE_SO) - 1)]

    def _he_so_src(base_key, tm_check, tc_key, lc_key, st_key, lc2_key):
        parts = [f"CG ×**{cg_he_so}**"]
        if tm and tm["buff"] == tm_check: parts.append(f"TM ×**{tm['buff_val']}**")
        if tc_b.get(tc_key) and tc_b[tc_key] != 1: parts.append(f"TC ×**{tc_b[tc_key]}**")
        if lc_p.get(lc_key):  parts.append(f"LC **+{lc_p[lc_key]:.0f}%**")
        if st_b.get(st_key):  parts.append(f"ST **+{st_b[st_key]:.1f}%**")
        if lc2.get(lc2_key):  parts.append(f"LC2 **+{lc2[lc2_key]:.1f}%**")
        return "  ·  ".join(parts)

    drop_parts = ["Base ×**1.0**"]
    if lc_p.get("drop_rate"):  drop_parts.append(f"LC **+{lc_p['drop_rate']:.0f}%**")
    if tc_b.get("drop_rate"):  drop_parts.append(f"TC **+{tc_b['drop_rate']:.0f}%**")
    if st_b.get("drop_rate"):  drop_parts.append(f"ST **+{st_b['drop_rate']:.1f}%**")
    if lc2.get("drop_rate"):   drop_parts.append(f"LC2 **+{lc2['drop_rate']:.1f}%**")

    he_so_val = (
        f"{E_TU_VI} **Tu vi** ×**{exp_m}**  ←  "
        + _he_so_src("exp", "exp", "exp_m", "exp_pct", "exp_pct", "exp_pct") + "\n"
        + f"{E_LINH_THACH} **Linh thạch** ×**{lt_m}**  ←  CG ×**{cg_he_so}**"
        + (f"  ·  TM ×**{tm['buff_val']}**" if tm and tm['buff'] == 'linh_thach' else "")
        + (f"  ·  TC ×**{tc_b['lt_m']}**" if tc_b.get('lt_m') and tc_b['lt_m'] != 1 else "")
        + "\n"
        + f"🍀 **Drop** ×**{drop_m}**  ←  " + "  ·  ".join(drop_parts)
    )
    if st_b.get("boss_dmg_pct"):
        he_so_val += f"\n💥 **Boss DMG** +**{st_b['boss_dmg_pct']:.0f}%** (ST)"
    embed.add_field(name=f"{E_TU_VI} Hệ Số Thưởng", value=he_so_val, inline=False)

    # ── Thể Chất + Linh Căn ──────────────────────────────────────
    tc_str = "*(chưa xác định)*"
    if tc_d:
        b = tc_b
        tc_parts = []
        if b.get("at_pct"):    tc_parts.append(f"ATK{b['at_pct']:+.0f}%")
        if b.get("def_pct"):   tc_parts.append(f"DEF{b['def_pct']:+.0f}%")
        if b.get("hp_pct"):    tc_parts.append(f"HP{b['hp_pct']:+.0f}%")
        if b.get("bao_kich"):  tc_parts.append(f"BK+{b['bao_kich']:.0f}%")
        if b.get("khang_bao"): tc_parts.append(f"KB+{b['khang_bao']:.0f}%")
        if b.get("hoi_tam"):   tc_parts.append(f"HT+{b['hoi_tam']}")
        if b.get("ho_tam"):    tc_parts.append(f"HoT+{b['ho_tam']}")
        if b.get("exp_m") and b["exp_m"] != 1: tc_parts.append(f"EXP×{b['exp_m']}")
        if b.get("lt_m") and b["lt_m"] != 1:   tc_parts.append(f"LT×{b['lt_m']}")
        if b.get("drop_rate"): tc_parts.append(f"Drop+{b['drop_rate']:.0f}%")
        if b.get("cd_tu_luyen_pct"): tc_parts.append(f"CD{b['cd_tu_luyen_pct']:+.0f}%")
        tc_str = f"{tc_d['emoji']} **{tc_d['ten']}**\n`{'  '.join(tc_parts) or '—'}`"

    lc_ids = ts.get("linh_can_so_huu", [])
    lc_lines = []
    for lc_id in lc_ids:
        lc = LINH_CAN_BY_ID.get(lc_id)
        if not lc: continue
        p = lc.get("passive", {})
        p_parts = []
        if p.get("at_flat"):   p_parts.append(f"AT+{p['at_flat']}")
        if p.get("at_pct"):    p_parts.append(f"AT+{p['at_pct']:.1f}%")
        if p.get("df_flat"):   p_parts.append(f"DEF+{p['df_flat']}")
        if p.get("def_pct"):   p_parts.append(f"DEF+{p['def_pct']:.1f}%")
        if p.get("hp_flat"):   p_parts.append(f"HP+{p['hp_flat']}")
        if p.get("hp_pct"):    p_parts.append(f"HP+{p['hp_pct']:.1f}%")
        if p.get("hoi_tam"):   p_parts.append(f"HT+{p['hoi_tam']}")
        if p.get("ho_tam"):    p_parts.append(f"HoT+{p['ho_tam']}")
        if p.get("bao_kich"):  p_parts.append(f"BK+{p['bao_kich']:.0f}%")
        if p.get("khang_bao"): p_parts.append(f"KB+{p['khang_bao']:.0f}%")
        if p.get("drop_rate"): p_parts.append(f"Drop+{p['drop_rate']:.0f}%")
        if p.get("exp_pct"):   p_parts.append(f"EXP+{p['exp_pct']:.0f}%")
        lc_lines.append(f"{lc['emoji']} **{lc['ten']}**  `{'  '.join(p_parts) or '—'}`")

    embed.add_field(name="🧬 Thể Chất", value=tc_str, inline=True)
    embed.add_field(name="🌿 Linh Căn Lớp 1", value="\n".join(lc_lines) or "*(chưa có)*", inline=True)

    # Linh Căn Lớp 2
    if lc2:
        _L2 = {"hoi_tam":f"{E_HOI_TAM}","ho_tam":f"{E_HO_TAM}",
               "bao_kich":f"{E_BAO_KICH}","khang_bao":f"{E_KHANG_BAO}",
               "drop_rate":"🍀","exp_pct":f"{E_TU_VI}"}
        lc2_parts = []
        for k, emoji in _L2.items():
            v = lc2.get(k, 0)
            if not v: continue
            lc2_parts.append(f"{emoji} +{round(v,2)}{'%' if k in ('bao_kich','khang_bao','drop_rate','exp_pct') else ''}")
        if lc2_parts:
            embed.add_field(name="✨ Linh Căn Lớp 2 (Tích Lũy)", value="  ".join(lc2_parts), inline=False)

    # Buff lớp 2 dạng base (đã cộng vào gốc)
    _B_LABEL = {"at_pct": "ATK", "def_pct": "DEF", "hp_pct": "HP"}
    _BASE_F  = {"at_pct", "def_pct", "hp_pct"}
    base_notes = []
    for _id in lc_ids:
        _lc = LINH_CAN_BY_ID.get(_id)
        if not _lc: continue
        _dpb = _lc.get("dot_pha_buff", {})
        _base = {k: v for k, v in _dpb.items() if k in _BASE_F}
        if _base:
            _pts = [f"{_B_LABEL[k]}+{v}%/lần" for k, v in _base.items()]
            base_notes.append(f"{_lc['emoji']} {_lc['ten']}: {', '.join(_pts)}")
    if base_notes:
        embed.add_field(
            name="📊 Buff Lớp 2 Đã Cộng Vào Chỉ Số Gốc",
            value="\n".join(base_notes) + "\n**(ATK/DEF/HP tăng mỗi lần đột phá — không hiện riêng)**",
            inline=False,
        )

    # ── Tông Môn ─────────────────────────────────────────────────
    if tm:
        embed.add_field(
            name=f"{tm['emoji']} Tông Môn",
            value=f"**{tm['ten']}**\n{BUFF_LABELS[tm['buff']]} ×{tm['buff_val']}",
            inline=True,
        )
    else:
        embed.add_field(name="🏛️ Tông Môn", value="*(Vô Phái)*", inline=True)

    # ── Pháp Bảo ─────────────────────────────────────────────────
    pb_active_id = ts.get("phap_bao_active", -1)
    pb_active    = PHAP_BAO_BY_ID.get(pb_active_id) if pb_active_id >= 0 else None
    if pb_active:
        pas = pb_active.get("passive", {})
        pb_pas_parts = []
        if pas.get("at_pct"):  pb_pas_parts.append(f"ATK+{pas['at_pct']}%")
        if pas.get("def_pct"): pb_pas_parts.append(f"DEF+{pas['def_pct']}%")
        if pas.get("hp_pct"):  pb_pas_parts.append(f"HP+{pas['hp_pct']}%")
        pb_val = (
            f"{pb_active['emoji']} **{pb_active['ten']}** *(active)*\n"
            f"{E_CONG_KICH} +{pb_at}  {E_PHONG_NGU} +{pb_df}"
        )
        if pb_pas_parts:
            pb_val += f"\nPassive: `{'  '.join(pb_pas_parts)}`"
        embed.add_field(name="⚗️ Pháp Bảo", value=pb_val, inline=True)

    # ── Sủng Thú ─────────────────────────────────────────────────
    from cogs.views.sung_thu import _parse_sung_thu, _calc_sung_thu_buff
    kho_st       = _parse_sung_thu(ts)
    st_active_id = ts.get("sung_thu_active", -1)
    if st_active_id >= 0 and str(st_active_id) in kho_st:
        st_cfg  = SUNG_THU_BY_ID.get(st_active_id)
        st_data = kho_st[str(st_active_id)]
        if st_cfg:
            level     = st_data.get("level", 1)
            tier_tag  = "💫 HT" if st_cfg["tier"] == 2 else "⭐"
            has_set   = st_cfg["he"] in set(ts.get("linh_can_so_huu", []))
            full_buff = _calc_sung_thu_buff(ts)
            _BL = {"at_pct":f"{E_CONG_KICH}","def_pct":f"{E_PHONG_NGU}","hp_pct":f"{E_SINH_LUC}",
                   "bao_kich":f"{E_BAO_KICH}","khang_bao":f"{E_KHANG_BAO}",
                   "hoi_tam":f"{E_HOI_TAM}","ho_tam":f"{E_HO_TAM}",
                   "drop_rate":"🍀","exp_pct":f"{E_TU_VI}","boss_dmg_pct":"💥"}
            st_buff_parts = []
            for k, emoji in _BL.items():
                v = full_buff.get(k, 0)
                if not v: continue
                is_pct = ("pct" in k or k in ("bao_kich","khang_bao","boss_dmg_pct"))
                st_buff_parts.append(f"{emoji} +{v:.1f}{'%' if is_pct else ''}")
            skill      = SUNG_THU_SKILL.get(st_cfg["he"], {})
            passive_sk = skill.get("passive")
            active_sk  = skill.get("active") if st_cfg["tier"] == 2 else None
            st_val = (
                f"{tier_tag} **{st_cfg['emoji']} {st_cfg['ten']}** Lv{level}"
                + ("  🔗 Set ✅" if has_set else "")
                + f"\n{'  '.join(st_buff_parts) or '—'}"
            )
            if passive_sk: st_val += f"\n🔵 {passive_sk['ten']}: {passive_sk['mo_ta']}"
            if active_sk:  st_val += f"\n🔴 {active_sk['ten']} (CD {active_sk.get('cd','?')}l)"
            if len(st_val) > 1020: st_val = st_val[:1017] + "..."
            embed.add_field(name="🐾 Sủng Thú", value=st_val, inline=False)

    # ── Điểm Linh Căn ────────────────────────────────────────────
    lc_diem = ts.get("linh_can_diem", {})
    diem_lines = [
        f"{LINH_CAN_BY_ID[lc_id]['emoji']} {LINH_CAN_BY_ID[lc_id]['ten']}: **{lc_diem.get(lc_id, 0):,}đ**"
        for lc_id in lc_ids if lc_id in LINH_CAN_BY_ID
    ]
    if diem_lines:
        embed.add_field(name="📊 Điểm Linh Căn", value="\n".join(diem_lines), inline=False)

    embed.set_footer(text="📊 Thuộc Tính — PB · LC lớp 1+2 · TC · TM · CP tổng · ST · CG")
    return embed


async def setup(bot):
    pass
