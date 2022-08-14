import streamlit as st
from fpldata import FPLData
import new_team_config as ntc
from get_data import get_data
from weighting import weight_func, eval_team
from new_team_functions import get_squad_prod, combine_and_pick_top

PHOTO_URL = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{}.png"
FILL_NA_CHANCE_OF_PLAYING = 100
player_columns = ['code', 'first_name', 'second_name', 'now_cost', 'total_points']

fpl = FPLData(convert_to_dataframes=True)


def main():
    pg = ntc.draw_config(pick_groups=ntc.pick_groups_default, where=st.sidebar)

    total_players = sum([pg[k]['players'].get(pos, 0) for k in pg for pos in ntc.MAP_POS_NUM])

    df_info, game_week, df_elements, df_teams, df_type = get_data(fpl)

    col1, col2 = st.columns([1, 3])
    with col1:
        st.image('images/roboklopp1.jpeg')

    with col2:
        st.markdown("""
              # Robo Klopp presents: 

              ## _New Team Selection_
              
              ### Note: This is was converted from notebooks and I have made some bugs during conversion, it is far from perfect and I am rebuilding this whole app from scratch.
              ---
              "humans coaches are overrated" -- Robo Klopp   
          """)

    teams_to_exclude = st.multiselect("Exclude teams", df_teams.name)

    n_draws_per_group = st.slider("Number of draws per group", min_value=10, max_value=400, value=200, step=10)
    n_draws_selected_per_group = st.slider("Number of draws selected per group", min_value=5, max_value=50, value=10,
                                           step=1, help="Number of evaluated groups is the product of all groups")
    n_teams_to_recommend = st.slider("Number of teams to recommend", min_value=1, max_value=100, value=20,
                                     help="Number of teams to evaluated at the end of it")
    weight_for_cost_similarity_in_groups = 50

    if st.button("Generate a new team", disabled=total_players != ntc.MAX_PLAYERS):
        st.write("Please select {} players".format(ntc.MAX_PLAYERS))

        _cost_min = df_elements['now_cost'].min()
        _cost_max = df_elements['now_cost'].max()

        def _cost_norm(cost):
            return (cost - _cost_min) / (_cost_max - _cost_min)

        group_budget_player_norm = {k: _cost_norm(d["budget"] / sum(d["players"].values())) for k, d in
                                    pg.items()}

        for pos, d in pg.items():
            args = d["weight_func"]
            args.update(dict(mult=dict(rk_change_playing_filled=1)))
            args.update(dict(sim=dict(now_cost=(weight_for_cost_similarity_in_groups, group_budget_player_norm[pos]))))

        df_elements['rk_change_playing_filled'] = df_elements.chance_of_playing_next_round.fillna(100)

        df_metrics = df_elements[['now_cost', 'ep_next', 'total_points', 'rk_change_playing_filled',
                                  'team_strength_overall_home', 'team_strength_overall_away',
                                  'team_strength_attack_home', 'team_strength_attack_away',
                                  'team_strength_defence_home', 'team_strength_defence_away',
                                  'selected_by_percent']].astype(float)

        df_metrics['team_strength_attack'] = df_metrics[
            ['team_strength_attack_home', 'team_strength_attack_away']].mean(axis=1)
        df_metrics['team_strength_defence'] = df_metrics[
            ['team_strength_defence_home', 'team_strength_defence_away']].mean(axis=1)
        df_metrics['team_strength_overall'] = df_metrics[
            ['team_strength_overall_home', 'team_strength_overall_away']].mean(axis=1)

        for pos, d in pg.items():
            df_elements['w_' + pos] = weight_func(df_metrics, **d["weight_func"])

        weight_columns = [col for col in df_elements.columns if col.startswith('w_')]

        # normalise
        df_elements[weight_columns] = (df_elements[weight_columns] - df_elements[weight_columns].min()) / (
                df_elements[weight_columns].max() - df_elements[weight_columns].min())

        """##### Spot check top players"""

        df_elements.sort_values(by='w_Tier 1', ascending=False, ignore_index=True)[player_columns + weight_columns]

        # Weight distro

        df_elements[weight_columns].describe()

        df_teams['pick'] = 3
        df_teams.loc[df_teams['name'].isin(teams_to_exclude), 'pick'] = 0
        team_budget = {t_['code']: t_['pick'] for t_ in df_teams[['code', 'pick']].to_dict('record')}

        pick_group_order = sorted(pg.keys())

        comb_squad = get_squad_prod(df=df_elements, pick_group_order=pick_group_order, pick_groups_config=pg,
                                    team_budget=team_budget, extra_budget=0, top_n=n_draws_selected_per_group,
                                    ndraws_per_group=n_draws_per_group)

        # squad[player_columns + weight_columns]
        print("Combine squads")
        tt_ = combine_and_pick_top(comb_squad, by_order=['points', 'avg_select_percent', 'cost'],
                                   top_n=n_teams_to_recommend)

        """# RoboKloop Recommendations
        """
        recommended_teams = sorted([(eval_team(sq), sq) for sq in tt_], key=lambda x: x[0]['avg_select_percent'],
                                   reverse=True)

        """#### Team Recommendation - Order from best to worse"""

        for i, (e, sq) in enumerate(recommended_teams):
            st.write("Team: {}   Cost: {:.0f}   Points: {:.2f}   Avg Select: {:.2f}".format(i, e['cost'], e['points'],
                                                                                            e['avg_select_percent']))

            st.dataframe(sq[player_columns + weight_columns + ['type_name']].sort_values(by=['type_name', 'code'],
                                                                                         ascending=False,
                                                                                         ignore_index=True).head(
                n_teams_to_recommend))


if __name__ == '__main__':
    main()
