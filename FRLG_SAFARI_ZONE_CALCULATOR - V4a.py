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
    # Get the 'flee factor'
    rate = int(int((rate * 100)/255)/5)
    # When the rate is pulled from game files
    # there is a minimum of 2
    if rate < 2:
        rate = 2    
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
    # Get the odds of fleeing per turn (%)
    flee_odds = rate * 5
    # Due to non-even distribution of random number generation
    # We need to adjust this slightly
    if flee_odds > 36:
        sub = flee_odds - 36
        p = ((flee_odds * 656) - sub)/65_536
    else:
        p = (flee_odds * 656)/65_536
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
                if i == 2:
                    p_add_curr_bait = p_turn * 13108/65536 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 13107/65536 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 1:
            for i in (2, 3, 4, 5):
                #includes bait reduction for end-of-round
                new_bait = i
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                if i == 2:
                    p_add_curr_bait = p_turn * 13108/65536 * (1 - p_flee)                
                elif i != 5:
                    p_add_curr_bait = p_turn * 13107/65536 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 26214/65536 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
                # print('Still working')
        elif amount_of_bait == 2:
            for i in (2, 3, 4):
                #includes bait reduction for end-of-round
                new_bait = i + 1
                # Get the probability of adding the current amount of bait
                if i == 2:
                    p_add_curr_bait = p_turn * 13108/65536 * (1 - p_flee)  
                elif i != 4:
                    p_add_curr_bait = p_turn * 13107/65536 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 39321/65536 * (1 - p_flee)
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, turns[1:], r, p_add_curr_bait, new_bait, True, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 3:
            for i in (2, 3):
                #includes bait reduction for end-of-round
                new_bait = i + 2
                # Get the probability of adding the current amount of bait
                if i != 3:
                    p_add_curr_bait = p_turn * 13108/65536 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 52428/65536 * (1 - p_flee)
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
        #IF a ball and the pokemon is NOT run with optimal pattern odds
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
    if (flee_rate >= 100 or (flee_rate == 75 and catch_rate < 90)):
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
    pretty_outputs(255, 25, 'MAGIKARP')
    pretty_outputs(60, 75, 'SEAKING')
    pretty_outputs(75, 75, 'PARASECT & VENOMOTH')
    pretty_outputs(90, 75, 'EXEGGCUTE')
    pretty_outputs(120, 75, 'NIDORINO, NIDORINA, & RHYHORN')
    pretty_outputs(190, 50, 'PARAS, VENONAT, PSYDUCK, SLOWPOKE, & DODUO')
    pretty_outputs(225, 50, 'GOLDEEN')
    pretty_outputs(235, 50, 'NIDORAN AND NIDORAN')
    pretty_outputs(255, 50, 'POLIWAG')

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

