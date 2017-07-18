# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 21:28:26 2017

@author: laurentgelman
"""
import ctypes
from EmailConfig import smtpHost, defaultSender, defaultRecipient

class Email:
    """
    This class has four attributes:
        1. The address of the person sending the e-mail 
        2. The address of the one to whom the e-mail is sent
        3. The object of the e-mail
        4. The message itself (or report)
    """

    def __init__(self, exped = defaultSender, destin = defaultRecipient, title = "Report", message = "Nothing to Report"):
        self.exped = exped
        self.destin = destin
        self.title = title
        self.message = message
        
    def send(self):
        import smtplib
        from email.mime.text import MIMEText
        try:
    		msg = MIMEText(self.message)
    		msg['Subject'] = self.title
    		msg['From'] = self.exped
    		msg['To'] = self.destin
    		s = smtplib.SMTP(smtpHost)
    		s.sendmail(self.exped, self.destin, msg.as_string())
    		s.quit()
        except:
    		print("Could not send e-mail")
            
            
def getUserLogged():
    GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
    NameDisplay = 3

    size = ctypes.pointer(ctypes.c_ulong(0))
    GetUserNameEx(NameDisplay, None, size)

    nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
    GetUserNameEx(NameDisplay, nameBuffer, size)
    return nameBuffer.value


def createEmailAddress(loggedUser):
    try:
        userName = loggedUser.split(",")
        emailAdresse = userName[1][1:]+"."+userName[0]+"@fmi.ch"
    except:
        emailAdresse = "faim@fmi.ch"
    
    return emailAdresse