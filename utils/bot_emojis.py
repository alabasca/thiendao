"""
utils/bot_emojis.py
Tất cả emoji của bot — import từ đây thay vì hardcode rải rác.
"""

from __future__ import annotations

# ── Chỉ số chiến đấu ──────────────────────────────────────────
E_SINH_LUC  = "<:SinhLuc:1481643552545968331>"
E_LINH_LUC  = "<:LinhLuc:1481643549383590052>"
E_CONG_KICH = "<:CongKich:1481643551673811024>"
E_PHONG_NGU = "<:PhongNgu:1481643550168059984>"
E_LINH_THACH    = "<:LinhThach:1481645991181553796>"
E_TT_LINH_THACH = "<:tt_linh_thach:1481645991181553796>"  # alias dùng trong embed text

# ── Cảnh giới ─────────────────────────────────────────────────
E_LUYEN_KHI  = "<:luyen_khi:1481653213219389603>"
E_TRUC_CO    = "<:truc_co:1481653214339268649>"
E_KET_TINH   = "<:ket_tinh:1481653215245107420>"
E_KIM_DAN    = "<:kim_dan:1481653216197476495>"
E_TU_LINH    = "<:tu_linh:1481653216960712724>"
E_NGUYEN_ANH = "<:nguyen_anh:1481653217984118897>"
E_HOA_THAN   = "<:hoa_than:1481653218978041856>"
E_NGO_DAO    = "<:ngo_dao:1481653220555100332>"
E_VU_HOA     = "<:vu_hoa:1481653221716922481>"
E_DANG_TIEN  = "<:dang_tien:1481653222807568507>"

# ── Đan đột phá ───────────────────────────────────────────────
E_DAN_TRUC_CO    = "<:TrucCoDan:1481663527792935083>"
E_DAN_KIM_DAN    = "<:KimDanDan:1481663525880594565>"
E_DAN_CU_LINH    = "<:CuLinhDan:1481663524911452191>"
E_DAN_NGUYEN_ANH = "<:NguyenAnhDan:1481663523460485311>"
E_DAN_HOA_THAN   = "<:HoaThanDan:1481663515315015853>"
E_DAN_VU_HOA     = "<:VuHoaDan:1481663514258178254>"
E_DAN_NGO_DAO    = "<:NgoDaoDan:1481663512559485040>"
E_DAN_DANG_TIEN  = "<:DangTienDan:1481663513486164039>"

# ── Linh căn (thiên phú) ─────────────────────────────────────
E_THIEN_LINH_CAN   = "<:thien_linh_can:1482210576120942714>"
E_DIA_LINH_CAN     = "<:dia_linh_can:1482210577165324379>"
E_BIEN_DI_LINH_CAN = "<:bien_di_linh_can:1482210578192928838>"
E_TAP_LINH_CAN     = "<:tap_linh_can:1482210579392499722>"
E_PHAM_LINH_CAN    = "<:pham_linh_can:1482210580650524742>"

# ── Linh căn nguyên tố ───────────────────────────────────────
E_HOA_LINH_CAN   = "<:hoalinhcan:1482350037924315186>"
E_THUY_LINH_CAN  = "<:thuylinhcan:1482350037206962287>"
E_MOC_LINH_CAN   = "<:moclinhcan:1482350033616638102>"
E_THO_LINH_CAN   = "<:tholinhcan:1482350034727993405>"
E_PHONG_LINH_CAN = "<:phonglinhcan:1482350036292472852>"
E_LOI_LINH_CAN   = "<:loilinhcan:1482350032643686440>"

# ── Thanh HP ─────────────────────────────────────────────────
E_HP_START   = "<:hp_start:1481859799833509950>"
E_HP_MID     = "<:hp_mid:1481859798382415882>"
E_HP_END     = "<:hp_end:1481859789175652402>"
E_HP_START_E = "<:hp_start_e:1481859800479563857>"
E_HP_MID_E   = "<:hp_mid_e:1481859798835134627>"
E_HP_END_E   = "<:hp_end_e:1481859790148730991>"

# ── Thanh Linh Lực ────────────────────────────────────────────
E_LL_START   = "<:ll_start:1481859786739028142>"
E_LL_MID     = "<:ll_mid:1481859784683552839>"
E_LL_END     = "<:ll_end:1481859801389600779>"
E_LL_START_E = "<:ll_start_e:1481859787774758962>"
E_LL_MID_E   = "<:ll_mid_e:1481859785425944719>"
E_LL_END_E   = "<:ll_end_e:1481859783454752768>"

# ── Chỉ số chiến đấu mở rộng ─────────────────────────────────
E_HOI_TAM   = "<:HoiTam:1481643540374225099>"
E_HO_TAM    = "<:HoTam:1481643546527273000>"
E_KHANG_BAO = "<:KhangBao:1481643547370455273>"
E_BAO_KICH  = "<:BaoKich:1481643548280357007>"

