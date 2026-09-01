# erd_symbols.py
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath


def draw_erd_symbol(path: QPainterPath, anchor: QPointF, dir_v: QPointF, card_str: str, is_dependent: bool = False) -> float:
    """
    Hàm vẽ ký hiệu ERD.
    - Trả về: float (độ dài 'reach' mà ký hiệu chiếm dụng theo hướng dir_v)
    """
    ux, uy = dir_v.x(), dir_v.y()
    px, py = -uy, ux  # Vector vuông góc

    is_zero = "0," in card_str or "Optional" in card_str
    is_many = ",n" in card_str or "Many" in card_str

    # 1. TRƯỜNG HỢP DEPENDENT (Ký hiệu tam giác + vạch/vòng tròn)
    if is_dependent:
            # 3 vạch song song dính mép Entity
            for offset_p in [-5, 0, 5]:
                p_start = anchor + QPointF(px * offset_p, py * offset_p)
                p_end = p_start + QPointF(ux * 18, uy * 18) #tăng độ dài 3 vạch
                path.moveTo(p_start)
                path.lineTo(p_end)
    
            base_center = anchor + QPointF(ux * 19, uy * 19) #di chuyển tam giác về phía trước
            b1 = base_center + QPointF(px * 12, py * 12)
            b2 = base_center - QPointF(px * 12, py * 12)
            tip = anchor + QPointF(ux * 36, uy * 36)
    
            # Tam giác hướng ra dây (thon dài hơn, tỷ lệ sâu:rộng ~2:1 giống hình mẫu)
            tri_path = QPainterPath()
            tri_path.moveTo(b1)
            tri_path.lineTo(tip)
            tri_path.lineTo(b2)
            tri_path.closeSubpath()
            path.addPath(tri_path)
    
            # Ký hiệu Optional (0) hoặc Mandatory (1) sau tam giác
            if is_zero:
                # Vẽ đường nối từ đỉnh tam giác đến mép vòng tròn
                path.moveTo(tip)
                path.lineTo(tip + QPointF(ux * 1, uy * 1))
                
                c_center = tip + QPointF(ux * 6, uy * 6) #di vòng tròn về phía trước
                path.addEllipse(c_center, 5, 5)
                return 47.0  # 35 (tip) + 6 (center) + 5 (bán kính)
            else:
                # Vẽ đường nối từ đỉnh tam giác đến vạch thẳng
                path.moveTo(tip)
                path.lineTo(tip + QPointF(ux * 3, uy * 3))
                
                p_c = tip + QPointF(ux * 1, uy * 1)
                path.moveTo(p_c + QPointF(px * 10, py * 10)) #lên xuống
                path.lineTo(p_c - QPointF(px * 10, py * 10)) #dài ngắn
                return 38.0

    # 2. TRƯỜNG HỢP MANY (,n) - Ký hiệu chân chim
    if is_many:
        base_p = anchor + QPointF(ux * 20.5, uy * 20.5)
        s1 = anchor + QPointF(px * 8, py * 8)
        s2 = anchor - QPointF(px * 8, py * 8)

        path.moveTo(base_p); path.lineTo(anchor)
        path.moveTo(base_p); path.lineTo(s1)
        path.moveTo(base_p); path.lineTo(s2)
        
        if is_zero:
            # Vẽ đường nối từ gốc chân chim đến mép vòng tròn
            path.moveTo(base_p)
            path.lineTo(anchor + QPointF(ux * 20, uy * 20))
            
            c_center = anchor + QPointF(ux * 26, uy * 26)
            path.addEllipse(c_center, 5, 5)
            return 32.0  # 25 + 5
        else:
            # Vẽ đường nối từ gốc chân chim đến vạch thẳng
            path.moveTo(base_p)
            path.lineTo(anchor + QPointF(ux * 23, uy * 23))
            
            p_c = anchor + QPointF(ux * 21, uy * 21)
            path.moveTo(p_c + QPointF(px * 10, py * 10))
            path.lineTo(p_c - QPointF(px * 10, py * 10))
            return 24.0

    # 3. TRƯỜNG HỢP ONE (,1) - Ký hiệu vạch đơn
    else:
        if is_zero:
            # Nối từ anchor đến mép ngoài của vòng tròn (15 - 5 = 10px)
            path.moveTo(anchor)
            path.lineTo(anchor + QPointF(ux * 11, uy * 11))
            
            c_center = anchor + QPointF(ux * 16, uy * 16)
            path.addEllipse(c_center, 5, 5)
            return 21.0  # 15 + 5
        else:
            # Nối từ anchor đến điểm đặt vạch thẳng (13px)
            path.moveTo(anchor)
            path.lineTo(anchor + QPointF(ux * 18, uy * 18))
            
            p_c = anchor + QPointF(ux * 18, uy * 18)
            path.moveTo(p_c + QPointF(px * 10, py * 10))
            path.lineTo(p_c - QPointF(px * 10, py * 10))
            return 19.0