# VisiView Macro
import clr, math, sys
import csv, os, re
from System import Array
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\Examples\Image Access\OpenCV\Library")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\lib")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\faim-common-utils")
vvimport('OpenCV')
vvimport('fileutils')
import datetime
import ctypes
import EmailToolbox
import focusmap

# *************************************************************************************
# Positions in the position list are saved as a .stg file opened with a csv reader.
# The function returns 3 arrays of coordinates for x, y and z
# *************************************************************************************

def generateHeightImage(width, height, calibration, cX, cY, cZ):
	# Get Image corner coords as stage coordinates
	xLeft, yTop = VV.File.ConvertImageCoordinatesToStageCoordinates(0,0)
	# Triangulate list and corner points
	points = focusmap.buildTriangles(cX, cY, cZ,xLeft,yTop,width*calibration,height*calibration)
	# transform to pixel coords
	focusmap.transformTriangles(points, calibration, xLeft, yTop)
	# create empty heightImage
	outputImage = CvMat(height, width, MatrixType.F32C1)
	outputImage.Set(CvScalar(0.0))
	# interpolate and create image
	focusmap.BiLinearInterpolation(points, outputImage)
	# return image
	return outputImage

def saveHeightImage(heightImageHandle, focusMin, focusMax):
	SetGlobalVar('ch.fmi.VV.focusMin', focusMin)
	SetGlobalVar('ch.fmi.VV.focusMax', focusMax)
	VV.Window.Selected.Handle = heightImageHandle
	tempDir = os.getenv("TEMP")
	VV.File.SaveAs(os.path.join(tempDir, 'TmpFocusImage.tif'), True)

def loadHeightImage():
	focusMin = GetGlobalVar('ch.fmi.VV.focusMin')
	focusMax = GetGlobalVar('ch.fmi.VV.focusMax')
	tempDir = os.getenv("TEMP")
	VV.File.Open(os.path.join(tempDir, 'TmpFocusImage.tif'))
	w = VV.Image.Width
	h = VV.Image.Height
	heightImageRead = CvMat(h,w,MatrixType.U16C1)
	VV.Image.ReadToPointer(heightImageRead.Data)
	heightImageFloat = CvMat(h,w,MatrixType.F32C1)
	heightImageRead.Convert(heightImageFloat)
	heightImageDenormalized = (heightImageFloat * (focusMax - focusMin)) / 65535 + CvScalar(focusMin)
	return heightImageDenormalized

def displayHeightImage(heightImage, focusMin, focusMax, regionFileName, scale, heightImageW, heightImageH):
	# set values between 0 and 65000 for more contrast in display
	heightImageNormalized = heightImage if (focusMax==focusMin) else (heightImage-CvScalar(focusMin))*65535/(focusMax-focusMin)
	# create a 16-bit image
	heightImageU16 = CvMat(heightImageH, heightImageW, MatrixType.U16C1)
	# transfer values of height image into 16-bit image
	heightImageNormalized.Convert(heightImageU16)
	# create a new image window in Visiview and copy values of height image into it
	VV.Process.CreateEmptyPlane('Monochrome16', heightImageW, heightImageH)
	VV.Image.WriteFromPointer(heightImageU16.Data, heightImageH, heightImageW)

def displayImage(cvImage):
	VV.Process.CreateEmptyPlane('Monochrome8',VV.Image.Width, VV.Image.Height)
	VV.Image.WriteFromPointer(cvImage.Data, VV.Image.Width, VV.Image.Height)

