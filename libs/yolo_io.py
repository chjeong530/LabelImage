#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
from libs.constants import DEFAULT_ENCODING

TXT_EXT = '.txt'
ENCODE_METHOD = DEFAULT_ENCODING

class YOLOWriter:

    def __init__(self, foldername, filename, imgSize, databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        self.boxlist.append(bndbox)

    def BndBox2YoloLine(self, box, classList=[]):
        xmin = box['xmin']
        xmax = box['xmax']
        ymin = box['ymin']
        ymax = box['ymax']

        # xcen = float((xmin + xmax)) / 2 / self.imgSize[1]
        # ycen = float((ymin + ymax)) / 2 / self.imgSize[0]

        x = float(xmin) / self.imgSize[1]
        y = float(ymin) / self.imgSize[0]
        w = float((xmax - xmin)) / self.imgSize[1]
        h = float((ymax - ymin)) / self.imgSize[0]

        # PR387
        boxName = box['name']
        if boxName not in classList:
            classList.append(boxName)

        classIndex = classList.index(boxName)

        return classIndex, x, y, w, h

    def save(self, classList=[], text="", targetFile=None):

        out_file = None #Update yolo .txt
        out_class_file = None   #Update class list .txt

        if targetFile is None:
            out_file = open(
            self.filename + TXT_EXT, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        else:
            path = os.path.dirname(targetFile)
            filename = os.path.basename(targetFile)
            path = os.path.join(path, filename)
            out_file = codecs.open(path, 'w', encoding=ENCODE_METHOD)
            # out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(targetFile)), "classes.txt")
            out_class_file = open(classesFile, 'w')


        out_file.write("# filename : %s\n" % str(self.filename))
        out_file.write("# image width : %d\n" % int(self.imgSize[1]))
        out_file.write("# image height : %d\n" % int(self.imgSize[0]))
        out_file.write("# image description : %s\n" % text)

        for idx, box in enumerate(self.boxlist):
            classIndex, xcen, ycen, w, h = self.BndBox2YoloLine(box, classList)
            # print (classIndex, xcen, ycen, w, h)
            # out_file.write("%d %.6f %.6f %.6f %.6f\n" % (classIndex, xcen, ycen, w, h))
            out_file.write("%d %.6f %.6f %.6f %.6f\n" % (idx, xcen, ycen, w, h))
            # out_file.write("%d %.6f %.6f %.6f %.6f\n" % (classIndex, xmin, ymin, w, h))

        # print (classList) # print (out_class_file) for c in classList: out_class_file.write(c+'\n') out_class_file.close()
        out_file.close()



class YoloReader:

    def __init__(self, filepath, image, classListPath=None):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.filepath = filepath
        self.description = ""

        if classListPath is None:
            dir_path = os.path.dirname(os.path.realpath(self.filepath))
            self.classListPath = os.path.join(dir_path, "classes.txt")
        else:
            self.classListPath = classListPath

        # print (filepath, self.classListPath)

        classesFile = open(self.classListPath, 'r')
        self.classes = classesFile.read().strip('\n').split('\n')

        # print (self.classes)

        imgSize = [image.height(), image.width(),
                      1 if image.isGrayscale() else 3]

        self.imgSize = imgSize

        self.verified = False
        # try:
        self.parseYoloFormat()
        # except:
            # pass

    def getShapes(self):
        return self.shapes

    def getDescription(self):
        return self.description

    def addShape(self, label, xmin, ymin, xmax, ymax, difficult):

        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        self.shapes.append((label, points, None, None, difficult))

    def yoloLine2Shape(self, classIndex, xcen, ycen, w, h):
        # label = self.classes[int(classIndex)]
        label = classIndex

        # xmin = max(float(xcen) - float(w) / 2, 0)
        # xmax = min(float(xcen) + float(w) / 2, 1)
        # ymin = max(float(ycen) - float(h) / 2, 0)
        # ymax = min(float(ycen) + float(h) / 2, 1)

        # xmin = int(self.imgSize[1] * xmin)
        # xmax = int(self.imgSize[1] * xmax)
        # ymin = int(self.imgSize[0] * ymin)
        # ymax = int(self.imgSize[0] * ymax)

        xmin = int(self.imgSize[1] * float(xcen))
        ymin = int(self.imgSize[0] * float(ycen))
        xmax = int(self.imgSize[1] * float(w) + xmin)
        ymax = int(self.imgSize[0] * float(h) + ymin)

        return label, xmin, ymin, xmax, ymax

    def parseYoloFormat(self):
        bndBoxFile = open(self.filepath, 'r')
        bndBoxFileLines = bndBoxFile.readlines()
        for bndBox in bndBoxFileLines:
            if "description" in bndBox:
                self.description = bndBox.split(':')[-1].strip()

            if bndBox[0] is not '#':
                classIndex, xcen, ycen, w, h = bndBox.split(' ')
                label, xmin, ymin, xmax, ymax = self.yoloLine2Shape(classIndex, xcen, ycen, w, h[:-1])

                # Caveat: difficult flag is discarded when saved as yolo format.
                self.addShape(label, xmin, ymin, xmax, ymax, False)
