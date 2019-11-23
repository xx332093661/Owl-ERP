# -*- coding: utf-8 -*-
from odoo import api, models
# from odoo.addons.account.models.account_move import AccountMoveLine


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     @api.multi
#     def auto_reconcile_lines(self, amount=None):
#         """增加核销金额参数"""
#         # Create list of debit and list of credit move ordered by date-currency
#         debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
#         credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
#         debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
#         credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
#         # Compute on which field reconciliation should be based upon:
#         if self[0].account_id.currency_id and self[0].account_id.currency_id != self[0].account_id.company_id.currency_id:
#             field = 'amount_residual_currency'
#         else:
#             field = 'amount_residual'
#         #if all lines share the same currency, use amount_residual_currency to avoid currency rounding error
#         if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
#             field = 'amount_residual_currency'
#         # Reconcile lines
#         ret = self._reconcile_lines(debit_moves, credit_moves, field, amount)
#         return ret
#
#     @api.multi
#     def _reconcile_lines(self, debit_moves, credit_moves, field, amount=None):
#         """增加核销金额参数"""
#
#         if not amount:
#             reconcile_amount = float('inf')
#         else:
#             reconcile_amount = amount
#
#         (debit_moves + credit_moves).read([field])
#         to_create = []
#         cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
#         cash_basis_percentage_before_rec = {}
#         dc_vals ={}
#         while (debit_moves and credit_moves):
#             debit_move = debit_moves[0]
#             credit_move = credit_moves[0]
#             company_currency = debit_move.company_id.currency_id
#             # We need those temporary value otherwise the computation might be wrong below
#             temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual, reconcile_amount)
#             temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
#             dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
#             amount_reconcile = min(debit_move[field], -credit_move[field], reconcile_amount)
#
#             #Remove from recordset the one(s) that will be totally reconciled
#             # For optimization purpose, the creation of the partial_reconcile are done at the end,
#             # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
#             # and thus the amount_residual are not recomputed, hence we have to do it manually.
#             if amount_reconcile == debit_move[field]:
#                 debit_moves -= debit_move
#             else:
#                 debit_moves[0].amount_residual -= temp_amount_residual
#                 debit_moves[0].amount_residual_currency -= temp_amount_residual_currency
#
#             if amount_reconcile == -credit_move[field]:
#                 credit_moves -= credit_move
#             else:
#                 credit_moves[0].amount_residual += temp_amount_residual
#                 credit_moves[0].amount_residual_currency += temp_amount_residual_currency
#             #Check for the currency and amount_currency we can set
#             currency = False
#             amount_reconcile_currency = 0
#             if field == 'amount_residual_currency':
#                 currency = credit_move.currency_id.id
#                 amount_reconcile_currency = temp_amount_residual_currency
#                 amount_reconcile = temp_amount_residual
#
#             if cash_basis:
#                 tmp_set = debit_move | credit_move
#                 cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())
#
#             to_create.append({
#                 'debit_move_id': debit_move.id,
#                 'credit_move_id': credit_move.id,
#                 'amount': amount_reconcile,
#                 'amount_currency': amount_reconcile_currency,
#                 'currency_id': currency,
#             })
#             if amount:
#                 break
#
#         cash_basis_subjected = []
#         part_rec = self.env['account.partial.reconcile']
#         with self.env.norecompute():
#             for partial_rec_dict in to_create:
#                 debit_move, credit_move, amount_residual_currency = dc_vals[partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
#                 # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
#                 # i. e: we don't really receive/give money in a customer/provider fashion
#                 # Since those are not subjected to cash basis computation we process them first
#                 if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
#                     part_rec.create(partial_rec_dict)
#                 else:
#                     cash_basis_subjected.append(partial_rec_dict)
#
#             for after_rec_dict in cash_basis_subjected:
#                 new_rec = part_rec.create(after_rec_dict)
#                 # if the pair belongs to move being reverted, do not create CABA entry
#                 if cash_basis and not (new_rec.debit_move_id + new_rec.credit_move_id).mapped('move_id').mapped('reverse_entry_id'):
#                     new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
#         self.recompute()
#
#         return debit_moves+credit_moves


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False, amount=None):
        # Empty self can happen if the user tries to reconcile entries which are already reconciled.
        # The calling method might have filtered out reconciled lines.
        if not self:
            return True

        self._check_reconcile_validity()
        # reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines(amount)

        writeoff_to_reconcile = self.env['account.move.line']
        # if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            all_aml_share_same_currency = all([x.currency_id == self[0].currency_id for x in self])
            writeoff_vals = {
                'account_id': writeoff_acc_id.id,
                'journal_id': writeoff_journal_id.id
            }
            if not all_aml_share_same_currency:
                writeoff_vals['amount_currency'] = False
            writeoff_to_reconcile = remaining_moves._create_writeoff([writeoff_vals])
            # add writeoff line to reconcile algorithm and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).auto_reconcile_lines()
        # Check if reconciliation is total or needs an exchange rate entry to be created
        (self + writeoff_to_reconcile).check_full_reconcile()
        return True

    @api.multi
    def auto_reconcile_lines(self, amount=None):
        # Create list of debit and list of credit move ordered by date-currency
        debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
        credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
        debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        # Compute on which field reconciliation should be based upon:
        if self[0].account_id.currency_id and self[0].account_id.currency_id != self[0].account_id.company_id.currency_id:
            field = 'amount_residual_currency'
        else:
            field = 'amount_residual'
        #if all lines share the same currency, use amount_residual_currency to avoid currency rounding error
        if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
            field = 'amount_residual_currency'
        # Reconcile lines
        ret = self._reconcile_lines(debit_moves, credit_moves, field, amount)
        return ret

    @api.multi
    def _reconcile_lines(self, debit_moves, credit_moves, field, amount=None):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        if amount:
            reconcile_amount = amount
        else:
            reconcile_amount = float('inf')
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}
        dc_vals ={}
        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual, reconcile_amount)
            temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
            dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field], reconcile_amount)

            #Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency

            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual

            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())

            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })

            if amount:
                break

        cash_basis_subjected = []
        part_rec = self.env['account.partial.reconcile']
        with self.env.norecompute():
            for partial_rec_dict in to_create:
                debit_move, credit_move, amount_residual_currency = dc_vals[partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
                # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
                # i. e: we don't really receive/give money in a customer/provider fashion
                # Since those are not subjected to cash basis computation we process them first
                if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
                    part_rec.create(partial_rec_dict)
                else:
                    cash_basis_subjected.append(partial_rec_dict)

            for after_rec_dict in cash_basis_subjected:
                new_rec = part_rec.create(after_rec_dict)
                # if the pair belongs to move being reverted, do not create CABA entry
                if cash_basis and not (new_rec.debit_move_id + new_rec.credit_move_id).mapped('move_id').mapped('reverse_entry_id'):
                    new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
        self.recompute()

        return debit_moves+credit_moves
