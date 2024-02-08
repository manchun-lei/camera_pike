# -*- coding: utf-8 -*-
"""
Created on Mon Feb 28 10:43:29 2022

@author: Manchun LEI
LASTIG, Univ. Gustave Eiffel, ENSG, IGN, F-94160 Saint-Mandé, France

Package name:
    none
Module name:
    vimba_util
    ---------------
    This module is used to control the Pike camera using VimbaPython package.
    The Pike camera driver Vimba must be installed.
    The vimba package must be included.
    Use PIL to save image as tif format and add informations as tag of exif.
"""

import os
import numpy as np
from PIL import Image
from PIL import ExifTags
from datetime import datetime
from vimba import *
from util import create_exif_tag

_timeout_s_offset = 0.5

class CamState():
    '''
    get camera current state
    '''
    def __init__(self,cam):
      
        # print(dir(cam))
        self.name = cam.get_name()
        self.width = cam.Width.get()
        self.height = cam.Height.get()
        self.offset_x = cam.OffsetX.get()
        self.offset_y = cam.OffsetY.get()
        self._base = cam.ExposureAutoTimebase.get()
        self.exposure_time = cam.ExposureTime.get()
        self.pixel_format = str(cam.get_pixel_format())
    
    def __str__(self):
        msg = self.name+'\n'
        msg += 'pixel_format = '+self.pixel_format+' \n'
        msg += 'exposure_time = '+str(self.exposure_time)+' us \n'
        msg += 'time_base = '+str(self.time_base)+' \n'
        msg += 'width = '+str(self.width)+' \n'
        msg += 'height = '+str(self.height)+' \n'
        msg += 'offset_x = '+str(self.offset_x)+' \n'
        msg += 'offset_y = '+str(self.offset_y)+' \n'
        return msg

def current_state():
    print('Camera Current State')
    print('--------------------')
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam:
            print(CamState(cam))
        print('--------------------')
        
def cal_time_base(t):
    offset = 38
    factor = 4095.
    time_bases = np.array([1,2,5,10,20,50,100,500,1000])
    sel = t/factor
    ind = np.where(time_bases>=sel)
    if len(ind[0])<1:       
        return 'tb1000us'
    else:
        bases = time_bases[ind]
        factors = (t-offset)/bases
        
        decs = factors % 1
        ind1 = np.where(decs==np.min(decs))
        # factor = factors[ind1]
        time_base = 'tb'+str(bases[ind1[0][0]])+'us'
        # print(factors[ind1],time_base)
    
    return time_base        


def cam_set_exposure_time(cam,exposure_time):
    '''
    cam: camera object
    exposure_time: in us
    The camera Pike F210C can get max exposure time as 67108901us,
    but in fact, the expoure time >1.95s can not be executed.
    Modification 2022-03-01
    The problem with long exposure is caused by timtout setting in 
    cam.get_framce(timtout_ms=2000), the solution is change this value for
    long exposure time timeout_ms = (t_s+1)*1000
    '''
    exposure_min = 77
    exposure_max = 67108901
    # exposure_max = 1900000
    nmax = 200
    if exposure_time<exposure_min:
        print('exposure time cannot < {} s'.format(exposure_min/1e6))
        return False
    if exposure_time>exposure_max:
        print('exposure time cannot > {} s'.format(exposure_max/1e6))
        return False
    if(exposure_time != cam.ExposureTime.get()):
        #calculate time base for new exposure time
        new_time_base = cal_time_base(exposure_time)
        #check if need to change the time base
        if(new_time_base != cam.ExposureAutoTimebase.get()):
            cam.ExposureAutoTimebase.set(new_time_base)
        #change exposure time
        cam.ExposureTime.set(exposure_time)
        #check
        t_dif = np.abs(exposure_time-cam.ExposureTime.get())
        i = 0
        while (t_dif>0 and i<nmax):
            #try again
            cam.ExposureTime.set(exposure_time)
            t_dif = np.abs(exposure_time-cam.ExposureTime.get())
            i+=1
        #last check
        if t_dif>0:
            return False
        else:
            return True
    else:
        return True


