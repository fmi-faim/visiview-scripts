# VisiView Macro
import clr, math, sys
import csv, os, re
from pprint import pprint
from System import Array
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\Examples\Image Access\OpenCV\Library")
vvimport('OpenCV')
import datetime
import ctypes


# *************************************************************************************
# Positions in the position list are saved as a .stg file opened with a csv reader. 
# The function returns 3 arrays of coordinates for x, y and z
# *************************************************************************************
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


# *************************************************************************************
# Different functions for the triangulation
#
# *************************************************************************************
def counterclockwise(A,B,C):
	"""
	Tests if three points are listed in a counterclockwise order
	"""
	return (C.Y-A.Y)*(B.X-A.X) > (B.Y-A.Y)*(C.X-A.X)

def intersects( p0, p1, p2, p3 ) :
	"""
	Tests if a Line (p0,p1) and another (p2,p3) intersects
	"""
	if p0.X == p2.X and p0.Y == p2.Y: 
		return False
	if p1.X == p2.X and p1.Y == p2.Y: 
		return False
	if p0.X == p3.X and p0.Y == p3.Y: 
		return False
	if p1.X == p3.X and p1.Y == p3.Y: 
		return False
	return counterclockwise(p0,p2,p3) != counterclockwise(p1,p2,p3) and counterclockwise(p0,p1,p2) != counterclockwise(p0,p1,p3)

def transformTriangles(lines, cal, offsetLeft, offsetTop):
	for i in range(len(lines)):
		lines[i][1] = (lines[i][1] - offsetLeft) / cal
		lines[i][2] = (lines[i][2] - offsetTop) / cal
		lines[i][4] = (lines[i][4] - offsetLeft) / cal
		lines[i][5] = (lines[i][5] - offsetTop) / cal

def buildTriangles(coordsX, coordsY, coordsZ,L,T,W,H):

	# Generates a List of Triangles from a List of points (2D, on X-Y-Level)
	# coordsX, coordsY, coordsZ: X-,Y- and Z-Coords. of the points
	# L,T,W,H: Left,Top,Width,Height of the bounding bx

	allCoordsX = []
	allCoordsY = []
	allCoordsZ = []
	for i in range(len(coordsX)):
		allCoordsX.append(coordsX[i]);
		allCoordsY.append(coordsY[i]);
		allCoordsZ.append(coordsZ[i]);


	# Add the corners of the bounding box (or the image) and look for closest point defined in the stage position list.
	# The corner gets then the same Z as that point.
	
	cornersX = [L,L+W,L+W,L]
	cornersY = [T,T,T+H,T+H]
	for j in range(len(cornersX)):
		minDist = sys.maxint
		for i in range(len(allCoordsX)):
			dist = math.sqrt(math.pow(cornersX[j]-allCoordsX[i],2)+math.pow(cornersY[j]-allCoordsY[i],2))
			if dist < minDist:
				minDist = dist
				z = allCoordsZ[i]
		allCoordsX.append(cornersX[j]);
		allCoordsY.append(cornersY[j]);
		#Use Z.Coords. of the nearest Point
		allCoordsZ.append(z);


	# Generates all possible Lines and sorts them by length
	
	points = []
	for i in range(len(allCoordsX)):
		for j in range(i+1,len(allCoordsX)):
			if i == j: continue
			dist = math.sqrt(math.pow(allCoordsX[i]-allCoordsX[j],2)+math.pow(allCoordsY[i]-allCoordsY[j],2))
			insertIndex = -1
			for k in range(len(points)):
				if points[k][0] > dist:
					insertIndex = k
					break
			if insertIndex == -1:
				points.append([dist,allCoordsX[i],allCoordsY[i],allCoordsZ[i],allCoordsX[j],allCoordsY[j],allCoordsZ[j]])
			else:
				points.insert(k,[dist,allCoordsX[i],allCoordsY[i],allCoordsZ[i],allCoordsX[j],allCoordsY[j],allCoordsZ[j]])
	
	#delete all lines that intersects with a shorter line
	delIndizes = []
	for i in range(len(points)):
		index = (len(points) - i)-1
		for j in range(index):
			o1 = CvPoint2D32f(points[index][1],points[index][2])
			p1 = CvPoint2D32f(points[index][4],points[index][5])
			o2 = CvPoint2D32f(points[j][1],points[j][2])
			p2 = CvPoint2D32f(points[j][4],points[j][5])
			if intersects(o1,p1,o2,p2):
				delIndizes.append(index)
				break
	
	delPoints = []
	for i in range(len(delIndizes)):
		delPoints.append(points[delIndizes[i]])
		del points[delIndizes[i]]
		
	#add all deleted lines that do not intersect with a remaining line (needed for circular intersection)
	for i in range(len(delPoints)):
		j = len(delIndizes) - i -1
		intersection = False
		for k in range(len(points)):
			o1 = CvPoint2D32f(points[k][1],points[k][2])
			p1 = CvPoint2D32f(points[k][4],points[k][5])
			o2 = CvPoint2D32f(delPoints[j][1],delPoints[j][2])
			p2 = CvPoint2D32f(delPoints[j][4],delPoints[j][5])
			if intersects(o1,p1,o2,p2):
				intersection = True
				break
		if intersection == False:
			points.append(delPoints[j])
	return points


