import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle, Ellipse, Arc
from dataprep import load_all_as_rgba
from Python_multiprocessing import process_images_parallel
from IOzip import process_images
from orchestrator import setup_pipeline


flowchart = False
if flowchart:
    # --- GLOBAL FONT SETTINGS ---
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

    def draw_parallelogram(ax, x, y, w, h, text, color, fontsize=18, skew=0.4):
        """Draws an input/output parallelogram."""
        pts = [(x + skew, y), (x + w + skew, y), (x + w, y + h), (x, y + h)]
        ax.add_patch(Polygon(pts, closed=True, fc=color, ec="black", lw=1.5, zorder=2))
        ax.text(x + w/2 + skew/2, y + h/2, text,
                ha="center", va="center", fontsize=fontsize, zorder=3)

    def draw_cylinder(ax, x, y, w, h, text, color, fontsize=18):
        """Draws a data store cylinder with a dotted back curve."""
        ellipse_h = h * 0.3
        top_y = y + h - ellipse_h/2
        bottom_y = y + ellipse_h/2
        
        # 1. Draw the filled body
        ax.add_patch(Rectangle((x, bottom_y), w, h - ellipse_h, 
                            fc=color, ec="none", zorder=1))
        ax.add_patch(Ellipse((x + w/2, bottom_y), w, ellipse_h, 
                            fc=color, ec="none", zorder=1))
        ax.add_patch(Ellipse((x + w/2, top_y), w, ellipse_h, 
                            fc=color, ec="none", zorder=1))
        
        # 2. Draw the outlines
        ax.plot([x, x], [bottom_y, top_y], color="black", lw=1.5, zorder=2)
        ax.plot([x + w, x + w], [bottom_y, top_y], color="black", lw=1.5, zorder=2)
        
        # Bottom back curve (dotted)
        ax.add_patch(Arc((x + w/2, bottom_y), w, ellipse_h, 
                        theta1=0, theta2=180, color="black", lw=1.5, linestyle="--", zorder=2))
        
        # Bottom front curve (solid)
        ax.add_patch(Arc((x + w/2, bottom_y), w, ellipse_h, 
                        theta1=180, theta2=360, color="black", lw=1.5, zorder=2))
        
        # Top ellipse (fully solid)
        ax.add_patch(Ellipse((x + w/2, top_y), w, ellipse_h, 
                            fc="none", ec="black", lw=1.5, zorder=2))
        
        # Text
        ax.text(x + w/2, y + h/2 - 0.1, text, 
                ha="center", va="center", fontsize=fontsize, zorder=3)

    def draw_rectangle(ax, x, y, w, h, text, color, fontsize=20):
        """Draws a process rectangle."""
        ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="black", lw=1.5, zorder=2))
        ax.text(x + w/2, y + h/2, text,
                ha="center", va="center", fontsize=fontsize, zorder=3)

    def draw_arrow(ax, x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>",
            mutation_scale=25, lw=2, color="black", zorder=4))

    # Increase the overall figure size to give text more room
    fig, ax = plt.subplots(figsize=(14, 7)) 
    ax.set_xlim(0, 14); ax.set_ylim(0, 7); ax.axis("off")

    # ── Colors ──
    color_io = "#DCE8F5"      
    color_icons = "#FCE8D5"   
    color_process = "#D5E8D4" 

    # ── Dimensions ──
    skew = 0.4 
    center_x = 7.0

    # Center substitution (Process)
    sub_w, sub_h = 4.5, 2.6
    sub_x, sub_y = center_x - sub_w/2, 1.2

    # Source Images (Input) - Left
    src_w, src_h = 2.8, 1.8
    src_x, src_y = 0.5, sub_y + (sub_h - src_h)/2

    # Photomosaic (Output) - Right
    out_w, out_h = 2.8, 1.8
    out_x, out_y = 10.7, sub_y + (sub_h - out_h)/2

    # Icon Library (Data Store) - Top
    icon_w, icon_h = 3.2, 1.8
    icon_x, icon_y = center_x - icon_w/2, 4.8

    # ── Draw Shapes ──
    draw_parallelogram(ax, src_x, src_y, src_w, src_h, "Source\nImages", color_io, skew=skew)
    
    # Added line break to the icon library text so it fits in the cylinder
    draw_cylinder(ax, icon_x, icon_y, icon_w, icon_h, "Minecraft\nBlock Library", color_icons)
    
    draw_rectangle(ax, sub_x, sub_y, sub_w, sub_h, "Color-matched\nSubstitution", color_process)
    
    draw_parallelogram(ax, out_x, out_y, out_w, out_h, "Photomosaic", color_io, skew=skew)

    # ── Draw Arrows ──
    # Source -> Substitution
    src_right_x = src_x + src_w + skew/2
    draw_arrow(ax, src_right_x, src_y + src_h/2, sub_x, sub_y + sub_h/2)

    # Icon Library -> Substitution (90 degrees straight down)
    icon_bottom_y = icon_y
    draw_arrow(ax, center_x, icon_bottom_y, center_x, sub_y + sub_h)

    # Substitution -> Photomosaic
    out_left_x = out_x + skew/2
    draw_arrow(ax, sub_x + sub_w, sub_y + sub_h/2, out_left_x, out_y + out_h/2)

    plt.tight_layout()
    plt.savefig("mosaic_flowchart.png", dpi=300, bbox_inches="tight")
    plt.show()

