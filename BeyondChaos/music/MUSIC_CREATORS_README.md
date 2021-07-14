# MUSIC CREATORS README (WIP)

Refer to mfvitools docs at https://github.com/emberling/mfvitools/wiki for help with MML syntax.
This guide is a work in progress.
To do list:
* Extend style guide to encompass channel order, etc.
* Explain jdm devtools and features
* Info on folder structure, uniqueness rules, using variants within jdm etc.
* Info on playlist files
* Info on creating dancing mad tiers
* Quickstart for adding music using sqspcmml
* Guide to using/obtaining custom samples for your MML

## JOHNNYDMAD STYLE GUIDE - basic concerns

The main purpose of this guide is to provide some direction for which samples are appropriate to use to meet johnnydmad style standards, but I'll take the opportunity here to discuss a few other important structural concerns first.

### Sound effects and variants

There are several points in the game where ambient sound effects are combined into the music sequence. johnnydmad maintains this by programmatically adding these sound effects into whatever MML is selected for that area. The affected tracks are: `ruin`, `zozo`, `train`, and (in some % of seeds) `assault`.

Due to the popularity of `johnnyachaotic` you should always design your songs around the possibility that they will sometimes receive these automated edits.
* In the case of `zozo`, the last two tracks will be replaced by a rain sound effect.
* In the case of `ruin` and `assault`, a wind sound effect is placed in the first two tracks, and every other track is moved up by 2, with the last two tracks becoming unused.
* In the case of `train`, looping train track sound effects are added which advance to your song after an event trigger. No direct changes are made to the song itself, however sample 3A is loaded in program 2F, replacing whatever you may have had there.

Therefore, you must always design your songs to be resilient to either losing their last two channels in their entirety, or to having sample 2F replaced with a closed hi-hat. If you want to change anything in channel order, percussion use, or whatever in response to these changes, you can use *variants*.

Another place that may demand variants is `fanfare` - the end of a battle is one of the few places when a new music track is loaded without the loading time being camouflaged by a natural fade or pause. It's also extremely common. Because of this, you should aim to keep memory usage (and thus loading time) as low as possible, using the smallest samples you can get away with. The original FF6 victory fanfare is 1698 blocks, so that should be your target, though anything under 2000 should be fine. But if you're using the same song in any context outside of victory, you'll want access to the full sample memory. You can use variants to design for both cases at once.

### Loudness

Legacy music hasn't generally maintained any sort of standard for loudness and therefore has been somewhat prone to certain tracks being randomly too quiet or jarringly loud. While this is an amateur, collaborative project and worrying too much about loudness is a bit boring, I do feel like as quality improves moving forward it's a good idea to at least establish some standards and tests so that things stay within a certain degree of consistency wherever possible.

Moving forward, I'm going to tentatively try measuring each new track with standard loudness measurements (peak and RMS) and adjusting these to fit within vanilla music ranges for similar songs. I'll include a table of vanilla music loudness values here for reference.

It seems like a solid general target is **-25 dB** RMS and **-8 dB** peak, ranging to a soft maximum around **-22 dB** RMS and **-6.5 dB** peak and a soft minimum around **-28 dB** RMS and **-10 dB** peak.

Aside from battle music, it actually seems like the grand brassy and martial themes that sound like they *should* be loud (e.g. Edgar and Sabin, Save Them! etc.) are more on the average side, while naturally subtler or lower-impact timbres (Kids Run Through the City, Spinach Rag) sometimes get some extra loudness to compensate for their nature.

The maximum volumes above should be treated as a much harder limit than the minimum. If you have a choice between being too loud by one measure, too quiet by the other measure, or a little of both, it should usually be best to avoid being too loud, as long as subjective listening doesn't sound noticeably too quiet. The most important measurement is keeping the peak from being too high. The highest peak in vanilla is **-5.789 dB** with no possibility of overlapping sound effects, or **-6.206 dB** with sound effects. Do everything you can to stay below these numbers; if the song is still too subjectively quiet, try re-balancing the volumes in the track so that there is less contrast between the quieter and loudest parts.

Method: Convert SPC to WAV using SNES SPC700 Player's "save" function. Player volume must be at 100%. Open resulting WAV file in Audacity, select the whole thing, `"Tracks->Mix->Mix Stereo Down to Mono"` and then  use `"Analyze->Contrast" -> Measure selection` for RMS and `"Effect->Amplify" -> Set Amplification to 0 -> "New Peak Amplitude"` for peak.

