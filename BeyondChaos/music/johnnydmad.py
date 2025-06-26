# JOHNNYDMAD - developer tool/test interface for FF6 music randomization

# *** READ THIS BEFORE EDITING THIS FILE ***

# This file is part of the johnnydmad project.
# ( https://github.com/emberling/johnnydmad )
# johnnydmad is designed to be used inside larger projects, e.g.
# Beyond Chaos, Beyond Chaos Gaiden, or potentially others in the future.
# If you are editing this file as part of "Beyond Chaos" or any other
# container project, please respect the independence of these projects:
# - Keep johnnydmad project files in a subdirectory, and do not modify
#   the directory structure or mix in arbitrary code files specific to
#   your project.
# - Keep changes to johnnydmad files in this repository to a minimum.
#   Don't make style changes to code based on the standards of your
#   containing project. Don't remove functionality that you feel your
#   containing project won't need. Keep it simple so that code and
#   changes can be easily shared across projects.
# - Major changes and improvements should be handled through, or at
#   minimum shared with, the johnnydmad project, whether through
#   submitting changes or through creating a fork that other johnnydmad
#   maintainers can easily see and pull from.

import configparser
import os
import re
import sys
import traceback

from collections import Counter
from operator import itemgetter

# This construction is required for devtool functionality. Do not remove.
try:
    from .musicrandomizer import *
    from .jukebox import add_music_player
    from .mfvitools.insertmfvi import byte_insert, int_insert
    from .mfvitools.mml2mfvi import mml_to_akao
except ImportError:
    from musicrandomizer import *
    from jukebox import add_music_player
    from mfvitools.insertmfvi import byte_insert, int_insert
    from mfvitools.mml2mfvi import mml_to_akao

    
## TO DO LIST (* = essentially complete)
# * finish ripping FF6 vanilla songs
# * opera mode - johnnydmad side
# * tierboss - coding
# * tierboss - mml setup
# * tierboss insertion devtool
# - sfx insertion devtool
# * write metadata to spoiler
# - specify seed in jdm launcher
# - credits generator devtool
# * music frequency devtool
# * adjust frequency for battleprog to prevent skewing late
# * silent mode for insertmfvi
# * select alternate music.txt (curator mode)
# - external ignorelist for songs and/or sources
# * ensure function with pyinstaller
# - reconcile music player w/ Myria disable sound hack
# * integration with BC randomizer
# * opera mode - beyondchaos side
# - allow music sourced from ROM, if specified by host / integrate mfvi2mml
# - allow selection of less intrusive mode(s) in jdm launcher (no event edits, e.g.)
#       NOTE: the existing event edits remove the save point tutorial event!
#       This has no effect on Beyond Chaos, but in an unmodified ROM, the first save point breaks!
# - test with Gaiden
# - test with WC