def getAcquisitionTiles(regionIndex, binaryMask, bin, magnificationRatio, heightImage):
		# Select next region
		VV.Window.Regions.Active.Index = regionIndex
		# TODO make user-definable
		overlap = 0.1
		# get all information on the active region
		points, CoordX, CoordY = VV.Window.Regions.Active.CoordinatesToArrays()
		# Clear mask (reset to 0)
		binaryMask.Set(CvScalar(0))
		#Region as polyline
		polygonPoints = Array.CreateInstance(CvPoint, len(CoordX))
		for i in range(len(CoordX)):
			polygonPoints[i] = CvPoint(CoordX[i],CoordY[i])
		polyLines = Array.CreateInstance(Array[CvPoint], 1)
		polyLines[0] = polygonPoints
		if VV.Window.Regions.Active.Type == 'PolyLine':
			binaryMask.PolyLine(polyLines,False,CvScalar(255))
		else:
			binaryMask.FillPoly(polyLines,CvScalar(255))
		# calculate size and number of tiles to place for the active region
		regionW = VV.Window.Regions.Active.Width
		regionH = VV.Window.Regions.Active.Height
		regionLeft = VV.Window.Regions.Active.Left
		regionTop = VV.Window.Regions.Active.Top
		tileWidth = float(VV.Acquire.XDimension) * bin * magnificationRatio
		tileHeight = float(VV.Acquire.YDimension) * bin * magnificationRatio
		overlapWidth = tileWidth * overlap
		overlapHeight = tileHeight * overlap
		reducedTileWidth = tileWidth-overlapWidth
		reducedTileHeight = tileHeight-overlapHeight
		nTilesX = math.ceil((regionW-overlapWidth) / reducedTileWidth)
		nTilesY = math.ceil((regionH-overlapHeight) / reducedTileHeight)
		overhangX = (nTilesX * (reducedTileWidth) + overlapWidth) - regionW
		overhangY = (nTilesY * (reducedTileHeight) + overlapHeight) - regionH
		startLeft = max(regionLeft - (overhangX/2), 0)
		startTop = max(regionTop - (overhangY/2), 0)

		# return all possible tiles
		imgTiles = []
		if VV.Window.Regions.Active.Type == 'PolyLine':
			for p in range(points-1):
				dist = math.sqrt(math.pow(CoordX[p+1]-CoordX[p],2)+math.pow(CoordY[p+1]-CoordY[p],2))
				angleCOS = (CoordX[p+1]-CoordX[p])/dist
				angleSIN = (CoordY[p+1]-CoordY[p])/dist
				startX = CoordX[p]-tileWidth/2
				startY = CoordY[p]-tileWidth/2
				currentTile = CvRect(startX, startY, tileWidth, tileHeight)
				jump = False
				for ti in imgTiles:
					if (((startX+tileWidth/2>=ti.Left) & (startX+tileWidth/2<=ti.Left+ti.Width)) & ((startY+tileHeight/2>=ti.Top) & (startY+tileHeight/2<=ti.Top+ti.Height))):
						jump = True
						startX = startX - reducedTileWidth*angleCOS/3
						startY = startY - reducedTileWidth*angleSIN/3
						continue
				if jump == False:
					imgTiles.append(currentTile)

				for j in range(int(dist/reducedTileWidth)):
					startX = startX + reducedTileWidth*angleCOS
					startY = startY + reducedTileWidth*angleSIN
					jump = False
					for ti in imgTiles:
						if (((startX+tileWidth/2>=ti.Left) & (startX+tileWidth/2<=ti.Left+ti.Width)) & ((startY+tileHeight/2>=ti.Top) & (startY+tileHeight/2<=ti.Top+ti.Height))):
							jump = True
					if jump == True:
						continue
					else:
						currentTile = CvRect(startX, startY, tileWidth, tileHeight)
						imgTiles.append(currentTile)

		else:
			imageWidth = binaryMask.Width
			imageHeight = binaryMask.Height
			for col in range(int(nTilesX)):
				for row in range(int(nTilesY)):
					tLeft = startLeft + col * (reducedTileWidth)
					tTop = startTop + row * (reducedTileHeight)
					currentTile = CvRect(tLeft, tTop, min(tileWidth, imageWidth-tLeft), min(tileHeight, imageHeight-tTop))
					# Crop binary mask to current rectangle
					dummy, croppedMask = binaryMask.GetSubRect(currentTile)
					# Measure max value of cropped rectangle
					minValue = clr.Reference[float]()
					maxValue = clr.Reference[float]()
					Cv.MinMaxLoc(croppedMask,minValue,maxValue)
					# filter tiles according to actual polygon area
					if(int(maxValue) == 255):
						imgTiles.append(currentTile)

		# Return results
		return imgTiles

