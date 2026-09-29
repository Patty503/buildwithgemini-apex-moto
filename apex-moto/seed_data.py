import sys
from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-03-0447589ffaaa"

ROUTES = [
    {
        "id": "skyline-boulevard-ca35",
        "name": "Skyline Boulevard (CA-35)",
        "region": "Northern California / SF Bay Area",
        "distance_miles": 27.5,
        "twistiness_rating": 9,
        "surface_condition": "Smooth asphalt, occasional redwood debris",
        "elevation_gain_ft": 2400,
        "highlight": "Legendary ridge-top twisties through the redwoods with ocean views. Famous stop at Alice's Restaurant.",
        "recommended_bike_type": "Sport / Supermoto / Naked",
        "scenic_rating": 9,
    },
    {
        "id": "tail-of-the-dragon-us129",
        "name": "Tail of the Dragon (US-129)",
        "region": "Tennessee / North Carolina",
        "distance_miles": 11.0,
        "twistiness_rating": 10,
        "surface_condition": "Pristine banked tarmac, no intersections",
        "elevation_gain_ft": 1100,
        "highlight": "318 curves in 11 miles. The ultimate technical benchmark for motorcycle handling and apex carving.",
        "recommended_bike_type": "Sport / Track / Sport-Touring",
        "scenic_rating": 8,
    },
    {
        "id": "cherohala-skyway",
        "name": "Cherohala Skyway",
        "region": "Tennessee / North Carolina",
        "distance_miles": 43.0,
        "twistiness_rating": 8,
        "surface_condition": "Wide sweeping curves, excellent asphalt",
        "elevation_gain_ft": 5390,
        "highlight": "Sweeping mountain curves climbing over 5,000 feet into the clouds. Breathtaking overlook stops.",
        "recommended_bike_type": "Adventure / Sport-Touring / Cruiser",
        "scenic_rating": 10,
    },
    {
        "id": "mulholland-snake",
        "name": "Mulholland Highway & The Snake",
        "region": "Southern California / Malibu",
        "distance_miles": 18.2,
        "twistiness_rating": 9,
        "surface_condition": "Warm canyon pavement, tight hairpins",
        "elevation_gain_ft": 1850,
        "highlight": "Iconic Malibu canyon carver featuring tight chicanes and legendary Pacific lookout points.",
        "recommended_bike_type": "Supermoto / Naked / Sport",
        "scenic_rating": 9,
    },
    {
        "id": "beartooth-highway-us212",
        "name": "Beartooth Highway (US-212)",
        "region": "Montana / Wyoming",
        "distance_miles": 68.0,
        "twistiness_rating": 8,
        "surface_condition": "Alpine switchbacks, snow-walled in early summer",
        "elevation_gain_ft": 10947,
        "highlight": "Charles Kuralt called it 'the most beautiful drive in America'. Thrilling high-altitude switchbacks.",
        "recommended_bike_type": "Adventure / Touring",
        "scenic_rating": 10,
    }
]

def seed():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT}")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    routes_col = db.collection("routes")

    for route in ROUTES:
        doc_ref = routes_col.document(route["id"])
        doc_ref.set(route)
        print(f"✓ Seeded route: {route['name']} ({route['id']})")

    print("\nFirestore successfully seeded with motorcycle routes!")

if __name__ == "__main__":
    seed()

CREW_MEMBERS = [
    {
        "rider_id": "alex-ducati",
        "name": "Alex",
        "bike": "Ducati Hypermotard 950 SP",
        "status": "Riding",
        "current_road": "Skyline Boulevard (CA-35)",
        "current_speed_mph": 52,
        "battery_pct": 84,
        "last_ping": "2 mins ago",
        "heading": "Southbound towards Alice's Restaurant"
    },
    {
        "rider_id": "marcus-bmw",
        "name": "Marcus",
        "bike": "BMW R 1250 GS Adventure",
        "status": "Stopped",
        "current_road": "Alice's Restaurant Lookout",
        "current_speed_mph": 0,
        "battery_pct": 91,
        "last_ping": "Just now",
        "heading": "Coffee break / regroup point"
    },
    {
        "rider_id": "elena-yamaha",
        "name": "Elena",
        "bike": "Yamaha MT-09 SP",
        "status": "Riding",
        "current_road": "Highway 9 / Saratoga Gap",
        "current_speed_mph": 48,
        "battery_pct": 68,
        "last_ping": "4 mins ago",
        "heading": "Climbing up to meet the group"
    }
]

def seed_crew():
    db = firestore.Client(project=FIRESTORE_PROJECT)
    crew_col = db.collection("crew_members")
    for member in CREW_MEMBERS:
        crew_col.document(member["rider_id"]).set(member)
        print(f"✓ Seeded crew member: {member['name']} ({member['rider_id']})")

if __name__ == "__main__":
    seed_crew()
