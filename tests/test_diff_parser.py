# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from scanoss import diff_parser
from grappa import should
import hashlib


def test_parse_diff_1():
  with open("./tests/diff_1.diff") as f:
    diff, md5 = diff_parser.parse_diff(f.read())

    expected_keys = ["grappa/operators/__init__.py",
                     "grappa/operators/contain.py", "grappa/operators/equal.py",
                     "grappa/operators/only.py", "grappa/operators/present.py",
                     'grappa/reporters/subject.py', 'requirements-dev.txt',
                     'tests/operators/only_test.py']
    list(diff.keys()) | should.be.equal.to(expected_keys)
    # Now let's check some values
    len(diff["grappa/operators/only.py"]) | should.be.equal.to(47)
    diff["grappa/operators/equal.py"][0] | should.contain(
        "a value of type \"{type}\" with data \"{value}\"")
    len(md5) | should.be.equal.to(32)


def test_parse_diff_no_additions():
  with open("./tests/diff_no_additions.diff") as f:
    diff, md5 = diff_parser.parse_diff(f.read())
    len(diff) | should.be.equal.to(0)
    len(md5) | should.be.equal.to(32)


def test_add_whole_file_md5():
  with open("./tests/diff_add_file.diff") as f:
    diff, md5 = diff_parser.parse_diff(f.read())
    # Now let's calculate the md5 of a file and see if it corresponds to the real value
    print('\n'.join(diff['tests/test_basic.py']))
    file_md5 = hashlib.md5(
        '\n'.join(diff['tests/test_basic.py']).encode()).hexdigest()
    # Now we calculate the MD5 of the real file.
    with open("./tests/test_basic.py.test") as test_basic:
      expected_md5 = hashlib.md5(test_basic.read().encode()).hexdigest()
      len(diff) | should.be.equal.to(3)
      len(md5) | should.be.equal.to(32)
      file_md5 | should.be.equal.to(expected_md5)
