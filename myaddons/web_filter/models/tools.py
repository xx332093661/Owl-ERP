# -*- coding: utf-8 -*-
import os
from lxml import etree
import logging

from odoo.tools import view_validation
from odoo import tools
from odoo.tools.view_validation import _relaxng_cache

_logger = logging.getLogger(__name__)


def relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        if view_type == 'tree':
            path = os.path.join('web_filter', 'rng', '%s_view.rng' % view_type)
        else:
            path = os.path.join('base', 'rng', '%s_view.rng' % view_type)

        with tools.file_open(path) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception('Failed to load RelaxNG XML schema for views validation')
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


view_validation.relaxng = relaxng




