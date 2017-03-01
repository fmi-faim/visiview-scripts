# VisiView Macro
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Hello, this is an e-mail")
msg['Subject'] = "W1 info about region scanning"
msg['From'] = "W1-noreply@fmi.ch"
msg['To'] = "laurent.gelman@fmi.ch"

s = smtplib.SMTP('cas.fmi.ch')
s.sendmail("laurent.gelman@fmi.ch", "laurent.gelman@fmi.ch", msg.as_string())
s.quit()