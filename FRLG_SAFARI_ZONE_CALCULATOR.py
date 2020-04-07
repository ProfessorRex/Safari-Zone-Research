import math

'''
PLEASE DON'T JUDGE LAZY CODE
this is just for fun <3
'''

if __name__ == '__main__':
    print("GENERATION 3 SAFARI ZONE CALCULATOR")
    #  input("Enter the name of the Pokemon you are inquiring about")


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
    a = int(rate * 1.5 / 3)
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
    factor = int(100/1275 * rate)
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
    rate = int(100/1275 * rate)
    # OTHER STUFF TO DO - ROCKS
    if eating:
        # Divide flee rate by 4 if eating
        # based off a floored version of the flee factor / 4
        rate = int(rate/4)
    if rate < 2:
        # there is a bare minimum flee rate so bait cannot drop it below
        # 10% per turn (I think it applies even without bait will need to use
        # magikarp to test)
        rate = 2
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
    return result

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
    elif turn == 'T':
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
        print("If the Pokémon ever begins to 'watch carefully' refer to the lookup table and proceed as instructed.")



def all_pretty():
    #CHANSEY
    pretty_outputs(30, 125, 'CHANSEY')
    pretty_outputs(45, 125, 'DRAGONAIR, PINSIR, SCYTHER, TAUROS, & KANGASKHAN')
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

def best_patterns(balls, pattern='', r=3, catch_rate=45, flee_rate=125):
    def_balls = pattern.count('L')
    best_odds = 0
    # -1 because TL at the end is a useless simulation
    x = '0b' + '1' * (balls - def_balls - 1)
    max_range = int(x, base=2) + 1
    for i in range(0, max_range):
        curr_pattern = make_pattern(i, balls, pattern)
        odds = pattern_odds_catch(curr_pattern, r, catch_rate, flee_rate)
        if odds[0] > best_odds:
            best_pattern = curr_pattern
            best_odds = odds[0]
            best_fail = odds[1]
            best_i = i
    result = (i, best_pattern, best_odds, best_fail)
    print(result)

def make_best_patterns():
    print('getting 28')
    best_patterns(28, 'TLTLLLTLLTLLLTLLTLLLTLLTL', 3, 45, 100)
    print('getting 29')
    best_patterns(29, 'TLTLLLTLLTLLLTLLTLLLTLLTL', 3, 45, 100)
    print('getting 30')
    best_patterns(30, 'TLTLLLTLLTLLLTLLTLLLTLLTL', 3, 45, 100)

