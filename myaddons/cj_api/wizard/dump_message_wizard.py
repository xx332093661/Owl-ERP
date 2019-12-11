# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
import os
from itertools import groupby
import csv
import logging
import traceback

from odoo import fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class DumpMessageWizard(models.TransientModel):
    _name = 'dump.message.wizard'
    _description = '转储接口数据向导'

    note = fields.Char('备注')

    def action_dump(self):
        """转储"""
        dump_obj = self.env['api.message.dump']
        message_obj = self.env[self._context['active_model']]

        fields_list = list(message_obj._fields.keys())
        fields_list.pop(fields_list.index('__last_update'))
        fields_list.pop(fields_list.index('display_name'))
        fields_list.pop(fields_list.index('create_uid'))
        fields_list.pop(fields_list.index('write_uid'))
        messages = message_obj.search_read([('id', 'in', self._context['active_ids'])], fields_list, limit=10000, order='id asc')
        if not messages:
            return

        if any([message['state'] == 'draft' or (message['state'] == 'error' and message['attempts'] < 3) for message in messages]):
            raise ValidationError('草稿状态或失败次数小于3次的记录不能转储！')

        tz = self.env.user.tz or 'Asia/Shanghai'
        now = datetime.now(tz=pytz.timezone(tz))
        time = now.strftime("%Y-%m-%d_%H-%M-%S")

        files = []
        try:
            # 创建目录，路径：config['data_dir']/config['db_name']/api_message
            dir_path = os.path.join(self.env['ir.attachment']._filestore(), 'api_message')
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            # 删除原来的
            message_obj.search([('id', 'in', self._context['active_ids'])]).unlink()

            # 创建转储记录
            for state, ms in groupby(sorted(messages, key=lambda x: x['state']), lambda x: x['state']):
                ms = list(ms)
                file_name = '%s-%s.csv' % (time, state, )
                path = os.path.join(dir_path, file_name)

                message_names = [message['message_name'] for message in ms]
                dump_obj.create({
                    'name': file_name,
                    'path': path,
                    'to_date': now.strftime(DATETIME_FORMAT),
                    'message_names': '、'.join(list(set(message_names))),
                    'state': state,
                    'note': self.note
                })

                # 创建文件
                with open(path, 'w', encoding='utf-8')as f:
                    writer = csv.DictWriter(f, fieldnames=fields_list)
                    writer.writeheader()
                    for message in ms:
                        writer.writerow(message)

                files.append(path)
        except:
            _logger.error('转储记录时发生错误！')
            _logger.error(traceback.format_exc())
            for f in files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except IOError:
                        pass

            raise UserError('转储记录时出错！')