def cam_set_pixel_format(cam,pixel_format):
    '''
    set pixel format of camera
    cam: camera object
    '''
    pixel_formats = cam.get_pixel_formats()
    ret = True
    if pixel_format=='rgb16':
        cam.set_pixel_format(pixel_formats[3])
    elif pixel_format=='rgb8':
        cam.set_pixel_format(pixel_formats[1])
    elif pixel_format=='mono8':
        cam.set_pixel_format(pixel_formats[0])
    else:
        print('pixel_format error, current format will used')
        ret = False
    return ret

def cam_set_offset(cam,offset):
    '''
    set camera offset(x,y)
    Strongly I found if I don't call get_frame on time, the new offset
    can not be registred by camera.
    That mean I must take a frame just for the camera can remember the offset.
    And for timeout reason, I want use a fix small value as exposure time.
    But the savec exposure time will reset to camera after this frame.
    '''
    ret = True
    
    # #current offset
    # print('current offset x:',cam.OffsetX.get())
    # print('current offset y:',cam.OffsetY.get())
    
    offset_x,offset_y = offset
    xmin,xmax = cam.OffsetX.get_range()
    if offset_x>=xmin and offset_x<=xmax:
        if offset_x%2==0:
            cam.OffsetX.set(offset_x)
        else:
            print('error, offset_x is not a multiple of 2')
            ret = False
    else:
        print('offset_x error: must between {} and {}'.format(
            xmin,xmax))
        ret = False
    
    ymin,ymax = cam.OffsetY.get_range()
    if offset_y>=ymin and offset_y<=ymax:
        if offset_y%2==0:
            cam.OffsetY.set(offset_y)
        else:
            print('error, offset_y is not a multiple of 2')
            ret = False
    else:
        print('offset_y error: must between {} and {}'.format(
            ymin,ymax))
        ret = False
    # print('new offset x:',cam.OffsetX.get())
    # print('new offset y:',cam.OffsetY.get())
    if ret:
        current_exposure_time = cam.ExposureTime.get()
        cam.ExposureTime.set(100)
        frame = cam.get_frame()
        cam.ExposureTime.set(current_exposure_time)
    return ret

def cam_set_frame_size(cam,size):
    ret = True
    width,height = size
    width_min,width_max = cam.Width.get_range()
    if width>=width_min and width<=width_max:
        cam.Width.set(width)
    else:
        print('width config error, must between {} and {}'.format(
              width_min,width_max))
        ret = False
    height_min,height_max = cam.Height.get_range()
    if height>=height_min and height<=height_max:
        cam.Height.set(height)
    else:
        print('height config error,must between {} and {}'.format(
            height_min,height_max))
        ret = False
    return ret

# def cam_config(cam,pixel_format=None,width=None,height=None,\
#             offset_x=None,offset_y=None):
#     '''
#     camera configuration, excepte the exposure time
#     '''     
#     if pixel_format:
#         pixel_formats = cam.get_pixel_formats()
#         if pixel_format=='rgb16':
#             cam.set_pixel_format(pixel_formats[3])
#         elif pixel_format=='rgb8':
#             cam.set_pixel_format(pixel_formats[1])
#         elif pixel_format=='mono8':
#             cam.set_pixel_format(pixel_formats[0])
#         else:
#             print('pixel_format error, current format will used')
    
#     if offset_x:
#         xmin,xmax = cam.OffsetX.get_range()
#         if offset_x>=xmin and offset_x<=xmax:
#             if offset_x%2==0:
#                 cam.OffsetX.set(offset_x)
#             else:
#                 print('error, offset_x is not a multiple of 2')
#         else:
#             print('offset_x error: must between {} and {}'.format(
#                 xmin,xmax))
    
#     if offset_y:
#         ymin,ymax = cam.OffsetY.get_range()
#         if offset_y>=ymin and offset_y<=ymax:
#             if offset_y%2==0:
#                 cam.OffsetY.set(offset_y)
#             else:
#                 print('error, offset_y is not a multiple of 2')
#         else:
#             print('offset_y error: must between {} and {}'.format(
#                 ymin,ymax))
        
