from utils import *
import matplotlib.pyplot as plt

import constraints as constrs

Chart = List


def visualise_schedule(schedule: Schedule, title: str, path_to_save: str):
    shifts_no = schedule.properties.shift_span
    workers_no = len(schedule.bindings.w2ps_uni)
    pumps_no = len(schedule.bindings.ps2w_uni)
    fig = plt.figure(figsize=(2 + .7 * shifts_no, 5 + .25 * (workers_no + pumps_no)))
    plt.suptitle(title)

    shifts_list = []
    bsso = schedule.properties.base_start_shift_offset
    for shift_ix in schedule.iter_over_shifts():
        shift, day, week, month = helper__get_schedule_shift_date(schedule, shift_ix)
        week_ssix = helper__get_focus_week_bnds(schedule, shift_ix)[2]
        month_ssix = helper__get_focus_month_bnds(schedule, shift_ix)[2]

        tick = ""
        tick += "M{}".format(month + 1) if bsso + shift_ix == month_ssix or shift_ix == 0 else ""
        tick += "W{}".format(week + 1) if bsso + shift_ix == week_ssix or shift_ix == 0 else ""
        tick += "D{}".format(day + 1) if shift == 0 or shift_ix == 0 else ""
        tick += "S{}".format(shift + 1)
        shifts_list.append(tick)
    shifts_list.append("X")

    plt.subplot(2, 1, 1)
    plt.title("Przydział pracowników")
    plt.ylabel("ID pracownika")
    plt.ylim((-.5, workers_no-.5))
    plt.xlim((-.25, shifts_no+.25))
    plt.grid(markevery=None, color='k')
    plt.xticks([shift_ix for shift_ix, _ in enumerate(shifts_list)],
               [shift_tick for shift_tick in shifts_list], rotation=-35)

    workers_list = sorted([worker_id for worker_id in schedule.iter_over_workers()], reverse=True)
    plt.yticks([worker_ix for worker_ix, _ in enumerate(workers_list)],
               ["W:{:>2}".format(worker_id) for worker_id in workers_list])

    for worker_ix, worker_id in enumerate(workers_list):
        plt.plot((-.25, shifts_no+.25), (worker_ix,) * 2, color='gray', linewidth=5)
        for shift_ix in schedule.iter_over_shifts():
            if schedule.assoc_is_occ(worker_id, None, shift_ix):
                assoc_pump_id = schedule.assoc_get(worker_id, None, shift_ix)
                plt.plot((shift_ix+.1, shift_ix + .9), (worker_ix,) * 2, color='red', linewidth=10)
                plt.plot(shift_ix + .5, worker_ix, color='k', marker='$P:{:>2}$'.format(assoc_pump_id), markersize=20)

    plt.subplot(2, 1, 2, aspect=1)
    plt.title("Przydział przepompowni")
    plt.ylabel("ID przepompowni")
    plt.xlabel("Przydział zmian")
    plt.ylim((-.5, pumps_no - .5))
    # plt.xlabel("Day assignment")
    plt.xlim((-.25, shifts_no + .25))
    plt.grid(markevery=None, color='k')
    plt.xticks([shift_ix for shift_ix, _ in enumerate(shifts_list)],
               [shift_tick for shift_tick in shifts_list], rotation=-35)

    pumps_list = sorted([pump_id for pump_id in schedule.iter_over_pumps()], reverse=True)
    plt.yticks([pump_ix for pump_ix, _ in enumerate(pumps_list)],
               ["P:{:>2}".format(pump_id) for pump_id in pumps_list])

    for pump_ix, pump_id in enumerate(pumps_list):
        plt.plot((-.25, shifts_no+.25), (pump_ix,) * 2, color='gray', linewidth=5)
        for shift_ix in schedule.iter_over_shifts():
            assoc_pump_id = schedule.assoc_get(None, pump_id, shift_ix)
            plt.plot((shift_ix+.1, shift_ix + .9), (pump_ix,) * 2, color='red', linewidth=10)
            plt.plot(shift_ix + .5, pump_ix, color='k', marker='$W:{:>2}$'.format(assoc_pump_id), markersize=20)

    if path_to_save:
        plt.savefig(path_to_save + '.eps', format='eps')
    fig.show()


class ScheduleExaminationWorkerData:
    def __init__(self, schedule: Schedule):
        last_week_ix_inc, last_month_ix_inc = helper__get_schedule_shift_date(schedule,
                                                                              schedule.properties.shift_span - 1)[2:]

        self.weekly_assoc = [0 for _ in range(last_week_ix_inc + 1)]  # week_ix -> occ_shift_no
        self.monthly_assoc = [0 for _ in range(last_month_ix_inc + 1)]
        self.shiftly_assoc_total = [0 for _ in range(schedule.properties.shifts_per_day)]
        self.mean_occ_day_seq_length = 0.
        self.no_sec_assoc_violation_no = 0
        self.optional_unocc_shifts_violation_no = 0


