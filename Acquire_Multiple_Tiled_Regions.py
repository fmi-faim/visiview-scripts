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


def saveHeightImage(folder, heightImageHandle, focusMin, focusMax):
	# the global variables focusmin and focumax are used to display the focus map image with stretched histogram values.
	SetGlobalVar('ch.fmi.VV.focusMin', focusMin)
	SetGlobalVar('ch.fmi.VV.focusMax', focusMax)
	# select and save the focus map image
	VV.Window.Selected.Handle = heightImageHandle
	VV.File.SaveAs(os.path.join(folder, 'FocusImage.tif'), True)


def loadHeightImage(folder):
	# the global variables focusmin and focumax are used to display the focus map image with stretched histogram values.
	focusMin = GetGlobalVar('ch.fmi.VV.focusMin')
	focusMax = GetGlobalVar('ch.fmi.VV.focusMax')
	# open the image and create a CVmat matrix with the instensity values
	VV.File.Open(os.path.join(folder, 'FocusImage.tif'))
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
	
	# deals with polyline
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
	# otherwise, if regions is closed...
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


def saveTileList(roiNumber, folder, baseName, imgCentersX, imgCentersY, imgFocusPoints):
	stageListFile = os.path.join(folder, baseName + "_Region-" + str(roiNumber) + "_nTiles-" + str(len(imgCentersX)).zfill(3)+"_"+".stg")
	target = open(stageListFile, 'w')
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
	emailAdresse = EmailToolbox.createEmailAddress(EmailToolbox.getUserLogged())
	baseN = VV.Acquire.Sequence.BaseName
	# removing the underscore avoids bugs later in the acquisition and stitching workflow
	if baseN.endswith('_'):
		baseN = baseN[:-1]
	# check whether position list files (*.stg) for this specific overview exist already
	onlyFiles = [f for f in os.listdir(VV.Acquire.Sequence.Directory) if os.path.isfile(os.path.join(VV.Acquire.Sequence.Directory, f))]
	for f in onlyFiles:
		if (f.split(".")[1:][0] == "stg") & (f.split(".")[0].startswith(baseN)==1):
			listSTGfiles.append(f)
			condition = True
	# create a dialog window
	VV.Macro.InputDialog.Initialize("Experiment parameters.    (C)2017. J. Eglinger & L. Gelman, FAIM - FMI", True)
	VV.Macro.InputDialog.AddStringVariable("E-mail address", "mailAdresse", emailAdresse)
	VV.Macro.InputDialog.AddBoolVariable("Re-use focus map?", "reusefocusmap", False)
	VV.Macro.InputDialog.AddBoolVariable("Re-use Saved Lists of Positions?", "reusePositions", False)
	VV.Macro.InputDialog.Width=450
	VV.Macro.InputDialog.Show()
	# return results
	return reusefocusmap, reusePositions, listSTGfiles, mailAdresse


def stagePosDialog(listSTGfiles):
	myList = [] # will contain the postion list files
	global myVar
	myVar = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
	# create a dialog window with a check list of all stage position list files (.stg files) found in the folder
	VV.Macro.InputDialog.Initialize("Select position lists", True)
	for i in range(len(listSTGfiles)):
		VV.Macro.InputDialog.AddBoolVariable(listSTGfiles[i], "myVar["+str(i)+"]", False)
	VV.Macro.InputDialog.Show()
	# create an array with all selected files
	for i in range(len(listSTGfiles)):
		if myVar[i]:
			myList.append(listSTGfiles[i])
	# return list of stage position files which will be directly used for acquisition		
	return myList


def restoreFocusPositions(folder): # loads back the positions entered to calculate the focus map
	path = os.path.join(folder, "PositionListForFocusMap.stg")
	if os.path.isfile(path):
		VV.Acquire.Stage.PositionList.Load(path)


def restoreRegions(regionFileName):
	VV.Edit.Regions.Load(regionFileName)


def writeTileConfig(folder, stgFile, baseName, cal): #creates a txt file with the list of postions for stitching in Fiji
	# open the list of positions in stgFile as f, and create a TileConfiguration file for imageJ as tcFile
	f = open(os.path.join(folder,stgFile))
	tcFile = open(os.path.join(folder, baseName + "_TileConfiguration.txt"), "w")
	# dimension (2D versus 3D stacks) must be specified for imageJ stitcher
	dim = "3" if VV.Acquire.Z.Series else "2"
	# write headers in tcFile
	tcFile.write("# Define the number of dimensions we are working on\n")
	tcFile.write("dim = " + dim + "\n")
	tcFile.write("multiseries = true\n")
	tcFile.write("# Define the image coordinates\n")
	# skip 4 first lines in document
	reader = csv.reader(f)
	for i in range(4):
		reader.next()
	# parse information from Visiview into a file with a Fiji-readable structure
	j=0
	for row in reader:
		lineString = baseName + ".nd; " + str(j) + "; (" + str(float(row[1])/cal) + " ," + str(float(row[2])/cal)
		lineString += ", 0)\n" if dim == "3" else ")\n"
		tcFile.write(lineString)
		j += 1
	# close f and tcFile files
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


