# -*- coding: utf-8 -*-
"""
@author: Manchun LEI
LASTIG, Univ. Gustave Eiffel, ENSG, IGN, F-94160 Saint-Mandé, France
"""

import numpy as np
from PIL import Image,ExifTags

def debayer_sub(data):
    '''# debayer by sub sampling
    debayer without interpolation
 
    Args:
        data (TYPE): numpy array image raw data

    Returns:
        half size r,g1,g2,b image
        3 dimension numpy array: [ny,nx,nb],for(r,g1,g2,b)
    '''
    nl,nc = np.shape(data)
    nl = int(nl/2)
    nc = int(nc/2)
    l0 = [[0]]
    l1 = [[1]]
    for x in np.arange(nl-1):
        l0.append([x*2+2])
        l1.append([x*2+3])
    c0 = np.arange(nc)*2
    c1 = np.arange(nc)*2+1
    
    data1 = np.empty([nl,nc,4],data.dtype)
    data1[:,:,0] = data[l0,c1]  #r
    data1[:,:,1] = data[l0,c0]  #g1
    data1[:,:,2] = data[l1,c1]  #g2
    data1[:,:,3] = data[l1,c0]  #b
    
    return data1

def debayer_sub_rgb(data):
    deb_sub = debayer_sub(data)
    ny,nx,_ = deb_sub.shape
    rgb = np.empty([ny,nx,3],dtype=data.dtype)
    rgb[:,:,0] = deb_sub[:,:,0]
    rgb[:,:,1] = deb_sub[:,:,1]*0.5+deb_sub[:,:,2]*0.5
    rgb[:,:,2] = deb_sub[:,:,3]
    return rgb

def debayer_full(data):
    nl,nc = np.shape(data)
    l0 = [[0]]
    l1 = [[1]]
    for x in np.arange(int(nl/2)-1):
        l0.append([x*2+2])
        l1.append([x*2+3])
    c0 = np.arange(int(nc/2))*2
    c1 = np.arange(int(nc/2))*2+1
    
    r = np.empty([nl,nc],dtype=np.float32)
    g = np.empty([nl,nc],dtype=np.float32)
    b = np.empty([nl,nc],dtype=np.float32)
    g[l0,c0] = data[l0,c0].astype(np.float32) #g1
    r[l0,c1] = data[l0,c1].astype(np.float32)
    b[l1,c0] = data[l1,c0].astype(np.float32)
    g[l1,c1] = data[l1,c1].astype(np.float32) #g2
    
    #les 4 cones
    r[0,0] = r[0,1]
    b[0,0] = b[1,0]
    g[0,nc-1] = (g[0,nc-2]+g[1,nc-1])/2
    b[0,nc-1] = b[1,nc-2]
    r[nl-1,0] = r[nl-2,1]
    g[nl-1,0] = (g[nl-2,0]+g[nl-1,1])/2
    r[nl-1,nc-1] = r[nl-2,nc-1]
    b[nl-1,nc-1] = b[nl-1,nc-2]
            
    #permier ligne
    g[0,1:nc-2:2] = (g[0,0:nc-3:2]+g[0,2:nc-1:2]+g[1,1:nc-2:2])/3
    b[0,1:nc-2:2] = (b[1,0:nc-3:2]+b[1,2:nc-1:2])/2
    r[0,2:nc-1:2] = (r[0,1:nc-2:2]+r[0,3:nc:2])/2
    b[0,2:nc-1:2] = b[1,2:nc-1:2]
    #dernier ligne
    r[nl-1,1:nc-2:2] = r[nl-2,1:nc-2:2]
    b[nl-1,1:nc-2:2] = (b[nl-1,0:nc-3:2]+b[nl-1,2:nc-1:2])/2
    r[nl-1,2:nc-1:2] = (r[nl-2,1:nc-2:2]+r[nl-2,3:nc:2])/2
    g[nl-1,2:nc-1:2] = (g[nl-1,1:nc-2:2]+g[nl-1,3:nc:2]+g[nl-2,2:nc-1:2])/3
    #permier colonne
    r[1:nl-2:2,0] = 0.5*(r[0:nl-3:2,1]+r[2:nl-1:2,1])
    g[1:nl-2:2,0] = (g[0:nl-3:2,0]+g[2:nl-1:2,0]+g[1:nl-2:2,1])/3
    r[2:nl-1:2,0] = r[2:nl-1:2,1]
    b[2:nl-1:2,0] = (b[1:nl-2:2,0]+b[3:nl:2,0])/2
    #dernier colonne
    r[1:nl-2:2,nc-1] = (r[0:nl-3:2,nc-1]+r[2:nl-1:2,nc-1])/2
    b[1:nl-2:2,nc-1] = b[1:nl-2:2,nc-2]
    g[2:nl-1:2,nc-1] = (g[1:nl-2:2,nc-1]+g[3:nl:2,nc-1]+g[2:nl-1:2,nc-2])/3
    b[2:nl-1:2,nc-1] = (b[1:nl-2:2,nc-2]+b[3:nl:2,nc-2])/2   
    #filtre rouge
    g[2:nl-1:2,1:nc-2:2] = (g[1:nl-2:2,1:nc-2:2]+\
                            g[3:nl:2  ,1:nc-2:2]+\
                            g[2:nl-1:2,0:nc-3:2]+\
                            g[2:nl-1:2,2:nc-1:2])/4
    b[2:nl-1:2,1:nc-2:2] = (b[1:nl-2:2,0:nc-3:2]+\
                            b[1:nl-2:2,2:nc-1:2]+\
                            b[3:nl:2  ,0:nc-3:2]+\
                            b[3:nl:2  ,2:nc-1:2])/4
         
    #filtre vert1(ligne paire, colonne paire)
    r[2:nl-1:2,2:nc-1:2] = (r[2:nl-1:2,1:nc-2:2]+r[2:nl-1:2,3:nc:2])/2
    b[2:nl-1:2,2:nc-1:2] = (b[1:nl-2:2,2:nc-1:2]+b[3:nl:2,2:nc-1:2])/2
        
    #filtre vert2(ligne impaire, colonne impaire)
    r[1:nl-2:2,1:nc-2:2] = (r[0:nl-3:2,1:nc-2:2]+r[2:nl-1:2,1:nc-2:2])/2
    b[1:nl-2:2,1:nc-2:2] = (b[1:nl-2:2,0:nc-3:2]+b[1:nl-2:2,2:nc-1:2])/2
    
    #filtre bleu
    r[1:nl-2:2,2:nc-1:2] = (r[0:nl-3:2,1:nc-2:2]+\
                            r[2:nl-1:2,  3:nc:2]+\
                            r[0:nl-3:2,1:nc-2:2]+\
                            r[2:nl-1:2,  3:nc:2])/4
    g[1:nl-2:2,2:nc-1:2] = (g[1:nl-2:2,1:nc-2:2]+\
                            g[1:nl-2:2,  3:nc:2]+\
                            g[0:nl-3:2,2:nc-1:2]+\
                            g[2:nl-1:2,2:nc-1:2])/4
            
    rgb = np.empty([nl,nc,3],dtype=data.dtype)
    rgb[:,:,0] = r
    rgb[:,:,1] = g
    rgb[:,:,2] = b    
    
    return rgb

