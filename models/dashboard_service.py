# dashboard_blti/models/dashboard_service.py
from odoo import api, fields, models
from datetime import date, timedelta

class BltiDashboardService(models.Model):
    _name = "blti.dashboard.service"
    _description = "BLTI Dashboard Service"
    _auto = False  # no table needed

    # Optional: keep Odoo happy on module update
    def init(self):
        pass

    @api.model
    def _get_period_dates(self, period_key: str):
        """Return (date_from, date_to) as python date objects."""
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

        # default
        return today - timedelta(days=90), today

    @api.model
    def get_sales_overview(self, period_key="last_90_days"):
        """
        Return KPI cards for Sales dashboard:
        - quotations: draft/sent
        - orders: sale/done
        - revenue: sum(amount_total) for sale/done (SO based)
        - average_order: revenue/orders
        """
        date_from, date_to = self._get_period_dates(period_key)

        # domain date: order_date uses date_order (datetime). Use >= date_from 00:00 and <= date_to 23:59
        # In domain, comparing date to datetime field is OK in Odoo (it will cast).
        common_domain = [
            ("date_order", ">=", date_from),
            ("date_order", "<=", date_to),
        ]

        SaleOrder = self.env["sale.order"]

        # Quotations
        q_domain = common_domain + [("state", "in", ["draft", "sent"])]
        q_count = SaleOrder.search_count(q_domain)

        # Orders + Revenue (SO-based)
        o_domain = common_domain + [("state", "in", ["sale", "done"])]
        grouped = SaleOrder.read_group(
            domain=o_domain,
            fields=["amount_total:sum", "id:count"],
            groupby=[],
        )
        orders_count = int(grouped[0].get("id_count", 0)) if grouped else 0
        revenue = float(grouped[0].get("amount_total", 0.0)) if grouped else 0.0
        avg_order = (revenue / orders_count) if orders_count else 0.0

        return {
            "period": {
                "key": period_key,
                "date_from": str(date_from),
                "date_to": str(date_to),
            },
            "cards": {
                "quotations": {"value": q_count},
                "orders": {"value": orders_count},
                "revenue": {"value": revenue},
                "avg_order": {"value": avg_order},
            },
        }
