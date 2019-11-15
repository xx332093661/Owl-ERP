# -*- coding: utf-8 -*-
import csv

from odoo import models, api, fields
from odoo.exceptions import ValidationError


class ApiMessageDumpRestoreWizard(models.TransientModel):
    _name = 'api.message.dump.restore.wizard'
    _description = '下载或恢复转储的数据向导'

    line_ids = fields.One2many('api.message.dump.restore.wizard.line', 'wizard_id', '明细')

    @api.multi
    def button_restore(self):
        """恢复数据"""
        message_obj = self.env['api.message']

        if not self.line_ids:
            raise ValidationError('请选择要恢复或下载的文件！')

        vals_list = []
        for line in self.line_ids:
            message_dump = line.dump_id
            path = message_dump.path
            with open(path, 'r') as f:
                messages = csv.DictReader(f)
                for message in messages:
                    message.pop('create_date', False)
                    message.pop('write_date', False)
                    message.pop('id', False)
                    vals_list.append(message)

        if vals_list:
            message_obj.create(vals_list)

        self.line_ids.mapped('dump_id').unlink()

    @api.multi
    def button_download(self):
        """下载"""
        raise ValidationError('未实现的方法')


class ApiMessageDumpRestoreWizardLine(models.TransientModel):
    _name = 'api.message.dump.restore.wizard.line'
    _description = '下载或恢复转储的数据'

    wizard_id = fields.Many2one('api.message.dump.restore.wizard', '向导')
    dump_id = fields.Many2one('api.message.dump', '文件名', required=1)
    message_names = fields.Text('存储队列', related='dump_id.message_names', readonly=1)



