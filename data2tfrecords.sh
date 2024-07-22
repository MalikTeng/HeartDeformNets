#!/bin/bash

# Prompt user for input
read -p "Enter the path to the input folder: " folder
read -p "Enter the modality (e.g., ct, mr): " modality
read -p "Enter the postfix for the output folder (e.g., train, val, or test): " folder_postfix

# Automatically define the output folder
input_basename=$(basename "$folder")
parent_dir=$(dirname "$folder")

if [[ "$input_basename" == *"_augmented" ]]; then
    out_folder="${parent_dir}/tfrecords_augmented"
else
    out_folder="${parent_dir}/tfrecords"
fi

echo "Output folder set to: $out_folder"

# Run the Python script with user-provided inputs and auto-generated output folder
python data/data2tfrecords.py \
    --folder "$folder" \
    --modality "$modality" \
    --size 128 128 128 \
    --folder_postfix "_$folder_postfix" \
    --deci_rate 0 \
    --smooth_ite 50 \
    --out_folder "$out_folder" \
    --seg_id 1