def examine_schedule(schedule: Schedule) -> Tuple[Dict[WorkerID, ScheduleExaminationWorkerData], Tuple[int, int, int]]:
    exam_data = {}
    daily_workers_schedule = schedule.flatten_over_workers().flatten_shifts_to_days()

    for worker_id in schedule.iter_over_workers():
        exam_data[worker_id] = ScheduleExaminationWorkerData(schedule)

        for shift_ix in schedule.iter_over_shifts():
            week_ix, month_ix = helper__get_schedule_shift_date(schedule, shift_ix)[2:]

            if schedule.assoc_is_occ(worker_id, None, shift_ix):
                exam_data[worker_id].weekly_assoc[week_ix] += 1
                exam_data[worker_id].monthly_assoc[month_ix] += 1

                if constrs.is_violated__workers2occ_shift_primary(schedule, worker_id, shift_ix):
                    exam_data[worker_id].no_sec_assoc_violation_no += 1

                if constrs.is_violated__workers2unocc_shifts_optional(schedule, worker_id, shift_ix):
                    exam_data[worker_id].optional_unocc_shifts_violation_no += 1

        total_occ_days_ctr = 0
        seq_ctr = 1 if daily_workers_schedule.assoc_is_occ(worker_id, None, 0) else 0
        for day_ix in daily_workers_schedule.iter_over_shifts():
            if daily_workers_schedule.assoc_is_occ(worker_id, None, day_ix):
                assoc_shift_ix = daily_workers_schedule.assoc_get(worker_id, None, day_ix)
                exam_data[worker_id].shiftly_assoc_total[assoc_shift_ix] += 1

                total_occ_days_ctr += 1
                if day_ix == 0:
                    continue
                if not daily_workers_schedule.assoc_is_occ(worker_id, None, day_ix - 1):
                    seq_ctr += 1
        try:
            exam_data[worker_id].mean_occ_day_seq_length = total_occ_days_ctr / seq_ctr
        except ZeroDivisionError:
            exam_data[worker_id].mean_occ_day_seq_length = 0

    probe_exam_data = ScheduleExaminationWorkerData(schedule)
    shift_no = len(probe_exam_data.shiftly_assoc_total)
    week_no = len(probe_exam_data.weekly_assoc)
    month_no = len(probe_exam_data.monthly_assoc)

    return exam_data, (shift_no, week_no, month_no)


def visualise_schedule_exam(exam_data: Dict[WorkerID, ScheduleExaminationWorkerData],
                            period_cells_no: Tuple[int, int, int], title: str, path_to_save: str) -> Chart:
    shift_no = period_cells_no[0]
    week_no = period_cells_no[1]
    month_no = period_cells_no[2]

    tab_cells = []
    head_row = [
        "W:ID",  # "Worker's ID",
        *["W{}".format(week_ix + 1) for week_ix in range(week_no)],
        *["M{}".format(month_ix + 1) for month_ix in range(month_no)],
        "ShS%",  # "Shift share %",
        "AvSL",  # "Avg occ seq len",
        "ScPA",  # "Sec pump assigns",
        "OpRF",  # "Opt request fails"
    ]
    tab_cells.append(head_row)

    for worker_id, worker_data in exam_data.items():
        try:
            sat = "/".join(["{:.0f}".format(100 * exam_data[worker_id].shiftly_assoc_total[i] /
                                            sum(exam_data[worker_id].shiftly_assoc_total)) for i in range(shift_no)])
        except ZeroDivisionError:
            sat = "0/0/0"

        worker_row = [
            worker_id,
            *exam_data[worker_id].weekly_assoc,
            *exam_data[worker_id].monthly_assoc,
            sat,
            "{:.2f}".format(exam_data[worker_id].mean_occ_day_seq_length),
            exam_data[worker_id].no_sec_assoc_violation_no,
            exam_data[worker_id].optional_unocc_shifts_violation_no
        ]
        tab_cells.append(worker_row)

    fig, ax = plt.subplots()
    ax.set_axis_off()
    tabax = ax.table(tab_cells, cellLoc='center', loc='upper left')
    tabax.auto_set_font_size(False)
    tabax.set_fontsize(12)
    ax.set_title(title)

    if path_to_save:
        plt.savefig(path_to_save + '.eps', format='eps')
    fig.show()
    return tab_cells


def chart2csv(title: str, chart: Chart) -> None:
    txt_rows = [', '.join([str(cell_data) for cell_data in row_data]) + '\n' for row_data in chart]
    with open(title, "w") as file:
        file.writelines(txt_rows)