def saveTileList(roiNumber, baseDir, baseName, imgCentersX, imgCentersY, imgFocusPoints):
	stageListFile = os.path.join(baseDir, baseName + "_Region-" + str(roiNumber) + "_nTiles-" + str(len(imgCentersX)).zfill(3)+"_"+".stg")
	target = open(stageListFile, 'w')
	# csvWriter = csv.writer(target)
	target.write("\"Stage Memory List\", Version 5.0\n0, 0, 0, 0, 0, 0, 0, \"microns\", \"microns\"\n0\n"+str(len(imgCentersX))+"\n")
	for i in range(len(imgCentersX)):
		x,y = VV.File.ConvertImageCoordinatesToStageCoordinates(imgCentersX[i], imgCentersY[i])
		text = "\"Position"+str(i+1)+"\", "+("%.3f" % x)+", "+("%.3f" % y)+", "+("%.3f" % imgFocusPoints[i])+", 0, 0, FALSE, -9999, TRUE, TRUE, 0, -1, \"\"\n"
		target.write(text)
	target.close()

	return(stageListFile)


def configDialog():
	tempDir = os.getenv("TEMP")
	doReUse = False
	doReUse2 = False
	condition = False
	listSTGfiles = []
	baseN = VV.Acquire.Sequence.BaseName
	if baseN.endswith('_'):
		baseN = baseN[:-1]
	onlyFiles = [f for f in os.listdir(VV.Acquire.Sequence.Directory) if os.path.isfile(os.path.join(VV.Acquire.Sequence.Directory, f))]
	for f in onlyFiles:
		if (f.split(".")[1:][0] == "stg") & (f.split(".")[0].startswith(baseN)==1):
			listSTGfiles.append(f)
			condition = True
	emailAdresse = EmailToolbox.createEmailAddress(EmailToolbox.getUserLogged())
	VV.Macro.InputDialog.Initialize("Experiment parameters.    (C)2017. J. Eglinger & L. Gelman, FAIM - FMI", True)
	VV.Macro.InputDialog.AddStringVariable("Basename", "basename", VV.Acquire.Sequence.BaseName)
	VV.Macro.InputDialog.AddStringVariable("E-mail address", "mailAdresse", emailAdresse)
	if os.path.exists(os.path.join(tempDir, 'TmpFocusImage.tif')):
		VV.Macro.InputDialog.AddBoolVariable("Re-use focus map?", "reusefocusmap", False)
	if (condition == True):
		VV.Macro.InputDialog.AddBoolVariable("Re-use Saved Lists of Positions?", "reusePositions", False)
	VV.Macro.InputDialog.Width=450
	VV.Macro.InputDialog.Show()

	if os.path.exists(os.path.join(tempDir, 'TmpFocusImage.tif')):
		doReUse = reusefocusmap
	if condition == True:
		doReUse2 = reusePositions

	return (basename[:-1] if basename.endswith('_') else basename), doReUse, doReUse2, listSTGfiles, mailAdresse


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


def restoreFocusPositions():
	tempDir = os.getenv("TEMP")
	posList = tempDir + "\\PositionList.stg"
	if os.path.isfile(posList):
		VV.Acquire.Stage.PositionList.Load(posList)


def restoreRegions(regionFileName):
	VV.Edit.Regions.Load(regionFileName)

def reopenOverviewImage():
	path = GetGlobalVar('ch.fmi.VV.lastOverview')
	return VV.File.Open(path)

def writeTileConfig(baseDir, stgFile, baseName, cal):
	# parse stg file
	f = open(os.path.join(baseDir,stgFile))
	tcFile = open(os.path.join(baseDir, baseName + "_TileConfiguration.txt"), "w")
	dim = "3" if VV.Acquire.Z.Series else "2"

	tcFile.write("# Define the number of dimensions we are working on\n")
	tcFile.write("dim = " + dim + "\n")
	tcFile.write("multiseries = true\n")
	tcFile.write("# Define the image coordinates\n")

	reader = csv.reader(f)
	for i in range(4):
		reader.next()
	j=0
	for row in reader:
		lineString = baseName + ".nd; " + str(j) + "; (" + str(float(row[1])/cal) + " ," + str(float(row[2])/cal)
		lineString += ", 0)\n" if dim == "3" else ")\n"
		tcFile.write(lineString)
		j += 1
	f.close()
	tcFile.close()

