#-*- coding: utf-8 -*-
from odoo import models, fields, api, _
from .files import TempFileTransaction
import base64
import os
import inspect
import xml.etree.ElementTree as ET
import csv
import datetime

try:
    import wget
except ImportError:
   raise ImportError( 'This module needs wget, please install it in your system first. (sudo pip3 install wget)')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    url_blacklist_sat = fields.Char("URL blacklist SAT", config_parameter='url_blacklist_sat')

class VatBlacklist(models.Model):
    _name = 'vat.blacklist'
    _description = 'vat.blacklist'
    _rec_name= 'vat'
   
    vat = fields.Char(string='RFC', required=True)
    full_name = fields.Char(string='Razon Social')
    message = fields.Char(string='Mensaje')
    status = fields.Char(string='Estado ante el SAT', required=True)
    fecha_publicacion = fields.Date(string='Fecha Publicacion')
    
    def init(self):
        self.update_blacklist()

    def update_blacklist(self):
        url=self.env['ir.config_parameter'].sudo().get_param('url_blacklist_sat') or 'http://omawww.sat.gob.mx/cifras_sat/Documents/Definitivos.csv'
        try:
            os.remove("/tmp/vat_blacklisted.csv")
        except OSError:
            pass
        try:
            filename = wget.download(url, bar=False, out="/tmp/vat_blacklisted.csv")
        except:
            return False
        if filename:
             
            with open(filename, newline='', encoding='latin-1') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
                i = 0
                for row in spamreader:
                    i+=1
                    if i == 1 :
                        message=row[0]
                    if i < 4 :
                        continue
                    if i == 4 :
                        blacklist = self.with_context(active_test=False).search([])
                        if blacklist:
                            blacklist.unlink()
                    try:
                        vat=row[1] or False
                        full_name=row[2] or False
                        status=row[3] or False
                        fecha=datetime.datetime.strptime(row[12],'%d/%m/%Y')
                    except:
                        fecha = False
                        vat= False
                        full_name= False
                        status= False
                    if vat and full_name and status:
                        self.create({'vat': vat.upper(),
                            'full_name': full_name,
                            'status': status,
                            'fecha_publicacion': fecha,
                            'message': message})
            return True
                    
 

class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_partners = fields.Many2many('res.partner', string="Empresas permitidas")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    factura_subida = fields.Boolean("Factura subida", default=False, readonly=True)

    
    def copy(self, default=None):
        if default is None: default = {}
        default.update({'factura_subida': False})
        new_id = super(PurchaseOrder, self).copy(default=default)
        return new_id

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'


    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()
        res = super()._is_required_for_invoice(invoice)
        if self.code == 'cfdi_3_3':

        # Determine on which invoices the Mexican CFDI must be generated.
            return invoice.move_type in ('out_invoice', 'out_refund') and invoice.country_code == 'MX' and not invoice.creada_de_xml
        return res



