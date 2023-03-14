from utils import *

assoc_pumps_set: Set[PumpID] = {
    0  # Strumien
}

workers2pumps_primary_binding: Dict[WorkerID, PumpID] = {
    0: 0, 1: 0, 2: 0, 3: 0, 4: 0
}

workers2pumps_secondary_binding: Dict[WorkerID, Set[PumpID]] = {
    0: set(), 1: set(), 2: set(), 3: set(), 4: set()
}

workers2unocc_shift_ixs_optional_binding = {
    0: set(), 1: set(), 2: set(), 3: set(), 4: set()
}

workers2unocc_shift_ixs_rigid_binding = {
    0: {0, 1, 2, 3, 4, 5, 6, 7, 8, 24, 25, 26, 27, 28, 29, 45, 46, 47, 48, 49, 50, 57, 58, 59, 60, 61, 62, 75, 76, 77},
    1: {15, 16, 17, 18, 19, 20, 21, 22, 23, 42, 43, 44, 45, 46, 47, 48, 49, 50, 66, 67, 68, 69, 70, 71, 72, 73, 74},
    2: {9, 10, 11, 12, 13, 14,33,34,35,36,37,38,51,52,53,54,55,56,63,64,65,78,79,80,81,82,83},
    3: {0,1,2,9,10,11,12,13,14,15,16,17,36,37,38,39,40,41,51,52,53,54,55,56,72,73,74,75,76,77},
    4: {3,4,5,6,7,8,24,25,26,27,28,29,30,31,32,39,40,41,57,58,59,60,61,62,63,64,65}
}

days_per_week: int = 7
days_per_month: int = 28

shifts_per_day = 3
shift_span: ShiftIX = 3 * 7 * 4
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
init_adjacency_randomization_opt_solution_get_probability: float = .1

iterations_no_temperature_const = 100
iterations_no_loss_correction_cutoff = float('inf')

temperature_ratio_current2next: float = .99
temperature_ratio_final2init: float = .3