def getStgFileList(overviewHandle, stgFileList, baseName, dataFolder, infoFolder, reuseFocusMap, reusePositions, cal, cX, cY, cZ, magnificationRatio, bin):
	if reusePositions:
		return stagePosDialog(stgFileList)
	else:
		stgFileList = []
		# Save all regions and then unselect 
		regionFileName = "MultiTileRegion.rgn"
		VV.Edit.Regions.Save(regionFileName)
		VV.Window.Regions.Active.IsValid = False
		#Test size of region and delete it if too small. this is to avoid empty position lists afterwards
		for r in range(VV.Window.Regions.Count,0,-1):
			VV.Window.Regions.Active.Index = r
			regionSize = VV.Window.Regions.Active.Width * VV.Window.Regions.Active.Height
			if regionSize <= 150:
				VV.Window.Regions.Active.Remove()
		VV.Edit.Regions.Save(regionFileName)
		# Create an overview black image with the regions numbered
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
			if VV.Window.Regions.Active.Type=='PolyLine':
				imageWithRegion.DrawPolyLine(polyLines, False, CvScalar(30000),int(16/((int(zoom/100*2)+1))))
			else:
				imageWithRegion.DrawPolyLine(polyLines, True, CvScalar(30000),int(16/((int(zoom/100*2)+1))))

		VV.Image.WriteFromPointer(imageWithRegion.Data, he, wi)
		VV.Edit.Regions.ClearAll()
		path = os.path.join(infoFolder, baseName+'_regions.tif')
		VV.File.SaveAs(path, True)
		#regionImageHandle = VV.Window.GetHandle.Active
		VV.Window.Selected.Close(False)

		# Create Focus Map
		VV.Window.Selected.Handle = overviewHandle
		VV.Window.Active.Handle = overviewHandle
		VV.Window.Regions.Active.IsValid = False
		scale = int((he/512+wi/512)/4)+1
		SetGlobalVar('ch.fmi.VV.scale', scale)
		if not reuseFocusMap:
			heightImage = generateHeightImage(int(VV.Image.Width/scale), int(VV.Image.Height/scale), cal*scale, cX, cY, cZ)
			focusMin = float(min(cZ))
			focusMax = float(max(cZ))
			displayHeightImage(heightImage, focusMin, focusMax, regionFileName, scale, int(VV.Image.Width/scale), int(VV.Image.Height/scale))
			saveHeightImage(infoFolder, VV.Window.Active.Handle, focusMin, focusMax)
			VV.Window.Selected.Close(False)
		else:
			# load image, get data as CvMat, un-normalize with min and max
			heightImage = loadHeightImage(infoFolder)

		# Select the overview image
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
			# get the coordinates of the re-positioned or newly created regions and saves them in an array
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
			# saves coordinates list / array for acquisition
			stgFileList.append(saveTileList(r+1, dataFolder, baseName, imgCentersX, imgCentersY, imgFocusPoints))
			
		VV.Window.Selected.Handle = overviewHandle
		restoreRegions(regionFileName)

	# return results	
	return stgFileList


# ***************
# MAIN Function

