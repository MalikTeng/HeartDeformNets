nvcc = /global/software/sl-7.x86_64/modules/langs/cuda/10.0/bin/nvcc
cudalib =/global/software/sl-7.x86_64/modules/langs/cuda/10.0/lib64
tensorflow = /home/yd21/miniconda3/envs/deformnet/lib/python3.6/site-packages/tensorflow_core/include
TF_LIB= /home/yd21/miniconda3/envs/deformnet/lib/python3.6/site-packages/tensorflow_core/
all: tf_nndistance_so.so tf_nndistance_g.cu.o 

tf_nndistance_so.so: tf_nndistance_g.cu.o tf_nndistance.cpp
	g++ -std=c++11 tf_nndistance.cpp tf_nndistance_g.cu.o -o tf_nndistance_so.so -shared -fPIC -I $(tensorflow) -lcudart -L $(cudalib) -O2 -L $(TF_LIB) -ltensorflow_framework -D_GLIBCXX_USE_CXX11_ABI=0

tf_nndistance_g.cu.o: tf_nndistance_g.cu
	$(nvcc) -D_GLIBCXX_USE_CXX11_ABI=0 -std=c++11 -c -o tf_nndistance_g.cu.o tf_nndistance_g.cu -I $(tensorflow) -DGOOGLE_CUDA=1 -x cu -Xcompiler -fPIC -O2

# clean:
# 	rm tf_nndistance_so.so
# 	rm  *.cu.o 
