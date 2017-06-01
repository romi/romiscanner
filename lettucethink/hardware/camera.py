#!/usr/bin/python
import pydepthsense as ds
import cv2

class Camera(object):
    '''
    DepthSense camera
    ''' 
    def __init__(self):
       ds.start()

    def grab_image(self, rgb, depth):
       im_rgb = ds.getColourMap()
       cv2.imwrite(rgb, im_rgb)       
       im_depth = ds.getDepthMap()
       cv2.imwrite(depth, im_depth)   

    def grab_data(self, svg, i=0,
                  datas=["sync", "uv", "conf", "vertFP",
                         "rgb", "vert","depth"]):
       if "sync" in datas:
          im=ds.getSyncMap()
          np.save(svg+"sync-%03d.png"%i,im)
       if "uv" in datas:
          im=ds.getUVMap()
          np.save(svg+"uv-%03d.png"%i,im)
       if "conf" in datas:
          im=ds.getConfidenceMap()
          np.save(svg+"conf-%03d.png"%i,im)
       if "vertFP" in datas:
          im=ds.getVerticesFP()
          np.save(svg+"vertFP-%03d.png"%i,im)
       if "rgb" in datas:
          im=ds.getColourMap()
          np.save(svg+"rgb-%03d.png"%i,im)
       if "vert" in datas:
          im=ds.getVertices()
          np.save(svg+"vert-%03d.png"%i,im)
       if "depth" in datas:
          im=ds.getDepthMap()
          np.save(svg+"depth-%03d.png"%i,im)
