# -*- coding: utf-8 ``  -*-
'''
This file is created to handle constants
'''
# - # LOGGING # - #
#logging constants
DAYTIME_STRING = "%Y-%m-%d-%H:%M"
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGGING_NEW_USER = "%s: chat_id - user added"

#logging errors
LOGGING_ERR_NOT_IN_BASE = "%s: chat_id - not in base"

#logging generic
LOGGING_DONE = "Done."
LOGGING_BLOCK = '* * '*8

#logging info
LOGGING_CYCLE_START = "Starting cycle of %d channels"
LOGGING_CYCLE_DONE = ("Done cycle of %d channels in "
                     "%d seconds")

LOGGING_SETUP_START = "Starting setup..."
LOGGING_SETUP_CHLIST = "Setting up channel list"
LOGGING_SETUP_UPDATE = "Updating info for channels"

LOGGING_NEW_CHANNEL = ("Added channel %s for "
                    "user_id %s")
LOGGING_REMOVED_CHANNEL = ("Removed channel %s for "
                         "user id %s")
LOGGING_REMOVED_ALL = ("Removed all channels for "
                       "user id %s")
LOGGING_IMPORT_USER = ("Imported info in chat %s"
                       " for user %s")
LOGGING_LOADING_DB = ("Loading data from db...")

LOGGING_RESTART = ("Bot is restarting by %d")

LOGGING_SETUP_FAILURE = ("Failed to set up due to %s")
LOGGING_UPDATE_FAILURE = ("Failure while update: %s")
LOGGING_ACCESS_FAILURE = ("Unauthorized access denied for %d.")

LOGGING_LIVE = ("%s went live")
LOGGING_OFFLINE = ("%s went offline")
LOGGING_ONLINE = ("%s still online")

# - # TWITCH # - #
TWITCH_LINK = "twitch.tv/%s"

TWAPI_HEADER = "application/vnd.twitchtv.v5+json"
TWAPI_ID_BY_NAME = "https://api.twitch.tv/kraken/users?login="
TWAPI_FOLLOWS_BY_ID = "https://api.twitch.tv/kraken/users/%s/follows/channels?sortby=last_broadcast"
TWAPI_STREAM = "https://api.twitch.tv/kraken/streams/"
TWAPI_STREAMS = "https://api.twitch.tv/kraken/streams/?limit=100&channel="
TWAPI_CHANNEL = "https://api.twitch.tv/kraken/channels/"

TW_CHUNK_SIZE = 20
TW_UPDATE_DELAY = 10
TW_CD = 300

TW_LIVE = '\xF0\x9F\x94\xB4'

# - # ACCOUNTS # - #
UNPRIME_IMPORT_COUNT = 10

# - # ENVIRONMENT # - #
import os
TWAPI_CLIENT_ID = os.environ['TWAPI_CLIENT_ID']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TWITCHGRAM_TOKEN']
