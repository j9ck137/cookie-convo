import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db
import os

st.set_page_config(page_title="FB Automation", page_icon="⚙️", layout="wide")

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------- SESSION STATE SAFE INIT ----------
class AutoState:
    def __init__(self):
        self.running = False
        self.logs = []
        self.count = 0
        self.idx = 0

if "automation" not in st.session_state:
    st.session_state.automation = AutoState()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def log(msg):
    if "automation" not in st.session_state:
        return
    ts = time.strftime("%H:%M:%S")
    st.session_state.automation.logs.append(f"[{ts}] {msg}")

# ---------- SELENIUM BROWSER ----------
def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    termux_chrome = "/data/data/com.termux/files/usr/bin/chromium"
    termux_driver = "/data/data/com.termux/files/usr/bin/chromedriver"

    if Path(termux_chrome).exists():
        chrome_options.binary_location = termux_chrome

    from selenium.webdriver.chrome.service import Service
    service = Service(termux_driver)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# ---------- FIND MESSAGE INPUT ----------
def find_input(driver):
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        '[contenteditable="true"]',
        "textarea",
        'input[type="text"]'
    ]
    timeout = time.time() + 15
    while time.time() < timeout:
        for s in selectors:
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, s):
                    try:
                        el.click()
                        return el
                    except:
                        pass
            except:
                pass
        time.sleep(1)
    return None

# ---------- MESSAGE ROTATION ----------
def next_msg(msgs):
    a = st.session_state.automation
    msg = msgs[a.idx % len(msgs)]
    a.idx += 1
    return msg

# ---------- AUTOMATION THREAD ----------
def send_messages(cfg):
    a = st.session_state.get("automation")
if not a:
    return
    try:
        log("Starting browser...")
        driver = setup_browser()
        driver.get("https://www.facebook.com/messages")
        time.sleep(8)

        # cookies insert
        if cfg["cookies"]:
            for c in cfg["cookies"].split(";"):
                try:
                    n,v = c.strip().split("=",1)
                    driver.add_cookie({
                        "name":n.strip(),"value":v.strip(),
                        "domain":".facebook.com","path":"/"
                    })
                except:
                    pass

        if cfg["chat_id"]:
            driver.get(f"https://www.facebook.com/messages/t/{cfg['chat_id']}")
            time.sleep(8)

        box = find_input(driver)
        if not box:
            log("Message box not found!")
            return

        msgs = [m.strip() for m in cfg["messages"].split("\n") if m.strip()]
        if not msgs: msgs = ["Hello!"]
        delay = int(cfg["delay"])

        while a.running:
            msg = next_msg(msgs)
            try:
                driver.execute_script("""
                    const el = arguments[0];
                    el.focus();
                    el.textContent = arguments[1];
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                """, box, msg)

                driver.execute_script("""
                    const b=document.querySelector('[aria-label*="Send" i]');
                    if(b){b.click();}
                """)

                a.count += 1
                log(f"Sent: {msg[:30]}...")
                time.sleep(delay)

            except Exception as e:
                log(f"Error: {e}")
                box = find_input(driver)
                time.sleep(3)

    finally:
        if driver:
            driver.quit()
        log("Browser closed")

# ---------- START / STOP ----------
def start(cfg):
    a = st.session_state.automation
    if a.running: return
    a.running = True
    a.logs = []
    a.count = 0
    threading.Thread(target=send_messages, args=(cfg,), daemon=True).start()

def stop():
    st.session_state.automation.running = False

# ---------- AUTH SCREENS ----------
if not st.session_state.logged_in:

    st.title("FB Automation — Multi User")

    tab_login, tab_reg = st.tabs(["LOGIN", "REGISTER"])

    with tab_login:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            uid = db.verify_user(u, p)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab_reg:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")

        if st.button("Create Account"):
            if db.register_user(nu, np):
                st.success("Account created. Now login.")
            else:
                st.error("Username already exists")

else:
    st.title(f"Welcome — {st.session_state.username}")

    cfg = db.get_user_config(st.session_state.user_id) or {
        "chat_id":"", "messages":"Hello!", "delay":5
    }

    chat_id = st.text_input("CHAT ID", value=cfg["chat_id"])
    messages = st.text_area("MESSAGES", value=cfg["messages"])
    cookies = st.text_area("COOKIES")
    delay = st.number_input("DELAY (seconds)", min_value=1, max_value=300, value=int(cfg["delay"]))

    if st.button("Save Config"):
        db.save_user_config(st.session_state.user_id, chat_id, messages, delay)
        st.success("Saved")

    cfg = {
        "chat_id": chat_id,
        "messages": messages,
        "cookies": cookies,
        "delay": delay
    }

    col1, col2 = st.columns(2)
    with col1:
        if st.button("START"):
            start(cfg)
    with col2:
        if st.button("STOP"):
            stop()

    st.metric("Messages Sent", st.session_state.automation.count)

    if st.session_state.automation.logs:
        st.markdown("### Logs")
        st.text("\n".join(st.session_state.automation.logs[-80:]))

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()
