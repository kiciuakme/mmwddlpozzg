from utils import *
from utils import helper__get_focus_week_bnds, helper__get_focus_month_bnds


def is_violated__max_1_occ_shifts_in_adj_3x_seq(shedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    focus_sa = shedule.flatten_over_workers().convert_to_binary().convert_to_shift_array(worker_id, None)
    for six_seq_start_offset in (-2, -1, 0):
        six_seq_start = max(0, shift_ix + six_seq_start_offset)
        six_seq_endex = min(shedule.properties.shift_span, six_seq_start + 3)

        focus_seq = focus_sa[six_seq_start:six_seq_endex]
        if numpy.sum(focus_seq) > 1:
            return True
    else:
        return False


def is_violated__min_1_5x_unocc_seq_in_curr_week(shedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    """NB: Przyporządkowanie ciągu do tygodnia na podstawie ostatniej zmiany"""
    wsix_start, wsix_endex, wsix_start_ltd, wsix_endex_ltd = helper__get_focus_week_bnds(shedule, shift_ix)[:4]
    focus_sa = shedule.flatten_over_workers().convert_to_binary().convert_to_shift_array(worker_id, None)

    for ssix_end_inc in range(wsix_start, wsix_endex):
        ssix_end_ex = ssix_end_inc + 1
        ssix_start = max(ssix_end_ex - 5, 0)

        if numpy.all(focus_sa[ssix_start:ssix_end_ex] == 0):
            return False
    else:
        return True


def is_violated__max_6_occ_shifts_in_curr_week(schedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    wsix_start_ltd, wsix_endex_ltd = helper__get_focus_week_bnds(schedule, shift_ix)[2:4]

    focus_sa = schedule.flatten_over_workers().convert_to_binary().convert_to_shift_array(worker_id, None)
    focus_week = focus_sa[wsix_start_ltd:wsix_endex_ltd]
    return numpy.sum(focus_week) > 6


def is_violated__min_5_occ_shifts_in_curr_week(schedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    wsix_start_ltd, wsix_endex_ltd, wsix_start_oos, wsix_endex_oos = helper__get_focus_week_bnds(schedule, shift_ix)[2:]

    focus_sa = schedule.flatten_over_workers().convert_to_binary().convert_to_shift_array(worker_id, None)
    focus_week = focus_sa[wsix_start_ltd:wsix_endex_ltd]
    focus_week_oos = wsix_start_oos + wsix_endex_oos
    return numpy.sum(focus_week) + focus_week_oos < 5


def is_violated__min_1_unocc_sunday_in_curr_month(schedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    msix_start, msix_endex = helper__get_focus_month_bnds(schedule, shift_ix)[:2]
    dpw = schedule.properties.days_per_week
    for week_shift_ix in range(msix_start, msix_endex, dpw * schedule.properties.shifts_per_day):
        wsix_start, wsix_endex = helper__get_focus_week_bnds(schedule, ShiftIX(week_shift_ix))[:2]

        focus_shift_array = schedule.flatten_over_workers().convert_to_binary().convert_to_shift_array(worker_id, None)
        sunday_start_shift_ix = max(0, wsix_endex - 3)
        sunday_endex_shift_ix = wsix_endex
        if numpy.all(focus_shift_array[sunday_start_shift_ix:sunday_endex_shift_ix] == 0):
            return False
    else:
        return True


def is_violated__workers2unocc_shifts_rigid(shedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    if shedule.assoc_is_occ(worker_id, None, shift_ix):
        return shift_ix in shedule.bindings.w2us_rig[worker_id]
    else:
        return False


def is_violated__workers2unocc_shifts_optional(shedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    if shedule.assoc_is_occ(worker_id, None, shift_ix):
        return shift_ix in shedule.bindings.w2us_opt[worker_id]
    else:
        return False


def is_violated__workers2occ_shift_primary(schedule: Schedule, worker_id: WorkerID, shift_ix: ShiftIX) -> bool:
    if schedule.assoc_is_occ(worker_id, None, shift_ix):
        occ_pump_id = schedule.assoc_get(worker_id, None, shift_ix)
        return occ_pump_id != schedule.bindings.w2ps_pri[worker_id]
    else:
        return False
