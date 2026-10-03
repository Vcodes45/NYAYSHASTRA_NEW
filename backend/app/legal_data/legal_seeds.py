"""
Seed data for IPC, BNS, mappings, and landmark cases.
"""

IPC_SECTIONS = [
    {
        "section_number": "302",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Punishment for murder",
        "title_hi": "हत्या के लिए दंड",
        "content_en": "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
        "content_hi": "जो कोई हत्या करेगा वह मृत्युदंड या आजीवन कारावास से दंडित किया जाएगा, और जुर्माने के लिए भी उत्तरदायी होगा।",
        "chapter": "16",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Death or Imprisonment for Life + Fine",
        "is_cognizable": True,
        "is_bailable": False
    },
    {
        "section_number": "376",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Punishment for rape",
        "title_hi": "बलात्कार के लिए दंड",
        "content_en": "Whoever commits rape shall be punished with rigorous imprisonment...",
        "content_hi": "जो कोई बलात्कार करेगा उसे कठोर कारावास से दंडित किया जाएगा...",
        "chapter": "16",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Rigorous Imprisonment",
        "is_cognizable": True,
        "is_bailable": False
    }
]

BNS_SECTIONS = [
    {
        "section_number": "103",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Punishment for murder",
        "title_hi": "हत्या के लिए दंड",
        "content_en": "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
        "content_hi": "जो कोई हत्या करेगा वह मृत्युदंड या आजीवन कारावास से दंडित किया जाएगा, और जुर्माने के लिए भी उत्तरदायी होगा।",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Death or Imprisonment for Life + Fine",
        "is_cognizable": True,
        "is_bailable": False
    },
    {
        "section_number": "63",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Punishment for rape",
        "title_hi": "बलात्कार के लिए दंड",
        "content_en": "Whoever commits rape shall be punished with rigorous imprisonment...",
        "content_hi": "जो कोई बलात्कार करेगा उसे कठोर कारावास से दंडित किया जाएगा...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Rigorous Imprisonment",
        "is_cognizable": True,
        "is_bailable": False
    }
]

IPC_BNS_MAPPINGS = [
    {
        "ipc_section": "302",
        "bns_section": "103",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Death or Imprisonment for Life + Fine",
        "new_punishment": "Death or Imprisonment for Life + Fine",
        "punishment_increased": False
    },
    {
        "ipc_section": "376",
        "bns_section": "63",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Rigorous Imprisonment",
        "new_punishment": "Rigorous Imprisonment",
        "punishment_increased": False
    }
]

LANDMARK_CASES = [
    {
        "case_number": "SC/1973/1",
        "case_name": "Kesavananda Bharati v. State of Kerala",
        "case_name_hi": "केशवानंद भारती बनाम केरल राज्य",
        "court": "supreme_court",
        "court_name": "Supreme Court of India",
        "judgment_date": "1973-04-24",
        "reporting_year": "1973",
        "summary_en": "Basic structure doctrine established.",
        "summary_hi": "मूल संरचना सिद्धांत स्थापित किया गया।",
        "is_landmark": True,
        "domain": "constitutional",
        "key_holdings": ["Parliament cannot alter the basic structure of the Constitution."],
        "citation_string": "AIR 1973 SC 1461",
        "source_url": "https://indiankanoon.org/doc/257876/",
        "cited_sections": []
    }
]

# Provide getter functions for app.seed_database
def get_ipc_sections():
    return IPC_SECTIONS

def get_bns_sections():
    return BNS_SECTIONS

def get_mappings():
    return IPC_BNS_MAPPINGS

def get_landmark_cases():
    return LANDMARK_CASES
