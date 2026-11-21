from PIL import Image
from colorgrading import grade_icon, label_sort_key
import numpy as np

HUE_ORDER   = ["red", "orange", "yellow", "green", "cyan",
               "blue", "purple", "magenta", "brown", "neutral"]
TONE_ORDER  = ["vivid", "muted", "pale", "gray"]
BRIGHT_ORDER = ["light", "mid", "dark"]

def crop_source_to_grid(img, tile_size):
    """
    Load a source image and crop it (centered) to the largest dimensions
    that are exact multiples of `tile_size`. No downsampling — original
    resolution is preserved except for the unavoidable trim.

    img : PIL.Image object
    tile_size   : pixels per tile in the OUTPUT (e.g. 32 for 16x16 icons at 1:2)

    Returns (cropped_img, rows, cols, info)
    """
    src = img.convert("RGB")
    original_size = src.size
    W, H = src.size

    cols = W // tile_size # the symbol // rounds down, discarding the remainder
    rows = H // tile_size

    if cols == 0 or rows == 0:
        raise ValueError(
            f"Source too small ({W}x{H}) for tile_size={tile_size}. "
            f"Need at least {tile_size}x{tile_size}."
        )

    # Exact multiple dimensions after trim
    crop_W = cols * tile_size
    crop_H = rows * tile_size

    # It splits the crop evenly to provide a centereed crop
    left = (W - crop_W) // 2
    top  = (H - crop_H) // 2
    cropped = src.crop((left, top, left + crop_W, top + crop_H))

    info = {
        "original_size": original_size,
        "cropped_size":  (crop_W, crop_H),
        "tile_size":     tile_size,
        "rows":          rows,
        "cols":          cols,
        "crop_offset":   (left, top),
        "trimmed":       (W - crop_W, H - crop_H),
    }
    print(f"Source {original_size} → cropped {crop_W}x{crop_H} "
          f"({cols}x{rows} tiles of {tile_size}px). "
          f"Trimmed {W - crop_W}px width, {H - crop_H}px height "
          f"(centered, {left}px left / {top}px top offset).")
    return cropped, rows, cols, info


def slice_into_cells(cropped_img, tile_size, rows, cols):
    """
    Slice a cropped image into a rows x cols grid of tile_size x tile_size cells.

    Returns a 2D list: cells[r][c] = PIL.Image of that cell.
    """
    cells = [[None] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            box = (c * tile_size, r * tile_size,
                   (c + 1) * tile_size, (r + 1) * tile_size) # 4-tuple (left, upper, right, lower), it is a pixel coordinate 
            cells[r][c] = cropped_img.crop(box)
    return cells


def image_hsv_stats(img):
    """
    Standalone numeric HSV fingerprint for an image.

    Returns (hue, sat, val):
        hue — circular saturation-weighted mean, in degrees [0,360), or None
              if the image is effectively grayscale
        sat — mean saturation of colorful pixels (0..1)
        val — mean value of colorful pixels (0..1), or full-image mean if
              the image is grayscale

    NOTE: this duplicates the math in grade_icon on purpose so grade_icon
    can stay untouched. They must agree — if you change the thresholds or
    the weighting in one, change it in the other.
    """
    rgba = img.convert("RGBA")
    bg = Image.new("RGB", rgba.size, (255, 255, 255))
    bg.paste(rgba, mask=rgba.split()[3])

    hsv = np.asarray(bg.convert("HSV"), dtype=np.float32)
    h = hsv[..., 0] * 360 / 256
    s = hsv[..., 1] / 255
    v = hsv[..., 2] / 255

    mask = (s >= 0.15) & (v >= 0.15) # s >= 0.15 filters out near-grey pixels, v >= 0.15 filters out near-black pixels
    if mask.sum() == 0:
        return (None, 0.0, float(v.mean()))

    h_rad = np.radians(h[mask])
    w = s[mask]
    cx = (np.cos(h_rad) * w).sum()
    cy = (np.sin(h_rad) * w).sum()
    if abs(cx) + abs(cy) < 1e-9:
        return (None, float(w.mean()), float(v[mask].mean()))

    mean_hue = float(np.degrees(np.arctan2(cy, cx)) % 360)
    mean_sat = float(w.mean())
    mean_val = float(v[mask].mean())
    return (mean_hue, mean_sat, mean_val)

def hsv_distance(hsv_a, hsv_b):
    """
    Distance between two (hue, sat, val) triples.
    Hue is circular; grayscale entries (hue=None) compare on sat/val only.
    Weights: hue dominates, then sat, then val.
    """
    hue_a, sat_a, val_a = hsv_a
    hue_b, sat_b, val_b = hsv_b

    if hue_a is None or hue_b is None:
        return abs(sat_a - sat_b) + abs(val_a - val_b)

    dh = abs(hue_a - hue_b) % 360 # It gives raw distance, normalized by 360
    dh = min(dh, 360 - dh) / 180.0   # It gives shortest distance around the circle, normalized by 180
    ds = abs(sat_a - sat_b)
    dv = abs(val_a - val_b)
    return 2.0 * dh + 1.0 * ds + 0.5 * dv # designed weights: hue matters most, then saturation, then value

def build_icon_index(icons):
    """
    Group icons by the label grade_icon assigns them, and also keep a flat
    list with HSV stats for fallback matching.

    Returns (by_label, all_icons):
        by_label  — {(family, tone, brightness): [(name, hsv, img), ...]}
        all_icons — [(name, hsv, img), ...]
    """
    by_label = {}
    all_icons = []

    for name, img in icons.items():
        label = grade_icon(img)         
        hsv = image_hsv_stats(img)       
        entry = (name, hsv, img)

        by_label.setdefault(label, []).append(entry) # groupiong operation, if label is not a key in the dict, it creates a new list for that key 
        all_icons.append(entry) # adds the entry to the list

    return by_label, all_icons

def match_cell_to_icon(cell_hsv, cell_label, by_label, all_icons,
                       tiebreak_k=1, rng=None):
    """
    Pick an icon for a cell.

    tier 1: same (family, tone, brightness) — closest by hsv_distance
    tier 2: same family only — closest by hsv_distance
    tier 3: any icon — closest by hsv_distance

    tiebreak_k: if > 1, pick randomly among the K closest (variety). Needs rng.
    Returns (name, tier) where tier in {"exact", "family", "any"}.
    """
    def best(candidates):
        ranked = sorted(candidates, key=lambda e: hsv_distance(cell_hsv, e[1]))
        if tiebreak_k <= 1 or rng is None:
            return ranked[0] #picke the top choice 
        return rng.choice(ranked[:min(tiebreak_k, len(ranked))]) # randomly pick one of the top K closest candidates, this is for diversity in the mosaic

    bucket = by_label.get(cell_label)
    if bucket:
        name, _, _ = best(bucket)
        return name, "exact" # same exact label

    family = cell_label[0]
    same_family = [e for e in all_icons
                   if grade_icon(e[2])[0] == family]
    if same_family:
        name, _, _ = best(same_family)
        return name, "family" # same family only

    name, _, _ = best(all_icons)
    return name, "any"

def build_icon_tiles(icons, tile_size, background=(255, 255, 255, 255)): # in the process, no upscale or downscale has been done, all the icons are in 16x16
    """
    Resize each icon (composited over `background`) to tile_size x tile_size.
    Uses NEAREST when upscaling (pixel art stays crisp), LANCZOS when downscaling.
    Returns {name: PIL.Image (RGBA)}.
    """
    tiles = {}
    for name, img in icons.items():
        rgba = img if img.mode == "RGBA" else img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, background)
        bg.alpha_composite(rgba)
        if bg.size != (tile_size, tile_size):
            resample = Image.NEAREST if tile_size >= bg.size[0] else Image.LANCZOS
            bg = bg.resize((tile_size, tile_size), resample)
        tiles[name] = bg
    return tiles

