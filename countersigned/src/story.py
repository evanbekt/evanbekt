"""COUNTERSIGNED — six clauses, six signers, one counterparty. Building 3. 60 s each, 1080x1920, 30 fps.

The counterparty is never drawn: it is ink. Each part: who signed, what they wanted, the clause, the price.
Voices (one CC0 voice, processed): s = the signer (per-part character), c = the counterparty, cw = its whisper.
Every part has the same skeleton (times in seconds):
  0-4 card   4-20 the want (ink blooms)   20-38 the clause (typed)   38-46 the signature, the fold
  46-56 the price (the ink opens its eyes)   56-60 signed
"""

SERIES = 'COUNTERSIGNED'

PARTS = {
    1: dict(name='THE HOLDER', apt='307', signer='holder', caption='Signed', sig='You', sig_font='PermanentMarker-Regular.ttf',
            want='moth', price='hourglass',
            clause=['CLAUSE 1 — THE STILLNESS', 'The Holder may stop the world,', 'and everything in it, except themself.',
                    'Consideration: one (1) of the Holder,', 'nightly.', 'No refunds of time.'],
            red=['stop the world', 'one (1) of the Holder', 'No refunds of time.'],
            lines=[('s', 5.0, 'I wanted the world to stop. Just for a minute.'), ('s', 11.0, 'So I could breathe.'),
                   ('c', 21.0, 'Clause one.'), ('c', 23.6, 'The holder may stop the world, and everything in it.'),
                   ('c', 29.6, 'In exchange,'), ('c', 32.0, 'each night, the holder gives us one more of themselves.'),
                   ('cw', 49.5, 'We have ninety-nine of you now.')]),
    2: dict(name='MARTA', apt='309', signer='marta', caption='Her voice', sig='Marta K.', sig_font='Caveat.ttf',
            want='door', price='mouth',
            clause=['CLAUSE 2 — COMPANY', 'Someone will always be at the', 'Signer’s door.',
                    'The Counterparty will knock in a', 'voice the Signer trusts.', 'Consideration: the Signer’s voice.'],
            red=['always be at', 'knock', 'the Signer’s voice.'],
            lines=[('s', 5.0, 'I just didn\'t want to be alone at night.'), ('s', 10.5, 'I wanted someone to knock. Anyone.'),
                   ('c', 21.0, 'Clause two.'), ('c', 23.6, 'Someone will always be at your door.'),
                   ('c', 28.6, 'We will knock in a voice you trust.'), ('c', 34.0, 'Yours.'),
                   ('cw', 49.5, 'Open up, Marta. It\'s you.')]),
    3: dict(name='MR. HAAS', apt='304', signer='haas', caption='Fine print', sig='H. Haas', sig_font='RockSalt-Regular.ttf',
            want='book', price='eye',
            clause=['CLAUSE 3 — FULL DISCLOSURE', 'The Signer may read every clause', 'of every contract in Building 3.',
                    'Consideration: the Signer may', 'not look away.', 'Not even to sleep.'],
            red=['every clause', 'not look away.', 'Not even to sleep.'],
            lines=[('s', 5.0, 'I asked to read the whole contract first.'), ('s', 10.5, 'Every word. Before I signed anything.'),
                   ('c', 21.0, 'Clause three.'), ('c', 23.6, 'He may read every clause, of every contract, in this building.'),
                   ('c', 30.8, 'In exchange, he may never look away.'),
                   ('cw', 49.5, 'That is why he tells you not to answer.')]),
    4: dict(name='LILY', apt='311', signer='lily', caption='Mom\'s asleep', sig='lily', sig_font='Caveat.ttf',
            want='bed', price='mother',
            clause=['CLAUSE 4 — REST', 'The Signer’s mother will sleep,', 'and not wake.',
                    'A substitute will knock in her place,', 'nightly, at 3:07 AM.', 'Consideration: see Clause 6.'],
            red=['and not wake.', 'A substitute', 'see Clause 6.'],
            lines=[('s', 5.0, 'Mommy cries every night.'), ('s', 9.6, 'I wished she would just sleep.'),
                   ('c', 21.0, 'Clause four.'), ('c', 23.6, 'Her mother will sleep, and never wake.'),
                   ('c', 29.0, 'Someone will knock in her place.'), ('c', 33.6, 'Every night, at three oh seven.'),
                   ('cw', 49.5, 'Mommy? Can I come in?')]),
    5: dict(name='MARA', apt='307', signer='mara', caption='Forget me', sig='Mara H.', sig_font='RockSalt-Regular.ttf',
            want='heart', price='face',
            clause=['CLAUSE 5 — RELIEF', 'The Signer will not remember', 'the loss. Nor any day after it.',
                    'Consideration: every new memory.', '', 'Witness: E. (age 7)'],
            red=['will not remember', 'every new memory.', 'Witness: E. (age 7)'],
            lines=[('s', 5.0, 'My husband died on a Tuesday.'), ('s', 9.6, 'I wanted to stop remembering it.'),
                   ('c', 21.0, 'Clause five.'), ('c', 23.6, 'She will not remember.'),
                   ('c', 27.6, 'Not that Tuesday. Not any day after it.'), ('c', 33.4, 'Not even her daughter\'s face.'),
                   ('cw', 49.5, 'She has your eyes, Mara.')]),
    6: dict(name='YOU', apt='—', signer=None, caption='You signed', sig='', sig_font='PermanentMarker-Regular.ttf',
            want='hand', price='eyes',
            clause=['CLAUSE 6 — THE VIEWER', 'Anyone who reads this far', 'has read the terms.',
                    'Silence is taken as acceptance.', 'Effective: 3:07 AM, tonight.', 'Signature: ____________'],
            red=['has read the terms.', 'Silence is taken as acceptance.', '3:07 AM, tonight.'],
            lines=[('c', 5.0, 'There is one more clause.'), ('c', 10.0, 'It does not have a name on it yet.'),
                   ('c', 21.0, 'Clause six.'), ('c', 23.6, 'Anyone who watches to the end'), ('c', 27.8, 'has read the terms.'),
                   ('c', 31.4, 'And silence'), ('c', 33.6, 'is taken as acceptance.'),
                   ('cw', 49.5, 'See you at three oh seven.')]),
}
