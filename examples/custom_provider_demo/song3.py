# "Late Night at the Blue Note"
# Jazz in C major / A minor — ii-V-I-IV swing feel
# BPM: 138  |  Structure: intro → A-A-B-A head → repeat
#
# Note map (relevant):
#   z=C3 x=D3 c=E3 v=F3 b=G3 n=A3 m=B3(Bb3 w/ b)
#   a=C4 s=D4 d=E4 f=F4 g=G4 h=A4 j=B4(Bb4 w/ b)
#   q=C5 w=D5 e=E5 r=F5 t=G5 y=A5 u=B5
#
# Jazz chord voicings used:
#   Dm7  = [safhq]  (D4 F4 A4 C5)     — ii
#   G7   = [gjwr]   (G4 B4 D5 F5)     — V7
#   Cmaj7= [adgj]   (C4 E4 G4 B4)     — Imaj7
#   Fmaj7= [fahd]   (F4 A4 C4... → [fahd] F A C E in 4th oct)
#   Am7  = [ahsd]   (A4 C4 E4... → hmm use [hads])
#
# Valid voice keys: piano, electric_piano, banjo, bandoneon, bass,
#   electric_bass, synth_bass, clarinet, marimba, drum_kit, oboe,
#   recorder, tenor_sax, square_lead, synth_strings, trumpet, tuba

