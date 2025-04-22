#!/bin/bash
# This script automates the creation/recreation of the 'deformnet' conda environment
# and installs required packages: VTK via conda, others via pip.

ENV_NAME="deformnet"
PYTHON_VERSION="3.9"
REQ_FILE="requirements.txt"

# Check if the environment exists and remove it
if conda info --envs | grep -E "^${ENV_NAME}\s+" > /dev/null; then
    echo "Environment '${ENV_NAME}' already exists. Removing it..."
    conda env remove -n ${ENV_NAME} --yes
    if [ $? -ne 0 ]; then
        echo "Failed to remove existing environment '${ENV_NAME}'. Exiting."
        exit 1
    fi
fi

# Create the environment
echo "Creating conda environment '${ENV_NAME}' with Python ${PYTHON_VERSION}..."
conda create -n ${ENV_NAME} python=${PYTHON_VERSION} --yes
if [ $? -ne 0 ]; then
    echo "Failed to create environment '${ENV_NAME}'. Exiting."
    exit 1
fi

# Install VTK using conda into the specific environment
echo "Attempting to install vtk into '${ENV_NAME}' using conda..."
conda install -n ${ENV_NAME} vtk -c conda-forge --yes
if [ $? -ne 0 ]; then
    echo "Failed to install vtk using conda into '${ENV_NAME}'. Exiting."
    exit 1
fi

# Find the pip executable within the new environment
ENV_PATH=$(conda info --envs | grep -E "^${ENV_NAME}\s+" | awk '{print $NF}')
if [ -z "$ENV_PATH" ]; then
    echo "Could not find path for environment '${ENV_NAME}'. Exiting."
    exit 1
fi
PIP_EXEC="${ENV_PATH}/bin/pip"

if [ ! -f "$PIP_EXEC" ]; then
    echo "Pip executable not found at '${PIP_EXEC}'. Exiting."
    exit 1
fi

# Install remaining requirements using the environment's pip
echo "Processing remaining requirements from '${REQ_FILE}' with environment pip..."
while IFS= read -r requirement || [[ -n "$requirement" ]]; do
    # Skip comments and empty lines
    if [[ $requirement =~ ^\s*# ]] || [[ -z $requirement ]]; then
        continue
    fi

    echo "Attempting to install '$requirement' using ${PIP_EXEC}..."
    ${PIP_EXEC} install "$requirement"
    if [ $? -ne 0 ]; then
        echo "Failed to install '$requirement' using environment pip."
        # Consider adding 'exit 1' here for stricter error handling
    fi
done < "${REQ_FILE}"

echo "Finished processing requirements for environment '${ENV_NAME}'."
echo "To activate the environment, run: conda activate ${ENV_NAME}"