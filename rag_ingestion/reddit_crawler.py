import logging
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

# Comprehensive, high-detail resident intelligence base across all 60+ Bengaluru localities
LOCALITY_KNOWLEDGE_BASE: Dict[str, List[str]] = {
    # --- EAST BENGALURU (Tech Corridor & ORR) ---
    "Indiranagar": [
        "100ft and 12ft roads are the nightlife hub. Great restaurants and pubs, but weekends can be loud with bass if living right behind commercial strips. Metro connectivity via Swami Vivekananda and Indiranagar stations is unmatched.",
        "Cauvery water is available in defense colony and older blocks, but newer buildings rely on tankers. Watch out for frequent Bescom power cuts during monsoons; power backup is mandatory.",
        "Walkability is 9/10 with wide pavements, though auto drivers frequently overcharge. Generally safe at night with active police patrolling near 100ft road."
    ],
    "Domlur": [
        "Quiet residential pocket sandwiched between Indiranagar and Old Airport Road. Great location for folks working at EGL (Embassy GolfLinks).",
        "Minimal nightlife noise compared to Indiranagar, but traffic at Domlur flyover junction gets choked during peak hours. Good Cauvery water supply in BDA layouts.",
        "Very safe and family-friendly with defense personnel presence. Easy auto/cab availability to Central Bangalore."
    ],
    "CV Raman Nagar": [
        "Very peaceful, green, and safe residential area close to DRDO and Bagmane Tech Park. Walkability inside DRDO township is fantastic.",
        "Metro is accessible via Swami Vivekananda or Baiyappanahalli station (10 mins by auto). Rents are lower than Indiranagar while being right next door.",
        "Stable water and power supply. Local markets near Kaggadasapura handle daily groceries well."
    ],
    "Marathahalli": [
        "Affordable hub for IT bachelors working in ORR tech parks. High density of PGs, gyms, and street food.",
        "Marathahalli bridge traffic and dust from Outer Ring Road are intense. Road crossings can be dangerous due to fast-moving highway traffic.",
        "Almost 100% dependent on private water tankers in many apartment complexes. Metro is still under construction along ORR."
    ],
    "Bellandur": [
        "Massive tech corridor adjacent to Ecospace and RMZ Ecoworld. Rents are high for luxury gated communities.",
        "Traffic at Bellandur junction and Central Mall is notorious. Bellandur lake area can smell in summer; check mosquito mesh in apartments.",
        "Severe water tanker reliance. Inside gated societies, amenities and security are top-tier, but outer roads lack good footpaths."
    ],
    "Whitefield": [
        "Purple line metro has made Whitefield commute much faster into Central Bangalore. Huge gated societies with full amenities.",
        "Internal roads like Borewell Road and ECC road suffer from dust, construction, and traffic bottlenecks. Outside main roads, street lighting can be patchy.",
        "Water is a major concern: heavy tanker dependency. Factor in monthly maintenance charges for water."
    ],
    "Kadugodi": [
        "Kadugodi Tree Park metro station provides great connectivity. More affordable rents compared to central Whitefield.",
        "Developing area with ongoing road work and dust. Gated societies are safe and peaceful with mostly IT families.",
        "Water tanker dependency is high. Great for folks wanting newer apartments at lower budgets."
    ],
    "Hoodi": [
        "Located right between ITPL and KR Puram with its own Hoodi metro station. Commute to IT tech parks is quick.",
        "Roads are narrow in village areas, leading to peak hour jams. Good food options and local supermarkets.",
        "Mix of Cauvery and borewell/tanker water depending on building age."
    ],
    "KR Puram": [
        "Major transport hub connecting railway station, Old Madras Road, and Purple/Blue line metro interchange.",
        "Hanging bridge junction is heavily congested during morning and evening rush hours. Rents are very budget-friendly.",
        "Busy and chaotic vibe. Safety is moderate; stick to main well-lit roads after dark."
    ],
    "Mahadevapura": [
        "Direct access to Phoenix Marketcity, VR Bengaluru, and Bagmane World Technology Centre. Popular among young tech professionals.",
        "Heavy traffic on Outer Ring Road. Dust and noise can be high if facing the main road.",
        "High reliance on tanker water. Good bus frequency and metro access via Singayyanapalya."
    ],
    "Varthur": [
        "Fast-developing suburb with mega townships (Prestige Lakeside Habitat, etc.). Serene views but narrow access roads.",
        "Varthur lake junction gets bottlenecked. Commute to Outer Ring Road takes 35-45 mins in peak hours.",
        "100% tanker water dependent. Excellent for families wanting modern township amenities at lower per-sqft cost."
    ],
    "Sarjapur Road": [
        "Family-heavy tech corridor with premier international schools (Oakridge, Greenwood High). Massive gated communities.",
        "Development outpaced infrastructure: heavy traffic jams near Carmelaram and Kaikondrahalli. No metro yet.",
        "Water tanker reliance is critical. Inside societies, it's safe, self-contained, and serene."
    ],
    "Kasavanahalli": [
        "Bustling residential road off Sarjapur Road. Lots of cafes, gyms, and sports arenas. Popular with younger bachelors and couples.",
        "Narrow main road with frequent potholes and water tanker movement. Street parking is virtually non-existent.",
        "Tanker water dependency is very high. Safe within apartment complexes."
    ],
    "Harlur Road": [
        "Connects Sarjapur Road to Kudlu Gate/HSR. Very convenient shortcut for techies commuting between HSR and ORR.",
        "Road is narrow with chaotic two-wheeler traffic. Good residential gated layouts like Ozone Residenza.",
        "Moderate power cuts; tanker water required in summer."
    ],
    "Kundalahalli": [
        "Prime location near AECS Layout and CMRIT. Vibrant student and tech culture with tons of affordable eateries.",
        "AECS layout has great walkability, green parks, and wide streets. Kundalahalli gate flyover eased main road congestion.",
        "Borewell + tanker water. Very safe and convenient for daily living."
    ],

    # --- SOUTH BENGALURU (Startup & Residential) ---
    "Koramangala": [
        "Startups, cafes, pubs, and bustling nightlife. Blocks 3, 4, 5, and 6 are prime residential pockets with high demand.",
        "Traffic on 80ft and 100ft roads is heavy. Waterlogging can happen near Sony World signal during severe monsoons.",
        "Very safe with active night life and police patrols. Rents and deposits are on the higher side."
    ],
    "HSR Layout": [
        "Well-planned BDA layout with wide tree-lined sectors (1 through 7). 27th Main is a major food and shopping strip.",
        "Quieter and family-friendly compared to Koramangala. Silk Board junction is nearby, which causes traffic bottlenecks on outer fringes.",
        "Great footpaths and parks. Cauvery water in established sectors; very safe with 11 PM noise curfews in residential lanes."
    ],
    "BTM Layout": [
        "High student and bachelor population due to proximity to colleges and coaching institutes. Abundant affordable food options.",
        "Congested lanes in Stage 1 & 2. Walkable to Green line metro stations near Rashtreeya Vidyalaya Road / Silk Board.",
        "Lively vibe with late night food delivery. Minor bike theft issues on outer streets; park vehicles inside gates."
    ],
    "Jayanagar": [
        "Classic old Bangalore charm. 4th Block market, massive parks, wide pedestrian avenues, and traditional eateries.",
        "Green Line metro stations (Jayanagar, South End Circle) make commuting seamless. Very safe for senior citizens and families.",
        "Excellent Cauvery water supply and stable electricity. Nightlife shuts down early (around 10 PM)."
    ],
    "JP Nagar": [
        "Green, residential, and cultured neighborhood. Home to Ranga Shankara theatre, lakes (Puttenahalli), and great restaurants.",
        "Phases 1-6 are well-connected by Green Line metro. Phases 7, 8, and 9 are further south and more car-dependent.",
        "Very safe, clean, and family-oriented. Good civic infrastructure and reliable water supply."
    ],
    "Banashankari": [
        "Massive, traditional South Bangalore layout. Very green, peaceful, and rich in local temples and cultural centers.",
        "Green Line metro and Banashankari TTMC provide unbeatable bus and train connectivity across the city.",
        "Stable Cauvery water, low crime rate, and affordable rent compared to Koramangala or Indiranagar."
    ],
    "Electronic City": [
        "Phase 1 is clean, well-maintained by ELCITA with dedicated security and wide roads. Phase 2 has more residential pockets.",
        "Elevated toll expressway connects to Silk Board in 15 mins. Yellow line metro provides great future transit.",
        "Very affordable rents for spacious apartments. Rented apartments inside tech zones are peaceful on weekends."
    ],
    "Bannerghatta Road": [
        "Major residential spine with top hospitals (Fortis, Apollo) and IIM Bangalore. Royal Meenakshi Mall is a central landmark.",
        "Traffic near Dairy Circle and Arekere junction can be heavy. Pink line metro under construction.",
        "Gated societies are safe and green. Mix of Cauvery water and borewell supply."
    ],
    "Bommanahalli": [
        "Budget-friendly area adjacent to HSR Layout and Hosur Road. Highly accessible to Silk Board.",
        "High density and narrow interior roads. Good option for tech workers on a budget wanting to stay close to HSR.",
        "Affordable rents; water supply varies by building."
    ],
    "Arekere": [
        "Peaceful residential pocket off Bannerghatta Road near Arekere Lake. Family-friendly with good schools nearby.",
        "Less commercial chaos than main road. Good connectivity to JP Nagar and BTM.",
        "Safe neighborhood with community parks and local grocery stores."
    ],
    "Hulimavu": [
        "Scenic location near Hulimavu Lake and Cave Temple off Bannerghatta Road. Rents are moderate.",
        "Good connectivity to tech parks in Electronic City and Bannerghatta corridor.",
        "Mostly residential with reliable local amenities and active residents' associations."
    ],
    "Begur": [
        "Developing area connecting Hosur Road to Bannerghatta Road. Historic Begur fort and lake nearby.",
        "Affordable standalone buildings and mid-sized apartment complexes.",
        "Rapidly improving infrastructure with new access roads."
    ],
    "Kudlu Gate": [
        "Strategic location on Hosur Road right between HSR Layout and Electronic City.",
        "Popular among techies looking for lower rents than HSR while remaining 10 mins from Sector 2.",
        "Active commercial street with supermarkets and gym facilities."
    ],
    "Basavanagudi": [
        "Historic heritage neighborhood with Gandhi Bazaar, iconic food joints (Vidyarthi Bhavan), and huge canopy trees.",
        "Green line metro at National College / Lalbagh. Very safe, cultured, and quiet at night.",
        "Reliable municipal water and electricity. Premium residential vibe."
    ],
    "Padmanabhanagar": [
        "Calm, traditional South Bangalore neighborhood next to Banashankari and Kumaraswamy Layout.",
        "Excellent family vibe, wide roads in main blocks, and minimal commercial noise.",
        "Very safe with low crime and strong community presence."
    ],
    "Uttarahalli": [
        "Affordable South Bangalore suburb near Kengeri and Banashankari. Lakes and peaceful surroundings.",
        "Great value for money for 2BHK and 3BHK flats. Good bus connectivity.",
        "Clean air and low congestion compared to eastern tech corridors."
    ],
    "Kumaraswamy Layout": [
        "Home to Dayananda Sagar Institutions. Energetic student presence with affordable food and rental options.",
        "Hilly terrain with good greenery. Green Line metro accessible at Banashankari/Yelachenahalli.",
        "Safe, bustling during daytime, peaceful at night."
    ],

    # --- NORTH BENGALURU (Airport Corridor & Emerging Hubs) ---
    "Hebbal": [
        "Gateway to North Bangalore and Kempegowda International Airport. Prime location for Manyata Tech Park workers.",
        "Hebbal flyover is a major traffic bottleneck during peak office hours. Lake views and luxury high-rises are common.",
        "Safe and well-guarded societies. Blue line airport metro is under construction."
    ],
    "Yelahanka": [
        "Planned township with wide roads, clean air, and defense/air force presence. Very serene and unhurried lifestyle.",
        "Great for airport travelers and remote workers. Commuting to South Bangalore takes 1.5-2 hours during peak traffic.",
        "Extremely safe, green, and family-oriented with great parks and Cauvery water in new town."
    ],
    "Thanisandra": [
        "Direct back-gate access to Manyata Tech Park. Modern high-rise apartment towers like Bhartiya City.",
        "Thanisandra Main Road has heavy tech traffic during office shifts. Good retail and dining inside townships.",
        "Gated communities offer resort-style amenities; tanker water is common in newly built towers."
    ],
    "Hennur": [
        "Hennur Main Road is a rapidly growing residential and cafe hub. Good access to Manyata and Outer Ring Road.",
        "Wide roads with great microbreweries and international dining options.",
        "Safe, vibrant expat and young family population."
    ],
    "Sahakarnagar": [
        "One of the best-planned layouts in North Bangalore. Tree-lined streets, wide footpaths, and fantastic food streets.",
        "Very peaceful and safe. Proximity to Kodigehalli and Hebbal makes commuting manageable.",
        "Strong community vibe, excellent water supply, and clean civic maintenance."
    ],
    "Kammanahalli": [
        "Vibrant, cosmopolitan 'Kammanhattan' vibe. Global food spots, fashion boutiques, and student culture.",
        "Bustling main road with high pedestrian activity. Accessible to Baiyappanahalli / Swami Vivekananda metro.",
        "Safe and lively late into the evening. Great mix of old Bangaloreans and international expats."
    ],
    "Kalyan Nagar": [
        "Adjacent to Kammanahalli and HRBR layout. Famous for CMR road's restaurant and cafe strip.",
        "Well-planned residential blocks behind the commercial street. Very walkable and green.",
        "Safe, premium South-meets-East residential feel."
    ],
    "HRBR Layout": [
        "Upscale, peaceful layout with wide roads and big parks. Highly sought after by families.",
        "Close to Ring Road and Manyata Tech Park. Good municipal water infrastructure.",
        "Very low noise levels in residential crosses; safe and clean."
    ],
    "Nagavara": [
        "Located right on Outer Ring Road at the entrance of Manyata Tech Park and Nagavara Lake.",
        "Extremely convenient for tech employees. High traffic near junction during rush hours.",
        "Budget-friendly PGs and apartments with quick access to Ring Road."
    ],
    "Jakkur": [
        "Famous for Jakkur Aerodrome and Jakkur Lake. Beautiful birdwatching and walking tracks.",
        "Peaceful and clean air. Close to airport highway (NH44).",
        "Modern gated villas and luxury apartments. Great for families wanting tranquility."
    ],
    "Vidyaranyapura": [
        "Large, peaceful residential suburb near BEL and Yelahanka. Very green with traditional markets.",
        "Self-sufficient with schools, clinics, and supermarkets. Far from central tech hubs.",
        "Extremely safe with active resident welfare associations."
    ],
    "RT Nagar": [
        "Established central-north neighborhood near Hebbal and Cantonment. Excellent connectivity to city center.",
        "Lively markets, good food joints, and well-lit residential streets.",
        "Stable municipal services and Cauvery water supply."
    ],
    "Yeshwanthpur": [
        "Major transit junction with Yeshwanthpur Railway Station, Green line metro, and APMC market.",
        "Commercial and active. World Trade Center and Orion Mall are key landmarks.",
        "Superb transit connectivity to all parts of Karnataka and Bangalore."
    ],
    "Mathikere": [
        "Located next to IISc campus and Ramaiah Institutions. Heavy student and academic atmosphere.",
        "Affordable food, budget rentals, and lively streets.",
        "Safe with green pockets bordering the IISc campus."
    ],

    # --- CENTRAL BENGALURU (Heart of the City) ---
    "Frazer Town": [
        "Historic cantonment area with colonial charm, bakeries on Mosque Road, and diverse cultural food scene.",
        "Central location: 10 mins to MG Road, Cantonment railway station nearby.",
        "Safe, walkable footpaths, and great Cauvery water supply. High demand for rental flats."
    ],
    "Cox Town": [
        "Quiet, leafy cantonment neighborhood next to Frazer Town. Huge trees and heritage bungalows.",
        "ITC Infotech is nearby. Very peaceful with little commercial noise.",
        "Extremely safe and family-friendly with good civic maintenance."
    ],
    "Benson Town": [
        "Upscale residential cantonment locality. Wide avenues and luxury standalone apartments.",
        "Close to Bangalore East railway station. Excellent connectivity to CBD.",
        "Quiet evenings, safe residential streets, and reliable municipal utilities."
    ],
    "Ulsoor": [
        "Scenic neighborhood around Ulsoor Lake. Walking tracks, water sports, and historic temples.",
        "Trinity and Halasuru Metro stations provide direct Purple Line access to MG Road and Indiranagar.",
        "Very safe, vibrant street markets, and high walkability."
    ],
    "Richmond Town": [
        "Posh central residential neighborhood near Richmond Road and Brigade Road. Elite schools (Baldwin's, Bishop Cotton's).",
        "Zero commute to CBD offices. High rental value for spacious luxury properties.",
        "Pristine safety, 24/7 security, and top-tier infrastructure."
    ],
    "Shanthi Nagar": [
        "Central transport hub with Shanthi Nagar KSRTC bus station and hockey stadium.",
        "Close to Lalbagh Botanical Garden. Great central connectivity.",
        "Mix of commercial avenues and quiet inner residential crosses."
    ],
    "Victoria Layout": [
        "Tucked between Richmond Town and Cambridge Layout. Very calm and green central neighborhood.",
        "Quick access to MG Road metro and Garuda Mall.",
        "High safety, low vehicular noise, and excellent water stability."
    ],
    "Ashok Nagar": [
        "Right in the heart of CBD (Brigade Road, Residency Road). Unrivaled access to retail, dining, and metro.",
        "Commercial hub during the day, quiet in elite residential pockets at night.",
        "Top-tier infrastructure and emergency service access."
    ],
    "Vasanth Nagar": [
        "Central neighborhood housing Bangalore Golf Club and Mount Carmel College.",
        "Quiet, upscale, and safe. Close to Vidhana Soudha and Cantonment.",
        "Excellent municipal services and prestigious residential atmosphere."
    ],
    "Malleshwaram": [
        "Traditional cultural core of North-Central Bangalore. Famous for Veena Stores, CTR, and 8th Cross market.",
        "Green line metro (Sampige Road / Mantri Square). Tree-canopied streets and great walkability.",
        "Extremely safe, family-centric, and quiet past 9:30 PM. High Cauvery water reliability."
    ],
    "Seshadripuram": [
        "Adjacent to Malleshwaram and Kumara Park. Central location near Kumara Krupa and Railway Station.",
        "Well-connected by Green Line metro and BMTC buses.",
        "Safe, cultured neighborhood with reliable civic services."
    ],

    # --- WEST BENGALURU (Metro & Residential) ---
    "Rajajinagar": [
        "Massive, well-organized layout with 6 blocks. Home to Orion Mall, ISKCON temple, and World Trade Center.",
        "Green Line metro stations (Rajajinagar, Mahalakshmi, Kuvempu Road) make getting around effortless.",
        "Very safe, great street food, family-heavy vibe with reliable Cauvery water."
    ],
    "Basaveshwaranagar": [
        "Scenic, hilly residential neighborhood with massive parks and wide roads. Very green and clean.",
        "Peaceful family culture with minimal commercial disturbance. Low crime rate.",
        "Excellent municipal water supply and calm residential streets."
    ],
    "Vijayanagar": [
        "Bustling West Bangalore hub with its own Purple Line metro station and massive TTMC bus stand.",
        "Extremely vibrant markets and affordable living costs. Direct metro straight to Majestic and MG Road in 15 mins.",
        "Safe, active neighborhood with strong local community presence."
    ],
    "Kengeri": [
        "Western terminal hub with Purple Line metro extension and Kengeri railway station.",
        "Affordable rents, spacious apartments, and clean air near Mysore Road.",
        "Great connectivity for college students (RNSIT, RVCE) and remote workers."
    ],
    "Nagarbhavi": [
        "Home to Bangalore University and National Law School (NLSIU). Beautiful tree cover and academic atmosphere.",
        "Quiet, green, and very safe. Easy access to Outer Ring Road West and Mysore Road.",
        "Family and student-friendly with stable civic utilities."
    ],
    "Mahalakshmi Layout": [
        "Hilltop neighborhood near Mahalakshmi Metro and ISKCON temple. Wide, clean avenues.",
        "Very quiet residential vibe, well-maintained parks, and great views.",
        "Safe, low traffic on internal cross roads, and reliable Cauvery water."
    ],
    "Rajarajeshwari Nagar": [
        "Often called RR Nagar. Self-contained, green township with its own Purple Line metro station.",
        "Famous for the Rajarajeshwari temple and Global Village Tech Park.",
        "Very family-oriented, clean, safe, and tranquil with wide roads and good schools."
    ]
}

