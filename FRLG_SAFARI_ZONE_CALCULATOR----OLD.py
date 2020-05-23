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
    # odds of a shake
    b = int(int('0xffff0', 16)/(int(math.sqrt(int(
             math.sqrt(int('0xff0000', 16)/a))))))
    if a >= 255:
        p = 1
    else:
        # odds of successful capture
        p = pow((b/65535), 4)
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


def multi_rounds(p_turn, p_catch, p_flee):
    '''
    mostly useless don't worry about it
    '''
    round_vals = odds_of_catch(p_turn, p_catch, p_flee)
    p_success = round_vals[1]
    p_failure = round_vals[2]
    while round_vals[1] >= 0.0000000001:
        round_vals = odds_of_catch(round_vals[0], p_catch, p_flee)
        p_success += round_vals[1]
        p_failure += round_vals[2]
    p_failure += round_vals[0]
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


def one_bait_catch(catch_rate, flee_rate):
    '''
    Odds of capture starting with one bait and subsequent balls
    Doesn't take into account running out of balls (Not super optimal)
    IGNORE CODE PLZ NOT PRETTY
    '''
    p_flee = calculate_flee_rate(flee_rate, False, False)
    p_catch_bait = calculate_catch_rate(catch_rate, 0, 1)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    p_failure = p_flee
    p_success = 0
    # Throwing the bait will grant between 2-6 turns of "eating"
    for i in range(1, 6):
        round_vals = odds_of_catch((1 - p_flee) * 0.2, p_catch_bait,
                                   p_flee_eating)
        p_success += round_vals[1]
        p_failure += round_vals[2]
        for i in range(0, i):
            round_vals = odds_of_catch(round_vals[0], p_catch_bait,
                                       p_flee_eating)
            p_success += round_vals[1]
            p_failure += round_vals[2]
        other_rounds = multi_rounds(round_vals[0], p_catch_bait,
                                    p_flee)
        p_success += other_rounds[0]
        p_failure += other_rounds[1]
    return(p_success, p_failure)


def bait_until_stop(p_turn, catch_rate, flee_rate):
    '''Odds of catching before bait wears off'''
    p_flee = calculate_flee_rate(flee_rate, False, False)
    p_catch_bait = calculate_catch_rate(catch_rate, 0, 1)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    p_failure = p_flee * p_turn
    p_success = 0
    p_continue = 0
    # Throwing the bait will grant between 2-6 turns of "eating"
    for i in range(1, 6):
        round_vals = odds_of_catch((p_turn - p_flee * p_turn) * 0.2,
                                   p_catch_bait, p_flee_eating)
        p_success += round_vals[1]
        p_failure += round_vals[2]
        for i in range(0, i):
            round_vals = odds_of_catch(round_vals[0], p_catch_bait,
                                       p_flee_eating)
            p_success += round_vals[1]
            p_failure += round_vals[2]
        p_continue += round_vals[0]
    return (p_continue, p_success, p_failure)


def bait_n_ball_catch(catch_rate, flee_rate):
    '''Odds of capture starting with one bait followed
    by balls and baiting again when eating stops'''
    round_vals = bait_until_stop(1, catch_rate, flee_rate)
    p_success = round_vals[1]
    p_failure = round_vals[2]
    while round_vals[0] > 0.000001:
        round_vals = bait_until_stop(round_vals[0], catch_rate, flee_rate)
        p_success += round_vals[1]
        p_failure += round_vals[2]
    return(p_success, p_failure)


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


def bait_ball_ball(catch_rate, flee_rate):
    '''ALGORITHM: BAIT BALL BALL BAIT BALL BALL etc...'''
    p_flee = calculate_flee_rate(flee_rate, False, False)
    p_catch_bait = calculate_catch_rate(catch_rate, 0, 1)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    # TURN 0 - BAIT
    p_continue = 1 - p_flee
    p_success = 0
    p_failure = p_flee
    curr_round = 1
    # Repeat until you run out of balls
    while curr_round < 16:
        # BALLL 1
        round_vals = odds_of_catch(p_continue, p_catch_bait, p_flee_eating)
        p_continue = round_vals[0]
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        # BALL 2
        round_vals = odds_of_catch(p_continue, p_catch_bait, p_flee_eating)
        p_continue = round_vals[0]
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        # BAIT
        # Each turn the odds of a pokemon watching is based off of the odds
        # that the last bait was a 2 x the odds all other bait so far was a 2
        odds_to_watch = 0.2*(1/curr_round)
        p_continue_old = p_continue
        p_continue = ((1-odds_to_watch)*(p_continue * (1 - p_flee_eating)) +
                      (odds_to_watch)*(p_continue * (1 - p_flee)))
        p_failure = p_failure + (p_continue_old - p_continue)
        curr_round += 1
    p_failure += p_continue
    return(p_success, p_failure)


