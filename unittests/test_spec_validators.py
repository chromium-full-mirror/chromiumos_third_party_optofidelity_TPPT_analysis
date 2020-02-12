# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromiumos file.

import unittest

from TPPTAnalysisSW.spec_validators import (Comparator, GestureValidator, GestureValidatorCollection, TestCaseValidator,
                                            TestCaseValidatorCollection, Verdict)


class MockLEValidator(GestureValidator):
    name = 'LE'
    comparator = Comparator.LE
    limit = 1.0
    unit = 'mm'
    tolerance = 1.0
    num_digits = 3


class MockEQValidator(GestureValidator):
    name = 'EQ'
    comparator = Comparator.EQ
    limit = 1
    unit = ''
    tolerance = 0
    num_digits = 0


class GestureValidatorTests(unittest.TestCase):
    def test_score(self):
        passing_validator = MockLEValidator(0.5)
        borderline_validator = MockLEValidator(1.5)
        failing_validator = MockLEValidator(2.5)

        self.assertEqual(passing_validator.score, 1.0)
        self.assertEqual(borderline_validator.score, 0.5)
        self.assertEqual(failing_validator.score, 0.0)

        self.assertEqual(passing_validator.verdict, Verdict.PASS)
        self.assertEqual(borderline_validator.verdict, Verdict.BORDERLINE)
        self.assertEqual(failing_validator.verdict, Verdict.FAIL)

    def test_strings(self):
        validator = MockLEValidator(1.5)

        self.assertEqual(validator.spec_string, '<= 1.000 mm ~ 1.000')
        self.assertEqual(validator.score_string, '0.50')
        self.assertEqual(validator.value_string, '1.500')

        eq_validator = MockEQValidator(2)

        self.assertEqual(eq_validator.spec_string, '== 1')
        self.assertEqual(eq_validator.score_string, '0.00')
        self.assertEqual(eq_validator.value_string, '2')

    def test_comparison(self):
        very_passing_validator = MockLEValidator(0.0)
        barely_passing_validator = MockLEValidator(0.5)
        borderline_validator = MockLEValidator(1.5)
        barely_failing_validator = MockLEValidator(2.5)
        very_failing_validator = MockLEValidator(10.0)

        # Even when comparing two passing or failing validators, keep track of which is better.
        self.assertIs(GestureValidator.worst_case(barely_passing_validator, very_passing_validator),
                      barely_passing_validator)
        self.assertIs(GestureValidator.best_case(barely_passing_validator, borderline_validator),
                      barely_passing_validator)
        self.assertIs(GestureValidator.best_case(barely_failing_validator, borderline_validator),
                      borderline_validator)
        self.assertIs(GestureValidator.best_case(barely_failing_validator, very_failing_validator),
                      barely_failing_validator)
        self.assertIs(GestureValidator.worst_case(barely_failing_validator, very_failing_validator),
                      very_failing_validator)

        # Can't compare different types of GestureValidators
        eq_validator = MockEQValidator(2)
        with self.assertRaises(ValueError):
            GestureValidator.best_case(barely_passing_validator, eq_validator)


class GestureValidatorCollectionTests(unittest.TestCase):
    def test_basic(self):
        validators = GestureValidatorCollection(
            MockLEValidator(1.5),  # score 0.5
            MockEQValidator(1)     # score 1.0
        )

        self.assertEqual(validators[MockLEValidator].value, 1.5)
        self.assertEqual(validators[MockLEValidator].score, 0.5)
        self.assertEqual(validators[MockLEValidator].verdict, Verdict.BORDERLINE)
        self.assertEqual(validators[MockEQValidator].value, 1)
        self.assertEqual(validators[MockEQValidator].score, 1.0)
        self.assertEqual(validators[MockEQValidator].verdict, Verdict.PASS)

        self.assertEqual(validators._worst_score, 0.5)
        self.assertEqual(validators.verdict, Verdict.BORDERLINE)

    def test_merge(self):
        shape_1_validators = GestureValidatorCollection(
            MockLEValidator(1.5),  # score 0.5
            MockEQValidator(1)     # score 1.0
        )

        shape_2_validators = GestureValidatorCollection(
            MockLEValidator(0.5),  # score 1.0
            MockEQValidator(2)     # score 0.0
        )

        gesture_validators = GestureValidatorCollection()
        gesture_validators.merge(shape_1_validators)
        gesture_validators.merge(shape_2_validators)

        self.assertEqual(shape_1_validators._worst_score, 0.5)
        self.assertEqual(shape_1_validators.verdict, Verdict.BORDERLINE)

        self.assertEqual(shape_2_validators._worst_score, 0.0)
        self.assertEqual(shape_2_validators.verdict, Verdict.FAIL)

        # For each type of gesture validator, only the worst score is retained.
        self.assertEqual(gesture_validators[MockLEValidator].value, 1.5)
        self.assertEqual(gesture_validators[MockLEValidator].score, 0.5)
        self.assertEqual(gesture_validators[MockLEValidator].verdict, Verdict.BORDERLINE)

        self.assertEqual(gesture_validators[MockEQValidator].value, 2)
        self.assertEqual(gesture_validators[MockEQValidator].score, 0.0)
        self.assertEqual(gesture_validators[MockEQValidator].verdict, Verdict.FAIL)

        self.assertEqual(gesture_validators._worst_score, 0.0)
        self.assertEqual(gesture_validators.verdict, Verdict.FAIL)


