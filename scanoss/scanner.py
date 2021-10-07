# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import json
from json.decoder import JSONDecodeError
import logging
import requests
import uuid

from .winnowing import wfp_for_file


class Scanner:
  """
  This class communicates with SCANOSS API and returns scan results.

  ...

  Attributes
  ---------
  url : str
    The base URL of the SCANOSS API
  scan_url : str
    The full URL used to request scans
  token : str
    The SCANOSS API Key used to authenticate


  Methods
  -------
  scan_files(files, asset_json)
    Performs a scan of the files using the SCANOSS API.

  format_scan_results(scan_results)
    Formats the scan results as a markdown comment.
  """

  def __init__(self, config):
    self.url = config['scanoss']['url']
    self.scan_url = "%s/api/scan/direct" % self.url
    self.token = config['scanoss']['token']
    self.badge_ok_url = "%s/static/badge-scanoss-ok.svg" % self.url
    self.badge_failed_url = "%s/static/badge-scanoss-failed.svg" % self.url
    self.comment_verified_ok = "![Asset Verification Successful](%s)" % self.badge_ok_url
    self.comment_verified_failed = "![Asset Verification Failed](%s)" % self.badge_failed_url

  def scan_files(self, files, asset_json):
    """ Performs a scan of the files given

    """
    if not files:
      logging.debug("No files found and no scan performed")
      return None
    wfp = ''
    # This is a dictionary that is used to perform a lookup of a file name using the corresponding file index
    files_conversion = {}
    # We assign a number to each of the files. This avoids sending the file names to SCANOSS API,
    # hiding the names and the structure of the project from SCANOSS API.
    files_index = 0
    for file, contents in files.items():
      files_index += 1
      files_conversion[str(files_index)] = file
      wfp += wfp_for_file(files_index, contents)

    headers = {'X-Session': self.token}
    scan_files = {
        'file': ("%s.wfp" % uuid.uuid1().hex, wfp)}

    data = {"assets": asset_json} if asset_json else {}
    logging.debug(wfp)
    r = requests.post(self.scan_url, files=scan_files,
                      data=data, headers=headers)
    if r.status_code >= 400:
      return None
    try:
      json_resp = r.json()
    except JSONDecodeError:
      logging.error("The SCANOSS API returned an invalid JSON")
      return None
    return {files_conversion[k]: v for (k, v) in json_resp.items()}

  def format_scan_results(self, scan_results):
    """
    This function formats scan result as a markdown comment. Returns a dictionary with a validation flag and the comment string.
    """
    # Troubleshooting ONLY
    with open("/tmp/scan_results", "w") as f:
      f.write(json.dumps(scan_results))

    matches = []
    for f, m in scan_results.items():
      if m[0].get('id') != 'none':
        for match in m:
          link = match['url'] + '/blob/' + match['version'] + '/' + match['file']
          matches.append([f, match['purl'][0], match['version'], match['lines'], link, match['oss_lines']])
   
    if not matches:
      return {"validation": True, "comment": 'No matches'}
    else:
      comment = self.comment_verified_failed + "\n\n"
      comment += "| File | Purl | Version | Lines | Link | OSS lines\n"

      for match in matches:
        comment += "| %s | %s | %s | %s | %s | %s |\n" % (
            match[0], match[1], match[2], match[3], match[4], match[5])
      return {"validation": False, "comment": comment}
