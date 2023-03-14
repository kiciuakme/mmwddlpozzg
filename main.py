from utils import *
import visuals_n_exams
import constraints as constrs
import sys
import os
import importlib
import matplotlib.pyplot as plt
from datetime import datetime


def calc_loss_fcn_total(schedule: Schedule) -> float:
    adder = 0

    daily_binary_schedule = schedule.flatten_over_workers().flatten_shifts_to_days()
    for worker_id in daily_binary_schedule.iter_over_workers():
        seq_adder = 0
        for day_ix in daily_binary_schedule.iter_over_shifts():
            occ_assoc = daily_binary_schedule.assoc_is_occ(worker_id, None, day_ix)
            if occ_assoc:
                seq_adder += 1
            else:
                try:
                    seq_val = params.valorization__occupied_sequential_lookup[seq_adder]
                except KeyError:
                    seq_val = 0

                adder += seq_val * params.valorization__occupied_sequential
                seq_adder = 0

        try:
            seq_val = params.valorization__occupied_sequential_lookup[seq_adder]
        except KeyError:
            seq_val = 0

        adder += seq_val * params.valorization__occupied_sequential

    for constaint_fcn, days_period, violation_penatly in constrs_set:
        if violation_penatly != float('inf'):
            last_checked_shift_ix = 0
            for shift_ix in schedule.iter_over_shifts():
                if days_period == 0 or shift_ix == 0 \
                        or shift_ix - last_checked_shift_ix == days_period * schedule.properties.shifts_per_day:
                    last_checked_shift_ix = shift_ix

                    for worker_id in schedule.iter_over_workers():
                        constaint_violated = constaint_fcn(schedule, worker_id, shift_ix)
                        if constaint_violated:
                            adder -= violation_penatly

    return adder


