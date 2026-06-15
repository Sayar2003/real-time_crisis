# backend/app/templates.py
# Single source of truth for all text templates
# Used by both simulator.py and processor.py

BACKGROUND_TEMPLATES = [
    "Enjoying a lovely walk around {landmark} today! #local",
    "Traffic is a bit slow near {landmark} this afternoon.",
    "Having a delicious coffee and a pastry close to {landmark}.",
    "Beautiful weather at {landmark} right now! Perfect for photos.",
    "Shopping near {landmark}, it is incredibly crowded.",
    "Can't wait to check out the amazing view from {landmark}!",
    "Strolling through {landmark} on this nice day.",
    "Just passed by {landmark} on my commute back home.",
    "Met some old friends near {landmark} for a quick lunch.",
    "A lovely, quiet and peaceful evening around {landmark}."
]

CRISIS_TEMPLATES = {
    "Fire": [
        "OMG! Huge fire near {landmark}! Smoke is rising high in the sky! #Emergency",
        "Firefighters are battling a massive blaze at a building near {landmark}! Avoid the area!",
        "There is a serious building fire close to {landmark}. Multiple fire trucks on scene!",
        "Smelling strong smoke and seeing flames near {landmark}. Stay safe everyone!",
        "Building on fire near {landmark}! Fire alarms ringing and people evacuating!"
    ],
    "Flood": [
        "Serious flooding near {landmark}! Roads are completely underwater, stay inside!",
        "The water levels are rising fast around {landmark} after the heavy storm!",
        "Flooded streets close to {landmark}. Traffic is totally blocked and cars are stuck!",
        "Basements getting flooded near {landmark}. This rain is absolutely relentless.",
        "The river is overflowing near {landmark}. Avoid walking near the banks!"
    ],
    "Civic Unrest": [
        "Huge protest blocking the streets near {landmark}! Traffic is at a standstill.",
        "Police and protestors clashing close to {landmark} right now! Heavy tension.",
        "Massive demonstration near {landmark}, riot police are deployed on scene! #protest",
        "Avoid the area around {landmark}, the crowd is getting aggressive!",
        "Protestors chanting and blocking all major intersections near {landmark}."
    ],
    "Outbreak": [
        "Public health alert: several severe food poisoning cases reported near {landmark}!",
        "A sudden viral outbreak reported at a local school near {landmark}.",
        "Dozens hospitalized with high fever and infection symptoms close to {landmark}.",
        "Warning: sudden measles outbreak detected in the community around {landmark}.",
        "Many people falling sick near {landmark}. Local clinic is completely full."
    ]
}