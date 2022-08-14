import streamlit as st

BUDGET = 1000
MAP_POS_NUM = {'Goalkeeper': 1, 'Defender': 2, 'Midfielder': 3, 'Forward': 4}
MAP_NUM_POS = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}
MAX_POS = {'Goalkeeper': 2, 'Defender': 5, 'Midfielder': 5, 'Forward': 3}
MAX_PLAYERS = 15
WEIGHT_FOR_COST_SIMILARITY_IN_GROUPS = 50

pick_groups_default = {
    "Tier 1": dict(
        players={'Midfielder': 2},
        budget=250,
        weight_func=dict(add=dict(now_cost=10, total_points=10, team_strength_attack=1, selected_by_percent=10))),
    "Tier 2": dict(
        players={'Forward': 3},
        budget=250,
        weight_func=dict(add=dict(now_cost=2, total_points=5, team_strength_attack=1, selected_by_percent=10))),
    "Tier 3": dict(
        players={'Goalkeeper': 1, 'Defender': 3, "Midfielder": 2},
        budget=315,
        weight_func=dict(
            add=dict(now_cost=1, total_points=3, team_strength_overall=-2, team_strength_defence=1,
                     selected_by_percent=10))),
    "Tier 4": dict(
        players={'Goalkeeper': 1, 'Defender': 2, "Midfielder": 1},
        budget=185,
        weight_func=dict(add=dict(now_cost=-5, total_points=3, team_strength_overall=1, selected_by_percent=10)))
}


def draw_config(pick_groups=None, where=st.sidebar):
    if pick_groups is None:
        pick_groups = pick_groups_default

    where.header("Player types configuration")
    tabs = where.tabs(pick_groups.keys())

    # totals_pos = {pos: sum([pick_groups[k]['players'].get(pos, 0) for k in pick_groups]) for pos in MAP_POS_NUM}
    all_weights = set([w for k in pick_groups for w in pick_groups[k]['weight_func']['add']])

    for t, k in zip(tabs, pick_groups.keys()):
        # t.subheader(k+" selection of players")
        c1, c2 = t.columns([2, 1])

        pick_groups[k]['budget'] = c1.slider("Budget", value=pick_groups[k]['budget'], min_value=0, max_value=1000,
                                             step=5, key="{}_{}".format(k, 'budget'))

        total_budget = sum([pick_groups[k_]['budget'] for k_ in pick_groups])
        if total_budget > BUDGET:
            c2.error("Max is {}".format(BUDGET))
        else:
            c2.slider("Total", value=total_budget, max_value=BUDGET, step=1,
                      key="{}_{}".format(k, 'total_budget'), disabled=True)

        for pos in MAP_POS_NUM.keys():
            pick_groups[k]['players'][pos] = c1.slider(pos, value=pick_groups[k]['players'].get(pos, 0), min_value=0,
                                                       max_value=MAX_POS[pos], step=1, key="{}_{}".format(k, pos))

        totals_pos = {pos: sum([pick_groups[k]['players'].get(pos, 0) for k in pick_groups]) for pos in MAP_POS_NUM}
        for pos in MAP_POS_NUM.keys():
            if totals_pos[pos] > MAX_POS[pos]:
                c2.error("Total: {} > {}".format(totals_pos[pos], MAX_POS[pos]))
            else:
                c2.slider("Total", value=totals_pos[pos], max_value=MAX_POS[pos], step=1,
                          key="{}_{}_{}".format(k, pos, 'total'), disabled=True, )

        t.write("Weights")
        for w in all_weights:
            pick_groups[k]['weight_func']['add'][w] = t.slider(w, value=pick_groups[k]['weight_func']['add'].get(w, 0),
                                                               min_value=0, max_value=10, step=1,
                                                               key="{}_{}_{}".format(k, 'weight', w))

    return pick_groups


def _test():
    pg = draw_config(pick_groups=pick_groups_default)

    total_players = sum([pg[k]['players'].get(pos, 0) for k in pg for pos in MAP_POS_NUM])
    assert total_players == MAX_PLAYERS, "Total players must be {}".format(MAX_PLAYERS)


if __name__ == "__main__":
    _test()