def is_any_rigid_contraints_violated(check_schedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    for constraint_fcn, day_period, violation_penatly in constrs_set:
        if violation_penatly == float('inf'):
            if constraint_fcn(check_schedule, worker_id, shift_ix):
                return True
    else:
        return False


def get_random_schedule(schedule_bindings: ScheduleBindings, shift_properties: ScheduleShiftProperites) -> Schedule:
    cutoff_counter = 0
    while cutoff_counter < params.initial_randomization_cutoff_patience:
        random_schedule = Schedule(schedule_bindings, shift_properties)

        worker_choice = []
        for pump_id in random_schedule.iter_over_pumps():
            for shift_ix in random_schedule.iter_over_shifts():
                wc_list = list(random_schedule.bindings.ps2w_uni[pump_id])
                random.shuffle(wc_list)
                wc_pointer = -1
                wc_jam_counter = 0

                worker_choice.append(((shift_ix, pump_id), wc_list, wc_pointer, wc_jam_counter))

        wc_index = 0
        while wc_index < len(worker_choice):
            print("(initial schedule generating progress: {:.2f} %; patience margin fulfill: {:.2f} %)".format(
                100 * wc_index / len(worker_choice),
                (100 * wc_index / len(worker_choice))/params.initial_randomization_cutoff_patience
                + 100*cutoff_counter/params.initial_randomization_cutoff_patience
            ))
            if wc_index < 0:
                raise Exception

            shift_ix, pump_id = worker_choice[wc_index][0]
            wc_list = worker_choice[wc_index][1]
            wc_pointer = worker_choice[wc_index][2]
            wc_jam_counter = worker_choice[wc_index][3]

            if wc_pointer != -1:
                random_schedule.assoc_reset(wc_list[wc_pointer], pump_id, shift_ix)
                wc_pointer = -1

            for new_pointer in range(wc_pointer + 1, len(wc_list)):
                worker_id = wc_list[new_pointer]

                if random_schedule.assoc_is_occ(worker_id, None, shift_ix):
                    continue
                check_schedule = random_schedule.copy()
                check_schedule.assoc_set(worker_id, pump_id, shift_ix)
                if is_any_rigid_contraints_violated(check_schedule, worker_id, shift_ix):
                    continue

                random_schedule.assoc_set(worker_id, pump_id, shift_ix)
                worker_choice[wc_index] = ((shift_ix, pump_id), wc_list, new_pointer, wc_jam_counter)
                wc_index += 1
                break
            else:
                wc_jam_counter += 1
                if wc_jam_counter > params.initial_randomization_choice_jam_patience:
                    cutoff_counter += 1
                    break
                else:
                    worker_choice[wc_index] = ((shift_ix, pump_id), wc_list, wc_pointer, wc_jam_counter)
                    wc_index -= 1

        if wc_index == len(worker_choice):
            return random_schedule
    raise Exception


def get_random_unitary_rematch_schedule(schedule: Schedule) -> Tuple[Schedule, int]:
    rematch_rigid_fail_counter = 0
    while True:
        random_shift = random.choice([shift_ix for shift_ix in schedule.iter_over_shifts()])
        random_pump = random.choice([pump_id for pump_id in schedule.iter_over_pumps()])
        pump_worker_assoc = schedule.flatten_over_pumps().assoc_get(None, random_pump, random_shift)
        alternative_pwa_set = schedule.bindings.ps2w_uni[random_pump].difference({pump_worker_assoc})
        for alternative_pwa_candidate in copy(alternative_pwa_set):
            if schedule.assoc_is_occ(alternative_pwa_candidate, None, random_shift):
                current_pump = schedule.assoc_get(alternative_pwa_candidate, None, random_shift)
                if current_pump not in schedule.bindings.w2ps_uni[pump_worker_assoc]:
                    alternative_pwa_set.remove(alternative_pwa_candidate)
        try:
            alternative_pump_worker_assoc = random.choice(list(alternative_pwa_set))
        except IndexError:
            rematch_rigid_fail_counter += 1
            continue

        check_schedule = schedule.copy()
        check_schedule.assoc_reset(pump_worker_assoc, random_pump, random_shift)
        check_schedule.assoc_set(alternative_pump_worker_assoc, random_pump, random_shift)
        if schedule.assoc_is_occ(alternative_pump_worker_assoc, None, random_shift):
            alternative_pwa_pump = schedule.assoc_get(alternative_pump_worker_assoc, None, random_shift)
            check_schedule.assoc_set(pump_worker_assoc, alternative_pwa_pump, random_shift)
            check_schedule.assoc_reset(alternative_pump_worker_assoc, alternative_pwa_pump, random_shift)

        if is_any_rigid_contraints_violated(check_schedule, pump_worker_assoc, random_shift) or \
                is_any_rigid_contraints_violated(check_schedule, alternative_pump_worker_assoc, random_shift):
            rematch_rigid_fail_counter += 1
            continue
        else:
            return check_schedule, rematch_rigid_fail_counter


def get_initial_opt_data(schedule_bindings: ScheduleBindings, shift_properties: ScheduleShiftProperites) -> \
        Tuple[Schedule, float, float]:
    init_schedule = get_random_schedule(schedule_bindings, shift_properties)
    init_schedule_loss = calc_loss_fcn_total(init_schedule)
    rematch_rigid_fail_counter = 0

    worse_loss_difference_adder = 0
    worse_loss_counter = 0
    for _ in range(params.init_adjacency_randomization_temperature_iterations_no):
        random_rematch_schedule, rematch_rigid_fails_no = get_random_unitary_rematch_schedule(init_schedule)
        random_rematch_schedule_loss = calc_loss_fcn_total(random_rematch_schedule)
        rematch_rigid_fail_counter += rematch_rigid_fail_counter
        print("random_rematch_loss no{}".format(_), random_rematch_schedule_loss)

        if random_rematch_schedule_loss < init_schedule_loss:
            worse_loss_difference_adder += init_schedule_loss - random_rematch_schedule_loss
            worse_loss_counter += 1

    init_temerature = worse_loss_difference_adder / worse_loss_counter \
                      / numpy.log(params.init_adjacency_randomization_opt_solution_get_probability)
    adjacency_acceptance_ratio = params.init_adjacency_randomization_temperature_iterations_no \
            / (params.init_adjacency_randomization_temperature_iterations_no + rematch_rigid_fail_counter)
    return init_schedule, init_temerature, adjacency_acceptance_ratio


Chart = List


class AnnealingExaminationIterationData:
    def __init__(self):
        self.temperature = -1
        self.loss_all = []  # step -> loss
        self.loss_cooldown = -1
        self.loss_accepted = []
        self.schedule_correction_pos_no = 0
        self.schedule_correction_neg_no = 0
        self.schedule_correction_nop_no = 0
        self.adjacency_acceptance_ratio = -1


def examine_annealing_core(init_schedule: Schedule, init_temperature: float) -> \
        Tuple[Schedule, float, List[AnnealingExaminationIterationData]]:
    final_temperature = init_temperature * params.temperature_ratio_final2init
    last_pos_correction_step_no = 0
    best_schedule = init_schedule
    max_sch_loss = -float('inf')

    current_temperature = init_temperature
    current_schedule = init_schedule
    current_sch_loss = calc_loss_fcn_total(current_schedule)

    exam_data = []

    while current_temperature < final_temperature \
            and last_pos_correction_step_no < params.iterations_no_loss_correction_cutoff:

        exam_data.append(AnnealingExaminationIterationData())
        exam_data[-1].temperature = current_temperature
        rigid_rematch_fails_counter = 0
        print("iter no {}; temp drop to final {}%".format(len(exam_data), 100 * current_temperature/init_temperature))

        step_ix = 0
        while True:
            adjacent_schedule, rematch_rigid_fail_no = get_random_unitary_rematch_schedule(current_schedule)
            adjacent_sch_loss = calc_loss_fcn_total(adjacent_schedule)

            exam_data[-1].loss_all.append(adjacent_sch_loss)
            rigid_rematch_fails_counter += rematch_rigid_fail_no

            random_uniform = random.uniform(0, 1)
            if adjacent_sch_loss > current_sch_loss \
                    or numpy.exp((current_sch_loss - adjacent_sch_loss)/current_temperature) > random_uniform:
                if adjacent_sch_loss > current_sch_loss:
                    if adjacent_sch_loss > max_sch_loss:
                        best_schedule = adjacent_schedule
                        max_sch_loss = adjacent_sch_loss

                    exam_data[-1].schedule_correction_pos_no += 1
                else:
                    exam_data[-1].schedule_correction_neg_no += 1
                exam_data[-1].loss_accepted.append(adjacent_sch_loss)

                current_schedule = adjacent_schedule
                current_sch_loss = adjacent_sch_loss
            else:
                exam_data[-1].schedule_correction_nop_no += 1

            if adjacent_sch_loss > current_sch_loss:
                last_pos_correction_step_no = 0
            else:
                last_pos_correction_step_no += 1

            step_ix += 1
            if step_ix > params.iterations_no_temperature_const:
                exam_data[-1].adjacency_acceptance_ratio = step_ix / (step_ix + rigid_rematch_fails_counter)
                exam_data[-1].loss_cooldown = current_sch_loss
                current_temperature *= params.temperature_ratio_current2next
                break

    return best_schedule, current_temperature, exam_data


def visualise_annealing_exam_iter(title: str, exam_data: List[AnnealingExaminationIterationData], path_to_save: str) \
        -> Chart:
    fig, ax = plt.subplots(nrows=2)
    plt.suptitle(title)

    iter_domain = [i+1 for i in range(len(exam_data))]
    iter_gen = range(len(exam_data))

    head_row = [
        "iteration",
        "loss-best",
        "loss-worst",
        "loss-avg",
        "loss-cooldown",
        "corrections-pos",
        "corrections-neg",
        "no-corrections",
        "average adjacency acceptance"
    ]
    tab_cells = [[head_row]] + [
        [iter_domain[i],
         max(exam_data[i].loss_accepted),
         min(exam_data[i].loss_accepted),
         sum(exam_data[i].loss_accepted) / len(exam_data[i].loss_accepted),
         exam_data[i].loss_cooldown,
         exam_data[i].schedule_correction_pos_no,
         exam_data[i].schedule_correction_neg_no,
         exam_data[i].schedule_correction_nop_no,
         exam_data[i].adjacency_acceptance_ratio
         ] for i in iter_gen
    ]

    plt.subplot(2, 1, 1)
    plt.title("Wartości funkcji celu")

    chart_loss_best = plt.plot(iter_domain, [max(exam_data[i].loss_accepted) for i in iter_gen], c='g')
    chart_loss_wrst = plt.plot(iter_domain, [min(exam_data[i].loss_accepted) for i in iter_gen], c='r')
    chart_loss_mean = plt.plot(iter_domain, [sum(exam_data[i].loss_accepted)/len(exam_data[i].loss_accepted)
                                             for i in iter_gen], c='b')

    plt.subplot(2, 1, 2)
    plt.title("Liczba zmian rozwązania")
    plt.xlabel("Iteracja algorytmu")

    chart_corc_pos = plt.plot(iter_domain, [exam_data[i].schedule_correction_pos_no for i in iter_gen], c='g')
    chart_corc_neg = plt.plot(iter_domain, [exam_data[i].schedule_correction_neg_no for i in iter_gen], c='r')
    chart_corc_nop = plt.plot(iter_domain, [exam_data[i].schedule_correction_nop_no for i in iter_gen], c='k')

    if path_to_save:
        plt.savefig(path_to_save + '_stat.eps', format='eps')
    fig.show()

    fig, ax = plt.subplots(1, 1)
    plt.suptitle("Optymalna wartość funkcji celu")
    plt.xlabel("Iteracja algorytmu")
    plt.plot(iter_domain, [exam_data[i].loss_cooldown for i in iter_gen], c='k')

    if path_to_save:
        plt.savefig(path_to_save + '_cooldown.eps', format='eps')
    fig.show()

    return tab_cells


def main():
    schedule_bindings = ScheduleBindings(
        params.assoc_pumps_set,
        params.workers2pumps_primary_binding,
        params.workers2pumps_secondary_binding,
        params.workers2unocc_shift_ixs_rigid_binding,
        params.workers2unocc_shift_ixs_optional_binding
    )
    schedule_shift_properties = ScheduleShiftProperites(
        params.shifts_per_day,
        params.shift_span,
        params.base_start_shift_offset,
        params.days_per_week,
        params.days_per_month
    )
    time_1 = datetime.now()

    init_schedule, init_temperature, init_aa_ratio = get_initial_opt_data(schedule_bindings, schedule_shift_properties)
    # print('init temp', init_temperature)
    print('init_loss', calc_loss_fcn_total(init_schedule))

    time_2 = datetime.now()

    opt_schedule, cutoff_temp, aci_exam_data = examine_annealing_core(init_schedule, init_temperature)
    print('opt loss', calc_loss_fcn_total(opt_schedule))

    time_3 = datetime.now()

    nie_pamietam, co_tu_bylo = visuals_n_exams.examine_schedule(init_schedule)
    aaa, bbb = visuals_n_exams.examine_schedule(opt_schedule)

    annealing_chart = visualise_annealing_exam_iter("Przebieg symulowanego wyżarzania", aci_exam_data,
                                                    examination_dir + "/annealing_chart")
    visuals_n_exams.visualise_schedule(init_schedule, "Harmonogram wstępny", examination_dir + "/init_schedule")
    init_chart = visuals_n_exams.visualise_schedule_exam(nie_pamietam, co_tu_bylo, "Harmonogram wstępny",
                                                         examination_dir + "/init_schedule_exam")
    visuals_n_exams.visualise_schedule(opt_schedule, "Harmonogram końcowy", examination_dir + "/opt_schedule")
    opt_chart = visuals_n_exams.visualise_schedule_exam(aaa, bbb, "Harmonogram końcowy",
                                                        examination_dir + "/opt_schedule_exam")

    visuals_n_exams.chart2csv(examination_dir + "/annealing.csv", annealing_chart)
    visuals_n_exams.chart2csv(examination_dir + "/init_schedule.csv", init_chart)
    visuals_n_exams.chart2csv(examination_dir + "/opt_schedule.csv", opt_chart)

    overall_exam = [
        ["init_temperature", "last_temperature", "randomization_time", "annealing_time", "init adjacency acceptance"],
        [init_temperature  , aci_exam_data[-1].temperature, time_2 - time_1     , time_3 - time_2, init_aa_ratio]
    ]
    visuals_n_exams.chart2csv(examination_dir + "/overall.csv", overall_exam)

    return aci_exam_data


if __name__ == '__main__':
    parameter_file = sys.argv[1]
    examination_dir = sys.argv[2]

    # parameter_file = "cases.params_std" #DG
    # examination_dir = "debug_data" #DG

    params = importlib.import_module("cases." + parameter_file)
    examination_dir = "exams/" + examination_dir
    os.mkdir(examination_dir)

    # random.seed(521478963258)  # default_seed = 382949082379

    constrs_set = [
        (constrs.is_violated__max_1_occ_shifts_in_adj_3x_seq, 0,
         params.violation_penatly__max_1_occ_shifts_in_curr_3x_seq),
        (constrs.is_violated__min_1_5x_unocc_seq_in_curr_week, params.days_per_week,
         params.violation_penatly__min_1_5x_unocc_seq_in_curr_week),
        (constrs.is_violated__max_6_occ_shifts_in_curr_week, params.days_per_week,
         params.violation_penatly__max_6_occ_shifts_in_curr_week),
        (constrs.is_violated__min_5_occ_shifts_in_curr_week, params.days_per_week,
         params.violation_penatly__min_5_occ_shifts_in_curr_week),
        (constrs.is_violated__min_1_unocc_sunday_in_curr_month, params.days_per_month,
         params.violation_penatly__min_1_unocc_sunday_in_curr_month),
        (constrs.is_violated__workers2unocc_shifts_rigid, 0, params.violation_penatly__workers2unocc_shifts_rigid),
        (
            constrs.is_violated__workers2unocc_shifts_optional, 0,
            params.violation_penatly__workers2unocc_shifts_optional),
        (constrs.is_violated__workers2occ_shift_primary, 0, params.violation_penatly__workers2occ_shift_primary)
    ]

    r = main()
    input("Wciśnij enter aby zakończyć i zamknąć okna")
