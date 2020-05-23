import math
import concurrent.futures
import time

'''
PLEASE DON'T JUDGE LAZY CODE
this is just for fun <3
'''



def calculate_catch_rate(rate, rock=False, bait=False):
    '''Can only accept EITHER balls OR Rocks
    The FRLG games use a fairly odd catch formula
    the catch rate of a pokemon is modified to a 'catch factor' and then
    back to a catch rate by multiplying it by 100/1275, modifiying for 
    any bait or balls that have been thrown, then multiplying by 1275/100
    again. Since division doesn't maintain floating point numbers in this case
    most catch rates are modified and end up being lower
    SEE NOTE AT END FOR ALL THE RATES BEFOER AND AFTER MODIFICATION
    '''
    # pull the modified catch rate
    rate = get_catch_factor(rate, rock, bait)[0]
    # calculate catch rate after ball and health (full health with a safari ball)
    a = int(int((rate * 15) /10)/3)
    if a >= 255:
        p = 1    
    else:
        # odds of a shake
        b = int(int('0xffff0', 16)/(int(math.sqrt(int(
                 math.sqrt(int('0xff0000', 16)/a))))))
        # odds of successful capture
        p = pow((b/65536), 4)
    return p


def get_catch_factor(rate, rock=False, bait=False):
    '''
    The game multiplies the Pokemon's base catch rate by 100/1275
    to get a 'Catch Factor'
    the catch factor is modified by bait or balls however the devs
    put in a minimum of '3' after bait which actually increases Chansey's
    catch factor from 2 -> 3
    there is also a maximum of 20
    THESE MODIFIERS ARE PERMANENT AND ARE NOT REMOVED EVEN IF THE POKEMON STOPS
    EATING OR BEING ANGRY
    '''
    factor = int(int((rate * 100)/255)/5)
    if rock > 0:
        # Bait and balls stack
        factor = int(rate * 2 * rock)
    elif bait > 0:
        factor = int(factor * 0.5 * bait)
    # Iff bait or rocks have been used the game has max & min values
    if (bait or rock) and (factor < 3):
        # Minimum is 3 effectivley 38 Catch rate
        factor = 3
    if (bait or rock) and (factor > 20):
        # Max is 20 which is a 255 catch rate
        factor = 20
    rate = int(factor * 1275/100)
    return (rate, factor)


def calculate_flee_rate(rate, angry, eating):
    # When the rate is pulled from game files
    # there is a minimum of 2
    if rate < 2:
        rate = 2
    # Get the 'flee factor'
    rate = int(int((rate * 100)/255)/5)
    # OTHER STUFF TO DO - ROCKS
    if eating:
        # Divide flee rate by 4 if eating
        # based off a floored version of the flee factor / 4
        rate = int(rate/4)
    if rate < 1:
        # there is a bare minimum flee rate so bait cannot drop it below
        # 5% per turn
        rate = 1
    # The game generates a random # and compares it to 5 x the flee rate
    # Get the odds of fleeing per turn
    p = rate * 5 / 100
    return p


def balls_only_catch(catch_rate, flee_rate):
    '''
    USED TO GET THE ODDS OF CAPTURE WITHOUT ANY BAIT
    INT catch_rate - the pokemons base catch rate
    INT flee_rate - base flee rate
    '''
    # get the odds of capture per ball
    p_catch = calculate_catch_rate(catch_rate, 0, 0)
    # get odds of fleeing per ball
    p_flee = calculate_flee_rate(flee_rate, False, False)
    # Run the first turn
    round_vals = odds_of_catch(1, p_catch, p_flee)
    p_success = round_vals[1]
    p_failure = round_vals[2]
    balls = 1
    #Throw balls until we run out
    while balls < 30:
        round_vals = odds_of_catch(round_vals[0], p_catch, p_flee)
        p_success += round_vals[1]
        p_failure += round_vals[2]
        balls += 1
    p_failure += round_vals[0]
    #Return the probability of successfully catching the Chansey vs not
    return (p_success, p_failure)