# ── Đan dược ─────────────────────────────────────────────────
E_DAN_DUOC = "<:danduoc:1482432457457537166>"

# ── Tim quan hệ ───────────────────────────────────────────────
E_TIM_DO  = "<:tim_do:1482444880817946786>"
E_TIM_NUA = "<:tim_nua:1482444880117502092>"
E_TIM_DEN = "<:tim_den:1482444879203401799>"

# ── Tu Vi ─────────────────────────────────────────────────────
E_TU_VI = "<:tuvi:1482517005331468380>"

# ── Loại Công Pháp ────────────────────────────────────────

# ── Công pháp / Kỹ năng ──────────────────────────────────────
E_HOANNGUYEN          = "<:hoannguyen:1482180577707688046>"
E_HONDONCHITUC        = "<:hondonchituc:1482180578039173233>"
E_HONDONCHITUC_HIEM   = "<:hondonchituc_hiem:1482180579243069530>"
E_HONDONLINHTUC       = "<:hondonlinhtuc:1482180580522070137>"
E_HOPLINH             = "<:hoplinh:1482180598175895552>"
E_KETTHAN             = "<:ketthan:1482180581398806710>"
E_LUYENTHEDAN_HIEM    = "<:luyenthedan_hiem:1482180582132809810>"
E_LUYENTHEDAN_THUONG  = "<:luyenthedan_thuong:1482180582971674665>"
E_NGUNGTHAN           = "<:ngungthan:1482180583802015765>"
E_TAPKHI              = "<:tapkhi:1482180585349971999>"
E_TAYTUY_HIEM         = "<:taytuy_hiem:1482180586905800915>"
E_TAYTUY_THUONG       = "<:taytuy_thuong:1482180588143378555>"
E_THANGNGUYEN         = "<:thangnguyen:1482180589271384155>"
E_THANHTINHLINHTUC    = "<:thanhtinhlinhtuc:1482346534795477154>"
E_THONGMACH           = "<:thongmach:1482180591100100638>"
E_THUANMACH           = "<:thuanmach:1482180592018915444>"
E_TIENTHIENNHATKHI_HIEM    = "<:tienthiennhatkhi_hiem:1482180592736014336>"
E_TIENTHIENNHATKHI_THUONG  = "<:tienthiennhatkhi_thuong:1482180593562292325>"
E_TRUHUYET            = "<:truhuyet:1482180594723979448>"
E_TUKHI               = "<:tukhi:1482180595831406732>"
E_UANHUYET            = "<:uanhuyet:1482180596439580822>"
E_DUNGLINH            = "<:dunglinh:1482180597219590165>"

# ── Hệ công pháp ─────────────────────────────────────────────
E_CAP_THIEN  = "<:thien:1482343941792595988>"
E_CAP_DIA    = "<:dia:1482343940999876791>"
E_CAP_HUYEN  = "<:huyen:1482343942434590751>"
E_CAP_HOANG  = "<:hoang:1482343940299423744>"

# Emoji loại kỹ năng → alias sang emoji hệ công pháp (V3)
E_LOAI_VO_KY      = E_CAP_DIA    # Địa
E_LOAI_TUYET_KY   = E_CAP_THIEN  # Thiên
E_LOAI_THAN_PHAP  = E_CAP_HUYEN  # Huyền
E_LOAI_THAN_THONG = E_CAP_HOANG  # Hoàng

# Thiên (Tuyệt Kỹ)
E_THIEN_HA      = "<:hatuyeky:1482578655044698245>"
E_THIEN_TRUNG   = "<:trungtuyetky:1482579332215083108>"
E_THIEN_THUONG  = "<:thuongtuyetky:1482579720481673429>"
E_THIEN_CUC     = "<:cuctuyetky:1482580368749105233>"

# Địa (Võ Kỹ)
E_DIA_HA      = "<:havoky:1482578656328155252>"
E_DIA_TRUNG   = "<:trungvoky:1482579333938675894>"
E_DIA_THUONG  = "<:thuongvoky:1482579722650124308>"
E_DIA_CUC     = "<:cucvoky:1482580374508015626>"

# Huyền (Thần Pháp)
E_HUYEN_HA      = "<:hathanphap:1482578653903720540>"
E_HUYEN_TRUNG   = "<:trungthanphap:1482579332974252203>"
E_HUYEN_THUONG  = "<:thuongthanphap:1482579721714929806>"
E_HUYEN_CUC     = "<:cucthanphap:1482580369596223652>"

# Hoàng (Thần Thông)
E_HOANG_HA      = "<:hathanthong:1482578653278634087>"
E_HOANG_TRUNG   = "<:trungthanthong:1482579331346731038>"
E_HOANG_THUONG  = "<:thuongthanthong:1482579719403864105>"
E_HOANG_CUC     = "<:cucthanthong:1482580367767634029>"

