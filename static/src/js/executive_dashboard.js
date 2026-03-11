/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class BltiExecutiveDashboard extends Component {
    static template = "dashboard_blti.ExecutiveDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            period: "last_90_days",
            data: null,
        });

        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        const res = await this.orm.call(
            "blti.dashboard.service",
            "get_sales_overview",
            [this.state.period],
            {}
        );
        this.state.data = res;
        this.state.loading = false;
    }

    async onChangePeriod(ev) {
        this.state.period = ev.target.value;
        await this.load();
    }

    // Drilldown helpers
    async openQuotations() {
        const { date_from, date_to } = this.state.data.period;
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Quotations",
            res_model: "sale.order",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["state", "in", ["draft", "sent"]],
                ["date_order", ">=", date_from],
                ["date_order", "<=", date_to],
            ],
        });
    }

    async openOrders() {
        const { date_from, date_to } = this.state.data.period;
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Orders",
            res_model: "sale.order",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["state", "in", ["sale", "done"]],
                ["date_order", ">=", date_from],
                ["date_order", "<=", date_to],
            ],
        });
    }
}

registry.category("actions").add("blti_executive_dashboard", BltiExecutiveDashboard);
