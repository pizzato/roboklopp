import streamlit as st
from fpldata import FPLData
from get_data import get_data
import pulp

# Team recommendation with Linear Programming based on https://statnamara.wordpress.com/2021/02/05/finding-the-best-lazy-fantasy-football-team-using-pulp-in-python/

st.set_page_config(page_title=None, page_icon='images/roboklopp_eye.jpeg', layout="wide", initial_sidebar_state="auto", menu_items=None)

PHOTO_URL = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{}.png"
player_columns = ['first_name', 'second_name', 'web_name', 'now_cost', 'total_points', 'ep_next', 'selected_by_percent', 'bonus', 'dreamteam_count', 'element_type']
players = {'Goalkeeper': 2, 'Defender': 5, 'Midfielder': 5, 'Forward': 3}
BUDGET = 1000
map_pos_num = {'Goalkeeper': 1, 'Defender': 2, 'Midfielder': 3, 'Forward': 4}
map_num_pos = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}


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

    df_elements.selected_by_percent = df_elements.selected_by_percent.astype(float)
    df_elements.ep_next = df_elements.ep_next.astype(float)

    df_elements.now_cost = df_elements.now_cost.astype(float)

    df_elements = df_elements.set_index("code")

    team = solve_lp(df_elements, budget=BUDGET)
    if team is not None:
        df_team = df_elements.loc[team]

        st.markdown("### Team Created")
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_team[player_columns].sort_values(by=['element_type', 'total_points'], ascending=False))

        with col2:
            st.write("Team cost: ${:.2f}".format(sum(df_team.now_cost)))
            st.write("Team total points: {:.2f}".format(sum(df_team.total_points)))
            st.write("Team ep_next: {:.2f}".format(sum(df_team.ep_next)))
            st.write("Team avg selected_by_percent: {:.2f}".format(sum(df_team.selected_by_percent)/11.))


    else:
        st.write("No solution found")


def solve_lp(df, budget=BUDGET):
    # Create the model
    model = pulp.LpProblem(name="create-team", sense=pulp.LpMaximize)

    codes = df.index.to_list()

    players = pulp.LpVariable.dict("player", codes, 0, 1, cat=pulp.LpInteger)

    # now_cost = pulp.LpVariable(name='now_cost', e=df.now_cost, lowBound=0, upBound=1000, cat='Integer')
    # total_points = pulp.LpVariable(name='total_points', e=df.total_points, lowBound=0, cat='Integer')
    # dreamteam_count = pulp.LpVariable(name='dreamteam_count', lowBound=0)
    # ep_next = pulp.LpVariable(name='ep_next', lowBound=0)
    # selected_by_percent = pulp.LpVariable(name='selected_by_percent', lowBound=0)
    # bonus = pulp.LpVariable(name='bonus', lowBound=0)

    # Add the constraints to the model
    model += (sum(df.now_cost.loc[c] * players[c] for c in codes) <= budget, "cost")
    model += (sum(players[c] for c in codes) == 11, "Max 11 players")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 1) == 1, "One Goalie")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 2) >= 3, "Min 3 Defenders")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 2) <= 5, "Max 5 Defenders")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 3) >= 3, "Min 3 Midfielders")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 3) <= 5, "Max 5 Midfielders")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 4) >= 1, "Min 1 Attackers")
    model += (sum(players[c] for c in codes if df.element_type.loc[c] == 4) <= 3, "Max 3 Attackers")

    # Add the objective function to the model
    # model += pulp.lpSum([df.total_points.loc[c] * players[c]] for c in codes)
    #
    # model += pulp.lpSum([10 * df.total_points.loc[c] * players[c],
    #                      1 * df.now_cost.loc[c] * players[c],
    #                      5 * df.ep_next.loc[c] * players[c],
    #                      3 * df.selected_by_percent.loc[c] * players[c],
    #                      1 * df.bonus.loc[c] * players[c],
    #                      1 * df.dreamteam_count.loc[c] * players[c]] for c in codes
    #                     )

    with st.sidebar:
        w_points = st.slider("Total Points", min_value=0, max_value=10, value=10)
        w_cost = st.slider("Cost", min_value=0, max_value=10, value=1)
        w_ep = st.slider("EP", min_value=0, max_value=10, value=5)
        w_selected = st.slider("Selected", min_value=0, max_value=10, value=3)
        w_bonus = st.slider("Bonus", min_value=0, max_value=10, value=1)
        w_dreamteam = st.slider("Dreamteam", min_value=0, max_value=10, value=1)

    model += pulp.lpSum([w_points * df.total_points.loc[c] * players[c],
                         w_cost * df.now_cost.loc[c] * players[c],
                         w_ep * df.ep_next.loc[c] * players[c],
                         w_selected * df.selected_by_percent.loc[c] * players[c],
                         w_bonus * df.bonus.loc[c] * players[c],
                         w_dreamteam * df.dreamteam_count.loc[c] * players[c]]
                        for c in codes)


    # Solve the problem
    # st.write(pulp.listSolvers(onlyAvailable=True))
    # status = model.solve(solver=pulp.GLPK(msg=False))
    status = model.solve()
    if status == pulp.LpStatusOptimal:
        return [c for c in codes if pulp.value(players[c]) == 1]
    else:
        return None

if __name__ == "__main__":
    main()