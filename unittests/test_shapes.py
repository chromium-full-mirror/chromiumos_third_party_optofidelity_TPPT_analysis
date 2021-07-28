# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromiumos file.

import math
import unittest
from collections import namedtuple

from TPPTAnalysisSW.shapes import Arc, Point

MockDbCompass = namedtuple('MockDbCompass', ['center_x', 'center_y', 'separation', 'start_azimuth', 'end_azimuth'])


class ArcTests(unittest.TestCase):
    def test_clockwise_arc_path_mapping(self):
        arc = Arc(MockDbCompass(center_x=30.0, center_y=30.0, separation=20.0, start_azimuth=180.0, end_azimuth=45.0))
        measurements = [Point(30.0, 50.0),
                        Point(30.0, 55.0),
                        Point(30.0, 45.0),
                        Point(10.0, 30.0),
                        Point(5.0, 30.0),
                        Point(15.0, 30.0),
                        Point(30.0, 10.0),
                        Point(30.0, 5.0),
                        Point(30.0, 15.0),
                        Point(50.0, 30.0),
                        Point(55.0, 30.0),
                        Point(45.0, 30.0)
                        ]
        mapped_points = arc.to_path_coordinates(measurements)

        circumference = 2.0 * arc.radius * math.pi
        expected_points = [Point(-circumference / 4.0, 0.0),
                           Point(-circumference / 4.0, 5.0),
                           Point(-circumference / 4.0, -5.0),
                           Point(0.0, 0.0),
                           Point(0.0, 5.0),
                           Point(0.0, -5.0),
                           Point(circumference / 4.0, 0.0),
                           Point(circumference / 4.0, 5.0),
                           Point(circumference / 4.0, -5.0),
                           Point(circumference / 2.0, 0.0),
                           Point(circumference / 2.0, 5.0),
                           Point(circumference / 2.0, -5.0)
                           ]

        for mapped_point, expected_point in zip(mapped_points, expected_points):
            self.assertEqual(mapped_point, expected_point)

    def test_counter_clockwise_arc_path_mapping(self):
        arc = Arc(MockDbCompass(center_x=30.0, center_y=30.0, separation=20.0, start_azimuth=90.0, end_azimuth=225.0))
        measurements = [Point(30.0, 50.0),
                        Point(30.0, 55.0),
                        Point(30.0, 45.0),
                        Point(10.0, 30.0),
                        Point(5.0, 30.0),
                        Point(15.0, 30.0),
                        Point(30.0, 10.0),
                        Point(30.0, 5.0),
                        Point(30.0, 15.0),
                        Point(50.0, 30.0),
                        Point(55.0, 30.0),
                        Point(45.0, 30.0)
                        ]
        mapped_points = arc.to_path_coordinates(measurements)

        circumference = 2.0 * arc.radius * math.pi
        expected_points = [Point(circumference / 2.0, 0.0),
                           Point(circumference / 2.0, 5.0),
                           Point(circumference / 2.0, -5.0),
                           Point(circumference / 4.0, 0.0),
                           Point(circumference / 4.0, 5.0),
                           Point(circumference / 4.0, -5.0),
                           Point(0.0, 0.0),
                           Point(0.0, 5.0),
                           Point(0.0, -5.0),
                           Point(-circumference / 4.0, 0.0),
                           Point(-circumference / 4.0, 5.0),
                           Point(-circumference / 4.0, -5.0)
                           ]

        for mapped_point, expected_point in zip(mapped_points, expected_points):
            self.assertEqual(mapped_point, expected_point)

