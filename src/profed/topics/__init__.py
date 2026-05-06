# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics import (activities_topic,
                           deliveries_topic,
                           followers_topic,
                           incoming_activities_topic,
                           known_accounts_topic,
                           oauth_apps_topic,
                           oauth_codes_topic,
                           oauth_tokens_topic,
                           users_topic)


activities = activities_topic.topic
deliveries = deliveries_topic.topic
followers = followers_topic.topic
incoming_activities = incoming_activities_topic.topic
known_accounts = known_accounts_topic.topic
oauth_apps = oauth_apps_topic.topic
oauth_codes = oauth_codes_topic.topic
oauth_tokens = oauth_tokens_topic.topic
users = users_topic.topic

