import itertools
import tempfile

from . import options
from . randomizer import randomize

TEST_ON = False
TEST_SEED = "2|normal|bcdefgimnopqrstuwyz makeover partyparty novanillar andombosses supernatural alasdraco capslockoff johnnydmad notawaiter mimetime questionablecontent canttouchthis suplexwrecks cursepower:1 |1603333081"
#FLARE GLITCH TEST_SEED = "2|normal|bcdefgimnopqrstuwyzmakeoverpartypartynovanillarandombossessupernaturalalasdracocapslockoffjohnnydmadnotawaitermimetimedancingmaduinquestionablecontenteasymodocanttouchthisdearestmolulu|1635554018"
#REMONSTERATE ASSERTION TEST_SEED = "2|normal|bcdefgijklmnopqrstuwyzmakeoverpartypartyrandombossesalasdracocapslockoffjohnnydmadnotawaiterbsiabmimetimedancingmaduinremonsterate|1642044398"
#TEST_SEED = "2|normal|bdefgijmnopqrstuwyzmakeoverpartypartynovanillaelectricboogaloorandombossesalasdracojohnnydmadbsiabmimetimedancingmaduinquestionablecontentdancelessons|1639809308"
TEST_FILE = "FF3.smc"

def _modify_args_for_testing(args):
    # while len(args) < 3:
    #    args.append(None)
    # args[1] = TEST_FILE
    # args[2] = TEST_SEED
    args['sourcefile'] = TEST_FILE
    args['seed'] = TEST_SEED

class SeedTester:
    def __init__(self, source, seed, **kwargs):
        self._seed = seed
        self.reset()
        self._args = {
            # Do not recommend overriding these
            "TEST_ON": False,
            "use_gui": False,

            "source": source,
            # FIXME: we should probably delete this when we're done with it
            "destination": tempfile.mkdtemp(),
            "seed": seed,
            **kwargs
        }

    def reset(self):
        options.Options_ = options.Options(options.ALL_MODES)

    def cycle_codes(self, mode, flags=None, codes=None):
        from . import State

        if flags is None:
            flags = list(set(options.ALL_FLAGS) - set(mode.prohibited_flags))

        if codes is None:
            codes = list(set(options.ALL_CODES) - set(mode.prohibited_codes))

        # This will get *very* out of hand if we have more than
        # a handful of choices
        #n = len(codes)
        #combos = [itertools.combinations(codes, n - i) for i in range(n)]
        # Do individual codes, then all codes
        combos = [[code] for code in codes]
        combos += [codes]

        for code_set in combos:
            self.reset()
            options.Options_.mode = mode

            # TODO: check if flag is prohibited in mode
            for flag in flags:
                options.Options_.activate_flag(flag)

            for code in code_set:
                options.Options_.activate_code(code)

            self._state = State()
            new_args = self._args.copy()
            self._state._process_args(new_args, interactive=False)
            try:
                randomize(self._state, **new_args)
            except Exception as e:
                print(f"Flag / code combination failed:\n"
                      f"args: {new_args}\n"
                      f"flags: {''.join([f.name for f in  flags])}\n"
                      f"codes: {' '.join([c.name for c in code_set])}\n"
                      + str(e))

if __name__ == "__main__":
    from argparse import ArgumentParser
    argp = ArgumentParser(description=f"Beyond Chaos Randomizer testing suite")
    argp.add_argument("-S", "--source-file", help='where the rom at?')
    argp.add_argument("-s", "--seed", default=0, type=int, help='numeric random seed')
    argp.add_argument("-m", "--mode", default=1, help="game mode to test")
    args = argp.parse_args()

    seed = f"testing|{args.mode}||{args.seed}"

    tester = SeedTester(args.source_file, seed)
    tester.cycle_codes(options.ALL_MODES[args.mode])