def get_best_pattern(balls, t='TLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL', p_flee=0.45):
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
            return ('LLLLLLL', 0.16222809267777477, 0.8377719073222252)
        elif balls == 8:
            return ('TLTLLLLLLL', 0.16439039173068648, 0.8356096082693136)
        elif balls == 9:
            return ('TLTLLTLLLLLL', 0.16928523510120777, 0.8307147648987923)
        elif balls == 10:
            return ('TLTLLLTLLLLLL', 0.17304200243813683, 0.8269579975618633)
        elif balls == 11:
            return ('TLTLLTLLLTLLLLL', 0.17555639400489573, 0.8244436059951044)
        elif balls == 12:
            return ('TLTLLTLLLTLLLLLL', 0.17805247986379613, 0.821947520136204)
        elif balls == 13:
            return ('TLTLLTLLLTLLTLLLLL', 0.17946473151486, 0.8205352684851401)
        elif balls == 14:
            return ('TLTLLTLLLTLLTLLLLLL', 0.18113105975015584, 0.8188689402498444)
        elif balls == 15:
            return ('TLTLLTLLLTLLTLLLLLLL', 0.1819831227767754, 0.8180168772232247)
        elif balls == 16:
            return ('TLTLLTLLLTLLTLLLTLLLLL', 0.18290603534976066, 0.8170939646502395)
        elif balls == 17:
            return ('TLTLLTLLLTLLTLLLTLLLLLL', 0.18361012782345376, 0.8163898721765465)
        elif balls == 18:
            return ('TLTLLTLLLTLLTLLLTLLTLLLLL', 0.18401456348694878, 0.8159854365130514)
        elif balls == 19:
            return ('TLTLLTLLLTLLTLLLTLLTLLLLLL', 0.1844885541202192, 0.815511445879781)
        elif balls == 20:
            return ('TLTLLTLLLTLLTLLLTLLTLLLLLLL', 0.18473277354618586, 0.8152672264538142)
        elif balls == 21:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.18499598100901493, 0.8150040189909852)
        elif balls == 22:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.18519675015443607, 0.8148032498455641)
        elif balls == 23:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.1853127968058429, 0.8146872031941571)
        elif balls == 24:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.18544807735885732, 0.8145519226411428)
        elif balls == 25:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLLL', 0.18551801387110115, 0.8144819861288989)
        elif balls == 26:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.18559330975920235, 0.8144066902407978)
        elif balls == 27:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.1856505727531093, 0.8143494272468909)
        elif balls == 28:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLL', 0.18568389746997177, 0.8143161025300283)
        elif balls == 29:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.1857225102010371, 0.8142774897989631)
        elif balls == 30:
            return ('TLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLLL', 0.18574253925759304, 0.8142574607424071)
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
            return ('LLLLL', 0.18566679417863463, 0.8143332058213654)
        elif balls == 6:
            return ('LLLLLL', 0.19182338467170354, 0.8081766153282965)
        elif balls == 7:
            return ('LLLLLLL', 0.19550140935924643, 0.8044985906407536)
        elif balls == 8:
            return ('TLTLLLLLLL', 0.20031230187380816, 0.7996876981261919)
        elif balls == 9:
            return ('TLTLLLTLLLLL', 0.20502792330201625, 0.7949720766979839)
        elif balls == 10:
            return ('TLTLLLTLLLLLL', 0.21043379286867947, 0.7895662071313205)
        elif balls == 11:
            return ('TLTLLLTLLLLLLL', 0.21361159516539302, 0.7863884048346069)
        elif balls == 12:
            return ('TLTLLLTLLTLLLLLL', 0.21631070022469712, 0.7836892997753029)
        elif balls == 13:
            return ('TLTLLLTLLTLLLLLLL', 0.21842011772174935, 0.7815798822782506)
        elif balls == 14:
            return ('TLTLLLTLLTLLLTLLLLL', 0.2199638553434019, 0.7800361446565982)
        elif balls == 15:
            return ('TLTLLLTLLTLLLTLLLLLL', 0.22148974643298036, 0.7785102535670196)
        elif balls == 16:
            return ('TLTLLLTLLTLLLTLLLLLLL', 0.2224279500815314, 0.7775720499184686)
        elif balls == 17:
            return ('TLTLLLTLLTLLLTLLTLLLLLL', 0.22321494650761117, 0.7767850534923889)
        elif balls == 18:
            return ('TLTLLLTLLTLLLTLLTLLLLLLL', 0.2238317717137413, 0.7761682282862586)
        elif balls == 19:
            return ('TLTLLLTLLTLLLTLLTLLLTLLLLL', 0.22428497472042278, 0.7757150252795773)
        elif balls == 20:
            return ('TLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.22472769338007836, 0.7752723066199217)
        elif balls == 21:
            return ('TLTLLLTLLTLLLTLLTLLLTLLLLLLL', 0.22500222847512008, 0.77499777152488)
        elif balls == 22:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.22523174496358384, 0.7747682550364162)
        elif balls == 23:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLLLLL', 0.22541333981764267, 0.7745866601823573)
        elif balls == 24:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLL', 0.22554396099944152, 0.7744560390005586)
        elif balls == 25:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.22567348750791535, 0.7743265124920846)
        elif balls == 26:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLLL', 0.22575382276197453, 0.7742461772380257)
        elif balls == 27:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLLLL', 0.22582072634367928, 0.7741792736563209)
        ################################
        elif balls -- 30:
            return ('TLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLLLLL', 0.2259496020706997, 0.7740503979293004)
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
