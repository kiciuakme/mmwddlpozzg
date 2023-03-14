from __future__ import annotations

from copy import copy, deepcopy
from typing import Dict, Generator, Set, Optional, Tuple, List
from nptyping import NDArray
import numpy
import random
from sys import maxsize

WorkerID = int
PumpID = int

WorkerIX = int
PumpIX = int
ShiftIX = int

ShiftNo = ShiftIX
ShiftOfDayIX = int


class ScheduleBindings:
    def __init__(self,
                 pumps_set: Set[PumpID],
                 workers2pumps_primary: Dict[WorkerID, PumpID],
                 workers2pumps_secondary: Dict[WorkerID, Set[PumpID]],
                 workers2unocc_shift_ix_rigid: Dict[WorkerID, Set[ShiftIX]],
                 workers2unocc_shift_ix_optional: Dict[WorkerID, Set[ShiftIX]]
                 ):
        self.w2ps_pri = workers2pumps_primary
        self.w2ps_sec = workers2pumps_secondary
        self.w2ps_uni = {worker_id: self.w2ps_sec[worker_id].union({self.w2ps_pri[worker_id]})
                         for worker_id in set(self.w2ps_pri.keys()).union(self.w2ps_sec.keys())}

        self.ps2w_pri = {pump_id: {worker_id for worker_id in self.w2ps_uni.keys()
                                   if pump_id == self.w2ps_pri[worker_id]} for pump_id in pumps_set}
        self.ps2w_sec = {pump_id: {worker_id for worker_id in self.w2ps_uni.keys()
                                   if pump_id in self.w2ps_sec[worker_id]} for pump_id in pumps_set}
        self.ps2w_uni = {pump_id: {worker_id for worker_id in self.w2ps_uni.keys()
                                   if pump_id in self.w2ps_uni[worker_id]} for pump_id in pumps_set}

        self.w2us_rig = workers2unocc_shift_ix_rigid
        self.w2us_opt = workers2unocc_shift_ix_optional


class ScheduleShiftProperites:
    def __init__(self, shifts_per_day: ShiftNo, shift_span: ShiftNo, base_start_shift_offset: ShiftIX,
                 days_per_week: int, days_per_month: int):
        self.shifts_per_day = shifts_per_day
        self.shift_span = shift_span
        self.base_start_shift_offset = base_start_shift_offset
        self.days_per_week = days_per_week
        self.days_per_month = days_per_month