def print_progress_bar(cur, max):
    pct = (cur / max) * 100
    cursor = " >)|(<-"
    full_boxes = int(pct // 2)
    cursor_idx = int((pct % 2) * (len(cursor)/2))
    boxtext = cursor[-1] * full_boxes + cursor[cursor_idx]
    print(f"\r[{boxtext:<50}] {cur}/{max}", end="", flush=True)
    
def generate_rom():
    pass
    
def johnnydmad(args):
    print("johnnydmad EX5 test console")

    allow_user_input = args.prompt_user
    insert_music_player = args.music_player 
    infile = args.input_file
    outfile = args.output_file
    playlist = args.playlist
    spoiler_outfile = args.spoiler_output_file
    freespace = args.free_space.split(",")
    try:
        print(f"Using {infile} as source")
        with open(infile, "rb") as f:
            inrom = f.read()
    except IOError:
        if allow_user_input:
            while True:
                print("File not found. Enter source ROM filename:")
                fn = input()
                try:
                    with open(fn, "rb") as f:
                        inrom = f.read()
                except:
                    continue
                break
        else:
            raise Exception(f"Input file {infile} not found")
        
    f_chaos = False
    f_motif = False
    force_dm = None
    def generate_rom():
        print('Generating rom with randomized music')
        metadata = {}
        outrom = process_music(inrom, meta=metadata, f_chaos=f_chaos, f_motif=f_motif, freespace=freespace, playlist_filename=playlist)
        outrom = process_formation_music_by_table(outrom)
        outrom = process_map_music(outrom)

        print()
        if insert_music_player:
            print("Adding in-game music player")
            outrom = add_music_player(outrom, metadata)
        else:
            print('Skipping in-game music player')
        print()
        print(f"Outputting generated rom to location {outfile}")
        with open(outfile, "wb") as f:
            f.write(outrom)
        
        print(f"Generating spoiler log")
        sp = get_music_spoiler()
        print(f"Outputting spoiler log to location {spoiler_outfile}")
        with open(spoiler_outfile, "w", encoding="utf-8") as f:
            f.write(sp)
            
    kw = {}
    kw["playlist_filename"] = playlist

    def print_playlist(playlist_name):
        print(f"Playlist file is set to {playlist_name}")

    print_playlist(playlist)
    if not allow_user_input:
        generate_rom()
    else:
        while True:
            print()
            print("press enter to continue or type:")
            print('    "chaos" to toggle chaotic mode')
            print('    "motif" to toggle motif mode (prefer songs from same game)')
            print('    "sfxv" to check songs for errors, sorted by longest sequence variant')
            print('    "mem" to check songs for errors, sorted by highest memory use variant')
            print('    "pool" to simulate many seeds and report the observed probability pools for each track')
            print('    "battle" to simulate many seeds and report probabilities for only battle music')
            print('    "pl FILENAME" to set FILENAME as playlist instead of default')
            print('    "dm FILENAME" to generate a test tierboss MML file including FILENAME')
            i = input()
            print()
            if i.startswith("pl "):
                playlist = i[3:]
                kw["playlist_filename"] = playlist
                print_playlist(playlist)
                continue
            if i == "chaos":
                f_chaos = True
                continue
            if i == "motif":
                f_motif = True
                continue
            break
        if i == "sfxv":
            mass_test("sfx", **kw)
        elif i == "mem":
            mass_test("mem", **kw)
        elif i == "pool":
            pool_test(inrom, freespace=freespace, **kw)
        elif i == "battle":
            pool_test(inrom, battle_only=True, freespace=freespace, **kw)
        elif i.startswith("dm "):
            tierboss_test(i[3:], **kw)
        else:
            generate_rom()
            
#################################

def tierboss_test(test_song, playlist_filename=None, **kwargs):
    _, original_pool = init_playlist(playlist_filename)
    while True:
        mml = None
        pool = set((a for a in original_pool))
        try:
            mml = generate_tierboss_mml(pool, force_include=test_song)
        except Exception:
            traceback.print_exc()  
        if mml:
            with open("tierboss.mml", "w") as f:
                f.write(mml)
            print("wrote tierboss.mml", end=" ")
        else:
            print(f"failed to generate with \"{test_song}\"", end=" ")
        print("(press enter to reroll; or type a new filename; or type q to quit)")
        i = input()
        if i.lower() == "q":
            break
        elif i:
            test_song = i.strip()
    
def pool_test(inrom, battle_only=False, playlist_filename=None, **kwargs):
    results = {}
    results_by_song = {}
    iterations = 10000
    
    print()
    for i in range(iterations):
        tracklist = process_music(inrom, pool_test=True, playlist_filename=playlist_filename)
        for track, song in tracklist.items():
            if track not in results:
                results[track] = []
            results[track].append(song)
            if not battle_only:
                vsong = song
                if track == "train":
                    if len(song) > 3:
                        if song[-3:] == ":tr":
                            vsong = song[:-3]
                elif track in ["assault", "zozo", "ruin"]:
                    if len(song) > 4:
                        if song[-4:] == ":sfx":
                            vsong = song[:-4]
                elif track in ["tier1", "tier2", "tier3"]:
                    vsong += " (DM)"
                if vsong not in results_by_song:
                    results_by_song[vsong] = {}
                if track not in results_by_song[vsong]:
                    results_by_song[vsong][track] = 0
                results_by_song[vsong][track] += 1
        print_progress_bar(i, iterations)
    print()
    
    if battle_only:
        tracks_to_check = ["battle", "bat2", "bat3", "bat4", "mboss", "boss",
                           "atma", "dmad5", "tier1", "tier2", "tier3"]
    else:
        tracks_to_check = results.keys()
        
    for track in tracks_to_check:
        pool = results[track]
        if len(pool) < iterations:
            pool.extend(["not present"] * (iterations - len(pool)))
            
        print(f"[{track.upper()}]:")
        
        c = Counter(pool)
        rank = sorted(c.items(), key=itemgetter(1), reverse=True)
        songlen = max([len(s) for s in c.keys()])
        for song, reps in rank:
            pct = (reps / iterations) * 100
            print(f"    {pct:04.1f}% {song:<{songlen}} ({reps} / {iterations})")
            
    if not battle_only:
        print("\n * * * * * * * * * *\n")
        song_order = sorted(results_by_song.items(), key=itemgetter(0))
        for song, songtracks in song_order:
            song_count = 0
            for track, track_count in songtracks.items():
                song_count += track_count
            pct = (song_count / iterations) * 100
            print(f"{song.upper()} appears in {pct:.1f}% of seeds:")
            
            rank = sorted(songtracks.items(), key=itemgetter(1), reverse=True)
            for track, track_count in rank:
                pct = (track_count / iterations) * 100
                share = (track_count / song_count) * 100
                print(f"    {pct:4.1f}% ({share:4.1f}%) as {track}")
            
        
def mass_test(sort, playlist_filename=None, **kwargs):
    global used_song_names
    testbed = [
        ("***", "plain", 0x4C, False),
        ("rain", "zozo", 0x29, True),
        ("wind", "ruin", 0x4F, True),
        ("train", "train", 0x20, False)
        ]
    #cursor = " >)|(<"
    playlist_map, _ = init_playlist(playlist_filename)
    results = []
    legacy_files = set()
    jukebox_titles = {}
    song_warnings = {}
    i = 0
    print("")
    for song in sorted(playlist_map):
        binsizes = {}
        memusage = 0
        debugtext = f"{song}: "
        song_warnings[song] = set()
        for type, trackname, idx, use_sfx in testbed:
            tl = Tracklist()
            tl.add_random(trackname, [song], idx=idx, allow_duplicates=True)
            variant = tl[trackname].variant
            if variant is None:
                variant = "_default_"
                
            mml = tl[trackname].mml
            if tl[trackname].is_legacy:
                legacy_files.add(song)
                iset = mml_to_akao(mml, variant=variant, inst_only=True, use_extra_commands=True)
                mml = append_legacy_imports(mml, iset, raw_inst=True)
            mml = apply_variant(mml, type, trackname, variant=variant)
            bin = mml_to_akao(mml, song + ' ' + trackname, sfxmode=use_sfx, variant=variant, use_extra_commands=True)[0]
            binsizes[type] = len(bin)
            
            if song not in jukebox_titles:
                jukebox_titles[song] = get_jukebox_title(mml, song)
            var_memusage = get_spc_memory_usage(mml, variant=variant, custompath=os.path.dirname(tl[trackname].file))
            debugtext += f"({var_memusage}) "
            memusage = max(memusage, var_memusage)
            
            if memusage > 3746:
                song_warnings[song].add("BRR memory overflow")
            if len(bin) > 0x1002:
                song_warnings[song].add("Sequence memory overflow")
            if "%f0" not in mml:
                if re.search("%[Ff][0-9]", mml) is None:
                    song_warnings[song].add("Echo FIR unset (%f)")
            if "%b" not in mml:
                song_warnings[song].add("Echo feedback unset (%b)")
            if "%v" not in mml:
                song_warnings[song].add("Echo volume unset (%v)")
        order = memusage if sort == "mem" else max(binsizes.values())
        results.append((order, song, binsizes, memusage))
        print_progress_bar(i, len(playlist_map))
        i += 1
        
    results = sorted(results)
    print("")
    for largest, song, binsizes, memusage in results:
        print(f"{song:<20} :: ", end="")
        for k, v in binsizes.items():
            print(f"[{k} ${v:0X}] ", end="")
        if song in legacy_files:
            print(f" :: ~{jukebox_titles[song]:<18}~", end="")
        else:
            print(f" :: <{jukebox_titles[song]:<18}>", end="")
        print(f" ({memusage})", end="")
        #if largest >= 0x1002 or memusage > 3746 or song in song_warnings:
        if song_warnings[song]:
            print(" ~~WARNING~~")
            for w in song_warnings[song]:
                print("    " + w)
        else:
            print("")
            
#################################



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Randomize the music in a Final Fantasy 6 rom")
    
    parser.add_argument('-i', '--in', 
                            dest="input_file", 
                            help="Set location for the input ROM",)
    parser.add_argument('-o', '--out', 
                            dest="output_file", 
                            help="Set location for the output ROM")
    parser.add_argument('-so', '--spoiler-out', 
                            dest="spoiler_output_file", 
                            help="Set location for the spoiler log")
    parser.add_argument('-p', '--playlist',   
                            dest="playlist",  
                            help="Set playlist")
    parser.add_argument('-fs', '--free-space',
                            help="Set free space to be used. Comma-delimited list of free rom space to be used for music")
    parser.add_argument('-prompt', '--prompt-user',
                            action="store_true",
                            dest="prompt_user",
                            help="Prompt user for options. Uses set of defaults but allows configuration at runtime")
    parser.add_argument('-noprompt', '--dont-prompt-user',
                            action="store_false",
                            dest="prompt_user",
                            help="Automatically run johnnydmad against the specified arguments. Uses set of defaults if none are set.")

    parser.add_argument('-mp', '--music-player', action='store_true', help="Add a music player to the in-game menu")
    parser.add_argument('-nmp', '--no-music-player', dest='music_player', action='store_false', help = "Do not add the music player to the in-game menu")

    parser.set_defaults(
        free_space="53C5F-9FDFF,310000-37FFFF,410000-4FFFFF", 
        input_file="ff6.smc",
        music_player=True, 
        output_file="mytest.smc",
        playlist = "default.txt",
        prompt_user = True,
        spoiler_output_file="spoiler.txt",
    )

    args = parser.parse_args()
    johnnydmad(args)
    
    print('end')