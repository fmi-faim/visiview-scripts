# VisiView Macro
import sys
import csv, os, re
from System import Array
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\Examples\Image Access\OpenCV\Library")
vvimport('OpenCV')


def parsePositions():
	tempDir = os.getenv("TEMP")
	# Save the position list to calculate the focus map
	VV.Acquire.Stage.PositionList.Save(tempDir + "\\PositionList.stg")
	# TODO save position list to same folder as datasets

	# Read the position list from file
	fo = open(tempDir + "\\PositionList.stg")
	reader = csv.reader(fo)
	stagePositions = []
	coordsX = []
	coordsY = []
	coordsZ = []

	for row in reader:
		if (reader.line_num > 4):
			coordsX.append(float(row[1]))
			coordsY.append(float(row[2]))
			coordsZ.append(float(row[3]))
	return coordsX, coordsY, coordsZ

def stagePosDialog(listSTGfiles):
	myList = []
	global myVar
	myVar = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
	VV.Macro.InputDialog.Initialize("Select position lists", True)
	for i in range(len(listSTGfiles)):
		VV.Macro.InputDialog.AddBoolVariable(listSTGfiles[i], "myVar["+str(i)+"]", False)
	VV.Macro.InputDialog.Show()

	for i in range(len(listSTGfiles)):
		if myVar[i]:
			myList.append(listSTGfiles[i])
	return myList


# *************************************************************************************
# 	MAIN
# *************************************************************************************
def main():

	# Initialization
	cal = VV.Image.Calibration.Value
	bin = VV.Acquire.Binning
	VV.Acquire.Stage.SeriesType = 'PositionList'
	baseDir = VV.Acquire.Sequence.Directory
	baseName = VV.Acquire.Sequence.BaseName
	listSTGfiles = []
	stgFileList = []
	tileCentersX = []
	tileCentersY = []
	tileCentersZ = []
	magnificationRatio = float(VV.Magnification.Calibration.Value)/float(VV.Image.Calibration.Value)
	print (magnificationRatio)
	s = 2048*magnificationRatio
	xLeft, yTop = VV.File.ConvertImageCoordinatesToStageCoordinates(0,0)

	# List all stg files in baseDir folder
	onlyFiles = [f for f in os.listdir(VV.Acquire.Sequence.Directory) if os.path.isfile(os.path.join(VV.Acquire.Sequence.Directory, f))]
	for f in onlyFiles:
		if (f.split(".")[1:][0] == "stg") & (baseName in f):
			listSTGfiles.append(f)
			
	# Select stg file in dialog window
	stgFileList = stagePosDialog(listSTGfiles)
	
	for STGlist in stgFileList:
		path = os.path.join(baseDir, STGlist)
		VV.Acquire.Stage.PositionList.Load(path)
		tileCentersX, tileCentersY, tileCentersZ = parsePositions()
		# Draw regions
		for j in range(len(tileCentersX)):
			x = int((tileCentersX[j]-xLeft)/cal)
			y = int((tileCentersY[j]-yTop)/cal)
			VV.Window.Regions.AddCentered("Rectangle", x, y, s, s)

main()
