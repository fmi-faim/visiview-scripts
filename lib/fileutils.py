import csv, os

def parsePositions():
	path = os.getenv("TEMP") + "\\PositionList.stg"
	VV.Acquire.Stage.PositionList.Save(path)
	fo = open(path)
	reader = csv.reader(fo)
	coordsX = []
	coordsY = []
	coordsZ = []

	for row in reader:
		if (reader.line_num > 4):
			coordsX.append(float(row[1]))
			coordsY.append(float(row[2]))
			coordsZ.append(float(row[3]))

	fo.close()
	os.remove(path)
	return coordsX, coordsY, coordsZ
