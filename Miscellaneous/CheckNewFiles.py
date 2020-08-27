# VisiView Macro
import sys, os, glob
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\lib")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\faim-common-utils")
vvimport('fileutils')
import EmailToolbox
VV.Macro.PrintWindow.Clear()
VV.Macro.PrintWindow.IsVisible = True

# *********** Parameters **********

delay = 5 #minutes
emailAddress = "faim@fmi.ch"

# **********************************

VV.Macro.InputDialog.Initialize("Set Parameters", True)
VV.Macro.InputDialog.AddFloatVariable("Check frequency (in minutes):", "delay", delay, 1, 1000, 1)
VV.Macro.InputDialog.AddStringVariable("E-mail address:", "emailAddress", "FirstName.LastName@fmi.ch")
VV.Macro.InputDialog.Show()

older_file = ""
path = os.path.join(VV.Acquire.Sequence.Directory,"*")
list_of_files = glob.glob(path)
latest_file = max(list_of_files, key=os.path.getctime)
print ("Latest File is: "+ latest_file)

while(latest_file != older_file):
	older_file = latest_file
	print ("Waiting "+str(int(delay))+" min...")
	VV.Macro.Control.Delay(delay,'min')
	list_of_files = glob.glob(path)
	latest_file = max(list_of_files, key=os.path.getctime)
	print ("Latest File in the Folder: "+latest_file)

	
print ("No new file since "+str(int(delay))+" min")
InfoMail = EmailToolbox.Email(destin = emailAddress, title = "Acquisition stopped", message = "No new file since "+str(int(delay))+" min")
InfoMail.send()

