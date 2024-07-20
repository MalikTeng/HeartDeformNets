# HeartDeformNets

This repository forks from the [fkong/HeartDeformNet](https://github.com/fkong7/HeartDeformNets.git) that used for their paper:

Fanwei Kong, Shawn Shadden, Learning Whole Heart Mesh Generation From Patient Images For Computational Simulations (2022)

<img width="1961" alt="network2" src="https://user-images.githubusercontent.com/31931939/184846001-eb3b9442-ae46-4152-a3dc-791e1ccdf946.png">


## Installation

To download the source code with submodules, please run 
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
If the tensorflow-gpu version cannot be installed, try terminate the above shell script and run the following command:
```
pip install tensorflow-gpu==1.15.0
```

## Template Meshes

_Due to vtk version compatibility issues, the `create_template.sh` file the author provided cannot produce compatible vtp files in an end to end manner, and test passed if only one surface mesh is needed._

To generate a template mesh (left ventricle myocardium) from `templates/segmentation/mmwhs_binary.nii.gz`, which is a binary segmentation mask of a randomly selected MMWHS dataset case, follow the steps below:
- Compile the C++ code for computing biharmonc coordinates in `templates/bc` by 
    ```
    cd templates/bc
    mkdir build
    cd build
    cmake ..
    make
    ```
- Change the `output_dir` as the path to store the template mesh and `seg_fn` as the path to the binary segmentation mask in `create_template.sh`.
- Run the following command to generate the template mesh (by default `templates/meshes/template.vtp`), type in or paste a) the path to store the template mesh, b) the path to the binary segmentation mask.
    ```
    ./create_template.sh
    ```
- Take a note of the last two lines of the output, which are `ctrl_fn` and `weight_fn` that will be used later.
- Locate the output template mesh from the previous step in the `output_dir`, overwrite it with another software or packages -- I used __ParaView__ to load it, save it with __selecting "RegionID" data and save it in ASCII__, and overwrite the file.
- Run the following command to generate the dat data, type in path as required.
    ```
    chmod +x create_dat.sh
    ./create_dat.sh
    ```
- Check the output vtp file with __the filename of current date and time__ in the `output_dir`, and do the same as what been done with the template mesh in previous steps.

## Training

### Data Preparation

The data preparation code is a copy from the author's [MeshDeformNet](https://github.com/fkong7/MeshDeformNet.git) repository. 

Ensure you have a directory structure as follows (e.g. for __MMWHS__ dataset):
```
|-- MMWHS
    |-- nii
        |-- ct_train        # image nii.gz files
        |-- ct_train_seg    # label nii.gz files
        |-- ct_val
        |-- ct_val_seg
        |-- mr_train
        |-- mr_train_seg
        |-- mr_val
        |-- mr_val_seg
```
_I have all image and label foreground cropped, resized, and padded to 128x128x128. Not sure what will happen if not doing so._

The data preparation steps are as follows:
- If data augmentation is prefered, you need the __mpi4py__ (Python bindings for MPI) installed, which I will showcase how to install it on a Linux machine.
    - Install MPI implementation:
    ```
    sudo apt update
    sudo apt install libopenmpi-dev
    ```
    - Install mpi4py (if you are in the `deformnet` environment):
    ```
    pip install mpi4py
    ```
- Run data augmentation by the following command (I did this by running on local machine, but if you are doing this with ssh on a remote machine, you need to install __X11__ and __xauth__):
    ```
    mpirun -n 4 python data/data_augmentation.py \
        --im_dir /path/to/MMWHS/nii/ct_train \
        --seg_dir /path/to/MMWHS/nii/ct_train_seg \
        --out_dir /path/to/MMWHS/nii_augmented \
        --modality ct \ # ct or mr
        --mode train \  # train or val
        --num 10        # number of augmentated copies per image, 10 for ct and 20 for mr
    ```

    where I used `-n 4` instead of `-n 20` as the author suggested in __MeshDeformNet__ because of not enough resources on my local machine.
- Do the same to `val` data same as above as you like. The above command will produce a new folder `nii_augmented` in the `MMWHS` directory.
- Preprocess data by applying intensity normalisation and resizing, results will be saved as tfrecords files in a new folder `tfresults` in the `MMWHS` directory.
    ```
    python data/data2tfrecords.py \
        --folder /path/to/MMWHS/nii \
        --modality ct \             # ct or mr
        --size 128 128 128 \        # image dimension for training
        --folder_postfix _train \   # _train or _val, i.e. will process the images/segmentation in ct_train and ct_train_seg
        --deci_rate 0  \            # decimation rate on ground truth surface meshes
        --smooth_ite 50 \           # Laplacian smoothing on ground truth surface meshes
        --out_folder /path/to/MMWHS/tfrecords \
        --seg_id 1                  # segmentation ids, 1-7 for seven cardiac structures
    ```
- Do the same to augmented data in `nii_augmented` folder as above, if you are using data augmentation.

### Compile nndistance Loss

If not already seen a `tf_nndistance_so.so` file in the `external/`, which is a required Python module compiled in C++ for training the network. To compile the module, run the following command:
```
cd external/
make
cd ..
```

### Training

_You may create a training YAML file following the author's provided examples in the `config` folder. This config uses a myocardium template mesh, a correct template mesh is required._

After the previous steps of data preprocessing, generating template mesh and dat files, you should change the pathnames in the `config/task1_mmwhs.yaml` file, and may run the following command to train the network:
```
python train.py --config config/task1_mmwhs.yaml
```

## Evaluation


After changing the pathnames in the `config/task1_mmwhs.yaml` file, you may run the following command to evaluate the network: 
```
python predict.py --config config/task2_wh.yaml
```