#bilinear interpolation of the Z-Coord of each point along the triangles built by "lines"
def BiLinearInterpolation(lines, img):

	points = []
	for i in range(len(lines)):
		p1 = [lines[i][1],lines[i][2],lines[i][3]]
		if p1 not in points:
			points.append(p1)
			BiLinearInterpolationTrianglesByPoint(p1[0],p1[1],p1[2],lines,img)
		p2 = [lines[i][4],lines[i][5],lines[i][6]]
		if p2 not in points:
			points.append(p2)
			BiLinearInterpolationTrianglesByPoint(p2[0],p2[1],p2[2],lines,img)

#bilinear interpolation of the Z-Coord along the triangles builded by "lines" for all triangles whose lower point is (x,y,z)
def BiLinearInterpolationTrianglesByPoint(x,y,z,lines,img):
	maxInt = sys.maxint
	minInt = -sys.maxint - 1
	#search all points with a lower y-Coords as 'y', which build a line with 'x,y,z'
	endPoints = []
	for i in range(len(lines)):
		if lines[i][1] == x and lines[i][2] == y and lines[i][5] <= y:
			endPoints.append([lines[i][4],lines[i][5],lines[i][6]])
		if lines[i][4] == x and lines[i][5] == y and lines[i][2] <= y:
			endPoints.append([lines[i][1],lines[i][2],lines[i][3]])

	#sort the remaining lines by angle
	sortedEndPoints = []
	for i in range(len(endPoints)):
		if endPoints[i][1] == y and endPoints[i][0] < x: m = maxInt
		elif endPoints[i][1] == y and endPoints[i][0] > x: m = minInt
		elif endPoints[i][0] == x: m = 0
		else: m = float(endPoints[i][0] - x)/float(endPoints[i][1] - y)
		insertIndex = -1
		for k in range(len(sortedEndPoints)):
			if sortedEndPoints[k][0] < m:
				insertIndex = k
				break
		if insertIndex == -1:
			sortedEndPoints.append([m,endPoints[i][0],endPoints[i][1],endPoints[i][2]])
		else:
			sortedEndPoints.insert(k,[m,endPoints[i][0],endPoints[i][1],endPoints[i][2]])

	for i in range(len(sortedEndPoints)-1):
		BiLinearInterpolationTriangle(x,y,z,sortedEndPoints[i][1],sortedEndPoints[i][2],sortedEndPoints[i][3],sortedEndPoints[i+1][1],sortedEndPoints[i+1][2],sortedEndPoints[i+1][3],img)