song = {

    # ── TENOR SAX ── main melody / head
    # Plays the "head" — a swinging 16-bar AABA form
    # A section: Dm7 → G7 → Cmaj7 → Fmaj7  (2 bars each)
    # B section (bridge): Am → D7 → Gm → G7  (2 bars each)
    # 'tenor_sax': (
    #     '^1.2 @138 '

    #     # 4-bar intro: sax riff establishing the vibe
    #     '!0.8 -/2 w/4 e/4 | r/2 e/4 w/4 q/2 -/2 | '
    #     '!0.7 -/2 t/4 y/4 | t/2 e/4 w/4 w2 | '

    #     # HEAD — A section 1  (Dm7 - G7 - Cmaj7 - Fmaj7)
    #     # bar 1-2: Dm7
    #     '!0.9 w/4 e/4 r/4 e/4 w/2 s/2 | '
    #     '!0.8 -/4 e/4 w/4 q/4 -/2 w/4 e/4 | '
    #     # bar 3-4: G7
    #     '!0.9 t/4 r/4 e/4 r/4 t/2 -/4 t/4 | '
    #     '!0.8 y/2 t/4 r/4 e/2 -/2 | '
    #     # bar 5-6: Cmaj7
    #     '!0.9 e/4 w/4 q/4 w/4 e/2 q/4 w/4 | '
    #     '!0.8 e/2 w/4 q/4 -/2 e/4 r/4 | '
    #     # bar 7-8: Fmaj7
    #     '!0.9 r/2 e/4 w/4 q/4 w/4 e/4 w/4 | '
    #     '!0.8 w2 -/2 w/4 e/4 | '

    #     # HEAD — A section 2  (same changes, varied melody)
    #     '!0.9 r/4 e/4 w/4 e/4 r/2 e/2 | '
    #     '!0.8 w/4 e/4 r/4 t/4 -/2 e/4 w/4 | '
    #     '!0.9 t/4 y/4 t/4 r/4 e/2 -/4 t/4 | '
    #     '!0.8 r/2 t/4 y/4 t/2 -/2 | '
    #     '!0.9 q/4 w/4 e/4 w/4 q/2 -/4 e/4 | '
    #     '!0.8 w/2 e/4 w/4 q/2 w/4 e/4 | '
    #     '!0.9 r/2 t/4 r/4 e/4 w/4 q/4 w/4 | '
    #     '!0.85 e2 -/2 t/4 y/4 | '

    #     # HEAD — B section (bridge)  Am7 - D7 - Gm7 - G7
    #     '!0.9 y/4 t/4 r/4 t/4 y/2 t/4 r/4 | '
    #     '!0.8 t/2 y/4 t/4 r/2 -/2 | '
    #     '!0.9 w/4 e/4 r/4 e/4 w/2 e/4 w/4 | '
    #     '!0.8 q/2 w/4 e/4 -/2 e/4 r/4 | '
    #     '!0.9 t/4 r/4 e/4 w/4 q/4 w/4 e/4 w/4 | '
    #     '!0.8 e/2 w/4 q/4 -/2 w/4 e/4 | '
    #     '!0.9 r/4 e/4 w/4 e/4 r/4 e/4 w/4 q/4 | '
    #     '!0.85 w2 -2 | '

    #     # HEAD — A section 3 (final, with tag ending)
    #     '!0.9 w/4 e/4 r/4 e/4 w/4 q/4 w/4 e/4 | '
    #     '!0.8 r/2 e/4 w/4 q/2 -/2 | '
    #     '!0.9 t/4 y/4 t/4 r/4 e/4 r/4 t/4 y/4 | '
    #     '!0.8 t2 -/2 r/4 t/4 | '
    #     '!0.9 y/4 t/4 r/4 t/4 y/2 t/4 r/4 | '
    #     '!0.8 t/2 e/4 w/4 q/2 -/2 | '
    #     '!0.9 r/2 e/4 w/4 q/4 w/4 e/4 r/4 | '
    #     '!0.85 e4'
    # ),

    # ── TRUMPET ── counter-melody & response phrases
    # Stays quiet during sax phrases, answers back in the gaps
    'trumpet': (
        '^0.9 @138 '

        # silent intro
        '-8 | '

        # A1: trumpet harmony a 3rd above sax, softer
        '!0.6 -/2 q/4 w/4 | e/2 w/4 q/4 -2 | '
        '!0.6 -/2 y/4 t/4 | y/2 t/4 r/4 -2 | '
        '!0.6 -/2 t/4 y/4 | t/2 r/4 e/4 -2 | '
        '!0.6 -/2 y/4 t/4 | y2 -/2 t/4 y/4 | '

        # A2: more assertive, punchy stabs
        '!0.75 -2 q/4 w/4 e/4 w/4 | '
        '!0.7 q/2 -/2 -/2 e/4 r/4 | '
        '!0.75 t/4 y/4 -/2 t/4 r/4 -/2 | '
        '!0.7 e/2 -2 e/4 r/4 | '
        '!0.75 t/4 y/4 t/4 r/4 -2 | '
        '!0.7 q/2 -2 w/4 e/4 | '
        '!0.75 r/4 t/4 -/2 r/4 e/4 -/2 | '
        '!0.7 w2 -2 | '

        # B: bridge trumpet takes a bolder line
        '!0.8 y/4 t/4 y/4 t/4 y/2 -/2 | '
        '!0.75 -/2 r/4 t/4 y/2 t/4 r/4 | '
        '!0.8 e/4 r/4 t/4 r/4 e/2 -/2 | '
        '!0.75 -/2 t/4 y/4 t/2 -/2 | '
        '!0.8 y/4 t/4 r/4 e/4 w/4 e/4 r/4 t/4 | '
        '!0.75 y/2 t/4 r/4 e/2 -/2 | '
        '!0.8 r/4 e/4 w/4 e/4 r/2 e/4 w/4 | '
        '!0.75 e2 -2 | '

        # A3: final harmonies, both voices together
        '!0.7 -/2 e/4 r/4 | t/2 r/4 e/4 -2 | '
        '!0.7 -/2 y/4 t/4 | y/2 t/4 -/4 r/4 -/4 t/4 | '
        '!0.7 y/4 t/4 r/4 t/4 -2 | '
        '!0.7 -/2 t/4 y/4 t/2 -/2 | '
        '!0.7 y/4 t/4 r/4 e/4 w/4 e/4 r/4 t/4 | '
        '!0.75 r4'
    ),

    # ── PIANO ── jazz comping — syncopated chord stabs
    # Plays 7th chord voicings, lays back slightly
    # Dm7=[safhq]→ use [sfh]  G7=[gjw]  Cmaj7=[adgj]  Fmaj7=[fhad]
    'piano': (
        '^0.85 @138 '

        # intro: sparse comp
        '!0.6 -3 [sfh]/2 | -3 [gjw]/2 | -3 [adgj]/2 | -3 [fhd]/2 | '

        # A section comping pattern — syncopated stabs on beat 2+ and 4+
        # Each 2-bar block = one chord
        # Dm7 x2 bars
        '(!0.65 -/2 [sfh]/2 -/2 [sfh]/4 -/4 | -/2 [sfh]/2 -/4 [sfh]/4 -/2)*2 | '
        # G7 x2 bars
        '(!0.65 -/2 [gjw]/2 -/2 [gjw]/4 -/4 | -/2 [gjw]/2 -/4 [gjw]/4 -/2)*2 | '
        # Cmaj7 x2 bars
        '(!0.65 -/2 [adgj]/2 -/2 [adgj]/4 -/4 | -/2 [adgj]/2 -/4 [adgj]/4 -/2)*2 | '
        # Fmaj7 x2 bars
        '(!0.65 -/2 [fhd]/2 -/2 [fhd]/4 -/4 | -/2 [fhd]/2 -/4 [fhd]/4 -/2)*2 | '

        # A2: same changes
        '(!0.7 -/2 [sfh]/2 -/2 [sfh]/4 -/4 | -/2 [sfh]/2 -/4 [sfh]/4 -/2)*2 | '
        '(!0.7 -/2 [gjw]/2 -/2 [gjw]/4 -/4 | -/2 [gjw]/2 -/4 [gjw]/4 -/2)*2 | '
        '(!0.7 -/2 [adgj]/2 -/2 [adgj]/4 -/4 | -/2 [adgj]/2 -/4 [adgj]/4 -/2)*2 | '
        '(!0.7 -/2 [fhd]/2 -/2 [fhd]/4 -/4 | -/2 [fhd]/2 -/4 [fhd]/4 -/2)*2 | '

        # B: bridge — Am7, D7, Gm7, G7
        # Am7=[ahd]  D7=[swfh]→[sfh] offset  Gm7=[gaj]→[gjw]... approx
        '(!0.7 -/2 [had]/2 -/2 [had]/4 -/4 | -/2 [had]/2 -/4 [had]/4 -/2)*2 | '
        '(!0.7 -/2 [sfh]/2 -/2 [sfh]/4 -/4 | -/2 [sfh]/2 -/4 [sfh]/4 -/2)*2 | '
        '(!0.7 -/2 [gjw]/2 -/2 [gjw]/4 -/4 | -/2 [gjw]/2 -/4 [gjw]/4 -/2)*2 | '
        '(!0.7 -/2 [gjw]/2 -/2 [gjw]/4 -/4 | -/2 [gjw]/2 -/4 [gjw]/4 -/2)*2 | '

        # A3: final — build intensity with fuller voicings
        '(!0.8 -/2 [sfh]/2 -/2 [sfhq]/4 -/4 | -/2 [sfh]/2 -/4 [sfhq]/4 -/2)*2 | '
        '(!0.8 -/2 [gjw]/2 -/2 [gjwr]/4 -/4 | -/2 [gjw]/2 -/4 [gjwr]/4 -/2)*2 | '
        '(!0.8 -/2 [adgj]/2 -/2 [adgj]/4 -/4 | -/2 [adgj]/2 -/4 [adgj]/4 -/2)*2 | '
        '!0.8 -/2 [fhd]/2 -/2 [fhd]/4 -/4 | [fhd]4'
    ),

    # ── ELECTRIC BASS ── walking bass line
    # Classic jazz walk: root on 1, approach tones on 2, 3, 4
    # C3=z  D3=x  E3=c  F3=v  G3=b  A3=n  Bb3=mb  B3=m
    # C4=a  D4=s  E4=d  F4=f  G4=g
    'electric_bass': (
        '^1.4 @138 '

        # intro walk
        '!0.8 z/4 x/4 a/4 b/4 | n/4 b/4 n/4 z/4 | '
        'a/4 b/4 z/4 a/4 | b/4 z/4 n/4 b/4 | '

        # A1 walking — Dm7: D walk  /  G7: G walk  /  Cmaj7: C walk  /  Fmaj7: F walk
        # Dm7 (2 bars): D E F# G (approach chromatic)
        '!0.8 x/4 c/4 v/4 b/4 | n/4 b/4 x/4 c/4 | '
        # G7 (2 bars): G A B C
        'b/4 n/4 m/4 z/4 | a/4 z/4 b/4 n/4 | '
        # Cmaj7 (2 bars): C D E F
        'z/4 x/4 c/4 v/4 | b/4 v/4 z/4 x/4 | '
        # Fmaj7 (2 bars): F G A Bb
        'v/4 b/4 n/4 mb/4 | n/4 mb/4 v/4 b/4 | '

        # A2 walking (same changes, slight variation)
        '!0.85 x/4 n/4 b/4 c/4 | v/4 c/4 x/4 n/4 | '
        'b/4 z/4 n/4 m/4 | a/4 b/4 z/4 a/4 | '
        'z/4 c/4 x/4 v/4 | b/4 n/4 z/4 x/4 | '
        'v/4 n/4 b/4 mb/4 | mb/4 n/4 b/4 v/4 | '

        # B bridge — Am7: A  /  D7: D  /  Gm7: G  /  G7: G
        '!0.85 n/4 b/4 n/4 m/4 | z/4 n/4 b/4 n/4 | '
        'x/4 v/4 x/4 c/4 | b/4 x/4 c/4 x/4 | '
        'b/4 n/4 b/4 m/4 | a/4 b/4 n/4 b/4 | '
        'b/4 z/4 n/4 m/4 | a/4 z/4 b/4 n/4 | '

        # A3 final — push harder
        '!0.9 x/4 c/4 v/4 b/4 | n/4 b/4 x/4 c/4 | '
        'b/4 n/4 m/4 z/4 | a/4 z/4 b/4 n/4 | '
        'z/4 x/4 c/4 v/4 | b/4 v/4 z/4 x/4 | '
        'v/4 b/4 n/4 mb/4 | v4'
    ),

    # ── DRUM KIT ── jazz ride pattern with snare on 2 & 4
    # Jazz ride: z=ride cymbal feel (repurposed as pitch)
    # Swing eighth feel: LONG-short LONG-short
    # Using: z=hi-hat/ride, s=snare, a=kick (repurposed from pitch)
    'drum_kit': (
        '^0.55 @138 '

        # intro: just ride cymbal, 4 bars
        '(!0.6 z/2 z/4 z/4)*8 | '

        # main groove: ride on top, snare on 2&4, kick on 1
        # kick(1) ride(1+) snare(2) ride(2+) kick(3+) ride(3+) snare(4) ride(4+)
        '(!1.0 '
        'a/4 z/4 !0.7 z/4 !1.0 s/4 !0.7 z/4 !0.5 z/4 !1.0 s/4 !0.7 z/4 | '
        '!1.0 a/4 z/4 !0.7 z/4 !1.0 s/4 !0.7 z/4 !0.5 z/4 !1.0 s/4 !0.7 z/4)*28 | '

        # fill bar
        '!1.0 a/4 s/4 s/4 s/4 s/4 s/4 s/4 s/4 | '

        # ending
        '(!1.0 a/4 z/4 !0.7 z/4 !1.0 s/4 !0.7 z/4 !0.5 z/4 !1.0 s/4 !0.7 z/4)*3 | '
        '!1.0 a4'
    ),

    # ── CLARINET ── fills between phrases, woody texture
    # Only plays in gaps — rests during busy melody bars
    'clarinet': (
        '^0.75 @138 '

        # intro response
        '-4 | '
        '!0.65 r/4 e/4 w/4 -/4 -/2 q/4 w/4 | '
        '!0.6 e/2 w/4 q/4 -2 | '
        '-4 | '

        # A1: occasional fills in bar 2 and 4
        '!0.6 -4 | -/2 e/4 w/4 q/4 w/4 e/4 w/4 | '
        '-4 | -/2 t/4 r/4 e/4 r/4 t/4 r/4 | '
        '-4 | -/2 e/4 w/4 q/4 w/4 e/4 w/4 | '
        '-4 | -/2 r/4 e/4 w/4 e/4 r/4 e/4 | '

        # A2: a bit more active
        '!0.65 -/2 q/4 w/4 e/4 w/4 q/4 w/4 | -4 | '
        '-/2 y/4 t/4 r/4 t/4 y/4 t/4 | -4 | '
        '-/2 t/4 y/4 t/4 r/4 -/2 | -4 | '
        '-/2 r/4 t/4 r/4 e/4 -/2 | -4 | '

        # B bridge: clarinet more prominent
        '!0.7 y/4 t/4 r/4 e/4 w/4 e/4 r/4 t/4 | '
        '!0.65 -/2 r/4 t/4 y/2 -/2 | '
        'e/4 r/4 t/4 r/4 e/4 w/4 e/4 w/4 | '
        '-/2 e/4 r/4 t/2 -/2 | '
        '!0.7 r/4 t/4 y/4 t/4 r/4 e/4 w/4 q/4 | '
        '!0.65 -/2 t/4 r/4 e/2 -/2 | '
        'w/4 e/4 r/4 e/4 w/4 q/4 w/4 e/4 | '
        '-4 | '

        # A3: warm fills to close
        '!0.65 -/2 e/4 r/4 t/4 r/4 e/4 r/4 | -4 | '
        '-/2 y/4 t/4 r/4 t/4 y/4 t/4 | -4 | '
        '-/2 t/4 y/4 t/4 r/4 e/4 r/4 | -4 | '
        '!0.7 r/2 e/4 w/4 q/2 w/4 e/4 | '
        '!0.65 e4'
    ),

}