def main():

	try:
		origBaseName = VV.Acquire.Sequence.BaseName
		origBaseDir = VV.Acquire.Sequence.Directory
		baseName = VV.Acquire.Sequence.BaseName
		dataDir = os.path.join(origBaseDir, baseName + datetime.datetime.now().strftime("_%Y-%m-%d_%H-%M"))
		infoDir = os.path.join(dataDir, "Tile_Info")
		os.mkdir(dataDir)
		os.mkdir(infoDir)
		VV.Acquire.Sequence.Directory = dataDir
		# Initialization
		initializeUI()
		overviewHandle = VV.Window.GetHandle.Active
		VV.File.SaveAs(os.path.join(infoDir, "Overview.tif"), True)
		VV.Edit.Regions.Save(os.path.join(infoDir, "Regions.rgn"))
		# The list of positions entered to create the focus map is parsed into 3 arrays containing the X, Y, and Z coordinates
		cX, cY, cZ = parsePositions(infoDir)
		# get Magnification, binning and ratio between overview acquisition and small tiles acquisition 
		magnificationRatio = float(VV.Magnification.Calibration.Value)/float(VV.Image.Calibration.Value)
		bin = VV.Acquire.Binning
		cal = VV.Image.Calibration.Value
		# initialisation of variables
		reuseFocusMap = False
		reusePositions = False
		stgFileList = []
		mailText = ""

		# get information from user about tile experiment
		reuseFocusMap, reusePositions, stgFileList, mailAdresse = configDialog()

		stgFileList = getStgFileList(overviewHandle, stgFileList, baseName, dataDir, infoDir, reuseFocusMap, reusePositions, cal, cX, cY, cZ, magnificationRatio, bin)
	
		# last user warning before start.
		VV.Macro.MessageBox.ShowAndWait("Please check parameters in the Acquire window (i.e. z-stack and multi-wavelengths options)", "Check...", False)

		# read from name the number of tiles in each region formated as 3digit number
		numberTilesEachRegion = []
		for stgFile in (stgFileList):
			index = stgFile.find("_nTiles-")+8
			numberTilesEachRegion.append(int(stgFile[index:-len(stgFile)+index+3]))

		# start Acquisition per se
		# record starting time for further estiomation of full acquisition time
		timeStart = datetime.datetime.now()
		print (timeStart.strftime("\nExperiment started at %H:%M:%S"))
		# loop through all regions and acquires tiles
		for count, stgFile in enumerate(stgFileList):
			if count == 1: # estimate time for acquisition of all regions based on time elapsed for region 0 (code runs aonly once)
				timeFirstRegion = datetime.datetime.now()
				diff = timeFirstRegion - timeStart
				timeAcquisitionFirstRegion = diff.total_seconds()
				timePerTile = timeAcquisitionFirstRegion / numberTilesEachRegion[0]
				print ("\n____________\nInformation about duration of regions acquisition")
				for k in range(len(numberTilesEachRegion)):
					myString1 = "Time to acquire region "+str(k+1)+" (containing "+str(numberTilesEachRegion[k])+" tiles) = "+str(int(timePerTile*numberTilesEachRegion[k]))+" sec"
					if numberTilesEachRegion[0] == 0:
						numberTilesEachRegion[0] = 1
					timeStart = timeStart + diff/numberTilesEachRegion[0]*numberTilesEachRegion[k]
					myString2 = ""
					if k>0:
						myString2 = (" - Region "+str(k+1)+" will finish at "+timeStart.strftime("%H:%M:%S"))
						print(myString2)
					mailText=mailText+myString1+"\n"+myString2+"\n"
				# send an e-mail with information about all region scan duration to user
				InfoMail = EmailToolbox.Email(destin = mailAdresse, title = "Acquisition Schedule", message = mailText)
				InfoMail.send()
			# Acquire module per se
			VV.Acquire.Stage.PositionList.Load(os.path.join(dataDir,stgFile))
			m = re.match(r'.*\\([^\\]+).stg', os.path.join(dataDir,stgFile))
			baseName = m.group(1)
			VV.Acquire.Sequence.BaseName = baseName
			print ("\nNow acquiring " + baseName +"...")
			VV.Acquire.Sequence.Start()
			VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
			VV.Window.Selected.Handle = VV.Window.Active.Handle
		 
			# write the TileConfiguration file for Fiji
#			ndBaseName = VV.File.Info.NameOnly
#			ndBaseName = ndBaseName[0:ndBaseName.rfind('_')]
#			newCalibration = VV.Magnification.Calibration.Value
#			writeTileConfig(dataDir, stgFile, ndBaseName, newCalibration * bin)
		
			# close image windows after acquisition
			VV.Window.Selected.Close(False)
		
		# Send a mail to user, restore original base name and positions for the focus map
		FinalMail = EmailToolbox.Email(destin = mailAdresse, title = "Acquisition finished", message = "All regions have been acquired")
		FinalMail.send()
		VV.Acquire.Sequence.BaseName = origBaseName
		VV.Acquire.Sequence.Directory = origBaseDir
		restoreFocusPositions(infoDir)
		print ("All regions have been acquired...")

	except KeyboardInterrupt:
		restoreFocusPositions(infoDir)
		VV.File.Open(os.path.join(infoDir, "Overview.tif"))
		VV.Window.Selected.Handle = VV.Window.GetHandle.Active
		VV.Edit.Regions.Load(os.path.join(infoDir, "Regions.rgn"))
		VV.Acquire.Sequence.BaseName = origBaseName
		VV.Acquire.Sequence.Directory = origBaseDir
	
	
# ***************
# Launching the code

main()
	
