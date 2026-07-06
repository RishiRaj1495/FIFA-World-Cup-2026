"""
Static reference data describing the venue.

In a production deployment this would be backed by a venue-management
database or a stadium's IoT/ticketing platform. For this submission it is
an in-memory dataset so the whole system is runnable and testable with
zero external dependencies beyond the Anthropic API key.
"""

GATES = [
    {
        "gate_id": "A",
        "name": "Gate A - North Plaza",
        "wheelchair_accessible": True,
        "amenities": ["accessible restrooms", "guest services desk", "elevator to upper tier"],
    },
    {
        "gate_id": "B",
        "name": "Gate B - East Concourse",
        "wheelchair_accessible": True,
        "amenities": ["family restroom", "first aid station", "ATM"],
    },
    {
        "gate_id": "C",
        "name": "Gate C - South Plaza",
        "wheelchair_accessible": False,
        "amenities": ["food court", "team store", "media entrance"],
    },
    {
        "gate_id": "D",
        "name": "Gate D - West Concourse",
        "wheelchair_accessible": True,
        "amenities": ["sensory room", "quiet zone", "accessible parking shuttle stop"],
    },
]

AMENITIES = {
    "restrooms": "Available near every gate; accessible restrooms at Gates A, B, and D.",
    "food": "Food courts at Gate C and mobile carts on the main concourse ring.",
    "medical": "First aid stations at Gate B and behind Section 114.",
    "lost_and_found": "Guest Services desk at Gate A.",
    "transport": "Shuttle buses depart from the West Concourse (Gate D) every 10 minutes on matchday.",
    "sensory_room": "Quiet, low-stimulation room near Gate D for neurodivergent fans and anyone needing a break.",
    "prayer_room": "Multi-faith prayer room on the main concourse near Gate B.",
}

ACCESSIBILITY_FACILITIES = {
    "wheelchair": [
        "Step-free access at Gates A, B, and D",
        "Accessible seating platforms in Sections 101, 118, 204",
        "Accessible restrooms at Gates A, B, D",
        "Golf-cart shuttle from parking to nearest accessible gate on request",
    ],
    "low_vision": [
        "Tactile wayfinding strips from Gate A to Guest Services",
        "High-contrast signage on the main concourse",
        "Audio-described commentary available via the stadium app on request",
    ],
    "hearing_impaired": [
        "Induction hearing loops at Guest Services and all ticket windows",
        "Visual paging displays near every gate",
        "Sign language interpreters available on request at Guest Services (30 min notice)",
    ],
    "cognitive_support": [
        "Sensory/quiet room near Gate D",
        "Social story guide for first-time visitors available via the stadium app",
        "Reduced-noise viewing area in Section 220",
    ],
    "none": [
        "Standard general-admission facilities at every gate",
    ],
}

MATCH_CONTEXT = {
    "tournament": "FIFA World Cup 2026",
    "venue": "Example Host Stadium",
    "kickoff_local_time": "19:00",
    "gates_open_before_kickoff_minutes": 120,
}
