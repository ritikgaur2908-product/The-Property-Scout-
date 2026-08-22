from typing import Dict, List, Any

def map_osm_amenities(raw_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses and categorizes raw OSM Overpass data into structured buckets.
    """
    categories = {
        "healthcare": [],
        "education": [],
        "parks_and_leisure": [],
        "transport": [],
        "shopping_and_dining": []
    }
    
    elements = raw_data.get("elements", [])
    
    for el in elements:
        # We only care about nodes that have tags
        tags = el.get("tags", {})
        if not tags:
            continue
            
        name = tags.get("name", "Unnamed")
        
        # Determine category based on tags
        item = {
            "name": name,
            "lat": el.get("lat"),
            "lon": el.get("lon"),
            "type": tags.get("amenity") or tags.get("leisure") or tags.get("public_transport") or tags.get("shop")
        }
        
        if "amenity" in tags:
            val = tags["amenity"]
            if val in ["hospital", "clinic"]:
                categories["healthcare"].append(item)
            elif val in ["school", "college"]:
                categories["education"].append(item)
            elif val in ["cafe", "restaurant", "marketplace"]:
                categories["shopping_and_dining"].append(item)
                
        if "leisure" in tags:
            val = tags["leisure"]
            if val in ["park", "playground"]:
                categories["parks_and_leisure"].append(item)
                
        if "public_transport" in tags or tags.get("highway") == "bus_stop":
            categories["transport"].append(item)
            
        if "shop" in tags:
            val = tags["shop"]
            if val in ["supermarket", "mall"]:
                categories["shopping_and_dining"].append(item)
                
    # Sort and slice (e.g., top 5 per category to avoid context bloat)
    for key in categories:
        # Filter out unnamed if there are many, but keep them if few
        named_items = [i for i in categories[key] if i["name"] != "Unnamed"]
        categories[key] = named_items[:5] if len(named_items) >= 5 else categories[key][:5]
        
    return categories
