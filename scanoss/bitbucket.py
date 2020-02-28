# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from typing import Any

import json
import logging
import requests
from scanoss.scanner import Scanner
from scanoss.diff_parser import parse_diff

# CONSTANTS
BB_HEADER_EVENT = 'X-Event-Key'

BB_EVENT_PUSH = 'repo:push'

BB_STATUS_SUCC = 'SUCCESSFUL'
BB_STATUS_FAIL = 'FAILED'

# Executor
executor = ThreadPoolExecutor(max_workers=10)


class BitbucketAPI:
  """
  Several BitBucket API functions to support the webhook.

  Attributes
  ----------
  api_key : str
    The Bitbucket API key
  api_user : str
    The Bitbucket API Username
  base_url : str
    The Bitbucket API Base url.

  Methods
  -------
  """

  def __init__(self, config):
    self.api_key = config['bitbucket']['api-key']
    self.api_user = config['bitbucket']['api-user']
    self.base_url = config['bitbucket']['api-base']

  def get_commit_diff(self, base_url, commit):
    request_url = "%s/diff/%s" % (base_url, commit['hash'])

    r = requests.get(request_url, auth=(self.api_user, self.api_key))
    if r.status_code != 200:
      logging.error(
          "There was an error trying to obtain diff for commit, the server returned status %d", r.status_code)
      return None
    return r.text

  def get_files_in_commit_diff(self, base_url, commit):
    diff = self.get_commit_diff(base_url, commit)
    obj, _ = parse_diff(diff)
    return list(obj.keys())

  def post_commit_comment(self, base_url, commit, comment):

    comments_url = "%s/commit/%s/comments" % (base_url, commit['hash'])
    logging.debug("Posting comment to URL: %s, comment: %s",
                  comments_url, comment)
    r = requests.post(comments_url, json={"content": {"raw": comment}},
                      auth=(self.api_user, self.api_key))
    if r.status_code >= 400:
      logging.error(
          "There was an error posting a comment for commit, the server returned status %d, and response: %s", r.status_code, r.text)

  def get_assets_json_file(self, base_url, commit):
    return self.get_file_contents(base_url, commit, "oss_assets.json")

  def get_file_contents(self, base_url, commit, filename):
    url = "%s/src/%s/%s" % (base_url, commit['hash'], filename)
    logging.debug('Getting file contents from url: %s', url)
    r = requests.get(url, auth=(self.api_user, self.api_key))
    if r.status_code == 200:
      # obtain the download_url and request content from that URL
      return r.text.encode()
    return None

  def update_build_status(self, base_url, commit, status=False):

    logging.debug("Updating build status for commit %s", commit['hash'])
    url = "%s/commit/%s/statuses/build" % (base_url, commit['hash'])
    data = {"state": BB_STATUS_SUCC if status else BB_STATUS_FAIL,
            "key": commit['hash'], "url": "https://www.scanoss.co.uk"}
    r = requests.post(url, json=data, auth=(self.api_user, self.api_key))
    if r.status_code >= 400:
      logging.error(
          "There was an error updating build status for commit %s, %s", commit['hash'], r.text)


class BitbucketRequestHandler(BaseHTTPRequestHandler):
  """A Bitbucket hook request handler."""

  def __init__(self, config, *args: Any) -> None:
    self.config = config
    self.scanner = Scanner(config)
    self.base_url = self.config['bitbucket']['api-base']
    self.api = BitbucketAPI(config)
    logging.debug("Starting BitbucketRequestHandler with base_url: %s",
                  self.base_url)
    BaseHTTPRequestHandler.__init__(self, *args)

  def do_POST(self):

    # We are only interested in push events
    if self.headers.get(BB_HEADER_EVENT) != BB_EVENT_PUSH:
      self.send_response(200, "OK")
      self.end_headers()
      return

    # get payload
    header_length = int(self.headers['Content-Length'])
    json_payload = self.rfile.read(header_length).decode()
    with open('/tmp/bb_payload', 'w') as f:
      f.write(json_payload)
    json_params = {}
    if len(json_payload) > 0:
      json_params = json.loads(json_payload)
    else:
      self.send_response(200, "OK")
      self.end_headers()
      return

    if 'push' not in json_params:
      logging.warning('Push event without push key')
      self.send_response(200, "OK")
      self.end_headers()
      return
    # Return OK to Bitbucket and keep processing using executor workers.
    logging.debug("Returning 200 OK")
    self.send_response(200, "OK")
    self.end_headers()
    # In Bitbucket API, the Event payload for a repo:push event may contain many 'changes'
    # Each of the 'changes' may contain several commits.
    for change in json_params['push'].get('changes'):
      # If there are no commits, return
      commits = change.get("commits")
      if commits:
        try:
          change_diff_url = change['links']['diff']['href']
          base_url = change_diff_url[:change_diff_url.index('diff') - 1]
        except KeyError:
          logging.error("No Diff URL provided by the JSON payload, returning")
          return

        # Process via executor
        executor.submit(self.process_commits_diff(base_url, commits))

  def process_commits_diff(self, base_url, commits):
    logging.debug("Processing commits")
    # For each commit in push
    files = {}
    for commit in commits:
      # Get the contents of files in the commit
      for filename in self.api.get_files_in_commit_diff(base_url, commit):
        contents = self.api.get_file_contents(base_url, commit, filename)
        if contents:
          files[filename] = contents

      # Send diff to scanner and obtain results
      asset_json = self.api.get_assets_json_file(base_url, commit)
      scan_result = self.scanner.scan_files(files, asset_json)
      if scan_result:
        # Add a comment to the commit
        comment = self.scanner.format_scan_results(scan_result)
        if comment:

          self.api.post_commit_comment(base_url, commit, comment['comment'])
          # Update build status for commit
          self.api.update_build_status(
              base_url, commit, comment['validation'])
          logging.info("Updated comment and build status")

      else:
        logging.info("The server returned no result for scan")
    logging.debug("Finished processing commits")
