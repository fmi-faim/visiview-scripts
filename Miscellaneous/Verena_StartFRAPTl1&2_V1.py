# VisiView Macro

"""
Save the two acquisition conditions in C:\Users\<username>\AppData\Local\Temp
"""

def main():
	baseName = VV.Acquire.Sequence.BaseName
	VV.Macro.PrintWindow.Clear()
	VV.Acquire.Settings.Load("TLsettings1.acq")
	baseNameTL1 = baseName + "_TL1_"
	VV.Acquire.Sequence.BaseName = baseNameTL1
	VV.Acquire.Sequence.Start()
	VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
	VV.Acquire.Settings.Load("TLsettings2.acq")
	baseNameTL2 = baseName + "_TL2_"
	VV.Acquire.Sequence.BaseName = baseNameTL2
	timeInt = VV.Acquire.TimeLapse.TimeIntervalInMillisecs
	VV.Macro.Control.Delay(timeInt/1000,'sec')
	VV.Acquire.Sequence.Start()
	VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
	VV.Acquire.Sequence.BaseName = baseName
	
try:
	main()
except KeyboardInterrupt:
	pass






