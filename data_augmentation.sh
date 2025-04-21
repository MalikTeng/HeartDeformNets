#!/bin/bash

# Disable VTK parallel I/O to avoid dependency issues
export VTK_USE_PARALLEL=0

# Function to get input and confirm directories
get_and_confirm_directories() {
    # Prompt user for input
    read -p "Enter the base directory (e.g., /mnt/data/Experiment/Data/DeformNet_Data/SCOTHEART/nii/): " BASE_DIR
    
    # Ensure BASE_DIR ends with a slash
    [[ "${BASE_DIR}" != */ ]] && BASE_DIR="${BASE_DIR}/"
    
    # Check if the directory exists
    if [ ! -d "${BASE_DIR}" ]; then
        echo "Error: Directory does not exist."
        return 1
    fi
    
    echo "Directories found:"
    local found_valid_dir=false
    
    # List all matching directories
    for DIR in ${BASE_DIR}*_*/; do
        FOLDER_NAME=$(basename "${DIR}")
        
        # Skip folders that end with _seg
        if [[ "${FOLDER_NAME}" == *"_seg" ]]; then
            continue
        fi
        
        # Extract MODAL and MODE
        MODAL=$(echo "${FOLDER_NAME}" | cut -d'_' -f1)
        MODE=$(echo "${FOLDER_NAME}" | cut -d'_' -f2)
        
        # Check if it matches our criteria
        if [[ "${MODAL}" == "ct" || "${MODAL}" == "mr" ]] && [[ "${MODE}" == "train" || "${MODE}" == "test" || "${MODE}" == "val" ]]; then
            echo "  - ${FOLDER_NAME} (will be processed)"
            found_valid_dir=true
        else
            echo "  - ${FOLDER_NAME} (will be skipped)"
        fi
    done
    
    if [ "$found_valid_dir" = false ]; then
        echo "No valid directories found matching the pattern <ct/mr>_<train/test/val>."
        return 1
    fi
    
    # Ask for confirmation
    read -p "Are these the correct directories? (y/n): " CONFIRM
    if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
        return 1
    fi
    
    return 0
}

# Get and confirm directories
while true; do
    if get_and_confirm_directories; then
        break
    else
        echo "Let's try again."
    fi
done

read -p "Enter number of augmentations: " NUM

# Automatically set output directory
OUTDIR=$(dirname "${BASE_DIR}")/nii_augmented

# Create output directory if it doesn't exist
mkdir -p "${OUTDIR}"

echo "Base directory: ${BASE_DIR}"
echo "Output directory: ${OUTDIR}"
echo "Number of augmentations: ${NUM}"
echo "Starting augmentation process..."

# Get all folders that match the pattern <MODAL_MODE>
for DIR in ${BASE_DIR}*_*/; do
    # Extract MODAL and MODE from directory name
    FOLDER_NAME=$(basename "${DIR}")
    
    # Skip folders that end with _seg
    if [[ "${FOLDER_NAME}" == *"_seg" ]]; then
        continue
    fi
    
    # Extract MODAL and MODE
    MODAL=$(echo "${FOLDER_NAME}" | cut -d'_' -f1)
    MODE=$(echo "${FOLDER_NAME}" | cut -d'_' -f2)
    
    # Skip if MODAL is not ct or mr
    if [[ "${MODAL}" != "ct" && "${MODAL}" != "mr" ]]; then
        echo "Skipping ${FOLDER_NAME} (unknown modality)"
        continue
    fi
    
    # Skip if MODE is not train, test, or val
    if [[ "${MODE}" != "train" && "${MODE}" != "test" && "${MODE}" != "val" ]]; then
        echo "Skipping ${FOLDER_NAME} (unknown mode)"
        continue
    fi
    
    # Set the image and segmentation directories
    IMGDIR="${DIR%/}"
    SEGDIR="${IMGDIR}_seg"
    
    echo "Processing: ${FOLDER_NAME}"
    echo "  Image directory: ${IMGDIR}"
    echo "  Segmentation directory: ${SEGDIR}"
    echo "  Mode: ${MODE}"
    
    # Run the Python script for this folder
    mpirun -n 4 python data/data_augmentation.py \
        --im_dir "${IMGDIR}" \
        --seg_dir "${SEGDIR}" \
        --out_dir "${OUTDIR}" \
        --modality "${MODAL}" \
        --mode "${MODE}" \
        --num "${NUM}"
    
    echo "Completed processing ${FOLDER_NAME}"
    echo "----------------------------------------"
done

echo "All augmentations completed!"