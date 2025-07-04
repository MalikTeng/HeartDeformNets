import os
import numpy as np
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
sys.path.append(os.path.join(os.path.dirname(__file__), "external"))
import tensorflow as tf
import SimpleITK as sitk 
from pre_process import resample_spacing, RescaleIntensity, swapLabels_ori
from tensorflow.python.keras import backend as K
from model import HeartDeformNet
from data_loader import DataLoader
from utils import construct_feed_dict, natural_sort, write_scores, dice_score
import vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from vtk_utils.vtk_utils import (
    load_vtk_mesh,
    load_image_to_nifty,
    load_vtk_image,
    exportSitk2VTK,
    build_transform_matrix,
    vtk_marching_cube,
    appendPolyData,
    multiclass_convert_polydata_to_imagedata,
    write_vtk_image,
    vtk_write_mask_as_nifty,
    write_vtk_polydata,
    write_numpy_points,
)
import argparse
import pickle
import time
import scipy.sparse as sp
from scipy.spatial.distance import directed_hausdorff
import yaml

# from tensorflow.keras.backend import set_session
# tf.ConfigProto = tf.compat.v1.ConfigProto
# tf.Session = tf.compat.v1.Session

# config = tf.ConfigProto()
# config.gpu_options.allow_growth = True
# session = tf.Session(config=config)
# set_session(session)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = '0' # Set to -1 if CPU should be used CPU = -1 , GPU = 0

gpus = tf.config.experimental.list_physical_devices('GPU')
cpus = tf.config.experimental.list_physical_devices('CPU')

if gpus:
    try:
        # Currently, memory growth needs to be the same across GPUs
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logical_gpus = tf.config.experimental.list_logical_devices('GPU')
        print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
    except RuntimeError as e:
        # Memory growth must be set before GPUs have been initialized
        print(e)
elif cpus:
    try:
        # Currently, memory growth needs to be the same across GPUs
        logical_cpus= tf.config.experimental.list_logical_devices('CPU')
        print(len(cpus), "Physical CPU,", len(logical_cpus), "Logical CPU")
    except RuntimeError as e:
        # Memory growth must be set before GPUs have been initialized
        print(e)

