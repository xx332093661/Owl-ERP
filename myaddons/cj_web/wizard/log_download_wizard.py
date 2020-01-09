# -*- coding: utf-8 -*-
import os

from odoo import fields, models, api
from odoo.tools import config
from odoo.exceptions import ValidationError


class LogDownloadWizard(models.TransientModel):
    _name = 'log.download.wizard'
    _description = '日志下载向导'

    line_ids = fields.One2many('log.download.wizard.line', 'wizard_id', '文件列表')

    @api.model
    def default_get(self, fields_list):
        if not config.get('logfile'):
            return {}

        logfile = config['logfile']  # 日志文件
        dir_name = os.path.dirname(logfile)  # 日志目录

        result = []
        for file in os.listdir(dir_name):
            path = os.path.join(dir_name, file)
            if os.path.isfile(path):
                result.append((0, 0, {'name': file, 'name_copy': file}))

        return {
            'line_ids': result
        }

    @api.multi
    def button_download(self):
        """下载"""
        if not self.line_ids:
            raise ValidationError('请选择要下载的文件！')

        return {
            'type': 'ir.actions.act_url',
            'url':   '/web/log/download/%s' % self.id,
            'target': 'new',
        }


class LogDownloadWizardLine(models.TransientModel):
    _name = 'log.download.wizard.line'
    _description = '日志下载向导明细'

    name = fields.Char('文件名', required=1)
    name_copy = fields.Char('文件名', readonly=1)
    wizard_id = fields.Many2one('log.download.wizard', '向导')

    @api.model
    def create(self, vals):
        vals['name_copy'] = vals['name']
        return super(LogDownloadWizardLine, self).create(vals)
