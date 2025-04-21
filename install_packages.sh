#!/bin/bash
# This script reads package names line by line from requirements.txt
# and attempts to install each package using pip.
# It skips empty lines and lines starting with '#'.

while read requirement; do
    if [[ $requirement != \#* && -n $requirement ]]; then
        echo "Attempting to install '$requirement' using pip..."
        pip install "$requirement"
        if [ $? -ne 0 ]; then
            echo "Failed to install '$requirement' using pip."
            # Optionally add error handling here, like exiting the script
            # exit 1 
        fi
    fi
done < requirements.txt

echo "Finished processing requirements."