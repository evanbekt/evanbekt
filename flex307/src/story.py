"""307: OCCUPIED. A 60 s horror-comedy short, 1080x1920, 30 fps, set in Building 3.

Night one for the new tenant of 307. At 3:07 the thing that wears your voice knocks, slides the
Stillness terms under the door and rises out of the ink. The tenant says nothing at all. He flexes.
Captions are his; he never speaks. The voice is the entity's.

Lines: (kind, at seconds, text). Kinds: c = the entity, cw = its whisper, small = the entity, deflated.
"""

TITLE = '307: OCCUPIED'
CAPTION = 'Wrong door'

LINES = [
    ('c', 4.6, 'Let me in.'),
    ('c', 8.4, "It's you."),
    ('c', 19.4, 'Silence is taken as acceptance.'),
    ('cw', 27.2, "Say nothing. And you're mine."),
    ('small', 44.6, 'Wrong door.'),
    ('small', 54.4, 'Can you teach me?'),
]

# shots: (t0, t1, kind)
SHOTS = [
    (0.0, 4.0, 'clock'),
    (4.0, 11.0, 'door'),
    (11.0, 17.0, 'face'),
    (17.0, 25.0, 'under'),
    (25.0, 34.0, 'rise'),
    (34.0, 42.0, 'flex'),
    (42.0, 50.0, 'retreat'),
    (50.0, 60.0, 'title'),
]

# his captions, TikTok style: (t0, t1, text)
CAPTIONS = [
    (1.2, 3.8, 'night one in my new apartment'),
    (11.4, 13.9, 'me, pretending to be asleep'),
    (14.0, 16.8, 'apparently this building has rules'),
    (22.6, 24.8, 'I don’t sign things before coffee'),
    (30.4, 33.6, 'ok. plan B.'),
    (46.4, 49.8, '…it apologised'),
]

FLEX_AT = 34.0          # the lamp clicks on
STAMP_AT = 36.4         # CLAUSE 7: NO.
KNOCKS = [0.5, 1.0, 1.5, 7.0, 7.45, 7.9, 53.2, 53.5]
CHAT = [  # (at, who, text) — the Building 3 group chat, during the retreat
    (42.6, 'Marta · 309', 'who moved into 307??'),
    (43.8, 'Dev · 312', 'the knocking stopped. whole building.'),
    (45.0, 'Mr. Haas · 304', 'it said sorry to me in the stairwell'),
]
