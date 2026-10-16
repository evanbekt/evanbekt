"""DEVELOPING — a story told backwards in six Polaroids. 60 s each, 1080x1920, 30 fps.

Part 1 is the end of Mara's day; each part goes earlier and ends where the one before it began.
Mara is sure the girl who visits every evening is a stranger wearing her daughter's face.
Her Polaroids are messages to the real Elise. Part 6 shows the morning it all started.

Voices (one CC0 voice, processed per character):
  m  Mara, narrating, close      mw Mara, whispering
  e  Elise, in the room          ed Elise, through the door
  n  the nurse
Shot kinds: black, title, rewind, scene, polaroid, desk.  Times are seconds.
"""

SERIES = 'DEVELOPING'

PARTS = {
    1: dict(
        title='SHE KNOCKS', clock='6:40 PM', caption='Her eyes',
        shots=[
            dict(t0=0, t1=4, kind='black', knocks=[0.6, 1.1, 1.6]),
            dict(t0=4, t1=14, kind='desk', photos=[
                ('girl_door', 'SHE\'S WEARING YOUR FACE', 'mara', -250, -420, -7),
                ('child_swing', 'MY ELISE. 7. COME HOME', 'mara', 230, -300, 5),
                ('nurse', 'THEY LET HER IN', 'mara', -210, 230, 4),
                ('elise_smile', 'THIS IS ELISE. SHE IS YOUR DAUGHTER.', 'elise', 250, 360, -6, 'NOT YOU'),
            ], pan=[(0, -420, 1.6), (0, 420, 1.6)]),
            dict(t0=14, t1=24, kind='polaroid', photo='girl_door', note='SHE\'S WEARING YOUR FACE', hand='mara', develop=None, rot=-4),
            dict(t0=24, t1=36, kind='scene', scene='door_in', zoom=(1.05, 1.18), feet=26.5, knocks=[27.0, 27.5, 28.0]),
            dict(t0=36, t1=45, kind='scene', scene='door_in', zoom=(1.25, 1.45), viewfinder=True, ajar=(42.5, 1.0)),
            dict(t0=45, t1=56, kind='polaroid', photo='girl_face', note='SHE HAS MY EYES', hand='mara', develop=(45.8, 52.0), write=52.5, rot=3, eject=45.0),
            dict(t0=56, t1=60, kind='title'),
        ],
        flashes=[45.0],
        lines=[
            ('ed', 1.7, 'Mom? It\'s me. Open the door.'),
            ('m', 5.0, 'Every evening, she comes back.'),
            ('m', 9.5, 'I keep her pictures. For when Elise comes home.'),
            ('m', 15.0, 'This girl has been here all day.'),
            ('m', 19.0, 'She\'s wearing my daughter\'s face.'),
            ('ed', 28.8, 'Mom, please. You took my photo off the wall again.'),
            ('mw', 33.0, 'My daughter is seven years old.'),
            ('mw', 37.5, 'If I take her picture, I\'ll remember her face.'),
            ('m', 53.0, 'She has my eyes.'),
        ],
    ),
    2: dict(
        title='NOT MY HANDWRITING', clock='5:10 PM', caption='Not mine',
        shots=[
            dict(t0=0, t1=2, kind='rewind', to_clock='5:10 PM', from_clock='6:40 PM'),
            dict(t0=2, t1=12, kind='scene', scene='radiator', zoom=(1.0, 1.2), pull=(6.0, 9.0)),
            dict(t0=12, t1=24, kind='polaroid', photo='elise_smile', note='THIS IS ELISE. SHE IS YOUR DAUGHTER.', hand='elise', develop=None, rot=-3),
            dict(t0=24, t1=34, kind='polaroid', photo='elise_smile', note='THIS IS ELISE. SHE IS YOUR DAUGHTER.', hand='elise', develop=None, rot=-3,
                 scrawl='NOT YOU', scrawl_t=29.0),
            dict(t0=34, t1=45, kind='scene', scene='nurse_door', zoom=(1.0, 1.1)),
            dict(t0=45, t1=55, kind='polaroid', photo='nurse', note='THEY LET HER IN', hand='mara', develop=(45.8, 50.5), write=50.8, rot=4, eject=45.0),
            dict(t0=55, t1=60, kind='title'),
        ],
        flashes=[45.0],
        lines=[
            ('m', 2.6, 'I hide my photos behind the radiator.'),
            ('m', 6.8, 'Someone had already hidden one there.'),
            ('m', 13.0, 'This is Elise. She is your daughter.'),
            ('m', 18.0, 'Elise is seven. This girl is grown.'),
            ('m', 24.5, 'And that is not my handwriting.'),
            ('n', 35.0, 'Mara? Dinner\'s at six. Your visitor is coming back at half past.'),
            ('m', 40.4, 'What visitor?'),
            ('n', 42.0, 'Your daughter, love.'),
            ('mw', 51.5, 'They let her in. Every time.'),
        ],
    ),
    3: dict(
        title='THE GIRL', clock='3:30 PM', caption='Who\'s she',
        shots=[
            dict(t0=0, t1=2, kind='rewind', to_clock='3:30 PM', from_clock='5:10 PM'),
            dict(t0=2, t1=16, kind='scene', scene='corridor_glass', zoom=(1.0, 1.25), wave=10.5),
            dict(t0=16, t1=27, kind='polaroid', photo='girl_glass', note='WHO IS SHE?', hand='mara', develop=(16.8, 22.0), write=22.4, rot=-5, eject=16.0),
            dict(t0=27, t1=38, kind='scene', scene='nurse_door', zoom=(1.08, 1.0)),
            dict(t0=38, t1=51, kind='polaroid', photo='girl_door', note='SHE\'S WEARING YOUR FACE', hand='mara', develop=None, write=41.0, rot=-4),
            dict(t0=51, t1=60, kind='title'),
        ],
        flashes=[16.0],
        lines=[
            ('m', 2.5, 'There\'s a girl in the corridor.'),
            ('m', 6.0, 'She keeps looking at my door.'),
            ('m', 11.5, 'She waved. Like she knows me.'),
            ('m', 22.8, 'I took her picture. For Elise. So she\'d know.'),
            ('n', 28.0, 'That\'s your visitor, Mara. Same as yesterday.'),
            ('m', 32.5, 'I don\'t have visitors.'),
            ('m', 38.8, 'She has Elise\'s face.'),
            ('mw', 42.5, 'Where did she get it?'),
        ],
    ),
    4: dict(
        title='MISSING', clock='1:15 PM', caption='Missing',
        shots=[
            dict(t0=0, t1=2, kind='rewind', to_clock='1:15 PM', from_clock='3:30 PM'),
            dict(t0=2, t1=14, kind='scene', scene='wallet', zoom=(1.0, 1.3)),
            dict(t0=14, t1=27, kind='polaroid', photo='child_swing', note='MY ELISE. 7. COME HOME', hand='mara', develop=None, write=21.5, rot=2, old=True),
            dict(t0=27, t1=38, kind='scene', scene='room_day', zoom=(1.0, 1.12)),
            dict(t0=38, t1=52, kind='scene', scene='camera_bed', zoom=(1.0, 1.35)),
            dict(t0=52, t1=60, kind='title'),
        ],
        flashes=[],
        lines=[
            ('m', 2.6, 'I found her in my wallet.'),
            ('m', 6.4, 'My daughter. Elise.'),
            ('m', 14.8, 'She should be home from school by now.'),
            ('m', 22.0, 'I wrote on her picture, so they\'d look for her.'),
            ('m', 28.0, 'Nobody here will tell me where she is.'),
            ('m', 32.5, 'They just smile and say, same as yesterday.'),
            ('m', 39.0, 'Someone left me a camera.'),
            ('m', 43.5, 'With a note signed E.'),
        ],
    ),
    5: dict(
        title='WHO IS SHE?', clock='10:40 AM', caption='Who\'s that',
        shots=[
            dict(t0=0, t1=2, kind='rewind', to_clock='10:40 AM', from_clock='1:15 PM'),
            dict(t0=2, t1=13, kind='scene', scene='room_day', zoom=(1.2, 1.0)),
            dict(t0=13, t1=19, kind='scene', scene='mirror', zoom=(1.0, 1.15)),
            dict(t0=19, t1=29, kind='polaroid', photo='old_woman', note='WHO IS THIS?', hand='mara', develop=(19.8, 24.5), write=25.0, rot=-3, eject=19.0),
            dict(t0=29, t1=36, kind='scene', scene='door_out', zoom=(1.0, 1.15)),
            dict(t0=36, t1=47, kind='polaroid', photo='girl_leaving', note='WHO IS SHE?', hand='mara', develop=(36.8, 41.5), write=42.0, rot=4, eject=36.0),
            dict(t0=47, t1=54, kind='scene', scene='camera_bed', zoom=(1.3, 1.45)),
            dict(t0=54, t1=60, kind='title'),
        ],
        flashes=[19.0, 36.0],
        lines=[
            ('m', 2.6, 'I woke up and the room was wrong.'),
            ('m', 7.0, 'The curtains are wrong. My hands are wrong.'),
            ('m', 13.4, 'There was an old woman in my mirror.'),
            ('ed', 29.6, 'Bye, Mom. Same time tomorrow.'),
            ('m', 32.6, 'Who calls me Mom?'),
            ('m', 47.6, 'And whose camera is this?'),
        ],
    ),
    6: dict(
        title='THIS IS ELISE', clock='9:00 AM', caption='Start here',
        shots=[
            dict(t0=0, t1=2, kind='rewind', to_clock='9:00 AM', from_clock='10:40 AM'),
            dict(t0=2, t1=16, kind='scene', scene='elise_visit', zoom=(1.0, 1.15)),
            dict(t0=16, t1=29, kind='polaroid', photo='elise_smile', note='THIS IS ELISE. SHE IS YOUR DAUGHTER.', hand='elise', develop=(16.8, 21.5), write=22.0, rot=-3, eject=16.0),
            dict(t0=29, t1=40, kind='scene', scene='radiator', zoom=(1.15, 1.3), slip=(31.5, 34.5)),
            dict(t0=40, t1=51, kind='scene', scene='door_out', zoom=(1.0, 1.1)),
            dict(t0=51, t1=60, kind='title', loop=True),
        ],
        flashes=[16.0],
        lines=[
            ('e', 2.6, 'This is a camera, Mom. You press here.'),
            ('e', 7.0, 'Every time you meet someone, take their picture.'),
            ('e', 11.4, 'And write their name on it.'),
            ('e', 22.6, 'There. Now you\'ll know me tomorrow.'),
            ('m', 29.6, 'You have a kind face.'),
            ('e', 32.6, 'You always say that.'),
            ('ed', 40.6, 'Bye, Mom. Same time tomorrow.'),
            ('m', 45.0, 'Who was that?'),
        ],
    ),
}