#bilinear interpolation of the Z-Coords (z1,z2,z3) along the given triangle (x1,y1,x2,y2,x3,y3)
def BiLinearInterpolationTriangle(x1,y1,z1,x2,y2,z2,x3,y3,z3,img):
	if y1 >= y2 and y1 >= y3:
		if y2 >= y3:
			maxPY = float(y1)
			midPY = float(y2)
			minPY = float(y3)
			maxPX = float(x1)
			midPX = float(x2)
			minPX = float(x3)
			maxPZ = float(z1)
			midPZ = float(z2)
			minPZ = float(z3)
		if y2 < y3:
			maxPY = float(y1)
			midPY = float(y3)
			minPY = float(y2)
			maxPX = float(x1)
			midPX = float(x3)
			minPX = float(x2)
			maxPZ = float(z1)
			midPZ = float(z3)
			minPZ = float(z2)
	if y2 >= y1 and y2 >= y3:
		if y1 >= y3:
			maxPY = float(y2)
			midPY = float(y1)
			minPY = float(y3)
			maxPX = float(x2)
			midPX = float(x1)
			minPX = float(x3)
			maxPZ = float(z2)
			midPZ = float(z1)
			minPZ = float(z3)
		if y1 < y3:
			maxPY = float(y2)
			midPY = float(y3)
			minPY = float(y1)
			maxPX = float(x2)
			midPX = float(x3)
			minPX = float(x1)
			maxPZ = float(z2)
			midPZ = float(z3)
			minPZ = float(z1)
	if y3 >= y1 and y3 >= y2:
		if y1 >= y2:
			maxPY = float(y3)
			midPY = float(y1)
			minPY = float(y2)
			maxPX = float(x3)
			midPX = float(x1)
			minPX = float(x2)
			maxPZ = float(z3)
			midPZ = float(z1)
			minPZ = float(z2)
		if y1 < y2:
			maxPY = float(y3)
			midPY = float(y2)
			minPY = float(y1)
			maxPX = float(x3)
			midPX = float(x2)
			minPX = float(x1)
			maxPZ = float(z3)
			midPZ = float(z2)
			minPZ = float(z1)

	for y in range(int(minPY),int(maxPY)):
		factor = float(y-minPY)/float(maxPY-minPY)
		mamiX = (float(minPX) + ((factor)*float(maxPX-minPX)))
		mamiZ = (float(minPZ) + ((factor)*float(maxPZ-minPZ)))
		if y <= midPY:
			if midPY == minPY: factor = 1
			else: factor = float(y-minPY)/float(midPY-minPY)
			midX = (float(minPX) + ((factor)*float(midPX-minPX)))
			midZ = (float(minPZ) + ((factor)*float(midPZ-minPZ)))
		if y > midPY:
			if midPY == maxPY: factor = 1
			else: factor = float(y-midPY)/float(maxPY-midPY)
			midX = (float(midPX) + ((factor)*float(maxPX-midPX)))
			midZ = (float(midPZ) + ((factor)*float(maxPZ-midPZ)))
		LinearInterpolationLine(mamiX,midX,y,mamiZ,midZ,img)
	
#linear interpolation along a line
def LinearInterpolationLine(x1,x2,y,color1,color2,img):
	if x1 < x2:
		colorS = color1
		colorB = color2
		xS = x1
		xB = x2
	else:
		colorS = color2
		colorB = color1
		xS = x2
		xB = x1
	for x in range(int(xS),int(xB)):
		factor = float(x-xS)/float(xB-xS)
		tmpColor = colorS*(1.0-factor)+colorB*(factor)
		img.DrawRect(CvRect(int(x),int(y),1,1),CvScalar(tmpColor,tmpColor,tmpColor))



def generateHeightImage(width, height, calibration, cX, cY, cZ):
	# Get Image corner coords as stage coordinates
	xLeft, yTop = VV.File.ConvertImageCoordinatesToStageCoordinates(0,0)
	# xRight, yBottom = VV.File.ConvertImageCoordinatesToStageCoordinates(width,height)
	# Triangulate list and corner points
	points = buildTriangles(cX, cY, cZ,xLeft,yTop,width*calibration,height*calibration)

	# transform to pixel coords
	transformTriangles(points, calibration, xLeft, yTop)
	# create empty heightImage
	outputImage = CvMat(height, width, MatrixType.F32C1)
	outputImage.Set(CvScalar(0.0))
	# interpolate and create image
	BiLinearInterpolation(points, outputImage)
	return outputImage

def generateEmptyMask(height, width):
	# CvMat 512x512 empty (consider binning)
	binaryMask = CvMat(height, width, MatrixType.U8C1)
	binaryMask.Set(CvScalar(0))
	# return image
	return binaryMask

def saveHeightImage(heightImageHandle, focusMin, focusMax):
	SetGlobalVar('ch.fmi.VV.focusMin', focusMin)
	SetGlobalVar('ch.fmi.VV.focusMax', focusMax)
	VV.Window.Selected.Handle = heightImageHandle
	tempDir = os.getenv("TEMP")
	VV.File.SaveAs(os.path.join(tempDir, 'TmpFocusImage.tif'), True)
	
