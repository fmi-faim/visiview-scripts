# VisiView Macro
magList = VV.Magnification.List
magList = sorted(magList)
try:
	GetGlobalVar("ovobj")
except:
	SetGlobalVar("ovobj","")
	
try:
	GetGlobalVar("tileobj")
except:
	SetGlobalVar("tileobj","")

ovobjtemp = GetGlobalVar("ovobj")
tileobjtemp = GetGlobalVar("tileobj")

VV.Macro.InputDialog.Initialize("Select objectives", True)
VV.Macro.InputDialog.AddListOnlyVariable("Overview Objective", "ovobjtemp", ovobjtemp, magList)
VV.Macro.InputDialog.AddListOnlyVariable("Tiling Objective", "tileobjtemp", tileobjtemp, magList)
VV.Macro.InputDialog.Show()

SetGlobalVar("ovobj", ovobjtemp)
SetGlobalVar("tileobj", tileobjtemp)
