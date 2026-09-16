# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics import (account_resolution_topic,
                           accounts_topic,
                           activities_topic,
                           bookmarks_topic,
                           deliveries_topic,
                           followers_topic,
                           incoming_activities_topic,
                           instance_topic,
                           known_accounts_topic,
                           known_servers_topic,
                           me_links_topic,
                           media_topic,
                           oauth_apps_topic,
                           oauth_codes_topic,
                           oauth_tokens_topic,
                           person_topic,
                           preferences_topic,
                           raw_activities_topic,
                           reaction_refresh_topic,
                           reactions_resolution_topic,
                           remote_actors_topic,
                           resolution_topic,
                           resolved_activities_topic,
                           statuses_topic,
                           timeline_topic,
                           unknown_actors_topic,
                           users_topic)


account_resolution = account_resolution_topic.topic
accounts = accounts_topic.topic
activities = activities_topic.topic
bookmarks = bookmarks_topic.topic
deliveries = deliveries_topic.topic
followers = followers_topic.topic
incoming_activities = incoming_activities_topic.topic
instance = instance_topic.topic
known_accounts = known_accounts_topic.topic
known_servers = known_servers_topic.topic
me_links = me_links_topic.topic
media = media_topic.topic
oauth_apps = oauth_apps_topic.topic
oauth_codes = oauth_codes_topic.topic
oauth_tokens = oauth_tokens_topic.topic
person = person_topic.topic
preferences = preferences_topic.topic
raw_activities = raw_activities_topic.topic
reaction_refresh = reaction_refresh_topic.topic
reactions_resolution = reactions_resolution_topic.topic
remote_actors = remote_actors_topic.topic
resolution = resolution_topic.topic
resolved_activities = resolved_activities_topic.topic
statuses = statuses_topic.topic
timeline = timeline_topic.topic
unknown_actors = unknown_actors_topic.topic
users = users_topic.topic



def names():
    return [account_resolution["name"],
            accounts["name"],
            activities["name"],
            bookmarks["name"],
            deliveries["name"],
            followers["name"],
            incoming_activities["name"],
            instance["name"],
            known_accounts["name"],
            known_servers["name"],
            me_links["name"],
            media["name"],
            oauth_apps["name"],
            oauth_codes["name"],
            oauth_tokens["name"],
            person["name"],
            preferences["name"],
            raw_activities["name"],
            reaction_refresh["name"],
            reactions_resolution["name"],
            remote_actors["name"],
            resolution["name"],
            resolved_activities["name"],
            statuses["name"],
            timeline["name"],
            unknown_actors["name"],
            users["name"]]

