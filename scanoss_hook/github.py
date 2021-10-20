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
from github.Repository import Repository
from scanoss_hook.scanner import Scanner

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
    self.logger = logger
    self.sbom_file = "SBOM.json"
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
        self.sbom_file = config['scanoss']['sbom_filename']
    except Exception:
        self.logger.error("There is an error in the scanoss section in the config file")

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
    logging.debug(repo_own.get('name'))
    self.logger.debug(repo_type)
    if repo_type == "Organization":
      repo = self.g.get_organization(repo_own.get('login')).get_repo(repo_name)
      logging.info("Organization mode")
    else:
      repo = self.g.get_user(repo_own.get('name')).get_repo(repo_name)
      logging.info("User mode")
    return repo
  
  def process_pr(self,repository, pr):
    self.logger.info("Processing PR")
    repo = self.process_gh_request(repository)
    pull_resquest = repo.get_pull(pr.get('number'))
    commits = pull_resquest.get_commits()
    commits_results = "Processed Commit \t Validated \n"
    summary_list = []
    for commit in commits:
      self.logger.debug(commit.sha)
      result, commits_response = self.process_commit(repo,commit.sha)
      if result is True:
        commits_results += f"""{commit.sha} \t {MSG_VALIDATED} \n"""
      else:
        commits_results += f"""{commit.sha} \t {MSG_NO_VALIDATED} \n"""
        summary_list.append(commits_response)
    pull_resquest.create_issue_comment(commits_results)
    self.logger.debug(summary_list)
  
    self.logger.info("Finished processing PR")
    return



  def process_commit(self, repo: Repository, commit_id) -> bool:
    files = {}
    files_content = {}
    scan_result = {}
    commit_data = repo.get_commit(sha=commit_id)
    files = commit_data.raw_data.get('files')
    commit_url = commit_data.raw_data.get('html_url')
    logging.debug(json.dumps(commit_data.raw_data))
    #committer = commit_data.raw_data.get('commit')['committer']
    #commit_info = {'sha': commit_data.sha, 'user': committer['name'], 'email': committer['email'], 'url': commit_url, 'matches':[]}
    self.logger.debug(commit_url)
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
        contents = repo.get_contents(file['filename'])
        if contents:
          files_content[file['filename']] = contents.decoded_content

    try:
      asset_json = repo.get_contents(self.sbom_file).decoded_content
    except Exception:
      self.logger.info("No assets")
      asset_json = {}
    
    self.logger.debug(asset_json)
    scan_result = self.scanner.scan_files(files_content, asset_json)
    result = {'comment': 'No results', 'validation': True, 'cyclondx' : {}}
    
    if scan_result:
      result = self.scanner.format_scan_results(scan_result)
    # Add a comment to the commit
    if (not result['validation'] or self.comment_always) and result['comment']:
      full_comment = result['comment']
      if result['cyclondx']:
        full_comment += "\n Please find the CycloneDX component details to add to your %s to declare the missing components here:\n" % self.sbom_file
        if asset_json:
          full_comment += "```\n"+ json.dumps(result['cyclondx']['components'], indent=2) + "\n```"
        else:
          full_comment += "```\n"+ json.dumps(result['cyclondx'], indent=2) + "\n```"
      
      self.logger.debug(full_comment)
      commit_data.create_comment(full_comment)
    return result['validation']#, commit_info


  def process_commits_diff(self, repository, commits):
    self.logger.info("Processing commits")
    repo = self.process_gh_request(repository)
    for commit in commits:
      #get commit
      self.process_commit(repo, commit['id'])

    self.logger.info("Finished processing commits")