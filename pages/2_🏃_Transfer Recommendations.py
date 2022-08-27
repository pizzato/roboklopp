import random

import streamlit as st
from fpldata import FPLData
from get_data import get_data
import pulp

# Team recommendation with Linear Programming based on https://statnamara.wordpress.com/2021/02/05/finding-the-best-lazy-fantasy-football-team-using-pulp-in-python/

st.set_page_config(page_title=None, page_icon='images/roboklopp_eye.jpeg', layout="wide", initial_sidebar_state="auto",
                   menu_items=None)

PHOTO_URL = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{}.png"
player_columns = ['type_name', 'web_name', 'full_name', 'team_name', 'now_cost', 'total_points', 'ep_next',
                  'selected_by_percent', 'bonus', 'dreamteam_count', 'element_type']

BUDGET = 1000
PLAYERS_PER_TEAM = 3
map_pos_num = {'Goalkeeper': 1, 'Defender': 2, 'Midfielder': 3, 'Forward': 4}
map_num_pos = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}


def solve_group(df, current_team, n_transfers, budget, total_players, players_minmax, max_players_per_team,
                group_name="group"):
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
    # Max players per team
    for team in df.team_name.unique():
        model += (sum(group[c] for c in codes if df.team_name.loc[c] == team) <= max_players_per_team[team],
                  "Max {} players per team in {}".format(max_players_per_team[team], team))

    # change of playing next round for all players is 100%
    model += (sum(df.chance_of_playing_next_round.loc[c] * group[c] for c in codes) == 100 * total_players,
              "Chance of playing next round is 100%")

    model += (
        sum(group[c] for c in current_team) == total_players - n_transfers,
        "Keeping all by {} players".format(n_transfers))

    with st.sidebar:
        st.markdown("### {} ".format(group_name))

        w_points = st.slider("Total Points", min_value=0, max_value=10, value=10,
                             key='{}-{}'.format(group_name, 'points'))
        w_cost = st.slider("Cost", min_value=0, max_value=10, value=1, key='{}-{}'.format(group_name, 'cost'))
        w_ep = st.slider("Expected Points Next Round", min_value=0, max_value=10, value=5,
                         key='{}-{}'.format(group_name, 'ep'))
        w_selected = st.slider("Selected by Percent", min_value=0, max_value=10, value=3,
                               key='{}-{}'.format(group_name, 'selected'))
        w_bonus = st.slider("Bonus Points", min_value=0, max_value=10, value=1, key='{}-{}'.format(group_name, 'bonus'))
        w_dreamteam = st.slider("Times in Dreamteam", min_value=0, max_value=10, value=1,
                                key='{}-{}'.format(group_name, 'dreamteam'))

    model += pulp.lpSum([w_points * df.total_points.loc[c] * group[c],
                         w_cost * df.now_cost.loc[c] * group[c],
                         w_ep * df.ep_next.loc[c] * group[c],
                         w_selected * df.selected_by_percent.loc[c] * group[c],
                         w_bonus * df.bonus.loc[c] * group[c],
                         w_dreamteam * df.dreamteam_count.loc[c] * group[c]] for c in codes)

    # Solve the problem
    # st.write(pulp.listSolvers(onlyAvailable=True))
    # status = model.solve(solver=pulp.GLPK(msg=False))
    status = model.solve()
    if status == pulp.LpStatusOptimal:
        return [c for c in codes if pulp.value(group[c]) == 1]
    else:
        return None