def bait_ball_bait_ball(catch_rate, flee_rate):
    '''ALGORITHM: BAIT BALL BAIT BALL BALL etc...'''
    p_flee = calculate_flee_rate(flee_rate, False, False)
    p_catch_bait = calculate_catch_rate(catch_rate, 0, 1)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    # TURN 0 - BAIT
    p_continue = 1 - p_flee
    p_success = 0
    p_failure = p_flee
    curr_round = 0
    balls_thrown = 0
    while balls_thrown < 30:
        # BALLL 1
        round_vals = odds_of_catch(p_continue, p_catch_bait, p_flee_eating)
        p_continue = round_vals[0]
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        balls_thrown += 1
        if(curr_round != 0 and balls_thrown < 30):
            # BALL 2
            round_vals = odds_of_catch(p_continue, p_catch_bait, p_flee_eating)
            p_continue = round_vals[0]
            p_success = p_success + round_vals[1]
            p_failure = p_failure + round_vals[2]
            balls_thrown += 1
        # BAIT
        if curr_round == 0:
            odds_to_watch = 0
        else:
            odds_to_watch = pow(2, curr_round - 1)/(pow(5, curr_round + 1))
        p_continue_old = p_continue * (1 - odds_to_watch)
        # IF IT STARTS WATCHING WE START ALL OVER AGAIN AS THOUGH IT WAS NEW
        watching_round = bait_ball_bait_ball_2(catch_rate, flee_rate,
                                               p_continue * odds_to_watch,
                                               balls_thrown)
        p_success = p_success + watching_round[0]
        p_failure = p_failure + watching_round[1]
        p_continue = (1-odds_to_watch)*(p_continue * (1 - p_flee_eating))
        p_failure = p_failure + (p_continue_old - p_continue)
        curr_round += 1
    p_failure = p_failure + p_continue
    return(p_success, p_failure)


def bait_ball_bait_ball_2(catch_rate, flee_rate, p_turn=1, balls_thrown=0):
    '''
    NON-RECURSIVE VERSION of bait_ball_bait_ball
    ALGORITHM: BAIT BALL BAIT BALL BALL etc...'''
    p_flee = calculate_flee_rate(flee_rate, False, False)
    p_catch_bait = calculate_catch_rate(catch_rate, 0, 1)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    # TURN 0 - BAIT
    p_continue = (1 - p_flee) * p_turn
    p_success = 0
    p_failure = p_flee * p_turn
    curr_round = 0
    while balls_thrown < 30:
        # BALL 1
        round_vals = odds_of_catch(p_continue, p_catch_bait, p_flee_eating)
        p_continue = round_vals[0]
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        balls_thrown += 1
        if(curr_round != 0 and balls_thrown < 30):
            # BALL 2
            round_vals = odds_of_catch(p_continue, p_catch_bait, p_flee_eating)
            p_continue = round_vals[0]
            p_success = p_success + round_vals[1]
            p_failure = p_failure + round_vals[2]
            balls_thrown += 1
        # BAIT
        if curr_round == 0:
            odds_to_watch = 0
        else:
            odds_to_watch = pow(3, curr_round - 1)/(pow(5, curr_round + 1))
        p_continue_old = p_continue
        p_continue = ((1-odds_to_watch)*(p_continue * (1 - p_flee_eating)) +
                      (odds_to_watch)*(p_continue * (1 - p_flee)))
        p_failure = p_failure + (p_continue_old - p_continue)
        curr_round += 1
    p_failure += p_continue
    return(p_success, p_failure)