class Prediction:
    #This class use the GCN model to predict mesh from 3D images
    def __init__(self, info, model_name, mesh_tmplt):
        self.heartFFD = HeartDeformNet(**info)
        self.info = info
        self.model = self.heartFFD.build_bc() 
        self.model.summary()
        self.model_name = model_name
        self.model.load_weights(self.model_name)
        self.mesh_tmplt = mesh_tmplt
        self.amplify_factor = info['amplify_factor']
    
    def set_image_info(self, modality, image_fn, size, out_fn, mesh_fn=None, write=False):
        self.modality = modality
        self.image_fn = image_fn
        self.image_vol = load_image_to_nifty(image_fn)
        self.origin = np.array(self.image_vol.GetOrigin())
        self.img_center = np.array(self.image_vol.TransformContinuousIndexToPhysicalPoint(np.array(self.image_vol.GetSize())/2.0))
        self.size = size
        self.out_fn = out_fn
        self.image_vol = resample_spacing(self.image_vol, template_size = size, order=1)[0]
        if write:
            dir_name = os.path.dirname(self.out_fn)
            base_name = os.path.basename(self.out_fn)
            sitk.WriteImage(self.image_vol, os.path.join(dir_name, base_name+'_input_linear.nii.gz'))
        self.img_center2 = np.array(self.image_vol.TransformContinuousIndexToPhysicalPoint(np.array(self.image_vol.GetSize())/2.0))
        self.prediction = None
        self.mesh_fn = mesh_fn

    def mesh_prediction(self):
        BLOCK_NUM = self.info['num_block']
        img_vol = sitk.GetArrayFromImage(self.image_vol).transpose(2,1,0)
        img_vol = RescaleIntensity(img_vol,self.modality, [750, -750])
        self.original_shape = img_vol.shape
        transform = build_transform_matrix(self.image_vol)
        spacing = np.array(self.image_vol.GetSpacing())
        model_inputs = [np.expand_dims(np.expand_dims(img_vol, axis=-1), axis=0)]
        # model_inputs = [np.expand_dims(np.expand_dims(img_vol, axis=-1), axis=0), np.expand_dims(transform, axis=0), np.expand_dims(spacing,axis=0)]
        start = time.time()
        prediction = self.model.predict(model_inputs)
        end = time.time()
        self.pred_time = end-start
        if self.heartFFD.num_seg > 0:
            prediction = prediction[1:]
        # remove control points output
        self.prediction_im = []
        sample_coords = self.info['feed_dict']['sample_coords'].numpy()
        IMAGE_NUM = 0
        
        grid_mesh = []

        prediction_mesh = prediction[BLOCK_NUM+IMAGE_NUM:BLOCK_NUM+IMAGE_NUM+BLOCK_NUM*self.info['num_mesh']]
        num = len(prediction_mesh)//BLOCK_NUM
        self.prediction = []
        for i in range(BLOCK_NUM): # block number 
            mesh_i = vtk.vtkPolyData()
            mesh_i.DeepCopy(self.mesh_tmplt)
            pred_all = np.zeros((1, 0, 3))
            r_id = np.array([])
            for k in range(num):
                pred = prediction_mesh[i*num+k]
                if self.info['train']:
                    pred = pred[:, (self.info['feed_dict']['struct_node_ids'][k+1]-self.info['feed_dict']['struct_node_ids'][k]):, :]
                pred_all = np.concatenate((pred_all, pred), axis=1)
                r_id = np.append(r_id, np.ones(pred.shape[1])*k)
            r_id_vtk = numpy_to_vtk(r_id)
            r_id_vtk.SetName('Ids')
            pred_all = np.squeeze(pred_all)
            # Use the line below for un-scaled prediction
            #pred_all /= np.array([128, 128, 128])
            # Use the 4 lines below for projected prediction onto images
            pred_all = pred_all * np.array(self.size)/np.array([128, 128, 128])
            pred_all = np.concatenate((pred_all,np.ones((pred_all.shape[0],1))), axis=-1)  
            pred_all = np.matmul(transform, pred_all.transpose()).transpose()[:,:3]
            pred_all = pred_all + self.img_center - self.img_center2

            if self.info['train']:
                l = i-1 if i>0 else i
                slice_ids = self.info['feed_dict']['id_ctrl_on_sample'][l].numpy()
                grid_points_i = pred_all[slice_ids, :]
                grid_mesh.append(grid_points_i)
            
            mesh_i.GetPoints().SetData(numpy_to_vtk(pred_all))
            mesh_i.GetPointData().AddArray(r_id_vtk)
            self.prediction.append(mesh_i)
            self.prediction_grid = grid_mesh

       
    def evaluate_dice(self):
        print("Evaluating dice: ", self.image_fn, self.mesh_fn)
        ref_im = sitk.ReadImage(self.mesh_fn)
        ref_im, M = exportSitk2VTK(ref_im)
        ref_im_py = swapLabels_ori(vtk_to_numpy(ref_im.GetPointData().GetScalars()))
        pred_im_py = vtk_to_numpy(self.seg_result.GetPointData().GetScalars())
        dice_values = dice_score(pred_im_py, ref_im_py)
        return dice_values
    
    def evaluate_assd(self):
        def _get_assd(p_surf, g_surf):
            dist_fltr = vtk.vtkDistancePolyDataFilter()
            dist_fltr.SetInputData(1, p_surf)
            dist_fltr.SetInputData(0, g_surf)
            dist_fltr.SignedDistanceOff()
            dist_fltr.Update()
            distance_poly = vtk_to_numpy(dist_fltr.GetOutput().GetPointData().GetArray(0))
            return np.mean(distance_poly), dist_fltr.GetOutput()
        ref_im =  sitk.ReadImage(self.mesh_fn)
        ref_im = resample_spacing(ref_im, template_size=(256 , 256, 256), order=0)[0]
        ref_im, M = exportSitk2VTK(ref_im)
        ref_im_py = swapLabels_ori(vtk_to_numpy(ref_im.GetPointData().GetScalars()))
        ref_im.GetPointData().SetScalars(numpy_to_vtk(ref_im_py))
        
        dir_name = os.path.dirname(self.out_fn)
        base_name = os.path.basename(self.out_fn)
        pred_im = sitk.ReadImage(os.path.join(dir_name, base_name+'.nii.gz'))
        pred_im = resample_spacing(pred_im, template_size=(256,256,256), order=0)[0]
        pred_im, M = exportSitk2VTK(pred_im)
        pred_im_py = swapLabels_ori(vtk_to_numpy(pred_im.GetPointData().GetScalars()))
        pred_im.GetPointData().SetScalars(numpy_to_vtk(pred_im_py))

        ids = np.unique(ref_im_py)
        pred_poly_l = []
        dist_poly_l = []
        ref_poly_l = []
        dist = [0.]*len(ids)
        #evaluate hausdorff 
        haus = [0.]*len(ids)
        for index, i in enumerate(ids):
            if i==0:
                continue
            p_s = vtk_marching_cube(pred_im, 0, i)
            r_s = vtk_marching_cube(ref_im, 0, i)
            dist_ref2pred, d_ref2pred = _get_assd(p_s, r_s)
            dist_pred2ref, d_pred2ref = _get_assd(r_s, p_s)
            dist[index] = (dist_ref2pred+dist_pred2ref)*0.5

            haus_p2r = directed_hausdorff(vtk_to_numpy(p_s.GetPoints().GetData()), vtk_to_numpy(r_s.GetPoints().GetData()))
            haus_r2p = directed_hausdorff(vtk_to_numpy(r_s.GetPoints().GetData()), vtk_to_numpy(p_s.GetPoints().GetData()))
            haus[index] = max(haus_p2r, haus_r2p)
            pred_poly_l.append(p_s)
            dist_poly_l.append(d_pred2ref)
            ref_poly_l.append(r_s)
        dist_poly = appendPolyData(dist_poly_l)
        pred_poly = appendPolyData(pred_poly_l)
        ref_poly = appendPolyData(ref_poly_l)
        dist_r2p, _ = _get_assd(pred_poly, ref_poly)
        dist_p2r, _ = _get_assd(ref_poly, pred_poly)
        dist[0] = 0.5*(dist_r2p+dist_p2r)

        haus_p2r = directed_hausdorff(vtk_to_numpy(pred_poly.GetPoints().GetData()), vtk_to_numpy(ref_poly.GetPoints().GetData()))
        haus_r2p = directed_hausdorff(vtk_to_numpy(ref_poly.GetPoints().GetData()), vtk_to_numpy(pred_poly.GetPoints().GetData()))
        haus[0] = max(haus_p2r, haus_r2p)

        return dist, haus

    def write_prediction(self, seg_id, index=0, motion=False,  write_image=True):
        dir_name = os.path.dirname(self.out_fn)
        base_name = os.path.basename(self.out_fn)
        for i, pred in enumerate(self.prediction):
            fn_i =os.path.join(dir_name, 'block_{}_{}_{}.vtp'.format(i, base_name, index) if motion else 'block_{}_{}.vtp'.format(i, base_name))
            write_vtk_polydata(pred, fn_i)
        for i, pred in enumerate(self.prediction_grid):
            fn_i =os.path.join(dir_name, 'block_{}_{}_grid_{}.vtp'.format(i, base_name, index) if motion else 'block_{}_{}_grid.vtp'.format(i, base_name) )
            write_numpy_points(pred, fn_i)
        if write_image:
            _, ext = self.image_fn.split(os.extsep, 1)
            if ext == 'vti':
                ref_im = load_vtk_image(self.image_fn)
            else:
                im = sitk.ReadImage(self.image_fn)
                ref_im, M = exportSitk2VTK(im)
            self.seg_result=multiclass_convert_polydata_to_imagedata(self.prediction[-1], ref_im)
            if ext == 'vti':
                write_vtk_image(self.seg_result, os.path.join(dir_name, base_name+'.vti'))
            else:
                vtk_write_mask_as_nifty(self.seg_result, M, self.image_fn, os.path.join(dir_name, base_name+'.nii.gz'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='config/cap.yaml')
    args = parser.parse_args()
    with open(args.config, 'r') as stream:
        params = yaml.safe_load(stream)
    
    if not os.path.exists(params['prediction']['output_folder']):
        os.makedirs(params['prediction']['output_folder'])
    import time
    start = time.time()
    #load image filenames
    BATCH_SIZE = 1
    pkl = pickle.load(open(params['prediction']['mesh']['mesh_dat_filemame'], 'rb'))
    mesh_tmplt = load_vtk_mesh(params['prediction']['mesh']['mesh_tmplt_filename'])
    if params['prediction']['mesh']['swap_bc_coordinates'] is not None:
        swap_weight = [np.genfromtxt(params['prediction']['mesh']['swap_bc_coordinates'],delimiter=',')]
        pkl['bbw'] = swap_weight * len(pkl['bbw'])
        pkl['tmplt_coords'] = vtk_to_numpy(mesh_tmplt.GetPoints().GetData())
        pkl['id_ctrl_on_sample_all'] = [pkl['id_ctrl_on_sample_all'][-1]]*len(pkl['id_ctrl_on_sample_all'])
        pkl['struct_node_ids'] = [0] + [pkl['tmplt_coords'].shape[0]]*params['prediction']['mesh']['num_mesh']

    mesh_info = construct_feed_dict(pkl,params['network']['num_blocks'], params['network']['coord_emb_dim'], has_cap=False)
    info = {'batch_size': BATCH_SIZE,
            'input_size': (*params['network']['input_size'], 1),
            'hidden_dim': params['network']['hidden_dim'],
            'feed_dict': mesh_info,
            'num_mesh': params['prediction']['mesh']['num_mesh'],
            'num_seg': params['network']['num_seg_class'],
            'num_block': params['network']['num_blocks'], 
            'amplify_factor': params['network']['rescale_factor'], 
            'train': False
            }
    filenames = {}
    extensions = ['nii', 'nii.gz', 'vti']
    predict = Prediction(info, params['prediction']['model_weights_filename'], mesh_tmplt)
    for m in params['prediction']['image']['modality']:
        x_filenames, y_filenames = [], []
        for ext in extensions:
            im_loader = DataLoader(m, params['prediction']['image']['image_folder'], \
                    fn=params['prediction']['image']['image_folder_attr'], \
                    fn_mask=None if params['prediction']['mode']=='test' else params['prediction']['image']['image_folder_attr']+'_masks', ext='*.'+ext, ext_out='*.'+ext)
            x_fns_temp, y_fns_temp = im_loader.load_datafiles()
            x_filenames += x_fns_temp
            y_filenames += y_fns_temp
        x_filenames = natural_sort(x_filenames)
        try:
            y_filenames = natural_sort(y_filenames)
        except: pass
        score_list = []
        assd_list = []
        haus_list = []
        time_list = []
        time_list2 = []
        for i in range(len(x_filenames)):
            #set up models
            print("processing "+x_filenames[i])
            out_fn = os.path.basename(x_filenames[i]).split('.')[0]
            start2 = time.time()
            predict.set_image_info(m, x_filenames[i], params['network']['input_size'], os.path.join(params['prediction']['output_folder'], out_fn), y_filenames[i], write=False)
            predict.mesh_prediction()
            predict.write_prediction(list(range(1, params['prediction']['mesh']['num_mesh']+1)), 0, False, write_image=True)
            time_list.append(predict.pred_time)
            end2 = time.time()
            time_list2.append(end2-start2)
            if y_filenames[i] is not None:
                score_list.append(predict.evaluate_dice())
                #assd, haus = predict.evaluate_assd()
                #assd_list.append(assd)
                #haus_list.append(haus)
                #metric_names = predict.get_metric_names
        if len(score_list) >0:
            csv_path = os.path.join(params['prediction']['output_folder'], '%s_test.csv' % m)
            csv_path_assd = os.path.join(params['prediction']['output_folder'], '%s_test_assd.csv' % m)
            csv_path_haus = os.path.join(params['prediction']['output_folder'], '%s_test_haus.csv' % m)
            write_scores(csv_path, score_list)
            write_scores(csv_path_assd, assd_list)
            write_scores(csv_path_haus, haus_list)

    end = time.time()
    print("Total time spent: ", end-start)
    print("Avg pred time ", np.mean(time_list)) 
    print("Avg generation time", np.mean(time_list2))