#     if width:
#         width_min,width_max = cam.Width.get_range()
#         if width>=width_min and width<=width_max:
#             cam.Width.set(width)
#         else:
#             print('width config error, must between {} and {}'.format(
#                   width_min,width_max))
#     if height:
#         height_min,height_max = cam.Height.get_range()
#         if height>=height_min and height<=height_max:
#             cam.Height.set(height)
#         else:
#             print('height config error,must between {} and {}'.format(
#                 height_min,height_max))
    
    

# def config(pixel_format=None,width=None,height=None,\
#             offset_x=None,offset_y=None):
#     with Vimba.get_instance() as vimba:
#         cams = vimba.get_all_cameras()
#         with cams[0] as cam:
#             # cam_config(cam,pixel_format=pixel_format,
#             #            width=width,height=height,
#             #            offset_x=offset_x,offset_y=offset_y)
            
#             cam_set_pixel_format(cam,pixel_format)
            
#     vimba._shutdown()

def state():
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam:
            print(CamState(cam))
    vimba._shutdown()


def set_exposure_time(t):
    '''
    t: exposure time in s
    return: bool, Ture if exposure time is correctly set
    '''
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam:
            exposure_time = t*1e6
            ret = cam_set_exposure_time(cam, exposure_time)
    vimba._shutdown()
    return ret

def set_pixel_format(pixel_format):
    #set pixel format: rgb16, rgb8, mono8
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam:
            ret = cam_set_pixel_format(cam, pixel_format)
    vimba._shutdown()
    return ret

def reset_offset():
    '''
    reset offset to 0
    '''
    ret = False
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam:
            ret = cam_set_offset(cam,(0,0))
    vimba._shutdown()
    return ret

def set_offset(offset):
    ret = False
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam:
            ret = cam_set_offset(cam,offset)
    vimba._shutdown()
    return ret

def set_frame_size_full():
    ret = reset_offset()
    if ret:
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            with cams[0] as cam:
                ret = cam_set_frame_size(cam,(1920,1080))
        vimba._shutdown()
    return ret

def set_frame_size_sub(size):
    '''
    the offset set will reset to 0 with this function.
    size = (nx,ny)
    '''
    ret = reset_offset()
    if ret:
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            with cams[0] as cam:
                ret = cam_set_frame_size(cam,size)
        vimba._shutdown()
    return ret

def set_frame_size_sub_center(size):
    '''
    the sub frame is base on center of image
    '''
    ret = set_frame_size_sub(size)
    if ret:    
        #calculate the offset
        width,height = size
        offset_x = (1920-width)/2
        offset_y = (1080-height)/2
        ret = set_offset((offset_x,offset_y))
    return ret

def config_rgb16_1920x1080():
    '''
    configuration for rgb16 full frame
    '''
    set_pixel_format('rgb16')
    set_frame_size_full()


def config_mono8_640x480c():
    '''
    configuraiton for a roi frame of 640x480 at center of image
    mono8.
    '''
    set_pixel_format('mono8')
    set_frame_size_sub_center((640,480))

def single_acquisition(t=None,path=None,head='pike',show=False,fn=-1,\
                       description = "single image acquisition"):
    '''
    All camera configuration, including pixel_format, bits, image size, exposure,
    must be condigured before call this function
    '''    
    ret = ''
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam: 
            t_ret = True
            if t:
                t_ret = cam_set_exposure_time(cam, t*1e6)             
            if t_ret:  
                timeout_ms = int((t+_timeout_s_offset)*1000)
                if timeout_ms<2000:
                    timeout_ms = 2000
                #get a frame
                frame = cam.get_frame(timeout_ms)  
                #get datetime
                now = datetime.now()
                #sleep time in s
                real_wait = _timeout_s_offset                        
                time.sleep(t+real_wait)
                #read cam state
                state = CamState(cam)                   
                #get numpy array image, is a bayer 2d array
                data = frame.as_numpy_ndarray()[:,:,0]
                if path:        
                    img = Image.fromarray(data)
                    #create exif tags
                    dt = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    img.tag = create_exif_tag(state.name,state.pixel_format,dt,
                                              state.exposure_time/1e6,
                                              state.offset_x,state.offset_y,
                                              fnumber=fn,description=description)
                    t_str = str(int(state.exposure_time)).zfill(8)
                    file = os.path.join(path,head+'_'+t_str+'.tif')
                    img.save(file,tiffinfo=img.tag)
                    ret = file         
                if show:
                    plt.figure()
                    plt.imshow(data)
                    plt.axis('off')
    
    vimba._shutdown()
    return ret


