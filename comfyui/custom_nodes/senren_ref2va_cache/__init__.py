"""Additive Ref2VA nested conditioning cache; no changes to existing nodes."""
import json, pathlib
import torch, safetensors.torch, folder_paths
from comfy.nested_tensor import NestedTensor

def pack(value, tensors):
    if isinstance(value,NestedTensor):return {'nested':[pack(t,tensors) for t in value.unbind()]}
    if isinstance(value,torch.Tensor):
        key=f't{len(tensors)}';tensors[key]=value.detach().cpu().contiguous();return {'tensor':key}
    if isinstance(value,dict):return {'dict':{str(k):pack(v,tensors) for k,v in value.items()}}
    if isinstance(value,(list,tuple)):return {'tuple' if isinstance(value,tuple) else 'list':[pack(v,tensors) for v in value]}
    if value is None or isinstance(value,(str,int,float,bool)):return {'scalar':value}
    raise TypeError(f'Unsupported cache type {type(value)}')
def unpack(v,tensors):
    if 'nested' in v:return NestedTensor([unpack(x,tensors) for x in v['nested']])
    if 'tensor' in v:return tensors[v['tensor']]
    if 'dict' in v:return {k:unpack(x,tensors) for k,x in v['dict'].items()}
    if 'tuple' in v:return tuple(unpack(x,tensors) for x in v['tuple'])
    if 'list' in v:return [unpack(x,tensors) for x in v['list']]
    return v['scalar']
class SenrenSaveReferenceCache:
    @classmethod
    def INPUT_TYPES(cls):return {'required':{'conditioning':('CONDITIONING',),'latent':('LATENT',),'filename_prefix':('STRING',{'default':'senren_ref2va/cache'})}}
    RETURN_TYPES=(); FUNCTION='save'; CATEGORY='senren/ref2va'; OUTPUT_NODE=True
    def save(self,conditioning,latent,filename_prefix):
        directory,name,counter,_,_=folder_paths.get_save_image_path(filename_prefix,folder_paths.get_output_directory())
        target=pathlib.Path(directory)/f'{name}_{counter:05}_.safetensors'; tensors={}
        structure=pack({'conditioning':conditioning,'latent':latent},tensors)
        safetensors.torch.save_file(tensors,str(target),metadata={'senren_schema':'1','structure':json.dumps(structure)})
        return {'ui':{'cache_files':[str(target)]}}
class SenrenLoadReferenceCache:
    @classmethod
    def INPUT_TYPES(cls):return {'required':{'cache_name':(folder_paths.get_filename_list('embeddings'),)}}
    RETURN_TYPES=('CONDITIONING','LATENT'); FUNCTION='load'; CATEGORY='senren/ref2va'
    def load(self,cache_name):
        from safetensors import safe_open
        path=folder_paths.get_full_path_or_raise('embeddings',cache_name)
        with safe_open(path,framework='pt',device='cpu') as f:
            meta=f.metadata();assert meta['senren_schema']=='1'
            value=unpack(json.loads(meta['structure']),{k:f.get_tensor(k) for k in f.keys()})
        return (value['conditioning'],value['latent'])
NODE_CLASS_MAPPINGS={'SenrenSaveReferenceCache':SenrenSaveReferenceCache,'SenrenLoadReferenceCache':SenrenLoadReferenceCache}
