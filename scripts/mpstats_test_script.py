# async_test.py
import asyncio
import os
import sys
from pathlib import Path
from time import sleep
from turtledemo.sorting_animate import enable_keys

from selenium.webdriver import Keys
from sqlalchemy.sql.base import elements

# Устанавливаем переменные окружения ДО импорта
os.environ['DOCKER_MODE'] = 'false'
os.environ['SELENIUM_HEADLESS'] = 'false'

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 50)
print("АСИНХРОННЫЙ ТЕСТ С ВАШИМИ КОМПОНЕНТАМИ")
print("=" * 50)


async def open_browser_and_test():


    """Асинхронная функция для открытия браузера"""

    # Импортируем внутри функции
    from app.config.config import config
    from app.utils.selenium_tools.driver_manager import ChromeDriverManager

    downloads_dir = os.path.join(project_root, "downloads", "mpstats")
    os.makedirs(downloads_dir, exist_ok=True)

    try:
        # 1. Создаем менеджер драйвера
        print("\n1. Создаю ChromeDriverManager...")
        driver_manager = ChromeDriverManager(
            headless=False,  # Обязательно false для Windows
            use_stealth=True  # Включаем stealth
        )

        # 2. Настройки stealth
        stealth_options = {
            "languages": ["ru-RU", "ru", "en-US", "en"],
            "vendor": "Google Inc.",
            "platform": "Win32",
            "webgl_vendor": "Intel Inc.",
            "renderer": "Intel Iris OpenGL Engine",
            "fix_hairline": False,
            "run_on_insecure_origins": False,
        }

        # 3. Создаем драйвер асинхронно
        print("2. Создаю драйвер...")
        driver = driver_manager.create_driver(
            download_dir=config.paths.mpstats_downloads_dir,
            block_videos=True,
            block_images=False,
            block_sounds=True,
            user_agent=config.selenium.user_agent,
            stealth_options=stealth_options
        )

        print("✅ Драйвер создан успешно!")

        # 4. Открываем страницу асинхронно
        print("3. Открываю страницу...")
        driver.maximize_window()
        await asyncio.to_thread(driver.get, "https://mpstats.io/seo/keywords/expanding")

        # Даем странице загрузиться
        await asyncio.sleep(2)

        print(f"✓ Страница загружена!")
        print(f"  Заголовок: {driver.title}")
        print(f"  URL: {driver.current_url}")

        # 5. Асинхронно проверяем элементы
        print("4. Проверяю элементы страницы...")

        # Импортируем необходимые модули
        from selenium.webdriver.common.by import By

        try:
            email = driver.find_element(By.NAME, 'mpstats-login-form-name')
            email.send_keys(config.api.mpstats_email)
            pswd = driver.find_element(By.NAME, 'mpstats-login-form-password')
            pswd.send_keys(config.api.mpstats_pswd)
            pswd.send_keys(Keys.ENTER)


        except Exception as e:
            print(f'Ошибка login/pswd: "{e}"')
        sleep(3)
        """
        Поиск кнопки "Запросы" по классу кнопок в bar (class="pqQVD")
        """

        try:

            while len(driver.find_elements(By.XPATH, "//*[contains(@class, 'pqQVD')]")) == 0:
                print(123)
                sleep(1)
            elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'pqQVD')]")
            elements[1].click()
        except Exception as e:
            print(f'Ошибка Запросы: "{e}"')

        try:
            textarea = driver.find_element(By.TAG_NAME, "textarea")
            textarea.send_keys('пергамент для выпечки')
        except Exception as e:
            print(f'Ошибка textarea: "{e}"')

        try:
            element = driver.find_element(By.CSS_SELECTOR, ".whAjj.M_JA1")
            driver.execute_script("arguments[0].click();", element)
        except Exception as e:
            print(f'Ошибка "Подобрать запросы": {e}')
        sleep(4)
        try:
            while len(driver.find_elements(By.XPATH, "//*[contains(@class, 'pqQVD')]")) == 0:
                print(123)
                sleep(1)
            elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'pqQVD')]")
            elements[1].click()
        except Exception as e:
            print(f'Ошибка "Переключиться на слова": {e}')

        sleep(2)
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, ".whAjj.M_JA1")
            driver.execute_script("arguments[0].click();", elements[0])
        except Exception as e:
            print(f'Ошибка "Скачать 1": {e}')
        sleep(2)
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, ".whAjj.M_JA1")
            driver.execute_script("arguments[0].click();", elements[2])
        except Exception as e:
            print(f'Ошибка "Скачать 2": {e}')

        def wait_for_download_complete(download_dir, timeout=30, check_interval=1):
            """
            Ожидает завершения скачивания файла.

            Args:
                download_dir: Директория скачивания
                timeout: Максимальное время ожидания в секундах
                check_interval: Интервал проверки в секундах

            Returns:
                Список новых файлов или пустой список
            """
            import time

            # Получаем начальный список файлов
            initial_files = set()
            if os.path.exists(download_dir):
                initial_files = set(os.listdir(download_dir))

            print(f"📁 Начальные файлы: {initial_files}")

            start_time = time.time()
            while time.time() - start_time < timeout:
                if os.path.exists(download_dir):
                    current_files = set(os.listdir(download_dir))
                    new_files = current_files - initial_files

                    if new_files:
                        # Проверяем, что файлы полностью скачались (нет временных расширений)
                        completed_files = []
                        for file in new_files:
                            if not (file.endswith('.crdownload') or file.endswith('.tmp') or file.endswith('.part')):
                                completed_files.append(file)

                        if completed_files:
                            print(f"✅ Скачаны файлы: {completed_files}")
                            return [os.path.join(download_dir, f) for f in completed_files]

                time.sleep(check_interval)

            print(f"⏰ Таймаут ожидания скачивания ({timeout} секунд)")
            return []

        # Использование в основном скрипте
        # После клика на кнопку скачивания:
        downloaded = wait_for_download_complete(downloads_dir, timeout=60)
        if downloaded:
            print(f"✅ Скачивание успешно: {len(downloaded)} файлов")
        else:
            print("❌ Скачивание не завершено")

        await asyncio.sleep(999)

        return driver

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Основная асинхронная функция"""
    driver = None

    try:
        # Запускаем тест
        driver = await open_browser_and_test()

        if driver:
            print("\n6. Закрываю браузер...")
            # Асинхронно закрываем драйвер
            await asyncio.to_thread(driver.quit)
            print("✅ Браузер закрыт!")

    except KeyboardInterrupt:
        print("\n\n⏹️  Прервано пользователем")
        if driver:
            await asyncio.to_thread(driver.quit)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        if driver:
            await asyncio.to_thread(driver.quit)

    print("\n" + "=" * 50)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 50)


if __name__ == '__main__':
    # Запускаем асинхронную функцию
    asyncio.run(main())