def odds_of_catch(p_turn, p_catch, p_flee):
    '''FOR ODDS BY TURN - TAKES INTO ACCOUNT ODDS OF GETTING TO SAID TURN'''
    # The probability to catch on any ball throw is:
    # the odds of getting to the turn x the odds of catching with one ball
    p_catch_new = p_catch * p_turn
    # The odds of flee after any ball throw is:
    # the odds of getting to the turn x the odds of not catching * odds of flee
    p_flee = (1 - p_catch) * p_turn * p_flee
    # the odds to get to the next turn is just whatever is left over
    p_continue = p_turn - p_catch_new - p_flee
    return (p_continue, p_catch_new, p_flee)

def add_bait(bait_to_add, current_bait):
    '''
    Takes in the currently remaining amount of bait in a pile
    adds the amount of bait rolled from the bait throw's RNG
    NOTE: Bait seems to be equally distributed between 2-6 turns
    Bait maxes at 6
    think of bait as being a pile though, each throw adds to the pile
    and does NOT reset the pile
    '''
    if (current_bait <= 0):
        current_bait = bait_to_add
    else:
        current_bait = current_bait + bait_to_add
    # set bait to the max of 6
    if current_bait > 6:
        current_bait = 6
    return current_bait

def pattern_odds_catch(turns='L',  r=0, catch_rate=30, flee_rate=125):
    '''
    catch_rate -> INT (Base catch rate of pokemon)
    flee_rate -> INT (Base flee rate of the pokemon)
    turns -> String ('R' Rock, 'T' Bait. 'L' Ball) ex 'TLTLLLTLL'
    r -> INT (0 = no repeat, hard run pattern), (1 = repeat pattern if bait ends), (2 = if bait fails, move to balls)
    amount_of_bait -> int 0 to 6 (Amount of bait left at the start of the turn)
    baited -> default is false but should be true if any bait has been thrown
    t -> retention of the overall pattern in recursive calls
    RETURN
    p_success -> probability of catching the pokemon using the pattern of turns
    p_failure -> probability of failing the capture
    '''    
    # Get catch rates and flee rates
    p_flee_watching = calculate_flee_rate(flee_rate, False, False)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    p_catch = calculate_catch_rate(catch_rate, 0, 1)
    p_catch_unbaited = calculate_catch_rate(catch_rate, 0, 0)    
    result = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch, p_catch_unbaited, turns, r)
    return (result[0], result[1], turns)

def pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns, r, p_turn=1, amount_of_bait=0, baited=False, t=0):
    '''
    catch_rate -> INT (Base catch rate of pokemon)
    flee_rate -> INT (Base flee rate of the pokemon)
    p_turn -> float <= 1 (the odds of the current turn occuring)
    turns -> String ('R' Rock, 'T' Bait. 'L' Ball) ex 'TLTLLLTLL'
    r -> BOOL true for restarting patterns, False to not
    amount_of_bait -> int 0 to 6 (Amount of bait left at the start of the turn)
    baited -> default is false but should be true if any bait has been thrown
    t -> retention of the overall pattern in recursive calls
    RETURN
    p_success -> probability of catching the pokemon using the pattern of turns
    p_failure -> probability of failing the capture
    '''
    #If this is the first turn store the full pattern
    #is reduced by one function after each turn
    if t == 0:
        t = turns
    if len(turns) > 0:
        turn = turns[0]
    else:
        p_success = 0
        p_failure = p_turn
        return (p_success, p_failure)
    p_success = 0
    p_failure = 0
    # Cycle through the pattern of turns until there are no turns left
    # OPTIMIALLY THE PATTERN WILL UTILIZE ALL 30 BALLS
    # DETERMINE IF THE POKEMON IS EATING
    p_catch = p_catch_baited
    if amount_of_bait > 0:
        eating = True
        p_flee = p_flee_eating
        baited = True
        #Amount of bait is reduced later (at end of round, before next check)
    else:
        eating = False
        p_flee = p_flee_watching
        if not baited:
            p_catch = p_catch_unbaited
    # If a ball was thrown get the odds of capture vs fleet
    if turn == 'L' and (eating or r == 0):
        round_vals = odds_of_catch(p_turn, p_catch, p_flee)
        ##print(round_vals[1])
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        p_turn = round_vals[0]
        #MOVE TO NEXT TURN
        if(amount_of_bait > 0):
            amount_of_bait -= 1
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_turn, amount_of_bait, baited, t[:-1])
        p_success = p_success + round_vals[0]
        p_failure = p_failure + round_vals[1]
    # If bait is to be thrown run the probabilities for each amount of bait
    elif turn == 'T' and (eating or (not baited) or r == 0):
        # add probability of fleeing on current turn
        p_failure = p_failure + (p_turn * p_flee)
        if amount_of_bait <= 0:
            for i in (2, 3, 4, 5, 6):
                #includes bait reduction for end-of-round
                new_bait = i - 1
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 1:
            for i in (2, 3, 4, 5):
                #includes bait reduction for end-of-round
                new_bait = i
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                if i != 5:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.4 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
                # print('Still working')
        elif amount_of_bait == 2:
            for i in (2, 3, 4):
                #includes bait reduction for end-of-round
                new_bait = i + 1
                # Get the probability of adding the current amount of bait
                if i != 4:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.6 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 3:
            for i in (2, 3):
                #includes bait reduction for end-of-round
                new_bait = i + 2
                # Get the probability of adding the current amount of bait
                if i != 3:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.8 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        else:
            #includes bait reduction for end-of-round
            new_bait = 5
            # Get the probability of adding the current amount of bait
            p_add_curr_bait = p_turn * (1 - p_flee)
            round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
            p_success = p_success + round_vals[0]
            p_failure = p_failure + round_vals[1]
    elif (r == 1):
        # IF A BALL, AND r = repeat, BUT THE POKEMON IS NOT EATING START THE PATTERN AGAIN
        # IF A BALL, BUT THE POKEMON IS NOT EATING START THE PATTERN AGAIN
        # Start the pattern again with the same number of still remaining balls
        #Get new number of turn
        n_balls = turns.count('L')
        new_turns = ''
        balls = 0
        i = 0
        while balls < n_balls:
            new_turns = new_turns + t[i]
            if t[i] == 'L':
                balls +=1
            i += 1
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, new_turns, r, p_turn, 0, baited, t)
        p_success = round_vals[0]
        p_failure = round_vals[1]
    elif (r == 2):
        #IF A BALL AND THE POKEMON IS NOT eating but r = balls after fail
        #remake pattern as Balls and change to no-repeat
        n_balls = turns.count('L')
        new_turns = 'L' * n_balls
        r = 0
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, new_turns, r, p_turn, 0, baited, t)
        p_success = round_vals[0]
        p_failure = round_vals[1]
    elif (r == 3):
        #IF a ball and the pokemon is NOT eating but r = restart with at least 15 balls, balls only otherwise
        n_balls = turns.count('L')
        new_turns = get_best_pattern(n_balls, t, p_flee_watching)
        if (new_turns[1] < 1):
            p_success = new_turns[1] * p_turn
            p_failure = new_turns[2] * p_turn
        else:
            round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, new_turns[0], r, p_turn, 0, baited, t)
            p_success = round_vals[0]
            p_failure = round_vals[1]
    return (p_success, p_failure)



