import os
from pathlib import Path
from PIL import Image, ImageFile, UnidentifiedImageError
from collections import Counter

# Allow loading of truncated images so we can detect partial corruption
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Common image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
                    ".tif", ".webp", ".heic", ".heif", ".ico", ".ppm", ".pgm"}

EXPECTED_SIZE = (16, 16)

def check_photos(folder: str | None = None) -> list[dict]:
    """
    Check all image files in the given folder (defaults to the script's folder)
    for format, pixel size, and potential damage.

    Returns a list of dicts with keys:
        file, format, mode, size (w,h), megapixels, status, issue
    """

    if folder is None:
        folder = Path(__file__).parent
    else:
        folder = Path(folder)   

    results = []

    for file in sorted(folder.iterdir()):
        if not file.is_file():
            continue
        if file.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        info = {
            "file": file.name,
            "format": None,
            "mode": None,
            "size": None,
        }

        
        with Image.open(file) as img:
            info["format"] = img.format # format, mode and size are attributes of Image object
            info["mode"] = img.mode
            info["size"] = img.size 

        if info["size"] != EXPECTED_SIZE:
            continue 

        results.append(info)

    return results


def print_report(results: list[dict]) -> None:

    if not results:
        print("No image files found.")
        return

    for r in results:
        size_str = f"{r['size'][0]}x{r['size'][1]}" if r["size"] else "-"
        print(f"{r['file']:<40} {str(r['format']):<8} {str(r['mode']):<6} {size_str:<14}") #run it if you want to see each photo information


    print("-" * 110)
    print(f"Total: {len(results)} image files found.")

    formats = Counter(r["format"] for r in results if r["format"])
    unknown = sum(1 for r in results if r["format"] is None)
    print("Format breakdown:")


    for fmt, count in sorted(formats.items(), key=lambda x: -x[1]): # sorting descending by count
        # .items() iterable of (format_string, count) tuples
        pct = 100 * count / len(results)
        print(f"  {fmt:<8} {count:>5}  ({pct:.1f}%)") #format specs
    if unknown:
        print(f"  {'Unknown':<8} {unknown:>5}  (unreadable/unidentified)") # two format specs

    w_exp, h_exp = EXPECTED_SIZE

    # I hide the below size check function, as images not being 16x16 already dropped out in the previous function
    '''print(f"Size check (expected {w_exp}x{h_exp}):")
    matching = [r for r in results if r["size"] == EXPECTED_SIZE]
    wrong_size = [r for r in results if r["size"] and r["size"] != EXPECTED_SIZE]
    no_size = [r for r in results if r["size"] is None]

    print(f"  Correct size : {len(matching):>5} / {len(results)}")
    print(f"  Wrong size   : {len(wrong_size):>5} / {len(results)}")

    if wrong_size:
        print("  Files with unexpected size:")
        for r in wrong_size[:20]:   # cap to 20 so it doesn't flood the console
            print(f"    {r['file']:<40} {r['size'][0]}x{r['size'][1]}")
        if len(wrong_size) > 20:
            print(f"    ... and {len(wrong_size) - 20} more")'''

    print("Modes:  ", dict(Counter(r["mode"]   for r in results if r["mode"])))
    print()

def load_all_as_rgba(folder):
    folder = Path(folder)
    images = {}
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".bmp",
                                    ".tiff", ".tif", ".webp"}:
            continue
        with Image.open(f) as img:
            images[f.name] = img.convert("RGBA")   # stored fully decoded
    return images



    