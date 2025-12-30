import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db
import os

# ----------- Streamlit Page Setup -----------
st.set_page_config(
    page_title="JATIN SINGH",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------- Session State -----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_state' not in st.session_state:
    class AutomationState:
        def __init__(self):
            self.running = False
            self.message_count = 0
            self.logs = []
            self.message_rotation_index = 0
    st.session_state.automation_state = AutomationState()

# ----------- Logger -----------
def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        st.session_state.automation_state.logs.append(formatted_msg)

# ----------- Browser Setup (Termux Ready) -----------
def setup_browser(automation_state=None):
    log_message("Setting up Chrome browser...", automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/121.0.0.0 Mobile Safari/537.36')

    # Termux paths
    chromium_path = '/data/data/com.termux/files/usr/bin/chromium'
    chromedriver_path = '/data/data/com.termux/files/usr/bin/chromedriver'

    if Path(chromium_path).exists():
        chrome_options.binary_location = chromium_path

    from selenium.webdriver.chrome.service import Service
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1920, 1080)
    log_message("Chrome browser setup completed", automation_state)
    return driver

# ----------- Find Message Input -----------
def find_message_input(driver, automation_state=None):
    log_message("Finding message input...", automation_state)
    time.sleep(5)
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        '[contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    element.click()
                    return element
                except:
                    continue
        except:
            continue
    return None

# ----------- Get Next Message -----------
def get_next_message(messages, automation_state=None):
    if not messages:
        return "Hello!"
    if automation_state:
        message = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
        return message
    return messages[0]

# ----------- Send Messages -----------
def send_messages(config, automation_state, user_id):
    driver = None
    try:
        log_message("Starting automation...", automation_state)
        driver = setup_browser(automation_state)
        driver.get("https://www.facebook.com/messages")
        time.sleep(8)

        # Add cookies
        if config['cookies']:
            for cookie in config['cookies'].split(';'):
                try:
                    name, value = cookie.strip().split('=', 1)
                    driver.add_cookie({'name': name.strip(), 'value': value.strip(), 'domain': '.facebook.com', 'path': '/'})
                except:
                    continue

        if config['chat_id']:
            driver.get(f"https://www.facebook.com/messages/t/{config['chat_id']}")
            time.sleep(10)

        message_input = find_message_input(driver, automation_state)
        if not message_input:
            log_message("Message input not found!", automation_state)
            return

        delay = int(config['delay'])
        messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
        if not messages_list:
            messages_list = ["Hello!"]

        while automation_state.running:
            msg = get_next_message(messages_list, automation_state)
            try:
                driver.execute_script("""
                    const element = arguments[0];
                    const message = arguments[1];
                    element.focus();
                    element.textContent = message;
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                """, message_input, msg)
                driver.execute_script("""
                    const sendButtons = document.querySelectorAll('[aria-label*="Send" i]');
                    if(sendButtons.length > 0){ sendButtons[0].click(); }
                """)
                automation_state.message_count += 1
                log_message(f"Sent: {msg[:30]}...", automation_state)
                time.sleep(delay)
            except Exception as e:
                log_message(f"Send error: {e}", automation_state)
                time.sleep(5)

    except Exception as e:
        log_message(f"Automation error: {e}", automation_state)
    finally:
        if driver:
            driver.quit()
            log_message("Browser closed", automation_state)

# ----------- Start / Stop Automation -----------
def start_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    if automation_state.running:
        return
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    thread = threading.Thread(target=send_messages, args=(user_config, automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation():
    st.session_state.automation_state.running = False

# ----------- Streamlit App -----------
if not st.session_state.logged_in:
    st.title("JATIN SINGH")
    username = st.text_input("USERNAME")
    password = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        user_id = db.verify_user(username, password)
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Invalid credentials!")
else:
    st.title(f"Welcome {st.session_state.username}")
    user_config = db.get_user_config(st.session_state.user_id)
    if user_config:
        st.text_input("CHAT ID", value=user_config['chat_id'], key="chat_id")
        st.text_area("MESSAGES", value=user_config['messages'], key="messages")
        st.text_area("COOKIES", value="", key="cookies")
        st.number_input("DELAY", value=int(user_config['delay']), key="delay", min_value=1, max_value=300)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("START AUTOMATION"):
                start_automation(user_config, st.session_state.user_id)
        with col2:
            if st.button("STOP AUTOMATION"):
                stop_automation()
        if st.session_state.automation_state.logs:
            st.markdown("### Logs")
            for log in st.session_state.automation_state.logs[-30:]:
                st.write(log)
        st.metric("Messages Sent", st.session_state.automation_state.message_count)
