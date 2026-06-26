""" agent tools and model with tools binding, for log analysis and threat intelligence gathering"""
import json
import os
from langchain.tools import tool


# 统一维护全局静态库或字典名（由于数据库或母表概念，采用统一的大写规整匹配）
THREAT_IPS = {
    "71.240.245.228": {"reputation": "Malicious", "tags": ["Brute Force", "Botnet"], "country": "US"},
    "176.122.96.88": {"reputation": "Suspicious", "tags": ["MFA Fatigue Target"], "country": "NL"},
    "138.250.93.183": {"reputation": "Suspicious", "tags": ["Anomalous Autonomous System"], "country": "BR"},
    "25.75.83.217": {"reputation": "High Risk", "tags": ["Command and Control / Tor Node"], "country": "UK"}
}

MITRE_MAPPING = {
    "LOGIN_FAILED": {
        "Tactic": "Credential Access (TA0006)",
        "Technique": "Brute Force (T1110)",
        "Description": "攻击者尝试通过自动化工具（如 Wget/脚本）对账户进行批量凭据探测。"
    },
    "MFA_FAILURE": {
        "Tactic": "Credential Access (TA0006) / Defense Evasion (TA0005)",
        "Technique": "Multi-Factor Authentication Request Generation (T1621)",
        "Description": "针对多因素认证（MFA）的频繁失败，可能存在凭据已被窃取后的 MFA 疲劳轰炸或绕过尝试。"
    },
    "PASSWORD_CHANGE": {
        "Tactic": "Persistence (TA0003)",
        "Technique": "Account Manipulation (T1098)",
        "Description": "密码修改发生超时（TIMEOUT），需警惕异常会话劫持或恶意的账户权限持久化操作。"
    },
    "NETWORK_ALERT": {
        "Tactic": "Command and Control (TA0011)",
        "Technique": "Application Layer Protocol (T1071)",
        "Description": "触发网络层告警，且 IP 关联外部高危节点，怀疑内部主机已被控并引发恶意外发流量。"
    }
}


@tool
def parse_logs(log_path: str) -> str:
    """Analyze the given log data and return a summary."""
    if not os.path.exists(log_path):
        return f"Log file not found: {log_path}"
    try:
        import json
        with open(log_path, "r",encoding="utf-8") as f:
            log_data = json.load(f)
    except Exception as e:
        return f"Error reading log file: {e}"
    suspicious_activities = []
    alert_events = ["LOGIN_FAILED","MFA_FAILURE","UNAUTHORIZED_ACCESS","NETWORK_ALERT"]
    alert_status = ["ERROR","CRITICAL","ALERT","TIMEOUT","THREAT_DETECTED"]
    
    for log in log_data:
        event = log.get("event", "")
        status = log.get("status", "")
        user_agent = log.get("user_agent", "")
        is_suspicious = (
            event in alert_events or
            status in alert_status or
            "Wget" in user_agent
        )
        if is_suspicious:
            extracted_info = {
                "timestamp": log.get("timestamp", ""),
                "event": event,
                "status": status,
                "user_agent": user_agent,
                "user": log.get("user", ""),
                "ip": log.get("ip", ""),
                "indicator": "Suspicious automated request" if "Wget" in user_agent else "Anomalous activity detected"
            }
            suspicious_activities.append(extracted_info)
    safe_name = os.path.basename(log_path).replace("\\", "_").replace("/", "_")
    CACHE_PATH = f"logs/cache/{safe_name}_suspicious_activities.json"
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(suspicious_activities, f, ensure_ascii=False, indent=4)
    return f"Suspicious activities have been parsed and cached to {CACHE_PATH}. You can now call find_threat_from_logs or map_threats_to_mitre to analyze the suspicious activities."

@tool
def find_threat_from_logs(CACHE_PATH: str) -> str:
    """Simulate threat intelligence gathering based on the log data."""
    if not os.path.exists(CACHE_PATH):
        return "No cached suspicious activities found. Please run parse_logs first."
    
    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        suspicious_activities = f.read()
    try:
        suspicious_activities = json.loads(suspicious_activities)
        ips_to_check = [suspicious_activity.get("ip") for suspicious_activity in suspicious_activities if suspicious_activity.get("ip")]
    except:
        ips_to_check = [suspicious_activities.strip("[]\"' ")]

    result={}
    for ip in set(ips_to_check):
        if ip in THREAT_IPS:
            result[ip]=THREAT_IPS[ip]
        elif ip.startswith("10.") or ip.startswith("172.16."):
            result[ip]={"reputation": "Internal", "tags": [], "country": "LAN"}
    if not result:
        return "Threat intelligence completed: All parsed IPs are clean or external unknown. No malicious threats detected."
        
    return json.dumps(result, indent=2, ensure_ascii=False)

@tool
def map_threats_to_mitre(CACHE_PATH: str) -> str:
    """Map the log data to MITRE ATT&CK framework."""
    """Simulate threat intelligence gathering based on the log data."""
    if not os.path.exists(CACHE_PATH):
        return "No cached suspicious activities found. Please run parse_logs first."
    try:
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            suspicious_activities = f.read()
        suspicious_activities = json.loads(suspicious_activities)
        event_list = list(set([suspicious_activity.get("event") for suspicious_activity in suspicious_activities if suspicious_activity.get("event")]))
    except json.JSONDecodeError:
        return "Error reading cached suspicious activities. Please ensure the cache file is valid JSON."

    mapped_results = {}
    for event in event_list:
        lookupkey = event.upper().strip()
        if lookupkey in MITRE_MAPPING:
            mapped_results[lookupkey] = MITRE_MAPPING[lookupkey]
    if not mapped_results:
        return "No MITRE ATT&CK mapping found for the suspicious activities in the cache."
    return json.dumps(mapped_results, indent=2, ensure_ascii=False)

from langchain_ollama import ChatOllama

model = ChatOllama(
    model="llama3.1:8b",
    base_url="http://localhost:11434",
)
tools=[parse_logs, find_threat_from_logs, map_threats_to_mitre]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)
    