def initializeUI():
	# Clear and show Print Window
	VV.Macro.PrintWindow.Clear()
	VV.Macro.PrintWindow.IsVisible = True

	# Move and resize overview window
	VV.Window.Selected.Top = 10
	VV.Window.Selected.Left = 10
	VV.Window.Selected.Height = ctypes.windll.user32.GetSystemMetrics(1)/3

	# Make sure Save Sequence to Disk is checked
	VV.Acquire.Sequence.SaveToDisk = True

	# Switch to PositionList in Acquire/Stage
	VV.Acquire.Stage.SeriesType = 'PositionList'

def getStgFileList(overviewHandle, stgFileList, baseName, baseDir, reuseFocusMap, reusePositions, cal, cX, cY, cZ, magnificationRatio, bin):
	if reusePositions:
		return stagePosDialog(stgFileList)
	else:
		stgFileList = []
		overviewName = VV.File.Info.Name
		if not overviewName.endswith("_OVERVIEW.tif"):
			overviewName = os.path.join(baseDir, baseName+'_OVERVIEW.tif')
			VV.File.SaveAs(overviewName, True)
		SetGlobalVar('ch.fmi.VV.lastOverview', overviewName)

		# Unselect regions
		regionFileName = "MultiTileRegion.rgn"
		VV.Edit.Regions.Save(regionFileName)
		# VV.Window.Regions.Active.Index = VV.Window.Regions.Count + 1
		# will have to be replaced by
		VV.Window.Regions.Active.IsValid = False


		#Test size of region and delete it if too small. this is to avoid empty position lists afterwards
		for r in range(VV.Window.Regions.Count,0,-1):
			VV.Window.Regions.Active.Index = r
			regionSize = VV.Window.Regions.Active.Width * VV.Window.Regions.Active.Height
			if regionSize <= 150:
				VV.Window.Regions.Active.Remove()
		VV.Edit.Regions.Save(regionFileName)

		# Create an image with the numbers of the regions
		VV.Window.Active.Handle = overviewHandle
		VV.Window.Selected.Handle = overviewHandle
		VV.Window.Regions.Active.IsValid = False
		he = VV.Image.Height
		wi = VV.Image.Width
		VV.Process.DuplicatePlane()
		VV.File.Info.Name = "Region Identification in "+baseName

		zoom = VV.Window.Selected.ZoomPercent
		imageWithRegion = CvMat(he,wi,MatrixType.U16C1)
		imageWithRegion.Set(CvScalar(0))
		restoreRegions(regionFileName)
		polyLines = Array.CreateInstance(Array[CvPoint], 1)

		for r in range(VV.Window.Regions.Count,0,-1):
			VV.Window.Regions.Active.Index = r
			points, CoordX, CoordY = VV.Window.Regions.Active.CoordinatesToArrays()
			font = CvFont(FontFace.Italic,int(16/(int(zoom/100*2)+1)),1)
			font.Thickness = int(16/((int(zoom/100*2)+1)))
			imageWithRegion.PutText(str(r), CvPoint(CoordX[0]-5,CoordY[0]-5), font, CvScalar(65000))
			polyLine = Array.CreateInstance(CvPoint, len(CoordX))
			for i in range(len(CoordX)):
				polyLine[i] = CvPoint(CoordX[i],CoordY[i])
			polyLines[0] = polyLine
			VV.Window.Regions.Active.Index = r
			if VV.Window.Regions.Active.Type=='PolyLine':
				imageWithRegion.DrawPolyLine(polyLines, False, CvScalar(30000),int(16/((int(zoom/100*2)+1))))
			else:
				imageWithRegion.DrawPolyLine(polyLines, True, CvScalar(30000),int(16/((int(zoom/100*2)+1))))

		VV.Image.WriteFromPointer(imageWithRegion.Data, he, wi)
		VV.Edit.Regions.ClearAll()
		VV.Window.Selected.Top = ctypes.windll.user32.GetSystemMetrics(1)/3 + 20
		VV.Window.Selected.Left = 10
		VV.Window.Selected.Width=ctypes.windll.user32.GetSystemMetrics(0)/4

		path = os.path.join(baseDir, baseName+'_regions.tif')
		VV.File.SaveAs(path, True)
		regionImageHandle = VV.Window.GetHandle.Active

		# Create Focus Map
		VV.Window.Active.Handle = overviewHandle
		VV.Window.Regions.Active.IsValid = False
		scale = int((he/512+wi/512)/4)+1
		SetGlobalVar('ch.fmi.VV.scale', scale)
		if not reuseFocusMap:
			heightImage = generateHeightImage(int(VV.Image.Width/scale), int(VV.Image.Height/scale), cal*scale, cX, cY, cZ)
			focusMin = float(min(cZ))
			focusMax = float(max(cZ))
			displayHeightImage(heightImage, focusMin, focusMax, regionFileName, scale, int(VV.Image.Width/scale), int(VV.Image.Height/scale))
			saveHeightImage(VV.Window.Active.Handle, focusMin, focusMax)
		else:
			# load image, get data as CvMat, un-normalize with min and max
			heightImage = loadHeightImage()
		focusImageHandle = VV.Window.Selected.Handle
		VV.Window.Selected.Top = ctypes.windll.user32.GetSystemMetrics(1)/3 +60
		VV.Window.Selected.Left = 30
		VV.Window.Selected.Width=ctypes.windll.user32.GetSystemMetrics(0)/4

		# TODO take care of regions and active image
		VV.Window.Active.Handle = overviewHandle
		VV.Window.Selected.Handle = overviewHandle

		# Create binary mask (CvMat) with all regions
		binaryMask = CvMat(VV.Image.Height, VV.Image.Width, MatrixType.U8C1)
		binaryMask.Set(CvScalar(0))
		VV.Edit.Regions.ClearAll()
		VV.Edit.Regions.Load(regionFileName)
		print ("Number of regions = "+str(VV.Window.Regions.Count))
		for r in range(VV.Window.Regions.Count):
			VV.Window.Selected.Handle = overviewHandle
			VV.Edit.Regions.ClearAll()
			VV.Edit.Regions.Load(regionFileName)
			currentTiles = getAcquisitionTiles(r+1, binaryMask, bin, magnificationRatio, heightImage)
			VV.Edit.Regions.ClearAll()

			for tile in currentTiles:
				VV.Window.Regions.AddCentered("Rectangle", tile.X+tile.Width/2, tile.Y+tile.Height/2, tile.Width, tile.Height)

			VV.Macro.MessageBox.ShowAndWait("Please Adjust Tiles for region "+str(r+1), "Tile Adjustment", False)

			# Adjust calculated tiles
			imgFocusPoints = []
			imgCentersX = []
			imgCentersY = []

			for t in range(VV.Window.Regions.Count):
					VV.Window.Regions.Active.Index = t+1
					left = VV.Window.Regions.Active.Left
					leftscaled = int(VV.Window.Regions.Active.Left/scale)
					width = VV.Window.Regions.Active.Width
					widthscaled = int(VV.Window.Regions.Active.Width/scale)
					top = VV.Window.Regions.Active.Top
					topscaled = int(VV.Window.Regions.Active.Top/scale)
					height = VV.Window.Regions.Active.Height
					heightscaled = int(VV.Window.Regions.Active.Height/scale)
					imgCentersX.append(left+width/2)
					imgCentersY.append(top+height/2)
					dummy, focusTile = heightImage.GetSubRect(CvRect(leftscaled, topscaled, widthscaled, heightscaled))
					imgFocusPoints.append(focusTile.Avg().Val0)

			stgFileList.append(saveTileList(r+1, baseDir, baseName, imgCentersX, imgCentersY, imgFocusPoints))
			
		VV.Window.Selected.Handle = overviewHandle
		restoreRegions(regionFileName)
	# return results	
	return regionImageHandle, focusImageHandle, stgFileList

