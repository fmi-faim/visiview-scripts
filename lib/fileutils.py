import csv

def positionsFromFile(path):
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
	return coordsX, coordsY, coordsZ