class TestCaseValidatorTests(unittest.TestCase):
    def test_basic(self):
        passing_gesture_validator = MockLEValidator(0.5)
        failing_gesture_validator = MockLEValidator(20.5)
        test_case_validator = TestCaseValidator(passing_gesture_validator)
        test_case_validator.add(failing_gesture_validator)

        self.assertIs(test_case_validator.best_gesture_validator, passing_gesture_validator)
        self.assertIs(test_case_validator.worst_gesture_validator, failing_gesture_validator)

        self.assertEqual(test_case_validator.mean_gesture_validator.value, 10.5)
        # Score should be mean of the calculated scores:
        #   (1.0 + 0.0) / 2 = 0.5
        # Not the score that would be calculated for the mean value:
        #   MockLEValidator(10.5).value = 0.0
        self.assertEqual(test_case_validator.mean_gesture_validator.score, 0.5)
        self.assertEqual(test_case_validator.mean_gesture_validator.verdict, Verdict.BORDERLINE)

    def test_wrong_type(self):
        le_gesture_validator = MockLEValidator(0.5)
        eq_gesture_validator = MockEQValidator(1)
        test_case_validator = TestCaseValidator(le_gesture_validator)

        with self.assertRaises(ValueError):
            test_case_validator.add(eq_gesture_validator)


class TestCaseValidatorCollectionTests(unittest.TestCase):
    def test_basic(self):
        passing_le_validator = MockLEValidator(0.5)     # score 1.0
        borderline_le_validator = MockLEValidator(1.5)  # score 0.5

        passing_eq_validator = MockEQValidator(1)       # score 1.0
        failing_eq_validator = MockEQValidator(2)       # score 0.0

        gesture_1_validators = GestureValidatorCollection(
            borderline_le_validator,
            passing_eq_validator
        )

        gesture_2_validators = GestureValidatorCollection(
            passing_le_validator,
            failing_eq_validator
        )

        test_case_validators = TestCaseValidatorCollection()
        test_case_validators.merge(gesture_1_validators)
        test_case_validators.merge(gesture_2_validators)

        self.assertIs(test_case_validators[MockLEValidator].worst_gesture_validator, borderline_le_validator)
        self.assertIs(test_case_validators[MockLEValidator].best_gesture_validator, passing_le_validator)
        self.assertEqual(test_case_validators[MockLEValidator].mean_gesture_validator.value, 1.0)
        self.assertEqual(test_case_validators[MockLEValidator].mean_gesture_validator.score, 0.75)
        self.assertEqual(test_case_validators[MockLEValidator].mean_gesture_validator.verdict, Verdict.BORDERLINE)

        self.assertIs(test_case_validators[MockEQValidator].worst_gesture_validator, failing_eq_validator)
        self.assertIs(test_case_validators[MockEQValidator].best_gesture_validator, passing_eq_validator)
        self.assertEqual(test_case_validators[MockEQValidator].mean_gesture_validator.value, 1.5)
        self.assertEqual(test_case_validators[MockEQValidator].mean_gesture_validator.score, 0.5)
        self.assertEqual(test_case_validators[MockEQValidator].mean_gesture_validator.verdict, Verdict.BORDERLINE)

        # Overall verdict is the worst of any TestCaseValidator's mean score.
        self.assertEqual(test_case_validators.verdict, Verdict.BORDERLINE)