def pretty_outputs(catch_rate, flee_rate, name):
    print("OUTPUT FOR " + name)
    print("Base catch rate: " + str(catch_rate))
    factor = get_catch_factor(catch_rate, 0, 0)
    print("Base catch factor: " + str(factor[1]))
    print("Modified catch rate: " + str(factor[0]))
    p_catch = calculate_catch_rate(catch_rate, 0, 0)
    print("Odds of capture per ball: " + str(p_catch * 100)[:7] + "%")
    print()
    print("Base catch rate: " + str(catch_rate))
    factor = get_catch_factor(catch_rate, 0, 1)
    print("Catch factor after bait: " + str(factor[1]))
    print("Modified catch rate after bait: " + str(factor[0]))
    p_catch = calculate_catch_rate(catch_rate, 0, 1)
    print("Odds of capture per ball after bait: " +
          str(p_catch * 100)[:7] + "%")
    print()
    print("Base flee rate: " + str(flee_rate))
    fleet = calculate_flee_rate(flee_rate, False, False)
    print("Odds of fleeing per turn while not eating: " +
          str(fleet * 100)[:7] + "%")
    print()
    print("Base flee rate: " + str(flee_rate))
    fleet = calculate_flee_rate(flee_rate, False, True)
    print("Odds of fleeing per turn while eating: " +
          str(fleet * 100)[:7] + "%")
    print('----------------------------------------------------')
    print("THE FOLLOWING ODDS ARE PER ENCOUNTER - NOT PER BALL")
    print('----------------------------------------------------')
    odds = balls_only_catch(catch_rate, flee_rate)
    print("Odds of capture with balls only and no bait: " +
          str(odds[0] * 100)[:7] + "%")
    odds = one_bait_catch(catch_rate, flee_rate)
    print("Odds of capture with one bait followed by only balls: " +
          str(odds[0] * 100)[:7] + "%")
    odds = bait_n_ball_catch(catch_rate, flee_rate)
    print("Odds of capture with one bait followed by balls until")
    print("the Pokemon stops eating where more bait is thrown: " +
          str(odds[0] * 100)[:7] + "%")
    odds = bait_ball_ball(catch_rate, flee_rate)
    print("Odds of capture with a pattern of (bait, ball, ball) repeating: " +
          str(odds[0] * 100)[:7] + "%")
    print()
    print("FOR BEST RESULTS THE FOLLOWING PATTERNS")
    print("SHOULD BE RESTARTED IF THE POKEMON EVER 'WATCHES CAREFULLY'")
    print()
    odds = bait_ball_bait_ball(catch_rate, flee_rate)
    print("Odds of capture with the pattern (Bait, Ball) -> ")
    print("(Bait, Ball, Ball) repeating: " + str(odds[0] * 100)[:7] + "%")
    print()
    odds = pattern_odds_catch_hard(catch_rate, flee_rate,
                                   'TLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLTLLTLLLL')
    print("Odds of capture with a pattern of (Bait, Ball) ->")
    print("(Bait, Ball, Ball, Ball, Bait, Ball, Ball) Repeating: " +
          str(odds[0] * 100)[:7] + "%")

