import streamlit as st
import pandas as pd
from datetime import datetime
from fpldata import FPLData
from weighting import PlayerWeights
from functions import squad_transfer
from helpers import *

PHOTO_URL = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{}.png"
FILL_NA_CHANCE_OF_PLAYING = 100
filename_to_export = "RK_{squad_name}_GW_{gw}_Recommendations_{datetime}.xls"

fpl = FPLData(convert_to_dataframes=True)


def main():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image('images/roboklopp1.jpeg')

    with col2:
        st.markdown("""
            # Robo Klopp presents: 
            
            ## _Weekly FPL Transfer Advice_
            ---
            "humans coaches are overrated" -- Robo Klopp   
        """)

    df_info = fpl.fetch_info()

    game_week = df_info["events"][df_info["events"].is_next].id.iloc[0]
    df_elements = df_info['elements'].set_index('id')
    df_teams = df_info['teams'].set_index('id')
    df_type = df_info['element_types'].set_index('id')

    _teams_cols = {c: "team_{}".format(c) for c in ['name', 'short_name', 'strength',
                                                    'strength_overall_home', 'strength_overall_away',
                                                    'strength_attack_home', 'strength_attack_away',
                                                    'strength_defence_home', 'strength_defence_away',
                                                    'pulse_id']}
    df_elements = df_elements.join(df_teams[_teams_cols.keys()].rename(_teams_cols, axis=1), on="team")

    _etype_cols = {'singular_name': 'type_name', 'singular_name_short': 'type_name_short'}
    df_elements = df_elements.join(df_type[_etype_cols.keys()].rename(_etype_cols, axis=1), on="element_type")

    df_elements.chance_of_playing_next_round = df_elements.chance_of_playing_next_round.fillna(
        FILL_NA_CHANCE_OF_PLAYING)
    df_elements["full_name"] = df_elements.first_name + ' ' + df_elements.second_name

    my_team = st.text_input("My Team", max_chars=10, key=None, type='default')
    email = st.text_input("Email", max_chars=None, key=None, type='default')
    password = st.text_input("Password", max_chars=None, key=None, type='password')
    if (my_team != "") and (email != "") and (password != ""):
        capt_ = fpl.fetch_managers([my_team])[my_team].iloc[0]
        captain_name = capt_.player_first_name + " " + capt_.player_last_name
        squad_name = capt_["name"]

        my_team = fpl.fetch_my_team(my_team=my_team, email=email, password=password)
        # st.dataframe(df_my_team['picks'])

        bank_budget = my_team['transfers']['bank']
        df_my_team = my_team['picks'].set_index('element').join(df_elements)

        st.markdown("""
        ***
        ## Squad: _{squad_name}_ by _{captain_name}_
        
        """.format(squad_name=squad_name, captain_name=captain_name))

        cols = st.columns(len(df_my_team))
        for i, col in enumerate(cols):
            with col:
                player = df_my_team.iloc[i]
                st.image(PHOTO_URL.format(player.code))
                st.markdown("<div style='writing-mode: vertical-rl;'>{name}</div>".format(name=player.web_name),
                            unsafe_allow_html=True)

        st.dataframe(df_my_team)

        st.markdown("## All players weighted")

        pw = PlayerWeights(df_elements=df_elements)
        df_elements.insert(0, "weights", pw.apply())
        st.dataframe(df_elements.sort_values(by="weights", ascending=False))

        teams_to_exclude = st.multiselect("Exclude teams", df_teams.name)
        df_teams['pick'] = df_info["game_settings"]["squad_team_limit"]
        df_teams.loc[df_teams['name'].isin(teams_to_exclude), 'pick'] = 0

        teams = df_teams.pick.to_dict()
        for team in df_my_team.team:
            teams[team] -= 1

        nq = squad_transfer(df=df_elements, squad=df_my_team,
                            teams=teams,
                            top_n=st.slider("Find Top N players for each squad memmber", 5, 200, 50, 5),
                            extra_budget=bank_budget)

        nq = sorted(nq, key=lambda x: (x[1]['avg_weights'], x[1]['points'], x[1]['cost'], x[1]['avg_select_percent']),
                    reverse=True)

        st.markdown("## Robo Klopp's Transfer Recommendations")
        df_rec = pd.DataFrame([e for _, e in nq])
        st.dataframe(df_rec)

        fn = filename_to_export.format(squad_name=squad_name, gw=game_week,
                                       datetime=datetime.now().strftime("%Y%m%d%H%M%S"))
        fn = fn.replace(' ', '')

        if st.button("Press to export to CSV"):
            st.markdown(get_table_download_link(df_rec, fn), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
