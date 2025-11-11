"""Utility functions for the game."""

from .config import swap_number_d, swap_number_l


def Swap_team(team):
    """Swap team perspective."""
    return 0 if team == 0 else 1 if team == 2 else 2


def flip_board_view(info):
    """Flip board view so the player always sees themselves as team 1."""
    team, state, moving_pawns, spawning_pawns, done = info

    if team == 1:
        return info

    # Update state
    new_state = [
        [Swap_team(state[swap_number_l[i]][0])] + state[swap_number_l[i]][1:]
        for i in range(len(state))
    ]

    for i in range(len(state)):
        new_state[i][5] = state[i][5]

    # Update moving_pawns
    new_moving_pawns = [
        [
            Swap_team(moving_pawns[i][0]),
            moving_pawns[i][1],
            swap_number_d[moving_pawns[i][2]],
            swap_number_d[moving_pawns[i][3]],
        ]
        + moving_pawns[i][4:]
        for i in range(len(moving_pawns))
    ]

    # Update spawning_pawns
    new_spawning_pawns = [
        [
            Swap_team(spawning_pawns[i][0]),
            spawning_pawns[i][1],
            spawning_pawns[i][2],
            swap_number_d[spawning_pawns[i][3]],
            swap_number_d[spawning_pawns[i][4]],
        ]
        + spawning_pawns[i][5:]
        for i in range(len(spawning_pawns))
    ]

    return [Swap_team(team), new_state, new_moving_pawns, new_spawning_pawns, done]