| Song                      |RMS (dB)|Peak (dB)|
| ----                      | ------  | ----   |
| The Prelude               | -29.74  |-14.665 |
| Omen pt.1                 | -25.26  | -6.386 |
| Omen pt.2                 | -23.54  | -7.131 |
| Omen pt.3                 | -24.30  | -8.360 |
| Awakening                 | -28.93  |-11.642 |
| Terra                     | -22.84  | -7.484 |
| Shadow                    | -26.38  | -7.374 |
| Strago                    | -26.64  | -9.266 |
| Gau                       | -24.86  | -9.435 |
| Edgar and Sabin           | -25.14  | -9.577 |
| Coin of Fate              | -24.52  |-10.190 |
| Cyan                      | -23.75  | -7.813 |
| Locke                     | -25.59  | -8.850 |
| Forever Rachel            | -24.24  | -8.565 |
| Relm                      | -25.84  | -8.764 |
| Setzer                    | -23.33  | -7.775 |
| Epitaph                   | -25.75  |-11.048 |
| Celes                     | -25.00  | -8.798 |
| Techno de Chocobo         | -24.04  | -8.438 |
| The Decisive Battle       | -22.38  | -8.034 |
| Johnny C. Bad             | -25.67  | -7.271 |
| Kefka                     | -26.64  | -7.256 |
| The Mines of Narshe       | -27.86  | -8.842 |
| The Phantom Forest        | -24.11  | -6.753 |
| The Veldt                 | -25.30  | -7.178 |
| Protect the Espers!       | -26.89  | -9.187 |
| The Gestahl Empire        | -24.99  | -8.809 |
| Troops March On           | -24.64  | -7.219 |
| Under Martial Law         | -25.40  | -7.010 |
| Metamorphosis             | -24.22  | -8.120 |
| The Phantom Train         | -24.90  | -8.559 |
| Esper World               | -22.74  | -8.255 |
| Grand Finale?             | -25.33  | -9.920 |
| Mt. Koltz                 | -24.08  | -7.610 |
| Battle Theme              | -23.53  | -7.048 |
| Aria di Mezzo Carattere   | -23.12  | -7.805 |
| The Serpent Trench        | -28.69  |-12.094 |
| Slam Shuffle              | -25.35  | -8.456 |
| Kids Run Through the City | -22.80  | -7.482 |
| What?!                    | -33.91  |-13.525 |
| Gogo                      | -24.68  | -6.452 |
| The Returners             | -26.14  | -9.347 |
| Victory Fanfare           | -25.63  | -6.902 |
| Umaro                     | -25.09  | -8.812 |
| Mog                       | -24.94  | -7.530 |
| The Unforgiven            | -24.68  | -7.808 |
| Battle to the Death       | -23.90  | -8.476 |
| From That Day On...       | -23.10  | -7.867 |
| The Airship Blackjack     | -23.55  | -7.252 |
| Catastrophe               | -21.54  | -7.266 |
| The Magic House           | -27.08  |-10.355 |
| Dancing Mad pt.1          | -21.80  | -6.475 |
| Dancing Mad pt.2          | -25.46  | -9.248 |
| Dancing Mad pt.3          | -24.25  | -6.206 |
| Dancing Mad pt.4          | -22.40  | -6.792 |
| Dancing Mad pt.5          | -21.30  | -6.704 |
| Spinach Rag               | -23.24  | -6.803 |
| Rest In Peace             | -25.97  |-11.204 |
| Overture pt.1             | -28.33  |-11.170 |
| Overture pt.2             | -24.77  |-10.038 |
| Overture pt.3             | -27.16  |-10.549 |
| Wedding Waltz pt.1        | -25.53  |-10.747 |
| Wedding Waltz pt.2        | -28.68  |-12.161 |
| Wedding Waltz pt.3        | -24.60  | -9.882 |
| Wedding Waltz pt.4        | -28.24  |-11.924 |
| Devil's Lab               | -25.12  | -7.815 |
| Floating Continent        | -22.31  | -6.447 |
| Searching For Friends     | -22.92  | -8.790 |
| The Fanatics              | -22.77  | -7.160 |
| Kefka's Tower             | -24.27  |-10.136 |
| Dark World                | -24.82  | -7.411 |
| Balance Is Restored pt.1  | -24.39  | -5.965 |
| Balance Is Restored pt.2  | -23.36  | -5.798 |

## JOHNNYDMAD STYLE GUIDE for sample selection (WIP)

For sample selection, THE HIGHEST PRIORITY IS SOUNDING GOOD. The second priority is sounding "right", meaning either the original mood, melodic line, and whatever accompaniment is feasible is preserved, or you as the arranger chose to change one or more of those things and the arrangement owns those changes; it should be obvious that any changes are not a mistake. The below sample selection guidelines should be followed only to the point that they don't endanger those first two priorities.

On sounding "right", though, a caveat: this stays within the context of late SNES RPG music. While we do want to do our best to preserve the *mood* of the source, be it from NES, PC MIDI, one of the various FM chips, or a live orchestra, or even from a SNES game with significantly more memory limitations or very different aesthetic requirements. We don't want a reproduction; we want the "Fight Against Culex" version, something that incorporates both the style of the original and the mood and sensibility of the surrounding game. NES tracks should be orchestral, for example, instead of or in addition to mimicking the NES sound capabilities using our own triangle and pulse wave samples. Natively orchestral tracks may have to add bass or rethink percussion in order to preserve a sense of impact, rhythm, or bombast that SPC700 isn't really capable of imitating in original form. And SNES original tracks with lower quality, heavily artifacted or FM-derived samples -- piano being the most common offender -- should aim for using the higher quality, more naturalistic equivalents, not imitating the originals.

### PIANOS:
* The standard multisampled piano is:
  * `C7+   06 LQPiano8 (sounds +3oct)`
  * `C6-B6 01 GrandPiano6 (sounds +1oct)`
  * `C5-B5 02 GrandPiano5`
  * `C4-B4 03 GrandPiano4`
  * `  -B3 11 BrightPiano3`
