# -*- coding: utf-8 -*-
import logging

from odoo import models, api, tools
from odoo.modules import get_module_path, get_module_resource
from odoo.modules.module import get_module_filetree, loaded

_logger = logging.getLogger(__name__)


class Translation(models.Model):
    """
    主要功能：
        通过重写po文件，覆盖原有的翻译
    """
    _inherit = 'ir.translation'

    def _get_import_cursor(self):
        """可以通过重写po文件，覆盖原有的翻译"""
        return super(Translation, self.with_context(overwrite=True))._get_import_cursor()

    def _load_base_lang(self, module_name, base_lang_code, lang, context):
        """load base language"""
        if base_lang_code:
            base_trans_file = get_module_resource(module_name, 'i18n', base_lang_code + '.po')
            if base_trans_file:
                _logger.info('module %s: loading base translation file %s for language %s',
                             module_name, base_lang_code, lang)
                tools.trans_load(self._cr, base_trans_file, lang, verbose=False, module_name=module_name, context=context)
                context['overwrite'] = True  # make sure the requested translation will override the base terms later

            # i18n_extra folder is for additional translations handle manually (eg: for l10n_be)
            base_trans_extra_file = get_module_resource(module_name, 'i18n_extra', base_lang_code + '.po')
            if base_trans_extra_file:
                _logger.info('module %s: loading extra base translation file %s for language %s',
                             module_name, base_lang_code, lang)
                tools.trans_load(self._cr, base_trans_extra_file, lang, verbose=False, module_name=module_name, context=context)
                context['overwrite'] = True  # make sure the requested translation will override the base terms later

    def _load_main_translation(self, module_name, lang_code, lang, context):
        """load the main translation file"""
        file_suffix = '%s.po' % lang_code

        trans_files = get_module_filetree(module_name, 'i18n')
        if trans_files:
            for trans_file in trans_files:
                if module_name == 'cj_base' and trans_file.split('.')[0] not in loaded:
                    continue

                if not trans_file.endswith(file_suffix):
                    continue

                _logger.info('module %s: loading translation file (%s) for language %s',
                             module_name, trans_file, lang)
                trans_file = get_module_resource(module_name, 'i18n', trans_file)
                tools.trans_load(self._cr, trans_file, lang, verbose=False, module_name=module_name, context=context)
        elif lang_code != 'en_US':
            _logger.info('module %s: no translation for language %s', module_name, lang_code)

        trans_extra_file = get_module_resource(module_name, 'i18n_extra', lang_code + '.po')
        if trans_extra_file:
            _logger.info('module %s: loading extra translation file (%s) for language %s',
                         module_name, lang_code, lang)
            tools.trans_load(self._cr, trans_extra_file, lang, verbose=False, module_name=module_name, context=context)

    @api.model_cr_context
    def load_module_terms(self, modules, langs):
        """ Load PO files of the given modules for the given languages. """
        # make sure the given languages are active
        res_lang = self.env['res.lang'].sudo()
        for lang in langs:
            res_lang.load_lang(lang)

        # load i18n files
        for module_name in modules:
            if not get_module_path(module_name):
                continue

            for lang in langs:
                context = dict(self._context)
                lang_code = tools.get_iso_codes(lang)
                base_lang_code = None
                if '_' in lang_code:
                    base_lang_code = lang_code.split('_')[0]

                # Step 1: for sub-languages, load base language first (e.g. es_CL.po is loaded over es.po)
                self._load_base_lang(module_name, base_lang_code, lang, context)

                # Step 2: then load the main translation file, possibly overriding the terms coming from the base language
                self._load_main_translation(module_name, lang_code, lang, context)

        return True
