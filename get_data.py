FILL_NA_CHANCE_OF_PLAYING = 100

def get_data(fpl):
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

    return df_info, game_week, df_elements, df_teams, df_type
