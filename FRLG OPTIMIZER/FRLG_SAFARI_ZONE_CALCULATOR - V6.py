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
    if bait > 0:
        factor = int(factor * 0.5 * bait)
    # Iff bait or rocks have been used the game has max & min values
    if (bait) and (factor < 3):
        # Minimum is 3 effectivley 38 Catch rate
        factor = 3
    if rock > 0:
        # Bait and balls stack
        factor = int(factor * 2 * rock)
    if (bait or rock) and (factor > 20):
        # Max is 20 which is a 255 catch rate
        factor = 20
    rate = int(factor * 1275/100)
    return (rate, factor)


def calculate_flee_rate(rate, angry=False, eating=False):
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
    elif angry:
        rate = rate * 2
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

def pattern_odds_catch(turns='L', r=0, catch_rate=45, flee_rate=125, baited=False):
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
    p_catch_baited = calculate_catch_rate(catch_rate, 0, 1)
    p_catch_unbaited = calculate_catch_rate(catch_rate, 0, 0)
    p_flee_angry = calculate_flee_rate(flee_rate, True, False)
    p_catch_baited_rocked = calculate_catch_rate(catch_rate, 1, 1)
    p_catch_rocked = calculate_catch_rate(catch_rate, 1, 0)
    result = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns, r, 1, 0, baited)
    return (result[0], result[1], turns)

def pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns, r, p_turn=1, amount_of_bait=0, baited=False, rocked=False, t=0):
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
    elif rocked:
        eating = False
        p_flee = p_flee_angry
        if baited:
            p_catch = p_catch_baited_rocked
        else:
            p_catch = p_catch_rocked
    else:
        eating = False
        p_flee = p_flee_watching
        if not baited:
            p_catch = p_catch_unbaited
    # If a ball was thrown get the odds of capture vs fleet
    if turn == 'L' and (eating or r == 0 or rocked):
        round_vals = odds_of_catch(p_turn, p_catch, p_flee)
        ##print(round_vals[1])
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        p_turn = round_vals[0]
        #MOVE TO NEXT TURN
        if(amount_of_bait > 0):
            amount_of_bait -= 1
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_turn, amount_of_bait, baited, rocked, t[:-1])
        p_success = p_success + round_vals[0]
        p_failure = p_failure + round_vals[1]
    # If a rock it to be thrown, run the probabilites of flee and add the rock flag
    elif (turn == 'R'):
        # add probability of fleeing on current turn
        p_failure = p_failure + (p_turn * p_flee)
        p_turn = p_turn * (1 - p_flee)
        amount_of_bait = 0
        rocked = True
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_turn, amount_of_bait, baited, rocked, t)       
        p_success = p_success + round_vals[0]
        p_failure = p_failure + round_vals[1]        

    # If bait is to be thrown run the probabilities for each amount of bait
    elif turn == 'T' and (eating or r == 0 or rocked or p_turn == 1):
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
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_add_curr_bait, new_bait, True, rocked, t)
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
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_add_curr_bait, new_bait, True, rocked, t)
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
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_add_curr_bait, new_bait, True, rocked, t)
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
                round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_add_curr_bait, new_bait, True, rocked, t)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        else:
            #includes bait reduction for end-of-round
            new_bait = 5
            # Get the probability of adding the current amount of bait
            p_add_curr_bait = p_turn * (1 - p_flee)
            round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, turns[1:], r, p_add_curr_bait, new_bait, True, rocked, t)
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
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, new_turns, r, p_turn, 0, baited, rocked, t)
        p_success = round_vals[0]
        p_failure = round_vals[1]
    elif (r == 2):
        #IF A BALL AND THE POKEMON IS NOT eating but r = balls after fail
        #remake pattern as Balls and change to no-repeat
        n_balls = turns.count('L')
        new_turns = 'L' * n_balls
        r = 0
        round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, new_turns, r, p_turn, 0, baited, rocked, t)
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
            round_vals = pattern_odds_catch_deep(p_flee_watching, p_flee_eating, p_catch_baited, p_catch_unbaited, p_flee_angry, p_catch_baited_rocked, p_catch_rocked, new_turns[0], r, p_turn, 0, baited, rocked, t)
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
    print(fleet_ub)
    print("Odds of fleeing per turn while not eating: " +
          str(round((fleet_ub * 100), 2)) + "%")
    print()
    print("Base flee rate: " + str(flee_rate))
    fleet = calculate_flee_rate(flee_rate, False, True)
    print(fleet)
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

def new_pats(t_balls, start_p='TT'):
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

