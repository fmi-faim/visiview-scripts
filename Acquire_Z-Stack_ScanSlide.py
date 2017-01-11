# VisiView Macro
import sys
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\Examples\Image Access\OpenCV\Library")
vvimport('OpenCV')

def acquire(xTiles, yTiles,  xPixels, yPixels, bin, cal, areaTopLeftX, areaTopLeftY, totalSizeX, totalSizeY, resultImage, overview):

	# loop through X and Y dimensions to acquire tiles
	for i in range(xTiles):
		for j in range(yTiles):
			VV.Stage.XPosition = areaTopLeftX + (0.5 * xPixels * bin * cal) + (i * xPixels * bin * cal * 0.9)
			VV.Stage.YPosition = areaTopLeftY + (0.5 * yPixels * bin * cal) + (j * yPixels * bin * cal * 0.9)
			VV.Macro.Control.Delay(500, "ms")
			VV.Acquire.Sequence.Start()
			VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
			
			handleList = VV.Window.GetHandle.List		
			VV.Window.Selected.Handle = handleList[len(handleList)-1]
			MIP = VV.Process.StackArithmetic('StackMaximum','ProcessOverzfocus')
			
			# Create CvMat image of same dimensions
			tmpMIP = CvMat(yPixels, xPixels, MatrixType.U16C1)
			tmpCopy = CvMat(totalSizeY, totalSizeX, MatrixType.U16C1)
			VV.Image.ReadToPointer(tmpMIP.Data)
			VV.Window.Selected.Close(False)
			offset = CvPoint(i * xPixels*0.9, j * yPixels*0.9)
			tmpMIP.CopyMakeBorder(tmpCopy, offset, 0)
			resultImage.Max(tmpCopy, resultImage)
			
			VV.Window.Selected.Handle = handleList[len(handleList)-1]
			VV.Window.Selected.Close(False)
			
			VV.Window.Selected.Handle = overview
			VV.Image.WriteFromPointer(resultImage.Data, totalSizeY, totalSizeX)
			
def main():
	VV.Macro.PrintWindow.Clear()
	VV.Acquire.Stage.Series = False
	VV.Acquire.Sequence.SaveToDisk = True
		
	# Retrieve information about tile experiment
	areaTopLeftX = VV.Acquire.Stage.ScanSlide.Area.UpperLeft.X
	areaTopLeftY = VV.Acquire.Stage.ScanSlide.Area.UpperLeft.Y
	areaLowerRightX = VV.Acquire.Stage.ScanSlide.Area.LowerRight.X
	areaLowerRightY = VV.Acquire.Stage.ScanSlide.Area.LowerRight.Y

	# Retrieve information about frame and calibration
	xPixels = VV.Acquire.XDimension
	yPixels = VV.Acquire.YDimension
	bin = VV.Acquire.Binning
	cal = VV.Magnification.Calibration.Value

	# Calculate number of tiles	
	xTiles = int(round((areaLowerRightX-areaTopLeftX)/cal/bin/xPixels))
	yTiles = int(round((areaLowerRightY-areaTopLeftY)/cal/bin/yPixels))

	# Calculate size of final stitched image and display empty image
	totalSizeX = xPixels * 0.9 * xTiles + xPixels * 0.1
	totalSizeY = yPixels * 0.9 * yTiles + yPixels * 0.1

	resultImage = CvMat(totalSizeY, totalSizeX, MatrixType.U16C1)
	resultImage.Set(CvScalar(0))
	overview = VV.Process.CreateEmptyPlane('Monochrome16', totalSizeX, totalSizeY)
	VV.Image.WriteFromPointer(resultImage.Data, totalSizeY, totalSizeX)
	
	# Acquire tiles
	acquire(xTiles, yTiles, xPixels, yPixels, bin, cal, areaTopLeftX, areaTopLeftY, totalSizeX, totalSizeY, resultImage, overview)
	
	VV.Acquire.Stage.Series = True

try:
	main()
except KeyboardInterrupt:
	pass
