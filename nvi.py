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
import random
import string
import asyncio
import httpx
from bs4 import BeautifulSoup

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("registration.log"),
        logging.StreamHandler()
    ]
)

def generate_email(domain):
    first_name = ''.join(random.choices(string.ascii_lowercase, k=5))
    last_name = ''.join(random.choices(string.ascii_lowercase, k=5))
    random_nums = ''.join(random.choices(string.digits, k=3))
    email = f"{first_name}{last_name}{random_nums}@{domain}"
    logging.info(f"📧 Generated email: {email}")
    return email

async def get_domains():
    retries = 3
    for attempt in range(retries):
        try:
            key = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=2))
            response = requests.get(f"https://generator.email/search.php?key={key}", timeout=10)
            
            if response.ok:
                json_data = response.json()
                if isinstance(json_data, list) and json_data:
                    return json_data
        except requests.exceptions.RequestException as error:
            logging.error(f"Error fetching domains (Attempt {attempt + 1}/{retries}): {error}")
        await asyncio.sleep(2)
    return []

async def get_verification_link(email):
    email_username, email_domain = email.split('@')
    cookies = {'embx': f'[%22{email}%22]', 'surl': f'{email_domain}/{email_username}'}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(5):
            logging.info(f"⏳ Checking for verification email (Attempt {attempt + 1}/5)...")
            response = await client.get(f"https://generator.email/inbox1/", headers=headers, cookies=cookies)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                email_body = soup.prettify()
                match = re.search(r'<a\s+href=["\'](https?://[^"\']+)["\'][^>]*>\s*this verification link\s*</a>', email_body, re.IGNORECASE)
                if match:
                    verification_link = match.group(1)
                    logging.info(f"🔗 Verification link found: {verification_link}")
                    return verification_link
            await asyncio.sleep(10)
    logging.error("❌ Verification email not found.")
    return None

async def get_temp_email():
    domains = await get_domains()
    if not domains:
        logging.error("❌ No available email domains.")
        return None
    domain = random.choice(domains)
    return generate_email(domain)

def register_account_selenium(email, password, referral_code):
    if not email:
        logging.warning("⚠️ Cannot register, email not generated.")
        return
    
    logging.info("Starting Chrome in headless mode...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Opening registration page...")
        driver.get("https://dataquest.nvg8.io/signup")
        
        logging.info("Filling registration form...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.NAME, "referral").send_keys(referral_code)
        
        logging.info("Clicking register button...")
        sign_up_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", sign_up_button)
        time.sleep(1)
        sign_up_button.click()
        
        logging.info("✅ Registration successful, waiting for verification email...")
        time.sleep(10)
    except Exception as e:
        logging.error(f"❌ Registration error: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)

def verify_account(verification_link):
    if not verification_link:
        logging.warning("⚠️ No verification link, cannot proceed.")
        return
    
    logging.info("Opening verification link...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(verification_link)
        logging.info("✅ Account verified!")
        time.sleep(5)
    except Exception as e:
        logging.error(f"❌ Verification error: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)

if __name__ == "__main__":
    referral_code = input("Enter referral code: ")
    jumlah_pendaftaran = int(input("Enter number of registrations: "))
    
    for _ in range(jumlah_pendaftaran):
        logging.info("Starting registration process...")
        email = asyncio.run(get_temp_email())
        password = "Test@1234"
        
        if email:
            register_account_selenium(email, password, referral_code)
            verification_link = asyncio.run(get_verification_link(email))
            if verification_link:
                verify_account(verification_link)
            else:
                logging.error("⚠️ Registration failed, no verification email.")
        else:
            logging.error("❌ Failed to get temporary email. Process halted.")
