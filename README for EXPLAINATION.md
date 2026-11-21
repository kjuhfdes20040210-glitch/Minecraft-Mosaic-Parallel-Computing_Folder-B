This file is for explaining different .py files content.

main.py: main file for putting both Minecraft texture files and photo files.

timer.py: the code calculates time spent for converting each photo and also the whole process.

dataprep.py: the code checks the integrity of the photos and convert it all into RGBA formats. ALthough it mainly uses the convert RGBA function.

IOzip.py: handles the problem of reading photos one by one in a zip folder or non-zipped folder, and writes the result in PNG format to the zip folder output.

colorgrading.py: it process the Minecraft-texture icons and any image into a graded group or value, for matching processes later. it also involves 2 graphs making to show that a.) the Minecraft-texture icons cover generally the full color spectrum and b.) paste all the Minecraft-textures onto 1 single graph to showcase all the possible icons for reference.

make_mosaic.py: main part for mosaic conversion, covering cropping of target image, HSV values calculation into groups and values, matching color with Minecraft-textures icons, and assemble the whole mosaic picture, and returns the result.

Python_multiprocessing.py: dedicated for parallelization of the workflow, aims to reduce total time when the input consists of thousands of images to be converted. It allows parallel processing of images by prociding multiple workers based on available CPU cores on the pc. For example, with 3 workers and 3 images: sequential time = T1 + T2 + T3. parallel time = max {T1, T2, T3}. This equation does not hold anymore when number of photos exceed total workers available, in which the worker takes on another image after processing one.

orchestrator.py: setup_pipeline is for worker in parallel processing, sequential_pipeline is the main loop. The flags for colorgrading and pasting are False, you can turn them on to see the a.) the Minecraft-texture icons cover generally the full color spectrum and b.) paste all the Minecraft-textures onto 1 single graph to showcase all the possible icons for reference.

Graph_making.py: responsible for makng visualizations for data analysis for presentation and report.

pasting.py: responsible for pasting the selected Minecraft-texture icon onto the substituting tile.

This aims to allow understanding and also tuning for your own use.

