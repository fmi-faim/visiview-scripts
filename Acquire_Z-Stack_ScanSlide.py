
"""
Laurent Gelman & Jan Eglinger
Friedrich Miescher Institute for Biomedical Research
Jan-2017
"""

import os, sys
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\Examples\Image Access\OpenCV\Library")
vvimport('OpenCV')

# Save the list of postions in ImageJ format for stitching
def saveTileList(baseDir, baseName, fileNames, xPos, yPos, nChannels):
	stageListFile = os.path.join(baseDir, baseName + "_TileConfig.txt")
	target = open(stageListFile, 'w')
	dimNumber = 2
	lineEnd = ")\n"
	fileExtension = "tif"
	if VV.Acquire.Z.Series == True:
		dimNumber = 3
		lineEnd = ", 0)\n"
		fileExtension = "stk"
		
	target.write("# Define the number of dimensions we are working on\ndim = "+str(dimNumber)+"\n\n# Define the image coordinates\n")
	
	count = 0
	print (len(xPos))
	print (len(yPos))
	
	if nChannels>=2:
		VV.Acquire.WaveLength.Current = 1
		subNameString = "_w1"+VV.Acquire.WaveLength.Illumination
	else:
		subNameString = "_"+VV.Acquire.WaveLength.Illumination

	for x in range(len(xPos)):
		textImageJ = fileNames[count]+ subNameString +"." + fileExtension + "; ; ("+("%.3f" % xPos[count])+", "+("%.3f" % yPos[count])+lineEnd
		print (textImageJ)
		target.write(textImageJ)
		count = count + 1
	target.close()


# Acquire the images at calculated stage positions
def acquire(xTiles, yTiles,  xPixels, yPixels, binning, cal, areaTopLeftX, areaTopLeftY, totalSizeX, totalSizeY, resultImages, overviewWindows):

	# Create arrays of X,Y postions
	xPos = []
	yPos = []
	fileNames = []
	
	# loop through X and Y dimensions to acquire tiles
	for i in range(xTiles):
		for j in range(yTiles):
		
			VV.Stage.XPosition = areaTopLeftX + (0.5 * xPixels * binning * cal) + (i * xPixels * binning * cal * 0.9)
			VV.Stage.YPosition = areaTopLeftY + (0.5 * yPixels * binning * cal) + (j * yPixels * binning * cal * 0.9)

			channelWindows = []

			# ***** ACQUISITION START *****
			VV.Macro.Control.WaitFor('VV.Stage.IsMoving', "==", False)
			fileNames.append(VV.Acquire.Sequence.NextBaseName)
			VV.Acquire.Sequence.Start()

			# Get all aquisition windows as they appear
			for ch,_ in enumerate(overviewWindows):
				currentWindow = VV.Window.GetHandle.Empty
				while VV.Window.GetHandle.CheckIfEmpty(currentWindow):
					currentWindow = VV.Window.GetHandle.Acquire(ch+1)
				channelWindows.append(currentWindow)

			VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
			# ***** ACQUISITION END *****

			xPos.append(i * xPixels*0.9)
			yPos.append(j * yPixels*0.9)
				
			# Select each channel, do MIP, add to respective resultImage
			for index, currentChannel in enumerate(channelWindows):
				VV.Window.Selected.Handle = currentChannel;
				VV.Process.StackArithmetic('StackMaximum','ProcessOverzfocus')

				# Create CvMat image of same dimensions
				tmpMIP = CvMat(yPixels, xPixels, MatrixType.U16C1)
				tmpCopy = CvMat(totalSizeY, totalSizeX, MatrixType.U16C1)
				VV.Image.ReadToPointer(tmpMIP.Data)
				VV.Window.Selected.Close(False)
				offset = CvPoint(i * xPixels*0.9, j * yPixels*0.9)
				tmpMIP.CopyMakeBorder(tmpCopy, offset, 0)
				resultImages[index].Max(tmpCopy, resultImages[index])
				VV.Window.Selected.Handle = currentChannel
				VV.Window.Selected.Close(False)

				VV.Window.Selected.Handle = overviewWindows[index]
				VV.Image.WriteFromPointer(resultImages[index].Data, totalSizeY, totalSizeX)

	return xPos, yPos, fileNames



def main():

	VV.Macro.PrintWindow.Clear()

	# Initialize
	VV.Macro.PrintWindow.Clear()
	VV.Acquire.Stage.Series = False
	baseName = VV.Acquire.Sequence.BaseName
	baseDir = VV.Acquire.Sequence.Directory
	
	# Retrieve information about tile experiment
	areaTopLeftX = VV.Acquire.Stage.ScanSlide.Area.UpperLeft.X
	areaTopLeftY = VV.Acquire.Stage.ScanSlide.Area.UpperLeft.Y
	areaLowerRightX = VV.Acquire.Stage.ScanSlide.Area.LowerRight.X
	areaLowerRightY = VV.Acquire.Stage.ScanSlide.Area.LowerRight.Y

	# Retrieve information about frame and calibration
	xPixels = VV.Acquire.XDimension
	yPixels = VV.Acquire.YDimension
	binning = VV.Acquire.Binning
	cal = VV.Magnification.Calibration.Value

	# Calculate number of tiles
	xTiles = int(round((areaLowerRightX-areaTopLeftX)/cal/binning/xPixels))
	yTiles = int(round((areaLowerRightY-areaTopLeftY)/cal/binning/yPixels))

	# Calculate size of final stitched image and display empty image
	totalSizeX = xPixels * 0.9 * xTiles + xPixels * 0.1
	totalSizeY = yPixels * 0.9 * yTiles + yPixels * 0.1

	# Get number of channels
	if VV.Acquire.WaveLength.Series:
		nChannels = VV.Acquire.WaveLength.Count
	else:
		nChannels = 1
		currentIlluminationName = VV.Acquire.WaveLength.Illumination
		VV.Acquire.WaveLength.Current = 1
		VV.Acquire.WaveLength.Illumination = currentIlluminationName

	resultImages = []
	overviewWindows = []
	for ch in range(nChannels):
		resultImage = CvMat(totalSizeY, totalSizeX, MatrixType.U16C1)
		resultImage.Set(CvScalar(0))
		newWindow = VV.Process.CreateEmptyPlane('Monochrome16', totalSizeX, totalSizeY)
		VV.Acquire.WaveLength.Current = ch+1			
		VV.File.Info.Name = VV.File.Info.Name + "_MIP_" + VV.Acquire.WaveLength.Illumination
		overviewWindows.append(newWindow)
		VV.Image.WriteFromPointer(resultImage.Data, totalSizeY, totalSizeX)
		resultImages.append(resultImage)

	# Acquire tiles
	xPos, yPos, fileNames = acquire(xTiles, yTiles, xPixels, yPixels, binning, cal, areaTopLeftX, areaTopLeftY, totalSizeX, totalSizeY, resultImages, overviewWindows)
	
	# Save TileConfig file
	if VV.Acquire.Sequence.SaveToDisk:
		saveTileList(baseDir, baseName, fileNames, xPos, yPos, nChannels)
	
	# Re-activate series option
	VV.Acquire.Stage.Series = True
	

try:
	main()
except KeyboardInterrupt:
	# Re-activate series option
	VV.Acquire.Stage.Series = True

