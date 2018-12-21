# VisiView Macro
import sys
import os

paramFile = "C:\\Users\\Public\\Metamorph\\PositionList.stg"
try:
	VV.Acquire.Stage.PositionList.Load("C:\\Users\\Public\\Metamorph\\PositionList.stg")
except:
	print ("There was a problem")

