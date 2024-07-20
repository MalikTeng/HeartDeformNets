while read requirement; do
    if [[ $requirement != \#* ]]; then
        package_name=$(echo $requirement | sed 's/[<>=].*//')
        conda install --yes "$package_name" || pip install "$package_name"
    fi
done < requirements.txt