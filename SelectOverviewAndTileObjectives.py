# VisiView Macro
magList = VV.Magnification.List
magList = sorted(magList)
SetGlobalVar("ovobj","")
SetGlobalVar("tileobj","")

ovobjtemp = "--"
tileobjtemp = "--"

VV.Macro.InputDialog.Initialize("Select objectives", True)
VV.Macro.InputDialog.AddListOnlyVariable("Overview Objective", "ovobjtemp", magList[1], magList)
VV.Macro.InputDialog.AddListOnlyVariable("Tiling Objective", "tileobjtemp", magList[1], magList)
VV.Macro.InputDialog.Show()

SetGlobalVar("ovobj",ovobjtemp)
SetGlobalVar("tileobj",tileobjtemp)