def get_best_pattern(balls, t='TLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL', p_flee=0.4503021240234375):
    # CHANSEY GANG (v4 Done)
    if (p_flee > 0.45):
        if balls == 1:
            return ('L', 0.08090370381673062, 0.9190962961832694)
        elif balls == 2:
            return ('LL', 0.12177830037861859, 0.8782216996213814)
        elif balls == 3:
            return ('LLL', 0.14242917994628063, 0.8575708200537194)
        elif balls == 4:
            return ('LLLL', 0.15286252639588732, 0.8471374736041127)
        elif balls == 5:
            return ('LLLLL', 0.15813371679631855, 0.8418662832036815)
        elif balls == 6:
            return ('LLLLLL', 0.16079685545195532, 0.8392031445480448)
        elif balls == 7:
            return('LLLLLLL', 0.1621423404298014, 0.8378576595701986)
        elif balls == 8:
            return ('TTLLLLTLLLL', 0.1681451513265395, 0.8318548486734605)
        elif balls == 9:
            return ('TTLLLTLLLLLL', 0.17324918696403283, 0.8267508130359672)
        elif balls == 10:
            return ('TTLLLLTLLLLLL', 0.17651584672595966, 0.8234841532740405)
        elif balls == 11:
            return ('TTLLLTLLTLLLLLL', 0.18010946874501638, 0.8198905312549837)
        elif balls == 12:
            return ('TTLLLTLLTLLLLTLLL', 0.18208555955666217, 0.8179144404433378)
        elif balls == 13:
            return ('TTLLLTLLTLLLTLLLLL', 0.18419954181650144, 0.8158004581834988)
        elif balls == 14:
            return ('TTLLLTLLTLLLTLLLLLL', 0.18576218468316105, 0.814237815316839)
        elif balls == 15:
            return ('TTLLLTLLTLLLTLLTLLLLL', 0.18669103301404127, 0.8133089669859586)
        elif balls == 16:
            return ('TTLLLTLLTLLLTLLTLLLLLL', 0.18774802736386503, 0.812251972636135)
        elif balls == 17:
            return ('TTLLLTLLTLLLTLLTLLLLTLLL', 0.18832412031643928, 0.8116758796835607)
        elif balls == 18:
            return ('TTLLLTLLTLLLTLLTLLLTLLLLL', 0.18892783340119906, 0.8110721665988008)
        elif balls == 19:
            return ('TTLLLTLLTLLLTLLTLLLTLLLLLL', 0.189379975122608, 0.810620024877392)
        elif balls == 20:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.18965153557123465, 0.8103484644287655)
        elif balls == 21:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.18995601605679852, 0.8100439839432014)
        elif balls == 22:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLLTLLL', 0.19012532960550482, 0.8098746703944952)
        elif balls == 23:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.19029819718067026, 0.8097018028193299)
        elif balls == 24:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.19042923931892092, 0.8095707606810789)
        elif balls == 25:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.19050864209773072, 0.8094913579022692)
        elif balls == 26:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.19059637431025278, 0.8094036256897474)
        elif balls == 27:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLTLLL', 0.1906460777326922, 0.8093539222673077)
        elif balls == 28:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.19069563145135943, 0.8093043685486405)
        elif balls == 29:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.19073360810883894, 0.809266391891161)
        elif balls == 30:
            return ('TTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.1907568152780696, 0.8092431847219304)
    # DRATINI
    elif (p_flee > 0.35):
        if balls == 1:
            return ('L', 0.08090370381673062, 0.9190962961832694)
        elif balls == 2:
            return ('LL', 0.1292365952582831, 0.870763404741717)
        elif balls == 3:
            return ('LLL', 0.1581112732383264, 0.8418887267616737)
        elif balls == 4:
            return ('LLLL', 0.17536136946853897, 0.824638630531461)
        elif balls == 5:
            return ('TTLLLLL', 0.19205777271881955, 0.8079422272811805)
        elif balls == 6:
            return ('TTLLLLLL', 0.2146631940922486, 0.7853368059077513)
        elif balls == 7:
            return ('TTLLTLLLLL', 0.2313178548879708, 0.768682145112029)
        elif balls == 8:
            return ('TTLLTLLLLLL', 0.24765183313852976, 0.7523481668614701)
        elif balls == 9:
            return ('TTLLTLLLTLLLL', 0.26007474552287985, 0.7399252544771202)
        elif balls == 10:
            return ('TTLLTLLLTLLLLL', 0.2716846104917178, 0.7283153895082821)
        elif balls == 11:
            return ('TTLLTLLLTLLLLLL', 0.2806832491675522, 0.7193167508324477)
        elif balls == 12:
            return ('TTLLTLLLTLLTLLLLL', 0.28940696810566574, 0.7105930318943343)
        elif balls == 13:
            return ('TTLLTLLLTLLTLLLLLL', 0.2960685097331115, 0.7039314902668885)
        elif balls == 14:
            return ('TTLLTLLLTLLTLLTLLLLL', 0.3015249071241963, 0.6984750928758039)
        elif balls == 15:
            return ('TTLLTLLLTLLTLLTLLLLLL', 0.3066124489191312, 0.6933875510808687)
        elif balls == 16:
            return ('TTLLTLLLTLLTLLTLLLTLLLL', 0.31049980676120653, 0.6895001932387935)
        elif balls == 17:
            return ('TTLLTLLLTLLTLLTLLTLLLLLL', 0.31413881022611706, 0.6858611897738829)
        elif balls == 18:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLLL', 0.3169547293391364, 0.6830452706608636)
        elif balls == 19:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.31959440904342107, 0.6804055909565789)
        elif balls == 20:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.32175301091863695, 0.6782469890813632)
        elif balls == 21:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLLLL', 0.3235244810730687, 0.6764755189269311)
        elif balls == 22:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLLLLL', 0.3250890606883454, 0.6749109393116546)
        elif balls == 23:
            return ('TTLLTLLLTLLTLLTLLTLLTLLLTLLTLLLLL', 0.3263097659496999, 0.6736902340503002)
        elif balls == 24:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLLLL', 0.3274648640093355, 0.6725351359906645)
        elif balls == 25:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLTLLLL', 0.3283470662158826, 0.6716529337841173)
        elif balls == 26: 
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLTLLLLLL', 0.3291717605138369, 0.6708282394861631)
        elif balls == 27:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLTLLLTLLLL', 0.32981459381452183, 0.6701854061854781)
        elif balls == 28:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.3303977707862832, 0.6696022292137168)
        elif balls == 29:
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.33088599127474816, 0.6691140087252518)
        elif balls == 30: #V4
            return ('TTLLTLLLTLLTLLTLLTLLLTLLTLLTLLTLLLTLLTLLLLL', 0.33128659690084766, 0.6687134030991523)
    # PARA-SEANAT
    elif (p_flee > 0.25):
        if balls == 1:
            return ('L', 0.08090370381673062, 0.9190962961832694)
        elif balls == 2:
            return ('LL', 0.13665427083033024, 0.8633457291696698)
        elif balls == 3:
            return ('LLL', 0.17507186576984787, 0.8249281342301521)
        elif balls == 4:
            return ('LLLL', 0.2015453472068496, 0.7984546527931504)
        elif balls == 5:
            return ('TTLLLLL', 0.22229923131359608, 0.7777007686864039)
        elif balls == 6:
            return ('TTLLLLLL', 0.2493182850599433, 0.7506817149400568)
        elif balls == 7:
            return ('TTLLLLTLLL', 0.2687232216585702, 0.7312767783414298)
        elif balls == 8:
            return ('TTLLTLLLLLL', 0.2873833936788264, 0.7126166063211736)
        elif balls == 9:
            return ('TTLLLTLLLLLL', 0.30287645244759065, 0.6971235475524092)
        elif balls == 10:
            return ('TTLLLTLLTLLLLL', 0.31552022421454523, 0.6844797757854546)
        elif balls == 11:
            return ('TTLLLTLLTLLLLLL', 0.32716657067459654, 0.6728334293254035)
        elif balls == 12:
            return ('TTLLTLLLTLLTLLLLL', 0.33591239211725055, 0.6640876078827493)
        elif balls == 13:
            return ('TTLLTLLLTLLTLLLLLL', 0.34437061683353776, 0.6556293831664624)
        elif balls == 14:
            return ('TTLLLTLLTLLLTLLLLLL', 0.35085000884451756, 0.6491499911554824)
        elif balls == 15:
            return ('TTLLTLLLTLLTLLTLLLLLL', 0.3566618126331179, 0.643338187366882)
        elif balls == 16:
            return ('TTLLTLLLTLLTLLLTLLLLLL', 0.3615332412039789, 0.6384667587960211)
        elif balls == 17:
            return ('TTLLTLLLTLLTLLTLLLTLLLLL', 0.3655874219133732, 0.6344125780866268)
        elif balls == 18:
            return ('TTLLTLLLTLLTLLLTLLTLLLLLL', 0.36925915054423125, 0.6307408494557687)
        elif balls == 19:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.37209344486897583, 0.6279065551310242)
        elif balls == 20:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.37476773977197614, 0.6252322602280238)
        elif balls == 21:
            return ('TTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.37678665345768014, 0.6232133465423199)
        elif balls == 22:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLLLL', 0.378684821430573, 0.6213151785694269)
        elif balls == 23:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLTLLLLLL', 0.3802350181811945, 0.6197649818188055)
        elif balls == 24:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLLLL', 0.3815274053133011, 0.6184725946866988)
        elif balls == 25:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.3826930124049491, 0.6173069875950509)
        elif balls == 26:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLL', 0.38360374456187146, 0.6163962554381286)
        elif balls == 27:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLLLLL', 0.38445658420759976, 0.6155434157924002)
        elif balls == 28:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.385103681837245, 0.614896318162755)
        elif balls == 29:
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLTLLLLLL', 0.3857113015844994, 0.6142886984155006)
        elif balls ==30: #V4
            return ('TTLLTLLLTLLTLLTLLLTLLTLLTLLLTLLTLLLTLLLLLL', 0.3862047205092316, 0.6137952794907684)
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
        print(pattern_odds_catch(pattern, 0, cr, fr))
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
    print("Para-Venoking VERIFICATION")
    #  input("Enter the name of the Pokemon you are inquiring about")
    #balls_only(45, 75)
    #all_best(45, 75, 5)
    #make_best_patterns()
    #input('FINI')
    
