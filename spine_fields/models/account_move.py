# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_id = fields.Many2one(string="Pagador")

    commission_agent_id = fields.Many2one('res.partner', string="Comisionista")
    doctor_id = fields.Many2one('res.partner', string="Doctor")
    hospital_id = fields.Many2one('res.partner', string="Hospital")
    paciente_id = fields.Many2one('res.partner', string="Paciente")
    first_adviser_id = fields.Many2one('res.partner', string="Asesor Quirúrjico 1")
    second_adviser_id = fields.Many2one('res.partner', string="Asesor Quirúrjico 2")
    episode_number = fields.Char(string="Número de Episodio")
    commitment_date = fields.Datetime(string="Fecha Cirugía")
    surgery_city_id = fields.Many2one('res.city', string="Lugar de la cirugía")
    surgery_type = fields.Selection(selection=[
        ('1','Lumbar'),
        ('3','Lumbar Anterior'),
        ('4','Lumbar Lateral'),
        ('5','Lumbar Posterior'),
        ('2','Cervical'),
        ('6','Cervical Anterior'),
        ('7','Cervical Posterior'),
        ('8','Torácica Lateral'),
        ('9','Torácica Posterior'),
        ], string="Tipo de Cirugía")
    procedure_type = fields.Selection(selection=[
        ('1','Lateral / Escoliosis'),
        ('2','Cemento / Ablación'),
        ('3','Procedimientos Generales'),
        ('4','Apoyo'),
        ('5','Entrenamiento'),
        ], string="Tipo de Procedimiento")
    


   
    def get_sale_orders(self):
        res=[]
        sale_orders=self.invoice_origin.split(",") if self.invoice_origin else ""
        for sale_order in sale_orders:
            sale_order_id = self.env['sale.order'].search([('name','=',sale_order.strip())], limit=1)
            if sale_order_id :
                res.append(sale_order_id)
        return res

    def get_sale_order(self):
        sale_orders=self.get_sale_orders()
        return sale_orders and sale_orders[0] or False


    def update_surgery_fields(self):
        for invoice in self:
           sale_order_id=invoice.get_sale_order()
           if sale_order_id:
               vals={
                     'commission_agent_id':sale_order_id.commission_agent_id,
                     'doctor_id':sale_order_id.doctor_id,
                     'hospital_id':sale_order_id.hospital_id,
                     'paciente_id':sale_order_id.paciente_id,
                     'first_adviser_id':sale_order_id.first_adviser_id,
                     'second_adviser_id':sale_order_id.second_adviser_id,
                     'episode_number': sale_order_id.episode_number,
                     'commitment_date':sale_order_id.commitment_date,
                     'surgery_city_id': sale_order_id.surgery_city_id,
                     'surgery_type': sale_order_id.surgery_type,
                     'procedure_type': sale_order_id.procedure_type

                       }
               invoice.write(vals)
        return



    @api.model
    def create(self, vals):
        
        invoice = super(AccountMove, self).create(vals)
        invoice.update_surgery_fields()
        return invoice





# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
