# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Objects defining the geometry of robot gestures and DUT measurements."""

from abc import ABC, abstractmethod
import math
import numpy as np
import TPPTAnalysisSW.transform2d as transform2d


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def from_polar(cls, r, phi, degrees=True):
        """Build a point given standard polar coordinates.

        Args:
            r: distance from origin
            phi: angle above the x axis. Note that the standard coordinate system is used, where x increases to
                the right, y increases upward, and phi increases counter-clockwise. This is different than the
                coordinate system used by TargetShape, where y increases downward.
            degrees: is phi given in  degrees or radians?
        """
        if degrees:
            phi = math.radians(phi)

        return Point(r * math.cos(phi), r * math.sin(phi))

    def distance(self, other):
        return math.hypot(other.x - self.x, other.y - self.y)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Point(self.x * other, self.y * other)

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        return Point(self.x / other, self.y / other)

    def __repr__(self):
        return 'Point({}, {})'.format(self.x, self.y)


class TargetShape(ABC):
    """Shapes drawn on the target panel.

    All coordinates should be from the top-left in mm. Each shape should represent something drawn by a single finger
    during the test.

    Attributes:
        mapped_measurements: list of measurement points that have been determined to belong to this TargetShape.
    """
    def __init__(self):
        self.mapped_measurements = []

    @abstractmethod
    def rms_error(self, measurement_points):
        """Given a list of measurement points, return the root-mean-square distance of from the TargetShape."""
        pass


class Line(TargetShape):
    """A single line drawn by the robot."""
    def __init__(self, start, end):
        super().__init__()
        self.start = Point(start.x, start.y)
        self.end = Point(end.x, end.y)

    @classmethod
    def list_from_db_line(cls, db_swipe):
        """Builds a list of Line objects based on a (possibly multi-finger) swipe gesture performed by the robot.

        Args:
            db_swipe: database object defining a swipe gesture.
                The following attributes are required, and should be from the top-left of the panel in mm:
                    start_x, start_y, end_x, end_y
                The following attributes are required for multi-finger swipes:
                    num_fingers
                    separation (mm): offset for subsequent lines after the first
                    azimuth (degrees): direction of offset, where 0 is to the right and increasing counter-clockwise
        Returns:
            List of Lines, as defined by db_swipe
        """
        if not hasattr(db_swipe, "separation"):
            return [Line(Point(db_swipe.start_x, db_swipe.start_y), Point(db_swipe.end_x, db_swipe.end_y))]

        separation = Point.from_polar(db_swipe.separation, -db_swipe.azimuth)

        lines = []
        for i in range(db_swipe.num_fingers):
            start = Point(db_swipe.start_x, db_swipe.start_y) + i * separation
            end = Point(db_swipe.end_x, db_swipe.end_y) + i * separation
            lines.append(Line(start, end))
        return lines

    @classmethod
    def list_from_db_pinch(cls, db_pinch):
        """Builds a list of Line objects based on a pinch gesture performed by the robot.

        Args:
            db_pinch: database object defining a pinch gesture.
                The following attributes are required:
                    center_x (mm), center_y (mm)
                    start_separation (mm), end_separation (mm): beginning and ending distance between fingers
                    azimuth (degrees): angle of pinch, where 0 is horizontal and increasing counter-clockwise
        Returns:
            List of Lines, as defined by db_pinch
        """
        center = Point(db_pinch.center_x, db_pinch.center_y)
        start_separation = Point.from_polar(db_pinch.start_separation, -db_pinch.azimuth)
        end_separation = Point.from_polar(db_pinch.end_separation, -db_pinch.azimuth)

        return [Line(center + start_separation / 2.0, center + end_separation / 2.0),
                Line(center - start_separation / 2.0, center - end_separation / 2.0)]

    @property
    def length(self):
        return self.start.distance(self.end)

    @property
    def angle(self):
        """Return angle in degrees of the line, where 0 is to the right and increasing counter-clockwise"""
        rads = -math.atan2(self.end.y - self.start.y, self.end.x - self.start.x)
        return np.degrees(rads)

    def rms_error(self, measurement_points):
        line_points = self.to_line_coordinates(measurement_points)
        errors = [p.y for p in line_points]
        return np.sqrt(np.mean(np.power(errors, 2)))

    def to_line_coordinates(self, measurement_points):
        """Transform a set of measurement points to line coordinates

        Args:
            measurement_points: List of Point objects in panel coordinates.
        Returns:
            List of Point objects in line coordinates, where the x value is the parallel distance along the Line from
            the start, and the y value is the perpendicular distance from the Line.
        """
        transform = (transform2d.Transform2D.offset(-self.start.x, -self.start.y) +
                     transform2d.Transform2D.rotate_degrees(self.angle))
        return transform.transform(measurement_points)


