from utils import *

assoc_pumps_set: Set[PumpID] = {
    0,  # Strumien
    1,  # Zablocie
    2,  # Zarzecze
    3,  # Frelichow
    4  # Podgrobel
}

workers2pumps_primary_binding: Dict[WorkerID, PumpID] = {
    0: 0, 1: 0, 2: 0, 3: 0, 4: 0,
    5: 1, 6: 1, 7: 1, 8: 1, 9: 1,
    10: 2, 11: 2, 12: 2, 13: 2,
    14: 3, 15: 3, 16: 3, 17: 3,
    18: 4, 19: 4, 20: 4, 21: 4
}

workers2pumps_secondary_binding: Dict[WorkerID, Set[PumpID]] = {
    0: {2, 3, 4}, 1: {2, 3, 4}, 2: {2, 3, 4}, 3: {2, 3, 4}, 4: {2, 3, 4},
    5: {2, 3, 4}, 6: {2, 3, 4}, 7: {2, 3, 4}, 8: {2, 3, 4}, 9: {2, 3, 4},
    10: set(), 11: set(), 12: set(), 13: set(),
    14: set(), 15: set(), 16: set(), 17: set(),
    18: set(), 19: set(), 20: set(), 21: set()
}

workers2unocc_shift_ixs_rigid_binding = {
    0: {0}, 1: {1}, 2: {2}, 3: {3}, 4: {4},
    5: {5}, 6: {6}, 7: {7}, 8: {8}, 9: {9},
    10: {10}, 11: {11}, 12: {12}, 13: {13},
    14: {14}, 15: {15}, 16: {16}, 17: {17},
    18: {18}, 19: {19}, 20: {20}, 21: {21}
}

workers2unocc_shift_ixs_optional_binding = {
    0: {1}, 1: {2}, 2: {3}, 3: {4}, 4: {5},
    5: {6}, 6: {7}, 7: {8}, 8: {9}, 9: {10},
    10: {11}, 11: {12}, 12: {13}, 13: {14},
    14: {15}, 15: {16}, 16: {17}, 17: {18},
    18: {19}, 19: {20}, 20: {21}, 21: {0}
}

days_per_week: int = 7
days_per_month: int = 28

shifts_per_day = 3
shift_span: ShiftIX = 3 * 7 * 1
base_start_shift_offset: ShiftIX = 0  # (0...6 *3)

valorization__occupied_sequential: float = 1
valorization__occupied_sequential_lookup: Dict[int, float] = {
    1: -4e4,
    2: -4e4,
    3: -4e4,
    4: 3e5,
    5: 1e6,
    6: -3e4,
}
violation_penatly__max_1_occ_shifts_in_curr_3x_seq: float = float('inf')  # nie relaksowac!
violation_penatly__min_1_5x_unocc_seq_in_curr_week: float = float('inf')  # tu przy inf chyba jest problem z dluga rand
violation_penatly__max_6_occ_shifts_in_curr_week: float = float('inf')
violation_penatly__min_1_unocc_sunday_in_curr_month: float = float('inf')
violation_penatly__workers2unocc_shifts_rigid: float = float('inf')

violation_penatly__min_5_occ_shifts_in_curr_week: float = 5e7  # nie dawac jako inf!
violation_penatly__workers2unocc_shifts_optional: float = 2e3
violation_penatly__workers2occ_shift_primary: float = 3e3

initial_randomization_choice_jam_patience: int = 20
initial_randomization_cutoff_patience: int = 2500

init_adjacency_randomization_temperature_iterations_no: int = 500
init_adjacency_randomization_opt_solution_get_probability: float = .8

iterations_no_temperature_const = 100
iterations_no_loss_correction_cutoff = 5000

temperature_ratio_current2next: float = .99
temperature_ratio_final2init: float = .5
