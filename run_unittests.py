#!/usr/bin/env python3
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromiumos file.

from unittest import TestLoader, TextTestRunner

if __name__ == '__main__':
    test_suite = TestLoader().discover('unittests')
    TextTestRunner(verbosity=2).run(test_suite)
