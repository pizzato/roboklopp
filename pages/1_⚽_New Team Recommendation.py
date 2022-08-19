import streamlit as st
from fpldata import FPLData
from get_data import get_data
import pulp

# Team recommendation with Linear Programming based on https://statnamara.wordpress.com/2021/02/05/finding-the-best-lazy-fantasy-football-team-using-pulp-in-python/

st.set_page_config(page_title=None, page_icon='images/roboklopp_eye.jpeg', layout="wide", initial_sidebar_state="auto", menu_items=None)

PHOTO_URL = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{}.png"
player_columns = ['type_name', 'web_name', 'full_name', 'now_cost', 'total_points', 'ep_next', 'selected_by_percent', 'bonus', 'dreamteam_count', 'element_type']
BUDGET = 1000
MIN_PLAYER_COST = 45
map_pos_num = {'Goalkeeper': 1, 'Defender': 2, 'Midfielder': 3, 'Forward': 4}
map_num_pos = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}

#todo: still missing: add team_budget (players per team)


def main():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image('images/roboklopp1.jpeg')

    with col2:
        st.markdown("""
                 # Robo Klopp presents: 

                 ## _New Team Selection_

                 ---
                 "humans coaches are overrated" -- Robo Klopp   
             """)

    fpl = FPLData(convert_to_dataframes=True)

    _, _, df_elements, _, _ = get_data(fpl)

    df_elements['photo_url'] = df_elements['code'].apply(lambda x: PHOTO_URL.format(x))

    df_elements.selected_by_percent = df_elements.selected_by_percent.astype(float)
    df_elements.ep_next = df_elements.ep_next.astype(float)

    df_elements.now_cost = df_elements.now_cost.astype(float)

    df_elements = df_elements.set_index("code")
    other_columns = df_elements.columns.difference(player_columns).to_list()

    # Configurations for players
    squad_total_players = 15
    subs_total_players = 4
    lineup_total_players = 11

    squad_budget = BUDGET
    subs_budget = MIN_PLAYER_COST * subs_total_players
    subs_budget = st.sidebar.slider("Budget for Substitutes", min_value=subs_budget,
                            max_value=squad_budget - MIN_PLAYER_COST * lineup_total_players, value=subs_budget)
    lineup_budget = squad_budget - subs_budget

    squad_players = {'Goalkeeper': 2, 'Defender': 5, 'Midfielder': 5, 'Forward': 3}
    lineup_minmax = {'Goalkeeper': (1, 1), 'Defender': (3, 5), 'Midfielder': (3, 5), 'Forward': (1, 3)}

    # team = solve_lp(df_elements, squad_budget, lineup_budget, subs_budget, squad_total_players, lineup_total_players, subs_total_players, squad_players, subs_players, lineup_players)

    lineup = solve_group(df=df_elements,
                         budget=lineup_budget,
                         total_players=lineup_total_players,
                         players_minmax=lineup_minmax,
                         group_name='Main Lineup')
    if lineup is None:
        st.write("No subs found")
        return

    df_lineup = df_elements.loc[lineup]

    st.markdown("### Line Up")

    cols = st.columns(len(df_lineup))
    for i, col in enumerate(cols):
        with col:
            st.image(df_lineup.iloc[i].photo_url)
            st.markdown("<div style='writing-mode: vertical-rl;'>{name}</div>".format(name=df_lineup.iloc[i].web_name),
                        unsafe_allow_html=True)

    st.dataframe(df_lineup[player_columns+other_columns].sort_values(by=['element_type', 'total_points'], ascending=False))


    #count how many players are in each position in df_lineup
    _df_lineup_pos = df_lineup.groupby('element_type').count()
    _df_lineup_pos.index = _df_lineup_pos.index.map(map_num_pos)

    lineup_pos = _df_lineup_pos['type_name'].to_dict()

    lineup_final_budget = sum(df_lineup.now_cost)
    subs_minmax = {pos:(squad_players[pos]-_pos_lineup, squad_players[pos]-_pos_lineup) for pos, _pos_lineup in lineup_pos.items()}

    subs = solve_group(df=df_elements.loc[df_elements.index.difference(lineup)],
                       budget=squad_budget - lineup_final_budget,
                       total_players=subs_total_players,
                       players_minmax=subs_minmax,
                       group_name='Substitutes')

    if subs is None:
        st.write("No subs found")
        return

    df_subs = df_elements.loc[subs]

    st.markdown("### Substitutes")

    cols = st.columns(len(df_lineup))
    for i, col in enumerate(cols):
        if i >= len(df_subs):
            break
        with col:
            st.image(df_subs.iloc[i].photo_url)
            st.markdown("<div style='writing-mode: vertical-rl;'>{name}</div>".format(name=df_subs.iloc[i].web_name),
                        unsafe_allow_html=True)


    st.dataframe(df_subs[player_columns + other_columns].sort_values(by=['element_type', 'total_points'], ascending=False))


    st.markdown("### Selected Team Summary")

    st.write("Team cost: \${:.2f} = \${:.2f} + \${:.2f}".format(sum(df_lineup.now_cost)+sum(df_subs.now_cost), sum(df_lineup.now_cost), sum(df_subs.now_cost)))
    st.write("Team total points: {:.2f} = {:.2f} + {:.2f}".format(sum(df_lineup.total_points)+sum(df_subs.total_points), sum(df_lineup.total_points), sum(df_subs.total_points)))
    st.write("Team ep_next: {:.2f} = {:.2f} + {:.2f}".format(sum(df_lineup.ep_next)+sum(df_subs.ep_next), sum(df_lineup.ep_next), sum(df_subs.ep_next)))
    st.write("Team avg selected_by_percent: {:.2f} = {:.2f} + {:.2f}".format((sum(df_lineup.selected_by_percent) + sum(df_subs.selected_by_percent) / squad_total_players), sum(df_lineup.selected_by_percent) / lineup_total_players, sum(df_subs.selected_by_percent) / subs_total_players))