def pretty_outputs(catch_rate=30, flee_rate=125, name='CHANSEY'):
    print("OUTPUT FOR " + name)
    print("Base catch rate: " + str(catch_rate))
    factor = get_catch_factor(catch_rate, 0, 0)
    print("Base catch factor: " + str(factor[1]))
    print("Modified catch rate: " + str(factor[0]))
    p_catch = calculate_catch_rate(catch_rate, 0, 0)
    print("Odds of capture per ball: " + str(round((p_catch * 100), 2)) + "%")
    print()
    print("Base catch rate: " + str(catch_rate))
    factor = get_catch_factor(catch_rate, 0, 1)
    print("Catch factor after bait: " + str(factor[1]))
    print("Modified catch rate after bait: " + str(factor[0]))
    p_catch = calculate_catch_rate(catch_rate, 0, 1)
    print("Odds of capture per ball after bait: " +
          str(round((p_catch * 100), 2)) + "%")
    print()
    print("Base flee rate: " + str(flee_rate))
    fleet_ub = calculate_flee_rate(flee_rate, False, False)
    print("Odds of fleeing per turn while not eating: " +
          str(round((fleet_ub * 100), 2)) + "%")
    print()
    print("Base flee rate: " + str(flee_rate))
    fleet = calculate_flee_rate(flee_rate, False, True)
    print("Odds of fleeing per turn while eating: " +
          str(round((fleet * 100), 2)) + "%")
    print('----------------------------------------------------')
    print("THE FOLLOWING ODDS ARE PER ENCOUNTER - NOT PER BALL")
    print('----------------------------------------------------')
    odds_b = pattern_odds_catch('LLLLLLLLLLLLLLLLLLLLLLLLLLLLLL', 0, catch_rate, flee_rate)
    print("Odds of capture with balls only and no bait: " +
          str(round((odds_b[0] * 100), 2)) + "%")
    odds_bb = pattern_odds_catch('TLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL', 0, catch_rate, flee_rate)
    print("Odds of capture with one bait followed by only balls: " +
          str(round((odds_bb[0] * 100), 2)) + "%")
    if (flee_rate >= 100):
        odds = get_best_pattern(30, '', fleet_ub)
    else:
        odds = [('L' * 30), odds_b[0], odds_b[1]]
    print("Odds of capture using the optimal algorithm lookup table: " + str(round((odds[1] * 100), 2)) + "%")
    print("This optimal pattern is: " + odds[0])
    print("Where 'L' -> Ball, & 'T' -> Bait")
    if (flee_rate >= 100):
        print("If the Pokemon ever begins to 'watch carefully' refer to the lookup table and proceed as instructed.")



def all_pretty():
    # CHANSEY
    pretty_outputs(30, 125, 'CHANSEY')
    pretty_outputs(45, 125, 'DRAGONAIR, PINSIR, SCYTHER, TAUROS, N KANGASKHAN')
    pretty_outputs(45, 100, 'DRATINI')

def make_pattern(number, balls, pattern=''):
    balls = balls - pattern.count('L')
    binary = str(bin(number))[2:]
    if (len(binary) < balls):
        binary = '0' * (balls - len(binary)) + binary
    for i in range (1, balls + 1):
        if (binary[-i] == '1'):
            pattern += 'TL'
        else:
            pattern += 'L'
    return pattern

def new_pats(t_balls, start_p='T'):
    balls = t_balls - start_p.count('L')
    pats = []
    for x in range(0, balls-2):
        num = balls - x
        max_tll = int(num/2)
        min_tllll = int(num/4)
        if min_tllll == 0:
            min_tllll = 1
        for t in range(min_tllll, max_tll + 1):
            s = '2' * (t)
            max_range = int(s, base=3)
            for i in range(0, max_range + 1):
                pat = start_p
                tern = ternary(i)
                bin_p = str(tern)
                if len(bin_p) < t:
                    bin_p = '0' * (t - len(bin_p)) + bin_p
                p_sum = 0
                for p in bin_p:
                    if p == '0':
                        p_sum += 2
                        pat = pat + 'TLL'
                    elif p == '1':
                        p_sum += 3
                        pat = pat + 'TLLL'
                    elif p == '2':
                        p_sum += 4
                        pat = pat + 'TLLLL'
                p_sum += x
                if p_sum == balls:
                    pat = pat + 'L' * x
                    pats.append(pat)
    pats = list(dict.fromkeys(pats))
    return pats

