read -p "Enter the output directory: " output_dir
read -p "Enter the ctrl_fns: " ctrl_pt_arr
read -p "Enter the weight_fns: " weight_arr

num_mesh=1

python make_mesh_info_dat.py \
    --tmplt_fn $output_dir/template.vtp \
    --sample_fn $output_dir/template.vtp \
    --weight_fns $weight_arr \
    --ctrl_fns $ctrl_pt_arr \
    --out_dir $output_dir \
    --num_mesh $num_mesh