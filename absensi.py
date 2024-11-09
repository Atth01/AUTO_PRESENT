from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import time
from datetime import datetime
import pytz
import logging
from dotenv import load_dotenv

# Fungsi untuk mendapatkan waktu Jakarta
def get_jakarta_time():
    return datetime.now(pytz.timezone('Asia/Jakarta'))

# Fungsi untuk mengecek waktu absensi
def is_absen_time(test_mode=False):
    now = get_jakarta_time()
    logger = setup_logging()
    logger.info(f"Checking time: {now.strftime('%Y-%m-%d %H:%M:%S')} WIB")
    
    if test_mode:
        logger.info("Running in TEST mode")
        return "test_mode"
        
    hour = now.hour
    minute = now.minute
    
    # Jadwal 1: 09:30-10:00
    if hour == 9 and minute >= 30 or hour == 10 and minute == 0:
        return "jadwal_1"
    elif hour == 12 and minute >= 30 or hour == 13 and minute == 0:
        return "jadwal_2"
    elif hour == 13 and minute >= 30 or hour == 14 and minute == 0:
        return "jadwal_3"
    else:
        return None

# Setup logging untuk mencatat proses
def setup_logging():
    log_dir = os.path.join('absen', 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f"absensi_{get_jakarta_time().strftime('%Y-%m-%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Setup driver untuk Selenium
def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

# Fungsi untuk verifikasi berhasilnya absen
def verify_absen_success(driver, logger):
    try:
        page_source = driver.page_source.lower()
        already_absen_indicators = ["anda sudah melakukan absensi", "sudah absen", "absensi berhasil"]
        for indicator in already_absen_indicators:
            if indicator in page_source:
                logger.info("Sudah absen hari ini")
                return True
        success_indicators = ["berhasil", "logout"]
        if any(ind in page_source for ind in success_indicators):
            timestamp = get_jakarta_time().strftime('%Y-%m-%d_%H-%M-%S')
            screenshot_dir = os.path.join('absen', 'log', 'screenshots')
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f'absen_{timestamp}.png')
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False

# Fungsi utama untuk melakukan absensi
def login_dan_absen_multiple_users(test_mode=False):
    logger = setup_logging()
    jadwal = is_absen_time(test_mode)
    
    if not jadwal and not test_mode:
        logger.warning("Bukan waktu absen!")
        return False
    
    index = 1
    success_count = 0
    
    while True:
        username = os.getenv(f'UNBIN_USERNAME_{index}')
        password = os.getenv(f'UNBIN_PASSWORD_{index}')
        
        if not username or not password:
            break
        
        logger.info(f"Proses absen untuk user ke-{index}")
        if login_dan_absen_single_user(username, password, test_mode, jadwal, logger):
            success_count += 1
        
        index += 1
    
    logger.info(f"Total absen berhasil untuk {success_count} dari {index-1} pengguna.")
    return success_count > 0

# Fungsi untuk proses login dan absensi untuk satu user
def login_dan_absen_single_user(username, password, test_mode, jadwal, logger):
    driver = None
    try:
        driver = setup_driver()
        driver.get("https://akademik.unbin.ac.id/absensi/")
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "userid"))
        )
        password_field = driver.find_element(By.NAME, "pin")
        username_field.send_keys(username)
        password_field.send_keys(password)
        driver.find_element(By.NAME, "login").click()
        
        time.sleep(5)
        if verify_absen_success(driver, logger):
            logger.info(f"Absen berhasil untuk {username}")
            return True
        else:
            logger.error(f"Absen gagal untuk {username}")
            return False
            
    except Exception as e:
        logger.error(f"Error untuk {username}: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed for this user")

if __name__ == "__main__":
    load_dotenv()
    login_dan_absen_multiple_users(test_mode=False)
