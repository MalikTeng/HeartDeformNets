nvcc = /usr/local/cuda-11.4/bin/nvcc
cudalib = /usr/local/cuda-11.4/lib64
tensorflow = /mnt/data/Experiment/miniconda3/envs/deformnet/lib/python3.9/site-packages/tensorflow/include
TF_LIB = /mnt/data/Experiment/miniconda3/envs/deformnet/lib/python3.9/site-packages/tensorflow
all: tf_nndistance_so.so tf_nndistance_g.cu.o

tf_nndistance_so.so: tf_nndistance_g.cu.o tf_nndistance.cpp
	g++ -std=c++17 tf_nndistance.cpp tf_nndistance_g.cu.o -o tf_nndistance_so.so -shared -fPIC -I $(tensorflow) -I $(tensorflow)/external/nsync/public -lcudart -L $(cudalib) -O2 $(TF_LIB)/libtensorflow_framework.so.2

tf_nndistance_g.cu.o: tf_nndistance_g.cu
	$(nvcc) -std=c++17 -c -o tf_nndistance_g.cu.o tf_nndistance_g.cu -I $(tensorflow) -DGOOGLE_CUDA=1 -x cu -Xcompiler -fPIC -O2

# clean:
# 	rm tf_nndistance_so.so
# 	rm *.cu.o 
