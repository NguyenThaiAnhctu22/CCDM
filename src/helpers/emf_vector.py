import sys
if not sys.platform.startswith("win"):
    raise ImportError("emf_vector chỉ chạy được trên Windows (cần GDI của gdi32.dll)")

import ctypes
from ctypes import wintypes

gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    msimg32 = ctypes.WinDLL("msimg32", use_last_error=True)
except OSError:
    msimg32 = None

TRANSPARENT = 1
MM_TEXT = 1
PS_SOLID = 0
NULL_BRUSH = 5
NULL_PEN = 8
PT_MOVETO = 0x06
PT_LINETO = 0x02
PT_BEZIERTO = 0x04
GRADIENT_FILL_RECT_V = 0x01
FW_NORMAL = 400
FW_BOLD = 700
DEFAULT_CHARSET = 1
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
DEFAULT_QUALITY = 0
DEFAULT_PITCH = 0
FF_DONTCARE = 0

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

class LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight", wintypes.LONG), ("lfWidth", wintypes.LONG),
        ("lfEscapement", wintypes.LONG), ("lfOrientation", wintypes.LONG),
        ("lfWeight", wintypes.LONG), ("lfItalic", wintypes.BYTE),
        ("lfUnderline", wintypes.BYTE), ("lfStrikeOut", wintypes.BYTE),
        ("lfCharSet", wintypes.BYTE), ("lfOutPrecision", wintypes.BYTE),
        ("lfClipPrecision", wintypes.BYTE), ("lfQuality", wintypes.BYTE),
        ("lfPitchAndFamily", wintypes.BYTE), ("lfFaceName", wintypes.WCHAR * 32),
    ]

class TRIVERTEX(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG),
                ("Red", wintypes.USHORT), ("Green", wintypes.USHORT),
                ("Blue", wintypes.USHORT), ("Alpha", wintypes.USHORT)]

class GRADIENT_RECT(ctypes.Structure):
    _fields_ = [("UpperLeft", wintypes.ULONG), ("LowerRight", wintypes.ULONG)]

HDC = wintypes.HDC
HANDLE = wintypes.HANDLE
HGDIOBJ = wintypes.HANDLE

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, HDC]
user32.ReleaseDC.restype = wintypes.INT

gdi32.CreateEnhMetaFileW.argtypes = [HDC, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.LPCWSTR]
gdi32.CreateEnhMetaFileW.restype = HDC
gdi32.CloseEnhMetaFile.argtypes = [HDC]
gdi32.CloseEnhMetaFile.restype = HANDLE
gdi32.DeleteEnhMetaFile.argtypes = [HANDLE]
gdi32.DeleteEnhMetaFile.restype = wintypes.BOOL

gdi32.SetMapMode.argtypes = [HDC, wintypes.INT]
gdi32.SetMapMode.restype = wintypes.INT
gdi32.SetBkMode.argtypes = [HDC, wintypes.INT]
gdi32.SetBkMode.restype = wintypes.INT

gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = HGDIOBJ
gdi32.CreatePen.argtypes = [wintypes.INT, wintypes.INT, wintypes.COLORREF]
gdi32.CreatePen.restype = HGDIOBJ
gdi32.CreateFontIndirectW.argtypes = [ctypes.POINTER(LOGFONTW)]
gdi32.CreateFontIndirectW.restype = HGDIOBJ
gdi32.GetStockObject.argtypes = [wintypes.INT]
gdi32.GetStockObject.restype = HGDIOBJ
gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
gdi32.SelectObject.restype = HGDIOBJ
gdi32.DeleteObject.argtypes = [HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.Rectangle.argtypes = [HDC, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT]
gdi32.Rectangle.restype = wintypes.BOOL
gdi32.MoveToEx.argtypes = [HDC, wintypes.INT, wintypes.INT, ctypes.c_void_p]
gdi32.MoveToEx.restype = wintypes.BOOL
gdi32.LineTo.argtypes = [HDC, wintypes.INT, wintypes.INT]
gdi32.LineTo.restype = wintypes.BOOL
gdi32.PolyDraw.argtypes = [HDC, ctypes.c_void_p, ctypes.c_void_p, wintypes.INT]
gdi32.PolyDraw.restype = wintypes.BOOL

gdi32.SetTextColor.argtypes = [HDC, wintypes.COLORREF]
gdi32.SetTextColor.restype = wintypes.COLORREF
gdi32.TextOutW.argtypes = [HDC, wintypes.INT, wintypes.INT, wintypes.LPCWSTR, wintypes.INT]
gdi32.TextOutW.restype = wintypes.BOOL

if msimg32 is not None:
    msimg32.GradientFill.argtypes = [HDC, ctypes.c_void_p, wintypes.ULONG,
                                      ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG]
    msimg32.GradientFill.restype = wintypes.BOOL


def RGB(r, g, b):
    return r | (g << 8) | (b << 16)

def _c16(v8):
    return (v8 & 0xFF) << 8


class EmfCanvas:
    def __init__(self, file_path: str, scene_rect, scale: float = 3.0):
        self.rect = scene_rect
        self.scale = scale
        self.w = max(1, round(scene_rect.width() * scale))
        self.h = max(1, round(scene_rect.height() * scale))

        ref_dc = user32.GetDC(None)
        
        try:
            dpi_x = gdi32.GetDeviceCaps(ref_dc, 88) or 96
            dpi_y = gdi32.GetDeviceCaps(ref_dc, 90) or 96

            width_mm = int((self.w / dpi_x) * 2540)
            height_mm = int((self.h / dpi_y) * 2540)
            frame = RECT(0, 0, width_mm, height_mm)

            desc_str = "CCDM\0ERD Diagram\0\0"
            desc_buf = (ctypes.c_wchar * len(desc_str))(*desc_str)
            
            self.hdc = gdi32.CreateEnhMetaFileW(
                ref_dc, 
                file_path, 
                ctypes.byref(frame), 
                ctypes.cast(desc_buf, wintypes.LPCWSTR)
            )
        finally:
            user32.ReleaseDC(None, ref_dc)

        if not self.hdc:
            raise RuntimeError(f"CreateEnhMetaFileW thất bại: {ctypes.get_last_error()}")

        gdi32.SetMapMode(self.hdc, MM_TEXT)
        gdi32.SetBkMode(self.hdc, TRANSPARENT)

    def dev_pt(self, x, y):
        px = round((x - self.rect.x()) * self.scale)
        py = round((y - self.rect.y()) * self.scale)
        return POINT(px, py)

    def dev_len(self, length_scene):
        return max(1, round(length_scene * self.scale))

    def fill_white_background(self):
        brush = gdi32.CreateSolidBrush(RGB(255, 255, 255))
        old_brush = gdi32.SelectObject(self.hdc, brush)
        old_pen = gdi32.SelectObject(self.hdc, gdi32.GetStockObject(NULL_PEN))
        gdi32.Rectangle(self.hdc, 0, 0, self.w, self.h)
        gdi32.SelectObject(self.hdc, old_brush)
        gdi32.SelectObject(self.hdc, old_pen)
        gdi32.DeleteObject(brush)

    def draw_vertical_gradient_rect(self, x0, y0, x1, y1, top_rgb, bottom_rgb):
        p0 = self.dev_pt(x0, y0)
        p1 = self.dev_pt(x1, y1)

        if msimg32 is None:
            r = tuple((a + b) // 2 for a, b in zip(top_rgb, bottom_rgb))
            brush = gdi32.CreateSolidBrush(RGB(*r))
            old_brush = gdi32.SelectObject(self.hdc, brush)
            old_pen = gdi32.SelectObject(self.hdc, gdi32.GetStockObject(NULL_PEN))
            gdi32.Rectangle(self.hdc, p0.x, p0.y, p1.x, p1.y)
            gdi32.SelectObject(self.hdc, old_brush)
            gdi32.SelectObject(self.hdc, old_pen)
            gdi32.DeleteObject(brush)
            return

        verts = (TRIVERTEX * 2)(
            TRIVERTEX(p0.x, p0.y, _c16(top_rgb[0]), _c16(top_rgb[1]), _c16(top_rgb[2]), 0xFF00),
            TRIVERTEX(p1.x, p1.y, _c16(bottom_rgb[0]), _c16(bottom_rgb[1]), _c16(bottom_rgb[2]), 0xFF00),
        )
        grect = GRADIENT_RECT(0, 1)
        msimg32.GradientFill(self.hdc, verts, 2, ctypes.byref(grect), 1, GRADIENT_FILL_RECT_V)

    def draw_rect_outline(self, x0, y0, x1, y1, rgb, width_scene):
        p0 = self.dev_pt(x0, y0)
        p1 = self.dev_pt(x1, y1)
        pen = gdi32.CreatePen(PS_SOLID, self.dev_len(width_scene), RGB(*rgb))
        old_pen = gdi32.SelectObject(self.hdc, pen)
        old_brush = gdi32.SelectObject(self.hdc, gdi32.GetStockObject(NULL_BRUSH))
        gdi32.Rectangle(self.hdc, p0.x, p0.y, p1.x, p1.y)
        gdi32.SelectObject(self.hdc, old_pen)
        gdi32.SelectObject(self.hdc, old_brush)
        gdi32.DeleteObject(pen)

    def draw_line(self, x0, y0, x1, y1, rgb, width_scene):
        p0 = self.dev_pt(x0, y0)
        p1 = self.dev_pt(x1, y1)
        pen = gdi32.CreatePen(PS_SOLID, self.dev_len(width_scene), RGB(*rgb))
        old_pen = gdi32.SelectObject(self.hdc, pen)
        
        gdi32.MoveToEx(self.hdc, p0.x, p0.y, None)
        gdi32.LineTo(self.hdc, p1.x, p1.y)
        
        gdi32.SelectObject(self.hdc, old_pen)
        gdi32.DeleteObject(pen)

    def draw_qpainterpath(self, path, offset_x, offset_y, rgb, width_scene):
        n = path.elementCount()
        if n == 0:
            return

        pts, type_list = [], []
        i = 0
        while i < n:
            el = path.elementAt(i)
            sx, sy = el.x + offset_x, el.y + offset_y
            if el.isMoveTo():
                pts.append(self.dev_pt(sx, sy))
                type_list.append(PT_MOVETO)
                i += 1
            elif el.isLineTo():
                pts.append(self.dev_pt(sx, sy))
                type_list.append(PT_LINETO)
                i += 1
            elif el.isCurveTo():
                if i + 2 < n:
                    el2 = path.elementAt(i + 1)
                    el3 = path.elementAt(i + 2)
                    pts.append(self.dev_pt(sx, sy))
                    pts.append(self.dev_pt(el2.x + offset_x, el2.y + offset_y))
                    pts.append(self.dev_pt(el3.x + offset_x, el3.y + offset_y))
                    type_list.extend([PT_BEZIERTO, PT_BEZIERTO, PT_BEZIERTO])
                    i += 3
                else:
                    i += 1
            else:
                i += 1

        if not pts:
            return

        pen = gdi32.CreatePen(PS_SOLID, self.dev_len(width_scene), RGB(*rgb))
        old_pen = gdi32.SelectObject(self.hdc, pen)
        old_brush = gdi32.SelectObject(self.hdc, gdi32.GetStockObject(NULL_BRUSH))

        arr_pts = (POINT * len(pts))(*pts)
        arr_types = (ctypes.c_ubyte * len(type_list))(*type_list)
        gdi32.PolyDraw(self.hdc, arr_pts, arr_types, len(pts))

        gdi32.SelectObject(self.hdc, old_pen)
        gdi32.SelectObject(self.hdc, old_brush)
        gdi32.DeleteObject(pen)

    def _make_font(self, family, point_size, bold, italic=False, underline=False):
        lf = LOGFONTW()
        lf.lfHeight = -round(point_size * self.scale * 1.333)
        lf.lfWeight = FW_BOLD if bold else FW_NORMAL
        lf.lfItalic = 1 if italic else 0
        lf.lfUnderline = 1 if underline else 0
        lf.lfCharSet = DEFAULT_CHARSET
        lf.lfOutPrecision = OUT_DEFAULT_PRECIS
        lf.lfClipPrecision = CLIP_DEFAULT_PRECIS
        lf.lfQuality = DEFAULT_QUALITY
        lf.lfPitchAndFamily = DEFAULT_PITCH | FF_DONTCARE
        lf.lfFaceName = family[:31]
        return gdi32.CreateFontIndirectW(ctypes.byref(lf))

    def draw_text(self, text, x, y, family, point_size, bold, rgb, italic=False, underline=False):
        if not text:
            return
        font = self._make_font(family, point_size, bold, italic, underline)
        old_font = gdi32.SelectObject(self.hdc, font)
        gdi32.SetTextColor(self.hdc, RGB(*rgb))
        p = self.dev_pt(x, y)
        gdi32.TextOutW(self.hdc, p.x, p.y, text, len(text))
        gdi32.SelectObject(self.hdc, old_font)
        gdi32.DeleteObject(font)

    def close(self) -> bool:
        hemf = gdi32.CloseEnhMetaFile(self.hdc)
        if not hemf:
            return False
        gdi32.DeleteEnhMetaFile(hemf)
        return True


def _draw_entity(canvas: EmfCanvas, item, pk_text_cls):
    scene_pos = item.scenePos()
    rect = item.rect()
    x0, y0 = scene_pos.x() + rect.left(), scene_pos.y() + rect.top()
    x1, y1 = scene_pos.x() + rect.right(), scene_pos.y() + rect.bottom()

    # 1. Nền gradient
    canvas.draw_vertical_gradient_rect(x0, y0, x1, y1, (0xE0, 0xFF, 0xFF), (0xB2, 0xEB, 0xF2))

    # 2. Viền khung
    canvas.draw_rect_outline(x0, y0, x1, y1, (0x00, 0x80, 0x80), 1.5)

    # 3. Kẻ ngang header
    line_y = y0 + item.header_height
    canvas.draw_line(x0, line_y, x1, line_y, (0x00, 0x80, 0x80), 1.2)

    # 4. Tiêu đề Entity
    if hasattr(item, 'title_item') and item.title_item:
        tpos = item.title_item.scenePos()
        canvas.draw_text(
            item.entity.name, tpos.x(), tpos.y() + 2,
            item.entity_font.family(), item.entity_font.pointSize(),
            item.entity_font.bold(), (item.entity_color.red(), item.entity_color.green(), item.entity_color.blue())
        )

    # 5. Attributes
    for attr_item in item.attr_items:
        apos = attr_item.scenePos()
        text = attr_item.toPlainText()
        ax, ay = apos.x(), apos.y() + 2
        font = attr_item.font()
        color = attr_item.defaultTextColor()
        rgb = (color.red(), color.green(), color.blue())

        # Kiểm tra PK toàn diện: Font thuộc tính / Tên lớp / Cờ is_pk / Lớp truyền vào
        is_pk = (
            font.underline() or 
            getattr(attr_item, 'is_pk', False) or 
            getattr(attr_item, 'is_primary_key', False) or
            (pk_text_cls and isinstance(attr_item, pk_text_cls)) or
            "PKTextItem" in type(attr_item).__name__
        )

        canvas.draw_text(
            text, ax, ay, 
            font.family(), font.pointSize(), font.bold(), 
            rgb, italic=font.italic(), underline=is_pk
        )


def _draw_relationship(canvas: EmfCanvas, item):
    scene_pos = item.scenePos()
    pen = item.pen()
    pen_color = (pen.color().red(), pen.color().green(), pen.color().blue())
    pen_width = pen.widthF() or 2.0

    canvas.draw_qpainterpath(item.path(), scene_pos.x(), scene_pos.y(), pen_color, pen_width)

    if hasattr(item, "label_item") and item.label_item:
        lbl = item.label_item
        lpos = lbl.scenePos()
        text = lbl.toPlainText()
        font = lbl.font()
        color = lbl.defaultTextColor()
        rgb = (color.red(), color.green(), color.blue())
        canvas.draw_text(
            text, lpos.x() + 2, lpos.y() + 2,
            font.family(), font.pointSize(), font.bold(), rgb,
            italic=font.italic(), underline=font.underline()
        )


def export_scene_to_vector_emf(scene, file_path: str, scene_rect, white_background: bool) -> bool:
    from ..views.items.entity_item import EntityItem
    from ..views.items.relationship_item import RelationshipItem

    canvas = EmfCanvas(file_path, scene_rect)

    try:
        if white_background:
            canvas.fill_white_background()

        items_in_rect = scene.items(scene_rect)

        entities = [it for it in items_in_rect if isinstance(it, EntityItem)]
        relationships = [it for it in items_in_rect if isinstance(it, RelationshipItem)]

        all_items = sorted(entities + relationships, key=lambda it: it.zValue())

        pk_cls = getattr(EntityItem, "PKTextItem", None)

        for item in all_items:
            if isinstance(item, EntityItem):
                _draw_entity(canvas, item, pk_cls)
            elif isinstance(item, RelationshipItem):
                _draw_relationship(canvas, item)

        return canvas.close()
    except Exception as e:
        print(f"Lỗi khi xuất EMF vector: {e}")
        try:
            canvas.close()
        except Exception:
            pass
        return False