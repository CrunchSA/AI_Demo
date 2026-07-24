import streamlit as st
import requests
import re
import os

# --- Network Configuration & Fail-Safe Normalization ---
CRDP_BASE = os.getenv("CRDP_URL", "http://crdp-service:8090/v1")

# Clean up trailing routes if passed erroneously via deployment variables
CRDP_BASE = CRDP_BASE.rstrip("/")
if CRDP_BASE.endswith("/protect"):
    CRDP_BASE = CRDP_BASE.rsplit("/protect", 1)[0]
elif CRDP_BASE.endswith("/reveal"):
    CRDP_BASE = CRDP_BASE.rsplit("/reveal", 1)[0]

CRDP_PROTECT_URL = f"{CRDP_BASE}/protect"
CRDP_REVEAL_URL = f"{CRDP_BASE}/reveal"

OLLAMA_CHAT_URL = os.getenv("OLLAMA_URL", "http://ollama-service:11434/api/chat")
CRDP_POLICY = os.getenv("CRDP_POLICY", "llm-ssn-tokenize-policy")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:1.5b")
KNOWLEDGE_PATH = os.getenv("KNOWLEDGE_PATH", "/data/enterprise_knowledge.txt")

# --- Web UI Custom Workspace Setup ---
st.set_page_config(page_title="CipherTrust AI Perimeter", layout="wide")
st.title("🔒 Thales CipherTrust AI Perimeter")
st.subheader("Zero-Trust Conversational Memory & Context Guardrails")

# --- 👥 User Identity Session Configuration ---
st.sidebar.markdown("### 👥 Identity Access Management")
active_user = st.sidebar.selectbox(
    "Simulate Request User:",
    options=["Alice", "Bob", "Malicious_Actor"]
)

# --- Initialize Stateful Memory Arrays ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # Tokenized conversational history matrix sent to Ollama

if "display_history" not in st.session_state:
    st.session_state.display_history = []  # Presentation layer clean-text chat log array

if "crdp_api_logs" not in st.session_state:
    st.session_state.crdp_api_logs = []  # Session log trace for tracking raw HTTP wire calls

if "token_version_vault" not in st.session_state:
    st.session_state.token_version_vault = {}  # Internal lookups: { "Token_Value": "Version_String" }

