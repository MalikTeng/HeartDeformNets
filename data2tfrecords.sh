#!/bin/bash

# Disable VTK parallel I/O to avoid dependency issues
export VTK_USE_PARALLEL=0

# Prompt user for input
read -p "Enter the path to the input folder: " folder
read -p "Enter the modality (e.g., ct, mr): " modality

# Automatically define the output folder
input_basename=$(basename "$folder")
parent_dir=$(dirname "$folder")

if [[ "$input_basename" == *"_augmented" ]]; then
    out_folder="${parent_dir}/tfrecords_augmented"
else
    out_folder="${parent_dir}/tfrecords"
fi

echo "Output folder set to: $out_folder"

# Run Python script once with all postfixes as arguments
python data/data2tfrecords.py \
    --folder "$folder" \
    --modality "$modality" \
    --size 128 128 128 \
    --folder_postfixes "_train" "_val" "_test" \
    --deci_rate 0 \
    --smooth_ite 50 \
    --out_folder "$out_folder" \
    --seg_id 1