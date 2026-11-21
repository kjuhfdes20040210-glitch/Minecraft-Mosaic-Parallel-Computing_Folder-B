import colorsys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def make_contact_sheet(images, out="contact_sheet.png", cell=32, cols=32):

    """
    images: dict {name: PIL.Image} or list of (name, Image) tuples.
            Each image will be converted to RGBA and composited over light gray.
    """

    # Normalize input to a list of (name, image) pairs
    if isinstance(images, dict):
        items = list(images.items())
    else:
        items = list(images)   # already (name, img) pairs

    if not items:
        print("No images to draw.")
        return

    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), (240, 240, 240)) # cell is cell size in pixels


    for i, (name, img) in enumerate(items): # this loop fills each cell with each icon
        r, c = divmod(i, cols) # returns the row and column index

        rgba = img.convert("RGBA") if img.mode != "RGBA" else img

        bg = Image.new("RGBA", rgba.size, (240, 240, 240, 255))
        bg.alpha_composite(rgba)

        small = bg.convert("RGB").resize((cell, cell), Image.NEAREST) # scaling for upscale and downscale
        sheet.paste(small, (c * cell, r * cell))

    sheet.save(out)
    print(f"{len(items)} icons → {out}  ({cols}x{rows} grid)")
    print()



def make_hue_strip(images, out="hue_strip.png", cell=32, cols=32):
    
    """
    images: dict {name: PIL.Image} (RGBA or any mode)
    Sorts icons by hue, then draws them as a contact sheet.
    Grayscale icons are pushed to the end.
    """

    def mean_hsv(img):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])

        r, g, b = bg.resize((1, 1), Image.BOX).getpixel((0, 0)) # red channel, green channel, blue channel 0-255

        # re-encoding
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255) # hue, saturation, value 0-1

        # Grayscale/desaturated icons get sorted to the end, not scattered
        if s < 0.15:
            return (2.0, v)   # key = 2.0 so they land after all hue values
        return (h, s)

    items = sorted(images.items(), key=lambda kv: mean_hsv(kv[1]))

    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols*cell, rows*cell), (240, 240, 240))

    for i, (name, img) in enumerate(items):
        r, c = divmod(i, cols)
        rgba = img if img.mode == "RGBA" else img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (240, 240, 240, 255))
        bg.alpha_composite(rgba)
        small = bg.convert("RGB").resize((cell, cell), Image.NEAREST)
        sheet.paste(small, (c*cell, r*cell))

    sheet.save(out)
    print(f"{len(items)} icons sorted by hue → {out}")

HUE_ORDER   = ["red", "orange", "yellow", "green", "cyan",
               "blue", "purple", "magenta", "brown", "neutral"]
TONE_ORDER  = ["vivid", "muted", "pale", "gray"]
BRIGHT_ORDER = ["light", "mid", "dark"]

def grade_icon(img):
    """Return (hue_family, tone, brightness) labels for one image."""
    rgba = img.convert("RGBA")
    bg = Image.new("RGB", rgba.size, (255, 255, 255))
    bg.paste(rgba, mask=rgba.split()[3])

    hsv = np.asarray(bg.convert("HSV"), dtype=np.float32)
    h = hsv[..., 0] * 360 / 256
    s = hsv[..., 1] / 255
    v = hsv[..., 2] / 255

    mask = (s >= 0.15) & (v >= 0.15)
    if mask.sum() == 0:
        mean_v = float(v.mean())
        brightness = "light" if mean_v > 0.66 else "mid" if mean_v > 0.33 else "dark"
        return ("neutral", "gray", brightness)

    h_rad = np.radians(h[mask])
    w = s[mask]
    cx = (np.cos(h_rad) * w).sum() # hue is circular
    cy = (np.sin(h_rad) * w).sum() # w is saturation, we notice saturated colors more than desaturated ones
    mean_hue = float(np.degrees(np.arctan2(cy, cx)) % 360) # arctan2 is the correct inverse of (cos, sin)
    mean_sat = float(w.mean())
    mean_val = float(v[mask].mean())

    families = ["red", "orange", "yellow", "green",
                "cyan", "blue", "purple", "magenta"]
    hue_family = families[int(mean_hue // 45) % 8] # dividing the hue circle equally into 8 slices

    # hue is undefined for grey pixels
    # brown is dark-orange, it is not a hue in color wheel

    tone = "vivid" if mean_sat > 0.6 else "muted" if mean_sat > 0.3 else "pale" # empirical values, not theoretical
    brightness = "light" if mean_val > 0.66 else "mid" if mean_val > 0.33 else "dark"

    if hue_family == "orange" and brightness == "dark" and tone != "pale":
        hue_family = "brown"

    return (hue_family, tone, brightness)


def label_sort_key(label):
    h, t, b = label
    return (HUE_ORDER.index(h)   if h in HUE_ORDER   else 99,
            TONE_ORDER.index(t)  if t in TONE_ORDER  else 99,
            BRIGHT_ORDER.index(b) if b in BRIGHT_ORDER else 99)


def make_graded_sheet(images, out="graded_sheet.png",
                      cell=32, cols=32, gap=6):
    """
    images: dict {name: PIL.Image}
    Sorts by (hue_family, tone, brightness) and draws a contact sheet
    with a colored separator line between groups.
    """
    # Grade every icon, sort by the ordinal label
    graded = []
    for name, img in images.items():
        label = grade_icon(img)
        graded.append((label, name, img))
    graded.sort(key=lambda x: (label_sort_key(x[0]), x[1]))

    # Layout: cell size + gap between cells, but bigger gap between groups
    step = cell + gap
    rows = math.ceil(len(graded) / cols)
    W = cols * step
    H = rows * step

    sheet = Image.new("RGB", (W, H), (250, 250, 250))
    draw = ImageDraw.Draw(sheet) # wraps a PIL.Image object and provides drawing methods

    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except OSError:
        font = ImageFont.load_default()

    prev_label = None
    group_start_row = 0
    groups = []  # (label, start_index, end_index)

    for i, (label, name, img) in enumerate(graded):
        r, c = divmod(i, cols)

        # Detect group change → draw a new black line
        # A label group can span multiple rows
        if label != prev_label:
            if prev_label is not None:
                groups[-1] = (groups[-1][0], groups[-1][1], i)
            groups.append((label, i, i))  # end will be filled in later
            # Draw a thin tinted line across the top of this group's row
            if i > 0:
                sep_y = r * step
                draw.line([(0, sep_y), (W, sep_y)],
                          fill=(60, 60, 60), width=1)
            prev_label = label

        # Composite icon over white
        rgba = img if img.mode == "RGBA" else img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        small = bg.convert("RGB").resize((cell, cell), Image.NEAREST)

        x = c * step + gap // 2
        y = r * step + gap // 2
        sheet.paste(small, (x, y))

    groups[-1] = (groups[-1][0], groups[-1][1], len(graded))

    sheet.save(out)

    # ---- Console report ----
    print(f"{len(graded)} icons → {out}  ({cols} cols × {rows} rows)\n")
    print(f"{'Hue family':<10} {'Tone':<7} {'Brightness':<10} {'Count':>6}   Index range")
    print("-" * 60)
    for (h, t, b), start, end in groups:
        print(f"{h:<10} {t:<7} {b:<10} {end-start:>6}   {start}–{end-1}")

    return groups


