import random
from PIL import Image

def paste_icons_onto_plane(images, icon_size=16,
                           min_icons=2, max_icons=20,
                           seed=None, bg=(255, 255, 255, 255)):
    """
    images:    dict {name: PIL.Image} or list of PIL.Image (all same size)
    icon_size: expected icon dimension in pixels (int)
    min_icons: minimum icons per axis in the random size
    max_icons: maximum icons per axis in the random size
    seed:      optional random seed for reproducibility

    Returns (cropped, blank, info):
        cropped — plane size = (cols*icon_size, rows*icon_size), no leftover
        blank   — plane size = original random (W, H), leftover stays as bg
    """
    rng = random.Random(seed)

    # ── 1. Generate ONE random plane size ──
    cols = rng.randint(min_icons, max_icons)
    rows = rng.randint(min_icons, max_icons)
    # Random extra leftover: 0 .. icon_size-1 on each axis (may be zero)
    extra_w = rng.randint(0, icon_size - 1)
    extra_h = rng.randint(0, icon_size - 1)

    W = cols * icon_size + extra_w
    H = rows * icon_size + extra_h

    # ── 2. Prepare icon list ──
    icons = list(images.values()) if isinstance(images, dict) else list(images)
    if not icons:
        raise ValueError("No icons provided")

    # ── 3. Two canvases ──
    cropped = Image.new("RGBA", (cols * icon_size, rows * icon_size), bg) # no leftover
    blank   = Image.new("RGBA", (W, H), bg)

    # ── 4. Paste in grid, cycling through icons ──
    idx = 0
    for r in range(rows):
        for c in range(cols):
            icon = icons[idx % len(icons)]
            icon = icon if icon.mode == "RGBA" else icon.convert("RGBA")
            x, y = c * icon_size, r * icon_size
            cropped.alpha_composite(icon, (x, y))
            blank.alpha_composite(icon, (x, y))
            idx += 1

    info = {
        "random_size": (W, H),
        "grid": (cols, rows),
        "used_size": (cols * icon_size, rows * icon_size),
        "leftover": (extra_w, extra_h),
        "icons_placed": cols * rows,
    }
    return cropped, blank, info