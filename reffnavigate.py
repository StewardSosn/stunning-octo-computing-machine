import time
import re
import requests
import logging
import tempfile
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("registration.log"),  # Log ke file
        logging.StreamHandler()  # Log ke konsol
    ]
)

# API GuerrillaMail
GUERRILLAMAIL_API = "https://api.guerrillamail.com/ajax.php"

def get_temp_email():
    """Mendapatkan email sementara dari GuerrillaMail"""
    logging.info("Mencoba mendapatkan email sementara dari GuerrillaMail...")
    try:
        response = requests.get(f"{GUERRILLAMAIL_API}?f=get_email_address")
        if response.status_code != 200:
            logging.error(f"❌ Gagal mendapatkan email. Kode status: {response.status_code}")
            return None, None

        email_data = response.json()
        email_address = email_data["email_addr"]
        sid_token = email_data["sid_token"]

        logging.info(f"📧 Email sementara: {email_address}")
        return email_address, sid_token
    except Exception as e:
        logging.error(f"❌ Terjadi kesalahan saat mendapatkan email: {e}")
        return None, None

def register_account_selenium(email, password, referral_code):
    """Mendaftar akun di website tanpa CAPTCHA"""
    if not email:
        logging.warning("⚠️ Tidak bisa mendaftar karena email tidak diperoleh.")
        return

    logging.info("Mengatur browser Chrome dalam mode headless...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Mode headless (tanpa GUI)
    chrome_options.add_argument("--no-sandbox")  # Tambahan untuk lingkungan tanpa GUI
    chrome_options.add_argument("--disable-dev-shm-usage")  # Mengatasi masalah resource

    # Buat direktori data pengguna yang unik
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Membuka halaman pendaftaran...")
        driver.get("https://dataquest.nvg8.io//signup?ref=1668969")

        logging.info("Mengisi formulir pendaftaran...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        
        logging.info("Mengklik tombol pendaftaran...")
        sign_up_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", sign_up_button)
        time.sleep(1)
        sign_up_button.click()

        logging.info("✅ Akun berhasil didaftarkan, menunggu email verifikasi...")
        time.sleep(10)
    except Exception as e:
        logging.error(f"❌ Terjadi kesalahan saat mendaftar: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
        # Hapus direktori data pengguna beserta isinya
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)  # Menggunakan shutil.rmtree() untuk menghapus direktori dan isinya

def get_verification_link(sid_token, email_address):
    """Mendapatkan link verifikasi dari email menggunakan GuerrillaMail"""
    if not sid_token or not email_address:
        logging.warning("⚠️ Token atau alamat email tidak valid. Gagal mengambil email verifikasi.")
        return None

    retries = 5
    for attempt in range(retries):
        logging.info(f"⏳ Mencoba mendapatkan email verifikasi (Percobaan {attempt + 1}/{retries})...")
        time.sleep(10)  # Tunggu email masuk

        params = {
            "f": "get_email_list",
            "sid_token": sid_token,
            "offset": 0,
            "seq": 0
        }
        response = requests.get(GUERRILLAMAIL_API, params=params)

        if response.status_code != 200:
            logging.warning(f"⚠️ HTTP Error {response.status_code} saat mengambil email.")
            continue

        try:
            email_list = response.json()["list"]
            if email_list:
                email_id = email_list[0]["mail_id"]
                params = {
                    "f": "fetch_email",
                    "sid_token": sid_token,
                    "email_id": email_id
                }
                response = requests.get(GUERRILLAMAIL_API, params=params)
                if response.status_code != 200:
                    logging.warning(f"⚠️ HTTP Error {response.status_code} saat membaca email.")
                    continue

                mail_content = response.json()["mail_body"]
                match = re.search(r"https://[^\" ]+", mail_content)
                if match:
                    logging.info(f"🔗 Link verifikasi ditemukan: {match.group(0)}")
                    return match.group(0)

        except Exception as e:
            logging.error(f"❌ Terjadi kesalahan saat memproses email: {e}")

    logging.error("❌ Gagal mendapatkan email verifikasi setelah beberapa percobaan.")
    return None

def verify_account(verification_link):
    """Membuka link verifikasi untuk menyelesaikan proses pendaftaran"""
    if not verification_link:
        logging.warning("⚠️ Tidak ada link verifikasi, tidak bisa lanjut.")
        return

    logging.info("Mengatur browser Chrome dalam mode headless...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Buat direktori data pengguna yang unik
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Membuka link verifikasi...")
        driver.get(verification_link)
        logging.info("✅ Akun berhasil diverifikasi!")
        time.sleep(5)
    except Exception as e:
        logging.error(f"❌ Terjadi kesalahan saat memverifikasi akun: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
        # Hapus direktori data pengguna beserta isinya
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)

if __name__ == "__main__":
    while True:
        jumlah_pendaftaran_input = input("Masukkan jumlah pendaftaran yang diinginkan: ")
        if jumlah_pendaftaran_input.isdigit():
            jumlah_pendaftaran = int(jumlah_pendaftaran_input)
            break
        logging.error("❌ Harap masukkan angka yang valid.")

    referral_code = input("Masukkan referral code: ")

    for _ in range(jumlah_pendaftaran):
        logging.info("Memulai proses pendaftaran akun...")
        email, sid_token = get_temp_email()
        password = "Test@1234"

        if email and sid_token:
            logging.info(f"🚀 Mendaftar dengan email: {email}")
            register_account_selenium(email, password, referral_code)

            verification_link = get_verification_link(sid_token, email)
            if verification_link:
                verify_account(verification_link)
            else:
                logging.error("⚠️ Pendaftaran gagal, tidak ada email verifikasi.")
        else:
            logging.error("❌ Gagal mendapatkan email sementara. Proses dihentikan.")