# *************************************************************************************
# 										MAIN
# *************************************************************************************
def main():

	# Initialization
	initializeUI()
	overviewHandle = VV.Window.GetHandle.Active

	cal = VV.Image.Calibration.Value
	cX, cY, cZ = parsePositions()
	magnificationRatio = float(VV.Magnification.Calibration.Value)/float(VV.Image.Calibration.Value)
	bin = VV.Acquire.Binning

	reuseFocusMap = False
	reusePositions = False
	baseDir = VV.Acquire.Sequence.Directory
	stgFileList = []
	mailText = ""

	baseName, reuseFocusMap, reusePositions, stgFileList, mailAdresse = configDialog()
	VV.Acquire.Sequence.BaseName = baseName
	origBaseName = baseName
	regionImageHandle, focusImageHandle, stgFileList = getStgFileList(overviewHandle, stgFileList, baseName, baseDir, reuseFocusMap, reusePositions, cal, cX, cY, cZ, magnificationRatio, bin)

	# *************************************************************************************
	# Start Acquisition
	# *************************************************************************************

	VV.Window.Active.Handle = overviewHandle
	timeStart = datetime.datetime.now()
	print (timeStart.strftime("\nExperiment started at %H:%M:%S"))

	VV.Macro.MessageBox.ShowAndWait("Please check parameters in the Acquire window (i.e. z-stack and multi-wavelengths options)", "Check...", False)

	# Close Region ID Image
	try:
		VV.Window.Selected.Handle = regionImageHandle
		VV.Window.Selected.Close(False)
	except:
		pass
	# Close Focus Image
	try:
		VV.Window.Selected.Handle = focusImageHandle
		VV.Window.Selected.Close(False)
	except:
		pass

	numberTilesEachRegion = []
	for stgFile in (stgFileList):
		index = stgFile.find("_nTiles-")+8
		numberTilesEachRegion.append(int(stgFile[index:-len(stgFile)+index+3]))
		#read from name the number of tiles in each region formated as 3digit number

	for count, stgFile in enumerate(stgFileList):
		"""
		Estimate time for acquisition of all regions based on time elapsed for region 0
		"""
		if count == 1:
			timeFirstRegion = datetime.datetime.now()
			diff = timeFirstRegion - timeStart
			timeAcquisitionFirstRegion = diff.total_seconds()
			if numberTilesEachRegion[0] != 0:
				timePerTile = timeAcquisitionFirstRegion / numberTilesEachRegion[0]
			else:
				timePerTile = timeAcquisitionFirstRegion
				print ("Times could not be calculated since number of tiles is not known")
			print ("\n______________________\n")
			for k in range(len(numberTilesEachRegion)):
				myString1 = "Time to acquire region "+str(k+1)+" (containing "+str(numberTilesEachRegion[k])+" tiles) = "+str(int(timePerTile*numberTilesEachRegion[k]))+" sec"
				if numberTilesEachRegion[0] == 0:
					numberTilesEachRegion[0] = 1
				timeStart = timeStart + diff/numberTilesEachRegion[0]*numberTilesEachRegion[k]
				myString2 = ""
				if k>0:
					myString2 = ("  => Region "+str(k+1)+" will finish at "+timeStart.strftime("%H:%M:%S"))
					print(myString2)
				mailText=mailText+myString1+"\n"+myString2+"\n"
			print ("______________________\n")

			InfoMail = EmailToolbox.Email(destin = mailAdresse, title = "Acquisition Schedule", message = mailText)
			InfoMail.send()

		# Acquire tiles
		VV.Acquire.Stage.PositionList.Load(os.path.join(baseDir,stgFile))
		m = re.match(r'.*\\([^\\]+).stg', os.path.join(baseDir,stgFile))
		baseName = m.group(1)
		VV.Acquire.Sequence.BaseName = baseName
		print ("\nNow acquiring " + baseName +"...")
		VV.Acquire.Sequence.Start()
		VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
		VV.Window.Selected.Handle = VV.Window.Active.Handle

		ndBaseName = VV.File.Info.NameOnly
		ndBaseName = ndBaseName[0:ndBaseName.rfind('_')]
		newCalibration = VV.Magnification.Calibration.Value
		writeTileConfig(baseDir, stgFile, ndBaseName, newCalibration * bin)

		VV.Window.Selected.Close(False)
		# close image windows after acquisition


	FinalMail = EmailToolbox.Email(destin = mailAdresse, title = "Acquisition finished", message = "All regions have been acquired")
	FinalMail.send()
	VV.Acquire.Sequence.BaseName = origBaseName
	restoreFocusPositions()


try:
	main()
except KeyboardInterrupt:
	restoreFocusPositions()
	handle = reopenOverviewImage()
	#VV.Macro.Control.Delay(100, 'ms')
	regionFileName = "MultiTileRegion.rgn"
	VV.Window.Selected.Handle = VV.Window.GetHandle.Active
	restoreRegions(regionFileName)
	pass
#except StandardError:
#	pass

