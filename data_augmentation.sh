#!/bin/bash

# Prompt user for input
read -p "Enter modality (e.g., mr): " MODAL
read -p "Enter number of augmentations: " NUM
read -p "Enter image directory: " IMGDIR

# Automatically set segmentation directory
SEGDIR="${IMGDIR%/}_seg"

# Automatically set output directory
OUTDIR=$(dirname $(dirname "$IMGDIR"))/nii_augmented

# Determine mode based on directory name
if [[ "$IMGDIR" == *"_train"* ]]; then
    MODE="train"
else
    MODE="val"
fi

# Print the directories for user confirmation
echo "Image directory: $IMGDIR"
echo "Segmentation directory: $SEGDIR"
echo "Output directory: $OUTDIR"
echo "Mode: $MODE"

# Run the Python script with user-provided and derived variables
mpirun -n 4 python data/data_augmentation.py \
    --im_dir "$IMGDIR" \
    --seg_dir "$SEGDIR" \
    --out_dir "$OUTDIR" \
    --modality "$MODAL" \
    --mode "$MODE" \
    --num "$NUM"