def solve_group(df, budget, total_players, players_minmax, group_name ="group"):
    # Create the model
    model = pulp.LpProblem(name="create-{}".format(group_name), sense=pulp.LpMaximize, )

    codes = df.index.to_list()

    group = pulp.LpVariable.dict("group", codes, 0, 1, cat=pulp.LpInteger)

    # Add the constraints to the model
    # Lineup constraints
    model += (sum(df.now_cost.loc[c] * group[c] for c in codes) <= budget, "Lineup budget")
    model += (sum(group[c] for c in codes) == total_players, "Max {} lineup".format(total_players))
    for player_type in players_minmax:
        min_val, max_val = players_minmax[player_type]
        element_type = map_pos_num[player_type]
        if min_val == max_val:
            model += (sum(group[c] for c in codes if df.element_type.loc[c] == element_type) == min_val,
                      "Val {} {} in lineup".format(min_val, player_type))
        else:
            model += (sum(group[c] for c in codes if df.element_type.loc[c] == element_type) >= min_val,
                      "Min {} {} in lineup".format(min_val, player_type))
            model += (sum(group[c] for c in codes if df.element_type.loc[c] == element_type) <= max_val,
                      "Max {} {} in lineup".format(max_val, player_type))


    with st.sidebar:
        st.markdown("### {} ".format(group_name))
        w_points = st.slider("Total Points", min_value=0, max_value=10, value=10, key='{}-{}'.format(group_name, 'points'))
        w_cost = st.slider("Cost", min_value=0, max_value=10, value=1, key='{}-{}'.format(group_name, 'cost'))
        w_ep = st.slider("Expected Points Next Round", min_value=0, max_value=10, value=5, key='{}-{}'.format(group_name, 'ep'))
        w_selected = st.slider("Selected by Percent", min_value=0, max_value=10, value=3, key='{}-{}'.format(group_name, 'selected'))
        w_bonus = st.slider("Bonus Points", min_value=0, max_value=10, value=1, key='{}-{}'.format(group_name, 'bonus'))
        w_dreamteam = st.slider("Times in Dreamteam", min_value=0, max_value=10, value=1, key='{}-{}'.format(group_name, 'dreamteam'))

    model += pulp.lpSum([w_points * df.total_points.loc[c] * group[c],
                         w_cost * df.now_cost.loc[c] * group[c],
                         w_ep * df.ep_next.loc[c] * group[c],
                         w_selected * df.selected_by_percent.loc[c] * group[c],
                         w_bonus * df.bonus.loc[c] * group[c],
                         w_dreamteam * df.dreamteam_count.loc[c] * group[c]] for c in codes)

    model.writeLP('file.txt')
    # Solve the problem
    # st.write(pulp.listSolvers(onlyAvailable=True))
    # status = model.solve(solver=pulp.GLPK(msg=False))
    status = model.solve()
    if status == pulp.LpStatusOptimal:
        return [c for c in codes if pulp.value(group[c]) == 1]
    else:
        return None


if __name__ == "__main__":
    main()