def new_best(balls, pattern='', r=3, catch_rate=45, flee_rate=125):
    best_odds = 0
    pats = new_pats(balls, pattern)
    while (len(pats) % 8) != 0:
        pats.append('L')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        i = 0
        while i < len(pats):
            futures = []
            for x in range (0,8):
                curr_pattern = pats[i + x]
                future = executor.submit(pattern_odds_catch, curr_pattern, r, catch_rate, flee_rate)
                futures.append(future)
            for f in concurrent.futures.as_completed(futures):
                odds = f.result()
                if odds[0] > best_odds:
                    best_pattern = odds[2]
                    best_odds = odds[0]
                    best_fail = odds[1]
                    best_i = x
            i += 8
    result = (best_i, best_pattern, best_odds, best_fail)
    print(result)

def best_patterns(balls, pattern='', r=3, catch_rate=45, flee_rate=125):
    def_balls = pattern.count('L')
    best_odds = 0
    # -1 because TL at the end is a useless simulation
    # -2 cuz it never picks TLL either
    x = '0b' + '1' * (balls - def_balls - 2)
    max_range = int(x, base=2)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        i = 0
        while i < max_range:
            futures = []
            for x in range (0,8):
                curr_pattern = make_pattern(i+x, balls, pattern)
                future = executor.submit(pattern_odds_catch, curr_pattern, r, catch_rate, flee_rate)
                futures.append(future)
            for f in concurrent.futures.as_completed(futures):
                odds = f.result()
                if odds[0] > best_odds:
                    best_pattern = odds[2]
                    best_odds = odds[0]
                    best_fail = odds[1]
                    best_i = i
            i+=8
    result = (best_i, best_pattern, best_odds, best_fail)
    print(result)

def make_best_patterns():
    print('getting 30 DRATINI')
    best_patterns(30, 'TTLLTLLLTLLTLLTLLTLLTLL', 3, 45, 100)
    print('DONE')

