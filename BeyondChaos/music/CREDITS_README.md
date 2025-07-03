# Explanation of credits associated with included songs and what they signify

## Composer
This is the official composer listed on the game OST, or best approximation available. If the official listing has multiple composers but does not specify which tracks they specifically worked on, but I can find well-sourced information about this, then that will be followed. (For example, "Fighting of the Spirit" appears on some Shinji Tamura albums without Sakuraba credits.)

If an arrangement not by the original composer is used as source, the official arranger credit may be included in comments in the .mml file.

## Transcription / reference / citation
Myself and other music hackers for FF6 have traditionally taken a romhacker's perspective primarily, rather than a musician's perspective. What this means is that when confronted with the prospect of creating a song hack, our first instinct isn't to listen carefully to the original song itself, identifying notes and parts by ear, but to dive into the data of its source game and decipher the sequence that produces the sound. (Generally through tools made for the purpose rather than raw hacking, but I did *make* some of those tools, and did my own reverse-engineering on two formats, sxc/Neverland/Lufia and rudra no hihou.)

Since musical transcription isn't necessarily a skill we cultivate, some music hackers have referenced fan-created transcriptions such as MIDIs, sheet music, and youtube videos when the data-first approach isn't feasible. Others prefer to muddle through the process of transcribing anyway.

Generally speaking, the intent is not to convert the transcription (and any attendant arrangement details) into FF6, but rather to use the transcription as a map of the original, referring to both transcription and original audio to produce a new arrangement of the original optimized for our particular constraints.

That said, we usually tend more toward faithful reproduction than remix -- the actual guideline is "imagine we're including the song as an official port, like from another console, or like Battle with Culex" -- and so a lot of things, like exact volume proportions, may be copied directly from the source/transcription. Typically the degree of copying lies somewhere on the spectrum between "tracing someone else's artwork" and "using sheet music to perform a musical piece" -- or less, when more of a remix is intended (typically in NES-sourced work). That is to say, these are not wholly original arrangements, but they are recreations, not direct digital file conversions. (With a major exception.)

The main exception is that Square SNES games have close enough cross-compatibility that digital file conversions are very effective and produce good results out of the box, and great results with editing. Anything with transcription source `FF5→FF6 MCS2` or `mvfitools` (excluding `mfvitools (sxc2mml)`) is an edited digital file conversion from its original game.

## Arranged / ripped by

This is the person responsible for creating the song hack itself, either as a .mml file or as a binary data blob in FF6 format. This generally implies arrangement in the sense of arranging a piece for an instrument it was not originally designed for -- because SPC700, and even the individual sound engines that run on it, are effectively distinct instruments.

Even in the case of songs transferred from closely-compatible SPC700 engines -- even in the case of native FF6 songs -- it's often necessary to rearrange, for instance, the assignment of different parts to different channels, because the environment that a song can play in might be different. BC and many other hacks sometimes don't play battle music in battles, meaning that field music has to be arranged to expect up to 4 channels at a time being interrupted by sound effects. On top of this, `johnnyachaotic` allows literally any song to have two channels taken out to devote to wind or rain sound effects, which can potentially add with the previous 4, leaving only 2 fully free channels of music. Vanilla songs, outside of the original battle themes, are rarely arranged in a way that supports this, instead being arranged to minimize program changes and thus file size.

The core creative elements of this role are:
- ordering parts into the eight channels as most appropriate, including selecting which details to merge or remove if the original source used more than eight simultaneous voices and where to add layers or new elements when the original source used fewer
- managing timbre, including selecting samples from our deliberately limited set, adjusting the idiosyncratic SPC ADSR appropriately, applying vibrato, tremolo, and legato where appropriate while avoiding LFO-related SPU slowdowns, etc. Also, mixing / levels adjustments.
- fitting within data constraints (16 samples, 3746 sample memory blocks (33,714 bytes), and 4096 bytes sequence data -- less in circumstances involving embedded sfx (train, ruin, zozo))
thus, it is very impactful on the final sound and generally represents the core, audible difference between original source material and final hack, but this should not be construed as a claim to have necessarily performed any transcription, composition, or arrangement in the sense of creating a substantively new orchestration rather than a best approximation with different tools, or any other musicianship elements not strictly required to create a song port.