* However, different tracks have different needs, and this is very demanding on memory. Feel free to use any combination that works and produces a generally natural piano sound; avoid using samples significantly above or below their ideal octave. The overly bright, artificial piano timbre found in many, particularly early, SNES games - think FF4 or Breath of Fire - should not be duplicated unless it's integral to the nature of the song (e.g. Lufia 2's casino theme) or unless a natural version proves unfeasible.
* For bass piano parts (single held notes that fill the low end and stay around O3 or below), 08 (Chrono Trigger) is preferred. 05 is provided as an alternative that meshes better with the 01-02-03 piano, as they have the same source (SD3), though 05 doesn't slide cleanly into 03. 04, though a different source entirely, can *sort of* smooth over this transition if needed.
* Most SNES piano parts that aren't that awful bright crap are recorded in the O6-O7 range and 01/09 is a good fit for them. 09 is a lower sample rate version of 01 (taken from Front Mission). The quality difference is mostly unimportant for a single sample, but the transition from 02 to 09 is too rough to recommend using it multisampled. (It's already unfortunate with 02 to 01; you can hear it in some SD3 tracks such as Fable.)
* If you MUST with the bright crap, 05 to its max at A5 then 04 above that seems relatively seamless and has a more natural timbre than 04 alone.
* Be aware of 13 (CT 12-string guitar that sounds like honky-tonk) and C5 (piano pad), which could fill some piano parts.
* Note that 06 sounds significantly better ingame (with echo) than in SF2 audition.
### OTHER ZITHERS/E.PIANOS:
* Not much to note; use what fits and aggressively replace not-quite-harpsichord originals with harpsichord if it sounds better that way. 13 can sub as a honky-tonk-type piano, as it does extensively in CT.
* No "clean" electric piano is provided because @3 exists, as well as D0 (sine) and D1 (triangle).
* 52 is not any instrument in particular but can sub in for many of this style of timbre; it's basically midway between electric piano and clavinet, though the ADSR may need some tweaking for this use case. (The origin of this sample is a tone similar to @3 with a serendipitous typo in its loop point; it's technically closer to e.piano than bass.)
### CHROMATIC PERC.:
* Try 20 for music box parts; octaved with the lower octave delayed by 2 ticks seems effective, if possible.
* It can be hard to tell what is what but try your best to match instrument types rather than just using whatever. Marimba/xylophone should be considered one type (it's all marimba, really) and 23/24 (labelled marimba) should be preferred if feasible.
* 7C can also work well in a marimba-like role. Play with the ADSR; attack of 13-14 might help.
* 28 is the preferred tubular bell.
### ACOUSTIC GUITARS:
* 34 (steel guitar) is the preferred acoustic guitar; even if it's not a match for the original, give it a shot. After that, try 36, then fall back to 35. 
* 33 rarely fits anything but when it does fit it's great - and it can play a wide variety of roles - so just keep it in mind in general. Not necessarily as a guitar.
* 35 plays a good stand-in for a bass guitar in busier soundscapes that drown out its high partials; it can be useful if the standard electric bass is a bit too emphatic.
### ELECTRIC GUITARS:
* A bit of an anything goes area; there's too much variation to make hard rules. If the original sample is a power chord (5th), even faintly, and there's no spare channel, use 44 unless it sucks. Favor the palm-mute combo (48-49) and the S50 guitar variants (41-44) in the rare circumstances that they're actually appropriate, but understand that those *are* rare; this isn't RotDS, and that sound makes a janky lead. If circumstances permit, aggressively split guitar parts into multiple timbres, particularly lead (39/40/maybe 43/etc), harmonic parts (46/47/43), and the crunchy almost-percussive low end (42/41/45/48-49), either by using different samples at different times or by using different samples in different channels at the same time.
* Note that as good as 39 is, 40 holds up better in lower octaves.
* E0, E1, and E2 may also be of use in unusual situations, industrial tinged, skirting the line between guitar and sound effect. Note that E0 sounds much more atonal ingame than SF2, more just the suggestion of tone over noise, but it could fit a super-distorted industrial riff sort of role.
### BASS:
* 50 is the only provided acoustic bass, but in the event it fails, 52, 35, and 57 might work as stand-ins.
* 51 is the canonical electric bass. It should be used for any standard picked/fingered bass parts unless the situation strongly calls for something else.
* If a more fingered and less picked sound is required, 52 and 35 are available, though they each have cases in which they fail hard: 52 when the bass part dips into higher notes, and 35 if the instrumentation is fairly sparse and fails to drown out its upper overtones.
* 54 should be considered the canonical synth bass over 55.
* 55 is a broadly useful sound for various purposes, thickening and layering, as well as certain synth 'blip' sounds, but should be AVOIDED when possible for standard bass guitar / synth bass parts. Try to keep use of this sample to subtler and not immediately recognizable uses.
* Note C6 as a synth-bass-like filter sweep synth, and D1 Triangle Wave as a NES-style bass. C1 also can serve as a particularly spicy synth bass if you've got enough going on above it.
### PIZZICATO:
* 58 (octave pizzicato) is another one of those "use this whenever possible, even when inaccurate to the original, but ONLY if it sounds good, which it usually won't" samples. Beyond that, use what works. 57 and 59 both work for most purposes, so pick whichever fits the desired character and the memory limitations.
### HARP:
* 60 (FF6) is the canonical harp.
* 61 is discouraged in most situations; the exception is when it is a close or exact match to the game's original sound. If the original sound matches 61, then ignore the discouragement and treat 60 and 61 as equal priority, going with what sounds best. I've identified FF4, Lufia 2, RS2, Terranigma, and Rudra no Hihou as using this harp or a very close equivalent, and though the sample differs, I consider Chrono Trigger a close enough sound to consider using this as well.
### STRING ENSEMBLES:
* I've identified a few varied considerations with string samples. 65 should be the rough "default" with 66 and 67 as memory-saving fallbacks, but there are other concerns to watch.
* First is that, to my ear, SNES string samples can be roughly divided into smooth, airy sounds that remind me of fluffy clouds or mist, and rough textured sounds that feel like polished wood grain. On higher notes, the textured style can sound overly noisy, and the smooth style tends to sound indistinct and muddy in medium to low ranges. Chrono Trigger, especially, has only the smooth style of strings, and often high notes will sound weird and breathy with 65. 62 is provided as an attempt to fill this role.
* Second is the baked-in attack time of the samples. Many SNES string samples start directly in the main loop and don't contain the sound of the initial contact between string and bow. Chrono Trigger and Lufia 2 are examples of games with instant-on samples. Usually, these will use the SPC700 attack instead and it becomes moot, but in some cases, especially very short notes, low notes, and especially especially short low notes, you need to reproduce that instant attack. 66 and 67 are instant attack samples, though both have a short attack time applied through ADSR that you may want to adjust to match the target.
* 64 also works very well for those short low notes; if you have the space, it's preferable to use this alongside 65 or 66, taking over the lowest string part (as vanilla FF6 did extensively).
* 63 is for combining two parts separated by one octave, and should swap relatively seamlessly with 65/66/67 when those parts diverge. 67 may need a volume change, as it runs a bit louder than the others.
* C4 is a synth string pad that should primarily be used to represent parts that are clearly intended for synth string pads -- e.g. the lead on Mako Reactor -- but can work as a fallback for normal strings if none of the other options are working out. Like 64, it has a pretty snappy low end, though it isn't instant-on.
* C5 is piano+synth strings and could be conceivably used as another string option with ADSR cropping out the piano hit.
* C3 can also be treated as an alternative fallback to the airy type of strings, though it's inescapably synthetic.
### SOLO STRINGS:
* Mostly a use-whatever-works-best area. 72 can be considered the default but it's a very soft default.
* Generally, in my experience, mid/lower octave solo string parts, like cellos, can be very hard to get to sound "right" and most samples will just sound wrong. Rather than trying to include a large enough variety of samples to fit every situation, it should just be expected that in some cases you will have to load an external sample for this.
* Oboe, bassoon, bagpipe, harmonica type sounds may also serve as replacements either if you're desperate or if the original is a synthetic or ambiguous sound.
### VOX/CHOIR:
* 75 is the default or canonical choir sound.
* Use 73 and 74 to match original source timbres or to aim for a more "realistic" sound, particularly if two or three of these are used for separate parts. Do not use these if the original part is more of a standard SNES or synthesized choir sound.
* Use 78 to match original source (at even priority to 75, not higher), or if a more synthetic sound than 75 is needed, or if a fuller sound at low octaves is needed and 73/74 aren't appropriate, or as a single-octave match to 79 if you need to octave-merge choir parts.
* 77 can also be used (with ADSR) for vox pad type sounds, or (ADSR optional) for many of the synth accent timbres with names like "Halo", "Goblins", "Brightness" and so forth.
* 76 is an odd one that should be avoided for any standard chorus/vox sound. Only use it if you strongly need the "oooh" rather than "ahh" sound, or if the original is also this style of janky '90s General MIDI "Voice Doohs" patch, or (most likely) use it not as a voice sound but as a synthetic alternative pan flute, either above ~ octave 5, or with an attack, so that the 'doo" sound is indistinct.
* B7 is an organ/vox hybrid that may be partially or completely based on the same original sound as 74 (either combined with a rock organ type sample or just cleverly edited). With attack it serves as a LQ version of 74.
### BRASS:
* 81 is the canonical trumpet. Two issues to watch out for: first, it has a relatively slow attack, so if you're using short staccato notes at all, go ahead and lower the sustain level and raise the volume accordingly. %s5 and 1.33x volume usually works well. (Decay defaults to 0 to facilitate this.) Second, it can sometimes induce some weird artifacting at higher notes, especially with vibrato; feel free to replace it if this gets too bad.
* You are also encouraged to consider replacing original "trumpet" parts with the weightier 83 or more enthusiastic and extra 87 if it feels appropriate to the song.
* Use 82 as a single-octave match of 80, or as a versatile second brass timbre if you're already using 81, or to save space, or if 81 proves too problematic.
* 84 is the canonical horn; afterward, there is a clear priority: 84 > 85 > 86 > 7F. Both 84 and 85 are intended to be signature sounds of this sample set. Horn parts vary a lot in character and how well they need to either blend with or distinguish themselves from the surrounding sounds; expect to use this sample frequently, but also reject it frequently. This is the FF7 horn sound and significantly more of a foreground sort of sound than most horn patches. Note that, like 81, this has a slower attack. The default ADSR already starts at %s5 and you may need to bring that even lower, e.g. %s3 / 1.5x, for staccato notes. (It's also a loud sample and at sustain 5 approximately matches other samples' volumes at sustain 7.)
* 85 is a really big-sounding horn that can add a sense of epic scale: the horn of the army approaching on the horizon. It's relatively quiet and blendy for all its dynamism, making it sound like something really big off in the distance. Try not to use without at least a light vibrato, as the transition from onset to loop is jarring without.
* 86 is a more unassuming and mellow horn. It's both blendy and not very dynamic, but its simplicity can lead to its own problems. Approaches a flutelike sound at higher octaves. Like 81, may need adjustment for shorter notes.
* 7F ... if you must. This is provided as a match for those annoying ambiguous timbres in SNES games that sound somewhere between a horn and an oboe -- for instance, the first lead in FF6's Under Martial Law. (Did you realize the lead changes from horn to oboe when the chord changes in that song? I didn't!) In the interest of having our horn parts sound like they're being played by horns, ideally if memory and channels permit this should be subtly layered with one of the horns that sound like horns.
* 88 should be favored over 89 when feasible. Try to watch closely whether the source is octaved and use 87 or 88 accordingly; don't swap it around heedlessly. If the weird tremolo is a problem on 88, feel free to jump to 89.
### PERCUSSION - GENERAL
* Most percussion that doesn't typically sound on multiple notes (e.g. kicks and snares, not toms and congas) is tuned to typically play on A at octave 5. Feel free to shift this around as needed, but if there's no particular need to, leave it on A.
* I'll often make references to two main styles of percussion found in game music: orchestral and rock. In orchestral, you'll typically have a snare drum on its own channel, usually with timpani and cymbals on other channels. In the rock style, you have kick and snare drums sharing a channel, and usually hi-hats and cymbals on another. This is a vast oversimplification of all the possibilities, but for sample selection purposes, those are the distinctions you need to watch. Typically you see short, repeated snare hits and rolls, with main beats emphasized, on the orchestral style, while the rock style usually has about two snares per measure, generally on offbeats, almost never on the first beat.
* You should almost never use rests with percussion. Fill space with ties to let each note ring as long as possible.
### PERCUSSION - KICK
* The vast majority of the time you should be using 0A. Most sources, SNES and otherwise, use this sort of unassuming kick. In almost all cases you should not use echo for this sound. 
* 0B and 0C are available for similar sounding or otherwise "extra" sources. You'll particularly want to use one of these for any songs that use multiple bass drum notes. Unlike most percussion, the origin note on these is F5 instead of A5.
* 0D -- synthetic kick, the oon in oontz. Don't use it unless it matches the source. Do use it if it does. Don't confuse this with the "HiQ" punchy chirp, which is at AC.
### PERCUSSION - SNARE
* Default snare for orchestral style is 1A. Feel free to experiment with 1F instead, particularly if the song is especially martial and/or has a slower tempo, but only use this if it's a solid upgrade. Adding a release rate of roughly 14 to 24 is highly recommended for 1F and optional for 1A. Feel free to lower the pitch a bit with 1F.
* 1B is available if neither of the above work out; it's much more suited for unobtrusively sitting in the background.
* 1C is the default snare for rock styles.
* 1D is our "hard snare", or gated snare. Many games have one of these, used for particularly intense songs like boss fights. Use this if the original song used something similar. This sample can be dampened significantly with ADSR to either act as a normal rock snare when 1C is too expensive, or to match snares like FF5's hard snare, which lacks the "gated reverb" sound that this and most SNES hard snare samples display.
* Either 1A or 1F can be used for rock styles if necessary; they may be appropriate for e.g. jazzy songs. 1C should be an absolute last resort for orchestral styles, and kept at a relatively low volume and muted by ADSR. 1D should not be used for orchestral styles.
* Echo is optional on snares. Feel free to add or remove it without necessarily matching the original. If the original is deliberately cutting snares short for effect, though, be careful not to mess up that effect with echo.
### PERCUSSION - CYMBALS
* Ride cymbals 2A vs 2B - usually one sounds better, use that one. If neither sounds better, go with 2A.
* 2C - clash cymbal - while very few SNES-era songs use a recognizable "clash" rather than "crash", you should strongly consider changing any "crash" sounds to this in orchestral-style songs. Doesn't scale very well to pitch shifting - keep it around A5.
* 2D - default crash cymbal for all rock-style songs and any orchestral songs that 2C isn't good for.
* 2E - alternate crash cymbal, use only if you need to save memory vs. 2D.
* 2F - gong - play this at 4A or thereabouts. This is a gong. Do not randomly replace cymbals with it. You can experiment with it if the original track is doing weird pitch shifty effects that aren't recognizably cymbals, or if it's got those cliches that are often accompanied by gongs (you know the ones).
* Applying `%a3`, `%a5` etc. to any of the above cymbals (other than ride) will produce a passable cymbal roll or "reverse cymbal" sound.
* BA - if the only cymbal you need is that "reverse cymbal" sound, and you're short on memory, you can use this. A5 is a bit high for this one - usable, but try lower pitches. You can also use BA alongside 2C since that doesn't "reverse" quite as well as the others. Try to keep the tone matching if you do - the BA note should be lower by a few tones to match. 
* Echo is optional on cymbals, but there is rarely a downside and a pretty big upside - you can take advantage of the echo to allow a fairly short cymbal note to sound much bigger, freeing the channel for other instruments earlier. If you do crop cymbal notes short, make sure you use ADSR or other functions so that the edges aren't noticeably clipped. It should be fading out rapidly, not cutting instantaneously.
### PERCUSSION - HI HATS
* To my ear, there are basically four common hi hat sample shapes. 3A through 3D provides one example of each shape. Memory and aesthetics permitting, you should try to use the sample matching the original shape. Unfortunately I don't really have the vocabulary to correctly communicate what these shapes represent, but I'll try my best.
* 3A is a "tick" style closed hihat, a sound that rings out pretty loudly then immediately cuts off to silence.
* 3D is a closed hihat that has less harsh boundaries, with a slightly lighter hit and a gradual fade with a longer ring time.
* 3B is an open hihat that has a similar profile, with a lighter onset and a gradual fade before its end.
* 3C is an open hihat with harsh boundaries, possibly heavily compressed, or just an originally much longer sound that is harshly truncated. It has a pretty constant volume until its end.
* Any open hihat sample can be used as a closed hihat via ADSR, if loading two separate samples is impractical. It's lightly recommended to prefer using 3B in this way over 3D, since 3D is a lower quality sample. Try a technique lifted from FFMQ - set sustain to 0 and then swap decay between [0..2] for open and [5..6] for closed. 3B comes with default decay of 5 so you can also swap sustain between 0 and 7 for the same effect. You may want to use different pitches for open and closed when you do this.
* 3D can also be used as an open hihat with the same method; sustain is already 0 so just switch decay. This should primarily/only be used to save memory (vs. using 3B/3C)
* 3E is not intended for use, but only to allow SF2 preview of 3D as an open hihat. The only circumstances under which 3E should ever be used are if sequence memory does not permit using 3D with ADSR.
### PERCUSSION - TOMS
* 4A should be considered the default tom and used in general cases.
* 4B is the same sample as 4A, but cropped less aggressively. Use this rather than 4A whenever sample memory permits - which won't be very often.
* 4C is a gated tom suitable for very synthetic tracks or when the source is also using a gated tom sound, or something unusual that you can approximate with it.
* 4D is a fairly bland backup tom for use in cases when 4A doesn't sound good, or in less intense synthetic drum tracks.
### PERCUSSION - TIMPANI
* 5A is the default timpani. Needs to be played at an octave higher than other timpani. Has an unusual clipped, vaguely glitchy sound that often adds an interesting character but also sometimes just sounds bad. In the cases when it sounds bad, try one of the other timpani.
* 5B is essentially 5A without the weird cropping. A general-purpose fallback, rarely bad, but rarely inspiring.
* 5C is an alternate sound that has a good bit less treble, leaving a more bassy sound. Is a pretty close match to many other games, like FF7; try it first in those cases. Also use it when 5A sounds bad and 5B is too large, or just whenever it sounds significantly better.
* 5D is an alternate sound that's got a little more everything. It's mostly too extra for general use, but can be helpful for certain tracks that lean really heavily on the timpani (e.g. FF5's boss theme).
### PERCUSSION - VERY LARGE DRUMS
* The usual tradition for SNES games is to just use a tom or timpani sound at a low octave, so you always have that option.
* 4E (timbale) at a low octave is often a very effective tonal large drum sound that keeps a fairly heavy onset without being too melodic. Heavy ADSR can also render it into a lot of diverse configurations - see ff12_prison.mml for an example.
* 5E (miyadaiko) is a powerful taiko sound for those long echoing beats, unfortunately at a high memory cost.
* 5F has not proven useful and might get replaced at this point.
* BB (distant boom) is not an effective sound on its own but can be added to another drum for a serious impact. Hold it for a similar long-echoing-beat sound to the miyadaiko (but depending on another sample for the onset), or play a note of even a very short length with echo to get a burst of power added to whatever other drum plays on that beat. See ff14_forthesky.mml for examples.

## LEGACY SAMPLE CONVERSION SUGGESTIONS:
* `01` (Acoustic Guitar) -> try 34 > 36 > 35. No clear match though. Note: 35 sounds one octave lower.
* `02` (Bass Guitar) -> 51. Note: sounds one octave higher.
* `03` (Pan Flute) -> A3
* `04` (Banjo) -> 31 (or 17, 14, 33, 32, 12). Most sound one octave higher. You'll want to add some harsh ADSR.
* `05` (Cello) -> 70, 72, or re-import this sample. Alternatives sound one octave higher.
* `06` (Choir) -> 75. Sounds one octave higher.
* `07` (Flute) -> A5, or A7 for space. Same timbre (A7 is same sample).
* `08` (Horn) -> Priority 84 > 85 > 86 > 7F. At least one of those should work.
* `09` (Atma Synth) -> Import.
* `0A` (Oboe) -> Ideally multisample between 91 through 94. If not, 92 is the same timbre and sounds one octave higher.
* `0B` (Perc organ) -> B4. Same sample.
* `0C` (Piano) -> 01, 06, or various multisample arrangements. 01 sounds one octave higher. 06 sounds three octaves higher and should only be used if the part stays around o6 or higher.
* `0D` (Strings) -> 65, or 66/67 to save space. Same sample, or same timbre for the alternatives.
* `0E` (Trumpet) -> Consider using 83. If not, priority 81 > 82. 81 and 82 sound one octave higher.
* `0F` (closed hihat) -> 3A. Same sample.
* `10` (mouth harp) -> AF. Same timbre, sounds two octaves higher.
* `11` (open hihat) -> 3C.
* `12` (crash cymbal) -> 2D. Will generally want to sound on a higher note (12 was native A4 while 2D is native A5, but many custom songs used 12 on higher notes so blanket shifting up an octave may not be advisable.)
* `13` (breath sfx) -> import
* `14` (march snare) -> 1A is preferred over 1B. 1B is same sample.
* `15` (pat) -> try 6E
* `16` (timpani) -> 5A is preferred over 5B. (5A same timbre/one octave lower; 5B same sample.)
* `17` (tom) -> 4B is same sample. 4A is a much less memory intensive variation.
* `18` (ac. bass) -> 50. Sounds one octave higher. May need to play with the ADSR some.
* `19` (pizzicato) -> 59 is a clean replacement, but go ahead and experiment with 57 and 58. They sound one octave lower.
* `1A` (tuba) -> 83. Same timbre, sounds one octave higher.
* `1B` (harp) -> 60. Same sample.
* `1C` (synth bass) -> 55 is the same sample, but please see if you can use 54 instead.
* `1D` (bouzouki/mandolin) -> 32, same timbre.
* `1E` (dist guitar) -> 41, same sample, but experiment with 42/43/literally anything.
* `1F` (ocarina) -> If it's being used as a thin flute, A4 (sounds one octave higher). If it's being used as a whistle, A6 (sounds one lower) or D0 with a bit of attack.
* `20` (rhodes) -> 19 or 18 (sounds one higher)
* `21` (hard snare) -> 1D
* `22` (kick) -> 0A, same sample.
* `23` (cowbell) -> 9D or 9C.
* `24` (tubular bells) -> 28, or 29 if it doesn't work out. Will probably need to fiddle with octaves, but there's no definitive answer for how much.
* `25` (church organ) -> B0.
* `26` (cuica) -> AB.
* `27-29` (cho-co-bo) import.
* `2A` (fingersnap) -> 8E.
* `2B` (side stick) -> 8A.
* `2C` (contrabass) -> 64, same sample.
* `2D` (guiro) -> 9B. Will need fiddling.
* `2E` (conga) -> 7A.
* `2F` (shaker) -> 6B, or 6A for space saving.
* `30` (wood block) -> 8C.
* `31` (dulcimer) -> try 14, 13, or 6. 14/13 sound one octave below, 6 sounds two above.
* `32` (ac. guitar) -> 36 is closest, but try 34 > 36 > 35.
* `33` (bagpipe) -> 99, same sample.
* `34` (shakuhachi) -> A4 is probably closest; use legato to imitate the initial trill.
* `35` (recorder) -> This is pretty close to a pure sine with some attack. If that's what you're after, use A6 (sounds one higher), D0 (two higher), or D1 (one higher) with attack added. But if you want to lean into the recorder sound with something breathier, use A1 (two higher). And if you want a smooth, ambiguous woodwind, go with the clarinet at 95 (one higher). All else equal, I prefer the clarinet. C3 is also a decent match if you're looking for something atmospheric.
* `36` (recorder/tin whistle) -> This usually gets used as "flute with prominent attack", so A4 (two higher) or A3 (one higher) are the most likely replacements. Again, though, I encourage pivoting to recorder (A1, one higher) or especially clarinet (95).
* `37` (sleigh bells) -> 6D.
* `38` (Ralse) -> 73, or if you absolutely must, the same sample is available at F0.
* `39` (Draco) -> 73, or if you absolutely must, the same sample is available at F1.
* `3A` (Maria) -> 75 or 74, or if you absolutely must, the same sample is available at F2.
* `3B` (pipe organ) -> B0. Same sample, sounds one octave higher.
* `3C` (bonk!) -> 4E maybe?
* `3D` (crane sfx) -> treat this as an import, so only use if you specifically need it, but it's at FA.
* `3E` (marimba) -> 23, same sample.
* `3F` (crowd sfx) -> FC, treat it as an import, do not break glass unless there is a fire etc.
* `40` (oboe) -> Use multisample if you can, but if you can't, this is same timbre as 94.
* `41` (brightness FX) -> 77, same sample.
* `42` (vibraphone) -> 22, same sample.
* `43` (RS3 strings 2) -> 62, probably, or 65/66/67/C4. All sound one octave lower. Maybe C3, which doesn't.
* `44` (12str. Guitar?) -> 33, same sample.
* `45` (CT strings) -> 62 or 66 are the most likely replacements, depending on whether you need instant-onset with 66 or clear airy high notes with 62. Feel free to use both. C4 can be a lifesaver as an alternative. All sound one octave lower.
* `46` (RnH strings) -> 67, generally.
* `47` (melodic bell) -> 27, same sample.
* `48` (sitar) -> 30.
* `49` (RS3 strings 1) -> 65, or maybe 62, or maybe one of the other strings. Sounds one octave lower.
* `4A` (slap bass) -> 56. Sounds one octave higher.
* `4B` (2300AD glass synth) -> if this is the original sound, import it (it's a fifth, so you need to). if it's just there to be fancy, try ... just about anything in the choir/organ/synth sections, really (7x/Bx/Cx). C5 is probably closest.
* `4C` (gong) -> 2F, same sample.
* `4D` (fretless bass) -> 53, sounds one octave higher.
* `4E` (violin) -> 71, or 70/72 (sounds one lower) or import.
* `4F` (sax) -> 98, same sample.
* `50` (crash cymbal) -> 2D.
* `51` (clap) -> 8F, same sample.
* `52` (od.guitar) -> 
* `53` (piano) ->
* `54` (ac.guitar) -> 34 > 36 > 35
* `55` (tambourine) -> 6C.
* `56` (snare) -> 1C, same sample.
* `57` (conga) -> 
* `58` (cembalo) -> 
* `59` (trance kick) -> 0D, same sample.
* `5A` (open hihat) -> 3B, same sample.
* `5B` (conga + gliss) ->
* `5C` (ultra pulse) -> C1, same sample.
* `5D` (od.guitar) -> 
* `5E` (wood block) ->
* `5F` (shaker) -> 
* `60` (bass piano) -> 08, same sample.
* `61` (violin) -> 70, same sample, sounds one octave lower.
* `62` (e.piano) -> 
* `63` (ocarina/whistle) -> 
* `64` (vox) -> 
* `65` (kick) -> 
* `66` (tom) -> 4A, adjust pitch.
* `67` (e.piano) -> 
* `68` (open hihat) -> 3C, same sample.
* `69` (fiddle) -> 72, same sample.
* `6A` (oct.brass) -> 88, sounds one lower.
* `6B` (bass) -> 51, same timbre, sounds one higher.
* `6C` (fuzzy dist.) -> 45, same sample.
* `6D` (cymbal) -> 2D.
* `6E` (tom) -> 4A or 4D, adjust pitch.
* `6F` (elec.guitar) -> 
* `70` (filter sweep synth) -> C6, same sample.
* `71` (hard snare) -> 1D with heavy ADSR
* `72` (brass) -> 87
* `73` (horn) -> 85, same sample. Default ADSR slightly different, adjust if needed.
* `74` (clarinet) -> 96
* `75` (timpani) -> 5D, same sample.
* `76` (glockenspiel) -> 21, same sample.
* `77` (orch hit) -> 68 or 69
* `78` (bassoon?cello?) -> 72 or 90/99
* `79` (piano) -> 01
* `7A` (horn) -> 86
* `7B` (12str/dulcimer) -> 13, same sample.
* `7C` (ultra-sawtooth) -> C2, same timbre.
* `7D` (solo-overdrive) -> 39, or 40 (apply vibrato). 39 sounds one octave lower.
* `7E` (hard snare) -> 1D
* `7F` (trumpet) -> 82, same sample.
* `80` (electric bass) -> 51 or 35. 35 sounds one octave higher.
* `81` (march snare) -> 1A, same sample.
* `82` (brass sect. - octave) -> 89, same sample.
* `83` (calliope) -> C0, same sample.
* `84` (tom) -> 4D is a close timbre match, but consider 4A/4B instead. Transpose down about 4 semitones.
* `85` (conga slap) -> 7B
* `86` (marimba/xylo) -> 23/24/25. Sounds one octave lower.
* `87` (accordion) -> B9 or A9, or maybe A8 (-1) or E3
* `88` (ride) -> 2B (same sample) or 2A. Pitch is different for both.
* `89` (fuzzy synth) -> experimentation will be necessary; consider C1, C3, B5, B6, 67, 42 etc.
* `8A` (piano O4) -> 03, same sample
* `8B` (piano O5) -> 02, same sample
* `8C` (piano O6) -> 01, same sample. sounds one octave higher
* `8D` (tubular bell) -> 28, or 29
* `8E` (cymbal) -> 2D, or 2E
* `8F` (hi-hat) -> 3C, or if size is an issue, use 3D with ADSR (%y0 ~ %y2)
* `90` (pizzicato) -> experimentation will likely be necessary among 57/57/59
* `91` (tubular bell) -> 29, same sample
* `92` (vox pad) -> 78, same sample
* `93` (choir ahhhs) -> 73
* `94` (octave strings) -> 63
* `95` (dulcimer/santur) -> 15 (same source)
* `96` (pizzicato bass) -> 57, same sample
* `97` (clean guitar) -> 35, same timbre
* `98` (kid lawl) -> import lawl
* `99` (rena lawl) -> import lawl
* `9A` (trumpet) -> 81, same sample
* `9B` (rotary organ) -> B5, same sample, sounds one octave lower
* `9C` (clavinet) -> 16, same sample
* `9D` (timbale) -> 4E, same sample
* `9E` (steel drum) -> 26, same sample
* `9F` (bass clarinet) -> 97, same sample
* `A0` (synth overdrive) -> 40, same sample, or 39, E2, D2 ~ D6 etc.
