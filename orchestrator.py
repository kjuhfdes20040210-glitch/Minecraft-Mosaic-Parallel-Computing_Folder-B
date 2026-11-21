from dataprep import check_photos, print_report, load_all_as_rgba
from colorgrading import make_contact_sheet, make_hue_strip, make_graded_sheet
from pasting import paste_icons_onto_plane
from make_mosaic import make_mosaic
from timer import timer


def setup_pipeline(icons):

    # This is set up to satisfy the structure for the parallel processing
    def sequential_pipeline(img): 

        # for your reference, turn True to the color grading and pasting functions to see the outputs of minecraft textures, but they are not needed for the mosaic generation
        # those shouldn't be in a loop anyway, but I don't care to move them out
  
        colorgrading_flag = False
        pasting_flag = False
        make_mosaic_flag = True
        
        if colorgrading_flag:
            with timer("Color grading"):
                make_contact_sheet(icons, out="graded_sheet.png")
                make_hue_strip(icons, out="hue_strip.png")
            print()

        if pasting_flag: # this is only a test of pasting icons onto a random plane, not the mosaic
            with timer("Pasting"):
                cropped, blank, info = paste_icons_onto_plane(icons, icon_size=16, seed=42)
            print(info)
            print()
            cropped.save("plane_cropped.png")
            blank.save("plane_blank.png")

        if make_mosaic_flag:
            with timer("Mosaic generation"):
                mosaic = make_mosaic( #mosaic, matches, labels, tiers
                    img,
                    icons,
                    tile_size=8,        
                out_path="mosaic.png",
                tiebreak_k=3,        # pick randomly among n closest per bucket → more variety
                seed=42,             # reproducible
            )
            return mosaic
        
    return sequential_pipeline

    