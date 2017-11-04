# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import github3


def dt_to_str(dt):
    """Converts a dt value to a YYYY-MM-DD string

    If the dt value is a string, it gets returned. If it's a datetime.datetime
    or a datetime.date, then it gets formatted as YYYY-MM-DD and returned.

    :arg varies dt: the date to convert

    :returns: date as a YYYY-MM-DD string

    """
    if isinstance(dt, (datetime.datetime, datetime.date)):
        return dt.strftime('%Y-%m-%d')
    return dt


def two_factor_callback():
    code = ''
    while not code:
        code = input('Enter 2fa: ').strip()
    return code


class GitHubBrief:
    def __init__(self, username=None, password=None):
        if username and password:
            self.client = github3.login(
                username=username, password=password, two_factor_callback=two_factor_callback
            )
        else:
            self.client = github3.GitHub()

    def merged_pull_requests(self, owner, repo, from_date, to_date):
        from_date = dt_to_str(from_date)
        to_date = dt_to_str(to_date)

        merged_prs = []

        repo = self.client.repository(owner=owner, repository=repo)
        resp = repo.iter_pulls(state='closed', sort='updated', direction='desc')

        # We're sorting by "updated", but that could be a comment and not
        # necessarily a merge event, so we fudge this by continuing N past the
        # from_date
        N = 20
        past_from_date = 0

        for pr in resp:
            if not pr.merged_at:
                continue

            if to_date <= dt_to_str(pr.merged_at):
                break

            if from_date > dt_to_str(pr.merged_at):
                if past_from_date > N:
                    break
                past_from_date += 1
                continue

            merged_prs.append(pr)

        return {
            'prs': merged_prs
        }
