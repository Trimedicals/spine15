# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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
        ('3','Lumbar Anterior'),
        ('4','Lumbar Lateral'),
        ('5','Lumbar Posterior'),
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
    

 

    @api.depends('order_line.customer_lead', 'date_order', 'order_line.state')
    def _compute_expected_date(self):
       
        self.mapped("order_line")  # Prefetch indication
        for order in self:
            if not order.is_rental_order:
                dates_list = []
                for line in order.order_line.filtered(lambda x: x.state != 'cancel' and not x._is_delivery() and not x.display_type):
                    dt = line._expected_date()
                    dates_list.append(dt)
                if dates_list:
                    order.expected_date = fields.Datetime.to_string(min(dates_list))
                else:
                    order.expected_date = False
            else:
                dates_list = []
                for line in order.order_line.filtered(lambda x: x.state != 'cancel' and not x._is_delivery() and not x.display_type and x.is_rental):
                    dt = line._expected_date()
                    dates_list.append(dt)
                if dates_list:
                    order.expected_date = fields.Datetime.to_string(min(dates_list))
                else:
                    order.expected_date = False





class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _expected_date(self):
        self.ensure_one()
        if not self.order_id.is_rental_order:
            res = super(SaleOrderLine, self)._expected_date()
            return res
        return self.reservation_begin or fields.Datetime.now()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
