"""TRANSFER NEWS — a football transfer broadcast. A hyped commentator, a calm pundit, a live
ticker, stat bars, a gold player card and HERE WE GO.

Facts: 1.90 m, 30, runs a lot, gym, mountain bike. The ratings are jokes about those.
Kinds: breaking, photo (stat=(label, value, out_of)), card (the player card), end.
"""
VOICES = {
    'N': dict(model='ryan', speed=0.92, pitch=0.98, chest=0.1, drive=2.2, room=(1.6, 0.14)),
    'K': dict(model='kathleen', speed=1.0, gain=0.9, room=(0.5, 0.08)),
}

BEATS = [
    dict(kind='breaking', lead=0.5, hold=0.3,
         lines=[('N', 'Breaking news from the transfer window!')]),
    dict(kind='photo', img='cistern', view=((0.31, 0.47, 1.0), (0.31, 0.45, 1.12)), banner='FREE AGENT · AVAILABLE NOW', hold=0.3,
         lines=[('N', 'A thirty year old free agent is available, and the scouts are going absolutely mad!')]),
    dict(kind='photo', img='mirror', view=((0.5, 0.5, 1.0), (0.5, 0.48, 1.05)), stat=('HEIGHT', '1.90 m', 0.95), hold=0.3,
         lines=[('K', 'Look at the height on him. One ninety. Dominant in the air.')]),
    dict(kind='photo', img='river', view=((0.66, 0.6, 1.0), (0.66, 0.58, 1.12)), stat=('STAMINA', '99', 0.99), hold=0.3,
         lines=[('N', 'Stamina? Ninety nine! He simply does not stop running!'), ('K', 'We checked. He is still running.')]),
    dict(kind='photo', img='mtb', view=((0.47, 0.5, 1.0), (0.47, 0.42, 1.1)), stat=('CLIMBING', '94', 0.94), hold=0.3,
         lines=[('N', 'He climbs mountains on a bike, for fun! Recovery drink already in hand!')]),
    dict(kind='photo', img='table', view=((0.5, 0.44, 2.0), (0.5, 0.43, 2.15)), stat=('STRENGTH', '93', 0.93), hold=0.3,
         lines=[('K', 'In the gym every week. Strong in the tackle.'), ('N', 'And what a lean in technique!')]),
    dict(kind='photo', img='rooftop', view=((0.33, 0.5, 1.0), (0.31, 0.46, 1.1)), stat=('VISION', '97', 0.97), hold=0.3,
         lines=[('N', 'Vision! He sees the whole pitch, and most of the city!')]),
    dict(kind='card', lead=0.6, hold=0.5,
         lines=[('N', 'Here we go!', dict(speed=0.85)), ('K', 'Overall ninety four. Contract: open ended. Fee: one swipe.', dict(gap=0.5))]),
    dict(kind='end', lead=0.4, hold=1.6,
         lines=[('N', 'Swipe right to make an offer, before another club does!')]),
]