def pattern_odds_catch_hard(catch_rate, flee_rate, turns, p_turn=1,
                            amount_of_bait=0, baited=False):
    '''
    Hard code of patterns (ONLY USED FOR ROUGH ESTIMATE!)
    catch_rate -> INT (Base catch rate of the pokemon)
    flee_rate -> INT (Base flee rate of the pokemon)
    p_turn -> float <= 1 (the odds of the current turn occuring)
    turns -> list of moves ('R' Rock, 'T' Bait. 'L' Ball)
    amount_of_bait -> int 0 to 6 (Amount of bait left at the start of the turn)
    RETURN
    p_success -> probability of catching the pokemon using the pattern of turns
    p_failure -> probability of failing the capture
    '''
    if len(turns) > 0 and p_turn > 0.000001:
        turn = turns[0]
    else:
        return (0, 0)
    # Get catch rates and flee rates
    p_flee_watching = calculate_flee_rate(flee_rate, False, False)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    p_catch = calculate_catch_rate(catch_rate, 0, 1)
    p_catch_unbaited = calculate_catch_rate(catch_rate, 0, 0)
    p_success = 0
    p_failure = 0
    # Cycle through the pattern of turns until there are no turns left
    # OPTIMIALLY THE PATTERN WILL UTILIZE ALL 30 BALLS
    # DETERMINE IF THE POKEMON IS EATING
    if amount_of_bait > 0:
        eating = True
        p_flee = p_flee_eating
        baited = True
        # # DONT reduce the amount of bait for the next turn YET YOU TARD

    else:
        eating = False
        p_flee = p_flee_watching
        if not baited:
            p_catch = p_catch_unbaited
    # If a ball was thrown get the odds of capture vs fleet
    if turn == 'L':
        round_vals = odds_of_catch(p_turn, p_catch, p_flee)
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        p_turn = round_vals[0]
        if(amount_of_bait > 0):
            amount_of_bait -= 1
        new_turns = turns[1:]
        round_vals = pattern_odds_catch_hard(catch_rate, flee_rate, new_turns,
                                             p_turn, amount_of_bait, baited)
        p_success = p_success + round_vals[0]
        p_failure = p_failure + round_vals[1]
        # If a bait is thrown run the probabilities for each amount of bait
    elif turn == 'T':
        # add probability of fleeing on current turn
        p_failure = p_failure + (p_turn * p_flee)
        if amount_of_bait <= 0:
            for i in range(2, 7):
                new_bait = add_bait(i, amount_of_bait)
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                round_vals = pattern_odds_catch_hard(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait, new_bait,
                                                     True)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 1:
            for i in range(2, 6):
                new_bait = add_bait(i, amount_of_bait - 1)
                # print(new_bait)
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                round_vals = pattern_odds_catch_hard(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait, new_bait,
                                                     True)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 2:
            for i in range(2, 6):
                new_bait = add_bait(i, amount_of_bait - 1)
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                if i < 5:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.4 * (1 - p_flee)
                round_vals = pattern_odds_catch_hard(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait,
                                                     new_bait, True)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 3:
            for i in range(2, 5):
                new_bait = add_bait(i, amount_of_bait - 1)
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                if i < 4:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.6 * (1 - p_flee)
                round_vals = pattern_odds_catch_hard(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait,
                                                     new_bait, True)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 4:
                for i in range(2, 4):
                    new_bait = add_bait(i, amount_of_bait - 1)
                    # Get the probability of adding the current amount of bait
                    # Multiplied by the odds of not fleeing
                    if i < 3:
                        p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                    else:
                        p_add_curr_bait = p_turn * 0.8 * (1 - p_flee)
                    round_vals = pattern_odds_catch_hard(catch_rate, flee_rate,
                                                         turns[1:],
                                                         p_add_curr_bait,
                                                         new_bait, True)
                    p_success = p_success + round_vals[0]
                    p_failure = p_failure + round_vals[1]
        else:
            new_bait = add_bait(2, amount_of_bait - 1)
            # Get the probability of adding the current amount of bait
            # Multiplied by the odds of not fleeing
            p_add_curr_bait = p_turn * (1 - p_flee)
            round_vals = pattern_odds_catch_hard(catch_rate, flee_rate,
                                                 turns[1:], p_add_curr_bait,
                                                 new_bait, True)
            p_success = p_success + round_vals[0]
            p_failure = p_failure + round_vals[1]
    return (p_success, p_failure,)