def main():
    col1, col2 = st.columns([1, 3])
    with col1:

        st.image('images/roboklopp{}.png'.format(random.randint(1, 10)))

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

    # df_elements = df_elements.set_index("code")
    df_to_score = df_elements.copy().set_index("code")
    other_columns = df_to_score.columns.difference(player_columns).to_list()

    # Configurations for players
    squad_total_players = 15
    squad_players = {'Goalkeeper': (2, 2), 'Defender': (5, 5), 'Midfielder': (5, 5), 'Forward': (3, 3)}

    my_team = st.text_input("My Team", max_chars=10, key=None, type='default')
    email = st.text_input("Email", max_chars=None, key=None, type='default')
    password = st.text_input("Password", max_chars=None, key=None, type='password')
    if (my_team != "") and (email != "") and (password != ""):
        capt_ = fpl.fetch_managers([my_team])[my_team].iloc[0]
        captain_name = capt_.player_first_name + " " + capt_.player_last_name
        squad_name = capt_["name"]

        my_team = fpl.fetch_my_team(my_team=my_team, email=email, password=password)

        my_team_value = my_team['transfers']['value']
        my_team_bank = my_team['transfers']['bank']
        my_team_transfers_limit = my_team['transfers']['limit']
        my_team_transfers_cost = my_team['transfers']['cost']

        df_my_team = my_team['picks'].set_index('element').join(df_elements).sort_values(['element_type', 'code'],
                                                                                         ascending=True)

        teams_to_exclude = st.sidebar.multiselect("Teams to exclude", df_elements.team_name.unique(), default=[])
        if len(teams_to_exclude) > 0:
            df_to_score = df_to_score[~df_to_score.team_name.isin(teams_to_exclude)]

        max_players_per_team = {team: PLAYERS_PER_TEAM for team in df_to_score.team_name.unique()}

        st.markdown("""
        ***
        ## Current squad: _{squad_name}_ by _{captain_name}_

        """.format(squad_name=squad_name, captain_name=captain_name))

        for i, col in enumerate(st.columns(len(df_my_team))):
            with col:
                player = df_my_team.iloc[i]
                st.image(player.photo_url)
                if player.is_captain == 1:
                    st.markdown("**(C)**")
                elif player.is_vice_captain == 1:
                    st.markdown("**(VC)**")
                st.markdown("<div style='writing-mode: vertical-rl;'>{name}</div>".format(name=player.web_name),
                            unsafe_allow_html=True)

        # st.dataframe(df_my_team)

        n_transfers = st.sidebar.slider("Number of Transfers", min_value=0, max_value=squad_total_players,
                                        value=my_team_transfers_limit)

        lineup = solve_group(df=df_to_score,
                             current_team=list(df_my_team.code),
                             n_transfers=n_transfers,
                             budget=my_team_value + my_team_bank,
                             total_players=squad_total_players,
                             players_minmax=squad_players,
                             max_players_per_team=max_players_per_team,
                             group_name='Weights')

        if lineup is None:
            st.write("No subs found")
            return

        df_lineup = df_elements.set_index('code').loc[lineup].sort_values(['element_type', 'code'], ascending=True)

        # Players in my team not in the lineup
        df_my_team_not_in_lineup = df_my_team[~df_my_team.code.isin(lineup)]

        # Players in the lineup not in my team
        df_lineup_not_in_my_team = df_lineup[~df_lineup.index.isin(df_my_team.code)]

        st.markdown("""
            ---
            ## Transfer Recommendations
        """)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Replace players ####")

            for player in df_my_team_not_in_lineup.itertuples():
                st.image(player.photo_url, width=100)
                st.markdown(player.web_name)

        with col2:
            st.markdown("#### with players ####")

            for player in df_lineup_not_in_my_team.itertuples():
                st.image(player.photo_url, width=100)
                st.markdown(player.web_name)

        _ep_top = df_lineup.sort_values(['ep_next', 'total_points'], ascending=False)
        lu_captain = _ep_top.iloc[0].web_name
        lu_vice_captain = _ep_top.iloc[1].web_name

        st.markdown("### New Team")

        cols = st.columns(len(df_lineup))
        for i, col in enumerate(cols):
            with col:
                player = df_lineup.iloc[i]
                st.image(player.photo_url)
                if player.web_name == lu_captain:
                    st.markdown("**(C)**")
                elif player.web_name == lu_vice_captain:
                    st.markdown("**(VC)**")
                st.markdown("<div style='writing-mode: vertical-rl;'>{name}</div>".format(name=player.web_name),
                            unsafe_allow_html=True)

        st.dataframe(
            df_lineup[player_columns + other_columns].sort_values(by=['element_type', 'total_points'], ascending=False))

        st.markdown("### Selected Team Summary")

        # noinspection PyPep8
        st.write("Team cost: \${:.2f} ".format(sum(df_lineup.now_cost)))
        st.write("Team total points: {:.2f} ".format(sum(df_lineup.total_points)))
        st.write("Team ep_next: {:.2f} ".format(sum(df_lineup.ep_next)))
        st.write("Team avg selected_by_percent: {:.2f} ".format((sum(df_lineup.selected_by_percent))))
        point_cost = max(0, (n_transfers - my_team_transfers_limit) * my_team_transfers_cost)
        st.write("Transfer Cost: {:2d} points ".format(point_cost))
        ep_gain = sum(df_lineup.ep_next) - sum(df_my_team.ep_next)
        st.write("Expected points gain: {:.2f} points ".format(ep_gain))
        st.write("Expected points gain minus cost: {:.2f} points ".format(ep_gain - point_cost))


if __name__ == "__main__":
    main()
