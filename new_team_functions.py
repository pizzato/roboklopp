import pandas as pd
import random
from new_team_config import MAP_POS_NUM, MAP_NUM_POS
import itertools
from functions import eval_team


def pick(df: pd.DataFrame, weights: str, cost: str, budget: int, positions: dict, team_budget: dict):
    """
    Picks players from a dataframe using the weights and under a cost envelope
    df: DataFrame
    weights: weight column name
    cost: cost column name
    budget: total budget to use
    positions: dict with {position: number of players to pick}
    team_budget: dict with {teams: number of players we can still select from teams}
  """
    df.copy()
    positions = positions.copy()
    team_budget = team_budget.copy()

    n_picks = sum(positions.values())
    teams_left = {code for code, val in team_budget.items() if val > 0}
    positions_left = {MAP_POS_NUM[pos] for pos, val in positions.items() if val > 0}

    # filter by position left to pick
    df = df[df.element_type.isin(positions_left)]

    # filter out teams we exhausted the pick
    df = df[df.team_code.isin(teams_left)]

    # filter out players with higher cost
    df = df[df.now_cost <= budget]

    if len(df) == 0:
        return None

    player = df.sample(n=1, weights=weights)
    df = df.drop(player.index, axis=0)
    positions[MAP_NUM_POS[int(player.element_type)]] -= 1
    team_budget[int(player.team_code)] -= 1
    budget -= int(player.now_cost)

    n_picks -= 1

    if n_picks == 0:
        return pd.DataFrame(player)
    elif n_picks > 0:
        sel = None
        for i in range(20):  # try 20X at most
            sel = pick(df=df, weights=weights, cost=cost, budget=budget, positions=positions, team_budget=team_budget)
            if sel is not None:
                break

        if sel is None:
            return None  # pd.DataFrame(player)
        else:
            return pd.concat([pd.DataFrame(player), sel])


def get_squad_prod(df, pick_group_order, pick_groups_config, team_budget, extra_budget=0, top_n=5, ndraws_per_group=10):
    df = df.copy()
    groups_picked = {}

    # todo: this needs changing so it picks groups for one squad that doesnt have the same player twice

    for pick_group in pick_group_order:

        selections = []

        group_budget = pick_groups_config[pick_group]['budget']
        for i in range(ndraws_per_group):

            sel_ = pick(df=df,
                        weights='w_' + pick_group,
                        cost="now_cost",
                        budget=group_budget + extra_budget,
                        positions=pick_groups_config[pick_group]['players'],
                        team_budget=team_budget)

            if sel_ is not None:
                selections.append(sel_)

        selections = sorted(
            [(1 - sel['w_' + pick_group].mean(), group_budget - sel.now_cost.sum(), random.random(), sel) for sel
             in selections])

        extra_budget = selections[0][1]
        select_top_n = [_s[3] for _s in selections[:top_n]]

        print('{}: All extra budgets:'.format(pick_group), [_s[1] for _s in selections[:top_n]])

        groups_picked[pick_group] = select_top_n

        # full_squad = pd.concat([full_squad, select_top])
        # full_squad = select_top if full_squad is None else pd.concat([full_squad, select_top])
    return groups_picked


def combine_and_pick_top(comb_squad, by_order, top_n=10):
    prod_groups = list(itertools.product(*comb_squad.values()))
    prod_squads = [pd.concat(pg) for pg in prod_groups]
    eval_squads = pd.DataFrame([eval_team(sq) for sq in prod_squads])
    top_squad_indices = eval_squads.sort_values(by=by_order, ascending=False).head(top_n).index

    top_squads = [prod_squads[ind_] for ind_ in top_squad_indices]
    return top_squads
