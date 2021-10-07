# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from http.server import BaseHTTPRequestHandler
from typing import Any
from github import Github
import json
import logging
import hmac
import hashlib

from github.Commit import Commit

from github.Repository import Repository
from scanoss.scanner import Scanner
from scanoss.winnowing import wfp_for_file
from scanoss.email_html import send_report_mail

# CONSTANTS
GH_VERSION = "1.0.1"
GH_HEADER_EVENT = 'X-GitHub-Event'
GH_HEADER_SIGNATURE = 'X-Hub-Signature'

GH_EVENT_PUSH = 'push'
GH_EVENT_PING = 'ping'
GH_EVENT_PR = 'pull_request'

GH_CONTENTS_PATH = '{+path}'

GH_STATUS_SUCC = 'success'
GH_STATUS_FAIL = 'failure'

MSG_VALIDATED = "Automated code review complete"
MSG_NO_VALIDATED = "You PR/commit has been forwarded to AWS Trusted Committers for review."
class GitHubRequestHandler(BaseHTTPRequestHandler):
  """A Github webhook request handler.

  """

  def __init__(self, config, logger: logging, *args: Any) -> None:
    self.config = config
    self.scanner = Scanner(config)
    self.email_config = {}
    self.email_config['enable'] = False
    self.logger = logger
    try:
      self.api_base = config['github']['api-base']
      self.api_key = config['github']['api-key']
      self.g = Github(base_url = self.api_base, login_or_token= self.api_key)
    except Exception:
      self.logger.error("There is an error in the github section in the config file")
      return
    try:
        self.secret_token = config['github']['secret-token']
        self.comment_always = config['scanoss']['comment_always']
    except Exception:
        self.logger.error("There is an error in the scanoss section in the config file")

    try:
      self.email_config['user']  = config['email_report']['user']
      self.email_config['pass']  = config['email_report']['pass']
      self.email_config['dest']  = config['email_report']['dest']
      self.email_config['enable']  = config['email_report']['enable']
    except Exception:
      self.logger.error("There is an error in the email report section in the config file")
  
    BaseHTTPRequestHandler.__init__(self, *args)

  def do_GET(self):
    self.logger.info("PING received")
    repo_list = self.g.get_repos().get_page(0)
    self.logger.debug(repo_list[0])
    resp = {"version":GH_VERSION, "gh_api_test":repo_list[:10]}
    self.send_response(200, resp)
    self.end_headers()
    return

  def validate_secret_token(self, gh_token, payload):
    digest = "sha1="+hmac.new(self.secret_token.encode('utf-8'),
                              payload.encode('utf-8'), hashlib.sha1).hexdigest()
    return digest == gh_token

  def do_POST(self):
    # get payload
    header_length = int(self.headers['Content-Length'])
    json_payload = self.rfile.read(header_length).decode()
    with open('/tmp/gh_payload', 'w') as f:
      f.write(json_payload)
    json_params = {}
    if len(json_payload) > 0:
      json_params = json.loads(json_payload)

         # Validate GH Secret
    gh_token = self.headers.get(GH_HEADER_SIGNATURE)
    if not self.validate_secret_token(gh_token, json_payload):
      logging.error("Not authorized, Invalid Github signature: %s", gh_token)
      self.send_response(401, "Invalid Github signature")
      self.end_headers()
      return

    # Get the contents url from the json
    try:
      repository = json_params['repository']

    except KeyError:
      self.send_response(400, "Malformed JSON")
      self.logger.error("No repository provided by the JSON payload")
      self.end_headers()
      return
    logging.debug("Returning 200 OK")
    self.send_response(200, "OK")
    self.end_headers()
    event = self.headers.get(GH_HEADER_EVENT)
    self.logger.info(event)
    if event == GH_EVENT_PR:
      pr = json_params.get("pull_request")
      if pr.get("state") == "open":
        self.process_pr(repository, pr)
    elif event == GH_EVENT_PUSH:
          # If there are no commits, return
      commits = json_params.get("commits")
      if not commits:
        logging.debug("NO COMMITS!!")
        self.send_response(200, "OK")
        self.end_headers()
        return

      self.process_commits_diff(repository, commits)
    else:
      self.send_response(200, "OK")
      self.end_headers()
      return

  def process_gh_request(self, repository):
    repo_name = repository.get('name')
    repo_own = repository.get('owner')
    repo_type = repo_own.get('type')
    self.logger.debug(repo_own)
    self.logger.debug(repo_type)
    if repo_type == "Organization":
      repo = self.g.get_organization(repo_own.get('login')).get_repo(repo_name)
      logging.info("Organization mode")
    else:
      repo = self.g.get_user().get_repo(repo_name)
      logging.info("User mode")
    return repo
  
  def process_pr(self,repository, pr):
    self.logger.info("Processing PR")
    repo = self.process_gh_request(repository)
    pull_resquest = repo.get_pull(pr.get('number'))
    commits = pull_resquest.get_commits()
    commits_results = "Processed Commit \t Validated \n"
    summary_list = []
    send_email = False
    for commit in commits:
      self.logger.debug(commit.sha)
      result, commits_response = self.process_commit(repo,commit.sha)
      if result is True:
        commits_results += f"""{commit.sha} \t {MSG_VALIDATED} \n"""
      else:
        commits_results += f"""{commit.sha} \t {MSG_NO_VALIDATED} \n"""
        summary_list.append(commits_response)
        send_email = True
    pull_resquest.create_issue_comment(commits_results)
    self.logger.debug(summary_list)
    if send_email is True and self.email_config['enable'] is True:
      email_error, email_error_message = send_report_mail(self.email_config, summary_list)
      if email_error:
        self.logger.error(email_error_message)
      else:
        self.logger.info(email_error_message)
    self.logger.info("Finished processing PR")
    return

  def process_commit(self, repo: Repository, commit_id) -> bool:
    files = {}
    files_content = {}
    scan_result = {}
    comment = {}
    commit_data = repo.get_commit(sha=commit_id)
    files = commit_data.raw_data.get('files')
    commit_url = commit_data.raw_data.get('html_url')
    logging.debug(json.dumps(commit_data.raw_data))
    committer = commit_data.raw_data.get('commit')['committer']
    commit_info = {'sha': commit_data.sha, 'user': committer['name'], 'email': committer['email'], 'url': commit_url, 'matches':[]}
    self.logger.debug(commit_url)
    validation = True
    for file in files:
      logging.debug(file)
      code = (file['patch'])
      lines = code.split("\n")
      file_scan = False
      for line in lines: #if one line was added or changed scan the full file.
        if line[0] == '+' or line[0] == 'M':
          file_scan = True
          break
      #wfp calculation
      if file_scan:
        contents = repo.get_contents(file['filename']) #self.api.get_file_contents(contents_url, commit, filename)
        if contents:
          files_content[file['filename']] = contents.decoded_content
    asset_json = {}

    try:
      asset_json = repo.get_contents("oss_assets.json")
    except Exception:
      self.logger.info("No assets")

    scan_result = self.scanner.scan_files(files_content, asset_json)
    result = {'comment': 'No results', 'validation': True}
    if scan_result:
        # Add a comment to the commit
        result = self.scanner.format_scan_results(scan_result)
        if result['comment']:
          commit_data.create_comment(result['comment'])

    return result['validation'], commit_info


  def process_commits_diff(self, repository, commits):
    self.logger.info("Processing commits")
    repo = self.process_gh_request(repository)
    summary_list = []
    send_email = False
    for commit in commits:
      #get commit
      validation, commit_result = self.process_commit(repo, commit['id'])
      summary_list.append(commit_result)
      if not validation:
        send_email = True

    if send_email is True and  self.email_config['enable'] is True:
      email_error, email_error_message = send_report_mail(self.email_config, summary_list)
      if email_error:
        self.logger.error(email_error_message)
      else:
        self.logger.info(email_error_message)
    self.logger.info("Finished processing commits")