# Initialize Telemetry Audit Counters
for key in ["audit_raw_in", "audit_sanitized_in", "audit_raw_out", "audit_revealed_out"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# --- Thales CipherTrust Orchestration Functions ---
def call_crdp(endpoint, data_string, username):
    """Executes atomic REST transactions, injecting plain-text user identities and token versions."""
    is_reveal = "reveal" in endpoint
    payload_data_key = "protected_data" if is_reveal else "data"
    
    # Assemble core payload containing explicit plaintext username parameters
    payload = {
        "protection_policy_name": CRDP_POLICY,
        payload_data_key: data_string,
        "username": username
    }
    
    # If conducting retrieval operations, extract and append version parameters
    if is_reveal:
        tracked_version = st.session_state.token_version_vault.get(data_string)
        if tracked_version:
            payload["external_version"] = tracked_version
            
    headers = {"Content-Type": "application/json"}
    
    # Log object setup for wire monitoring
    log_entry = {
        "url": endpoint,
        "method": "POST",
        "headers": headers,
        "request_payload": payload,
        "status_code": None,
        "response_payload": None
    }
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
        log_entry["status_code"] = response.status_code
        res_json = response.json() if response.status_code == 200 else {}
        log_entry["response_payload"] = res_json if res_json else response.text
        st.session_state.crdp_api_logs.append(log_entry)
        
        if response.status_code == 200:
            if is_reveal:
                return res_json.get("data", "ERROR")
            else:
                token = res_json.get("protected_data", "ERROR")
                ext_version = res_json.get("external_version")
                # Store structural key metadata versions inside application memory vault
                if ext_version and token != "ERROR":
                    st.session_state.token_version_vault[token] = str(ext_version)
                return token
                
        return f"[Access Denied: {response.status_code}]"
        
    except Exception as e:
        log_entry["status_code"] = "CONNECTION_FAILED"
        log_entry["response_payload"] = {"error": str(e)}
        st.session_state.crdp_api_logs.append(log_entry)
        return f"[CRDP Network Failure: {str(e)}]"

def process_text(text, operation_url, username):
    """Parses text strings using regular expressions to apply dynamic identity token mutations."""
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    matches = re.findall(ssn_pattern, text)
    mutated_text = text
    for item in matches:
        resolved_token = call_crdp(operation_url, item, username)
        mutated_text = mutated_text.replace(item, resolved_token)
    return mutated_text

def load_and_sanitize_knowledge(username):
    """Reads static manuals from the CTE storage volume and masks them under active user credentials."""
    if not os.path.exists(KNOWLEDGE_PATH):
        return "System Context Empty: No local corporate knowledge file found at /data/enterprise_knowledge.txt"
    try:
        with open(KNOWLEDGE_PATH, "r") as file:
            raw_knowledge = file.read()
        return process_text(raw_knowledge, CRDP_PROTECT_URL, username)
    except Exception as e:
        return f"Error executing context ingestion: {str(e)}"

# --- Layout Visual Grid Matrix ---
chat_column, audit_column = st.columns([3, 2])

with chat_column:
    st.markdown("### 💬 Secure AI Chat Session")
    
    # Redraw presentation components on state changes
    for msg in st.session_state.display_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Capturing input strings from user interface terminal
    if user_raw_prompt := st.chat_input("Ask a question about internal corporate data..."):
        
        # Flush log telemetry container for new runtime step
        st.session_state.crdp_api_logs = []
        
        with st.chat_message("user"):
            st.markdown(user_raw_prompt)
        st.session_state.display_history.append({"role": "user", "content": user_raw_prompt})

        # 1. INGESTION INTERCEPTION: Protect prompt properties before moving onto the network
        sanitized_user_prompt = process_text(user_raw_prompt, CRDP_PROTECT_URL, active_user)
        st.session_state.messages.append({"role": "user", "content": sanitized_user_prompt})

        # 2. CONTEXT INJECTION (RAG): Process training manuals through active user authorization paths
        sanitized_corporate_context = load_and_sanitize_knowledge(active_user)

        # Re-pack conversational array parameters, stuffing the sanitized policy manual
        compiled_messages = [
            {
                "role": "system", 
                "content": f"You are a secure corporate assistant. Use this internal text to answer inquiries: {sanitized_corporate_context}"
            }
        ] + st.session_state.messages

        payload = {
            "model": MODEL_NAME,
            "messages": compiled_messages,
            "stream": False
        }

        # 3. Transmit chat context history package cleanly to Ollama Core Pod
        with st.chat_message("assistant"):
            with st.spinner("Processing secured contextual pipeline..."):
                try:
                    res = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=30)
                    response_json = res.json()
                    
                    # Intercept processing flaws or internal engine errors
                    if res.status_code != 200 or "error" in response_json:
                        error_detail = response_json.get("error", f"HTTP {res.status_code}")
                        st.error(f"🛑 Ollama Rejected Request: {error_detail}")
                        st.session_state.audit_raw_in = user_raw_prompt
                        st.session_state.audit_sanitized_in = sanitized_user_prompt
                        st.session_state.audit_raw_out = f"ERROR: {error_detail}"
                        st.session_state.audit_revealed_out = "FAILED"
                        st.stop()

                    llm_raw_response = response_json["message"]["content"]
                    st.session_state.messages.append({"role": "assistant", "content": llm_raw_response})
                    
                    # 4. RETRIEVAL INTERCEPTION: Translate returned token fields via dynamic reveal pipelines
                    revealed_response = process_text(llm_raw_response, CRDP_REVEAL_URL, active_user)
                    
                    st.markdown(revealed_response)
                    st.session_state.display_history.append({"role": "assistant", "content": revealed_response})
                    
                    # Store session variables for dashboard presentation
                    st.session_state.audit_raw_in = user_raw_prompt
                    st.session_state.audit_sanitized_in = sanitized_user_prompt
                    st.session_state.audit_raw_out = llm_raw_response
                    st.session_state.audit_revealed_out = revealed_response

                except Exception as e:
                    error_msg = f"Inference execution failed: {str(e)}"
                    st.error(error_msg)

# --- Thales Real-Time Audit Console Panel ---
with audit_column:
    st.markdown("### 📊 Thales Real-Time Audit Console")
    st.sidebar.info(f"**Target Model:** `{MODEL_NAME}`\n\n**CRDP Base:** `{CRDP_BASE}`\n\n**Storage Context:** `{KNOWLEDGE_PATH}`")
    
    st.info("🔄 **Data Ingestion Path (Protect):**")
    st.text_area("1. Raw User/Application Input", value=st.session_state.audit_raw_in, height=70, disabled=True)
    st.text_area("2. Sent to LLM Engine Context Window", value=st.session_state.audit_sanitized_in, height=70, disabled=True)
    
    st.success("🔄 **Data Retrieval Path (Reveal):**")
    st.text_area("3. Raw Output from LLM Core Processes", value=st.session_state.audit_raw_out, height=70, disabled=True)
    st.text_area("4. Final Detokenized Presentation Layer", value=st.session_state.audit_revealed_out, height=70, disabled=True)
    
    # --- RAW HTTP WIRE LOGGER VIEWPORT ---
    st.markdown("---")
    with st.expander("🔌 Raw CRDP API Wire Logs (HTTP Traffic)", expanded=True):
        if st.session_state.crdp_api_logs:
            for idx, log in enumerate(st.session_state.crdp_api_logs):
                action = "PROTECT" if "protect" in log["url"] else "REVEAL"
                st.markdown(f"**Transaction #{idx+1}: `{action}`**")
                st.markdown(f"`{log['method']}` -> `{log['url']}` | **Status:** `{log['status_code']}`")
                
                req_col, res_col = st.columns(2)
                with req_col:
                    st.caption("📤 Request JSON Payload")
                    st.json(log["request_payload"])
                with res_col:
                    st.caption("📥 Response JSON Payload")
                    st.json(log["response_payload"])
                st.markdown("---")
        else:
            st.caption("No internal HTTP network transactions recorded for this session turn.")