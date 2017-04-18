# VisiView Macro
# Author: PW
# Date: 2017-01-31
# Description:
# Reads the Error Information out of a Toptica Laser and writes it in a File named TopticaLog.txt in C:\ProgramData\Visitron Systems\VisiView\
# Purpose:
# Run this macro in case of a problem with a Toptica Laser and send uns the file TopticaLog.txt
# Usage:
# Adapt the name of the Laser Component in Lines 21 and 26 to the laser you want to log
# When the laser shows erraneous behaviour, run this macro and send us the file TopticaLog.txt

import datetime

def getSpecifiedError(component,command):
	print VV.Device.SendString(component,command+'\n')
	text_file.write(' \n')
	text_file.write(command)
	while 1:
		try:
			#print VV.Device.ReadString('Toptica_Laser488')
			#text_file = open(path, "aw")

			text_file.write(VV.Device.ReadString(component))
			#text_file.close()
		except:
			#text_file.close()
			break

VV.Macro.PrintWindow.Clear()
VV.Macro.PrintWindow.IsVisible = True
now = datetime.datetime.now()
print str(now)

laserName = 'Toptica488_Laser488'

path = r'C:\ProgramData\Visitron Systems\VisiView\TopticaLog.txt'
text_file = open(path, "aw")
text_file.write('\n\nToptica Error Log\n')
text_file.write(str(now)+ '\n')
print 'System ID: {0}'.format(VV.Macro.Control.SystemIDNumber)
text_file.write('System ID: {0}\n'.format(VV.Macro.Control.SystemIDNumber))
#text_file.close()
getSpecifiedError(laserName,'sh err')
getSpecifiedError(laserName,'!pass BlueNOTE!')
getSpecifiedError(laserName,'talk debug')
getSpecifiedError(laserName,'serial')
getSpecifiedError(laserName,'ver')
getSpecifiedError(laserName,'sta up')
getSpecifiedError(laserName,'sh sys')
getSpecifiedError(laserName,'sh limits')
getSpecifiedError(laserName,'sh swi')
getSpecifiedError(laserName,'sta osc')
getSpecifiedError(laserName,'sh sat')
getSpecifiedError(laserName,'sh chn')
getSpecifiedError(laserName,'sh data')
getSpecifiedError(laserName,'sa all')
getSpecifiedError(laserName,'sh cur')
getSpecifiedError(laserName,'ini la')
getSpecifiedError(laserName,'las on')
getSpecifiedError(laserName,'di x')
getSpecifiedError(laserName,'en 1')
getSpecifiedError(laserName,'en 2')
getSpecifiedError(laserName,'sh cur')
getSpecifiedError(laserName,'sh pow')
getSpecifiedError(laserName,'sta tec')
getSpecifiedError(laserName,'sta temp')
getSpecifiedError(laserName,'sta clip')
getSpecifiedError(laserName,'list pic')
getSpecifiedError(laserName,'sh error')
getSpecifiedError(laserName,'error')
getSpecifiedError(laserName,'talk usual')


text_file.close()	


#CMD>sh pow 
#CMD> sta tec 
#CMD> sta temp 
#CMD> sta clip 
#CMD> list pic 
#CMD> sh error 
#CMD> error 
#CMD>talk usual 

	
	