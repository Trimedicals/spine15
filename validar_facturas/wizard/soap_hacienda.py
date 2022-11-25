import pycurl
from io import BytesIO
import os
import tempfile

template = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:ns0="http://tempuri.org/" xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
   <SOAP-ENV:Header/>
   <ns1:Body>
      <ns0:Consulta>
         <ns0:expresionImpresa>${data}</ns0:expresionImpresa>
      </ns0:Consulta>
   </ns1:Body>
</SOAP-ENV:Envelope>"""

def ConsultaCFDI(data):
    datas= data.split("&rr=")
    data = datas[0].replace("&","&amp;")+"&rr="+datas[1]
    soap_env = template.replace("${data}", data).replace("&", "&amp;")
    fp, temp_file_name = tempfile.mkstemp()
    f = open(temp_file_name, "w")
    f.write(soap_env)
    f.close()

    c = pycurl.Curl()
    buf = BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, buf.write)

    filename = temp_file_name
    filesize = os.path.getsize(filename)
    fin = open(filename, 'rb')
    
    c.setopt(pycurl.URL, "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc")
    c.setopt(pycurl.HTTPHEADER, ['SOAPAction: http://tempuri.org/IConsultaCFDIService/Consulta','Content-Type: text/xml; charset=utf-8'])
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDSIZE, filesize)
    c.setopt(pycurl.READFUNCTION, fin.read)
    c.perform()
    c.close()
    os.unlink(filename)
    
    body = buf.getvalue()
    return body
