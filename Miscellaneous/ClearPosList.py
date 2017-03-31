# VisiView Macro

CancelButton = True
try:
	VV.Macro.MessageBox.ShowAndWait("Are you sure you want to delete all positions?", "Warning", CancelButton)
	VV.Acquire.Stage.PositionList.Save("C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\LastList.stp")
	VV.Acquire.Stage.PositionList.Load("C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\EmptyList.stp")
except:
	pass


