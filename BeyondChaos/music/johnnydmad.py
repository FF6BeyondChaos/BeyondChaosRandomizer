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
    
def johnnydmad():
    print("johnnydmad EX5 test console")
    
    try:
        print("using ff6.smc as source")
        with open("ff6.smc", "rb") as f:
            inrom = f.read()
    except IOError:
        while True:
            print("File not found. Enter source ROM filename:")
            fn = input()
            try:
                with open(fn, "rb") as f:
                    inrom = f.read()
            except:
                continue
            break
        
    f_chaos = False
    kw = {}
    force_dm = None
    while True:
        print()
        if "playlist_filename" in kw:
            print(f"Playlist file is set to {kw['playlist_filename']}")
        print()
        print("press enter to continue or type:")
        print('    "chaos" to test chaotic mode')
        print('    "sfxv" to check songs for errors, sorted by longest sequence variant')
        print('    "mem" to check songs for errors, sorted by highest memory use variant')
        print('    "pool" to simulate many seeds and report the observed probability pools for each track')
        print('    "battle" to simulate many seeds and report probabilities for only battle music')
        print('    "pl FILENAME" to set FILENAME as playlist instead of default')
        print('    "dm FILENAME" to generate a test tierboss MML file including FILENAME')
        i = input()
        print()
        if i.startswith("pl "):
            kw["playlist_filename"] = i[3:]
            continue
        break
    if i == "chaos":
        f_chaos = True
    if i == "sfxv":
        mass_test("sfx", **kw)
    elif i == "mem":
        mass_test("mem", **kw)
    elif i == "pool":
        pool_test(inrom, **kw)
    elif i == "battle":
        pool_test(inrom, battle_only=True, **kw)
    elif i.startswith("dm "):
        tierboss_test(i[3:], **kw)
    else:
        print('generating..')
        metadata = {}
        outrom = process_music(inrom, meta=metadata, f_chaos=f_chaos, **kw)
        outrom = process_formation_music_by_table(outrom)
        outrom = process_map_music(outrom)
        outrom = add_music_player(outrom, metadata)
    
        print("writing to mytest.smc")
        with open("mytest.smc", "wb") as f:
            f.write(outrom)
        
        sp = get_music_spoiler()
        with open("spoiler.txt", "w") as f:
            f.write(sp)
            
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
    iterations = 10000
    
    print()
    for i in range(iterations):
        tracklist = process_music(inrom, pool_test=True, playlist_filename=playlist_filename)
        for track, song in tracklist.items():
            if track not in results:
                results[track] = []
            results[track].append(song)
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
                iset = mml_to_akao(mml, variant=variant, inst_only=True)
                mml = append_legacy_imports(mml, iset, raw_inst=True)
            mml = apply_variant(mml, type, trackname, variant=variant)
            bin = mml_to_akao(mml, song + ' ' + trackname, sfxmode=use_sfx, variant=variant)[0]
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
    johnnydmad()
    print("end")
    input()