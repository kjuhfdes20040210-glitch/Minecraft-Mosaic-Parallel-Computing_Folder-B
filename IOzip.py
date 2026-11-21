import io
import zipfile
from pathlib import Path
from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp",
                    ".tiff", ".tif", ".webp", ".ico"}

# Junk that macOS and Windows put into zip files / folders
JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_PREFIXES = ("__MACOSX/",)

def _load_one(name, data):
    """
    Given a name and raw bytes, return a PIL Image in its native mode.
    No conversion — whatever Pillow opens is what you get.

    The image is `.copy()`-ed so it survives after the BytesIO is closed.
    """
    with Image.open(io.BytesIO(data)) as img:
        return img.copy()

def read_images_from_zip(zip_path):
    """
    Returns (images, errors, skipped):
      images  — {filename: PIL.Image (native mode)}
      errors  — {filename: error message}
      skipped — [filename, ...] for non-images and junk
    """
    images, errors, skipped = {}, {}, []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename

            # Skip directory entries and junk
            if info.is_dir():
                skipped.append(name)
                continue
            if Path(name).name in JUNK_NAMES:
                skipped.append(name)
                continue
            if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                skipped.append(name)
                continue

            try:
                images[name] = _load_one(name, zf.read(name))
            except (UnidentifiedImageError, OSError, SyntaxError) as e:
                errors[name] = f"{type(e).__name__}: {e}"

    return images, errors, skipped

def read_images_from_folder(folder_path):
    """
    Same return shape as the zip reader. Flat scan — only files directly
    in the folder, no subfolders.
    """
    folder_path = Path(folder_path)
    images, errors, skipped = {}, {}, []

    for p in sorted(folder_path.iterdir()):
        if not p.is_file():
            continue
        if p.name in JUNK_NAMES:
            skipped.append(p.name)
            continue
        if p.suffix.lower() not in IMAGE_EXTENSIONS:
            skipped.append(p.name)
            continue

        try:
            images[p.name] = _load_one(p.name, p.read_bytes())
        except (UnidentifiedImageError, OSError, SyntaxError) as e:
            errors[p.name] = f"{type(e).__name__}: {e}"

    return images, errors, skipped

def read_images(path):
    """
    Unified reader. `path` may be a .zip file or a folder.
    Returns (images, errors, skipped) either way.

    Images are returned in their native mode (RGB / RGBA / P / L / ...).
    Conversion to RGBA — if needed — is the caller's job.
    """
    p = Path(path)
    if p.is_file() and p.suffix.lower() == ".zip":
        return read_images_from_zip(p)
    if p.is_dir():
        return read_images_from_folder(p)
    raise ValueError(f"Input must be a .zip file or a folder: {p}")

def _png_bytes(img):
    """Encode a PIL Image to PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def write_images_to_zip(images, zip_path,
                        compression=zipfile.ZIP_DEFLATED):
    """
    Write {name: Image} into a new zip, all as PNG.
    The output entry name is the input name with the extension forced to .png.
    """
    with zipfile.ZipFile(zip_path, "w", compression=compression) as zf:
        for name, img in images.items():
            out_name = Path(name).with_suffix(".png").name
            zf.writestr(out_name, _png_bytes(img))

def process_images(src, dst_zip, process_fn=None, verbose=True):
    """
    Read images from `src` (zip OR folder), run each through `process_fn`,
    write the results into `dst_zip` (a .zip file).

    process_fn : callable {name: image} -> image.
                 If None, images pass through unchanged
                 (useful for pure re-pack / format normalization).
    """
    images, errors, skipped = read_images(src)

    if process_fn is None:
        processed = images
    else:
        processed = {}
        for name, img in images.items():
            try:
                processed[name] = process_fn(img)
                print(f"Processed {name} → {len(processed)} images")
                print()
            except Exception as e:
                errors[name] = f"process_fn failed: {type(e).__name__}: {e}"

    write_images_to_zip(images=processed, zip_path=dst_zip)

    if verbose:
        print(f"Source : {src}")
        print(f"  read    {len(images)} image(s)")
        print(f"  skipped {len(skipped)} non-image file(s)")
        if errors:
            print(f"  failed  {len(errors)} file(s)")
            for name, msg in list(errors.items())[:10]:
                print(f"    {name}: {msg}")
            if len(errors) > 10:
                print(f"    ... and {len(errors) - 10} more")
        print(f"Dest   : {dst_zip}")
        print(f"  wrote   {len(processed)} image(s)")

    return processed, errors, skipped