def loadHeightImage():
	focusMin = GetGlobalVar('ch.fmi.VV.focusMin')
	focusMax = GetGlobalVar('ch.fmi.VV.focusMax')
	scale = GetGlobalVar('ch.fmi.VV.scale')
	tempDir = os.getenv("TEMP")
	VV.File.Open(os.path.join(tempDir, 'TmpFocusImage.tif'))
	w = int(VV.Image.Width/scale)
	h = int(VV.Image.Height/scale)
	heightImageRead = CvMat(h,w,MatrixType.U16C1)
	VV.Image.ReadToPointer(heightImageRead.Data)
	heightImageFloat = CvMat(h,w,MatrixType.F32C1)
	heightImageRead.Convert(heightImageFloat)
	heightImageDenormalized = (heightImageFloat * (focusMax - focusMin)) / 65535 + CvScalar(focusMin)
	return heightImageDenormalized

def displayHeightImage(heightImage, focusMin, focusMax, regionFileName, scale, heightImageW, heightImageH):
	heightImageNormalized = heightImage if (focusMax==focusMin) else (heightImage-CvScalar(focusMin))*65535/(focusMax-focusMin)

	heightImageU16 = CvMat(heightImageH, heightImageW, MatrixType.U16C1)
	heightImageNormalized.Convert(heightImageU16)
	
	#VV.Edit.Duplicate.Plane()
	VV.Process.CreateEmptyPlane('Monochrome16', heightImageW, heightImageH)
	VV.Image.WriteFromPointer(heightImageU16.Data, heightImageH, heightImageW)
	#if regionFileName:
	#	VV.Edit.Regions.Load(regionFileName)

def displayImage(cvImage):
	VV.Process.CreateEmptyPlane('Monochrome8',VV.Image.Width, VV.Image.Height)
	VV.Image.WriteFromPointer(cvImage.Data, VV.Image.Width, VV.Image.Height)


def getAcquisitionTiles(regionIndex, binaryMask, bin, magnificationRatio, heightImage):
		# Select next region
		VV.Window.Regions.Active.Index = regionIndex
		# TODO make user-definable
		overlap = 0.1
		
		# Draw current region into mask
		#get all information of the active region 
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
		
		# Get bounding box coordinates
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
		
		startLeft = regionLeft - (overhangX/2)
		startTop = regionTop - (overhangY/2)	

		binaryMaskRectangles = binaryMask.Clone()
		# Create container lists for results
		# TODO replace by better structure (dict?)
		imgTiles = []
		imgTileRegions = []
		imgCentersX = []
		imgCentersY = []

		# return all possible tiles

		
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
					imgTileRegions.append(regionIndex)
					imgCentersX.append(startX)
					imgCentersY.append(startY)

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
						imgTileRegions.append(regionIndex)
						imgCentersX.append(startX)
						imgCentersY.append(startY)


		else:
			for col in range(int(nTilesX)):
				for row in range(int(nTilesY)):
					tLeft = startLeft + col * (reducedTileWidth)
					tTop = startTop + row * (reducedTileHeight)
					currentTile = CvRect(tLeft, tTop, tileWidth, tileHeight)
					
					# Crop binary mask to current rectangle
					dummy, croppedMask = binaryMask.GetSubRect(currentTile)
					
					# Measure max value of cropped rectangle
					minValue = clr.Reference[float]()
					maxValue = clr.Reference[float]()
					Cv.MinMaxLoc(croppedMask,minValue,maxValue)
					
					# filter tiles according to actual polygon area
					if(int(maxValue) == 255):
						imgTiles.append(currentTile)
						imgTileRegions.append(regionIndex)
						imgCentersX.append(tLeft + tileWidth/2)
						imgCentersY.append(tTop + tileHeight/2)
					
		# Return all results
		return imgTiles, imgTileRegions, imgCentersX, imgCentersY

def saveTileList(roiNumber, baseDir, baseName, imgCentersX, imgCentersY, imgFocusPoints):
	stageListFile = os.path.join(baseDir, baseName + "_Region-" + str(roiNumber) + "_nTiles-" + str(len(imgCentersX)) + ".stg")
	target = open(stageListFile, 'w')
	# csvWriter = csv.writer(target)
	target.write("\"Stage Memory List\", Version 5.0\n0, 0, 0, 0, 0, 0, 0, \"microns\", \"microns\"\n0\n"+str(len(imgCentersX))+"\n")
	# csvWriter.writeRow("Stage Memory List", )

	for i in range(len(imgCentersX)):
		x,y = VV.File.ConvertImageCoordinatesToStageCoordinates(imgCentersX[i], imgCentersY[i])
		text = "\"Position"+str(i+1)+"\", "+("%.3f" % x)+", "+("%.3f" % y)+", "+("%.3f" % imgFocusPoints[i])+", 0, 0, FALSE, -9999, TRUE, TRUE, 0, -1, \"\"\n"
		target.write(text)
	target.close()
	#sleep(2)
	return(stageListFile)

