import re

def scrub_pii(text: str) -> str:
    """
    Removes emails, phone numbers, and common agent names using regex.
    """
    if not text:
        return ""
        
    # 1. Scrub Emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    text = re.sub(email_pattern, "[EMAIL REMOVED]", text)
    
    # 2. Scrub Indian Phone Numbers (+91, 0, or just 10 digits)
    phone_pattern = r'(?:\+91[\-\s]?)?[0]?[6789]\d{9}'
    text = re.sub(phone_pattern, "[PHONE REMOVED]", text)
    
    # Also catch space-separated or dashed formats like 98765-43210
    phone_pattern_2 = r'[6789]\d{4}[\-\s]\d{5}'
    text = re.sub(phone_pattern_2, "[PHONE REMOVED]", text)
    
    # 3. Scrub basic Name footprints (e.g. "Contact Harshit", "Call Agent Rahul")
    name_contact_pattern = r'(?i)(contact|call|ask for)\s+([A-Za-z]+(?:\s[A-Za-z]+)?)'
    text = re.sub(name_contact_pattern, r'\1 [NAME REMOVED]', text)
            
    return text
