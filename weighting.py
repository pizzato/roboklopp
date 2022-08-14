import pandas as pd
import streamlit as st


def weight_func(df: pd.DataFrame, add: dict, sim: dict = None, mult: dict = None):
    """
    weight_func: calculates weight for pick func

    df: data frame with players
    add: dictionary of columns and weights to get res = sum(w * col) for all cols
    sim: dictionary with columns and tuple of weights and value to be summed according to their distance to an avg value: res = res + w * (1 - abs(val - col))
    mul: dictionary with columns adn weights that should be multiplied as: res = res * w * col

    """
    s = 0
    for (col, w) in add.items():
        s += w * df[col]

    if sim is not None:
        for (col, (w, v)) in sim.items():
            s += w * (1 - abs(v - df[col]))

    if mult is not None:
        for (col, w) in mult.items():
            s *= w * df[col]

    return s


class MinMaxScaler:
    def __init__(self):
        self.min, self.max = (None, None)

    def fit(self, s: pd.Series):
        self.min = s.min()
        self.max = s.max()
        return self

    def transform(self, v):
        return (v - self.min) / (self.max - self.min)

    def fit_transform(self, s: pd.Series):
        return self.fit(s).transform(v=s)


class PlayerWeights:
    def __init__(self, df_elements):
        self._build_metrics(df_elements)
        self._get_weights()

    def apply(self):
        weights = weight_func(self.df_metrics, **self.weight_func_args)

        # normalise
        scaler = MinMaxScaler()
        weights = scaler.fit_transform(weights)
        return weights

    def _get_weights(self):
        _original_val = dict(ep_this=100,
                             ep_next=70,
                             now_cost=30,
                             total_points=50,
                             strength_overall=5,
                             selected_by_percent=5,
                             transfers_in_out=50,
                             form=50)

        st.sidebar.write("Importance of stats")
        add_weights = {}
        for col in self.df_metrics.columns:
            add_weights[col] = st.sidebar.slider(label="+ " + col, min_value=0, max_value=100,
                                                 value=_original_val.get(col, 0),
                                                 step=1, )

        mult_weights = dict()
        if st.sidebar.checkbox("Multiply by chance of playing?", value=True):
            mult_weights["chance_of_playing_next_round"] = 10

        self.weight_func_args = dict(add=add_weights,
                                     mult=mult_weights)

    def _build_metrics(self, df_elements):
        # df_elements[['ep_this', 'ep_next']] = df_elements[['ep_this', 'ep_next']].fillna(0).astype(float)
        df_elements = df_elements.fillna(0)
        self.df_metrics = df_elements[['ep_this', 'ep_next',
                                       'now_cost', 'total_points', 'chance_of_playing_next_round',
                                       'team_strength_overall_home', 'team_strength_overall_away',
                                       'team_strength_attack_home', 'team_strength_attack_away',
                                       'team_strength_defence_home', 'team_strength_defence_away',
                                       'transfers_in_event', 'transfers_out_event',
                                       'transfers_in', 'transfers_out',
                                       'form',
                                       'selected_by_percent']].astype(float)

        self.df_metrics['team_strength_attack'] = self.df_metrics[
            ['team_strength_attack_home', 'team_strength_attack_away']].mean(axis=1)
        self.df_metrics['team_strength_defence'] = self.df_metrics[
            ['team_strength_defence_home', 'team_strength_defence_away']].mean(axis=1)
        self.df_metrics['team_strength_overall'] = self.df_metrics[
            ['team_strength_overall_home', 'team_strength_overall_away']].mean(axis=1)
        self.df_metrics['transfers_in_out'] = self.df_metrics['transfers_in'] - self.df_metrics['transfers_out']
        self.df_metrics['transfers_in_out_event'] = self.df_metrics['transfers_in_event'] - self.df_metrics[
            'transfers_out_event']

        self.df_metrics = (self.df_metrics - self.df_metrics.min()) / (self.df_metrics.max() - self.df_metrics.min())

        self.df_metrics = self.df_metrics.drop(columns=['team_strength_attack_home', 'team_strength_attack_away',
                                                        'team_strength_defence_home', 'team_strength_defence_away',
                                                        'team_strength_overall_home', 'team_strength_overall_away',
                                                        'transfers_in_event', 'transfers_out_event',
                                                        'transfers_in', 'transfers_out',
                                                        ])


def eval_team(df_team, col_prefixes=None):
    res = dict(
        cost=df_team['now_cost'].sum(),
        points=df_team['total_points'].sum(),
        avg_select_percent=df_team['selected_by_percent'].astype(float).mean()
    )

    if col_prefixes is not None:
        avg_pref_cols = []
        for prefix in col_prefixes:
            avg_pref_cols += [col for col in df_team.columns if col.startswith(prefix)]

        for col in avg_pref_cols:
            res['avg_' + col] = df_team[col].mean()

    return res
