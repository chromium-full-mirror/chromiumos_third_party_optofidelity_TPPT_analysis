# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromiumos file.

from abc import ABC
from collections import OrderedDict
from enum import Enum


def _format_score(score):
    return '{:.2f}'.format(score)


class Verdict(Enum):
    PASS = 'Pass'
    FAIL = 'Fail'
    BORDERLINE = 'Borderline'

    @classmethod
    def score_to_verdict(cls, score):
        if score == 1.0:
            return cls.PASS
        elif score == 0.0:
            return cls.FAIL
        elif 0.0 < score < 1.0:
            return cls.BORDERLINE
        raise ValueError('Score should be between 0.00 and 1.00, got: {:.2f}'.format(score))


class Comparator(Enum):
    LE = '<='
    GE = '>='
    EQ = '=='


class GestureValidator(ABC):
    """Validator to evaluate the performance of a single robot gesture relative to specification.

    Each subclass of GestureValidator must define the following class variables:
        name
        comparator: Comparator.LE: Passing values are equal to or below the limit.
                    Comparator.GE: Passing values are equal to or above the limit.
                    Comparator.EQ: Passing values are equal to the limit.
        limit: threshold for passing values.
        unit: physical unit of the value (e.g. 'mm')
        tolerance: If a value is beyond the limit by less than the tolerance, it is borderline. Any further and it
                   is failing.
        num_digits: Number of digits to display after the decimal point. Applies to limit, tolerance, and measured
                    value.
    """
    name: str
    comparator: Comparator
    limit: float
    unit: str
    tolerance: float
    num_digits: int

    def __init__(self, value, score=None):
        """Initialize a GestureValidator.

        Calculate the score and verdict given the provided value.

        Args:
            value: The value calculated for the given validator.
            score: May be provided if you don't want to calculate the score automatically. This option is used by the
                   TestCaseValidator, when aggregating the results across multiple gestures.
        """
        self.value = value
        if score is None:
            self._deviance, self.score = self._calculate_score()
        else:
            self._deviance, self.score = 0.0, score
        self.verdict = Verdict.score_to_verdict(self.score)

    def _calculate_score(self):
        """Calculates the score for this validator.

        If the value meets the spec, the score is 1.0.
        If the value fails the spec but is within the tolerance, the score is between 0.0 and 1.0.
        Otherwise, the score is 0.0.
        """
        if self.comparator == Comparator.LE:
            deviance = self.value - self.limit
        elif self.comparator == Comparator.GE:
            deviance = self.limit - self.value
        elif self.comparator == Comparator.EQ:
            deviance = abs(self.value - self.limit)
        else:
            raise ValueError('Validator has invalid comparator')

        if deviance <= 0:
            score = 1.0
        elif deviance > self.tolerance:
            score = 0.0
        else:
            score = (self.tolerance - deviance) / self.tolerance
        return deviance, score

    @property
    def spec_string(self):
        """Return a pretty version of the spec.

        For example: '<= 0.5 mm ~ 0.5'
        """
        ret = self.comparator.value + ' ' + self._format_num(self.limit)

        if self.unit:
            ret += ' ' + self.unit

        if self.tolerance > 0.0:
            ret += ' ~ ' + self._format_num(self.tolerance)
        return ret

    @property
    def value_string(self):
        return self._format_num(self.value)

    @property
    def score_string(self):
        return _format_score(self.score)

    def _format_num(self, num):
        format_str = '{:.' + str(self.num_digits) + 'f}'
        return format_str.format(num)

    @staticmethod
    def worst_case(first, second):
        if not isinstance(first, type(second)):
            raise ValueError("Validator types don't match")
        return first if first._deviance > second._deviance else second

    @staticmethod
    def best_case(first, second):
        if not isinstance(first, type(second)):
            raise ValueError("Validator types don't match")
        return first if first._deviance < second._deviance else second


class GestureValidatorCollection(OrderedDict):
    """Collection of different GestureValidators, all applied to the same gesture performed by the robot.

    OrderedDict where keys are GestureValidator subclasses, and the values are corresponding GestureValidators. If
    multiple GestureValidators of the same type are added, only the worst result is kept. This can happen if there
    are, for example, multiple lines in a single gesture and each is evaluated with a LinearityValidator.

    The worst overall score among all GestureValidators is tracked.
    """
    def __init__(self, *args):
        super().__init__()
        self._worst_score = 1.0
        for validator in args:
            self.add(validator)

    @property
    def score_string(self):
        return _format_score(self._worst_score)

    @property
    def verdict(self):
        return Verdict.score_to_verdict(self._worst_score)

    def add(self, validator):
        if not isinstance(validator, GestureValidator):
            raise TypeError('Wrong type added to GestureValidatorCollection: {}'.format(type(validator)))

        self._worst_score = min(self._worst_score, validator.score)
        if type(validator) not in self:
            self[type(validator)] = validator
        else:
            self[type(validator)] = GestureValidator.worst_case(validator, self[type(validator)])

    def merge(self, other):
        for validator in other.values():
            self.add(validator)


