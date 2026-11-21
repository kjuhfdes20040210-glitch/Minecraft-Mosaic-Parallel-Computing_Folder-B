from IOzip import process_images
from orchestrator import setup_pipeline
from Python_multiprocessing import process_images_parallel
from dataprep import load_all_as_rgba, print_report, check_photos
from timer import timer
from pasting import paste_icons_onto_plane
from colorgrading import make_contact_sheet, make_hue_strip, make_graded_sheet
from pathlib import Path

# Flags for controlling what runs
information = False
graph_comparison = False
run_sequential = False
run_parallel = True
run_full_2000 = False 

if __name__ == "__main__":  

    # Get the directory where main.py is located
    BASE_DIR = Path(__file__).parent.resolve()

    # 1. Load the icons
    ICON_PATH = BASE_DIR / "minecraft_textures"
    icons = load_all_as_rgba(ICON_PATH)

    # 2. Data Prep & Information (Optional)
    if information:
        results = check_photos(str(ICON_PATH))
        
        with timer("Color grading"):
            make_contact_sheet(icons)
            make_hue_strip(icons, out="hue_strip.png")
            groups = make_graded_sheet(icons, out="graded_sheet.png")
        print()

        with timer("Data prep"):
            print_report(check_photos(str(ICON_PATH)))
        print()

        with timer("Pasting"):
            cropped, blank, info = paste_icons_onto_plane(icons, icon_size=16, seed=42)
        print(info)
        print()
        cropped.save("plane_cropped.png")
        blank.save("plane_blank.png")

    if run_sequential:
        sequential_pipeline = setup_pipeline(icons) 
        
        # Uses the sample folder or zip in the root directory
        input_data = BASE_DIR / "sample_images_24" 
        output_zip = BASE_DIR / "sequential_computing_result.zip"
        
        print("Running Sequential Pipeline...")
        process_images(input_data, output_zip, process_fn=sequential_pipeline)

    if run_parallel:
        input_data = BASE_DIR / "sample_images_24"
        output_zip = BASE_DIR / "sample_images_24_parallel_result.zip"
        
        process_images_parallel(
            src=input_data, 
            dst_zip=output_zip, 
            make_pipeline_fn=setup_pipeline, 
            icons=icons, 
            pipeline_kwargs={}, 
            workers=12
        )

    # Run Parallel Pipeline (Full 2000 images)
    # Only runs if the 2000 zip file exists in the directory and the flag is True
    if run_full_2000:
        input_data = BASE_DIR / "sample_images_2000.zip"
        output_zip = BASE_DIR / "full_graph_2000_images_result.zip"
        
        if input_data.exists():

            process_images_parallel(
                src=input_data, 
                dst_zip=output_zip, 
                make_pipeline_fn=setup_pipeline, 
                icons=icons, 
                pipeline_kwargs={}, 
                workers=12,
                limit=2000
            )
        else:
            print(f"Error: Could not find {input_data}. Please download the dataset and place it here.")