class TapPoint(TargetShape, Point):
    """A single point drawn by the robot."""
    def __init__(self, p):
        Point.__init__(self, p.x, p.y)
        TargetShape.__init__(self)

    @classmethod
    def list_from_db_tap(cls, db_tap):
        """Builds a list of TapPoint objects based on a (possibly multi-finger) tap gesture performed by the robot.

        Args:
            db_tap: database object defining a tap gesture.
                The following attributes are required, and should be from the top-left of the panel in mm:
                    tap_x, tap_y
                The following attributes are required for multi-finger swipes:
                    num_fingers
                    separation (mm): offset for subsequent TapPoints after the first
                    azimuth (degrees): direction of offset, where 0 is to the right and increasing counter-clockwise
        Returns:
            List of TapPoints, as defined by db_tap
        """
        if not hasattr(db_tap, "separation"):
            return [TapPoint(Point(db_tap.tap_x, db_tap.tap_y))]

        separation = Point.from_polar(db_tap.separation, -db_tap.azimuth)

        tap_points = []
        for i in range(db_tap.num_fingers):
            tap_points.append(TapPoint(Point(db_tap.tap_x, db_tap.tap_y) + i * separation))
        return tap_points

    @classmethod
    def list_from_db_drumroll(cls, db_drumroll):
        """Builds a list of TapPoint objects based on a drumroll gesture performed by the robot.

        Args:
            db_drumroll: database object defining a drumroll gesture.
                The following attributes are required:
                    center_x (mm), center_y (mm)
                    separation (mm): distance between fingers
                    azimuth (degrees): angle of drumroll, where 0 is horizontal and increasing counter-clockwise
        Returns:
            List of TapPoints, as defined by db_drumroll
        """
        center = Point(db_drumroll.center_x, db_drumroll.center_y)
        separation = Point.from_polar(db_drumroll.separation, -db_drumroll.azimuth)

        tap_points = [TapPoint(center + separation / 2.0),
                      TapPoint(center - separation / 2.0)]
        return tap_points

    def rms_error(self, measurement_points):
        errors = [self.distance(p) for p in measurement_points]
        return np.sqrt(np.mean(np.power(errors, 2)))


class Arc(TargetShape):
    """An arc drawn by the robot."""
    def __init__(self, db_compass):
        """Initializes an Arc based on a compass gesture performed by the robot.

        Args:
            db_compass: database object defining a compass gesture.
                The following attributes are required:
                    center_x (mm), center_y (mm): location of the stationary finger
                    separation (mm): distance between fingers
                    start_azimuth (degrees), end_azimuth: angle of moving finger relative to the stationary finger,
                        where 0 is horizontal and increasing counter-clockwise
        """
        super().__init__()
        self.center = Point(db_compass.center_x, db_compass.center_y)
        self.radius = db_compass.separation
        self.start_azimuth = db_compass.start_azimuth
        self.end_azimuth = db_compass.end_azimuth

    def rms_error(self, measurement_points):
        radii = [p.distance(self.center) for p in measurement_points]
        return np.sqrt(np.mean(np.power(np.subtract(radii, self.radius), 2)))