def create_exif_tag(camera_name,pixel_format,datetime,exposure_time,offset_x,offset_y,
                    fnumber=-1,description="Description d'image"):
    '''
    camera_name,pixel_format,exposure_time,offset_x,offset_y are metadata from vimba camera state
    datetime is registed when launch camera acquisition, use datetime.now()
    fnumber requist manual registration, fnumber=-1, means fnumber information is not registed
    '''
    tag = {}
    tag[270] = description
    tag[271] = cam_name
    tag[272] = str(pixel_format)
    tag[306] = datetime
    tag[33434] = exposure_time # s
    tag[33437] = fn
    tag[1000] = offset_x
    tag[1001] = offset_y
    return tag
    

def convert_tags_to_dict(tags):
    custom_tags_mapping = {
        1000: 'offset_x',
        1001: 'offset_y'
    }
    tags_dict = {}
    for tag, value in tags.items():
        tag_name = custom_tags_mapping.get(tag, ExifTags.TAGS.get(tag, tag))
        tags_dict[tag_name] = value
                
    return tags_dict

def convert_selected_tags_to_dict(tags):
    custom_tags_mapping = {
        1000: 'offset_x',
        1001: 'offset_y'
    }    
    selected_tags = ['Make','Model','ImageDescription','BitsPerSample',
                     'DateTime','FNumber','ExposureTime',
                     'ImageWidth', 'ImageLength', 'offset_x','offset_y']
    renamed_tags_mapping = {'ImageWidth':'nx','ImageLength':'ny','BitsPerSample':'bits',
                            'ImageDescription':'description','Make': 'camera','Model':'pixel_format',
                           'ExposureTime':'exposure','FNumber':'fnumber','DateTime':'datetime'}
    
    tags_dict = {}
    for tag, value in tags.items():
        tag_name = custom_tags_mapping.get(tag, ExifTags.TAGS.get(tag, tag))
        if tag_name in selected_tags:
            tags_dict[tag_name] = value
    
    ordered_tags_dict = {renamed_tags_mapping.get(tag_name, tag_name): tags_dict[tag_name] 
                         for tag_name in selected_tags if tag_name in tags_dict}
    
    val = ordered_tags_dict['bits'][0]
    ordered_tags_dict['bits'] = val
         
    return ordered_tags_dict

def read_exif_tags(srcfile,show=False):
    tags = Image.open(srcfile).tag_v2
    tags_dict = convert_tags_to_dict(tags)
    if show:
        for name,val in tags_dict.items():
            print(name,':',val)
    return tags_dict

def read_exif_selected_tags(srcfile,show=False):
    
    tags = Image.open(srcfile).tag_v2
    selected_tags_dict = convert_selected_tags_to_dict(tags)
    if show:
        for name,val in selected_tags_dict.items():
            print(name,':',val)
    return selected_tags_dict
    
def read_rgb_sub(srcfile):
    return debayer_sub_rgb(np.asarray(Image.open(srcfile)))