class TestCaseValidator:
    """Validator to track the performance of all gestures relative to a single specification.

    Multiple GestureValidators of the same subclass may be added to a TestCaseValidator. The TestCaseValidator will
    keep track of the mean, worst, and best results.
    """
    def __init__(self, gesture_validator):
        if not isinstance(gesture_validator, GestureValidator):
            raise TypeError('TestCaseValidator constructor must be called with a GestureValidator.')
        self.gesture_count = 1
        self.mean_gesture_validator = gesture_validator
        self.worst_gesture_validator = gesture_validator
        self.best_gesture_validator = gesture_validator

    @property
    def name(self):
        return self.mean_gesture_validator.name

    @property
    def spec_string(self):
        return self.mean_gesture_validator.spec_string

    def add(self, other):
        if not isinstance(other, GestureValidator):
            raise TypeError('Can only add GestureValidators to TestCaseValidator')
        if not isinstance(other, type(self.mean_gesture_validator)):
            raise ValueError("Can't add different GestureValidator types to a single TestCaseValidator")
        mean_value = (self.gesture_count * self.mean_gesture_validator.value + other.value) / (self.gesture_count + 1)
        mean_score = (self.gesture_count * self.mean_gesture_validator.score + other.score) / (self.gesture_count + 1)
        self.gesture_count += 1
        self.mean_gesture_validator = type(other)(mean_value, mean_score)
        self.worst_gesture_validator = GestureValidator.worst_case(self.worst_gesture_validator, other)
        self.best_gesture_validator = GestureValidator.best_case(self.best_gesture_validator, other)


class TestCaseValidatorCollection(OrderedDict):
    """Collection of TestCaseValidators for different subclasses of GestureValidator.

    OrderedDict where keys are GestureValidator subclasses, and the values are corresponding TestCaseValidators.
    Multiple GestureValidators of the same type can be added, and the corresponding TestCaseValidator will be updated.
    """
    @property
    def verdict(self):
        worst_mean_score = min(test_validator.mean_gesture_validator.score for test_validator in self.values())
        return Verdict.score_to_verdict(worst_mean_score)

    def add(self, validator):
        if not isinstance(validator, GestureValidator):
            raise TypeError('Can only add GestureValidators to TestCaseValidatorCollection')

        if type(validator) not in self:
            self[type(validator)] = TestCaseValidator(validator)
        else:
            self[type(validator)].add(validator)

    def merge(self, other):
        for validator in other.values():
            self.add(validator)


class StationaryMovementValidator(GestureValidator):
    name = 'Stationary Movement'
    comparator = Comparator.LE
    limit = 1.0
    unit = 'mm'
    tolerance = 0.0
    num_digits = 1


class MinimumEnclosingRadiusValidator(GestureValidator):
    name = 'Minimum Enclosing Radius'
    comparator = Comparator.LE
    limit = 0.5
    unit = 'mm'
    tolerance = 0.5
    num_digits = 1


class FingerCountValidator(GestureValidator):
    name = 'Finger Count Error'
    comparator = Comparator.EQ
    limit = 0
    unit = ''
    tolerance = 0
    num_digits = 0


class EdgeRangeValidator(GestureValidator):
    name = 'Edge Range'
    comparator = Comparator.LE
    limit = 0.5
    unit = 'mm'
    tolerance = 1.0
    num_digits = 1


class GapRatioValidator(GestureValidator):
    name = 'Gap Ratio'
    comparator = Comparator.LE
    limit = 1.8
    unit = ''
    tolerance = 1.0
    num_digits = 1


class ReversedMotionValidator(GestureValidator):
    comparator = Comparator.LE
    limit = 1.0
    unit = 'mm'
    tolerance = 0.5
    num_digits = 1


class ReversedMotionEndsValidator(ReversedMotionValidator):
    name = 'Reversed Motion at Ends'


class ReversedMotionMiddleValidator(ReversedMotionValidator):
    name = 'Reversed Motion in Middle'


class ReportRateValidator(GestureValidator):
    name = 'Report Rate'
    comparator = Comparator.GE
    limit = 60.0
    unit = 'Hz'
    tolerance = 0.0
    num_digits = 0


class MaxPathDeviationValidator(GestureValidator):
    comparator = Comparator.LE
    limit = 2.0
    unit = 'mm'
    tolerance = 1.0
    num_digits = 1


class MaxCircularityValidator(MaxPathDeviationValidator):
    name = 'Max Circularity Error'


class MaxLinearityValidator(MaxPathDeviationValidator):
    name = 'Max Linearity Error'


class RMSPathDeviationValidator(GestureValidator):
    comparator = Comparator.LE
    limit = 0.5
    unit = 'mm'
    tolerance = 0.5
    num_digits = 1


class RMSCircularityValidator(RMSPathDeviationValidator):
    name = 'RMS Circularity Error'


class RMSLinearityValidator(RMSPathDeviationValidator):
    name = 'RMS Linearity Error'


class DrumrollRadiusValidator(GestureValidator):
    name = 'Drumroll Radius'
    comparator = Comparator.LE
    limit = 2.0
    unit = 'mm'
    tolerance = 0.0
    num_digits = 1


class HysteresisValidator(GestureValidator):
    name = 'Hysteresis'
    comparator = Comparator.LE
    limit = 2.0
    unit = ''
    tolerance = 0.0
    num_digits = 1


class AngleValidator(GestureValidator):
    name = 'Angle Error'
    comparator = Comparator.LE
    limit = 2.5
    unit = 'degrees'
    tolerance = 2.5
    num_digits = 1


class SwipeLengthValidator(GestureValidator):
    name = 'Swipe Length Error'
    comparator = Comparator.LE
    limit = 2.0
    unit = 'mm'
    tolerance = 1.0
    num_digits = 1


class PacketCountValidator(GestureValidator):
    name = 'Packet Count'
    comparator = Comparator.GE
    limit = 3
    unit = ''
    tolerance = 3
    num_digits = 0