read -p "Enter the output directory: " output_dir
# read -p "Enter the ctrl_fns: " ctrl_pt_arr
# read -p "Enter the weight_fns: " weight_arr

ctrl_pt_arr=$(cat "$output_dir/ctrl_fns.txt")
weight_arr=$(cat "$output_dir/weight_fns.txt")

num_mesh=1

echo "Using control points: $ctrl_pt_arr"
echo "Using weights: $weight_arr"

python make_mesh_info_dat.py \
    --tmplt_fn $output_dir/template.vtp \
    --sample_fn $output_dir/template.vtp \
    --weight_fns $weight_arr \
    --ctrl_fns $ctrl_pt_arr \
    --out_dir $output_dir \
    --num_mesh $num_mesh

# Clean up temporary files
rm "$output_dir/ctrl_fns.txt"
rm "$output_dir/weight_fns.txt"
echo "Cleaned up temporary files."