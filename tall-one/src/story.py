"""THE TALL ONE — a dating-profile trailer. 1080x1920, 30 fps, about a minute.

Two voices: N, the trailer narrator (deep, sure of himself); K, a deadpan friend who keeps
correcting him. Facts from the man himself: 1.90 m, 30, runs a lot, gym, mountain bike.
Everything else is a joke about the photos.

A beat is one shot. Its length comes from its lines (voice.py measures them), plus `hold`.
Shot kinds: card (black, trailer type), photo, flex (the cutout on a backdrop), title, rating.
"""

BEATS = [
    dict(kind='card', text=['IN A WORLD'], hold=0.4,
         lines=[('N', 'In a world of endless swiping...')]),
    dict(kind='card', text=['OF BLURRY PHOTOS', 'BAD OPENERS', '& MEN HOLDING FISH'], hold=0.2,
         lines=[('N', 'of blurry photos, bad openers, and men holding fish...')]),
    dict(kind='photo', img='cistern', view=((0.31, 0.47, 1.0), (0.31, 0.45, 1.12)), tag=('THE SMILE', 'certified real'), hold=0.3,
         lines=[('N', 'one man chose to smile.'), ('K', 'In an underground cistern. Normal first photo.')], scratch=True),
    dict(kind='photo', img='mirror', view=((0.5, 0.5, 1.0), (0.5, 0.5, 1.0)), ruler=True, hold=0.4,
         lines=[('N', 'Standing one meter ninety.'), ('K', "Yes. He'll get the thing off the top shelf.")]),
    dict(kind='photo', img='mtb', view=((0.5, 0.5, 1.0), (0.47, 0.42, 1.1)), tag=('THE CLIMBER', 'mountain bike · elevation: yes'), hold=0.3,
         lines=[('N', 'He climbs mountains. On a bike. For fun.'), ('K', 'Then has one beer and calls it recovery.')]),
    dict(kind='photo', img='river', view=((0.66, 0.55, 1.0), (0.66, 0.6, 1.12)), tag=('THE RUNNER', 'kilometres this week: yes'), hold=0.3,
         lines=[('N', 'He runs. A lot.'), ('K', 'Like, a worrying amount. Nobody is chasing him.')]),
    dict(kind='photo', img='table', view=((0.5, 0.44, 2.0), (0.5, 0.43, 2.15)), tag=('THE LIFTER', 'leg day: attended'), hold=0.3,
         lines=[('N', 'He trains at the gym.'), ('K', 'And he will lean across a table to tell you about it.')]),
    dict(kind='photo', img='rooftop', view=((0.33, 0.5, 1.0), (0.31, 0.47, 1.1)), tag=('THE GAZER', 'professional'), hold=0.3,
         lines=[('N', "He has seen the world."), ('K', 'And looked at it. Thoughtfully. From the side.')]),
    dict(kind='photo', img='bridge', view=((0.36, 0.55, 1.0), (0.36, 0.52, 1.07)), tag=('AGE: 30', 'season thirty'), hold=0.3,
         lines=[('N', 'Thirty years in the making.'), ('K', "He's thirty. He's looking at a bridge.")]),
    dict(kind='flex', tag=('THE JAR OPENER', 'jars opened: all of them'), hold=0.5,
         lines=[('N', 'And this summer, every jar you could never open...'), ('N', 'has finally met its match.')]),
    dict(kind='title', hold=0.9, lead=1.5,
         lines=[('N', 'The Tall One.'), ('K', 'Swipe right. Before he goes for another run.')]),
    dict(kind='rating', hold=1.6,
         lines=[('N', 'Rated R. For running.'), ('K', 'Coming soon. To your phone.')]),
]