def multiple_acquisition(n, path,head='pike_multi',wait=None,fn=-1,\
                         description="multi image acquisition"):
    '''
    multiple acquisition of n number images with same exposure time.
    the exposure time must be configured before call this function.
    '''
    
    ret = []
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam: 
            state = CamState(cam)
            #timeout in ms
            timeout_ms = int(((state.exposure_time/1e6)+_timeout_s_offset)*1000)
            if timeout_ms<2000:
                timeout_ms = 2000
            #sleep time in s
            real_wait = _timeout_s_offset
            if wait:
                if real_wait < wait:
                    real_wait = wait
            for c in range(n):
                c+=1
                    
                #get a frame
                frame = cam.get_frame(timeout_ms)  
                #get datetime
                now = datetime.now()
                #get numpy array image, is a bayer 2d array
                data = frame.as_numpy_ndarray()[:,:,0]
                img = Image.fromarray(data)
                #create exif tags
                dt = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]                    
                img.tag = create_exif_tag(state.name,state.pixel_format,dt,
                                              state.exposure_time/1e6,
                                              state.offset_x,state.offset_y,
                                              fnumber=fn,description=description)
                c_str = str(c).zfill(2)
                t_str = str(int(state.exposure_time)).zfill(8)
                file = os.path.join(path,head+'_'+c_str+'_'+t_str+'.tif')
                img.save(file,tiffinfo=img.tag)
                ret.append(file)
                
                time.sleep((state.exposure_time/1e6)+real_wait)
                    
    vimba._shutdown()
    return ret
        
def hdr_acquisition(lt,path,head='pike_seq',wait=None,\
                    fn=-1,description = "hdr images acquisition"):
    '''
    use this function for sequence hdr images acquisition, 
    only exposure time can be changed for each frame.
    Others pamameters must be set by using config()
    Input:
        lt: list of exposure time in s
        path: path name
        head: head name
        wait: a sleep time in s between 2 acquisitions, 
        sleep time should > exposure time
        slepp time = t + wait
        if wait==None, sleep time = t+_timeout_s
        
    Return:
        ret: return the list of filename
    '''
    ret = []
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        with cams[0] as cam: 
            state = CamState(cam)
            c = 1
            for t in lt:
                t_ret = cam_set_exposure_time(cam, t*1e6)
                if t_ret:  
                    timeout_ms = int((t+_timeout_s_offset)*1000)
                    if timeout_ms<2000:
                        timeout_ms = 2000
                    #get a frame
                    frame = cam.get_frame(timeout_ms)  
                    #get datetime
                    now = datetime.now()
                    #get numpy array image, is a bayer 2d array
                    data = frame.as_numpy_ndarray()[:,:,0]
                    img = Image.fromarray(data)
                    #create exif tags
                    dt = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    exposure_real = cam.ExposureTime.get()
                    img.tag = create_exif_tag(state.name,state.pixel_format,dt,
                                              exposure_real/1e6,
                                              state.offset_x,state.offset_y,
                                              fnumber=fn,description=description)
                    c_str = str(c).zfill(2)
                    t_str = str(int(exposure_real)).zfill(8)
                    file = os.path.join(path,head+'_'+c_str+'_'+t_str+'.tif')
                    img.save(file,tiffinfo=img.tag)
                    ret.append(file)
                    c+=1
                    #sleep time in s
                    real_wait = _timeout_s_offset
                    if wait:
                        if real_wait < wait:
                            real_wait = wait                        
                    time.sleep(t+real_wait)
                    
    vimba._shutdown()
    return ret         
    


