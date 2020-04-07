# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import codecs
import json
from json.decoder import JSONDecodeError
import logging
import os
import requests
import shutil
import time
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
    logging.debug("Starting scan")
    if not asset_json:
      logging.info("Scanning files without oss_assets.json")
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
    # For Troubleshooting store the resulting WFP
    wfp_file = "scan_wfp_%s" % time.time()
    with open("/tmp/%s" % wfp_file, "w") as f:
      f.write(wfp)

    headers = {'X-Session': self.token}
    scan_files = {
        'file': ("%s.wfp" % uuid.uuid1().hex, wfp)}

    data = {"assets": asset_json} if asset_json else {}

    r = requests.post(self.scan_url, files=scan_files,
                      data=data, headers=headers)
    if r.status_code >= 400:
      return None
    try:
      with codecs.open("/tmp/scan_result_%s" % time.time(), 'w', 'utf-8') as f:
        f.write(r.text)
    except:
      logging.error("Error serialising scan result")
    try:
      json_resp = r.json()
    except JSONDecodeError:
      logging.error("The SCANOSS API returned an invalid JSON")
      # For Troubleshooting copy wfp file to failed_wfps folder
      if not os.path.exists('failed_wfps'):
        os.makedirs('failed_wfps')
      shutil.copyfile('/tmp/%s' % wfp_file, 'failed_wfps/%s' % wfp_file)
      return None
    logging.debug("Scan completed")
    return {files_conversion[k]: v for (k, v) in json_resp.items()}

  def format_scan_results(self, scan_results, repository_url):
    """
    This function formats scan result as a markdown comment. Returns a structure with a validation flag.
    """
    logging.debug("Formatting scan results for repository: %s", repository_url)
    matches = {}
    for f, m in scan_results.items():

      if m[0].get('id') != 'null':
        result = {"component": "", "url": "", "lines": "", "also": []}
        for match in m:
          match_id = match.get('id')
          # We ignore results containing the same repository as the current one
          if match_id and match_id != 'none' and repository_url not in match.get('url'):
            if not result['component']:
              result['component'] = match['component']
              result['url'] = match['url']
              result['lines'] = match['lines']
            elif match['component'] and match['component'] != 'N/A':
              result['also'].append(match['component'])
        # Only add result for file if there is a component found.
        if result['component']:
          matches[f] = result
    if not matches:
      return {"validation": True, "comment": self.comment_verified_ok}
    else:
      comment = self.comment_verified_failed + "\n\n"
      comment += "**Found %d Undeclared OSS Assets**\n\n| File | Component | Lines | Also In |\n| --- | --- | --- | ---:|\n" % len(
          matches)

      for f, match in matches.items():
        comment += "| %s | [%s](%s) | %s | %s |\n" % (f,
                                                      match['component'], match['url'], match['lines'], ','.join(match['also']))

      return {"validation": False, "comment": comment}
