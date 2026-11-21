import io
import os
import time
import zipfile
from pathlib import Path
from multiprocessing import Pool
from PIL import Image
import itertools 
import random 

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp",
                    ".tiff", ".tif", ".webp", ".ico"}

# Junk that macOS and Windows put into zip files / folders
JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_PREFIXES = ("__MACOSX/",)

# ─────────────────────────────────────────────────────────────
# Worker-side state and functions  (module-level, picklable)
# ─────────────────────────────────────────────────────────────

_worker = {}


def _init_worker(make_pipeline_fn, icons, pipeline_kwargs): #runs one per worker process
    """
    Runs ONCE per worker process. Builds the pipeline — including the
    expensive build_icon_index / build_icon_tiles — and stores it.
    """
    _worker["pipeline"] = make_pipeline_fn(icons, **pipeline_kwargs)


def _process_one_worker(item):
    """
    Runs once per photo. Receives (name, raw_bytes) from the stream.
    Returns (name, png_bytes, error). Bytes in / bytes out = cheap pickling.
    """
    name, data = item
    t0 = time.perf_counter() # Start timer
    try:
        img = Image.open(io.BytesIO(data))
        img.load()

        width, height = img.size
        megapixels = (width * height) / 1_000_000 

        # 1. The pipeline now returns a tuple: (image, time)
        result = _worker["pipeline"](img) 
        
        # 2. Unpack the image and the time
        if isinstance(result, tuple):
            out, elapsed = result
        else:
            out, elapsed = result, 0.0

        buf = io.BytesIO()
        out.save(buf, format="PNG")

        elapsed = time.perf_counter() - t0 # Stop timer

        return name, buf.getvalue(), None, elapsed, megapixels
    
    except Exception as e:
        return name, None, f"{type(e).__name__}: {e}", 0.0, 0.0


# ─────────────────────────────────────────────────────────────
# Streaming reader  (one photo at a time; no bulk load)
# ─────────────────────────────────────────────────────────────

def _read_entries(src):
    """Yield (name, raw_bytes) one at a time, from a zip or a folder."""
    p = Path(src)
    
    if p.is_file() and p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p, "r") as zf:
            # 1. Build a list of valid files
            valid_entries = []
            for info in zf.infolist():
                name = info.filename
                if info.is_dir(): continue
                if Path(name).name in JUNK_NAMES: continue
                if Path(name).suffix.lower() not in IMAGE_EXTENSIONS: continue
                valid_entries.append(info)
            
            # 2. Shuffle the list (WITH A FIXED SEED)
            random.seed(42)  # <--- THIS IS THE MAGIC LINE
            random.shuffle(valid_entries)
            
            # 3. Yield the shuffled images
            for info in valid_entries:
                yield info.filename, zf.read(info.filename)
                
    elif p.is_dir():
        # 1. Build a list of valid files
        valid_files = []
        for f in p.iterdir(): 
            if not f.is_file(): continue
            if f.name in JUNK_NAMES: continue
            if f.suffix.lower() not in IMAGE_EXTENSIONS: continue
            valid_files.append(f)
            
        # 2. Shuffle the list (WITH A FIXED SEED)
        random.seed(42)  # <--- THIS IS THE MAGIC LINE
        random.shuffle(valid_files)
        
        # 3. Yield the shuffled images
        for f in valid_files:
            yield f.name, f.read_bytes()
            
    else:
        raise ValueError(f"Input must be a .zip file or a folder: {p}")


# ─────────────────────────────────────────────────────────────
# Parallel orchestrator
# ─────────────────────────────────────────────────────────────

def process_images_parallel(src, dst_zip, make_pipeline_fn, icons,
                            pipeline_kwargs=None,
                            workers=None,
                            verbose=True,
                            limit = None,
                            checkpoint_interval = 100):
    """
    Read photos from `src` (zip OR folder), dispatch each to a worker,
    write PNG results into `dst_zip`.

    make_pipeline_fn : callable(icons, **kwargs) -> callable(img) -> Image
                       Runs once per worker. Must be module-level so it's picklable.
    icons            : dict {name: PIL.Image}
    pipeline_kwargs  : kwargs forwarded to make_pipeline_fn
    workers          : number of worker processes (default: os.cpu_count())
    """
    pipeline_kwargs = pipeline_kwargs or {}
    workers = workers or os.cpu_count() or 1
    t0 = time.perf_counter()

    errors = {}
    written = 0
    processing_times = [] 
    resolutions = []

    progress_data = [] 
    running_seq_time = 0.0

    time_writing = 0.0

    entries = _read_entries(src)
    if limit is not None:
        entries = itertools.islice(entries, limit)

    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        with Pool(
            processes=workers,
            initializer=_init_worker,
            initargs=(make_pipeline_fn, icons, pipeline_kwargs),
        ) as pool:
            for name, png_bytes, err, m_time, megapixels in pool.imap_unordered(
                _process_one_worker, entries, chunksize=1
            ):
                if err:
                    errors[name] = err
                    if verbose:
                        print(f"  FAILED {name}: {err}")
                else:
                    out_name = Path(name).with_suffix(".png").name
                    t_write_start = time.perf_counter()
                    zf.writestr(out_name, png_bytes)
                    time_writing += time.perf_counter() - t_write_start

                    written += 1
                    if verbose:
                        print(f"  Processed {written} images.")

                    processing_times.append(m_time)
                    resolutions.append(megapixels)

                    running_seq_time += m_time

                    if written % checkpoint_interval == 0 or (limit and written == limit):
                        current_par_time = time.perf_counter() - t0
                        progress_data.append({
                            "images": written,
                            "approx_seq_time": running_seq_time,
                            "actual_par_time": current_par_time
                        })

    elapsed = time.perf_counter() - t0
    if verbose:
        print(f"Workers: {workers}  |  Wrote {written} PNG(s) → {dst_zip}")
        if errors:
            print(f"Failed: {len(errors)}")
        print(f"Total: {elapsed:.2f} s")

        pct_writing = (time_writing / elapsed) * 100
        print(f"Time spent writing to ZIP: {time_writing:.2f} s ({pct_writing:.1f}% of total)")

    return errors, {"workers": workers, "written": written, 
                    "elapsed": elapsed, "processing_times": processing_times, 
                    "time_writing": time_writing, "resolutions": resolutions,
                      "progress_data": progress_data}
