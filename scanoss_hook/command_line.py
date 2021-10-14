# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2017-2020, SCANOSS Ltd. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
import yaml
import logging
import logging.handlers as handlers
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
from http.server import HTTPServer
from scanoss_hook.bitbucket import BitbucketRequestHandler
from scanoss_hook.gitlab import GitLabRequestHandler
from scanoss_hook.github import GitHubRequestHandler
from functools import partial

os.environ["PYTHONUNBUFFERED"] = "1"

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG,
                    stream=sys.stdout)

logger = logging.getLogger('scanoss-hook')
logger.setLevel(logging.DEBUG)
log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

def get_parser():
  """Returns the command line parser for the SCANOSS webhook.
  """
  parser = ArgumentParser(description=__doc__,
                          formatter_class=ArgumentDefaultsHelpFormatter)

  parser.add_argument("--addr",
                      dest="addr",
                      default="0.0.0.0",
                      help="address where it listens")
  parser.add_argument("--port",
                      dest="port",
                      type=int,
                      default=8888,
                      metavar="PORT",
                      help="port where it listens")
  parser.add_argument("--handler", dest="handler", choices=['gitlab', 'github', 'bitbucket'],
                      default="gitlab", metavar="HANDLER", help="webhook handler")

  parser.add_argument("--cfg",
                      dest="cfg",
                      type=FileType('r'),
                      required=True,
                      help="path to the config file")

  return parser


def main():
  """Starts a HTTPServer which waits for requests. Configures the webhook in GitHub, GitLab and BitBucket mode.
  """
  p = get_parser()
  args = p.parse_args()
  if not args.cfg:
    p.print_help()
    sys.exit(1)

  config = yaml.safe_load(args.cfg)

  handler = handlers.TimedRotatingFileHandler("/var/log/scanoss-hook.log", when='midnight', interval=1)
  handler.setFormatter(log_format)
  logger.addHandler(handler)

  if args.handler == 'gitlab':
    handler = partial(GitLabRequestHandler, config)
  elif args.handler == 'github':
    handler = partial(GitHubRequestHandler, config, logger)
  elif args.handler == 'bitbucket':
    handler = partial(BitbucketRequestHandler, config)

  httpd = HTTPServer((args.addr, args.port),
                     handler)
  httpd.serve_forever()


if __name__ == '__main__':
  main()