class AccountInvoice(models.Model):
    _inherit = "account.move"

    creada_de_xml = fields.Boolean(string="Creada a partir de CFDI", default=False, copy=False, readonly=True)

    l10n_mx_edi_cfdi_uuid = fields.Char(string='Fiscal Folio', copy=False, readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_cfdi_values', store=True, compute_sudo=False)


    def action_subir_xml(self):
        context = dict(self.env.context or {})
        context['active_ids'] = [self.id]
        context['active_id'] = self.id
        context["active_model"] = "account.move"

        data_obj = self.env['ir.model.data']
        view = data_obj._xmlid_to_res_id('validar_facturas.vf_subir_form')
        wiz_id = self.env['validar_facturas.subir.factura'].create({})
        return {
             'name': _('Subir XML y PDF'),
             'type': 'ir.actions.act_window',
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'validar_facturas.subir.factura',
             'views': [(view, 'form')],
             'view_id': view,
             'target': 'new',
             'res_id': wiz_id.id,
             'context': context,
         }

    
    def validar_xml(self, fname_xml):
        current_path = os.path.dirname(os.path.abspath(
                inspect.getfile(inspect.currentframe())))
        tmpfiles = TempFileTransaction()
        fname_xsd = self._context.get('xml_xsd', '')
        fname_xsd = current_path + fname_xsd
        fname_xml_sello = tmpfiles.save(fname_xml, 'xml_sin_sello_validar')
        xml_message = ""
        valido=False
        try:
            command = "xmllint --noout --schema  %s  --encode utf-8 %s 2>&1"%(fname_xsd, fname_xml_sello)
            out = os.popen(command).read().strip()
            if out and not out.endswith("validates"):
                xml_message = "La estructura del comprobante es  inválida: %s\n"% out
            else:
                xml_message = "La estructura del comprobante es  válida:\n %s\n"% out
                valido=True
            tmpfiles.clean()
        except ValueError as e:
            xml_message = str(e)
        except Exception as e:
            xml_message = str(e)
        return valido,xml_message

    def _get_xml_datas(self, xml_sellado):
        res = {
            'importe_total': 0.0,
            'version': '1.0',
            'tipo_comprobante': 'ingreso',
            'certificado_sat': '',
            'certificado_emisor': '',
            'fecha_emision': '',
            'fecha_certificacion': '',
            'uuid': '',
            'rfc_emisor': '',
            'nombre_emisor': '',
            'rfc_receptor': '',
            'nombre_receptor': ''
        }
        try:
            root = ET.fromstring(xml_sellado)
            res['importe_total'] = float(root.attrib.get("total", root.attrib.get('Total',False)))
            res['version'] = root.attrib.get('version',root.attrib.get('Version',False))
            res['tipo_comprobante'] = root.attrib.get('tipoDeComprobante',root.attrib.get('TipoDeComprobante',False))
            res['certificado_emisor'] = root.attrib.get('noCertificado',root.attrib.get('NoCertificado',False))
            res['fecha_emision'] = root.attrib.get('fecha',root.attrib.get('Fecha',False))
            for child in root:
                if child.tag.endswith("Emisor"):
                    res['nombre_emisor'] = child.attrib.get('nombre',child.attrib.get('Nombre',False))
                    res['rfc_emisor'] = child.attrib.get('rfc',child.attrib.get('Rfc',False))
                elif child.tag.endswith("Receptor"):
                    res['nombre_receptor'] = child.attrib.get('nombre',child.attrib.get('Nombre',False))
                    res['rfc_receptor'] = child.attrib.get('rfc',child.attrib.get('Rfc',False))
                elif child.tag.endswith("Complemento"):
                    for child2 in child:
                        if child2.tag.endswith("TimbreFiscalDigital"):
                            res['uuid'] = child2.attrib["UUID"]
                            res['certificado_sat'] = child2.attrib.get('noCertificadoSAT',child2.attrib.get('NoCertificadoSAT',False))
                            res['fecha_certificacion'] = child2.attrib["FechaTimbrado"]
            return res

        except:
            pass
        return res

    def _reporte_validacion_xml(self, xml_sellado):
        xml_datas = self._get_xml_datas(xml_sellado)
        validar_xml = """
            <table class="small"  width="95%" style="border-collapse: separate; border-spacing: 0 0px; padding: 0px; padding-top: 0px; padding-bottom: 0px; " cellpadding="0" cellspacing="0" >
                <tbody>
                    <tr><td colspan="2" align="center" bgcolor="#dfe1d2"><h2>Reporte de validación</h2></td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Versión:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{version}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Tipo Comprobante:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{tipo_comprobante}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Certificado SAT:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{certificado_sat}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Certificado Emisor:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{certificado_emisor}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Fecha Emisión:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{fecha_emision}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Fecha Certificación:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{fecha_certificacion}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">UUID:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{uuid}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Importe Total:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{importe_total}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">RFC Emisor:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{rfc_emisor}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Nombre Emisor:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{nombre_emisor}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">RFC Receptor:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{rfc_receptor}</td></tr>
                    <tr><td class="small" style="color:black; font-weight:bold; border-bottom: 1px solid #dfe1d2;" width="25%">Nombre Receptor:</td><td width="75%" style="border-bottom: 1px solid #dfe1d2;">{nombre_receptor}</td></tr> 
                </tbody>
            </table>
            <br />
            <br />
        """.format(**xml_datas)
        return validar_xml

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        '''
        fix cfdi_data  with wrong schemaLocation name space declaration
        '''
        self.ensure_one()
        if not cfdi_data:
            signed_edi = self._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)
       
        if cfdi_data:
            if type(cfdi_data) != bytes:
                cfdi_data = cfdi_data.encode('utf-8')
            cfdi_data = cfdi_data.replace(b'xmlns:schemaLocation',b'xsi:schemaLocation')
        return super()._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi_data)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