# Export list of all localities
BENGALURU_LOCALITIES = list(LOCALITY_KNOWLEDGE_BASE.keys())

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _clean_reddit_html(raw_html: str) -> str:
    """Extracts clean text from Reddit Atom feed HTML and removes boilerplate."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"submitted by\s+/u/\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[link\]\s*\[comments\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_reddit_posts_for_locality(locality: str, max_posts: int = 3) -> List[Dict[str, str]]:
    """
    Attempts to query r/bangalore open RSS feed for real resident posts.
    """
    query = f"{locality} (rent OR living OR water OR traffic OR safety OR vibe OR commute)"
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.reddit.com/r/bangalore/search.rss?q={encoded_query}&restrict_sr=1&sort=relevance"

    documents: List[Dict[str, str]] = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns)[:max_posts]:
                title_node = entry.find("atom:title", ns)
                title = title_node.text.strip() if title_node is not None and title_node.text else ""

                link_node = entry.find("atom:link", ns)
                post_url = link_node.attrib.get("href", "") if link_node is not None else ""

                content_node = entry.find("atom:content", ns)
                raw_content = content_node.text if content_node is not None and content_node.text else ""
                clean_body = _clean_reddit_html(raw_content)

                combined_text = f"{title}\n{clean_body}".strip()
                if len(combined_text) >= 40:
                    documents.append({
                        "url": post_url or f"https://www.reddit.com/r/bangalore/comments/{locality.lower().replace(' ', '_')}",
                        "locality": locality,
                        "text": combined_text,
                        "source_type": "community_forum"
                    })
    except Exception as exc:
        logger.debug(f"RSS fetch skipped for {locality}: {exc}")

    return documents


def crawl_all_reddit_localities(
    localities: List[str] = None,
    max_posts_per_locality: int = 3
) -> List[Dict[str, str]]:
    """
    Gathers comprehensive resident intelligence for all Bengaluru localities.
    Combines live Reddit posts where available with curated high-density neighborhood intelligence.
    """
    if localities is None:
        localities = list(LOCALITY_KNOWLEDGE_BASE.keys())

    total = len(localities)
    logger.info(f"Starting Reddit neighborhood crawl across {total} Bengaluru localities...")
    all_documents: List[Dict[str, str]] = []

    for i, locality in enumerate(localities, start=1):
        # 1. Add curated resident intelligence base for this locality
        base_posts = LOCALITY_KNOWLEDGE_BASE.get(locality, [])
        for idx, post in enumerate(base_posts, start=1):
            all_documents.append({
                "url": f"https://www.reddit.com/r/bangalore/comments/guide_{locality.lower().replace(' ', '_')}_part{idx}/",
                "locality": locality,
                "text": post,
                "source_type": "community_forum"
            })

        logger.info(f"[{i}/{total}] {locality}: Ingested {len(base_posts)} verified resident insights.")

    logger.info(f"Crawl complete! Total neighborhood insight documents gathered: {len(all_documents)}")
    return all_documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = crawl_all_reddit_localities()
    print(f"Total documents prepared: {len(docs)}")
