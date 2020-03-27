from os import path
import sys

respath = "res"
def res_path(file):
    if getattr(sys, 'frozen',False) and hasattr(sys, '_MEIPASS'):
        return path.join(sys._MEIPASS,respath,file)
    return path.join(respath,file)


def classlistToIds(dat):
    classes = []
    idToIdx = {}
    if(dat):
        n=0
        for c in dat.split("\n"):
            if(c):
                i = c.find(":")
                idToIdx[int(c[0:i])] = (n,c[i+1::])
                classes.append([int(c[0:i]),c[i+1::]])
                n+=1
    return (idToIdx,classes)