# Lookup helpers
CP_CAP_EMOJI = {
    "Thiên": E_CAP_THIEN,
    "Địa":   E_CAP_DIA,
    "Huyền": E_CAP_HUYEN,
    "Hoàng": E_CAP_HOANG,
}
CP_PHAM_EMOJI = {
    ("Thiên","Hạ"):      E_THIEN_HA,
    ("Thiên","Trung"):   E_THIEN_TRUNG,
    ("Thiên","Thượng"):  E_THIEN_THUONG,
    ("Thiên","Cực"):     E_THIEN_CUC,
    ("Địa","Hạ"):        E_DIA_HA,
    ("Địa","Trung"):     E_DIA_TRUNG,
    ("Địa","Thượng"):    E_DIA_THUONG,
    ("Địa","Cực"):       E_DIA_CUC,
    ("Huyền","Hạ"):      E_HUYEN_HA,
    ("Huyền","Trung"):   E_HUYEN_TRUNG,
    ("Huyền","Thượng"):  E_HUYEN_THUONG,
    ("Huyền","Cực"):     E_HUYEN_CUC,
    ("Hoàng","Hạ"):      E_HOANG_HA,
    ("Hoàng","Trung"):   E_HOANG_TRUNG,
    ("Hoàng","Thượng"):  E_HOANG_THUONG,
    ("Hoàng","Cực"):     E_HOANG_CUC,
}

# ── Mảnh linh căn ─────────────────────────────────────────────
E_MANH_HOA   = "<:manhhoa:1482822971507740753>"
E_MANH_THUY  = "<:manhthuy:1482822972602585129>"
E_MANH_THO   = "<:manhtho:1482822975349723217>"
E_MANH_MOC   = "<:manhmoc:1482822973474869452>"
E_MANH_KIM   = "<:manhkim:1482822957284855808>"
E_MANH_LOI   = "<:manhloi:1482822974552805426>"
E_MANH_PHONG = "<:manhphong:1482822970488651928>"
E_MANH_AM    = "<:manham:1482822958132236489>"
E_MANH_QUANG = "<:manhquang:1482822959008846005>"

# ── Linh quả ──────────────────────────────────────────────────
E_QUA_HOA   = "<:hoaqua:1482822969385423083>"
E_QUA_THUY  = "<:thuyqua:1482822967632203887>"
E_QUA_THO   = "<:thoqua:1482822964872482928>"
E_QUA_MOC   = "<:mocqua:1482822964503253164>"
E_QUA_KIM   = "<:kimqua:1482822960254287932>"
E_QUA_LOI   = "<:loiqua:1482822963681300590>"
E_QUA_PHONG = "<:phongqua:1482822966222917822>"
E_QUA_AM    = "<:amqua:1482822955984621788>"
E_QUA_QUANG = "<:quangqua:1482822961177034772>"

# ── Linh căn bổ sung ──────────────────────────────────────────
E_KIM_LINH_CAN   = "<:kimlinhcan:1482822961873289307>"
E_AM_LINH_CAN    = "<:amlinhcan:1482822962724995113>"
E_QUANG_LINH_CAN = "<:quanglinhcan:1482822954902487040>"

# ── Pháp bảo ──────────────────────────────────────────────────
E_PB_HIEU_GIAC   = "<:hieugiac:1482901981314945067>"
E_PB_HOANG_CUC   = "<:hoangcuc:1482901980358639699>"
E_PB_TINH_CHUY   = "<:tinhchuy:1482901979087769804>"
E_PB_HUYEN_CHUNG = "<:huyenchung:1482901978232127499>"
E_PB_HUYET_DIEN  = "<:huyetdien:1482901977586208920>"
E_PB_CHI_KY      = "<:chiky:1482901976457937117>"
E_PB_NGUNG_CHAU  = "<:ngungchau:1482901974998450247>"
E_PB_BACH_BAO    = "<:bachbao:1482901973366865920>"
E_PB_THIET_BICH  = "<:thietbich:1482901970003169360>"
E_PB_CO_CAM      = "<:cocam:1482901971609325568>"

# Lookup theo id_base → emoji
PB_BASE_EMOJI = {
    0: E_PB_HIEU_GIAC,
    1: E_PB_HOANG_CUC,
    2: E_PB_TINH_CHUY,
    3: E_PB_HUYEN_CHUNG,
    4: E_PB_HUYET_DIEN,
    5: E_PB_CHI_KY,
    6: E_PB_NGUNG_CHAU,
    7: E_PB_BACH_BAO,
    8: E_PB_THIET_BICH,
    9: E_PB_CO_CAM,
}

# ── Tài nguyên đột phá thể chất ──────────────────────────────
E_TULOICAMQUY     = "<:tuloicamquy:1483262173047427083>"
E_HUYETHONXAHUONG = "<:huyethonxahuong:1483262171982069820>"
E_COCTRUCTANG     = "<:coctructang:1483262170849607802>"
E_NGUNGCANNHU     = "<:ngungcannhu:1483262169272291420>"
E_HUYETCHIHOALINH = "<:huyetchihoalinh:1483262168274305176>"
