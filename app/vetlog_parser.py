import re

def extract_money(text: str) -> list[int]:
    """
    Extracts all monetary amounts from the text safely, ignoring commas.
    Looks for amounts prefixed or suffixed by PKR, Rs, etc.
    """
    if not text:
        return []
    
    # Matches PKR 100,000 or Rs 50,000 or 100000 PKR
    # Find all numbers that might have commas
    amounts = []
    # Find PKR or Rs followed by numbers with optional commas
    matches = re.findall(r'(?:PKR|Rs\.?)\s*([\d,]+)', str(text), re.IGNORECASE)
    for match in matches:
        clean_num = match.replace(',', '')
        try:
            amounts.append(int(clean_num))
        except ValueError:
            pass
            
    # Also find numbers followed by PKR
    matches_post = re.findall(r'([\d,]+)\s*(?:PKR|Rs\.?)', str(text), re.IGNORECASE)
    for match in matches_post:
        clean_num = match.replace(',', '')
        try:
            amounts.append(int(clean_num))
        except ValueError:
            pass
            
    return list(set(amounts)) # unique amounts

def extract_donor(text: str):
    """
    Attempts to extract a donor's name from a message string.
    Returns the donor name or None if not found.
    Handles punctuation and Roman Urdu mixing.
    """
    if not text:
        return None
    
    text = str(text)
    donor = None
    
    # 1. "from Ms. Fatima" or "from JDC Foundation"
    match = re.search(r'from\s+(.*?)(?=\s+PKR|\s+Rs|\s+shelter|$)', text, re.IGNORECASE)
    if match:
        donor = match.group(1).strip()
    
    # 2. "Donor: JDC Foundation"
    if not donor:
        match = re.search(r'Donor:\s+(.*?)(?=\s+PKR|\s+Rs|\s+shelter|$)', text, re.IGNORECASE)
        if match:
            donor = match.group(1).strip()
            
    # 3. "JDC Foundation se" 
    if not donor:
        match = re.search(r'(.*?)\s+se\b', text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # grab capitalized words to avoid "us se"
            words = candidate.split()
            cap_words = [w for w in words if w and w[0].isupper() and w.lower() != 'pkr']
            if cap_words:
                donor = ' '.join(cap_words)
                
    # 4. "Thank you Ms. Fatima"
    if not donor:
        match = re.search(r'Thank you\s+(.*?)(?=\s+PKR|\s+Rs|\s+shelter|$)', text, re.IGNORECASE)
        if match:
            donor = match.group(1).strip()
    
    if donor:
        donor = re.sub(r'PKR\s*[\d,]+', '', donor, flags=re.IGNORECASE)
        donor = donor.replace('milay', '').replace('donation', '').strip('.,-! ')
        if donor.lower() == 'jdc':
            donor = 'JDC Foundation'
            
    return donor

def is_expenditure(text: str) -> bool:
    """
    Checks if a message indicates an expenditure or fund allocation rather than a donation.
    """
    if not text:
        return False
        
    text_lower = str(text).lower()
    expenditure_keywords = ['allocated', 'spent', 'used for', 'paid', 'kharach']
    
    for kw in expenditure_keywords:
        if kw in text_lower:
            return True
            
    return False
