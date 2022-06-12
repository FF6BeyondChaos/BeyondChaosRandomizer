import sys
import os
import pathlib
import configparser

from argparse import ArgumentParser

from . import State
from . import randomizer
from .config import VERSION, BETA, VERSION_ROMAN

argp = ArgumentParser(description=f"Beyond Chaos Randomizer Community Edition, "
                                  "version {VERSION}")
argp.add_argument("source", default=None, nargs="?",
                  help='file path to your unrandomized Final Fantasy 3 v1.0 ROM file')
argp.add_argument("destination", default=None, nargs="?",
                  help='directory path where you want the randomized ROM and spoiler log created')
argp.add_argument("seed", default=None, nargs="?",
                  help='flag and seed information in the format version.mode.flags.seed')
argp.add_argument("bingotype", default="aims", nargs="?",
                  help='The desired bingo options, if you are using the bingoboingo code')
argp.add_argument("bingosize", type=int, default=5, nargs="?",
                  help='The desired positive integer for the size of bingo card, if you are using the bingoboingo code')
argp.add_argument("bingodifficulty", default="n", nargs="?",
                  help='The desired bingo difficulty selection, if you are using the bingoboingo code')
argp.add_argument("bingocards", type=int, default=1, nargs="?",
                  help='The desired positive integer for number of bingo cards to generate, if you are using the bingoboingo code')

argp.add_argument("TEST_ON", type=bool, default=False, nargs="?",
                  help='Turn on testing mode. Legacy flag, do not use.')

if __name__ == "__main__":
    # Legacy option handling
    # if len(argv) > 3 and argv[3].strip().lower() == "test" or TEST_ON:
    #    randomize(args=args)
    #    sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == '?':
        argp.print_help()
        sys.exit()

    print('You are using Beyond Chaos CE Randomizer version "%s".' % VERSION)
    if BETA:
        print("WARNING: This version is a beta! Things may not work correctly.")

    state = State()
    args = argp.parse_args()
    args = state._process_args(vars(args))

    if state.version and state.version != VERSION:
        print("WARNING! Version mismatch! "
              "This seed will not produce the expected result!")
    # FIXME: restore this
    #mode_name = ...
    #print(f"Using seed: {VERSION}|{mode_name}|{flags}|{seed}")

    randomizer.randomize(state, **args)
    exit()

    try:
        randomizer.randomize(state, **args)
        input('Press enter to close this program.')
    except Exception as e:
        print('ERROR: %s' % e, '\nTo view valid keyword arguments, use `python -m BeyondChaos.beyondchaos -h`')
        import traceback

        traceback.print_exc()
        if fout:
            fout.close()
        if outfile is not None:
            print('Please try again with a different seed.')
            input('Press enter to delete %s and quit. ' % outfile)
            os.remove(outfile)
        else:
            input('Press enter to quit.')
