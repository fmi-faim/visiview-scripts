from datetime import datetime

import csv, os, datetime

tempDir = os.getenv("TEMP")

VV.Macro.PrintWindow.IsVisible = True
VV.Macro.PrintWindow.Clear()

VV.Acquire.Stage.PositionList.Save(tempDir + "\\PositionList.stg")
VV.Acquire.Stage.Series = False
VV.Acquire.TimeLapse.Series = False
VV.Acquire.TimeLapse.Stream.Request = False

VV.Macro.InputDialog.Initialize("Experiment Info", True)
VV.Macro.InputDialog.AddLabelOnly("Time-lapse Info")
VV.Macro.InputDialog.AddFloatVariable("Time points number", "TimePoints", 10, 1, 1000, 1)
VV.Macro.InputDialog.AddFloatVariable("Time interval (sec)", "TimeInterval", 60, 1, 10000, 1)
VV.Macro.InputDialog.AddStringVariable("Base File", "basename", VV.Acquire.Sequence.BaseName)
VV.Macro.InputDialog.Show()

nStagePositions = 5
fo = open(tempDir + "\\PositionList.stg")
reader = csv.reader(fo)
StagePositions = []
k=0
for row in reader:
	if (k > 3):
		StagePositions.append({'Name': row[0],
						 'X': row[1],
						 'Y': row[2],
						 'Z': row[3]})
	k += 1

timestart = datetime.datetime.now()
print (timestart.strftime("Experiment started at %H:%M:%S"))
print ("****************")

for timepoint in range(TimePoints):
	time0 = datetime.datetime.now()
	lineNumber = 0
	for stagePos in StagePositions:
		# go to position
		VV.Stage.XPosition = float(stagePos['X'])
		VV.Stage.YPosition = float(stagePos['Y'])
		VV.Focus.ZPosition = float(stagePos['Z'])
		# acquire setting1
		VV.Acquire.Settings.Load("C:\Users\Public\Metamorph\setting1")
		VV.Acquire.Sequence.BaseName = basename+"_ntime"+str(timepoint+1)+"_position"+stagePos['Name']+"_"
		VV.Acquire.Stage.Series = False
		VV.Acquire.TimeLapse.Series = False
		VV.Acquire.Z.Series = True
		VV.Acquire.Z.Stream.Request = True
		VV.Acquire.Sequence.Start()
		VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)
		# acquire setting2
		VV.Acquire.Settings.Load("C:\Users\Public\Metamorph\setting2")
		VV.Acquire.Sequence.BaseName = basename+"_ntime"+str(timepoint+1)+"_position"+stagePos['Name']+"_"
		VV.Acquire.Stage.Series = False
		VV.Acquire.TimeLapse.Series = False
		VV.Acquire.Z.Series = True
		VV.Acquire.Z.Stream.Request = True
		VV.Acquire.Sequence.Start()
		VV.Macro.Control.WaitFor('VV.Acquire.IsRunning', "==", False)

	# wait for next time-point
	nexttime = timestart + datetime.timedelta(0, (timepoint+1)*TimeInterval)
	if timepoint+1 == TimePoints:
		print ("Done")
		break
	print (nexttime.strftime("Next time-point at %H:%M:%S"))
	VV.Macro.Control.Delay(((nexttime-time0).total_seconds())*1000,'ms')
	VV.Window.CloseAll(False)

VV.Acquire.Sequence.BaseName = basename
