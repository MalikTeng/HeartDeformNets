import os
import nibabel as nib
import numpy as np

# Define the path to the input file
input_file = '/home/yd21/Documents/HeartDeformNets/templates/segmentation/mmwhs.nii.gz'

# Load the segmentation mask volume
mask_volume = nib.load(input_file)
mask_data = mask_volume.get_fdata()

# Create a binary mask where all pixels not equal to 2 are set to 0
binary_mask = np.where(mask_data == 1, 1, 0)

# Save the new mask volume to the same directory with a different filename
output_file = os.path.join(os.path.dirname(input_file), 'mmwhs_binary.nii.gz')
binary_mask_volume = nib.Nifti1Image(binary_mask, mask_volume.affine)
nib.save(binary_mask_volume, output_file)