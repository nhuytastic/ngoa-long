# ... (phần trên giữ nguyên) ...
    def get_luc_than(khach_idx, ta_idx):
        e_khach, e_ta = elements[khach_idx], elements[ta_idx]
        if e_khach == e_ta: return '兄弟'
        sinh = {'木':'火', '火':'土', '土':'金', '金':'水', '水':'木'}
        khac = {'木':'土', '土':'水', '水':'火', '火':'金', '金':'木'}
        if sinh[e_khach] == e_ta: return '父母'
        if sinh[e_ta] == e_khach: return '子孙'
        if khac[e_khach] == e_ta: return '官鬼'
        if khac[e_ta] == e_khach: return '妻财'

    # ĐỔI ĐỊNH DẠNG: Tên Lục Diệu (Lục Thân)
    str_thang_html = f"{names[idx_month]} ({get_luc_than(idx_month, idx_hour)})"
    str_ngay_html  = f"{names[idx_day]} ({get_luc_than(idx_day, idx_hour)})"
    str_gio_html   = f"{names[idx_hour]}"
    
    # 1. Hiển thị viết dọc ở Trung Cung (Ngăn cách bằng thẻ <br>)
    final_liu_yao_html = f"{str_thang_html}<br>{str_ngay_html}<br>{str_gio_html}"
    
    # 2. Hiển thị viết ngang ở dòng Kết quả Module 7 (Ngăn cách bằng dấu phẩy)
    final_liu_yao_text = f"[{str_thang_html}, {str_ngay_html}, {str_gio_html}]"
        
    return final_ss, final_liu_yao_html, str_gio_html, final_liu_yao_text
