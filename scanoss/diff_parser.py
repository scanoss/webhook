# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import hashlib


def parse_diff(src):
  """
  Parse a commit diff.

  This function parses a diff string and generates an output dictionary containing as keys the filenames in the changeset.
  Each value is an array with the strings representing additions (starting with a '+').
  There are only entries for changesets with additions, as these are the only
  ones that we are interested in.

  Parameters
  ----------
  src : str
    The contents of the diff in raw format.
  """
  output = {}
  currentfile = ""
  currentlines = []
  all_lines = ""
  for line in src.splitlines():
    if line.startswith("+++"):
      # We are only interested in additions
      if currentfile and currentlines:
        output[currentfile] = currentlines
        currentlines = []
      # Typically a file line starts with "+++ b/...."
      currentfile = line[6:] if line.startswith('+++ b/') else line[:4]
      # Other lines starting with '+' are additions
    elif line.startswith('+'):
      currentlines.append(line[1:])
      all_lines += line[1:]
  # Wrap
  if currentfile and currentlines:
    output[currentfile] = currentlines
  return output, hashlib.md5(all_lines.encode('utf-8')).hexdigest()
