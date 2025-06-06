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

    code_name = CABLE_NAME_MAP.get(code, "NOMA'LUM")

    # Layout constants
    padding_left = 5 * mm
    padding_top = 5 * mm
    padding_right = 5 * mm
    x_text = padding_left
    y_start = label_height - padding_top
    line_height = 10

    # Use slightly larger font size
    font_size = 9
    c.setFont("DejaVuSans", font_size)

    def draw_bold_text(x, y, text):
        # Fake bold effect by drawing twice with small offset
        c.drawString(x, y, text)
        c.drawString(x + 0.2, y, text)

    y = y_start
    draw_bold_text(x_text, y, f"Tovar kodi : {code}")
    y -= line_height
    draw_bold_text(x_text, y, code_name)
    y -= line_height
    draw_bold_text(x_text, y, f"Uzunligi : {metr}")
    y -= line_height
    draw_bold_text(x_text, y, f"Og'irligi : {kg}")

    # Generate QR code
    qr_size = 1.5 * cm
    qr_img = qrcode.make(barkod)
    qr_x = label_width - padding_right - qr_size
    qr_y = label_height - padding_top - qr_size
    c.drawInlineImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

    # Barcode number under QR
    c.setFont("DejaVuSans", 9)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 12, barkod)

    c.rect(0, 0, label_width, label_height)

    c.save()
    buffer.seek(0)
    return buffer

def generate_custom_label(text: str):
    # Validate and split the input
    if not text or "-" not in text:
        raise ValueError("Invalid input format. Expected ****-**")

    left, right = text.strip().split("-")
    if not (left.isdigit() and right.isdigit()):
        raise ValueError("Both parts must be numeric.")

    label_width = 6 * cm
    label_height = 2.8 * cm
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(label_width, label_height))

    # Layout settings
    padding = 5 * mm
    qr_size = 2.2 * cm
    font_size = 11
    line_height = font_size + 2  # spacing between lines

    # Set font larger for left side text
    c.setFont("DejaVuSans", font_size)

    # Calculate total text block height (2 lines)
    text_block_height = 2 * line_height
    y_text_start = (label_height + text_block_height) / 2 - line_height

    x_left = padding
    y = y_text_start
    c.drawString(x_left, y, left)
    y -= line_height
    c.drawString(x_left, y, f"Razmer : {right}")

    # Generate QR code for only the left part
    qr_img = qrcode.make(left)
    qr_x = label_width - qr_size - padding
    qr_y = (label_height - qr_size) / 2
    c.drawInlineImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

    # Optional: border
    c.rect(0, 0, label_width, label_height)

    c.save()
    buffer.seek(0)
    return buffer

def generate_custom_label_page(c, text: str):
    if not text or "-" not in text:
        return

    left, right = text.strip().split("-")
    if not (left.isdigit() and right.isdigit()):
        return

    # Layout
    label_width = 6 * cm
    label_height = 2.8 * cm
    padding = 5 * mm
    qr_size = 2.2 * cm
    font_size = 11
    line_height = font_size + 2

    # Text block vertical center
    text_block_height = 2 * line_height
    y_text_start = (label_height + text_block_height) / 2 - line_height

    x_left = padding
    y = y_text_start
    c.setFont("DejaVuSans", font_size)
    c.drawString(x_left, y, left)
    y -= line_height
    c.drawString(x_left, y, f"Razmer : {right}")

    # QR code (left only)
    qr_img = qrcode.make(left)
    qr_x = label_width - qr_size - padding
    qr_y = (label_height - qr_size) / 2
    c.drawInlineImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

    # Optional border
    c.rect(0, 0, label_width, label_height)

if __name__ == "__main__":
    pdf = generate_pdf("GPC0040", "150", "7.00", "100016689")
    with open("example_label.pdf", "wb") as f:
        f.write(pdf.read())
    print("✅ Label PDF generated: example_label.pdf")

    pdf = generate_custom_label("1234-56")
    with open("example_label2.pdf", "wb") as f:
        f.write(pdf.read())
    print("✅ Label PDF generated: example_label2.pdf")