def configDialog():
	VV.Macro.InputDialog.Initialize("Confirm Basename", True)
	VV.Macro.InputDialog.AddStringVariable("Basename", "basename", VV.Acquire.Sequence.BaseName)
	tempDir = os.getenv("TEMP")
	doReUse = False
	if os.path.exists(os.path.join(tempDir, 'TmpFocusImage.tif')):
		VV.Macro.InputDialog.AddBoolVariable("Re-use focus map?", "reusefocusmap", True)
	VV.Macro.InputDialog.Show()
	if os.path.exists(os.path.join(tempDir, 'TmpFocusImage.tif')):
		doReUse = reusefocusmap
	VV.Acquire.Sequence.BaseName = basename
	return (basename[:-1] if basename.endswith('_') else basename), doReUse

def restoreFocusPositions():
	tempDir = os.getenv("TEMP")
	posList = tempDir + "\\PositionList.stg"
	if os.path.isfile(posList):
		VV.Acquire.Stage.PositionList.Load(posList)

def restoreRegions(regionFileName):
	VV.Edit.Regions.Load(regionFileName)



# *************************************************************************************
# *************************************************************************************
#
# 										MAIN
#
# *************************************************************************************
# *************************************************************************************
def main():

	# *************************************************************************************
	# Initialization
	# *************************************************************************************
	user32 = ctypes.windll.user32
	screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
	
	overviewHandle = VV.Window.GetHandle.Active
	VV.Window.Selected.Top = 10
	VV.Window.Selected.Left = 10
	VV.Window.Selected.Height = user32.GetSystemMetrics(1)/3
	
	cal = VV.Image.Calibration.Value
	cX, cY, cZ = parsePositions()
	magnificationRatio = float(VV.Magnification.Calibration.Value)/float(VV.Image.Calibration.Value)
	bin = VV.Acquire.Binning
	VV.Acquire.Stage.SeriesType = 'PositionList'
	
	reuseFocusMap = False
	baseName, reuseFocusMap = configDialog()
	baseDir = VV.Acquire.Sequence.Directory
	
	VV.Macro.PrintWindow.Clear()
	VV.Macro.PrintWindow.IsVisible = True
	
	# Unselect regions
	regionFileName = "MultiTileRegion.rgn"
	VV.Edit.Regions.Save(regionFileName)
	VV.Window.Regions.Active.Index = VV.Window.Regions.Count + 1
	# will have to be replaced by
	# VV.Window.Regions.Active.IsValid = False

	
	# *************************************************************************************
	# Create an image with the numbers of the regions
	# *************************************************************************************
	VV.Window.Active.Handle = overviewHandle
	VV.Window.Selected.Handle = overviewHandle
	VV.Window.Regions.Active.Index = VV.Window.Regions.Count + 1
	he = VV.Image.Height
	wi = VV.Image.Width
	VV.Process.DuplicatePlane()
	VV.File.Info.Name = "Region Identification in "+baseName

	zoom = VV.Window.Selected.ZoomPercent
	imageWithRegion = CvMat(he,wi,MatrixType.U16C1)
	imageWithRegion.Set(CvScalar(0))
	restoreRegions(regionFileName)
	polyLines = Array.CreateInstance(Array[CvPoint], 1)
	for r in range(VV.Window.Regions.Count):
		VV.Window.Regions.Active.Index = r+1
		points, CoordX, CoordY = VV.Window.Regions.Active.CoordinatesToArrays()
		font = CvFont(FontFace.Italic,int(16/(int(zoom/100*2)+1)),1)
		font.Thickness = int(16/((int(zoom/100*2)+1)))
		imageWithRegion.PutText(str(r), CvPoint(CoordX[0]-5,CoordY[0]-5), font, CvScalar(65000))
		polyLine = Array.CreateInstance(CvPoint, len(CoordX))
		for i in range(len(CoordX)):
			polyLine[i] = CvPoint(CoordX[i],CoordY[i])	
		polyLines[0] = polyLine
		VV.Window.Regions.Active.Index=r+1
		if VV.Window.Regions.Active.Type=='PolyLine':
			imageWithRegion.DrawPolyLine(polyLines, False, CvScalar(30000),int(16/((int(zoom/100*2)+1))))
		else:
			imageWithRegion.DrawPolyLine(polyLines, True, CvScalar(30000),int(16/((int(zoom/100*2)+1))))
	VV.Image.WriteFromPointer(imageWithRegion.Data, he, wi)
	VV.Edit.Regions.ClearAll()
	VV.Window.Selected.Top = user32.GetSystemMetrics(1)/3 + 20
	VV.Window.Selected.Left = 10
	VV.Window.Selected.Width=user32.GetSystemMetrics(0)/4

	path = os.path.join(baseDir, baseName+'_regions.tif')
	VV.File.SaveAs(path, True)


	# *************************************************************************************
	# Create Focus Map
	# *************************************************************************************
	VV.Window.Active.Handle = overviewHandle
	VV.Window.Regions.Active.Index = VV.Window.Regions.Count + 1
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
	VV.Window.Selected.Top = user32.GetSystemMetrics(1)/3 +60
	VV.Window.Selected.Left = 30
	VV.Window.Selected.Width=user32.GetSystemMetrics(0)/4
	
	# TODO take care of regions and active image
	VV.Window.Active.Handle = overviewHandle
	VV.Window.Selected.Handle = overviewHandle

	# Create binary mask (CvMat) with all regions
	binaryMask = generateEmptyMask(VV.Image.Height, VV.Image.Width)
	
	stgFileList = []
	numberTilesEachRegion = []

	for r in range(VV.Window.Regions.Count):
		VV.Window.Selected.Handle = overviewHandle
		VV.Edit.Regions.ClearAll()
		VV.Edit.Regions.Load(regionFileName)
		currentTiles, imgTileRegions, imgCentersX, imgCentersY = getAcquisitionTiles(r+1, binaryMask, bin, magnificationRatio, heightImage)
		VV.Edit.Regions.ClearAll()

		for tile in currentTiles:
			VV.Window.Regions.AddCentered("Rectangle", tile.X+tile.Width/2, tile.Y+tile.Height/2, tile.Width, tile.Height)

		VV.Macro.MessageBox.ShowAndWait("Please Adjust Tiles for region "+str(r), "Tile Adjustment", False)
		
		# *************************************************************************************
		# Adjust calculated tiles
		# *************************************************************************************		

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

		numberTilesEachRegion.append(VV.Window.Regions.Count)		
		stgFileList.append(saveTileList(r, baseDir, baseName, imgCentersX, imgCentersY, imgFocusPoints))


	# Select overview image with regions
	VV.Window.Active.Handle = overviewHandle
	#VV.Edit.Regions.Load(regionFileName)
	
	# acquire all tiles (new macro with choice dialog)
	timeStart = datetime.datetime.now()
	print (timeStart.strftime("Experiment started at %H:%M:%S"))

	for count, stgFile in enumerate(stgFileList):
		# Estimate time for acquisition of tiles
		if count == 1:
			timeFirstRegion = datetime.datetime.now()
			diff = timeFirstRegion - timeStart
			timeAcquisitionFirstRegion = diff.total_seconds()
			if numberTilesEachRegion[0] != 0:
				timePerTile = timeAcquisitionFirstRegion / numberTilesEachRegion[0]
			else:
				timePerTile = timeAcquisitionFirstRegion
				print ("!!!!!!!!!")
				print ("Times could not be calculated precisely since there is no tile in region 0")
				print ("!!!!!!!!!")				
			print ("\n______________________\n")
			for k in range(len(numberTilesEachRegion)):
				print ("Time to acquire region "+str(k)+" (containing "+str(numberTilesEachRegion[k])+" tiles) = "+str(int(timePerTile*numberTilesEachRegion[k]))+" sec")
				timeStart = timeStart + diff/numberTilesEachRegion[0]*numberTilesEachRegion[k]
				if k>0:
					print ("  => Region "+str(k)+" will finish at "+timeStart.strftime("%H:%M:%S"))
			print ("______________________\n")
					
		# Acquire tiles		
		VV.Acquire.Stage.PositionList.Load(stgFile)
		m = re.match(r'.*\\([^\\]+).stg', stgFile)
		VV.Acquire.Sequence.BaseName = m.group(1)
		print ("\nNow acquiring " + m.group(1)+"...")
		VV.Acquire.Sequence.Start()
		VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
		# close image windows after acquisition
		
	restoreFocusPositions()
	restoreRegions(regionFileName)


try:
	main()
except KeyboardInterrupt:
	restoreFocusPositions()
	pass
#except StandardError:
#	pass

