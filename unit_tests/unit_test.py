import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelBinarizer

def test_feature_engineering():
    data = [
        (-16, -16, -16, -16, -16, 100, 'hoko', 'mategai', 'bankara_challenge', 'bravo'),
        (-32, -32, -32, -32, -32, 300, 'yagura', 'yunohana', 'bankara_open', 'alpha'),
        (-48, -48, -48, -48, -48, 240, 'yagura', 'mategai', 'bankara_open', 'bravo'),
        (-64, -64, -64, -64, -64, 150, 'hoko', 'mategai', 'bankara_challenge', 'alpha'),
    ]

    num_columns = ['kill_diff', 'assist_diff', 'death_diff', 'special_diff', 'inked_diff', 'time']
    cat_columns = ['mode', 'stage', 'lobby']
    pred_col = ['win']

    df = pd.DataFrame(data, columns=num_columns + cat_columns + pred_col)
    df = pd.get_dummies(df, columns = cat_columns, drop_first = True)

    scaler = MinMaxScaler()

    scaler.fit(df[num_columns])
    df[num_columns] = scaler.transform(df[num_columns])

    lb = LabelBinarizer()

    lb.fit(df[pred_col])
    df['win'] = lb.transform(df[pred_col])

    for col in num_columns:
        df[col] = df[col].apply(lambda x: float("{:.4f}".format(x)))

    expected_data = [
        (1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 0.0000, 0, 0, 0, 1),
        (0.6667, 0.6667, 0.6667, 0.6667, 0.6667, 1.0000, 1, 1, 1, 0),
        (0.3333, 0.3333, 0.3333, 0.3333, 0.3333, 0.7000, 1, 0, 1, 1),
        (0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.2500, 0, 0, 0, 0),
    ]

    expected_cols = ['kill_diff', 'assist_diff', 'death_diff', 'special_diff', 'inked_diff', 'time', 'mode_yagura', 'stage_yunohana', 'lobby_bankara_open', 'win']

    resulting_df = df[expected_cols]
    expected_df = pd.DataFrame(expected_data, columns=expected_cols)


    assert resulting_df.to_dict() == expected_df.to_dict()




def test_transform_battle_data():

    new_column_list = ['-kill-assist', '-kill', '-assist', '-death', '-special', '-inked']
    team_list = ['A', 'B']
    columns = []

    data = [
       tuple(range(1, len(new_column_list)*8+1)),
       tuple(range(2, len(new_column_list)*8*2+1, 2)),
       tuple(range(3, len(new_column_list)*8*3+1, 3)),
       tuple(range(4, len(new_column_list)*8*4+1, 4)),
    ]

    for column in new_column_list:
        for team in team_list:
            column_names = [("{0}" + column).format(team + str(i)) for i in range(1, 5)]
            columns.append(column_names)

    columns = np.array(columns).flatten()

    df = pd.DataFrame(data, columns=columns)

    for column in new_column_list:
        for team in team_list:
            column_names = [("{0}" + column).format(team + str(i)) for i in range(1, 5)]
            df[team + column] = df[column_names].sum(axis=1)

    df['kill_diff'] = df['A-kill']-df['B-kill']
    df['assist_diff'] = df['A-assist']-df['B-assist']
    df['death_diff'] = df['A-death']-df['B-death']
    df['special_diff'] = df['A-special']-df['B-special']
    df['inked_diff'] = df['A-inked']-df['B-inked']

    expected_data = [
        (-16, -16, -16, -16, -16),
        (-32, -32, -32, -32, -32),
        (-48, -48, -48, -48, -48),
        (-64, -64, -64, -64, -64),
    ]

    expected_cols = ['kill_diff', 'assist_diff', 'death_diff', 'special_diff', 'inked_diff']
    resulting_df = df[expected_cols]
    expected_df = pd.DataFrame(expected_data, columns=expected_cols)

    assert resulting_df.to_dict() == expected_df.to_dict()


if __name__ == "__main__":
    test_transform_battle_data()
    test_feature_engineering()