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

delay = 1 #minutes
emailAddress = "laurent.gelman@fmi.ch"

# **********************************

VV.Macro.InputDialog.Initialize("Set Parameters", True)
VV.Macro.InputDialog.AddFloatVariable("Check frequency (in minutes):", "delay", 1, 1, 1000, 1)
VV.Macro.InputDialog.AddStringVariable("E-mail address:", "emailAddress", "FirstName.LastName@fmi.ch")
VV.Macro.InputDialog.AddDirectoryVariable("Select the directory", "directory", "")
VV.Macro.InputDialog.Show()

older_file = ""
list_of_files = glob.glob(os.path.join(directory,"*"))
latest_file = max(list_of_files, key=os.path.getctime)

while(latest_file != older_file):
	older_file = latest_file
	#list_of_files = glob.glob(r'C:\temp\Nikolas\*')
	list_of_files = glob.glob(os.path.join(directory,"*"))
	latest_file = max(list_of_files, key=os.path.getctime)
	print ("Latest File in the Folder: "+latest_file)
	print ("Waiting "+str(int(delay))+" min...")
	VV.Macro.Control.Delay(delay,'min')
	
print ("No new file since "+str(int(delay))+" min")
InfoMail = EmailToolbox.Email(destin = emailAddress, title = "Acquisition stopped", message = "No new file since "+str(delay)+" min")
InfoMail.send()

