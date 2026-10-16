"""WILD SINGLES — a nature documentary about one rare male. Hushed narrator, lower-thirds in Latin.

Facts: 1.90 m, 30, runs a lot, gym, mountain bike. The rest is a documentary crew trying very hard.
Kinds: title, photo (lower=(latin, line), viewfinder=True for the long-lens shots), end.
"""
VOICES = {
    'N': dict(model='ryan', speed=1.22, pitch=0.95, chest=0.25, drive=1.3, room=(0.5, 0.06)),
    'K': dict(model='kathleen', speed=1.05, whisper=True, gain=0.8, room=(0.3, 0.04)),
}

BEATS = [
    dict(kind='title', lead=0.8, hold=0.6,
         lines=[('N', 'Wild Singles. Episode one: The Tall One.')]),
    dict(kind='photo', img='river', view=((0.66, 0.62, 1.25), (0.66, 0.6, 1.0)), viewfinder=True,
         lower=('Homo sapiens altus', 'The Tall One · 1.90 m · 30 years'), hold=0.3,
         lines=[('N', 'Deep in the forest, we have found him. A rare male. Thirty years old, and one metre ninety tall.')]),
    dict(kind='photo', img='bridge', view=((0.36, 0.5, 1.0), (0.36, 0.55, 1.08)),
         lower=('Behaviour', 'gazing at something important'), hold=0.3,
         lines=[('N', 'Like all of his kind, he is mostly photographed from behind, gazing at something important.')]),
    dict(kind='photo', img='mtb', view=((0.47, 0.5, 1.0), (0.47, 0.42, 1.12)),
         lower=('Migration', 'uphill · on two wheels · voluntarily'), hold=0.3,
         lines=[('N', 'To reach the high ground, he climbs on two wheels. Then he refuels with a single, golden can.')]),
    dict(kind='photo', img='table', view=((0.5, 0.45, 2.0), (0.5, 0.43, 2.18)),
         lower=('Courtship display', 'the lean-in'), hold=0.3,
         lines=[('N', 'At feeding time, the male leans in close, and displays the arms he builds at the gym.'),
                ('N', 'It is, frankly, working.', dict(gap=0.5))]),
    dict(kind='photo', img='mirror', view=((0.5, 0.5, 1.0), (0.5, 0.48, 1.06)),
         lower=('Habitat', 'doorways · always ducking'), hold=0.3,
         lines=[('N', 'Back in his den, he checks his plumage. At one ninety, he must lower his head for most doorways.')]),
    dict(kind='photo', img='rooftop', view=((0.32, 0.5, 1.0), (0.31, 0.46, 1.1)),
         lower=('Range', 'many kilometres · every week'), hold=0.3,
         lines=[('N', 'He runs great distances, every single week.'),
                ('N', 'Our team never found out what from.', dict(gap=0.4))]),
    dict(kind='photo', img='cistern', view=((0.31, 0.5, 1.0), (0.31, 0.45, 1.15)), viewfinder=True, rare=True,
         lower=('Extremely rare footage', 'he is facing the camera'), hold=0.6,
         lines=[('N', 'And then, for the first time ever on film, he turns to the camera.'),
                ('N', 'And he smiles.', dict(gap=0.6))]),
    dict(kind='end', lead=0.6, hold=2.0,
         lines=[('N', 'If you meet one in the wild, swipe right. Slowly. Do not startle him.'),
                ('K', 'Is he single?', dict(gap=0.7)),
                ('N', 'Yes.', dict(gap=0.6, whisper=True, speed=1.4))]),
]