def pattern_odds_catch_easy(catch_rate, flee_rate, turns, p_turn=1,
                            amount_of_bait=0, baited=False, big_turns=0):
    '''
    catch_rate -> INT (Base catch rate of the pokemon)
    flee_rate -> INT (Base flee rate of the pokemon)
    p_turn -> float <= 1 (the odds of the current turn occuring)
    turns -> String ('R' Rock, 'T' Bait. 'L' Ball) ex 'TLTLLLTLL'
    amount_of_bait -> int 0 to 6 (Amount of bait left at the start of the turn)
    baited -> default is false but should be true if any bait has been thrown
    big_turns -> DO NOT USE, for bringing estimated odds to lower levels
    RETURN
    p_success -> probability of catching the pokemon ising the pattern of turns
    p_failure -> probability of failing the capture
    '''
    if len(turns) > 0:
        turn = turns[0]
    else:
        return (0, 0)
    if big_turns == 0:
        big_turns = pattern_odds_catch_hard(catch_rate, flee_rate, turns,
                                            1, 0, baited)
    # Get catch rates and flee rates
    p_flee_watching = calculate_flee_rate(flee_rate, False, False)
    p_flee_eating = calculate_flee_rate(flee_rate, False, True)
    p_catch = calculate_catch_rate(catch_rate, 0, 1)
    p_catch_unbaited = calculate_catch_rate(catch_rate, 0, 0)
    p_success = 0
    p_failure = 0
    # Cycle through the pattern of turns until there are no turns left
    # OPTIMIALLY THE PATTERN WILL UTILIZE ALL 30 BALLS
    # DETERMINE IF THE POKEMON IS EATING
    if amount_of_bait > 0:
        eating = True
        p_flee = p_flee_eating
        baited = True   
        # # DONT reduce the amount of bait for the next turn YET YOU TARD

    else:
        eating = False
        p_flee = p_flee_watching
        if not baited:
            p_catch = p_catch_unbaited
    # If a ball was thrown get the odds of capture vs fleet
    if turn == 'L' and eating:
        round_vals = odds_of_catch(p_turn, p_catch, p_flee)
        ##print(round_vals[1])
        p_success = p_success + round_vals[1]
        p_failure = p_failure + round_vals[2]
        p_turn = round_vals[0]
        #MOVE TO NEXT TURN
        if(amount_of_bait > 0):
            amount_of_bait -= 1
        new_turns = turns[1:]
        round_vals = pattern_odds_catch_easy(catch_rate, flee_rate, new_turns,
                                             p_turn, amount_of_bait,
                                             baited, big_turns)
        p_success = p_success + round_vals[0]
        p_failure = p_failure + round_vals[1]
        # If bait is to be thrown run the probabilities for each amount of bait
    elif turn == 'T':
        # add probability of fleeing on current turn
        p_failure = p_failure + (p_turn * p_flee)
        if amount_of_bait <= 0:
            for i in range(2, 7):
                new_bait = add_bait(i, amount_of_bait)
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                round_vals = pattern_odds_catch_easy(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait,
                                                     new_bait, True, big_turns)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 1:
            for i in range(2, 6):
                new_bait = add_bait(i, amount_of_bait - 1)
                # print(new_bait)
                # Get the probability of adding the current amount of bait
                # Multiplied by the odds of not fleeing
                if i < 5:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.4 * (1 - p_flee)
                round_vals = pattern_odds_catch_easy(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait,
                                                     new_bait, True, big_turns)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
                # print('Still working')
        elif amount_of_bait == 2:
            for i in range(2, 5):
                new_bait = add_bait(i, amount_of_bait - 1)
                # Get the probability of adding the current amount of bait
                if i < 4:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.6 * (1 - p_flee)
                round_vals = pattern_odds_catch_easy(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait,
                                                     new_bait, True, big_turns)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        elif amount_of_bait == 3:
            for i in range(2, 4):
                new_bait = add_bait(i, amount_of_bait - 1)
                # Get the probability of adding the current amount of bait
                if i < 3:
                    p_add_curr_bait = p_turn * 0.2 * (1 - p_flee)
                else:
                    p_add_curr_bait = p_turn * 0.8 * (1 - p_flee)
                round_vals = pattern_odds_catch_easy(catch_rate, flee_rate,
                                                     turns[1:],
                                                     p_add_curr_bait,
                                                     new_bait, True, big_turns)
                p_success = p_success + round_vals[0]
                p_failure = p_failure + round_vals[1]
        else:
            new_bait = add_bait(2, amount_of_bait - 1)
            # Get the probability of adding the current amount of bait
            p_add_curr_bait = p_turn * (1 - p_flee)
            round_vals = pattern_odds_catch_easy(catch_rate, flee_rate,
                                                 turns[1:], p_add_curr_bait,
                                                 new_bait, True, big_turns)
            p_success = p_success + round_vals[0]
            p_failure = p_failure + round_vals[1]
            # print('Still working')
    else:
        # IF A BALL, BUT THE POKEMON IS NOT EATING START THE PATTERN AGAIN
        # value pulled from the estimated odds from odds_pattern_hard x
        # odds of current turn
        round_vals = big_turns
        p_success = p_success + (round_vals[0] * p_turn)
        p_failure = p_failure + (round_vals[1] * p_turn)
    return (p_success, p_failure)

'''
USEFUL RAM ADDRESSES (FR)
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