# VisiView Macro
import sys
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\lib")
sys.path.append(r"C:\ProgramData\Visitron Systems\VisiView\PythonMacros\FMI-git\faim-common-utils")
vvimport('fileutils')
import EmailToolbox
VV.Macro.PrintWindow.Clear()

# *********** Parameters **********

delay = 1 #minutes
emailAdresse = "laurent.gelman@fmi.ch"

# **********************************

older_file = ""
latest_file = "xx"

while(latest_file != older_file):
	older_file = latest_file
	list_of_files = glob.glob(r'C:\temp\Nikolas\*')
	latest_file = max(list_of_files, key=os.path.getctime)
	print latest_file
	VV.Macro.Control.Delay(delay,'min')
	
print ("No new file since "+str(delay)+" min")
InfoMail = EmailToolbox.Email(destin = emailAdresse, title = "Acquisition stopped", message = "No new file since "+str(delay)+" min")
InfoMail.send()

