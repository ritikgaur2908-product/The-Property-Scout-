from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from backend.db.models import Property
from backend.llm.state_manager import UserPreferences

def build_base_query(db: Session, preferences: UserPreferences, include_soft_filters: bool = True):
    query = db.query(Property).filter(Property.status == 'available')
    
    if preferences.get('max_budget'):
        query = query.filter(Property.rent <= preferences['max_budget'])
        
    if preferences.get('min_bhk'):
        query = query.filter(Property.rooms >= preferences['min_bhk'])
        
    if preferences.get('localities') and len(preferences['localities']) > 0:
        from sqlalchemy import or_
        conditions = [Property.locality.ilike(f"%{loc}%") for loc in preferences['localities']]
        conditions += [Property.address.ilike(f"%{loc}%") for loc in preferences['localities']]
        query = query.filter(or_(*conditions))
        
    if preferences.get('accommodation_type'):
        query = query.filter(Property.accommodation_type == preferences['accommodation_type'])
        
    soft_filters_applied = []
    if include_soft_filters:
        if preferences.get('gender') and preferences.get('gender') != 'any':
            from sqlalchemy import or_
            query = query.filter(or_(Property.gender_openness == preferences['gender'], Property.gender_openness == 'any'))
            soft_filters_applied.append('gender')
            
        if preferences.get('food') and preferences.get('food') != 'any':
            from sqlalchemy import or_
            query = query.filter(or_(Property.flatmate_food_pref == preferences['food'], Property.flatmate_food_pref == 'any'))
            soft_filters_applied.append('food')
            
        if preferences.get('smoking') and preferences.get('smoking') != 'any':
            from sqlalchemy import or_
            query = query.filter(or_(Property.flatmate_smoking_pref == preferences['smoking'], Property.flatmate_smoking_pref == 'any'))
            soft_filters_applied.append('smoking')
            
        if preferences.get('parking'):
            query = query.filter(Property.parking_available == True)
            soft_filters_applied.append('parking')
            
    if preferences.get('min_bhk'):
        query = query.order_by(Property.rooms.asc(), Property.created_at.desc())
    else:
        query = query.order_by(Property.created_at.desc())
        
    return query, soft_filters_applied

def format_properties(properties: List[Property], preferences: UserPreferences) -> List[Dict[str, Any]]:
    results = []
    for p in properties:
        reasons = []
        if preferences.get('max_budget') and p.rent <= preferences['max_budget']:
            reasons.append(f"Under ₹{preferences['max_budget']:,} budget")
        if preferences.get('min_bhk') and p.rooms >= preferences['min_bhk']:
            reasons.append(f"Matches {preferences['min_bhk']}+ BHK")
        if preferences.get('localities'):
            reasons.append("In preferred area")
        if preferences.get('parking') and p.parking_available:
            reasons.append("Has Parking")
            
        reasoning = " • ".join(reasons) if reasons else "Matched based on your recent preferences."

        results.append({
            "id": str(p.id),
            "reasoning": reasoning,
            "rent": p.rent,
            "rooms": p.rooms,
            "type": p.accommodation_type,
            "locality": p.locality,
            "address": p.address,
            "move_in_time": p.move_in_time,
            "parking": p.parking_available,
            "gender": p.gender_openness,
            "food": p.flatmate_food_pref,
            "smoking": p.flatmate_smoking_pref,
            "source_url": p.source_url
        })
    return results

def search_properties_in_db(db: Session, preferences: UserPreferences, limit: int = 5) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Translates UserPreferences into a SQLAlchemy query and fetches matching properties.
    If soft filters cause 0 results, it falls back to hard filters only and returns a warning.
    """
    query, soft_filters = build_base_query(db, preferences, include_soft_filters=True)
    properties = query.limit(limit).all()
    
    warning = None
    if len(properties) == 0:
        if len(soft_filters) > 0:
            fallback_query, _ = build_base_query(db, preferences, include_soft_filters=False)
            properties = fallback_query.limit(limit).all()
            if len(properties) > 0:
                warning = f"No properties matched your preference for {', '.join(soft_filters)}. Showing alternatives without those filters."
        
        # If still 0 properties (hard filters failed), query what actually exists in the locality
        if len(properties) == 0 and preferences.get('localities'):
            locs = preferences['localities']
            from sqlalchemy import or_, func
            conditions = [Property.locality.ilike(f"%{loc}%") for loc in locs]
            
            # Find minimum rent and available configurations in that locality
            available_props = db.query(Property.rooms, func.min(Property.rent)).filter(or_(*conditions), Property.status == 'available').group_by(Property.rooms).all()
            
            if available_props:
                available_info = ", ".join([f"{int(rooms)} BHK starting at ₹{int(min_rent):,}" for rooms, min_rent in available_props if rooms is not None])
                warning = f"No exact matches found for your criteria. However, in this locality we do have: {available_info}."
            else:
                warning = f"We currently have absolutely no available properties in {', '.join(locs)}."
                
    results = format_properties(properties, preferences)
    return results, warning
