# app/config/mpstats_ui_config.py
"""Конфигурация UI элементов MPStats"""

MPSTATS_UI_CONFIG = {
    "login": {
        "email_field": {"by": "NAME", "value": "mpstats-login-form-name"},
        "password_field": {"by": "NAME", "value": "mpstats-login-form-password"}
    },
    "tabs": {
        "requests": {"by": "XPATH", "value": "//*[contains(@class, 'pqQVD')]"},
        "words": {"by": "XPATH", "value": "//*[contains(@class, 'pqQVD')]"}
    },
    "forms": {
        "textarea": {"by": "TAG_NAME", "value": "textarea"},
        "find_queries_btn": {"by": "CSS_SELECTOR", "value": ".whAjj.M_JA1"}
    },
    "download": {
        "download_btn": {"by": "CSS_SELECTOR", "value": ".whAjj.M_JA1"}
    }
}