def get_best_pattern(balls, t='TLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL', p_flee=0.45):
    # CHANSEY GANG (v3 Done)
    if (p_flee == 0.45):
        if balls == 1:
            return ('L', 0.08090370381673062, 0.9190962961832694)
        elif balls == 2:
            return ('LL', 0.12180076580573657, 0.8781992341942635)
        elif balls == 3:
            return ('LLL', 0.14247435181511667, 0.8575256481848833)
        elif balls == 4:
            return ('LLLL', 0.1529249107966428, 0.8470750892033572)
        elif balls == 5:
            return ('LLLLL', 0.1582076993257738, 0.8417923006742262)
        elif balls == 6:
            return ('LLLLLL', 0.1608781645796279, 0.839121835420372)
        elif balls == 7:
            return('LLLLLLL', 0.16222809267777477, 0.8377719073222252)
        elif balls == 8:
            return ('TTLLLLTLLLL', 0.16830671740469066, 0.8316932825953094)
        elif balls == 9:
            return ('TTLLLTLLLLLL', 0.17342245344920654, 0.8265775465507934)
        elif balls == 10:
            return ('TTLLLLTLLLLLL', 0.17669485427442488, 0.8233051457255751)
        elif balls == 11:
            return ('TTLLLTLLTLLLLLL', 0.18030255209048968, 0.8196974479095105)
        elif balls == 12:
            return ('TTLLLTLLTLLLLTLLL', 0.18228422870474015, 0.8177157712952601)
        elif balls == 13:
            return ('TTLLLTLLTLLLTLLLLL', 0.184404282711728, 0.8155957172882721)
        elif balls == 14:
            return ('TTLLLTLLTLLLTLLLLLL', 0.18597126472063313, 0.814028735279367)
        elif balls == 15:
            return ('TTLLLTLLTLLLTLLTLLLLL', 0.18690385300864581, 0.8130961469913544)
        elif balls == 16:
            return ('TTLLLTLLTLLLTLLTLLLLLL', 0.18796442928188759, 0.8120355707181127)
        elif balls == 17:
            return ('TTLLLTLLTLLLTLLTLLLLTLLL', 0.18854273829407667, 0.8114572617059235)
        elif balls == 18:
            return ('TTLLLTLLTLLLTLLTLLLTLLLLL', 0.18914862906034852, 0.8108513709396517)
        elif balls == 19:
            return ('TTLLLTLLTLLLTLLTLLLTLLLLLL', 0.18960241256951776, 0.8103975874304824)
        elif balls == 20:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.18987527384333064, 0.8101247261566695)
        elif balls == 21:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.19018103874431083, 0.8098189612556894)
        elif balls == 22:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLLTLLL', 0.19035110936934285, 0.8096488906306574)
        elif balls == 23:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.1905247782635673, 0.8094752217364327)
        elif balls == 24:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.19065640698242278, 0.8093435930175774)
        elif balls == 25:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.19073625164055685, 0.8092637483594434)
        elif balls == 26:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.19082442583132692, 0.8091755741686733)
        elif balls == 27:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLTLLL', 0.19087439248126886, 0.8091256075187313)
        elif balls == 28:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.19092421741917792, 0.8090757825808224)
        elif balls == 29:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.19096239607155366, 0.8090376039284465)
        elif balls == 30:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.19098575048934807, 0.8090142495106522)
    # DRATINI
    elif (p_flee == 0.35):
        if balls == 1:
            return ('L', 0.08090370381673062, 0.9190962961832694)
        elif balls == 2:
            return ('LL', 0.1292365952582831, 0.870763404741717)
        elif balls == 3:
            return ('LLL', 0.1581112732383264, 0.8418887267616737)
        elif balls == 4:
            return ('LLLL', 0.17536136946853897, 0.824638630531461)
        elif balls == 5:
            return ('TTLLLLL', 0.19218558195769303, 0.807814418042307)
        elif balls == 6:
            return ('TTLLLLLL', 0.21480977097208143, 0.7851902290279187)
        elif balls == 7:
            return ('TTLLTLLLLL', 0.23148688845745813, 0.7685131115425416)
        elif balls == 8:
            return ('TTLLTLLLLLL', 0.24783684417355756, 0.7521631558264423)
        elif balls == 9:
            return ('TTLLTLLLTLLLL', 0.2602763963638958, 0.739723603636104)
        elif balls == 10:
            return ('TTLLTLLLTLLLLL', 0.27189930620089603, 0.7281006937991039)
        elif balls == 11:
            return ('TTLLTLLLTLLLLLL', 0.2809083669488186, 0.7190916330511813)
        elif balls == 12:
            return ('TTLLTLLLTLLTLLLLL', 0.28940696810566574, 0.7105930318943343)
        elif balls == 13:
            return ('TTLLTLLLTLLTLLLLLL', 0.2963161764937821, 0.7036838235062177)
        elif balls == 14:
            return ('TTLLTLLLTLLTLLTLLLLL', 0.3017821715089778, 0.6982178284910221)
        elif balls == 15:
            return ('TTLLTLLLTLLTLLTLLLLLL', 0.3068770463625228, 0.6931229536374772)
        elif balls == 16:
            return ('TTLLTLLLTLLTLLTLLLTLLLL', 0.3107712621301031, 0.6892287378698968)
        elif balls == 17:
            return ('TTLLTLLLTLLTLLTLLTLLLLLL', 0.3144164989209397, 0.6855835010790601)
        elif balls == 18:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLLL', 0.3172377598907309, 0.682762240109269)
        elif balls == 19:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.3198813648838284, 0.6801186351161713)
        elif balls == 20:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.3220437110055217, 0.6779562889944784)
        elif balls == 21:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLLLL', 0.3238196008587215, 0.6761803991412784)
        elif balls == 22:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLLLLL', 0.325387100729413, 0.6746128992705871)
        elif balls == 23:
            return ('TTLLTLLLTLLTLLTLLTLLTLLLTLLTLLLLL', 0.32662603199734985, 0.6733739680026499)
        elif balls == 24:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLLLL', 0.32777851469963637, 0.6722214853003635)
        elif balls == 25:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLTLLLL', 0.32866283775755656, 0.6713371622424433)
        elif balls == 26: 
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLTLLLLLL', 0.3294874478375553, 0.6705125521624445)
        elif balls == 27:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLTLLLTLLLL', 0.3301292056211285, 0.6698707943788713)
        elif balls == 28:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.3307249582277525, 0.6692750417722475)
        elif balls == 29:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.3312147814535883, 0.6687852185464115)
        elif balls == 30: #V3
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLTLLLTLLTLLLLL', 0.33161672239261086, 0.6683832776073891)
    # PARA-SEANAT
    elif (p_flee == 0.25):
        if balls == 1:
            return ('L', 0.08090370381673062, 0.9190962961832694)
        elif balls == 2:
            return ('LL', 0.13667242471082963, 0.8633275752891703)
        elif balls == 3:
            return ('LLL', 0.1751150433233133, 0.8248849566766867)
        elif balls == 4:
            return ('LLLL', 0.20161439461005312, 0.798385605389947)
        elif balls == 5:
            return ('TLLLLL', 0.22388144847806607, 0.776118551521934)
        elif balls == 6:
            return ('TTLLLLLL', 0.2494425326820556, 0.7505574673179445)
        elif balls == 7:
            return ('TTLLLLTLLL', 0.26889898943858787, 0.7311010105614122)
        elif balls == 8:
            return ('TTLLTLLLLLL', 0.28754516671368774, 0.7124548332863123)
        elif balls == 9:
            return ('TTLLLTLLLLLL', 0.3030545872215335, 0.6969454127784666)
        elif balls == 10:
            return ('TTLLLTLLTLLLLL', 0.31572605489898464, 0.6842739451010155)
        elif balls == 11:
            return ('TTLLLTLLTLLLLLL', 0.32737231865938266, 0.6726276813406173)
        elif balls == 12:
            return ('TTLLTLLLTLLTLLLLL', 0.3361455605610303, 0.6638544394389698)
        elif balls == 13:
            return ('TTLLTLLLTLLTLLLLLL', 0.34459991445195814, 0.655400085548042)
        elif balls == 14:
            return ('TTLLLTLLTLLLTLLLLLL', 0.35108870686505755, 0.6489112931349424)
        elif balls == 15:
            return ('TTLLTLLLTLLTLLTLLLLLL', 0.35690503254580547, 0.6430949674541947)
        elif balls == 16:
            return ('TTLLTLLLTLLTLLLTLLLLLL', 0.36178397744952817, 0.6382160225504719)
        elif balls == 17:
            return ('TTLLTLLLTLLTLLTLLLTLLLLL', 0.365851773639004, 0.634148226360996)
        elif balls == 18:
            return ('TTLLTLLLTLLTLLLTLLTLLLLLL', 0.3695180523383902, 0.6304819476616098)
        elif balls == 19:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.37236180459553847, 0.6276381954044616)
        elif balls == 20:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.37504709691764415, 0.624952903082356)
        elif balls == 21:
            return ('TTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.37707042332716734, 0.6229295766728329)
        elif balls == 22:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLLLL', 0.3789726328439457, 0.6210273671560544)
        elif balls == 23:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLTLLLLLL', 0.3805260371189447, 0.6194739628810555)
        elif balls == 24:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLLLL', 0.38182390309306224, 0.618176096906938)
        elif balls == 25:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.38298965927407086, 0.6170103407259292)
        elif balls == 26:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.3838976113057896, 0.6161023886942105)
        elif balls == 27:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.3847511613943437, 0.6152488386056564)
        elif balls == 28:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.38539812359859205, 0.6146018764014081)
        elif balls == 29:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLTLLLLLL', 0.38600327631876075, 0.6139967236812395)
        elif balls ==30:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLLTLLLLLL', 0.38649788903973337, 0.613502110960267)
    pattern = ''
    n_balls = 0
    i = 0
    while n_balls < balls:
        pattern = pattern + t[i]
        if t[i] == 'L':
            n_balls +=1
        i += 1
    return (pattern, 1, 1)


