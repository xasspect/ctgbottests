# app/config/mpstats_ui_config.py
"""Конфигурация UI элементов MPStats"""

#!!! Классы в DOM динамические !!!
# или периодически обновлять их тут вручную, или писать тесты)))

MPSTATS_UI_CONFIG = {
    "login": {
        "email_field": {"by": "NAME", "value": "mpstats-login-form-name"},
        "password_field": {"by": "NAME", "value": "mpstats-login-form-password"}
    },
    # Параметры поиска (3 кнопки) в mpstats_scraper_service используется нажатие на индекс кнопки в списке по классу
    # метод _fill_keywords_form
    "tabs": {
        "requests": {"by": "XPATH", "value": "//*[contains(@class, 'tYj44tFk')]"},
        "words": {"by": "XPATH", "value": "//*[contains(@class, 'tYj44tFk')]"}
    },

    "forms": {
        "textarea": {"by": "TAG_NAME", "value": "textarea"},
        "find_queries_btn": {"by": "CSS_SELECTOR", "value": ".QfBtWSte.G5Kzc11I"}
    },
    # 2 поочередные кнопки скачать из одного списка класса (сейчас 0 и 2 индексы)
    "download": {
        "download_btn": {"by": "CSS_SELECTOR", "value": ".QfBtWSte.G5Kzc11I"}
    }
}