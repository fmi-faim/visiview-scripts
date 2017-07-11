# VisiView Macro
import os
tempDir = os.getenv("TEMP")
path = os.path.join(tempDir,"EmptyPosList.stg")
emptyPosListFile = open(path, "w") 
emptyPosListFile.write("\"Stage Memory List\", Version 6.0\n0, 0, 0, 0, 0, 0, 0, \"microns\", \"microns\"\n0\n0") 
emptyPosListFile.close()

CancelButton = True
try:
	VV.Macro.MessageBox.ShowAndWait("Are you sure you want to delete all positions?", "Warning", CancelButton)
	VV.Acquire.Stage.PositionList.Save(os.path.join(tempDir,"LastList.stp"))
	VV.Acquire.Stage.PositionList.Load(path)
except StandardError:
	pass

	