class Schedule:
    def __init__(self, bindings: ScheduleBindings, shift_properties: ScheduleShiftProperites):
        self.bindings = bindings
        self.properties = shift_properties

        self.worker_ix2id = list(self.bindings.w2ps_uni.keys())
        self.worker_id2ix = {self.worker_ix2id[worker_ix]: worker_ix for worker_ix in range(len(self.worker_ix2id))}

        self.pump_ix2id = list(bindings.ps2w_uni.keys())
        self.pump_id2ix = {self.pump_ix2id[pump_ix]: pump_ix for pump_ix in range(len(self.pump_ix2id))}

        self._data = numpy.zeros((self.properties.shift_span, len(self.bindings.ps2w_uni), len(self.bindings.w2ps_uni)),
                                 dtype=bool)
        self._assoc_unoccupied = False

    def _worker_id2ix(self, worker_id: Optional[WorkerID]) -> WorkerIX:
        return self.worker_id2ix[worker_id]

    def _worker_ix2id(self, worker_ix: WorkerIX) -> WorkerID:
        return self.worker_ix2id[worker_ix]

    def _pump_id2ix(self, pump_id: Optional[PumpID]) -> PumpIX:
        return self.pump_id2ix[pump_id]

    def _pump_ix2id(self, pump_ix: PumpIX) -> PumpID:
        return self.pump_ix2id[pump_ix]

    def assoc_set(self, worker_id: WorkerID, pump_id: PumpID, shift_ix: ShiftIX) -> None:
        self._data[shift_ix, self._pump_id2ix(pump_id), self._worker_id2ix(worker_id)] = True

    def assoc_reset(self, worker_id: WorkerID, pump_id: PumpID, shift_ix: ShiftIX) -> None:
        self._data[shift_ix, self._pump_id2ix(pump_id), self._worker_id2ix(worker_id)] = False

    def assoc_is_occ(self, worker_id: Optional[WorkerID], pump_id: Optional[PumpID], shift_ix: ShiftIX) -> bool:
        if worker_id in self.worker_ix2id and pump_id in self.pump_ix2id:
            return self._data[
                       shift_ix, self._pump_id2ix(pump_id), self._worker_id2ix(worker_id)] != self._assoc_unoccupied
        if (worker_id not in self.worker_ix2id and worker_id is None) and pump_id in self.pump_ix2id:
            return numpy.any(self._data[shift_ix, self._pump_id2ix(pump_id), :] != self._assoc_unoccupied)
        if worker_id in self.worker_ix2id and (pump_id not in self.pump_ix2id and pump_id is None):
            return numpy.any(self._data[shift_ix, :, self._worker_id2ix(worker_id)] != self._assoc_unoccupied)
        raise Exception

    def assoc_get(self, worker_id: Optional[WorkerID], pump_id: Optional[PumpID], shift_ix: ShiftIX
                  ) -> Optional[bool, WorkerID, PumpID]:
        if worker_id in self.worker_ix2id and pump_id in self.pump_ix2id:
            return self._data[shift_ix, self._pump_id2ix(pump_id), self._worker_id2ix(worker_id)]
        if worker_id in self.worker_ix2id and (pump_id not in self.pump_ix2id and pump_id is None):
            pump_ix = numpy.where(self._data[shift_ix, :, self._worker_id2ix(worker_id)])[0][0]
            return self._pump_ix2id(pump_ix)
        if (worker_id not in self.worker_ix2id and worker_id is None) and pump_id in self.pump_ix2id:
            worker_ix = numpy.where(self._data[shift_ix, self._pump_id2ix(pump_id), :])[0][0]
            return self._worker_ix2id(worker_ix)
        raise Exception

    def iter_over_shifts(self) -> Generator[ShiftIX, None, None]:
        for shift_ix in range(self.properties.shift_span):
            yield ShiftIX(shift_ix)

    def iter_over_workers(self) -> Generator[WorkerID, None, None]:
        for worker_id in self.worker_ix2id:
            yield worker_id

    def iter_over_pumps(self) -> Generator[PumpID, None, None]:
        for pump_id in self.pump_ix2id:
            yield pump_id

    def flatten_over_workers(self) -> Schedule:
        schedule_fow = self.copy()
        while schedule_fow._assoc_unoccupied in self.bindings.ps2w_uni.keys():
            schedule_fow._assoc_unoccupied = random.randint(-maxsize, maxsize)
        schedule_fow._data = numpy.ones((self._data.shape[0], 1, self._data.shape[2]), dtype=PumpID)
        schedule_fow._data *= schedule_fow._assoc_unoccupied

        schedule_fow.pump_ix2id = [None]
        schedule_fow.pump_id2ix = {None: 0}

        for shift_ix in self.iter_over_shifts():
            for worker_id in self.iter_over_workers():
                if self.assoc_is_occ(worker_id, None, shift_ix):
                    pump_id = self.assoc_get(worker_id, None, shift_ix)
                    schedule_fow._data[shift_ix, 0, self._worker_id2ix(worker_id)] = pump_id

        return schedule_fow

    def flatten_over_pumps(self) -> Schedule:
        schedule_fop = self.copy()
        while schedule_fop._assoc_unoccupied in self.bindings.w2ps_uni.keys():
            schedule_fop._assoc_unoccupied = random.randint(-maxsize, maxsize)
        schedule_fop._data = numpy.ones(self._data.shape[:2] + (1,), dtype=WorkerID)
        schedule_fop._data *= schedule_fop._assoc_unoccupied

        schedule_fop.worker_ix2id = [None]
        schedule_fop.worker_id2ix = {None: 0}

        for shift_ix in self.iter_over_shifts():
            for pump_id in self.iter_over_pumps():
                if self.assoc_is_occ(None, pump_id, shift_ix):
                    worker_id = self.assoc_get(None, pump_id, shift_ix)
                    schedule_fop._data[shift_ix, pump_id, 0] = worker_id

        return schedule_fop

    def flatten_shifts_to_days(self) -> Schedule:
        """NB1. warunek - następuje tylko jedna zmiana w danym dniu 2. dostosowane tylko do s.fo_workers, s.fo_pumps"""
        first_day_shift_offset = self.properties.base_start_shift_offset % self.properties.shifts_per_day
        days_no = ((self.properties.shift_span + first_day_shift_offset) + (self.properties.shifts_per_day - 1)) \
                  // self.properties.shifts_per_day

        schedule_sod = self.copy()
        schedule_sod._assoc_unoccupied = -1
        schedule_sod.properties.shift_span = days_no
        schedule_sod.properties.shifts_per_day = 1
        schedule_sod._data = numpy.ones((days_no,) + self._data.shape[1:], dtype=ShiftOfDayIX)
        schedule_sod._data *= schedule_sod._assoc_unoccupied

        for shift_ix in self.iter_over_shifts():
            for pump_id in self.iter_over_pumps():
                for worker_id in self.iter_over_workers():
                    if self.assoc_is_occ(worker_id, pump_id, shift_ix):
                        day_ix = (first_day_shift_offset + shift_ix) // self.properties.shifts_per_day
                        shift_of_day_ix = (first_day_shift_offset + shift_ix) % self.properties.shifts_per_day
                        schedule_sod._data[day_ix, self._pump_id2ix(pump_id), self._worker_id2ix(worker_id)] \
                            = shift_of_day_ix

        return schedule_sod

    def convert_to_binary(self) -> Schedule:
        schedule_bin = copy(self)
        schedule_bin._data = (self._data != self._assoc_unoccupied).astype(int)
        schedule_bin._assoc_unoccupied = int(False)
        return schedule_bin

    def convert_to_shift_array(self, worker_id: Optional[WorkerID], pump_id: Optional[PumpID]
                               ) -> NDArray[Optional[bool, PumpID, WorkerID]]:
        return self._data[:, self._pump_id2ix(pump_id), self._worker_id2ix(worker_id)]

    def crop(self, new_shift_span: ShiftNo) -> Schedule:
        schedule_crop = copy(self)
        schedule_crop.properties.shift_span = new_shift_span
        schedule_crop._data = self._data[:new_shift_span]
        return schedule_crop

    def copy(self) -> Schedule:
        schedule_copy = copy(self)
        schedule_copy.properties = copy(self.properties)
        schedule_copy._data = deepcopy(self._data)
        return schedule_copy


