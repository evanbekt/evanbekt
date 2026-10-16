"""HIM 30 — a product launch. Calm keynote voice, white stage, his photos as floating product
cards with spec callouts, and a fine-print voice at the end that reads very, very fast.

Facts: 1.90 m, 30, runs a lot, gym, mountain bike. Specs are jokes about those.
Kinds: intro, card (one photo card + headline + spec), pair (two cards), specs, end.
"""
VOICES = {
    'N': dict(model='ryan', speed=1.1, pitch=0.97, chest=0.15, drive=1.3, room=(0.9, 0.08)),
    'K': dict(model='kathleen', speed=0.62, gain=0.85, room=(0.2, 0.02)),
}

BEATS = [
    dict(kind='intro', lead=0.6, hold=0.7,
         lines=[('N', 'Introducing.'), ('N', 'Him. Thirty.', dict(gap=0.7))]),
    dict(kind='card', img='mirror', view=((0.5, 0.5, 1.0), (0.5, 0.5, 1.0)), head='Our tallest model yet.',
         spec=('1.90 m', 'reaches every top shelf'), ruler=True, hold=0.4,
         lines=[('N', 'Our tallest model yet. One metre ninety. Reaches every top shelf. No step stool required.')]),
    dict(kind='card', img='mtb', view=((0.47, 0.45, 1.05), (0.47, 0.42, 1.12)), head='All-terrain.',
         spec=('MTB mode', 'tested on real mountains'), hold=0.3,
         lines=[('N', 'Fully all-terrain. Tested on actual mountains. Runs on a single can of fuel.')]),
    dict(kind='card', img='river', view=((0.66, 0.6, 1.1), (0.66, 0.58, 1.2)), head='Endurance mode.',
         spec=('Always on', 'he runs. a lot.'), hold=0.3,
         lines=[('N', 'Endurance mode is always on. He runs. A lot.'), ('N', 'Battery life? We honestly stopped measuring.', dict(gap=0.45))]),
    dict(kind='card', img='table', view=((0.5, 0.44, 2.0), (0.5, 0.43, 2.12)), head='Pro arms.',
         spec=('Gym-trained', 'now with lean-in display'), hold=0.3,
         lines=[('N', 'Pro-grade arms, trained at the gym. Now with a lean-in display.')]),
    dict(kind='card', img='cistern', view=((0.31, 0.47, 1.0), (0.31, 0.45, 1.1)), head='The smile. Built in.',
         spec=('Works underground', 'no filter required'), hold=0.3,
         lines=[('N', 'And the smile. Built in. Works even underground.')]),
    dict(kind='pair', imgs=('rooftop', 'bridge'), head='Panorama mode.',
         spec=('Included', 'looks at views. thoughtfully.'), hold=0.3,
         lines=[('N', 'Also ships with panorama mode: looking thoughtfully at views. From the side. Or from behind.')]),
    dict(kind='specs', hold=0.4,
         lines=[('N', 'Him thirty. The full spec sheet.'), ('N', 'Available now.', dict(gap=0.5))]),
    dict(kind='end', lead=0.5, hold=1.6,
         lines=[('N', 'Swipe right to pre-order.'),
                ('K', 'Him thirty is not a product and cannot be pre-ordered. Height is not adjustable. May leave for a run without notice. Jars sold separately.', dict(gap=0.5)),
                ('N', 'Swipe right.', dict(gap=0.4))]),
]
