import subprocess
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import re
import logging

# */10 * * * * /Users/stefano.fiorentino/devel/pv_optimization/.venv/bin/python /Users/stefano.fiorentino/devel/pv_optimization/solar_plug.py >> /Users/stefano.fiorentino/devel/pv_optimization/power_log.err 2>&1

DOTENV_FILE  = "/Users/stefano.fiorentino/devel/pv_optimization/.env"
load_dotenv(DOTENV_FILE)

EMAIL = os.getenv("PVSOLAR_EMAIL")
PASSWORD = os.getenv("PVSOLAR_PASSWORD")
UUID = "d507369c-342c-4b6a-bdca-472268898241"

# Set up logging to a file
logging.basicConfig(
    filename='/Users/stefano.fiorentino/devel/pv_optimization/power_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def clean_log_line(line: str) -> str:
    return line.replace('\n', ' ').replace('\r', ' ').replace('%','').strip()

def parse_power_string(power_str):
    match = re.match(r"([\d.]+)\s*(k?W)", power_str.strip())
    if not match:
        raise ValueError(f"Invalid power format: {power_str}")
    
    value, unit = match.groups()
    value = float(value)
    
    if unit.lower() == 'kw':
        value *= 1000  # convert kW to W

    int_value = int(round(value))
    return int_value

def parse_battery_string(battery_str):
    value = float(battery_str)
    int_value = int(round(value))
    return int_value

def get_production():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set headless=True once it's stable
        page = browser.new_page()

        # Step 1: Go to login page
        page.goto("https://www.pvsolarportal.com/home/login")

        # Step 2: Fill in credentials and click checkbox
        page.fill('input[name="username"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)
        page.check('input[type="checkbox"][id="readStatement"]')
        page.click('input[type="button"][id="btnLogin"]')

        # Step 3: Wait for navigation and go to status page
        page.wait_for_load_state("networkidle")
        page.goto(f"https://www.pvsolarportal.com/PowerStation/PowerStatusSnMin/{UUID}")
        page.wait_for_load_state("networkidle")

        # Step 4: Extract production value
        # 👇 Use actual selector after inspecting it (we'll tweak if needed)
        power_str = ''
        battery_str = ''
        try:
            power_str = page.inner_text("#power_div")  # ← Update selector if needed
            battery_str = page.inner_text("p.soc-num")
        except Exception as e:
            return None, None

        browser.close()
        
        power_str = clean_log_line(power_str)
        power = parse_power_string(power_str)

        battery_str = clean_log_line(battery_str)
        battery = parse_battery_string(battery_str)

        return power, battery

if __name__ == "__main__":
    power, battery = get_production()
    if power == None or battery == None:
        logging.info(f"Power None W, Battery None %, ERR")
        os._exit(1)
    if power >= 4000 or battery >= 80:
        subprocess.run(["shortcuts", "run", "Plug ON"])
        logging.info(f"Power {power} W, Battery {battery} %, ON")
    elif power < 3000 and battery < 80:
        subprocess.run(["shortcuts", "run", "Plug OFF"])
        logging.info(f"Power {power} W, Battery {battery} %, OFF")
    else:
        logging.info(f"Power {power} W, Battery {battery} %, HOLD")
