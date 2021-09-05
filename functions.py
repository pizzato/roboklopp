def eval_team(df_team, col_prefixes=None):
    res = dict(
        ep_this=df_team['ep_this'].fillna(0).astype(float).sum(),
        ep_next=df_team['ep_next'].fillna(0).astype(float).sum(),
        cost=df_team['now_cost'].sum(),
        points=df_team['total_points'].sum(),
        avg_select_percent=df_team['selected_by_percent'].astype(float).mean(),
        avg_form=df_team['form'].astype(float).mean()
    )

    if col_prefixes is not None:
        avg_pref_cols = []
        for prefix in col_prefixes:
            avg_pref_cols += [col for col in df_team.columns if col.startswith(prefix)]

        for col in avg_pref_cols:
            res['avg_' + col] = df_team[col].astype(float).mean()

    return res


def squad_transfer(df, squad, teams, top_n=50, extra_budget=0):
    new_squads = []
    for id_rp, removed_player in squad.iterrows():
        _sq = squad.drop(id_rp)
        budget = extra_budget + removed_player['now_cost']
        print(budget)
        teams[removed_player['team']] += 1
        teams_to_pick = [k for k, v in teams.items() if v > 0]
        print(teams_to_pick)

        # remove current squad (leave the transfer player as one option is to leave him there)
        _df = df[~df.index.isin(_sq.index)]
        _df = _df[_df['now_cost'] <= budget]  # below budget
        _df = _df[_df['team'].isin(teams_to_pick)]  # ok team
        _df = _df[_df['element_type'] == removed_player['element_type']]  # same position

        for _, _np in _df.sort_values('weights', ascending=False).head(top_n).iterrows():
            _ns = _sq.append(_np)

            d_in_out_eval = dict(
                player_out=' '.join(removed_player[['first_name', 'second_name']]),
                player_in=' '.join(_np[['first_name', 'second_name']])
            )

            d_in_out_eval.update(eval_team(_ns, col_prefixes=['weights', 'transfers_']))
            new_squads.append((_ns, d_in_out_eval))

    return new_squads
