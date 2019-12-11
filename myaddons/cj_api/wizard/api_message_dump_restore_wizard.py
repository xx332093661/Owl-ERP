# -*- coding: utf-8 -*-
import csv
import os

from odoo import models, api, fields
from odoo.exceptions import ValidationError, UserError


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
        files = []
        dir_path = os.path.join(self.env['ir.attachment']._filestore(), 'api_message')
        for line in self.line_ids:
            message_dump = line.dump_id
            # path = message_dump.path
            path = os.path.join(dir_path, message_dump.name)
            files.append(path)
            with open(path, 'r', encoding='utf-8') as f:
                messages = csv.DictReader(f)
                for message in messages:
                    message.pop('create_date', False)
                    message.pop('write_date', False)
                    message.pop('id', False)
                    error_no = message.pop('error_no', '')
                    error_msg = message.pop('error_msg', '')
                    interface_param = message.pop('interface_param', '')
                    interface_url = message.pop('interface_url', '')
                    if error_no == 'False':
                        error_no = ''
                    if error_msg == 'False':
                        error_msg = ''
                    if interface_param == 'False':
                        interface_param = ''
                    if interface_url == 'False':
                        interface_url = ''

                    message.update({
                        'error_no': error_no,
                        'error_msg': error_msg,
                        'interface_param': interface_param,
                        'interface_url': interface_url,
                    })
                    vals_list.append(message)

        if vals_list:
            message_obj.create(vals_list)

        self.line_ids.mapped('dump_id').unlink()

        # # 暂时不删除文件(因做了文件夹同步，删不掉)
        # for f in files:
        #     os.remove(f)

    @api.multi
    def button_download(self):
        """下载"""
        raise UserError('未实现的方法')


class ApiMessageDumpRestoreWizardLine(models.TransientModel):
    _name = 'api.message.dump.restore.wizard.line'
    _description = '下载或恢复转储的数据'

    wizard_id = fields.Many2one('api.message.dump.restore.wizard', '向导')
    dump_id = fields.Many2one('api.message.dump', '文件名', required=0)
    message_names = fields.Text('存储队列', related='dump_id.message_names', readonly=1)
    state = fields.Selection(string='队列状态', related='dump_id.state', readonly=1)



