import clr
import sys
import math
sys.path.append(r"C:\Program Files\Visitron Systems\VisiView\Tools\OpenCVSharp_4_5_3")
clr.AddReference("OpenCvSharp")
from OpenCvSharp import *

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
