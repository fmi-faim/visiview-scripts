# VisiView Macro
if VV.Window.Regions.Active.IsValid:
	pp, xx, yy = VV.Window.Regions.Active.CoordinatesToArrays()
	ww = xx[1]-xx[0]
	hh = yy[2]-yy[1]
	VV.Window.Regions.AddCentered('Rectangle', xx[0]+ww/2+20, yy[0]+hh/2+20, ww, hh)
else:
	VV.Macro.MessageBox.ShowAndWait("Select a region first", " ", False)