# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from http.server import BaseHTTPRequestHandler

import base64

import json
import logging
import requests
from scanoss.scanner import Scanner
import time
from typing import Any


GITEE_HEADER_TOKEN = "X-Gitee-Token"
GITEE_HEADER_TIMESTAMP = "X-Gitee-Timestamp"
GITEE_HEADER_EVENT = "X-Gitee-Event"

GITEE_EVENT_PUSH = "Push Hook"


class GiteeAPI:
  """
  Several Gitee API utilities
  """

  def __init__(self, config):
    self.api_key = config['gitee']['api-key']
    self.api_user = config['gitee']['api-user']
    self.base_url = config['gitee']['api-base']
    self.secret_token = config['gitee']['secret-token']

  def get_files_in_commit(self, path, commit):
    """ Return all the files in a commit as well as their contents in an dictionary.
    """
    # https://gitee.com/api/v5/repos/{owner}/{repo}/commits/{sha}

    commit_url = "%s/repos/%s/commits/%s" % (self.base_url, path, commit['ID'])
    r = requests.get(commit_url, params={"access_token", self.api_key})
    if r.status_code != 200:
      logging.error(
          "There was an error requesting commit details from Gitee: %d %s", r.status_code, r.text)
      return None
    # Retrieve contents of the files.
    payload = r.json()
    files = {}
    for file in payload.get('files'):
      r = requests.get(file["content_url"], params={
                       "access_token", self.api_key})
      if r.status_code != 200:
        logging.error(
            "There was an error obtaining the contents for the file: %s", file['filename'])
      else:
        file_payload = r.json()
        base64_content = file_payload['content'].encode('ascii')
        contents = base64.b64decode(base64_content).decode('ascii')
        files[file['filename']] = contents
    return files

  def post_commit_comment(self, path, commit, comment):
    comments_url = "%s/repos/%s/commits/%s/comments" % (
        self.base_url, path, commit['ID'])
    logging.debug("Posting comment to URL: %s, comment: %s",
                  comments_url, comment)
    r = requests.post(comments_url, json={"body": comment},
                      data={"access_token": self.api_key})
    if r.status_code >= 400:
      logging.error(
          "There was an error posting a comment for commit, the server returned status %d, and response: %s", r.status_code, r.text)

  # TODO Only Webhook password authentication supported.
  def validate_secret_token(self, given_token):
    return self.secret_token == given_token

  def get_assets_json_file(self, path, commit):
    return self.get_file_contents(path, commit, "oss_assets.json")

  def get_file_contents(self, path, commit, filename) -> bytes:
    """ Returns the contents of a file in a commit as a byte array.
    """
    url = "%s/repos/%s/contents/%s" % (self.base_url, path, filename)
    logging.debug('Getting file contents from url: %s', url)
    r = requests.get(url,
                     params={"ref": commit["ID"], "access_token": self.api_key})
                  
    if r.status_code == 200:
      file_payload = r.json()
      base64_content = file_payload['content'].encode('ascii')
      contents = base64.b64decode(base64_content).decode('ascii')
      return contents
    logging.error("There was an error obtaining the content for file: %s, %d, %s", filename, r.status_code, r.text)
    return None

# TODO Implement update build status for commit.
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
    with open('/tmp/gitee_headers_%s' % time.time(), 'w') as f:
      f.write(self.headers.as_string())
      # We are only interested in push events
    if self.headers.get(GITEE_HEADER_EVENT) != GITEE_EVENT_PUSH:
      logging.debug("Ignoring event: %s", self.headers.get(GITEE_HEADER_EVENT))
      self.send_response(200, "OK")
      self.end_headers()
      return

    # VALIDATE Gitee signature
    gitee_token = self.headers.get(GITEE_HEADER_TOKEN)
    if not self.api.validate_secret_token(gitee_token):
      logging.error("Not authorized, Invalid Gitee signature: %s", gitee_token)
      self.send_response(401, "Invalid Gitee signature")
      self.end_headers()
      return

    # GET Payload
    header_length = int(self.headers['Content-Length'])
    payload = self.rfile.read(header_length).decode()
    with open('/tmp/gitee_payload_%s' % time.time(), 'w') as f:
      f.write(payload)

    if len(payload) == 0:
      logging.warning("The Push event had an empty payload")
      self.send_response(200, "OK")
      self.end_headers()
      return
    json_payload = json.loads(payload)
    commits = json_payload.get("commits")
    if not commits:
      logging.warning("The push event did not contain any commits")
      self.send_response(200, "OK")
      self.end_headers()
      return
    repo = json_payload.get('repository')
    if not repo:
      self.send_response(400, "Malformed JSON")
      logging.error("No repository provided by the JSON payload")
      self.end_headers()
      return

    repo_path = json_payload.get('path_with_namespace')
    if not repo_path:
      self.send_response(400, "Malformed JSON")
      logging.error("No repository path provided by the JSON payload")
      self.end_headers()
      return
    # Return success response and process commit.
    logging.debug("Returning 200 OK")
    self.send_response(200, "OK")
    self.end_headers()
    self.process_commits_diff(repo_path, commits)

  def process_commits_diff(self, repo_path, commits):
    logging.debug("Processing commits")

    for commit in commits:
      files = self.api.get_files_in_commit(repo_path, commit)
      if not files:
        logging.warning("No files found for commit %s", commit['ID'])
        return

      # Send diff to scanner and obtain results
      asset_json = self.api.get_assets_json_file(repo_path, commit)
      scan_result = self.scanner.scan_files(files, asset_json)
      if scan_result:
        # Add a comment to the commit
        comment = self.scanner.format_scan_results(scan_result)
        if comment:

          self.api.post_commit_comment(repo_path, commit, comment['comment'])
          # Update build status for commit
          # self.api.update_build_status(
          #     repository['statuses_url'], commit, comment['validation'])
          logging.info("Updated comment and build status")

      else:
        logging.info("The server returned no result for scan")
    logging.debug("Finished processing commits")
