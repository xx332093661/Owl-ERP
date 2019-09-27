# -*- coding: utf-8 -*-
import logging

from odoo import api
from odoo.exceptions import MissingError
from odoo.models import BaseModel

_logger = logging.getLevelName(__name__)


@api.multi
def read(self, fields=None, load='_classic_read'):
    """ res.users、res.company、res.partner等基础model，在继承时，如果添加新的字段，未升级之前，程序会报错
    """
    # check access rights
    self.check_access_rights('read')
    fields = self.check_field_access_rights('read', fields)

    # split fields into stored and computed fields
    stored, inherited, computed, cols = [], [], [], []
    if self._table in ['res_users', 'res_company', 'res_partner']:
        self._cr.execute("""SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema='public' AND TABLE_NAME='%s'""" % self._table)  # 查询列
        cols = [col for (col,) in self._cr.fetchall()]

    for name in fields:
        field = self._fields.get(name)
        if field:
            if field.store:
                if self._table in ['res_users', 'res_company', 'res_partner']:
                    if field.type in ['integer', 'char', 'float', 'text', 'many2one', 'selection', 'html', 'monetary', 'date', 'datetime', 'reference', 'boolean']:
                        if name in cols:
                            stored.append(name)
                    elif field.type == 'binary':
                        if name in cols:
                            stored.append(name)
                        else:
                            self._cr.execute("""SELECT * FROM ir_attachment WHERE res_model = '%s' AND res_field = '%s'""" % (self._name, name))
                            if len(self._cr.fetchall()) != 0:
                                stored.append(name)
                    else:
                        stored.append(name)
                else:
                    stored.append(name)
            elif field.base_field.store:
                inherited.append(name)
            else:
                computed.append(name)
        else:
            _logger.warning("%s.read() with unknown field '%s'", self._name, name)

    # fetch stored fields from the database to the cache; this should feed
    # the prefetching of secondary records
    self._read_from_database(stored, inherited)

    # retrieve results from records; this takes values from the cache and
    # computes remaining fields
    self = self.with_prefetch(self._prefetch.copy())
    data = [(record, {'id': record._ids[0]}) for record in self]
    use_name_get = (load == '_classic_read')
    for name in (stored + inherited + computed):
        convert = self._fields[name].convert_to_read
        # restrict the prefetching of self's model to self; this avoids
        # computing fields on a larger recordset than self
        self._prefetch[self._name] = set(self._ids)
        for record, vals in data:
            # missing records have their vals empty
            if not vals:
                continue
            try:
                vals[name] = convert(record[name], record, use_name_get)
            except MissingError:
                vals.clear()
    result = [vals for record, vals in data if vals]

    return result


BaseModel.read = read

