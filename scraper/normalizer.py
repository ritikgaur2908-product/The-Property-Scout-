import re

def normalize_rent(rent_str: str) -> int:
    """
    Converts strings like '₹ 35,000' or '35000' into integer 35000.
    """
    if not rent_str:
        return 0
    clean_str = re.sub(r'[^\d]', '', str(rent_str))
    return int(clean_str) if clean_str else 0

def normalize_bhk(bhk_str: str) -> int:
    """
    Converts strings like '2 BHK' or '3BHK' into integer 2 or 3.
    """
    if not bhk_str:
        return 0
    match = re.search(r'(\d+)', str(bhk_str))
    return int(match.group(1)) if match else 0

def normalize_gender(gender_str: str) -> str:
    """
    Converts strings to enum 'male', 'female', or 'any'
    """
    if not gender_str:
        return 'any'
    lower = gender_str.lower()
    if 'female' in lower or 'girls' in lower:
        return 'female'
    elif 'male' in lower or 'boys' in lower:
        return 'male'
    return 'any'

def normalize_food_pref(food_str: str) -> str:
    """
    Converts strings to enum 'veg', 'non_veg', or 'any'
    """
    if not food_str:
        return 'any'
    lower = food_str.lower()
    if 'non' in lower and 'veg' in lower:
        return 'non_veg'
    elif 'veg' in lower:
        return 'veg'
    return 'any'

def normalize_smoking_pref(smoking_str: str) -> str:
    """
    Converts strings to enum 'smoker', 'non_smoker', or 'any'
    """
    if not smoking_str:
        return 'any'
    lower = smoking_str.lower()
    if ('non' in lower or 'no ' in lower) and 'smok' in lower:
        return 'non_smoker'
    elif 'smok' in lower:
        return 'smoker'
    return 'any'
