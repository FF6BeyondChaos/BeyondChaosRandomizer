# BeyondChaos

FF6 Beyond Chaos CE "Community Edition" Randomizer
<p>
a fork of SubtractionSoup's FF6 Beyond Chaos EX Randomizer
<p>
a fork of Abyssonym's FF6 Beyond Chaos Randomizer
<p>

__Version__: 5.0.1
<br />
__Date__: 2023-07-02
<br />
__URL__: https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/releases/latest
<br />
__Beyond Chaos Discord__:    https://discord.gg/S3G3UXy

## Overview

Beyond Chaos CE is a randomizer, a program that remixes game content randomly, for FF6. It is a fork of [Abyssonym](https://github.com/abyssonym/)'s [Beyond Chaos randomizer](https://github.com/abyssonym/beyondchaos) with even more features.
Every time you run Beyond Chaos CE, it will generate a completely unique, brand-new mod of FF6 for you to challenge and explore. With the basic flags, there are over 10 billion different possible randomizations!

Nearly everything is randomized, including treasure, enemies, colors, graphics, character abilities, and more.
Beyond Chaos CE is also customizable. Using the flags in the above section, you can choose to only randomize certain parts of the game. Every flag you select will make the game a little more random, and also a little more difficult. Therefore, even experienced players should be able to find some challenge in the resulting game. As the game progresses, enemies may become more and more difficult, so that it becomes necessary to develop specialized strategies for individual formations.

__DISCLAIMER__: This randomizer uses a Markov chain to generate enemy names, and as such may create names that make you uncomfortable. Use at your own risk.

## Quickstart

### Requirements:
 * FF3 US 1.0 ROM (we cannot provide this)
 * If not running Windows, install [Python 3.7+](https://www.python.org/downloads/).

## Setup

### Windows:

Download the BeyondChaos.zip from [the releases](https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/releases), and extract the files to a folder of your choice. If you don't see a `BeyondChaos.exe`, you downloaded the wrong thing. The executable will download the Beyond Chaos Sprite pack automatically on startup. If you are using beyondchaos_console.exe, you will need to download the sprites manually at https://github.com/FF6BeyondChaos/BeyondChaosSprites and monster sprites at https://github.com/FF6BeyondChaos/BeyondChaosMonsterSprites

### Linux/Mac:
Download the source files and extract them to a folder of your choice. Install Python 3.7 or higher, python2 is no longer supported. Open a command prompt, navigate to the folder you chose, and type

```bash
pip3 install -r requirements.txt
```

## Running the randomizer

### Windows:
Run `BeyondChaos.exe`. If you're using a version prior to Windows 10 and get an error message, try [this](https://support.microsoft.com/en-us/help/2999226/update-for-universal-c-runtime-in-windows).

### Other users:

```bash
python randomizer.py
```

### Source ROM file

You must provide a FF3 US 1.0 ROM. Both unheadered and headered roms will work. Click the browse button and find the ROM on your system.

If you use an incorrect or modified rom, the randomizer will warn you after you click "Generate Seed". To be sure, you can check that your rom is correct by comparing the unheadered checksum/hash:

```
MD5 - e986575b98300f721ce27c180264d890
CRC32 - a27f1c7a
```

### Seed value

The seed value is an integer number that can be used to share the same randomization with other people. If you don't know which seed you want, just leave this blank (it will use the current time).

### Mode

In the GUI, on the left, you can select a mode.
 * `normal` mode (default): you play through the story as usual.
 * `ancient cave`, `speed cave`, and `race cave` modes: you will traverse a randomized three-party dungeon to defeat Kefka; they differ in the length of the dungeon.
 * `K at N` mode: you play through the beginning of the normal story, ending at the fight with Kefka at Narshe. Designed for racing, you start with a random set of Espers, encounters on the Lete River are fixed, and enemies always drop the same item 100% of the time.
 * `dragon hunt` mode: you start in the World of Ruin with the airship, and it ends immediately when you kill the 8th dragon.

### Flags

There are a LOT of options that affect what gets randomized and add additional changes to the game. __If this is your first seed__, I recommend going down to bottom where it says "Saved flag selection", and picking "Recommend new player flags" from the dropdown menu.
This will give you a good taste of Beyond Chaos CE while leaving out a few things that can sometimes be frustrating for new players.

__If you find that too hard__, try also unchecking the `m` flag.

__The "typical" flags used by veterans are__:

```
(all simple flags except l and k) partyparty makeover capslockoff johnnydmad
```

But the important thing is to pick flags that are fun for you. If you're having fun, you aren't doing it wrong! When you find options you like, click the "Save flag selection" button to save it as a preset so you can quickly select the same flags again.

### Generate Seed

When done selecting flags, click the "Generate Seed" button. It will take some time to generate the seed, and then a dialog box will pop up telling you it's finished.

Output rom file:
    The randomizer generates two files, a patched rom file, and a mini-FAQ. Both files will have the seed value in their name. To play the game, load the patched rom file in your emulator. The mini-FAQ is a text file that mainly includes information about where to get items; colosseum rewards, monster steals and drops, shop info, and monster rages are all included.

## FAQ/KNOWN ISSUES

Bugs can be reported in the [new issue](https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/issues) tracker, though you may get a speedier response in the Discord.
Please remember that this version is maintained by a group of volunteers and we cannot immediately respond to everything.

Q: How do I play Beyond Chaos Bingo?
<br />
A: The code is "bingoboingo". Use the code in the flags and the randomizer will ask you some more questions when the randomization is complete.

Q: How do I use different sprites?
<br />
A: Use the code "makeover" to randomly replace sprites. You can customize which sprites are available by checking custom/spritereplacements.txt.

Q: How do I get random music?
<br />
A: Use the code "johnnydmad" in the flags.

Q: I lost my seed number but I still have the rom. Can I find my seed number again?
<br />
A: The seed is displayed in the auto-generated guide, in the rom's SNES header, and in the opening sequence with the magitek armor.

Q: It says I learned a new Blitz but nobody in my party has Blitz.
<br />
A: Whenever ANY character reaches the level required to learn a Blitz, any characters with Blitz learn it.

Q: It says I learned a new Dance but nobody in my party has Dance.
<br />
A: Whenever you win a fight in a new environment, you learn that Dance, regardless of whether anyone with Dance is in your party.

Q: It says I learned a new Lore but nobody in my party has Lore.
<br />
A: Whenever you win a fight in which a Lore is used, you learn the Lore, regardless of whether anyone with Lore is in your party.

Q: How do I learn new Rages if I don't have Leap?
<br />
A: You learn new Rages by winning any battle with the monster, regardless of whether you're not on the Veldt or anyone with Rage is in your party.

Q: I'm at Vargas but I don't have Blitz. How do I beat him?
<br />
A: You can defeat him normally without Blitz. His HP was lowered to make him beatable without much (if any) grinding. Also, if you can Pummel him, that still works.

Q: How do I defeat TunnelArmr without Runic?
<br />
A: Just kill it.

Q: How do I defeat Ultros at the Esper's hideout without Sketch?
<br />
A: Just kill it. (If you happen to have another way to use Tentacle on him, that'll work too.)

Q: Speaking of Sketch, was the Sketch Glitch patched?
<br />
A: By default, yes. But if you want it unpatched, use the code 'sketch'.

Q: The Moogle Charm doesn't work.
<br />
A: It was nerfed. FF6 uses a threat level based random encounter system, and Moogle Charm increases threat level by the lowest possible value without removing encounters altogether. The specifics are a bit complex, but you should think of it as having about a 1/256 encounter rate if you've been wearing it for a while. Also, some later dungeons might randomly ignore Moogle Charm altogether.

Q: I'm in a dungeon and the encounter rate is insanely high.
<br />
A: Some later dungeons have a chance to become high encounter rate dungeons. However, these dungeons are twice as vulnerable to the effects of Charm Bangle and Moogle Charm.

Q: The switches in the final dungeon don't seem to be working.
<br />
A: They work, I assure you... it seems like the game is a bit buggy when there are parties standing on multiple switches and one of the parties is standing on a switch it doesn't expect. Try moving everyone else off of any switches or in the worst case have them leave the room entirely.

Q: The Fanatics Tower is really long. What gives?
<br />
A: I've made some changes to the Tower, with the intent to make it the most frustrating, obnoxious dungeon possible. If you're stuck, here are some hints in [ROT13](https://rot13.com/) format.
Decode them if you're having trouble.
 * Hint #1:  Vg'f zber qvssvphyg tbvat hc guna pbzvat qbja.
 * Hint #2:  Qba'g trg qvfgenpgrq. Fgnl sbphfrq ba lbhe tbny, naq riraghnyyl lbh jvyy ernpu vg.
 * Solution: Fbzr gernfher ebbzf ner gencf gung qebc lbh gb n ybjre yriry bs gur gbjre. Nibvq gur gernfher ebbzf naq lbh jba'g trg fghpx.

Q: I can't find the Striker! How do I get Shadow from the Colosseum in the World of Ruin?
<br />
A: Lbh pna trg gur Fgevxre ol orggvat vgrzf va gur Pbybffrhz.

Q: The old man in Narshe won't give me the Ragnarok esper. Is this a bug?
<br />
A: It's not a bug. Ragnarok (esper) is at a different location. Location: Gur obff ng gur gbc bs Snangvpf Gbjre unf vg.

Q: I heard that there's a secret item. How do I get it?
<br />
A: (ROT13) Va gur svany qhatrba, gurer'f n fznyy vagrevbe ebbz jvgu n qbbe cnfg n pbairlbe oryg gung vf vanpprffvoyr. Gb ernpu gur qbbe, lbh zhfg hfr na rkcybvg gung vf abeznyyl hfrq gb fxvc Cbygetrvfg va inavyyn SS6. Ybbx hc gur Cbygetrvfg fxvc gb svaq bhg ubj gb qb gur gevpx.

Q: What level should I be for the final dungeon?
<br />
A: It really depends on your gear and what builds you have access to. I usually end up going there around level 35-40, but it doesn't hurt to have a few absurdly high level characters to tank hits.

Q: Yo this is really hard.
<br />
A: Yeah I guess so. I was pretty careful to make sure it was always beatable, though. Obviously the difficulty depends on your specific randomization though, so if you're having trouble, don't feel bad about using savestates or anything. I tried to design the randomizer in such a way that savestates aren't necessary, but I can't account for everything. If you encounter anything that is absolutely absurd in difficulty, please let me know so I can try to adjust the balance for future versions. Also, save often! You never know when you'll randomly encounter a boss on the overworld or in a chest.

Q: I encountered <boss> as a random encounter/monster in a box! Is this a bug?
<br />
A: No.

Q: I used Control on an enemy and ordered him to use a skill on his own party, but he attacked me instead!
<br />
A: Some skills are just like that. They're flagged to never be used on your own party.

Q: The final boss is impossible! How do I win?
<br />
A: (ROT13) Gur orfg cerpnhgvba lbh pna gnxr vf univat rabhtu UC gb fheivir Zrgrbe (hfhnyyl nobhg 5000) naq vaihyarenovyvgl gb znal fgnghf rssrpgf, rfcrpvnyyl Fvyrapr. Xrsxn jba'g pbhagre juvyr ur'f pnfgvat Tbare naq gur fperra vf funxvat, fb guvf vf gur orfg gvzr gb fgevxr.

Q: The boss of the Fanatics Tower is impossible! How do I win without Life 3?
<br />
A: (ROT13) Gur pynffvp fgengrtl bs Enfcvat uvz gb qrngu fgvyy jbexf, naq ur vf bsgra ihyarenoyr gb Ofrex. Hfvat Cnyvqbe gb ynaq gur svany uvg pna jbex, ohg or jnel gung ur zvtug fgneg gur onggyr jvgu vaangr Yvsr 3. Nyfb, vs lbh unir n Trz Obk be fvzvyne vgrz, vg zvtug nyybj lbh gb hfr na novyvgl va gur gbjre gung lbh abeznyyl pna'g hfr... Hygvzn pna or Ehavpxrq, sbe rknzcyr.

Q: Dude I've got like six cursed shields.
<br />
A: Fun fact, if you equip cursed shields on multiple party members, you can uncurse one of them 2x or 3x or 4x as quickly.

Q: I just got a Game Over, but I didn't get to keep my experience levels.
<br />
A: This feature was removed because it didn't work properly with one of the new esper boosts. I also wasn't very fond of it to begin with, because I would often get a Game Over and forget to reset so I don't miss out on valuable esper levels.

Q: My berserker who uses Rage did a slam attack and it did a whole bunch of damage/somehow killed someone on my team.
<br />
A: That's a bug. For some reason when he has the Rage status, the slam attack gets the properties of the Fire spell but with a super high Magic Power. If the enemy has Reflect, it'll hit your team. Hopefully you have equipment that absorbs or nullifies fire.

Q: I can't find a Striker to recruit Shadow?
<br />
A: You can always get a Striker in the coliseum by buying an item from a shop, betting it, and then betting what you win.

Q: Can you add X to the mini-guide that gets generated?
<br />
A: Let me know. I'm not sure what kinds of things people want in the mini-FAQ.

Q: Can you add X feature?
<br />
A: Maybe. I'm open to suggestions, but things that require a lot of effort probably won't get made.

Q: Can I add X feature?
<br />
A: Possibly! Even if I don't think it's a good idea for the standard settings, it could be a flag. Send me a pull request to the project's Github.

Q: Does Beyond Chaos CE work with X mod?
<br />
A: Probably not, especially if the mod makes large changes. But try Beyond Chaos Gaiden, which does work with Brave New World.

Q: Does Beyond Chaos CE work on a real Super Nintendo?
<br />
A: Absolutely! Beyond Chaos has been tested on both Super Everdrive and SD2SNES, and it works 100% perfectly.

Q: I found a bug!
<br />
A: The best way to report it is on the Beyond Chaos Discord in the #bugs channel. Please include the seed number and flags used. (The easiest way is to copy and paste the first line of the .txt file.)

## CONTRIBUTORS

    Abyssonym - original Beyond Chaos creator
    subtractionsoup - former maintainer of Beyond Chaos EX
    CtrlxZ - created or modified a bunch of sprites for the randomizer
    HoxNorf - ported over sprites and music for the randomizer
    DarkSlash - madworld, darkworld, randombosses codes and some other things for KatN mode; current maintainer of Beyond Chaos CE (send help)
    emberling - speeddial, randomized music, alasdraco, dialoguemanager, converted a ton of music, and reworked palettes and sprite replacement, FF6 music player patch
    Rushlight - made music arrangements for the randomizer
    Lockirby2 - The worringtriad and notawaiter codes
    myself086 - new menu features and natural magic expansion
    Dracovious - Created new GUI and R-Limit, and some other codes
    GreenKnight5 - First GUI, Cecilbot
    DrInsanoPHD - Refactoring code, character stats randomizer, bug fixes, lots of help with CE releases
    Crimdahl - Rotating status patch, dancelessons code, removeflashing code, lots of help with CE releases,
    fusoyeahhh - lots of help with CE releases
    RazzleStorm - refactoring some code, adding type hints, lots of help with CE releases
    CDude - lots of help with event codes for CE versions, fixing Bio Blast and Flash/Schiller animations
    Cecil188 - ported over music, owner of the Discord, and overall helper with everything


## EXTERNAL PATCHES USED

    Synchysi - esper restriction
    Lenophis - unhardcoded tintinabar
    Novalia Spirit - "Allergic Dog" bug fix, Selective Reequip
    Leet Sketcher - Y Equip Relics, rotating statuses patch, Imp Skimp
    Assassin - That Damn Yellow Streak fix, sketch fix
    Power Panda - Divergent Paths: The 3 Scenarios
    HatZen08 - Coliseum Rewards Display
    madsiur, tsushiy, Lenophis - FF6 Music Player
    SilentEnigma, Imzogelmo - MP damage color digits

## SPECIAL THANKS

    Cecil188 - OG beyond chaos fan
    Fathlo23 - RPG speedrunner and BC challenge runner
    ffmasterfoobar - twitch broadcaster who did a lot of initial playtesting for my entertainment
    GreenKnight5 - bc_cecilbot programmer
    kupofasa - original permadeath runner
    quikdraw7777 - permadeath community leader and pioneer
    tenkarider - romhacker who gave me lots of early feedback, and creator of the Ultimate Czar Dragon hack, FF6 Curse of the Gods, and many other challenges
    ff6hacking.com community - additional sprites, see custom/sprites/credits.txt for details
    AND YOU

## SPECIAL NO THANKS

    Mitch McConnell
