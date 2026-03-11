# dashboard_blti/models/management_service.py
from odoo import api, fields, models
from datetime import date, timedelta


class BltiManagementService(models.Model):
    _name = "blti.management.service"
    _description = "BLTI Management Dashboard Service"
    _auto = False

    def init(self):
        pass

    # ──────────────────────────────────────────────
    # PERIOD HELPER
    # ──────────────────────────────────────────────

    @api.model
    def _resolve_dates(self, period_key):
        today = fields.Date.context_today(self)
        if period_key == "last_7_days":
            return today - timedelta(days=7), today
        if period_key == "last_30_days":
            return today - timedelta(days=30), today
        if period_key == "last_90_days":
            return today - timedelta(days=90), today
        if period_key == "this_month":
            return today.replace(day=1), today
        if period_key == "this_year":
            return date(today.year, 1, 1), today
        return today - timedelta(days=30), today

    @api.model
    def _sales_period_key(self, mgmt_period_key):
        """Map management period key → sales.dashboard period string."""
        return {
            "last_7_days": "last_7_days",
            "last_30_days": "last_30_days",
            "last_90_days": "last_30_days",   # fallback – sales has no last_90
            "this_month":  "month",
            "this_year":   "year",
        }.get(mgmt_period_key, "month")

    @api.model
    def _project_period_key(self, mgmt_period_key):
        """Map management period key → project.manager.dashboard period_filter value."""
        return {
            "last_7_days":  "last_7_days",
            "last_30_days": "last_30_days",
            "last_90_days": "last_30_days",   # fallback
            "this_month":   "this_month",
            "this_year":    "this_year",
        }.get(mgmt_period_key, "this_month")

    # ──────────────────────────────────────────────
    # SALES
    # ──────────────────────────────────────────────

    @api.model
    def _sales_summary(self, period_key, date_from, date_to):
        try:
            SO = self.env["sale.order"]
            common = [("date_order", ">=", date_from), ("date_order", "<=", date_to)]
            q_count = SO.search_count(common + [("state", "in", ["draft", "sent"])])
            grouped = SO.read_group(
                common + [("state", "in", ["sale", "done"])],
                ["amount_total:sum", "id:count"],
                [],
            )
            o_count = int(grouped[0].get("id_count", 0)) if grouped else 0
            revenue = float(grouped[0].get("amount_total", 0.0)) if grouped else 0.0
            avg = revenue / o_count if o_count else 0.0
            return {
                "quotations": q_count,
                "orders": o_count,
                "revenue": revenue,
                "avg_order": avg,
                "available": True,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # PURCHASE
    # ──────────────────────────────────────────────

    @api.model
    def _purchase_summary(self, date_from, date_to):
        try:
            if "purchase.order" not in self.env.registry:
                return {"available": False, "reason": "module_not_installed"}
            PO = self.env["purchase.order"]
            today = fields.Date.context_today(self)
            common = [("date_order", ">=", date_from), ("date_order", "<=", date_to)]
            rfq = PO.search_count(common + [("state", "in", ["draft", "sent"])])
            grouped = PO.read_group(
                common + [("state", "in", ["purchase", "done"])],
                ["amount_total:sum", "id:count"],
                [],
            )
            po_count = int(grouped[0].get("id_count", 0)) if grouped else 0
            total_spent = float(grouped[0].get("amount_total", 0.0)) if grouped else 0.0
            # Overdue: PO sudah confirmed tapi belum fully invoiced dan sudah lewat date_planned
            overdue = PO.search_count([
                ("state", "in", ["purchase", "done"]),
                ("invoice_status", "!=", "invoiced"),
                ("date_planned", "<", today),
            ])
            return {
                "rfq": rfq,
                "orders": po_count,
                "total_spent": total_spent,
                "overdue": overdue,
                "available": True,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # INVENTORY
    # ──────────────────────────────────────────────

    @api.model
    def _inventory_summary(self):
        try:
            if "stock.picking" not in self.env.registry:
                return {"available": False, "reason": "module_not_installed"}
            SP = self.env["stock.picking"]
            SQ = self.env["stock.quant"]
            now = fields.Datetime.now()
            currency = self.env.company.currency_id

            delivery_done  = SP.search_count([("state", "=", "done"), ("picking_type_code", "=", "outgoing")])
            receipt_done   = SP.search_count([("state", "=", "done"), ("picking_type_code", "=", "incoming")])
            delivery_ready = SP.search_count([("state", "=", "assigned"), ("picking_type_code", "=", "outgoing")])
            delivery_late  = SP.search_count([
                ("scheduled_date", "<", now),
                ("state", "not in", ["done", "cancel"]),
                ("picking_type_code", "=", "outgoing"),
            ])
            receipt_late   = SP.search_count([
                ("scheduled_date", "<", now),
                ("state", "not in", ["done", "cancel"]),
                ("picking_type_code", "=", "incoming"),
            ])
            quants      = SQ.search([("location_id.usage", "=", "internal")])
            total_qty   = sum(q.quantity for q in quants if q.quantity > 0)
            stock_value = sum(q.quantity * q.product_id.standard_price for q in quants if q.quantity > 0)

            return {
                "delivery_done":        delivery_done,
                "receipt_done":         receipt_done,
                "delivery_ready":       delivery_ready,
                "delivery_late":        delivery_late,
                "receipt_late":         receipt_late,
                "total_qty":            total_qty,
                "stock_value":          stock_value,
                "stock_value_display":  f"{currency.symbol} {stock_value:,.0f}",
                "available": True,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # INVOICE / ACCOUNTING
    # ──────────────────────────────────────────────

    @api.model
    def _invoice_summary(self, date_from, date_to):
        try:
            if "account.move" not in self.env.registry:
                return {"available": False, "reason": "module_not_installed"}
            AM = self.env["account.move"]
            today = fields.Date.context_today(self)
            date_domain = [("invoice_date", ">=", date_from), ("invoice_date", "<=", date_to)]

            invoices = AM.search_count(date_domain + [
                ("move_type", "=", "out_invoice"), ("state", "=", "posted"),
            ])
            bills = AM.search_count(date_domain + [
                ("move_type", "=", "in_invoice"), ("state", "=", "posted"),
            ])

            # A/R Outstanding
            ar_grouped = AM.read_group(
                date_domain + [
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("payment_state", "not in", ["paid", "in_payment"]),
                ],
                ["amount_residual:sum"],
                [],
            )
            receivable = float(ar_grouped[0].get("amount_residual", 0.0)) if ar_grouped else 0.0

            # A/P Outstanding
            ap_grouped = AM.read_group(
                date_domain + [
                    ("move_type", "=", "in_invoice"),
                    ("state", "=", "posted"),
                    ("payment_state", "not in", ["paid", "in_payment"]),
                ],
                ["amount_residual:sum"],
                [],
            )
            payable = float(ap_grouped[0].get("amount_residual", 0.0)) if ap_grouped else 0.0

            # Overdue customer invoices
            overdue = AM.search_count([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "not in", ["paid", "in_payment"]),
                ("invoice_date_due", "<", today),
            ])

            return {
                "invoices":   invoices,
                "bills":      bills,
                "receivable": receivable,
                "payable":    payable,
                "overdue":    overdue,
                "available":  True,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # PROJECT
    # ──────────────────────────────────────────────

    @api.model
    def _project_summary(self, period_key):
        try:
            if "project.manager.dashboard" not in self.env.registry:
                return {"available": False, "reason": "module_not_installed"}
            proj_period = self._project_period_key(period_key)
            dash = self.env["project.manager.dashboard"].sudo().create({"name": "mgmt_snap"})
            dash.write({"period_filter": proj_period})
            result = {
                "project_count":   int(dash.project_count or 0),
                "project_done":    int(dash.project_done_count or 0),
                "project_cancelled": int(dash.project_cancelled_count or 0),
                "task_count":      int(dash.task_count or 0),
                "task_done":       int(dash.task_done_count or 0),
                "task_overdue":    int(dash.task_overdue_count or 0),
                "task_due_7d":     int(dash.task_due_7_days_count or 0),
                "completion":      dash.project_completion_display or "0.00%",
                "on_time_rate":    f"{(dash.on_time_rate or 0):.1f}%",
                "available":       True,
            }
            dash.unlink()
            return result
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # EXPENSES
    # ──────────────────────────────────────────────

    @api.model
    def _expenses_summary(self, date_from, date_to):
        try:
            if "hr.expense" not in self.env.registry:
                return {"available": False, "reason": "module_not_installed"}
            EX = self.env["hr.expense"]
            domain = [("date", ">=", date_from), ("date", "<=", date_to)]
            all_exp = EX.search(domain)
            total_count   = len(all_exp)
            total_amount  = sum(all_exp.mapped("total_amount"))
            to_validate   = sum(all_exp.filtered(lambda x: x.state == "approved").mapped("total_amount"))
            to_reimburse  = sum(all_exp.filtered(lambda x: x.state == "done").mapped("total_amount"))
            currency      = self.env.company.currency_id
            return {
                "total_count":   total_count,
                "total_amount":  total_amount,
                "to_validate":   to_validate,
                "to_reimburse":  to_reimburse,
                "currency":      currency.symbol,
                "available":     True,
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ──────────────────────────────────────────────

    @api.model
    def get_management_overview(self, period_key="this_month"):
        date_from, date_to = self._resolve_dates(period_key)
        return {
            "period": {
                "key":       period_key,
                "date_from": str(date_from),
                "date_to":   str(date_to),
            },
            "sales":     self._sales_summary(period_key, date_from, date_to),
            "purchase":  self._purchase_summary(date_from, date_to),
            "inventory": self._inventory_summary(),
            "invoice":   self._invoice_summary(date_from, date_to),
            "project":   self._project_summary(period_key),
            "expenses":  self._expenses_summary(date_from, date_to),
        }