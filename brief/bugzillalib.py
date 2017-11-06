# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import bugzilla


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


class BugzillaBrief(bugzilla.Bugzilla):
    def get_history(self, bugid):
        """Retrieves the history for a bug"""
        return self._get('bug/{bugid}/history'.format(bugid=bugid))

    def get_bugs_created(self, product, from_date, to_date):
        """Retrieves summary of all bugs created between two dates for a given product

        :arg str product: the product to look at
        :arg from_date: greater than or equal to this date
        :arg to_date: less than or equal to this date

        :returns: dict with "count", "creator_count", and "bugs" keys

        """
        terms = [
            {'product': product},
            {'f1': 'creation_ts'},
            {'o1': 'greaterthaneq'},
            {'v1': dt_to_str(from_date)},
            {'f2': 'creation_ts'},
            {'o2': 'lessthaneq'},
            {'v2': dt_to_str(to_date)},
        ]
        resp = self.search_bugs(terms=terms)

        creation_count = len(resp.bugs)
        creators = {}
        for bug in resp.bugs:
            # FIXME(willkg): Move this to another function
            creator = bug.get('creator_detail', {}).get('real_name', None)
            if not creator:
                creator = bug.get('creator', '').split('@')[0]
            creators[creator] = creators.get(creator, 0) + 1
        return {
            'count': creation_count,
            'creators': creators,
            'bugs': resp.bugs
        }

    def get_resolution_history_item(self, bug):
        history = self.get_history(bug['id'])
        for item in reversed(history.bugs[0]['history']):
            # See if this item in the history is the resolving event.
            # If it is, then we know who resolved the bug and we
            # can stop looking at history.
            changes = [
                change for change in item['changes']
                if change['field_name'] == 'status' and change['added'] == 'RESOLVED'
            ]

            if not changes:
                continue

            bug['brief_resolution_item'] = item
            return
        bug['brief_resolution_item'] = None

    def get_bugs_resolved(self, product, from_date, to_date):
        terms = [
            {'product': product},
            {'f1': 'cf_last_resolved'},
            {'o1': 'greaterthaneq'},
            {'v1': dt_to_str(from_date)},
            {'f2': 'cf_last_resolved'},
            {'o2': 'lessthan'},
            {'v2': dt_to_str(to_date)},
        ]
        resp = self.search_bugs(terms=terms)

        resolved_count = len(resp.bugs)
        resolved_map = {}
        resolvers = {}

        for bug in resp.bugs:
            resolution = bug['resolution']
            resolved_map[resolution] = resolved_map.get(resolution, 0) + 1

            assigned_to = bug.get('assigned_to_detail', {}).get('real_name', None)
            if not assigned_to:
                assigned_to = bug.assigned_to.split('@')[0]

            self.get_resolution_history_item(bug)
            if 'nobody' in assigned_to.lower():
                # If no one was assigned, we give "credit" to whoever triaged
                # the bug. We go through the history in reverse order because
                # the "resolver" is the last person to resolve the bug.
                assigned_to = bug['brief_resolution_item']['who']

            if assigned_to:
                if '@' in assigned_to:
                    assigned_to = assigned_to.split('@')[0]

            resolvers[assigned_to] = resolvers.get(assigned_to, 0) + 1

        return {
            'count': resolved_count,
            'resolvers': resolvers,
            'resolved_map': resolved_map,
            'bugs': resp.bugs
        }