overallspeedup = False
if overallspeedup:
    import matplotlib.pyplot as plt
    import numpy as np

    # ==========================================
    # 1. SETUP & SIMULATED DATA
    # ==========================================
    # X-axis: 1 to 100 images
    n_images = np.arange(1, 101)

    # Assume 5 seconds per image
    avg_time_per_image = 5.0 
    sequential_time = n_images * avg_time_per_image

    # Parallel formula: (Total Work / Cores) + Startup Overhead
    cores = 12
    overhead = 2.0
    parallel_time = (n_images * avg_time_per_image) / cores + overhead

    # Calculate speedup
    speedup = sequential_time / parallel_time
    ideal_speedup = np.full(len(n_images), cores) # A flat line at 12x

    # ==========================================
    # 2. CREATE THE PLOT (2 Rows, 1 Column)
    # ==========================================
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 10))

    # --- Top Chart: Execution Time ---
    ax1.plot(n_images, sequential_time, color='#D9534F', linewidth=2.5, label='Sequential (1 Worker)')
    ax1.plot(n_images, parallel_time, color='#5CB85C', linewidth=2.5, label='Parallel (12 Workers)')

    ax1.set_title('Execution Time vs. Number of Images', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('Clock Time (Seconds)', fontsize=12)
    ax1.set_xlabel('Number of Images Processed', fontsize=11)
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(fontsize=11, loc='upper left')
    ax1.spines[['top', 'right']].set_visible(False)

    # --- Bottom Chart: Speedup Ratio ---
    ax2.plot(n_images, speedup, color='#0275D8', linewidth=2.5, label='Actual Speedup')
    ax2.plot(n_images, ideal_speedup, color='gray', linestyle='--', linewidth=2, label='Ideal Speedup (12x)')

    ax2.set_title('Parallelization Speedup vs. Number of Images', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('Speedup Ratio (Seq / Par)', fontsize=12)
    ax2.set_xlabel('Number of Images Processed', fontsize=11)
    ax2.set_ylim(0, 14) # Lock Y-axis to show the 12x ceiling clearly
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(fontsize=11, loc='lower right')
    ax2.spines[['top', 'right']].set_visible(False)

    # ==========================================
    # 3. FINALIZE & SAVE
    # ==========================================
    plt.tight_layout(pad=3.0)
    plt.savefig("scaling_benchmark.png", dpi=300, bbox_inches="tight")
    plt.show()

pixelbar = False
if pixelbar:

    import matplotlib.pyplot as plt
    import numpy as np

    # ==========================================
    # 1. SIMULATE A LARGE BATCH (500 IMAGES)
    # ==========================================
    np.random.seed(42) # For reproducible results

    # Simulate 500 images:
    # 450 normal images (clustered around 5-12 seconds)
    # 40 large images (clustered around 25-40 seconds)
    # 10 massive outliers (8K images, 100-500 seconds)
    times_normal = np.random.normal(loc=8, scale=2, size=450)
    times_large = np.random.normal(loc=30, scale=5, size=40)
    times_outliers = np.random.uniform(100, 500, size=10)

    processing_times = np.concatenate([times_normal, times_large, times_outliers])
    processing_times = np.clip(processing_times, a_min=1, a_max=None) # No negative times

    # ==========================================
    # 2. CREATE THE HISTOGRAM
    # ==========================================
    fig, ax = plt.subplots(figsize=(10, 6))

    # We use a log scale for the X-axis so the 8K outliers don't shrink the main bell curve
    bins = np.logspace(np.log10(1), np.log10(600), 40)

    # Plot Histogram (density=False means the Y-axis is the raw count/frequency)
    counts, bins, patches = ax.hist(
        processing_times, 
        bins=bins, 
        color='#5CB85C', 
        edgecolor='black', 
        alpha=0.8,
        linewidth=1.2
    )

    # Color the outlier bins red to highlight the 8K stragglers
    for i, count in enumerate(counts):
        if bins[i] > 50: # If the bin starts after 50 seconds
            patches[i].set_facecolor('#D9534F')

    # ==========================================
    # 3. FORMATTING
    # ==========================================
    ax.set_xscale('log')
    ax.set_title('Frequency Distribution of Processing Times (500 Images)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Processing Time (Seconds) - Log Scale', fontsize=12)
    ax.set_ylabel('Frequency (Number of Photos)', fontsize=12)

    ax.grid(axis='y', linestyle='--', alpha=0.6)
    ax.spines[['top', 'right']].set_visible(False)

    # Add a text annotation to explain the tail
    ax.annotate('The "Right Skew" Tail\n(Large / 8K Images)', 
                xy=(150, 2), 
                xytext=(50, 30),
                arrowprops=dict(facecolor='black', arrowstyle='->'),
                fontsize=11, color='#D9534F', fontweight='bold')

    plt.tight_layout()
    plt.savefig("time_distribution_frequency.png", dpi=300, bbox_inches="tight")
    plt.show()

time_frequency_plot = False
if time_frequency_plot:

    import matplotlib.pyplot as plt
    import numpy as np

    if __name__ == "__main__":  
        icons = load_all_as_rgba(r"C:\Users\kjuhf\Desktop\SemA Year 4\Data-intensive computing\Project\Code\minecraft_textures") #Change this path to yours

        sequential = False
        parallel = True

        if sequential:
            sequential_pipeline = setup_pipeline(icons) 

            # input file can be either a zip file or a folder of images. Output is a zip file of mosaic images.
            # .zip is in simple ZIP format
            process_images("Folder_test.zip", "sequential_computing_result.zip", process_fn=sequential_pipeline)

        if parallel:
            # input can be either a zip file or a folder of images. Output is a zip file of mosaic images.
            # .zip is in simple ZIP format
            errors, stats = process_images_parallel("sample_images_24", "sample_images_24_parallel_computing_result.zip", make_pipeline_fn=setup_pipeline, icons=icons, pipeline_kwargs={})

            # Assuming you just ran: errors, stats = process_images_parallel(...)
            all_times = stats["processing_times"]

            # Get your 24 images, filtering out any 0.0s (which happen if a file failed)
            times = [t for t in all_times if t > 0][:24]

            if len(times) == 0:
                print("No valid times to plot!")
            else:
                # ==========================================
                # 2. DYNAMICALLY CREATE LOG BINS
                # ==========================================
                # Find the fastest and slowest images in your 24 images
                min_val = max(min(times), 0.01) # Prevent log(0) errors
                max_val = max(times) * 1.2      # Add 20% headroom to the right side
                
                # Create 10 logarithmic bins spanning your exact data range
                bins = np.logspace(np.log10(min_val), np.log10(max_val), 11)

                fig, ax = plt.subplots(figsize=(11, 6))

                # ==========================================
                # 3. PLOT THE HISTOGRAM
                # ==========================================
                counts, bins, patches = ax.hist(
                    times, 
                    bins=bins, 
                    color="#503F20", 
                    edgecolor='black', 
                    linewidth=1.2
                )

                # Color the extreme outliers red (anything over 60 seconds)
                for i, count in enumerate(counts):
                    if bins[i] > 60:
                        patches[i].set_facecolor('#D9534F')

                # Add frequency labels on top of the bars
                for count, patch in zip(counts, patches):
                    if count > 0:
                        x = patch.get_x() + patch.get_width() / 2
                        y = patch.get_height()
                        ax.text(x, y + 0.1, f'{int(count)}', ha='center', va='bottom', fontsize=11, fontweight='bold')

                # ==========================================
                # 4. FORMATTING & LOG SCALE
                # ==========================================
                ax.set_xscale('log') # <--- THE MAGIC FIX

                ax.set_title('Mosaic Generation Time Distribution (24 Images)', fontsize=14, fontweight='bold', pad=15)
                ax.set_xlabel('Processing Time (Log Scale)', fontsize=12)
                ax.set_ylabel('Frequency (Number of Photos)', fontsize=12)

                ax.yaxis.get_major_locator().set_params(integer=True)
                ax.grid(axis='y', linestyle='--', alpha=0.7)
                ax.grid(axis='x', linestyle='--', alpha=0.4)
                ax.spines[['top', 'right']].set_visible(False)

                plt.tight_layout()
                plt.savefig("mosaic_time_distribution_log.png", dpi=300, bbox_inches="tight")
                plt.show()

if __name__ == "__main__":  
    icons = load_all_as_rgba(r"C:\Users\kjuhf\Desktop\SemA Year 4\Data-intensive computing\Project\Code\minecraft_textures")
    ICONS = icons # Your loaded icons dict

    comparison_graphs = False
    if comparison_graphs:
        import time
        import itertools
        import matplotlib.pyplot as plt
        import numpy as np
        from Python_multiprocessing import process_images_parallel, _read_entries
        from orchestrator import setup_pipeline

        # ==========================================
        # 1. SETUP
        # ==========================================
        SOURCE_ZIP = "your_2000_images.zip"

        # The batch sizes to test
        batch_sizes = [1, 10, 20, 30, 40]#5, 10, 25, 50, 100, 250, 500, 1000, 2000
        #1, 10, 20, 40

        # Lists to store results
        seq_times = []
        par_times = []

        # ==========================================
        # 2. THE AUTOMATED LOOP
        # ==========================================
        for n in batch_sizes:
            print(f"\n--- Benchmarking {n} images ---")
            
            # We use a trick: we can't easily slice a zip file generator, 
            # so we create a temporary wrapper to limit the number of images.
            # (If your process_images_parallel takes a list of images, this is easier).
            # Assuming your function can take a generator, we use itertools.islice:
            
            # 1. Sequential Run (workers=1)
            t0 = time.perf_counter()
            # Note: For this to work, your process_images_parallel must accept a custom generator.
            # If it doesn't, you can temporarily create a zip with just N images.
            process_images_parallel(
                src="sample_images_2000.zip", 
                dst_zip="comparison_sequential_sample_images_2000.zip", 
                make_pipeline_fn=setup_pipeline, 
                icons=ICONS, 
                workers=1, 
                limit=n 
            )
            seq_time = time.perf_counter() - t0
            seq_times.append(seq_time)
            print(f"Sequential: {seq_time:.2f}s")
            
            # 2. Parallel Run (workers=12)
            t0 = time.perf_counter()
            process_images_parallel(
                src="sample_images_2000.zip", 
                dst_zip="comparison_parallel_sample_images_2000.zip", 
                make_pipeline_fn=setup_pipeline, 
                icons=ICONS, 
                workers=12,
                limit=n # Same limit here
            )
            par_time = time.perf_counter() - t0
            par_times.append(par_time)
            print(f"Parallel:   {par_time:.2f}s")
            print(f"Speedup:    {seq_time/par_time:.2f}x")

        # ==========================================
        # 3. PLOT THE REAL DATA
        # ==========================================
        n_images = np.array(batch_sizes)
        seq_times = np.array(seq_times)
        par_times = np.array(par_times)
        speedup = seq_times / par_times
        ideal_speedup = np.full(len(n_images), 12.0)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 10))

        # Top Chart
        ax1.plot(n_images, seq_times, color='#D9534F', marker='o', linewidth=2.5, label='Sequential (1 Worker)')
        ax1.plot(n_images, par_times, color='#5CB85C', marker='o', linewidth=2.5, label='Parallel (12 Workers)')
        ax1.set_title('Execution Time across Different Batch Sizes', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Clock Time (Seconds)')
        ax1.set_xlabel('Batch Size (Number of Images)')
        ax1.grid(True, linestyle='--', alpha=0.6)
        ax1.legend()
        ax1.spines[['top', 'right']].set_visible(False)

        # Bottom Chart
        ax2.plot(n_images, speedup, color='#0275D8', marker='o', linewidth=2.5, label='Actual Speedup')
        #ax2.plot(n_images, ideal_speedup, color='gray', linestyle='--', linewidth=2, label='Ideal Speedup (12x)')
        ax2.set_title('Parallelization Speedup across Different Batch Sizes', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Speedup Ratio (Sequential / Parallel)')
        ax2.set_xlabel('Batch Size (Number of Images)')
        ax2.set_ylim(0, 14)
        ax2.grid(True, linestyle='--', alpha=0.6)
        ax2.legend()
        ax2.spines[['top', 'right']].set_visible(False)

        plt.tight_layout(pad=3.0)
        plt.savefig("real_scaling_benchmark.png", dpi=300, bbox_inches="tight")
        #plt.show()

    resolution_graph = False
    if resolution_graph:
        import matplotlib.pyplot as plt
        import numpy as np

        erros, stats= process_images_parallel("sample_images_2000.zip", "resolution_folder_parallel_computing_result.zip", make_pipeline_fn=setup_pipeline, icons=icons, pipeline_kwargs={}
                                              ,workers = 12, limit = 200)
        resolutions = stats["resolutions"]
        times = stats["processing_times"]

        fig, ax = plt.subplots(figsize=(9, 6))

        # 1. Plot the Scatter Points
        ax.scatter(resolutions, times, color='#0275D8', s=60, edgecolor='black', zorder=3, label='Sample Images')

        # 2. (Optional but highly recommended) Add a Trendline
        # This mathematically proves the linear relationship
        z = np.polyfit(resolutions, times, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(resolutions), max(resolutions), 100)
        ax.plot(x_trend, p(x_trend), color='#D9534F', linestyle='--', linewidth=2, label='Linear Trendline', zorder=2)

        # 3. Formatting
        ax.set_title('Impact of Image Resolution on Mosaic Processing Time', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Image Resolution (Megapixels)', fontsize=12)
        ax.set_ylabel('Processing Time (Seconds)', fontsize=12)

        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(fontsize=11)
        ax.spines[['top', 'right']].set_visible(False)

        plt.tight_layout()
        plt.savefig("Resolution_vs_time.png", dpi=300)
        #plt.show()

    full_graph = True
    if full_graph:

        errors, stats = process_images_parallel(
            src="sample_images_2000.zip", 
            dst_zip="full_graph_2000_images_result.zip",
            make_pipeline_fn=setup_pipeline,
            icons=icons,
            workers=12,
            limit=2000,              
            checkpoint_interval=100  # Record a data point every N images
        )

        # 2. Extract data for plotting
        progress = stats["progress_data"]
        images = [p["images"] for p in progress]
        seq_times = [p["approx_seq_time"] for p in progress]
        par_times = [p["actual_par_time"] for p in progress]

        # 3. Calculate speedup
        speedups = [s / p for s, p in zip(seq_times, par_times)]

        # 4. Create the plots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

        # Top Chart: Execution Time
        ax1.plot(images, seq_times, color='#D9534F', marker='o', linewidth=2.5, label='Sequential (Approximation)')
        ax1.plot(images, par_times, color='#5CB85C', marker='o', linewidth=2.5, label='Multiprocessing (12 Workers)')
        ax1.set_title('Processing Time across Cumulative Number of Images', fontsize=14, fontweight='bold', pad=15)
        ax1.set_ylabel('Clock Time (Seconds)', fontsize=12)
        ax1.set_xlabel('Number of Images Processed', fontsize=11)
        ax1.grid(True, linestyle='--', alpha=0.6)
        ax1.legend(fontsize=11, loc='upper left')
        ax1.spines[['top', 'right']].set_visible(False)

        # Bottom Chart: Speedup
        ideal_speedup = [12] * len(images)
        ax2.plot(images, speedups, color='#0275D8', marker='o', linewidth=2.5, label='Actual Speedup')
        ax2.plot(images, ideal_speedup, color='gray', linestyle='--', linewidth=2, label='Ideal Speedup (12x)')
        ax2.set_title('Parallelization Speedup across Cumulative Number of Images', fontsize=14, fontweight='bold', pad=15)
        ax2.set_ylabel('Speedup Ratio (Sequential / Parallel)', fontsize=12)
        ax2.set_xlabel('Number of Images Processed', fontsize=11)
        ax2.set_ylim(0, 14) 
        ax2.grid(True, linestyle='--', alpha=0.6)
        ax2.legend(fontsize=11, loc='lower right')
        ax2.spines[['top', 'right']].set_visible(False)

        plt.tight_layout(pad=3.0)
        plt.savefig("scaling_benchmark_2000.png", dpi=300)
        plt.show()





















    
























