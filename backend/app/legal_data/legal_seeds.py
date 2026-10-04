"""
Seed data for IPC, BNS, mappings, and landmark cases.
"""

IPC_SECTIONS = [
    {
        "section_number": "378",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Theft",
        "title_hi": "चोरी",
        "content_en": "Whoever, intending to take dishonestly any movable property out of the possession of any person...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 3 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "383",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Extortion",
        "title_hi": "जबरन वसूली",
        "content_en": "Whoever intentionally puts any person in fear of any injury to that person, or to any other...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 3 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "390",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Robbery",
        "title_hi": "लूट",
        "content_en": "In all robbery there is either theft or extortion...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Rigorous imprisonment up to 10 years and fine",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "391",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Dacoity",
        "title_hi": "डकैती",
        "content_en": "When five or more persons conjointly commit or attempt to commit robbery...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Imprisonment for life, or rigorous imprisonment up to 10 years, and fine",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "415",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Cheating",
        "title_hi": "धोखाधड़ी",
        "content_en": "Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 1 year or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "425",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Mischief",
        "title_hi": "शरारत",
        "content_en": "Whoever with intent to cause, or knowing that he is likely to cause, wrongful loss or damage...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 3 months or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "441",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Criminal trespass",
        "title_hi": "आपराधिक अतिचार",
        "content_en": "Whoever enters into or upon property in the possession of another with intent to commit an offence...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 3 months or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "463",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Forgery",
        "title_hi": "जालसाजी",
        "content_en": "Whoever makes any false document or false electronic record or part of a document...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 2 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "499",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Defamation",
        "title_hi": "मानहानि",
        "content_en": "Whoever, by words either spoken or intended to be read, or by signs or by visible representations...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Simple imprisonment up to 2 years, or with fine, or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "503",
        "act_code": "IPC",
        "act_name": "Indian Penal Code",
        "title_en": "Criminal intimidation",
        "title_hi": "आपराधिक धमकी",
        "content_en": "Whoever threatens another with any injury to his person, reputation or property...",
        "year_enacted": 1860,
        "domain": "criminal",
        "punishment_description": "Up to 2 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },

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
        "section_number": "303",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Theft",
        "title_hi": "चोरी",
        "content_en": "Whoever, intending to take dishonestly any movable property out of the possession of any person...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 3 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "308",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Extortion",
        "title_hi": "जबरन वसूली",
        "content_en": "Whoever intentionally puts any person in fear of any injury to that person, or to any other...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 3 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "309",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Robbery",
        "title_hi": "लूट",
        "content_en": "In all robbery there is either theft or extortion...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Rigorous imprisonment up to 10 years and fine",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "310",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Dacoity",
        "title_hi": "डकैती",
        "content_en": "When five or more persons conjointly commit or attempt to commit robbery...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Imprisonment for life, or rigorous imprisonment up to 10 years, and fine",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "318",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Cheating",
        "title_hi": "धोखाधड़ी",
        "content_en": "Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 1 year or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "324",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Mischief",
        "title_hi": "शरारत",
        "content_en": "Whoever with intent to cause, or knowing that he is likely to cause, wrongful loss or damage...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 3 months or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "329",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Criminal trespass",
        "title_hi": "आपराधिक अतिचार",
        "content_en": "Whoever enters into or upon property in the possession of another with intent to commit an offence...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 3 months or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "336",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Forgery",
        "title_hi": "जालसाजी",
        "content_en": "Whoever makes any false document or false electronic record or part of a document...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 2 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "356",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Defamation",
        "title_hi": "मानहानि",
        "content_en": "Whoever, by words either spoken or intended to be read, or by signs or by visible representations...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Simple imprisonment up to 2 years, or with fine, or both",
        "is_cognizable": True,
        "is_bailable": True
    },
    {
        "section_number": "351",
        "act_code": "BNS",
        "act_name": "Bhartiya Nyaya Sanhita",
        "title_en": "Criminal intimidation",
        "title_hi": "आपराधिक धमकी",
        "content_en": "Whoever threatens another with any injury to his person, reputation or property...",
        "year_enacted": 2023,
        "domain": "criminal",
        "punishment_description": "Up to 2 years or fine or both",
        "is_cognizable": True,
        "is_bailable": True
    },

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
        "ipc_section": "378",
        "bns_section": "303",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 3 years or fine or both",
        "new_punishment": "Up to 3 years or fine or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "383",
        "bns_section": "308",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 3 years or fine or both",
        "new_punishment": "Up to 3 years or fine or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "390",
        "bns_section": "309",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Rigorous imprisonment up to 10 years and fine",
        "new_punishment": "Rigorous imprisonment up to 10 years and fine",
        "punishment_increased": False
    },
    {
        "ipc_section": "391",
        "bns_section": "310",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Imprisonment for life, or rigorous imprisonment up to 10 years, and fine",
        "new_punishment": "Imprisonment for life, or rigorous imprisonment up to 10 years, and fine",
        "punishment_increased": False
    },
    {
        "ipc_section": "415",
        "bns_section": "318",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 1 year or fine or both",
        "new_punishment": "Up to 1 year or fine or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "425",
        "bns_section": "324",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 3 months or fine or both",
        "new_punishment": "Up to 3 months or fine or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "441",
        "bns_section": "329",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 3 months or fine or both",
        "new_punishment": "Up to 3 months or fine or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "463",
        "bns_section": "336",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 2 years or fine or both",
        "new_punishment": "Up to 2 years or fine or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "499",
        "bns_section": "356",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Simple imprisonment up to 2 years, or with fine, or both",
        "new_punishment": "Simple imprisonment up to 2 years, or with fine, or both",
        "punishment_increased": False
    },
    {
        "ipc_section": "503",
        "bns_section": "351",
        "mapping_type": "exact",
        "changes": [],
        "punishment_changed": False,
        "old_punishment": "Up to 2 years or fine or both",
        "new_punishment": "Up to 2 years or fine or both",
        "punishment_increased": False
    },

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