Note that in cases where two porters are listed, this almost certainly does not imply a collaboration but rather that one person posted a hack publicly and, later, another person edited it extensively.

## List of transcription/conversion software and keywords

### Keywords
- A person's name or handle in the transcription field, different from the name in the arranger/porter field, signifies that they created some sort of visible score -- MIDI file, module, sheet music, youtube video with note visualization, etc., and that that score was referred to in the production of some or all of the hack.
- If the same name is in both the arranger and transcription field, then the transcription was probably performed specifically for the hack and is likely not available publicly, and may not even exist in a generally legible form. This transcription may be performed directly by ear or, when possible, aided by channel-isolation tools such as [Audio Overload](https://www.bannister.org/software/ao.htm).
- `gamerip` signifies that the source game (usually a PC game) internally uses a legible format such as MIDI or modules, or an easily convertible variant thereof, and that these files were extracted and used for reference. Specific software used may be included in parentheses. If a name is included in parentheses, it means that the rip was not a direct file rip but a recording of MIDI output from the game, and the person who performed that rip is credited.
### Conversion directly to usable FF6 sequences
- FF5→FF6 MCS2 (FF5→FF6 MusicConvertSupport V2) by Snow. Converts raw AKAOSNES3 data to raw AKAOSNES4 data. Original source unknown, available at https://www.ff6hacking.com/wiki/doku.php?id=utility
- [mfvitools](https://github.com/emberling/mfvitools) by emberling. Provides conversion from all AKAOSNES versions as well as SuzukiSNES and the custom engine used by Rudra no Hihou, directly to our .mml format.
### Conversion of sequence data to legible intermediate formats (e.g. MIDI)
- [VGMTrans](https://github.com/vgmtrans/vgmtrans) by Mike, loveemu, sykhro et al. Massive multi-format sequence viewer and extractor, allowing for viewing both as extracted MIDI+SF2/DLS and as annotated hex sequences. Accuracy varies, but usefulness is always high.
- [AKAO2MID](https://github.com/ValleyBell/MidiConverters) by Valley Bell. Converts AKAO PSX (mainly FF7) to MIDI. Effectively obsoleted by VGMTrans.
- [gba_mus_riper](https://www.romhacking.net/utilities/881/) by Bregalad. Converts GBA "SAPPY" engine to MIDI+SF2.
- [top2mid](https://github.com/ValleyBell/MidiConverters) by Valley Bell. Converts Tales of Phantasia / Star Ocean SNES sequences to MIDI.
- [mfvitools (sxc2mml)](https://github.com/emberling/mfvitools) by emberling. Converts sxc/s2c (Lufia, Lufia II, Energy Breaker) somewhat inaccurately to .mml. The resulting file is not usable in this form and should only be used as a reference (usually by converting further to MIDI with VGMTrans). 
- [MIDIPLEX](https://github.com/stascorp/MIDIPLEX) by Stas'M Corp. Provides import of various MIDI-like formats sometimes used in games (RMI, XMI, MUS, etc.) and export to standard MIDI.
### Automatic transcription software / channel-split pitch detection
- [nsfimport](https://rainwarrior.ca/projects/nes/nsfimport.html) by Brad Smith. Famitracker fork that transcribes NSF channel output into an editable module file.
- [spc2it](https://github.com/uyjulian/spc2it) by uyjulian. Transcribes SPC channel output into an .it file, with appropriate samples but more or less arbitrary tuning.
- [FamiStudio](https://famistudio.org/) by BleuBleu. Piano roll based NES music editor that allows importing transcribed NSF channel output.