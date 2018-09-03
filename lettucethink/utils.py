#!/usr/bin/env python3
import zipfile
import imageio
import numpy as np
import os
import cv2


def createArchive(files, output_archive="all.zip"):
    zf = zipfile.ZipFile(output_archive, mode = 'w')
    try:    
        for f in files:
           print("adding", f)
           zf.write(f)
    finally:
        zf.close()
    return {"href": output_archive, "name": output_archive}


def createGif(files, data="rgb", output_gif="rgb.gif"):
    with imageio.get_writer(output_gif, mode='I',duration=1) as writer:
          for f in files:
              if f[:len(data)]==data: writer.append_data(imageio.imread(f))
                    

def clamp(value, lims, scale=1):
    return int(scale*np.clip(value, lims[0], lims[1]))



class ImageLogger(object):
    def __init__(self, root=False):
        self.root = root
        self.index = 0
        self.history = {}
        if root and not os.path.exists(root):
            os.mkdir(root)

    def storeImage(self, name, image):
        if self.root:
            filepath = self.makePath(name)
            cv2.imwrite(filepath, image)

    def makePath(self, name, ext="jpg"):
        if self.root:
            path = "%s/%02d-%s.%s" % (self.root, self.index, name, ext)
            self.index += 1
            self.history[name] = path
            return path
        else:
            return None

    def getPath(self, name):
        return self.history[name]

    def isLogging(self):
        return self.root != False

    def setRoot(self, root):
        self.root = root

    def reset(self):
        this.index = 0

    def incrementIndex(self):
        this.index += 1



        
class SVGDocument(object):
    def __init__(self, path, width, height):
        self.path = path
        self.printHeader(width, height)
        
    def printHeader(self, width, height):
        with open(self.path, "w") as f:
            f.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><svg xmlns:svg=\"http://www.w3.org/2000/svg\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" version=\"1.0\" width=\"%dpx\" height=\"%dpx\">\n" % (width, height))

    def addImage(self, href, x, y, width, height):
        with open(self.path, "a") as f:
            f.write("    <image xlink:href=\"%s\" x=\"%dpx\" y=\"%dpx\" width=\"%dpx\" height=\"%dpx\" />\n" % (href, x, y, width, height))

    def addPath(self, x, y):
        path = "M %f,%f L" % (x[0], y[0])
        for i in range(1, len(x)):
            path += " %f,%f" % (x[i], y[i])
        with open(self.path, "a") as f:
            f.write("    <path d=\"%s\" id=\"path\" style=\"fill:none;stroke:#0000ce;stroke-width:2;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none\" />" % path)
            
    def close(self):
        self.printFooter()
        
    def printFooter(self):
        with open(self.path, "a") as f:
            f.write("</svg>\n")


   

class Workspace(object):
   # (x0,y0) are the pixel coordinates of the origin of the CNC in the
   # topcam image.
   #
   # theta is the angle, in degrees, over which the image should
   # rotated (around x0,y0) to align the topcam image withe frame of
   # the rover topcam image. Only a rotation around the z-axis is
   # considered for now.
   #
   # width_px and height_px are the width and height of the workspace,
   # measured in pixels, as seen in the topcam image.
   # 
   # width_mm, height_mm are the width and the height of the real
   # workspace, measured in millimeters.
   def __init__(self, theta,
                x0, y0,
                width_px, height_px,
                width_mm, height_mm):
      self.theta = theta
      self.x0 = x0
      self.y0 = y0
      self.width = width_px
      self.height = height_px
      self.realWidth = width_mm
      self.realHeight = height_mm
      radians = np.radians(theta)
      self.c = np.cos(radians)
      self.s = np.sin(radians)

   # Converts a point in the topcam image (the original image, not the
   # cropped and rotated image) to the coordinate in the CNC's
   # workspace in millimeters.
   def convertImagePoint(self, x, y):
      x -= self.x0
      y -= self.y0
      x = self.px2mm(self.c * x - self.s * y)
      y = self.px2mm(self.s * x + self.c * y)
      return x, y
   
   def px2mm(self, x):
      return self.realWidth * x / self.width

   def mm2px(self, x):
      return self.width * x / self.realWidth

