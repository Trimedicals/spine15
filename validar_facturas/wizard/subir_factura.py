# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

import base64
import urllib.request, urllib.error, urllib.parse
import re
import os
import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime

from .soap_hacienda import ConsultaCFDI
import suds
from suds.client import Client

class validar_facturas_subir_factura_line(models.TransientModel):
    _name = "validar_facturas.subir.factura.line"
    _description = "validar_facturas.subir.factura.line"

    clave = fields.Char(string="Clave")
    cantidad = fields.Float(string="Cantidad XML")
    importe = fields.Float(string="Importe XML")
    udm = fields.Char(string="UdM XML")
    cantidad_fac = fields.Float(string="Cantidad factura")
    importe_fac = fields.Float(string="Importe factura")
    udm_fac = fields.Char(string="UdM factura")
    wizard_id = fields.Many2one("validar_facturas.subir.factura")
    ok = fields.Boolean(string="Ok")


class validar_facturas_subir_factura(models.TransientModel):
    _name = "validar_facturas.subir.factura"
    _description = "validar_facturas.subir.factura"

    xml = fields.Binary(string="XML")
    pdf = fields.Binary(string="PDF")
    codigo = fields.Char(string="Codigo Estatus")
    estado = fields.Char(string="Estado")
    next = fields.Boolean(string="Continuar", default=False)
    estructura_valida = fields.Boolean(string="Estructura Válida", default=False, readonly=True)
    uuid = fields.Char(string="UUID")
    validar_partidas = fields.Boolean(string="Validar partidas", default=True)
    total_xml = fields.Float(string="Total xml")
    total_fac = fields.Float(string="Total factura")
    all_ok = fields.Boolean(string="Todo bien")
    lines = fields.One2many("validar_facturas.subir.factura.line", "wizard_id", string="Partidas")
    mensajes = fields.Text(string="Mensajes")
    show_lines = fields.Boolean(string="Show lines", default=False)
    reporte_validation_xml = fields.Html("Validar XML")
    message_validation_xml = fields.Html("Validar XML")
    moneda = fields.Many2one("res.currency", string="Moneda")
    product_id = fields.Many2one("product.product", string="Producto que aparecerá en la factura")
    journal_id = fields.Many2one("account.journal", string="Diario de Factura")
    uuid_duplicado = fields.Boolean(string="UUID Duplicado")
    host= fields.Char(string='Host', default=lambda self: self.env['ir.config_parameter'].sudo().search([('key','=','pac_host')], limit=1).value or 'https://facturacion.finkok.com/servicios/soap', readonly=True)
    user= fields.Char(string='User', default=lambda self: self.env['ir.config_parameter'].sudo().search([('key','=','pac_user')], limit=1).value or self.env.company.l10n_mx_edi_pac_username, invisible=True)
    password= fields.Char(string='Password', default=lambda self: self.env['ir.config_parameter'].sudo().search([('key','=','pac_password')], limit=1).value or self.env.company.l10n_mx_edi_pac_password, invisible=True)
    pac_xml_valido=fields.Boolean('XML Válido PAC', default=False, readonly=True)
    pac_sello_valido=fields.Boolean(string="Sello Válido PAC", default=False, readonly=True)
    pac_sello_sat_valido=fields.Boolean(string="Sello SAT Válido PAC", default=False, readonly=True)
    pac_estado = fields.Char(string="Estado PAC", readonly=True)
    pac_cod_estatus= fields.Char(string="Codigo Estatus PAC", readonly=True)
    message_validation_pac = fields.Html("Validación PAC", readonly=True)
    ignore_pac_error = fields.Boolean(string="Ignore PAC Error", default=False)
   


    def force_next(self):
        self.next = True
        return


    # Factura de cliente
    def get_out_invoice_data(self):
        context = self._context
        xml = base64.decodebytes(self.xml)
        uid_company_id = self.env.company
        data = {
            'move_type': 'out_invoice',
            'journal_id': self.journal_id and self.journal_id.id or False
        }        
        partner_obj = self.env['res.partner']
        inv_line_obj = self.env['account.move.line']

        root = ET.fromstring(xml)
        fecha = root.attrib.get("fecha") or root.attrib.get("Fecha")
        version = root.attrib.get("Version") or root.attrib.get("version")
        data["invoice_date"] = fecha.split("T")[0]
        fpos = False
        if root.attrib.get("serie") or root.attrib.get("Serie"):
            data["number"] = root.attrib.get("serie") or root.attrib.get("Serie")
            data["name"] = root.attrib.get("serie") or root.attrib.get("Serie")
        if root.attrib.get("folio") or root.attrib.get("Folio"):
            if 'number' in data.keys():
                data["number"] = "%s-%s" % (data['number'],root.attrib.get("folio") or root.attrib.get("Folio"))
            else:
                data["number"] = root.attrib.get("folio") or root.attrib.get("Folio")
            if 'name' in data.keys():
                data["name"] = "%s-%s" %(data['name'], root.attrib.get("folio") or root.attrib.get("Folio"))
            else:
                data["name"] = root.attrib.get("folio") or root.attrib.get("Folio")
        del data['number']
        descuento = root.attrib.get("descuento") or root.attrib.get("Descuento")
        data["amount_total"] = root.attrib.get("total") or root.attrib.get("Total")

        last_account_id = None
        last_account_id = self.product_id.property_account_income_id and self.product_id.property_account_income_id.id or self.product_id.categ_id.property_account_income_categ_id.id
        for node in root:
            if node.tag.endswith("Receptor"):
                vat = node.attrib.get("rfc") or node.attrib.get("Rfc")
                pais = node.attrib.get("ResidenciaFiscal",False)
                partner_id = partner_obj.search([('vat', '=', vat),('parent_id','=',False),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=1)
                if not partner_id:
                    # Crear partner para cliente 
                    pais_id = False
                    if pais:
                        pais_id = self.env['res.country'].search([('l10n_mx_edi_code','=',pais)])
                    vals={
                        'vat':vat, 
                        'country_id': pais_id and pais_id.id or self.env.company.partner_id.country_id.id, 
                        'company_type':'company', 
                        'l10n_mx_type_of_operation':'85', 
                        'is_company':True, 
                        'supplier_rank':0,
                        'customer_rank':1,
                        'name': node.attrib.get("nombre") or node.attrib.get("Nombre") or vat
                    }
                    partner_id = partner_obj.create(vals)
                    if not partner_id:
                        raise UserError(_( "No se encontró en el sistema un cliente con el RFC %s"%vat))
                data["partner_id"] = partner_id.id
                data["invoice_payment_term_id"] = partner_id.property_payment_term_id.id
                data["user_id"] = partner_id.user_id.id
            elif node.tag.endswith("Conceptos"):
                for concepto in node:

                    line_vals = {}
                    line_vals["product_id"] = self.product_id.id
                    taxes=[]
                    for tax in self.sudo().product_id.taxes_id:
                        if tax.company_id == self.env.company :
                            taxes.append((4,tax.id))
                    line_vals['tax_ids'] = taxes
                    line_vals["account_id"] = last_account_id
                    line_vals["name"] = concepto.attrib.get("descripcion") or concepto.attrib.get("Descripcion")
                    line_vals["quantity"] = concepto.attrib.get("cantidad") or concepto.attrib.get("Cantidad")
                    line_vals["price_unit"] = concepto.attrib.get("valorUnitario") or concepto.attrib.get("ValorUnitario") 
                    line_vals["discount"] = float(concepto.attrib.get('Descuento', 0.0))*100/float(concepto.attrib.get('Importe',0.00000001)) or 0.0

                    if self.product_id.uom_id:
                        line_vals["product_uom_id"] = self.product_id.uom_id.id
                    data.setdefault("invoice_line_ids", []).append((0,0,line_vals))
                if descuento and version == '3.2':
                    disc_line_vals = {
                        'name': 'Descuento',
                        'quantity': 1,
                        'price_unit': -float(descuento),
                        'account_id': last_account_id,
                        'tax_ids': taxes
                    }
                    data.setdefault("invoice_line_ids", []).append((0,0,disc_line_vals))
        return data




    # Factura de proveedor
    def get_invoice_data(self): 
        context = self._context
        xml = base64.decodebytes(self.xml)

        uid_company_id = self.env.company
        data = {
            'move_type': 'in_invoice',
            'journal_id': self.journal_id and self.journal_id.id or False
        }        
        partner_obj = self.env['res.partner']
        inv_line_obj = self.env['account.move.line']

        root = ET.fromstring(xml)
        fecha = root.attrib.get("fecha") or root.attrib.get("Fecha")
        version = root.attrib.get("Version") or root.attrib.get("version")
        data["invoice_date"] = fecha.split("T")[0]
        fpos = False
        if root.attrib.get("serie") or root.attrib.get("Serie"):
            data["supplier_invoice_number"] = root.attrib.get("serie") or root.attrib.get("Serie")
            data["ref"] = root.attrib.get("serie") or root.attrib.get("Serie")
            data["name"] = root.attrib.get("serie") or root.attrib.get("Serie")
        if root.attrib.get("folio") or root.attrib.get("Folio"):
            if 'supplier_invoice_number' in data.keys():
                data["supplier_invoice_number"] = "%s-%s" % (data['supplier_invoice_number'],root.attrib.get("folio") or root.attrib.get("Folio"))
            else:
                data["supplier_invoice_number"] = root.attrib.get("folio") or root.attrib.get("Folio")
            if 'name' in data.keys():
                data["name"] = "%s-%s" %(data['name'], root.attrib.get("folio") or root.attrib.get("Folio"))
            else:
                data["name"] = root.attrib.get("folio") or root.attrib.get("Folio")
            if 'reference' in data.keys():
                data["ref"] = "%s-%s" %(data['ref'], root.attrib.get("folio") or root.attrib.get("Folio"))
            else:
                data["ref"] = root.attrib.get("folio") or root.attrib.get("Folio")
        if 'supplier_invoice_number' in data.keys():
            del data['supplier_invoice_number']
        descuento = root.attrib.get("descuento") or root.attrib.get("Descuento")
        data["amount_total"] = root.attrib.get("total") or root.attrib.get("Total")

        last_account_id = None
        last_account_id = self.product_id.property_account_expense_id and self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id
        combustible = False
        for node in root:
            if node.tag.endswith("Emisor"):
                vat = node.attrib.get("rfc") or node.attrib.get("Rfc")
                partner_id = partner_obj.search([('vat', '=', vat),('parent_id','=',False),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=1)
                if not partner_id:
                    # Crear partner proveeedor
                    vals={
                        'vat':vat, 
                        'country_id': self.env.company.partner_id.country_id.id, 
                        'company_type':'company', 
                        'l10n_mx_type_of_operation':'85', 
                        'is_company':True, 
                        'supplier_rank':1,
                        'customer_rank':0,
                        'name': node.attrib.get("nombre") or node.attrib.get("Nombre") or vat
                    }
                    partner_id = partner_obj.create(vals)
                    if not partner_id:
                        raise UserError(_( "No se encontró en el sistema un  proveedor con el RFC %s"%vat))
                data["partner_id"] = partner_id.id
                data["invoice_payment_term_id"] = partner_id.property_supplier_payment_term_id.id
            elif node.tag.endswith("Conceptos") and not combustible:
                for concepto in node:

                    line_vals = {}
                    line_vals["product_id"] = self.product_id.id
                    taxes=[]
                    for tax in self.sudo().product_id.supplier_taxes_id:
                        if tax.company_id == self.env.company :
                            taxes.append((4,tax.id))
                    line_vals['tax_ids'] = taxes
                    line_vals["account_id"] = last_account_id
                    line_vals["name"] = concepto.attrib.get("descripcion") or concepto.attrib.get("Descripcion")
                    line_vals["quantity"] = concepto.attrib.get("cantidad") or concepto.attrib.get("Cantidad")
                    line_vals["price_unit"] = concepto.attrib.get("valorUnitario") or concepto.attrib.get("ValorUnitario") 

                    if self.product_id.uom_id:
                        line_vals["product_uom_id"] = self.product_id.uom_id.id
                    data.setdefault("invoice_line_ids", []).append((0,0,line_vals))
                if descuento:
                    disc_line_vals = {
                        'name': 'Descuento',
                        'quantity': 1,
                        'price_unit': -float(descuento),
                        'account_id': last_account_id,
                        'tax_ids': taxes
                    }
                    data.setdefault("invoice_line_ids", []).append((0,0,disc_line_vals))
            elif node.tag.endswith("Complemento"):
                for nodecomp in node:
                    if nodecomp.tag.endswith("EstadoDeCuentaCombustible"):
                        total = float(nodecomp.attrib.get('Total'))
                        new_total = 0.0
                        taxes=[]
                        for tax in self.sudo().product_id.supplier_taxes_id:
                            if tax.company_id == self.env.company :
                                taxes.append((4,tax.id))
                        for conceptos_combustible in nodecomp:
                            for concepto  in conceptos_combustible:
                                if concepto.tag.endswith("ConceptoEstadoDeCuentaCombustible"):
                                    line_vals = {}
                                    line_vals["product_id"] = self.product_id.id
                                    analytic_account = self.env['account.analytic.account'].search([('company_id', '=', self.env.company.id),('code','=',concepto.attrib.get('Identificador') or False)], limit =1)
                                    analytic_tag = self.env['account.analytic.tag'].search([('company_id', '=', self.env.company.id),('name','=',concepto.attrib.get('Identificador') or False)], limit =1)
                                    line_vals['tax_ids'] = taxes
                                    line_vals["account_id"] = last_account_id
                                    line_vals["analytic_account_id"] = analytic_account and analytic_account.id or False
                                    if analytic_tag:
                                        line_vals["analytic_tag_ids"] = [(4,analytic_tag.id)]
                                    line_vals["name"] = concepto.attrib.get("NombreCombustible")
                                    line_vals["quantity"] = concepto.attrib.get("cantidad") or concepto.attrib.get("Cantidad")
                                    if self.product_id.uom_id:
                                        line_vals["product_uom_id"] = self.product_id.uom_id.id
                                    #Get traslados
                                    importe_traslados = 0
                                    tasa = 0.16
                                    for traslados in concepto:
                                        for traslado in traslados:
                                            if traslado.tag.endswith("Traslado"):
                                                importe_traslados += float(traslado.attrib.get('Importe'))
                                                tasa = float(traslado.attrib.get('TasaOCuota'))
                                    valor_unitario = (importe_traslados / tasa )/float(line_vals['quantity'])
                                    line_vals["price_unit"] = valor_unitario or concepto.attrib.get("valorUnitario") or concepto.attrib.get("ValorUnitario") 
                                    new_total += float(line_vals['price_unit'])*float(line_vals['quantity'])*(1+tasa)
                                    data.setdefault("invoice_line_ids", []).append((0,0,line_vals))
                        if total > new_total:
                            line_vals = {}
                            line_vals["product_id"] = self.product_id.id
                            line_vals["name"] = self.product_id.name
                            line_vals['tax_ids'] = taxes
                            line_vals["account_id"] = last_account_id
                            line_vals["quantity"] = 1
                            if self.product_id.uom_id:
                                line_vals["product_uom_id"] = self.product_id.uom_id.id
                            line_vals["price_unit"] = (total - new_total)/(1+tasa)
                            data.setdefault("invoice_line_ids", []).append((0,0,line_vals))


        return data

    
    def write_att_values(self):
        context = dict(self._context)
        invoice_id = context.get('invoice_id')
        att_obj = self.env['ir.attachment']
        xml_att_values = {
          'name': self.uuid + ".xml",
          'datas': self.xml,
          'description': self.uuid,
          'res_model': "account.move",
          'res_id': invoice_id,
          'type': 'binary'
        }
        pdf_att_values = {
            'name': self.uuid + ".pdf",
            'datas': self.pdf,
            'description': self.uuid,
            'res_model': "account.move",
            'res_id': invoice_id,
            'type': 'binary'
        }
        xml_att=att_obj.create(xml_att_values)
        att_obj.create(pdf_att_values)
        # Create Edi Record
        invoice = self.env['account.move'].browse([invoice_id])
        if invoice.move_type in ['out_invoice','out_refund','in_invoice','in_refund']:
            cfdi_3_3_edi = self.env.ref('l10n_mx_edi.edi_cfdi_3_3')
            edi_obj= self.env['account.edi.document']
            edi_values={
                'move_id':invoice_id,
                'state': 'sent',
                'attachment_id': xml_att.id,
                'edi_format_id': cfdi_3_3_edi.id
                }
            edi_obj.create(edi_values)
        invoice._compute_cfdi_values()    
        invoice.l10n_mx_edi_update_sat_status()    
        return True

    
    def action_upload(self):
        self.ensure_one()
        context = dict(self._context)
        this = self
        invoice_obj = self.env['account.move']
        invoice_id = context.get('active_id')

        view_name = 'validar_facturas.vf_subir_info_sat_form'
        xml = base64.decodebytes(this.xml)
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        objroot = etree.fromstring(xml, parser=parser)
        version= objroot.attrib.get('version',objroot.attrib.get('Version',False))    
        etree.strip_tags(objroot, etree.Comment)
        for child in objroot:
            if child.tag.endswith("Emisor"):    
                vat_emisor = child.attrib.get('rfc',child.attrib.get('Rfc',False))    
            if child.tag.endswith("Receptor"):    
                vat_receptor = child.attrib.get('rfc',child.attrib.get('Rfc',False))    
            if child.tag.endswith("Complemento"):
                for child2 in child:
                    if child2.tag.endswith("TimbreFiscalDigital"):
                        timbre = child2
                        child2.getparent().remove(child2)  
        xml_para_validacion = etree.tostring(objroot)
        uuid = timbre.attrib.get('UUID',False)
        inv_dup = invoice_obj.search([('l10n_mx_edi_cfdi_uuid','=',uuid),('company_id','=',self.env.company.id)])
        if inv_dup:
            raise UserError(_("UUID: %s Duplicado en Factura : %s con Referencia : %s y Estado: %s") % (str(uuid),inv_dup[0].name or '', inv_dup[0].ref or '', inv_dup[0].state))
        if context.get('inv_create', False):
            view_name = 'validar_facturas.vf_crear_info_sat_form'
        xml = base64.decodebytes(this.xml)
        uuid, codigo, estado, currency_id = self._validar_en_hacienda(xml)
        ok = True if codigo.startswith('S') and estado == 'Vigente' else False

        context['xml_file'] = 'xml_cfdi.xml'
        reporte_xml = self.env['account.move']._reporte_validacion_xml(xml)
        
        parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        objroot = etree.fromstring(xml, parser=parser)
        version= objroot.attrib.get('version',objroot.attrib.get('Version',False))    
         
        out_invoice=context['out_invoice'] if 'out_invoice' in context.keys() else False
        journal_id=False
        if out_invoice:
            journal_id = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], order="id asc", limit=1) 
        else:
            journal_id = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], order="id asc", limit=1)
        if version == '3.2':
            context['xml_xsd'] = "SAT/cfdv32.xsd"
            valido, validar_xml = self.env['account.move'].with_context(xml_xsd='/SAT/xsd/cfdv32.xsd').validar_xml(xml_para_validacion)
        elif version == '3.3':
            context['xml_xsd'] = "SAT/cfdv33.xsd"
            valido, validar_xml = self.env['account.move'].with_context(xml_xsd='/SAT/xsd/cfdv33.xsd').validar_xml(xml_para_validacion)
        elif version == '4.0':
            valido, validar_xml = self.env['account.move'].with_context(xml_xsd='/SAT/xsd/cfdv40.xsd').validar_xml(xml_para_validacion)
        vals = {
            'next': ok,
            'estructura_valida': valido or False,
            'codigo': codigo,
            'estado': estado,
            'uuid': uuid,
            'moneda': currency_id and currency_id.id or False,
            'journal_id': journal_id.id if journal_id else False,
            'message_validation_xml': validar_xml, 
            'reporte_validation_xml': reporte_xml
        }
        #validation_pac = self.ValidationPAC()
        validation_pac = False 
        validation_blacklist = self.ValidationBlacklist(vat_emisor=vat_emisor, vat_receptor=vat_receptor)
        if  validation_blacklist and validation_blacklist['error']:
            
            message_validation_blacklist = """ <br /> <br /> <p style="color: red;"> Hubo un error al validar con la lista negra : %s \n </p>""" % validation_blacklist['error']['message']
            vals['message_validation_pac']=message_validation_blacklist
            vals['next'] = False

        if validation_pac and validation_pac['error']:
            
            message_validation_pac = """ <br /> <br /> <p style="color: red;"> Hubo un error al validar con el pac : %s \n </p>""" % validation_pac['error']['message']
            vals['message_validation_pac']=message_validation_pac
            vals['next'] = False
        else:
            vals['pac_xml_valido']=True or validation_pac['xml_valido'] 
            vals['pac_sello_valido']=True or validation_pac['sello_valido'] 
            vals['pac_sello_sat_valido']=True or validation_pac['sello_sat_valido'] 
            vals['pac_estado']='Deshabilitado'or validation_pac['estado']
            vals['pac_cod_estatus']='Deshabilitado' or validation_pac['cod_estatus']

        self.write(vals)

        data_obj = self.env['ir.model.data']
        view = data_obj._xmlid_to_res_id(view_name)
        return {
             'name': _('Subir XML y PDF'),
             'type': 'ir.actions.act_window',
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'validar_facturas.subir.factura',
             'views': [(view, 'form')],
             'view_id': view,
             'target': 'new',
             'res_id': this.id,
             'context': context,
         }

    
    def action_accept(self):
        context = dict(self._context)
        invoice_obj = self.env['account.move']
        invoice_id = context["active_id"]
        purchase_tax_id = None

        xml = base64.decodebytes(self.xml)
        root = ET.fromstring(xml)
        reference=False
        if root.attrib.get("serie") or root.attrib.get("Serie"):
            reference = root.attrib.get("serie") or root.attrib.get("Serie")
        if root.attrib.get("folio") or root.attrib.get("Folio"):
            if reference:
               reference = "%s-%s" %(reference, root.attrib.get("folio") or root.attrib.get("Folio"))
            else:
                reference = root.attrib.get("folio") or root.attrib.get("Folio")

        fecha = root.attrib.get("fecha") or root.attrib.get("Fecha")
        inv = invoice_obj.browse(invoice_id)
        self.with_context(invoice_id=invoice_id).write_att_values()
        inv.write({
            'invoice_date': fecha.split("T")[0] or False,
            'creada_de_xml': True,
            'ref': reference or '',
        #    'name': reference or ''
        })
        
        purchase = self.env['purchase.order'].search([('name','=',inv.invoice_origin)], limit = 1)
        if purchase and reference:
            purchase.partner_ref = reference
        
        #Agregar descuento si el xml tiene descuento


        descuento = root.attrib.get("descuento") or root.attrib.get("Descuento")
        if descuento and float(descuento) > 0.0 :
            uid_company_id = self.env.company
            supplier_taxes_id = self.env['product.template'].new().supplier_taxes_id._origin.id
            if supplier_taxes_id:
                purchase_tax_id = isinstance(supplier_taxes_id, list) and supplier_taxes_id[0] or supplier_taxes_id
            else:
                for line in inv.invoice_line_ids:
                    for tax in line.tax_ids:
                        purchase_tax_id = tax.id
                        break
                    break
            if not purchase_tax_id:
                raise UserError(_("No hay configurado impuesto por defecto de compras"))
            disc_line_vals = {
                'name': 'Descuento',
                'quantity': 1,
                'price_unit': -float(descuento),
                'move_id': invoice_id,
                'tax_ids': [(4,purchase_tax_id)]
            }
            inv.write({
                    'invoice_line_ids': [(0,0,disc_line_vals)],
                 })
            inv._check_balanced()

        
        return { 'type': 'ir.actions.client', 'tag': 'reload' }

   
    def action_procesar(self):
        context = dict(self._context)
        this = self

        xml = base64.decodebytes(this.xml)
        out_invoice=context['out_invoice'] if 'out_invoice' in context.keys() else False
        view_name = 'account.view_move_form'
        if out_invoice:
            data = self.get_out_invoice_data()
        else:
            data = self.get_invoice_data()
        invoice_obj = self.env['account.move']
        data["currency_id"] = this.moneda.id
        data["creada_de_xml"] = True
        invoice_id = invoice_obj.create(data)
        self.with_context(invoice_id=invoice_id.id).write_att_values()
        data_obj = self.env['ir.model.data']
        view = data_obj._xmlid_to_res_id(view_name)
        return {
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view,
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'type': 'ir.actions.act_window',
            'context': context,
            'domain': [],
        }


    
    def _validar_en_hacienda(self, xml):
        context = self._context
        out_invoice=context['out_invoice'] if 'out_invoice' in context.keys() else False
        active_model=context['active_model'] if 'active_model' in context.keys() else False
        active_id=context['active_id'] if 'active_id' in context.keys() else False
        active_obj = False
        if active_model and active_id:
            active_obj =self.env[active_model].browse(active_id)
        currency_id = False
        try:
            root = ET.fromstring(xml)
        except:
            raise UserError(_("El archivo XML parece estar mal formado."))
        total = emisor = receptor = uuid = False
        total = float(root.attrib.get("total",root.attrib.get("Total",False)))
        moneda = root.attrib.get("moneda",root.attrib.get("Moneda",'MXN'))
        if moneda == 'Pesos' or moneda == 'pesos':
            moneda='MXN'
        if moneda:
            currency_id=self.env['res.currency'].search([('name','=',moneda),('active','=',True)], limit=1)
        tipo_comprobante = root.attrib.get('TipoDeComprobante',"I")
        
        if (tipo_comprobante in ['I','i'] and active_obj and  not active_obj.move_type in ['out_invoice','in_invoice']) \
        or (tipo_comprobante in ['E','e'] and active_obj and  not active_obj.move_type in ['out_refund','in_refund']) \
        or (tipo_comprobante in ['E','e'] and not active_obj):
            raise UserError(_("El archivo XML no es del tipo esperado."))
        for child in root:
            if child.tag.endswith("Emisor"):
                emisor = child.attrib.get("rfc") or child.attrib.get("Rfc")
            elif child.tag.endswith("Receptor"):
                receptor = child.attrib.get("rfc") or child.attrib.get("Rfc")
            elif child.tag.endswith("Complemento"):
                for child2 in child:
                    if child2.tag.endswith("TimbreFiscalDigital"):
                        uuid = child2.attrib["UUID"]
        if not all([emisor, receptor, uuid]):
            raise UserError(_("El archivo XML no parece ser un CFDI."))
        user_company = self.env['res.company'].browse(self.env.company.id) or False
        if user_company.partner_id.vat != receptor and not out_invoice :
            raise UserError(_("El RFC de la compañía no coincide el receptor del documento."))
        if user_company.partner_id.vat != emisor and out_invoice:
            raise UserError(_("El RFC de la compañía no coincide con el emisor del documento."))
        integer, decimal = str(total).split('.')
        integer, decimal = str(total).split('.')
        padded_total = integer.rjust(10, '0') + '.' + decimal.ljust(6, '0')
        data = '?re=%s&rr=%s&tt=%s&id=%s'%(emisor, receptor, padded_total, uuid)

        #Checar si hay internet
        import socket
        try:
            response=urllib.request.urlopen('http://google.com',timeout=2)
        except urllib.error.URLError:
            raise UserError(_("Parece que no hay conexion a Internet."))
        except socket.timeout:
            raise UserError(_("Parece que no hay conexion a Internet."))
        resp = ConsultaCFDI(data)
        m = re.search("<a:CodigoEstatus>(.*?)</a:CodigoEstatus>(.*?)<a:Estado>(.*?)</a:Estado>", resp.decode('utf-8'))
        if not m:
            #raise UserError(_("Hubo un error al consultar Hacienda."))
            return uuid, 'Hubo un Error al consultar Hacienda', 'Desconocido', currency_id
        return uuid, m.group(1), m.group(3), currency_id
        #return uuid, 'S - Comprobante Obtenido Satisfactoriamente', 'Vigente', currency_id


    def ValidationPAC(self):
        host_validate = "%s/%s"%(self.host, "validation.wsdl")
        client = Client(host_validate, cache=None)
        contenido = client.service.validate(self.xml.decode('utf-8'), self.user, self.password)
        try:
            error = contenido.error
            return {u'error': {u'message': "Error validar XML \n\n %s "%( error.upper() )}}
        except Exception as  e:
            return {
                "error": False,
                "xml_valido": contenido.xml,
                "sello_valido": contenido.sello,
                "sello_sat_valido": contenido.sello_sat,
                "estado": str('Estado' in contenido.sat.__keylist__ or ''),
                "cod_estatus": str(contenido.sat.CodigoEstatus),
            }
        return {}

    def ValidationBlacklist(self, vat_emisor=False, vat_receptor=False):
        blacklisted_emisor = self.env['vat.blacklist'].search([('vat','=',vat_emisor and vat_emisor.upper())])
        blacklisted_receptor = self.env['vat.blacklist'].search([('vat','=',vat_receptor and vat_receptor.upper())])
        if blacklisted_emisor:
            return {u'error': {u'message': "El RFC : %s emisor de la factura se encuentra en la lista negra del SAT  "%(vat_emisor.upper())}}
        if blacklisted_receptor:
            return {u'error': {u'message': "El RFC : %s receptor de la factura se encuentra en la lista negra del SAT "%(vat_receptor.upper())}}
        return {}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