FocusPeriodBndSet = Tuple[ShiftIX, ShiftIX, ShiftIX, ShiftIX, ShiftNo, ShiftNo]


def helper__get_focus_period_bnds(schedule: Schedule, shifts_no_per_period: ShiftNo, shift_ix: ShiftIX
                                  ) -> FocusPeriodBndSet:
    shift_ix_base = shift_ix + schedule.properties.base_start_shift_offset

    period_shift_ix_start = shift_ix_base - (shift_ix_base % shifts_no_per_period)
    period_shift_ix_end_ex = period_shift_ix_start + shifts_no_per_period

    period_shift_ix_start_ltd = max(period_shift_ix_start, ShiftIX(0))
    period_shift_ix_end_ex_ltd = min(period_shift_ix_end_ex, schedule.properties.shift_span)

    period_shift_no_out_of_schedule_before = period_shift_ix_start_ltd - period_shift_ix_start
    period_shift_no_out_of_schedule_after = period_shift_ix_end_ex - period_shift_ix_end_ex_ltd

    return ShiftIX(period_shift_ix_start), ShiftIX(period_shift_ix_end_ex), \
           ShiftIX(period_shift_ix_start_ltd), ShiftIX(period_shift_ix_end_ex_ltd), \
           ShiftNo(period_shift_no_out_of_schedule_before), ShiftNo(period_shift_no_out_of_schedule_after)


def helper__get_focus_day_bnds(schedule: Schedule, shift_ix: ShiftIX) -> FocusPeriodBndSet:
    shift_no_per_day = schedule.properties.shifts_per_day
    return helper__get_focus_period_bnds(schedule, shift_no_per_day, shift_ix)


def helper__get_focus_week_bnds(schedule: Schedule, shift_ix: ShiftIX) -> FocusPeriodBndSet:
    shift_no_per_week = schedule.properties.days_per_week * schedule.properties.shifts_per_day
    return helper__get_focus_period_bnds(schedule, shift_no_per_week, shift_ix)


def helper__get_focus_month_bnds(schedule: Schedule, shift_ix: ShiftIX) -> FocusPeriodBndSet:
    shift_no_per_month = schedule.properties.days_per_month * schedule.properties.shifts_per_day
    return helper__get_focus_period_bnds(schedule, shift_no_per_month, shift_ix)


def helper__get_schedule_shift_date(schedule: Schedule, shift_ix: ShiftIX) -> Tuple[int, int, int, int]:
    bsso = schedule.properties.base_start_shift_offset
    spd = schedule.properties.shifts_per_day
    shift = (bsso + shift_ix) % spd
    day = ((bsso + shift_ix) % (spd * schedule.properties.days_per_week)) // spd
    week = (bsso + shift_ix) // (spd * schedule.properties.days_per_week)
    month = (bsso + shift_ix) // (spd * schedule.properties.days_per_month)
    return shift, day, week, month
