# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromiumos file.

from collections import namedtuple
import unittest

from TPPTAnalysisSW.measurements import MeasurementList
from TPPTAnalysisSW.shapes import TargetShape
from optofidelity_protocols.dut import Action


class MockMeasurementPoint:
    def __init__(self, finger_id=0, event=Action.MOVE):
        self.finger_id = finger_id
        self.event = event


class MockShape(TargetShape):
    def __init__(self, error=0.0):
        super().__init__()
        self.error = error

    def rms_error(self, measurement_list):
        return self.error


class MeasurementListTests(unittest.TestCase):
    def test_single_mapping_with_extra_touches(self):
        finger_ids = [0, 0, 0,
                      1, 1,
                      2, 2, 2,
                      3, 3]
        measurements = MeasurementList([MockMeasurementPoint(finger_id=fid) for fid in finger_ids])
        measurements.num_touches = 4
        shapes = [MockShape(error) for error in range(2)]
        unmapped_measurements = measurements.assign_to_target_shapes(shapes)

        for shape in shapes:
            # There are more touches than shapes, so each should have mapped measurements
            self.assertGreater(len(shape.mapped_measurements), 0)

            # Only the touches with the most measurements should be mapped
            self.assertTrue(shape.mapped_measurements[0].finger_id == 0 or
                            shape.mapped_measurements[0].finger_id == 2)

            # All measurements should be from the same touch
            mapped_ids = [m.finger_id for m in shape.mapped_measurements]
            for fid in mapped_ids:
                self.assertEqual(mapped_ids[0], fid)

        # All measurements should be mapped to a shape, or dumped into unmapped_measurements
        self.assertEqual(len(shapes[0].mapped_measurements), 3)
        self.assertEqual(len(shapes[1].mapped_measurements), 3)
        self.assertEqual(len(unmapped_measurements), 4)

    def test_single_mapping_with_insufficient_touches(self):
        finger_ids = [0, 0,
                      1, 1, 1]
        measurements = MeasurementList([MockMeasurementPoint(finger_id=fid) for fid in finger_ids])
        measurements.num_touches = 2
        shapes = [MockShape(error) for error in range(3)]
        unmapped_measurements = measurements.assign_to_target_shapes(shapes)

        for shape in shapes:
            # All measurements should be from the same touch
            mapped_ids = [m.finger_id for m in shape.mapped_measurements]
            for fid in mapped_ids:
                self.assertEqual(mapped_ids[0], fid)

        # shape[0] has the lowest rms_error so the touch with most measurements should be mapped to it
        self.assertEqual(len(shapes[0].mapped_measurements), 3)
        self.assertEqual(shapes[0].mapped_measurements[0].finger_id, 1)

        # shape[1] has the next lowest rms_error so the remainig touch should be mapped to it
        self.assertEqual(len(shapes[1].mapped_measurements), 2)
        self.assertEqual(shapes[1].mapped_measurements[0].finger_id, 0)

        # All measurements should be mapped to a shape, leaving none for unmapped_measurements
        self.assertEqual(len(unmapped_measurements), 0)

    def test_multiple_mapping(self):
        finger_ids = [0, 0, 0,
                      1, 1,
                      2, 2, 2,
                      3, 3]
        measurements = MeasurementList([MockMeasurementPoint(finger_id=fid) for fid in finger_ids])
        measurements.num_touches = 4
        shapes = [MockShape(error) for error in range(3)]
        unmapped_measurements = measurements.assign_to_target_shapes(shapes, single_touch_per_shape=False)

        # All measurements should be mapped to shape[0], which always has the smallest rms_error
        self.assertEqual(len(shapes[0].mapped_measurements), len(measurements))

        # Remaining shapes should have no measurements mapped to them
        for shape in shapes[1:]:
            self.assertEqual(len(shape.mapped_measurements), 0)
        self.assertEqual(len(unmapped_measurements), 0)

    def test_assign_unique_finger_ids(self):
        MeasTuple = namedtuple('MeasTuple', ['old_id', 'event', 'new_id'])
        meas_tuples = [MeasTuple(0, Action.DOWN, 0),
                       MeasTuple(0, Action.MOVE, 0),
                       MeasTuple(1, Action.DOWN, 1),
                       MeasTuple(0, Action.UP  , 0),
                       MeasTuple(1, Action.MOVE, 1),
                       MeasTuple(0, Action.DOWN, 2),
                       MeasTuple(0, Action.MOVE, 2)]

        measurements = MeasurementList([MockMeasurementPoint(finger_id=m.old_id, event=m.event)
                                        for m in meas_tuples])
        measurements._assign_unique_finger_ids()
        for i, measurement in enumerate(measurements):
            self.assertEqual(measurement.finger_id, meas_tuples[i].new_id)


if __name__ == '__main__':
    unittest.main()