def other_new_pats(t_balls, start_p='TT'):
    balls = t_balls - start_p.count('L')
    pats = []
    for x in range(0, balls-2):
        num = balls - x
        max_tll = int(num/1)
        min_tllll = int(num/3)
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
                        p_sum += 1
                        pat = pat + 'TL'
                    elif p == '1':
                        p_sum += 2
                        pat = pat + 'TLL'
                    elif p == '2':
                        p_sum += 3
                        pat = pat + 'TLLL'
                p_sum += x
                if p_sum == balls:
                    pat = pat + 'L' * x
                    pats.append(pat)
    pats = list(dict.fromkeys(pats))
    return pats

def new_best(balls, rock=False, pattern='', r=3, catch_rate=45, flee_rate=125, end_pat=""):
    best_odds = 0
    pats1 = new_pats(balls, pattern)
    pats2 = other_new_pats(balls,pattern)
    pats = list(set(pats1 + pats2))
    while (len(pats) % 8) != 0:
        pats.append('L')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        i = 0
        while len(pats) > i:
            futures = []
            for x in range (0,8):
                curr_pattern = pats[i + x]
                if rock:
                    curr_pattern = curr_pattern[:-end_pat.count("L")] + end_pat
                if curr_pattern.count("L") == balls:
                    future = executor.submit(pattern_odds_catch, curr_pattern, r, catch_rate, flee_rate)
                    futures.append(future)
            for f in concurrent.futures.as_completed(futures):
                odds = f.result()
                if odds[0] > best_odds:
                    best_pattern = odds[2]
                    best_odds = odds[0]
                    best_fail = odds[1]
                    best_i = x
            i = i + 8
    result = (best_pattern, best_odds, best_fail)
    return result

def get_best_pattern(balls, t='', p_flee=0.4503021240234375):
    result = read_pattern(p_flee, balls)
    return result

def calc_patterns(balls_left, rock=True, pattern='T', r=3, catch_rate=30, flee_rate=125, end_pattern=""):
    p_flee = calculate_flee_rate(flee_rate, False, False)
    for i in range(balls_left, 31):
        r=3
        if i > 31:
            #Read best pattern and use up to the second to last bait
            pattern = read_pattern(p_flee, i-1)[0]
            pattern = reduce_pattern(pattern)
        if(pattern == ''):
            T1 = new_best(i, False, '', r, catch_rate, flee_rate, '')
            best = T1[1]
            result = T1
            T2 = new_best(i, False, 'T', r, catch_rate, flee_rate, '')
            T3 = new_best(i, True, '', r, catch_rate, flee_rate, 'RL')
            T4 = new_best(i, True, 'T', r, catch_rate, flee_rate, 'RL')
            T5 = new_best(i, True, '', r, catch_rate, flee_rate, 'RLL')
            T6 = new_best(i, True, 'T', r, catch_rate, flee_rate, 'RLL')
            if best < T2[1]:
                best = T2[1]
                result = T2
            if best < T3[1]:
                best = T3[1]
                result = T3
            if best < T4[1]:
                best = T4[1]
                result = T4
            if best < T5[1]:
                best = T5[1]
                result = T5
            if best < T6[1]:
                best = T6[1]
                result = T6
        elif end_pat == "test":
            T1=new_best(i, True, pattern, r, catch_rate, flee_rate, 'RL')
            best = T1[1]
            result = T1            
            T2=new_best(i, True, pattern, r, catch_rate, flee_rate, 'RLL')
            if best < T2[1]:
                best = T2[1]
                result = T2            
        else:
            result = new_best(i, end_pattern.count('R') > 0, pattern, r, catch_rate, flee_rate, end_pat)
            
        write_pattern(p_flee, result)
        print(str(i) + " Calculcated!")

def read_pattern(p_flee, balls):
    f = open(str(p_flee)+".txt", "r")
    lines = f.readlines()
    f.close()
    line = lines[balls-1].rstrip()[1:-1].split(", ")
    result = [line[0][1:-1], float(line[1]), float(line[2])]
    return result
 
def write_pattern(p_flee, result):
    f = open(str(p_flee)+".txt", "a")
    f.write(str(result)+"\n")
    f.close()

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

def ternary (n):
    if n == 0:
        return '0'
    nums = []
    while n:
        n, r = divmod(n, 3)
        nums.append(str(r))
    return ''.join(reversed(nums))

if __name__ == '__main__':
    #print("GENERATION 3 SAFARI ZONE CALCULATOR")
    #input("PRESS ENTER TO BEGIN")
    #print("Para-Venoking VERIFICATION")
    #  input("Enter the name of the Pokemon you are inquiring about")
    #balls_only(45, 75)
    #all_best(45, 75, 5)
    #make_best_patterns()
    #input('FINI')
    #starting_ball = int(input("Enter Starting Ball"))
    #if(starting_ball != 0):
        #CR = int(input("Enter CR"))
        #FR = int(input("Enter FR"))
        #Starting_pat = input("enter starting pattern: ")
        #end_pat= input("enter end pattern: ")
        #calc_patterns(starting_ball, True, Starting_pat, 3, CR, FR, end_pat)
    pass