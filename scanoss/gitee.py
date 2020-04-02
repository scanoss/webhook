# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from http.server import BaseHTTPRequestHandler

import json
import logging
import requests
from scanoss.scanner import Scanner
from scanoss.diff_parser import parse_diff
import time
from typing import Any

GITEE_HEADER_TOKEN = "X-Gitee-Token"
GITEE_HEADER_TIMESTAMP = "X-Gitee-Timestamp"
GITEE_HEADER_EVENT = "X-Gitee-Event"

class GiteeAPI:
  """
  Several Gitee API utilities
  """

  def __init__(self, config):
    self.api_key = config['gitee']['api-key']
    self.api_user = config['gitee']['api-user']
    self.base_url = config['gitee']['api-base']
    self.secret_token = config['gitee']['secret-token']

  def get_commit_diff(self, commit) -> str:
    request_url = "%s.diff" % commit['url']

    r = requests.get(request_url, auth=(self.api_user, self.api_key))
    if r.status_code != 200:
      logging.error(
          "There was an error trying to obtain diff for commit, the server returned status %d", r.status_code)
      return None
    return r.text

  def get_files_in_commit_diff(self, commit):
    """ Return a list containing the names of all the files mentioned in a commit.
    """
    diff = self.get_commit_diff(commit)
    obj, _ = parse_diff(diff)
    return list(obj.keys())

  def post_commit_comment(self, repository, commit, comment):

    comments_url = "%s/comments" % repository.get('commits_url').replace(
        '{/sha}', '/'+commit['id'])
    logging.debug("Posting comment to URL: %s, comment: %s",
                  comments_url, comment)
    r = requests.post(comments_url, json={"body": comment},
                      auth=(self.api_user, self.api_key))
    if r.status_code >= 400:
      logging.error(
          "There was an error posting a comment for commit, the server returned status %d, and response: %s", r.status_code, r.text)

  # def get_assets_json_file(self, contents_url, commit):
  #   return self.get_file_contents(contents_url, commit, "oss_assets.json")

  # def get_file_contents(self, contents_url, commit, filename) -> bytes:
  #   """ Returns the contents of a file in a commit as a byte array.
  #   """
  #   url = contents_url.replace(GH_CONTENTS_PATH, filename)
  #   logging.debug('Getting file contents from url: %s', url)
  #   r = requests.get(url, auth=(self.api_user, self.api_key),
  #                    params={"ref": commit["id"]})
  #   if r.status_code == 200:
  #     # obtain the download_url and request content from that URL
  #     contents_obj = r.json()
  #     r = requests.get(contents_obj['download_url'])
  #     return r.text.encode()
  #   return None

  # def update_build_status(self, statuses_url, commit, status=False):

  #   logging.debug("Updating build status for commit %s", commit['id'])
  #   url = statuses_url.replace("{sha}", commit['id'])
  #   data = {"state": GH_STATUS_SUCC if status else GH_STATUS_FAIL}
  #   r = requests.post(url, json=data, auth=(self.api_user, self.api_key))
  #   if r.status_code >= 400:
  #     logging.error(
  #         "There was an error updating build status for commit %s", commit['id'])

  # def validate_secret_token(self, gh_token, payload):
  #   digest = "sha1="+hmac.new(self.secret_token.encode('utf-8'),
  #                             payload.encode('utf-8'), hashlib.sha1).hexdigest()
  #   return digest == gh_token

class GiteeRequestHandler(BaseHTTPRequestHandler):
  """A Gitee webhook request handler.

  """

  def __init__(self, config, *args: Any) -> None:
    self.config = config
    self.scanner = Scanner(config)
    self.base_url = self.config['gitee']['api-base']
    self.api = GiteeAPI(config)
    logging.debug("Starting GiteeRequestHandler with base_url: %s",
                  self.base_url)
    BaseHTTPRequestHandler.__init__(self, *args)

  def do_POST(self):
    logging.debug("Received payload from Gitee")
    with open('/tmp/gitee_headers_' % time.time(), 'w') as f:
      f.write(json.dumps(self.headers))
    # GET Payload
    header_length = int(self.headers['Content-Length'])
    json_payload = self.rfile.read(header_length).decode()
    with open('/tmp/gitee_payload_' % time.time(), 'w') as f:
      f.write(json_payload)

    # We are only interested in push events
  #   if self.headers.get(GH_HEADER_EVENT) != GH_EVENT_PUSH:
  #     self.send_response(200, "OK")
  #     self.end_headers()
  #     return

  #   # get payload
  #   header_length = int(self.headers['Content-Length'])
  #   json_payload = self.rfile.read(header_length).decode()
  #   with open('/tmp/gh_payload', 'w') as f:
  #     f.write(json_payload)
  #   json_params = {}
  #   if len(json_payload) > 0:
  #     json_params = json.loads(json_payload)

  #    # Validate GH Secret
  #   gh_token = self.headers.get(GH_HEADER_SIGNATURE)
  #   if not self.api.validate_secret_token(gh_token, json_payload):
  #     logging.error("Not authorized, Invalid Github signature: %s", gh_token)
  #     self.send_response(401, "Invalid Github signature")
  #     self.end_headers()
  #     return

  #   # If there are no commits, return
  #   commits = json_params.get("commits")
  #   if not commits:
  #     self.send_response(200, "OK")
  #     self.end_headers()
  #     return

  #   # Get the contents url from the json
  #   try:
  #     repository = json_params['repository']

  #   except KeyError:
  #     self.send_response(400, "Malformed JSON")
  #     logging.error("No repository provided by the JSON payload")
  #     self.end_headers()
  #     return
  #   logging.debug("Returning 200 OK")
  #   self.send_response(200, "OK")
  #   self.end_headers()
  #   self.process_commits_diff(repository, commits)

  # def process_commits_diff(self, repository, commits):
  #   logging.debug("Processing commits")
  #   contents_url = repository.get('contents_url')
  #   # For each commit in push
  #   files = {}
  #   for commit in commits:

  #     # Get the contents of files in the commit
  #     for filename in self.api.get_files_in_commit_diff(commit):

  #       contents = self.api.get_file_contents(contents_url, commit, filename)
  #       if contents:
  #         files[filename] = contents

  #     # Send diff to scanner and obtain results
  #     asset_json = self.api.get_assets_json_file(contents_url, commit)
  #     scan_result = self.scanner.scan_files(files, asset_json)
  #     if scan_result:
  #       # Add a comment to the commit
  #       comment = self.scanner.format_scan_results(scan_result)
  #       if comment:

  #         self.api.post_commit_comment(repository, commit, comment['comment'])
  #         # Update build status for commit
  #         self.api.update_build_status(
  #             repository['statuses_url'], commit, comment['validation'])
  #         logging.info("Updated comment and build status")

  #     else:
  #       logging.info("The server returned no result for scan")
  #   logging.debug("Finished processing commits")
