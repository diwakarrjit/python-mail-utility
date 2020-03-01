from datetime import datetime
from flask import Flask
from flask import request
from flask import jsonify
import email
import smtplib
import ssl
import json
import base64
import os
import sys
import logging
import time
from datetime import date
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
app = Flask(__name__)
emailTemplateDir = 'email-template'
logging.basicConfig(filename="logger"+str(datetime.now().day) +
                    "-" + str(datetime.now().month)+"-"+str(datetime.now().year)+".log", level=logging.DEBUG)


@app.route('/test')
def hello_world():
    return 'Hello, World!'

@app.route('/sendemail', methods = ['POST'])
def api_message():
  try:
    logging.debug("Inside sendemail method.")
    if validateSendMailPayload() is False:
        return jsonify(
            success=False,
            error='Invalid Request.'
        )
    receiver_emails = request.json.get('addresses')
    # senderName = configData.get('senderName')
    mailSubject = request.json.get('subject')
    mailBody = request.json.get('body')
    mailAttachmentBase64String = request.json.get('blob')
    mailAttachmentFileName = request.json.get('file_name')
    useCase = request.json.get('use_case')

    logging.debug("Reading config file [app-config.json].")
    if os.path.exists("app-config.json") == False:
        logging.error("Missing config file [app-config.json]. It should present in application root directory.")
        return jsonify(
            success=False,
            error='Internal Server Error.'
        )

    with open('app-config.json') as fileConfigData:
        configData = json.load(fileConfigData)

    logging.debug("config data read.")
    logging.info("configData: " + str(configData))

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = configData.get('senderName')
    message["Subject"] = mailSubject

    logging.debug("Creating mail template.")

    if os.path.exists(emailTemplateDir + '\\message_template.html') == False:
        logging.error(
            "Missing email template file(s). Looking into application's root directory ["+emailTemplateDir+"].")
        return jsonify(
            success=False,
            error='Internal Server Error.'
        )

    with open(emailTemplateDir + '\\message_template.html', 'r') as file:
        data = file.read().replace('\n', '')
        if mailBody:
            data = data.replace('{{ paragraph }}', mailBody)

    logging.debug("Mail template body read.")
    # Add body to email
    message.attach(MIMEText(data, "html"))

    if os.path.exists(emailTemplateDir + '\\email_header.jpg') == True:
        # Read header image binary from the current directory
        fp = open(emailTemplateDir + '\\email_header.jpg', 'rb')
        headerImage = MIMEImage(fp.read())
        fp.close()
        logging.debug("mail header acquired:")

        # Define the image's ID as referenced above
        headerImage.add_header('Content-ID', '<email_header>')
        message.attach(headerImage)
        logging.debug("reading footer image")
    
    if os.path.exists(emailTemplateDir + '\\email_footer.png') == True:
        # Read footer image binary from the current directory
        fp = open(emailTemplateDir + '\\email_footer.png', 'rb')
        footerImage = MIMEImage(fp.read())
        fp.close()
        logging.debug("Footer image read.")

        # Define the image's ID as referenced above
        footerImage.add_header('Content-ID', '<email_footer>')
        message.attach(footerImage)


    attachmentTempFileName = ""
    if mailAttachmentBase64String and mailAttachmentFileName:
        randomNumber = getRandomNumber()
        attachmentTempFileName = "temp_" + \
            randomNumber + mailAttachmentFileName
        
        logging.debug("Writing payload base64 string to a temp file.")

        with open(attachmentTempFileName, "wb") as temp_file:
            temp_file.write(base64.b64decode(mailAttachmentBase64String))

        logging.debug("Adding file as attachment")

        with open(attachmentTempFileName, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())


        logging.debug("Encoding file to base64")
        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)


        logging.debug("Adding attachment with content-disposition header")
        # Add header as key/value pair to attachment part
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {request.json.get('file_name')}",
        )

        logging.debug("Preparing final mail body")
        # Add attachment to message and convert message to string
        message.attach(part)


    text = message.as_string()


    logging.debug("Creating SMTP Connection")
    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(configData.get('server'), configData.get('port'), context=context) as server:
        server.login(configData.get('senderEmail'), configData.get('password'))
        logging.debug("Sending EMail(s) to "+ str(receiver_emails))
        server.sendmail(configData.get('senderName'), receiver_emails, text)
        logging.debug("EMail(s) Sent.")
        server.quit()

    if attachmentTempFileName and os.path.exists(attachmentTempFileName):
        logging.debug("Deleting file post mail sent.")
        os.remove(attachmentTempFileName)
        logging.debug("File deleted post mail sent.")
    
    return jsonify(
        success = True
    )
  except:
      e = sys.exc_info()
      logging.error(e)
      if attachmentTempFileName and os.path.exists(attachmentTempFileName):
        os.remove(attachmentTempFileName)
      return jsonify(
          success = False,
          error = 'Error in sending email'
      )


def getRandomNumber():
    return str(int(time.mktime(datetime.now().timetuple())))

def validateSendMailPayload():
    if request.json.get('addresses') is None:
        return False
    else:
        return True

