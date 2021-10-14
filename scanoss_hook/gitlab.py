# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from http.server import BaseHTTPRequestHandler

import base64
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import requests
from urllib import parse
from typing import Any
from .scanner import Scanner

# CONSTANTS
GL_HEADER_TOKEN = 'X-Gitlab-Token'
GL_HEADER_EVENT = 'X-Gitlab-Event'

GL_PUSH_EVENT = 'Push Hook'
GL_MERGE_REQUEST_EVENT = 'Merge Request Hook'

executor = ThreadPoolExecutor(max_workers=10)


class GitLabAPI:
  """
  Several GitLab API functions

  Attributes
  ----------
  api_key : src
    The GitLab API Key
  base_url : src
    The GitLab API Base URL.

  Methods
  -------
  get_diff_json(project, commit)
    Returns the diff data structure for a commit from GitLab API

  get_commit_diff(project, commit)
    Retrieves the raw diff string for a commit.

  get_files_in_commit_diff(project, commit)
    Returns the list of files in a commit diff


  """

  def __init__(self, config):
    self.api_key = config['gitlab']['api-key']
    self.base_url = config['gitlab']['api-base']
    self.auth_headers = {'PRIVATE-TOKEN': self.api_key}

  def get_diff_json(self, project, commit):
    request_url = "%s/projects/%d/repository/commits/%s/diff" % (
        self.base_url, project['id'], commit['id'])

    r = requests.get(request_url, headers=self.auth_headers)
    if r.status_code != 200:
      logging.error(
          "There was an error trying to obtain diff for commit, the server returned status %d", r.status_code)
      return None
    return r.json()

  def get_commit_diff(self, project, commit):

    diff_list = self.get_diff_json(project, commit)
    if diff_list:
      diffs = ["--- %s\n+++ %s\n%s" %
               (d['old_path'], d['new_path'], d['diff']) for d in diff_list]
      return '\n'.join(diffs)
    return None

  def get_files_in_commit_diff(self, project, commit):
    diff_obj = self.get_diff_json(project, commit)
    if diff_obj:
      # We don't care about deleted files
      return [d['new_path'] for d in diff_obj if not d['deleted_file']]
    return None

  def post_commit_comment(self, project, commit, comment):
    """ Uses GitLab API to add a new commit comment
    """
    comments_url = "%s/projects/%d/repository/commits/%s/comments" % (
        self.base_url, project['id'], commit['id'])
    logging.debug("Post comment to URL: %s", comments_url)
    r = requests.post(comments_url, params=comment, headers=self.auth_headers)
    if r.status_code >= 400:
      logging.error(
          "There was an error posting a comment for commit, the server returned status %d", r.status_code)

  def get_assets_json_file(self, project, commit):
    return self.get_file_contents(project, commit, "oss_assets.json")

  def get_file_contents(self, project, commit, filename):
    url = "%s/projects/%d/repository/files/%s" % (
        self.base_url, project['id'], parse.quote_plus(filename))
    r = requests.get(url, headers=self.auth_headers,
                     params={"ref": commit["id"]})
    if r.status_code == 200:
      file_json = r.json()
      return base64.b64decode(file_json['content'])
    return None

  def update_build_status(self, project, commit, status=False):
    # POST /projects/:id/statuses/:sha
    logging.debug("Updating build status for commit %s", commit['id'])
    url = "%s/projects/%d/statuses/%s" % (self.base_url,
                                          project['id'], commit['id'])
    data = {"state": "success" if status else "failed"}
    r = requests.post(url, params=data, headers=self.auth_headers)
    if r.status_code >= 400:
      logging.error(
          "There was an error updating build status for commit %s", commit['id'])


class GitLabRequestHandler(BaseHTTPRequestHandler):
  """A GitLab webhook request handler. Handles Webhook events from GitLab

  Attributes
  ----------
  config : dict
    The configuration dictionary

  Methods
  -------
  do_POST()
    Handles the Webhook post event.

  """

  def __init__(self, config, *args: Any) -> None:
    self.config = config
    self.scanner = Scanner(config)
    self.api_key = self.config['gitlab']['api-key']
    self.base_url = self.config['gitlab']['api-base']
    self.api = GitLabAPI(config)
    logging.debug("Starting GitLabRequestHandler with base_url: %s",
                  self.base_url)
    BaseHTTPRequestHandler.__init__(self, *args)

  def do_POST(self):
    """ Handles the webhook post event.

    """
    # We are only interested in push events
    if self.headers.get(GL_HEADER_EVENT) != GL_PUSH_EVENT:
      self.send_response(200, "OK")
      self.end_headers()
      return

    # get payload
    header_length = int(self.headers['Content-Length'])
    # get gitlab secret token

    json_payload = self.rfile.read(header_length)
    json_params = {}
    if len(json_payload) > 0:
      json_params = json.loads(json_payload.decode('utf-8'))

    # If there are no commits, return
    commits = json_params.get("commits")
    if not commits:
      self.send_response(200, "OK")
      self.end_headers()
      return

    # Validate GL token

    gitlab_token = self.headers.get(GL_HEADER_TOKEN)
    if not self.config['gitlab'].get('secret-token') or self.config['gitlab'].get('secret-token') != gitlab_token:
      logging.error("Not authorized, Gitlab_Token not authorized")
      self.send_response(401, "Gitlab Token not authorized")
      self.end_headers()
      return

    # Get the project from the json
    try:
      project = json_params['project']
    except KeyError:
      self.send_response(400, "Malformed JSON")
      logging.error("No project provided by the JSON payload")
      self.end_headers()
      return
    logging.debug("Returning 200 OK")
    self.send_response(200, "OK")
    self.end_headers()
    executor.submit(self.process_commits_diff(project, commits))

  def process_commits_diff(self, project, commits):
    logging.debug("Processing commits")
    # For each commit in push
    files = {}
    for commit in commits:

      # Get the contents of files in the commit
      for filename in self.api.get_files_in_commit_diff(project, commit):

        contents = self.api.get_file_contents(project, commit, filename)
        if contents:
          files[filename] = contents

      # Send diff to scanner and obtain results
      asset_json = self.api.get_assets_json_file(project, commit)
      scan_result = self.scanner.scan_files(files, asset_json)
      if scan_result:
        # Add a comment to the commit
        comment = self.scanner.format_scan_results(scan_result)
        if comment:
          note = {'note': comment['comment']}
          self.api.post_commit_comment(project, commit, note)
          # Update build status for commit
          self.api.update_build_status(project, commit, comment['validation'])
          logging.info("Updated comment and build status")

      else:
        logging.info("The server returned no result for scan")
    logging.debug("Finished processing commits")
