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
