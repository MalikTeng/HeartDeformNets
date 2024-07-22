# HeartDeformNets

This repository forks from the [fkong/HeartDeformNet](https://github.com/fkong7/HeartDeformNets.git) used for their paper:

Fanwei Kong, Shawn Shadden, Learning Whole Heart Mesh Generation From Patient Images For Computational Simulations (2022)

<img width="1961" alt="network2" src="https://user-images.githubusercontent.com/31931939/184846001-eb3b9442-ae46-4152-a3dc-791e1ccdf946.png">

## Installation

To download the source code with submodules, please run:
```
git clone --recurse-submodules https://github.com/MalikTeng/HeartDeformNets.git
```
To prepare the environment for this implementation, follow the steps below:
```
cd HeartDeformNets
conda create -n deformnet python\<3.7
conda activate deformnet
chmod +x install_packages.sh
./install_packages.sh
```
If the tensorflow-gpu version cannot be installed, try terminating the above shell script and run the following command:
```
pip install tensorflow-gpu==1.15.0
```

## Template Meshes

_Due to VTK version compatibility issues, the `create_template.sh` file provided by the author cannot produce compatible VTP files in an end-to-end manner, and tests passed only if one surface mesh is needed._

To generate a template mesh (left ventricle myocardium) from `templates/segmentation/mmwhs_binary.nii.gz`, which is a binary segmentation mask of a randomly selected MMWHS dataset case, follow the steps below:
- Compile the C++ code for computing biharmonic coordinates in `templates/bc` by:
    ```
    cd templates/bc
    mkdir build
    cd build
    cmake ..
    make
    ```
- Change the `output_dir` to the path to store the template mesh and `seg_fn` to the path of the binary segmentation mask in `create_template.sh`.
- Run the following command to generate the template mesh (by default `templates/meshes/template.vtp`). Type in or paste a) the path to store the template mesh, and b) the path to the binary segmentation mask.
    ```
    ./create_template.sh
    ```
- Take note of the last two lines of the script output, which are `ctrl_fn` and `weight_fn` that will be used later.
- Locate the output template mesh from the previous step in the `output_dir`, overwrite it with another software or package. I used __ParaView__ to load it, save it with __selecting "RegionID" data and save it in ASCII__, and overwrite the file.
- Run the following command to generate the dat data, typing in the path as required.
    ```
    chmod +x create_dat.sh
    ./create_dat.sh
    ```
- Check the output VTP file with __the filename of the current date and time__ in the `output_dir`, and do the same as what was done with the template mesh in the previous steps.

## Training

### Data Preparation

The data preparation code is copied from the author's [MeshDeformNet](https://github.com/fkong7/MeshDeformNet.git) repository.

Ensure you have a directory structure as follows (e.g., for the __MMWHS__ dataset):
```
|-- MMWHS
    |-- nii
        |-- ct_train
            |-- 01.nii.gz
            |-- 02.nii.gz
            |-- ...
        |-- ct_train_seg
            |-- 01.nii.gz
            |-- 02.nii.gz
            |-- ...
        |-- ct_val
        |-- ct_val_seg
        |-- mr_train
        |-- mr_train_seg
        |-- mr_val
        |-- mr_val_seg
```
_I have all images and labels foreground cropped, resized, and padded to 128x128x128. Not sure what will happen if not doing so._

The data preparation steps are as follows:
- If data augmentation is preferred, you need the __mpi4py__ (Python bindings for MPI) installed. Here is how to install it on a Linux machine.
    - Install MPI implementation:
        ```
        sudo apt update
        sudo apt install libopenmpi-dev
        ```
    - Install mpi4py (if you are in the `deformnet` environment):
        ```
        pip install mpi4py
        ```
- Run data augmentation with the following command (I did this by running on a local machine, but if you are doing this with SSH on a remote machine, you need to install __X11__ and __xauth__):
    ```
    mpirun -n 4 python data/data_augmentation.py \
        --im_dir /path/to/MMWHS/nii/ct_train \
        --seg_dir /path/to/MMWHS/nii/ct_train_seg \
        --out_dir /path/to/MMWHS/nii_augmented \
        --modality ct \ # ct or mr
        --mode train \  # train or val
        --num 10        # number of augmented copies per image, 10 for ct and 20 for mr
    ```

    Note: I used `-n 4` instead of `-n 20` as the author suggested in __MeshDeformNet__ due to limited resources on my local machine.
- Do the same for `val` data if needed. The above command will produce a new folder `nii_augmented` in the `MMWHS` directory.
- Preprocess data by applying intensity normalization and resizing. Results will be saved as TFRecords files in a new folder `tfrecords` in the `MMWHS` directory.
    ```
    python data/data2tfrecords.py \
        --folder /path/to/MMWHS/nii \
        --modality ct \              # ct or mr
        --size 128 128 128 \         # image dimensions for training
        --folder_postfix _train \    # _train or _val, i.e. will process the images/segmentation in ct_train and ct_train_seg
        --deci_rate 0  \             # decimation rate on ground truth surface meshes
        --smooth_ite 50 \            # Laplacian smoothing on ground truth surface meshes
        --out_folder /path/to/MMWHS/tfrecords \
        --seg_id 1                   # segmentation ids, 1-7 for seven cardiac structures
    ```
- Do the same for augmented data in the `nii_augmented` folder as above, if you are using data augmentation.

### Compile nndistance Loss

If you do not see a `tf_nndistance_so.so` file in the `external/` directory, which is a required Python module compiled in C++ for training the network, compile the module by running the following command:
```
cd external/
make
cd ..
```

### Training

_You may create a training YAML file following the examples provided by the author in the `config` folder. This config uses a myocardium template mesh, so a correct template mesh is required._

After the previous steps of data preprocessing, generating a template mesh and data files, you should change the pathnames in the `config/task1_mmwhs.yaml` file. Then run the following command to train the network:
```
python train.py --config config/task1_mmwhs.yaml
```

## Evaluation

After changing the pathnames in the `config/task1_mmwhs.yaml` file, you may run the following command to evaluate the network:
```
python predict.py --config config/task2_wh.yaml
```
