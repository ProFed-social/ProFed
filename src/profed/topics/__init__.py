# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics import (activities_topic,
                           deliveries_topic,
                           followers_topic,
                           incoming_activities_topic,
                           known_accounts_topic,
                           media_topic,
                           oauth_apps_topic,
                           oauth_codes_topic,
                           oauth_tokens_topic,
                           person_topic,
                           users_topic)


activities = activities_topic.topic
deliveries = deliveries_topic.topic
followers = followers_topic.topic
incoming_activities = incoming_activities_topic.topic
known_accounts = known_accounts_topic.topic
media = media_topic.topic
oauth_apps = oauth_apps_topic.topic
oauth_codes = oauth_codes_topic.topic
oauth_tokens = oauth_tokens_topic.topic
person = person_topic.topic
users = users_topic.topic



def names():
    return [activities["name"],
            deliveries["name"],
            followers["name"],
            incoming_activities["name"],
            known_accounts["name"],
            media["name"],
            oauth_apps["name"],
            oauth_codes["name"],
            oauth_tokens["name"],
            person["name"],
            users["name"]]

