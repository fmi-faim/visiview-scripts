# VisiView Macro
import os

paramFile = "C:\\Users\\Public\\Metamorph\\PosInfo.txt"
try:
	target = open(paramFile, 'w')
	GetGlobalVar('XStart')
	target.write("\""+str(GetGlobalVar('XStart'))+";"+str(GetGlobalVar('YStart'))+";"+str(GetGlobalVar('ZStart'))+";"+str(GetGlobalVar('XEnd'))+";"+str(GetGlobalVar('YEnd'))+";"+str(GetGlobalVar('ZEnd'))+";"+str(GetGlobalVar('Z3'))+"\"")
	target.close()
except:
	print ("There was a problem")