def assemble_mosaic(rows, cols, tile_size, matches, icon_tiles,
                    background=(255, 255, 255, 255)):
    """
    Paste the chosen icons into a fresh image.

    matches     — 2D list [rows][cols] of icon names (from match_cell_to_icon)
    icon_tiles  — dict {name: PIL.Image already at tile_size}
    Returns the finished PIL.Image.
    """
    
    out = Image.new("RGBA", (cols * tile_size, rows * tile_size), background)
    for r in range(rows):
        for c in range(cols):
            name = matches[r][c]
            out.alpha_composite(icon_tiles[name],
                                (c * tile_size, r * tile_size))
    return out

def make_mosaic(source_path, icons, tile_size=32, out_path="mosaic.png",
                tiebreak_k=1, seed=None, verbose=True):
    """
    Full pipeline:
      1. crop source to exact grid multiple
      2. slice into cells
      3. grade each cell with grade_icon (same classifier as icons)
      4. match each cell to an icon (3-tier fallback)
      5. assemble and save

    tiebreak_k > 1 picks randomly among the K closest icons in each bucket —
    use it to break up repetition in large uniform regions of the source.
    """
    import random
    rng = random.Random(seed) if seed is not None else random

    cropped, rows, cols, info = crop_source_to_grid(source_path, tile_size) # first crop and grade the source image

    cells = slice_into_cells(cropped, tile_size, rows, cols)

    labels = [[None] * cols for _ in range(rows)]
    cell_hsvs = [[None] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            labels[r][c] = grade_icon(cells[r][c])        
            cell_hsvs[r][c] = image_hsv_stats(cells[r][c]) 

    by_label, all_icons = build_icon_index(icons) # grade and index the icons for matching
    matches = [[None] * cols for _ in range(rows)]
    tiers = {"exact": 0, "family": 0, "any": 0}

    for r in range(rows):
        for c in range(cols):
            name, tier = match_cell_to_icon(
                cell_hsvs[r][c], labels[r][c], by_label, all_icons, # matching with 3-tier, exact label, same family, any icon
                tiebreak_k=tiebreak_k, rng=rng)
            matches[r][c] = name
            tiers[tier] += 1


    icon_tiles = build_icon_tiles(icons, tile_size)
    out = assemble_mosaic(rows, cols, tile_size, matches, icon_tiles)
    out.save(out_path)

    if verbose:
        total = rows * cols
        print(f"Mosaic: {cols}x{rows} = {total} cells, tile={tile_size}px "
              f"→ {out_path}  ({out.size[0]}x{out.size[1]})")
        print(f"  tier 1 (exact label) : {tiers['exact']:>6} "
              f"({100*tiers['exact']/total:5.1f}%)")
        print(f"  tier 2 (same family) : {tiers['family']:>6} "
              f"({100*tiers['family']/total:5.1f}%)")
        print(f"  tier 3 (any icon)    : {tiers['any']:>6} "
              f"({100*tiers['any']/total:5.1f}%)")
        if tiers["any"] > total * 0.1:
            print("  note: >10% of cells had no same-family icon. "
                  "Consider expanding your icon set in those families.")

    return out #out, matches, labels, tiers