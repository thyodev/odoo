{
    "name": "Dashboard BLTI - Executive",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "summary": "Executive dashboard for management",
    "depends": ["web", "sale"],
    "data": [
        "security/security.xml",
        "views/dashboard_menu.xml",
        "views/actions.xml",
        "security/ir.model.access.csv",

    ],
    "assets": {
        "web.assets_backend": [
            "dashboard_blti/static/src/js/executive_dashboard.js",
            "dashboard_blti/static/src/xml/executive_dashboard.xml",
            "dashboard_blti/static/src/scss/executive_dashboard.scss",
        ],
    },
    "installable": True,
}
