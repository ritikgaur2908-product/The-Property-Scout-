import json
import os
import random

MOCK_REDDIT_DATA = [
    {
        "locality": "Koramangala",
        "posts": [
            "Living in Koramangala block 4 is great but the traffic on the 80ft road is insane. A 2km commute takes 30 mins in the evening. Also, water logging near Sony World signal is guaranteed during heavy monsoon.",
            "The vibe here is very student/startup driven, lots of nightlife. But beware of the stray dog menace at night near the parks. Dogs bark constantly past midnight.",
            "Pretty safe area overall, even at night due to the bustling pubs. The local police station is right in the 3rd block. Never faced any serious crime issues, but watch out for broker scams when renting.",
            "No metro station nearby yet, you have to rely entirely on autos or your own vehicle. Parking on the street is a nightmare and traffic police frequently tow cars. Always get a place with dedicated garage parking."
        ]
    },
    {
        "locality": "HSR Layout",
        "posts": [
            "HSR is probably the most well-planned layout. Wide roads, lots of trees. It's quieter and more family-heavy compared to Koramangala. Neighbours usually keep to themselves but are friendly.",
            "Walkability is fantastic here. The footpaths on the 27th main are actually usable. No metro connectivity though, have to go to Silk Board which is a massive traffic bottleneck.",
            "It's very safe, well-lit streets everywhere. But the garbage management is occasionally bad in Sector 1. Also, because of the open drains in some parts, mosquitoes and pests are a huge issue in the evenings.",
            "There's a strict 11 PM curfew for loud music in most residential societies here. Perfect if you want peace and quiet."
        ]
    },
    {
        "locality": "Indiranagar",
        "posts": [
            "Indiranagar 100ft road is the party capital. Amazing vibe, but if you live 1-2 streets behind it, be prepared for loud bass thumping until 1 AM on weekends. It's extremely loud.",
            "Getting around is super easy because of the Swami Vivekananda Metro station. You can walk to the metro from most places. Auto drivers here will rip you off though.",
            "There have been a few incidents of chain snatching reported recently early in the mornings. Stick to the busy, well-lit streets after dark. The Manipal Hospital is very close by for emergencies.",
            "Bescom power cuts are quite frequent, maybe 1-2 hours a week. A UPS/Inverter is absolutely mandatory if you are working from home."
        ]
    },
    {
        "locality": "Whitefield",
        "posts": [
            "The new purple line metro has made Whitefield so much more accessible! But the internal roads connecting tech parks are still dusty, pothole-ridden, and have severe traffic jams.",
            "Mostly gated communities here, so it feels very safe and insulated. Very family-heavy vibe. However, street lighting outside the main roads is very poor.",
            "Water supply is a critical issue in Whitefield. Most apartments rely 100% on private water tankers. Make sure you ask the landlord about tanker costs before renting.",
            "Air quality is pretty bad due to ongoing construction everywhere. The dust is terrible if you have a balcony facing the main road."
        ]
    },
    {
        "locality": "Bellandur",
        "posts": [
            "Bellandur lake smells awful during summers and foams during rains. The traffic at Bellandur junction is legendary for being bad. Commute is terrible even for short distances.",
            "It's purely a tech corridor, not much local culture. Very high density of IT folks. Safe inside societies but the main roads are chaotic and not pedestrian friendly.",
            "Water issues are severe here. Tanker mafia controls the supply. Renting here means you will definitely pay high water bills.",
            "No metro access at all. You have to rely on ORR buses which are insanely crowded. Auto drivers cancel trips here constantly."
        ]
    },
    {
        "locality": "BTM Layout",
        "posts": [
            "BTM is extremely student and bachelor friendly. Very affordable food options everywhere. But it's very congested and noisy at almost all hours.",
            "Traffic towards Silk Board is a daily nightmare. However, you can walk to the yellow/green line metro if you live in BTM Stage 1.",
            "Petty theft and bike thefts happen occasionally. Always park inside the gates, never on the street. The area feels busy so walking at night is generally safe.",
            "Lots of PG accommodations mean high turnover of neighbors. Not great if you want a quiet family vibe, but excellent if you want cheap rent and convenience."
        ]
    },
    {
        "locality": "Jayanagar",
        "posts": [
            "Classic old Bangalore charm. Huge trees, beautiful parks, and very quiet. Extremely family-oriented and peaceful culture.",
            "Walkability is 10/10. Wide footpaths. You also have the green line metro station right in the middle (Jayanagar block 4), making commute to majestic super easy.",
            "Very safe area, lots of senior citizens and families. Very little crime. However, almost everything shuts down by 10 PM. No nightlife.",
            "Water and electricity are mostly stable since it's an old, well-planned area. Rarely any flooding or massive power cuts."
        ]
    },
    {
        "locality": "JP Nagar",
        "posts": [
            "Similar to Jayanagar but slightly more modern. Great parks and lakes. Very peaceful vibe with mostly families and long-term residents.",
            "The green line metro serves JP Nagar phase 1 to 6 well, but phase 7/8 are a bit disconnected. Traffic on 15th cross can be bad during peak hours.",
            "Extremely safe at night. Very well-lit roads and active neighborhood watches. No major crime reported.",
            "Garbage collection is very systematic. One of the cleaner neighborhoods in South Bangalore."
        ]
    },
    {
        "locality": "Marathahalli",
        "posts": [
            "Marathahalli bridge is one of the worst traffic bottlenecks in the city. The noise pollution and dust from the Outer Ring Road is non-stop.",
            "Very cheap and practical if you work in ORR tech parks. Lots of bachelors and young professionals. But the aesthetic vibe is purely chaotic commercial.",
            "Safety is decent but be careful of pickpockets at the bus stops. Crossing the main road feels like playing Frogger.",
            "Water scarcity is common in the summer. No metro access, heavily reliant on BMTC buses which get stuck in traffic."
        ]
    },
    {
        "locality": "Electronic City",
        "posts": [
            "E-City Phase 1 is well planned, Phase 2 is a bit messy. The elevated tollway makes getting to the city center fast, but it's very far from central Bangalore.",
            "Yellow line metro is coming soon which will fix the isolation issue. Currently, relying on buses or cabs to go to Indiranagar takes 1.5 hours.",
            "Safety is very good inside the tech park zones, but outskirts can feel a bit deserted and dark at night. Lots of stray dogs in empty plots.",
            "Very affordable rents for huge apartments. Family friendly, quiet on weekends because it's a pure IT hub."
        ]
    },
    {
        "locality": "Malleshwaram",
        "posts": [
            "The absolute heart of traditional Bangalore. Very cultural, quiet, and deeply rooted in community. Amazing street food (CTR, Veena Stores).",
            "Extremely safe, heavily populated by families and old-timers. You can walk around safely at any hour, though everything closes early.",
            "Green line metro (Mantri Square / Sampige Road) makes connectivity incredible. Walkability is great, huge canopy trees everywhere.",
            "Don't expect any modern nightlife or pubs. It's a quiet residential area. Parking on the narrow cross roads is impossible if you have a big car."
        ]
    },
    {
        "locality": "Hebbal",
        "posts": [
            "Hebbal flyover traffic is infamous, but the connectivity to the airport is unmatched. Great if you travel by flight frequently.",
            "Lots of high-end, luxury apartments with great views of the lake. Very safe, heavily guarded societies. Outside the societies, it's mostly highway.",
            "No metro yet, but the blue line is under construction. Currently you have to rely on airport buses or cars. Walkability on the main highway is zero.",
            "The lake can sometimes smell during summer, and mosquitoes are definitely a problem if your balcony faces the water."
        ]
    },
    {
        "locality": "Sarjapur Road",
        "posts": [
            "Sarjapur road is basically one long traffic jam. Development outpaced infrastructure. Dust and construction noise is everywhere.",
            "Huge expat and tech crowd. Lots of nice international schools and massive gated communities. Inside the gates, it's paradise. Outside, it's a mess.",
            "Water is the biggest issue. Almost 100% tanker dependency in the newer apartments. Factor in high maintenance costs for water.",
            "No metro. Walking is dangerous because footpaths don't exist. You absolutely need a car or a two-wheeler to survive here."
        ]
    },
    {
        "locality": "Banashankari",
        "posts": [
            "BSK is huge. Stage 2 and 3 are very peaceful, green, and similar to Jayanagar. Very traditional, family-focused culture.",
            "Green line metro serves the area perfectly. Banashankari TTMC makes bus connectivity amazing to any part of the city.",
            "Very safe, low crime rate, strong community presence. Great local markets. No real nightlife or startup culture here.",
            "Infrastructure is stable. Good Cauvery water supply and less power cuts compared to newer areas like Sarjapur."
        ]
    },
    {
        "locality": "Kammanahalli",
        "posts": [
            "Often called 'Kammanhattan'. Extremely diverse, lots of expats, students, and great global cuisine. The vibe is very energetic and food-centric.",
            "Traffic on the main road is very slow. No direct metro, you have to go to Baiyappanahalli. Autos are plentiful though.",
            "Generally safe, but the main roads get very crowded. Some noise issues if you live right off the main commercial strip.",
            "Friendly neighborhood, a mix of old Bangaloreans and international students. Quite liberal and open culture."
        ]
    },
    {
        "locality": "Yelahanka",
        "posts": [
            "Yelahanka New Town is beautifully planned with wide roads and huge parks. Very peaceful and far from the city chaos.",
            "Great connectivity to the airport. No metro yet, so commuting to south Bangalore takes over 2 hours in peak traffic. You need a car.",
            "Extremely safe, quiet, and family-oriented. Lots of defense personnel and retired folks. Very clean air compared to ORR.",
            "If you work in central or south Bangalore, do not live here. The commute will destroy your soul. Great for remote workers or airport staff."
        ]
    }
]

def run():
    print("Injecting expanded synthetic Reddit data...")
    documents = []
    
    for item in MOCK_REDDIT_DATA:
        locality = item["locality"]
        for post in item["posts"]:
            documents.append({
                "url": f"https://www.reddit.com/r/bangalore/comments/mock_{locality.lower().replace(' ', '_')}/",
                "locality": locality,
                "text": post,
                "source_type": "community_forum"
            })
            
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from rag_ingestion.chunker import process_documents
    
    chunks = process_documents(documents)
    print(f"Injected and chunked {len(chunks)} Reddit documents covering {len(MOCK_REDDIT_DATA)} localities.")
    
    with open("rag_ingestion/reddit_chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

if __name__ == "__main__":
    run()