'''
USEFUL RAM ADDRESSES (FRLG)
SAFARI BALL COUNTER
02039994

CATCH FACTOR
0200008C

FLEE FACTOR
0200008B

NUMBER OF TURNS
03004FA3

NUMBER OF TURNS LEFT EATING
0200008A
---------------------------
POKEMON CATCH AND FLEE RATES
Order:
NAME = Base Flee Rate, Flee Factor, odds to run (unbaited)
Base Catch Rate, Catch Factor, Safari Zone Catch Rate

Nidoran F = 50, 3, 15%
235 -> 18 -> 229
Nidorina = 75, 5, 25%
120 -> 9 -> 114
Nidoran M = 50, 3, 15%
235 -> 18 -> 229
Nidorino = 75, 5, 25%
120 -> 9 -> 114
Paras = 50, 3, 15%
190 -> 14 -> 178
Parasect = 75, 5, 25%
75 -> 5 -> 63
Venonat = 50, 3, 15%
190 -> 14 -> 178
Venomoth = 75, 5, 25%
75 -> 5 -> 63
Psyduck = 50, 3, 15%
190 -> 14 -> 178
Poliwag = 50, 3, 15%
255 -> 20 -> 255
Slowpoke = 50, 3, 15%
190 -> 14 -> 178
Doduo = 50, 3, 15%
190 -> 14 -> 178
Exeggcute = 75, 5, 25%
90 -> 7 -> 89
Rhyhorn = 75, 5, 25%
120 -> 9 -> 114
Chansey = 125, 9, 45%
30 -> 2 -> 25
Kangaskhan = 125 9, 45%
45 -> 3 -> 38
Goldeen = 50, 3, 15%
225 -> 17 -> 216
Seaking = 75, 5, 25%
60 -> 4 -> 51
Scyther = 125, 9, 45%
45 -> 3 -> 38
Pinsir = 125, 9, 45%
45 -> 3 -> 38
Tauros = 125, 9, 45%
45 -> 3 -> 38
Magikarp = 25, 2?, 10%
255 -> 20 -> 255
Dratini = 100, 7, 35%
45 -> 3 -> 38
Dragonair = 125, 9, 45%
45 -> 3 -> 38
'''
def balls_only(cr, fr):
    for i in range(1, 31):
        pattern = 'L' * i
        print(i)
        print(pattern)
        print(pattern_odds_catch(pattern, 3, cr, fr))
    pass

def all_best(cr, fr, first):
    start = time.perf_counter()
    for i in range(first, 31):
        print(i)
        new_best(i, 'T', 3, cr, fr)
        fin = time.perf_counter()
        print(f'Finished in {round(fin-start, 2)} second(s)')
    input("DONE LMAO IMPRESSIVE")

def ternary (n):
    if n == 0:
        return '0'
    nums = []
    while n:
        n, r = divmod(n, 3)
        nums.append(str(r))
    return ''.join(reversed(nums))

if __name__ == '__main__':
    print("GENERATION 3 SAFARI ZONE CALCULATOR")
    #input("PRESS ENTER TO BEGIN")
    print("DRATINI VERIFICATION")
    #  input("Enter the name of the Pokemon you are inquiring about")
    #balls_only(45, 75)
    all_best(45, 100, 5)
    #make_best_patterns()
    #input('FINI')
    
