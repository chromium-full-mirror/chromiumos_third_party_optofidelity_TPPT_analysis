# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromiumos file.

import math
from collections import UserList

import TPPTAnalysisSW.transform2d as transform2d
from TPPTAnalysisSW.shapes import Point
from optofidelity_protocols.dut import Action


class MeasurementPoint(Point):
    """A touch point as measured by the touch panel."""
    def __init__(self, db_result):
        super().__init__(db_result.panel_x, db_result.panel_y)
        self.pressure = db_result.pressure
        self.time = db_result.time
        self.event = db_result.event
        self.finger_id = db_result.finger_id


class MeasurementList(UserList):
    """A list of points collected by the touch panel during a single gesture.

    Attributes:
        data: List of measurement points, with coordinates given from the top-left in mm, and with each continuous
            touch assigned a unique finger id.
        num_touches: Number of continuous touches.
    """
    def __init__(self, initlist=None):
        """Required constructor for UserList subclass.

        See the docs [0] if you want to modify this constructor.

        [0]: https://docs.python.org/3/library/collections.html#userlist-objects
        """
        super().__init__(initlist)

    @classmethod
    def from_db_results(cls, db_results, dut_info, remove_early=0.0):
        """Builds a MeasurementList from database entries.

        Performs coordinate scaling, assigns unique finger ids to measurements, and filters early points if required.

        Args:
            db_results: list of measurements from database. Assumed to be in ordered by measurement time.
            dut_info: database object defining the dimensions of the DUT.
            remove_early: How many seconds (s) of measurements to remove from the beginning of the results.
        """
        unscaled_measurements = [MeasurementPoint(result) for result in db_results]
        scaled_measurements = MeasurementList._panel_to_mm(unscaled_measurements, dut_info)
        ret = MeasurementList(scaled_measurements)
        ret._remove_early_points(remove_early)
        ret._assign_unique_finger_ids()
        return ret

    def assign_to_target_shapes(self, shapes, single_touch_per_shape=True):
        """Map each continuous touch to the closest target shape.

        For each continuous touch, use each shape's rms_error method, and assign all measurements from that touch to
        the shape with the lowest error.

        If single_touch_per_shape is True, only one touch may be assigned to each shape. In this case, we consider the
        touches with the most measurements first. If there are more touches than shapes, then the remaining touches
        are returned.
        """
        unmapped_measurements = []
        touches_by_id = [[m for m in self.data if m.finger_id == finger_id]
                         for finger_id in range(self.num_touches)]
        touches_by_length = sorted(touches_by_id, key=len, reverse=True)
        num_to_assign = len(shapes) if single_touch_per_shape else self.num_touches

        for touch in touches_by_length[:num_to_assign]:
            min_error = math.inf
            for shape in shapes:
                if single_touch_per_shape and shape.mapped_measurements:
                    continue
                shape_error = shape.rms_error(touch)
                if min_error > shape_error:
                    min_error, best_shape = shape_error, shape
            best_shape.mapped_measurements.extend(touch)

        for touch in touches_by_length[num_to_assign:]:
            unmapped_measurements.extend(touch)
        return unmapped_measurements

    def _assign_unique_finger_ids(self):
        """Ensure that each continuous touch has a unique finger id.

        It is possible for a single finger id to be re-used by multiple touches in the measurement database. This
        function reassigns finger ids so each touch has a unique finger id, assigned sequentially.

        Example:
        old id | Action | new id
        -------|--------|-------
           0   |  DOWN  | 0
           0   |  MOVE  | 0
           1   |  DOWN  | 1
           0   |  UP    | 0
           1   |  MOVE  | 1
           0   |  DOWN  | 2
           0   |  MOVE  | 2
        """
        old_id_to_new = {}
        num_unique = 0

        for measurement in self.data:
            old_id = measurement.finger_id
            if old_id not in old_id_to_new:
                old_id_to_new[old_id] = num_unique
                num_unique += 1

            measurement.finger_id = old_id_to_new[old_id]

            if measurement.event == Action.UP:
                del old_id_to_new[old_id]

        self.num_touches = num_unique

    def _remove_early_points(self, remove_early):
        """Remove early measurements.

        Args:
            remove_early: time in seconds (s) to remove from start of measurements.
        """
        if remove_early == 0.0 or len(self.data) == 0:
            return

        start = self.data[0].time
        for i, point in enumerate(self.data):
            if point.time >= start + remove_early * 1000:
                self.data = self.data[i:]
                return

        self.data = []

    @staticmethod
    def _panel_to_mm(points, dut_info):
        """Transform MeasurementPoints from panel measurements to distance from top-left of the panel in mm"""
        size_mm = Point(*dut_info.dimensions)                # Size of target (in mm)
        size_panel = Point(*dut_info.digitizer_resolution)   # Max reported values
        offset_mm = Point(*dut_info.offset)                  # Offset of panel->target conversion (in mm)

        flip_transform = transform2d.Transform2D.identity()
        if dut_info.switchxy:
            flip_transform = flip_transform + transform2d.Transform2D([[0, 1, 0], [1, 0, 0]])
        if dut_info.flipx:
            flip_transform = flip_transform + transform2d.Transform2D([[-1, 0, size_panel.x], [0, 1, 0]])
        if dut_info.flipy:
            flip_transform = flip_transform + transform2d.Transform2D([[1, 0, 0], [0, -1, size_panel.y]])

        scale_x = size_mm.x / size_panel.x
        scale_y = size_mm.y / size_panel.y
        scale_transform = transform2d.Transform2D.scale(scale_x, scale_y)

        offset_transform = transform2d.Transform2D.offset(offset_mm.x, offset_mm.y)

        full_transform = flip_transform + scale_transform + offset_transform
        return full_transform.transform(points)
