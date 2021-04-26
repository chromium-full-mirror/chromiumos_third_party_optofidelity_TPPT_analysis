# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Objects defining the geometry of robot gestures and DUT measurements."""

import math


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance(self, other):
        return math.hypot(other.x - self.x, other.y - self.y)

    def __repr__(self):
        return 'Point({}, {})'.format(self.x, self.y)
