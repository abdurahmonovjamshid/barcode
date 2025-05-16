from io import BytesIO
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
import os
from conf.settings import BASE_DIR  # Your Django-style BASE_DIR

# Register Cyrillic-safe font
FONT_PATH = os.path.join(BASE_DIR, "bot/DejaVuSans.ttf")
if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))

# Load cable names from .txt (Windows-1251 encoded)
def load_cable_name_map(filename):
    cable_map = {}
    with open(filename, encoding="cp1251") as f:
        next(f)  # Skip header line
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                code, name = parts
                cable_map[code.strip()] = name.strip()
    return cable_map

# Load it once globally
CABLE_NAME_MAP = load_cable_name_map(os.path.join(BASE_DIR, "bot/cable names.txt"))

def generate_pdf(code, metr, kg, barkod):
    label_width = 6 * cm
    label_height = 2.8 * cm

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(label_width, label_height))

    # Get cable name from map
    code_name = CABLE_NAME_MAP.get(code, "NOMA'LUM")

    # Layout constants
    padding_left = 5 * mm
    padding_top = 5 * mm
    padding_right = 5 * mm
    x_text = padding_left
    y_start = label_height - padding_top
    line_height = 10

    # Draw left text block
    c.setFont("DejaVuSans", 8)
    y = y_start
    c.drawString(x_text, y, f"Tovar kodi : {code}")
    y -= line_height
    c.drawString(x_text, y, code_name)
    y -= line_height
    c.drawString(x_text, y, f"Uzunligi : {metr}")
    y -= line_height
    c.drawString(x_text, y, f"Og'irligi : {kg}")

    # Generate QR code
    qr_size = 1.5 * cm
    qr_img = qrcode.make(barkod)
    qr_x = label_width - padding_right - qr_size
    qr_y = label_height - padding_top - qr_size
    c.drawInlineImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

    # Draw barcode number under QR
    c.setFont("DejaVuSans", 8)
    barcode_y = qr_y - 12
    c.drawCentredString(qr_x + qr_size / 2, barcode_y, barkod)

    # Draw optional border
    c.rect(0, 0, label_width, label_height)

    # Finalize PDF
    c.save()
    buffer.seek(0)
    return buffer

# Example usage (for testing):
if __name__ == "__main__":
    pdf = generate_pdf("GPC0040", "150", "7.00", "100016689", CABLE_NAME_MAP)
    with open("example_label.pdf", "wb") as f:
        f.write(pdf.read())
    print("✅ Label PDF generated: example_label.pdf")
