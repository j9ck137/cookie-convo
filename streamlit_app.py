#=========================

FIXED STREAMLIT APP

#=========================

import streamlit as st import threading, time from selenium import webdriver from selenium.webdriver.chrome.options import Options from selenium.webdriver.common.by import By import database as db

st.set_page_config(page_title="Automation", page_icon="ðŸ”¥", layout="wide")

#--------------------------------------------------

AUTOMATION STATE (THREAD SAFE)

#--------------------------------------------------

class AutomationState: def init(self): self.running = False self.message_count = 0 self.message_rotation_index = 0 self.live_logs = []

#--------------------------------------------------

THREAD SAFE LOGGER (NO streamlit inside)

#--------------------------------------------------

def live_log(msg, state): ts = time.strftime("%H:%M:%S") state.live_logs.append(f"[{ts}] {msg}") state.live_logs = state.live_logs[-200:]

#--------------------------------------------------

UI LOG RENDER (MAIN THREAD ONLY)

#--------------------------------------------------

def render_live_console(): st.markdown('<div class="logbox">', unsafe_allow_html=True) for line in st.session_state.automation_state.live_logs[-100:]: st.markdown(line) st.markdown('</div>', unsafe_allow_html=True)

#--------------------------------------------------

CSS

#--------------------------------------------------

st.markdown("""

<style>
.logbox {
    background: rgba(0,0,0,0.6);
    color:#0ff;
    padding:15px;
    height:300px;
    overflow:auto;
    border-radius:10px;
}
</style>""", unsafe_allow_html=True)

#--------------------------------------------------

SESSION INIT

#--------------------------------------------------

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if "automation_running" not in st.session_state: st.session_state.automation_running = False

if "automation_state" not in st.session_state: st.session_state.automation_state = AutomationState()

#--------------------------------------------------

LOGIN

#--------------------------------------------------

if not st.session_state.logged_in: u = st.text_input("Username") p = st.text_input("Password", type="password") if st.button("Login"): uid = db.verify_user(u, p) if uid: st.session_state.logged_in = True st.session_state.user_id = uid st.rerun() else: st.error("Invalid login") st.stop()

#--------------------------------------------------

AUTOMATION ENGINE

#--------------------------------------------------

def setup_browser(): opt = Options() opt.add_argument("--headless=new") opt.add_argument("--no-sandbox") opt.add_argument("--disable-dev-shm-usage") return webdriver.Chrome(options=opt)

def send_messages(cfg, stt): try: live_log("Starting browser...", stt) d = setup_browser() d.get("https://www.facebook.com") time.sleep(8) live_log("Facebook loaded", stt)

d.get(f"https://www.facebook.com/messages/t/{cfg.get('chat_id','')}")
    time.sleep(10)
    live_log("Chat opened", stt)

    box = d.find_element(By.CSS_SELECTOR, "div[contenteditable='true']")
    msgs = cfg.get("messages", ["Hello!"])

    while stt.running:
        msg = msgs[stt.message_rotation_index % len(msgs)]
        stt.message_rotation_index += 1
        box.send_keys(msg + "\n")
        stt.message_count += 1
        live_log(f"Sent: {msg}", stt)
        time.sleep(cfg.get("delay", 15))

    d.quit()
    live_log("Automation stopped", stt)

except Exception as e:
    live_log(f"Fatal Error: {e}", stt)

#--------------------------------------------------

CONTROLS

#--------------------------------------------------

col1, col2 = st.columns(2)

if col1.button("START", disabled=st.session_state.automation_running): st.session_state.automation_running = True st.session_state.automation_state.running = True

cfg = {
    "chat_id": st.text_input("Chat ID"),
    "delay": 15,
    "messages": ["Hello from bot"]
}

t = threading.Thread(
    target=send_messages,
    args=(cfg, st.session_state.automation_state),
    daemon=True
)
t.start()

if col2.button("STOP", disabled=not st.session_state.automation_running): st.session_state.automation_state.running = False st.session_state.automation_running = False

#--------------------------------------------------

LOG VIEW

#--------------------------------------------------

st.write(f"Messages Sent: {st.session_state.automation_state.message_count}") render_live_console()

if st.session_state.automation_running: time.sleep(1) st.rerun()
