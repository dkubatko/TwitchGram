# -*- coding: utf-8 ``  -*-
#force float division
from __future__ import division

from telegram.ext import (Updater, CommandHandler,
                        ConversationHandler, MessageHandler,
                        CallbackQueryHandler, Filters)
from telegram.bot import Bot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random
import logging
import datetime
from threading import Thread
from constants import *
import classUser as ClUs
from twitchClass import Twitch
import redis

#parse lang arg
import argparse
parser = argparse.ArgumentParser(description='TwitchGram bot')
parser.add_argument("--lang", help="language flag. ru/en", type=str)
args = parser.parse_args()

if args.lang == 'ru':
    from locale_ru import *
elif args.lang == 'en':
    from locale_en import *
else:
    from locale_en import *

def init():
    """
    Initializes filename accrding to current date.

    Args:
        None

    Returns:
        None

    """
    #setting up logging
    dt = datetime.datetime.now()
    fn = dt.strftime(DAYTIME_STRING)
    logging.basicConfig(filename="logs/" + fn, filemode = 'w',
     format=LOGGING_FORMAT, level=logging.INFO)

    #setting up bot inst
    bt = Bot(token = TELEGRAM_TOKEN)
    ClUs.user.set_bot(bt)

    #setting up database
    db = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    load_data(db)

    #setting up twitch inst
    tw = Twitch(TWAPI_CLIENT_ID, users = ClUs.user.Users)

    #setting up exit handler
    import atexit
    atexit.register(exit_handler)

    return tw, bt, db

def load_data(db):
    '''
    Loads data from a given database on start
    Args:
        db - db instance
    Return:
        None
    '''
    logging.info(LOGGING_LOADING_DB)
    for chat_id in db.scan_iter("chat_id:*"):
        channels = list(db.smembers(chat_id))
        chat_id = chat_id.split(':')[1]
        #handle empty channel
        if "" in channels:
            channels.remove("")
        usr = ClUs.user(chat_id, channels = channels)
        ClUs.user.add(usr)
    logging.info(LOGGING_DONE)

# TELEGRAM HANDLER FUNCTIONS #

def message(bot, update):
    """
    Handles first message of a user
    Fallbacks: user already in base

    """
    cur_user = ClUs.user.get_by_id(update.message.chat_id)
    #we want to welcome only new users
    if (cur_user != None):
        return
    start_btn = InlineKeyboardMarkup([[InlineKeyboardButton("Start",
                                    callback_data = "start")]])
    name = update.message.from_user.first_name
    #normalize cyrillics
    import unicodedata
    name = unicodedata.normalize("NFKD",
     name).encode('utf-8', 'ignore')
    bot.send_message(chat_id = update.message.chat_id,
                     text = MESSAGE_START %
                     name,
                     reply_markup = start_btn)

def start(bot, update):
    '''
    Starts an interaction with user
    Adds user to the list
    fallbacks: user already in base
    '''
    #handle double registration
    if (ClUs.user.get_by_id(update.message.chat_id)
        != None):
        bot.send_message(chat_id = update.message.chat_id,
                         text = MESSAGE_ERR_IN_BASE)
        return
    #track is set to false by default
    usr = ClUs.user(update.message.chat_id)
    ClUs.user.add(usr)

    #adding entry to db
    global db
    db.sadd("chat_id:" + str(update.message.chat_id), '')

    logging.info(LOGGING_NEW_USER, usr.chat_id)

    bot.send_message(chat_id = update.message.chat_id,
                     text = MESSAGE_NEW_USER)

def set_update(bot, update, args, chat_data):
    '''
    Sets update on a given channel by
    requested user
    Fallbacks: user not in base
    empty / insufficient args
    channel doesn't exist
    channel already in user's channels
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    if args == []:
        channel = ""
    else:
        channel = str(args[0]).lower()

    if (args == [] or '/' in channel):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_HELP_UPDATE)
        return

    #handle non-existing channel
    global tw
    if (not tw.exists(channel)):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_CH_NOT_EXISTS)
        return

    #handle already in channels
    if (channel in cur_user.get_channels()):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_CH_DUP)
        return

    #add channel to user's pool
    cur_user.add_channel(channel)

    #add channel to overall pool
    tw.add_channel(channel)

    #update chat data
    chat_data["channels"] = cur_user.get_channels()

    global db
    db.sadd("chat_id:" + str(cur_user.chat_id),
            channel)

    logging.info(LOGGING_NEW_CHANNEL, channel,
                 update.message.chat_id)

    close_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Close",
                                                callback_data = "close")]])

    bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_SUCCESS_UPD % channel,
                         reply_markup = close_markup)

def remove(bot, update, args, chat_data):
    """
    Removes channel from list of user's channels
    fallbacks: not in base
    empty / insufficient args
    channel not in user's channels

    """
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    if args == []:
        channel = ""
    else:
        channel = str(args[0]).lower()

    if (args == [] or '/' in channel):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_HELP_REMOVE)
        return

    #handle not in channels
    if (channel not in cur_user.get_channels()):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NO_CH)
        return

    #remove from user's preferences
    cur_user.remove(channel)

    #remove from tracking list
    global tw
    tw.remove_channel(channel)

    #remove from database
    global db
    db.srem("chat_id:" + str(cur_user.chat_id),
            channel)

    logging.info(LOGGING_REMOVED_CHANNEL, channel,
                 update.message.chat_id)

    undo_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Undo",
                                                callback_data = "undo"),
                                        InlineKeyboardButton("Close",
                                                callback_data = "close")]])

    #keep in memory what channel to undo
    chat_data["undo"] = channel
    #and sort unsorted data
    chat_data["channels"] = cur_user.get_channels()

    bot.send_message(chat_id = update.message.chat_id,
                         text = MESSAGE_SUCCESS_REM % channel,
                         reply_markup = undo_markup)

def remove_all(bot, update, chat_data):
    '''
    Removes all channels from user's list
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    #empty channels
    chat_data["channels"] = []

    chat_data["rem_channels"] = cur_user.get_channels()

    #remove all from user's preferences
    for channel in cur_user.get_channels():
      cur_user.remove(channel)

    #remove from tracking list
    global tw
    tw.remove_channel(channel)

    #remove from database
    global db
    for channel in chat_data["channels"]:
      db.srem("chat_id:" + str(cur_user.chat_id),
              channel)

    logging.info(LOGGING_REMOVED_ALL,
                 update.message.chat_id)

    undo_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Undo",
                                                callback_data = "undo_all"),
                                        InlineKeyboardButton("Close",
                                                callback_data = "close")]])

    bot.send_message(chat_id = update.message.chat_id,
                         text = MESSAGE_SUCCESS_REM_ALL,
                         reply_markup = undo_markup)

def help_com(bot, update):
    '''
    prints help message
    fallbacks: none
    '''
    bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_HELP_LONG)

def list_ch(bot, update):
    '''
    lists cur user's channels
    fallbacks: user not un base
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    channels = cur_user.get_channels()
    if len(channels) == 0:
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_NO_CHANNELS)
        return

    s = ', '.join(channels)
    bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_LIST_CHANNELS % s)

def import_st(bot, update, args):
    '''
    imports user's follows from twitch
    fallbacks:
    user not in base
    empty \ insuff args
    user does not exist
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    #handle case with no args
    if (args == []):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_HELP_IMPORT)
        return

    username = str(args[0])
    global tw
    #handle case with no user existing
    if (not tw.exists(username)):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_CH_NOT_EXISTS)
        return

    bot.send_message(chat_id = update.message.chat_id,
                         text = MESSAGE_LOADING)

    channels = tw.import_data(username)

    count = UNPRIME_IMPORT_COUNT
    if len(channels) < count:
        count = len(channels)

    #import up to 10 most viewed channels
    for ind in range(count):
        channel = str(channels[ind])

        #handle existing channel
        if channel in cur_user.get_channels():
            continue

        #add channel to user's pool
        cur_user.add_channel(channel)

        #add channel to
        tw.add_channel(channel)

        global db
        db.sadd("chat_id:" + str(cur_user.chat_id),
                channel)

    logging.info(LOGGING_IMPORT_USER % (update.message.chat_id, username))

    bot.send_message(chat_id = update.message.chat_id,
                         text = MESSAGE_SUCCESS_IMPORT)

def ch_info(bot, update, args, chat_data):
    '''
    Shows interactive channel info message
    fallbacks: user not in base
    empty / insuff args
    channel doesn not exist
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    if args == []:
        channel = ''
    else:
        channel = args[0]

    #handle no args or link as arg
    if (args == [] or '/' in channel):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_HELP_INFO)
        return

    global tw
    #handle non existing channel
    if (not tw.exists(channel)):
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_CH_NOT_EXISTS)
        return


    info_keys = [[InlineKeyboardButton("Bio",
                                       callback_data = "bio"),
                  InlineKeyboardButton("Stats",
                                       callback_data = "stats")]]

    if (tw.is_online(channel)):
        info_keys.append([InlineKeyboardButton("Live", callback_data = "live")])
    else:
        info_keys.append([InlineKeyboardButton("Offline", callback_data = "none")])

    info_keys.append([InlineKeyboardButton("Close", callback_data = "close")])

    keys_markup = InlineKeyboardMarkup(info_keys)

    chat_data["channel"] = channel

    ch_data = tw.get_data(channel)

    bot.send_message(chat_id = update.message.chat_id,
                     text = TWITCH_LINK % channel,
                     reply_markup = keys_markup)

def iterate(bot, update, chat_data):
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    channels = cur_user.get_channels()

    if len(channels) == 0:
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_NO_CHANNELS)
        return

    chat_data["ch_ind"] = 0
    chat_data["channels"] = channels

    text = TWITCH_LINK % channels[0]

    iter_keys = [[InlineKeyboardButton("Prev",
                                       callback_data = "prev"),
                  InlineKeyboardButton("%d/%d" % (1, len(channels)),
                                       callback_data = "none"),
                  InlineKeyboardButton("Next",
                                       callback_data = "next")],
                  [InlineKeyboardButton("Remove", callback_data = "remove"),
                  InlineKeyboardButton("Info", callback_data = "iter_info")],
                  [InlineKeyboardButton("Close", callback_data = "close")]]

    keys_markup = InlineKeyboardMarkup(iter_keys)

    bot.send_message(chat_id = update.message.chat_id,
                     text = text,
                     reply_markup = keys_markup)

def live(bot, update, chat_data):
    '''
    Sends all live channels to user
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    channels = cur_user.get_channels()
    if len(channels) == 0:
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_NO_CHANNELS)
        return

    chat_data["live_channels"] = sorted([channel for channel
                     in channels if tw.ch_table[channel]])

    chat_data["live_id"] = 0
    text = TWITCH_LINK % chat_data["live_channels"][0]

    iter_keys = [[InlineKeyboardButton("Prev",
                                       callback_data = "prev_live"),
                  InlineKeyboardButton("Next",
                                       callback_data = "next_live")],
                  [InlineKeyboardButton("Close", callback_data = "close")]]

    keys_markup = InlineKeyboardMarkup(iter_keys)

    bot.send_message(chat_id = update.message.chat_id,
                     text = text,
                     reply_markup = keys_markup)

def mute(bot, update):
    '''
    Mutes all notifications for current user
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    cur_user.track = False
    bot.send_message(chat_id =
                     update.message.chat_id,
                     text = MESSAGE_SUCCESS_MUTE)

def unmute(bot, update):
    '''
    Unmutes all notifications for current user
    '''
    cur_user = ClUs.user.get_by_id(update.message.chat_id)

    #handle case with no user
    if (cur_user == None):
        logging.info(LOGGING_ERR_NOT_IN_BASE,
         update.message.chat_id)
        bot.send_message(chat_id =
                         update.message.chat_id,
                         text = MESSAGE_ERR_NOT_IN_BASE)
        return

    cur_user.track = True
    bot.send_message(chat_id =
                     update.message.chat_id,
                     text = MESSAGE_SUCCESS_UNMUTE)



def unknown(bot, update):
    '''
    handles unknown commands
    fallbacks: none
    '''
    help_btn = InlineKeyboardMarkup([[InlineKeyboardButton("Help",
                                      callback_data = "help")]])
    bot.send_message(chat_id = update.message.chat_id,
                     text = MESSAGE_ERR_NO_CMD,
                     reply_markup = help_btn)

def notify_live(chat_id, channel, bot):
    '''
    notifies user that stream is live
    '''
    bot.send_message(chat_id = chat_id,
        text = MESSAGE_STREAM_LIVE % (channel.title(),
         channel))

def keyboard_callback(bot, update, chat_data):
    '''
    handles callback requests
    '''
    query = update.callback_query

    #handle no action
    if query.data == "none":
      return

    #start from message func
    if query.data == "start":
        bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
        start(bot, query)
        return

    #callback from unknown
    if query.data == "help":
        bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
        help_com(bot, query)
        return

    # handle close button
    if query.data == "close":
        bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
        return

    # - # ITER CALLBACKS # - #
    if query.data == "next":
        #aquire chat data
        channels = sorted(chat_data["channels"])

        if channels == []:
          bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
          return

        chat_data["ch_ind"] = (chat_data["ch_ind"] + 1) % len(channels)
        ind = chat_data["ch_ind"]

        text = TWITCH_LINK % channels[ind]

        iter_keys = [[InlineKeyboardButton("Prev",
                                           callback_data = "prev"),
                      InlineKeyboardButton("%d/%d" % (ind + 1, len(channels)),
                                           callback_data = "none"),
                      InlineKeyboardButton("Next",
                                           callback_data = "next")],
                       [InlineKeyboardButton("Remove", callback_data = "remove"),
                    InlineKeyboardButton("Info", callback_data = "iter_info")],
                    [InlineKeyboardButton("Close", callback_data = "close")]]

        keys_markup = InlineKeyboardMarkup(iter_keys)

        query.edit_message_text(
                         text = text)
        query.edit_message_reply_markup(
                         reply_markup = keys_markup)
        return

    if query.data == "prev":
        #aquire chat data
        channels = sorted(chat_data["channels"])

        if channels == []:
          bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
          return

        chat_data["ch_ind"] -= 1
        if chat_data["ch_ind"] == -1:
            chat_data["ch_ind"] = len(channels) - 1
        ind = chat_data["ch_ind"]

        text = TWITCH_LINK % channels[ind]

        iter_keys = [[InlineKeyboardButton("Prev",
                                           callback_data = "prev"),
                      InlineKeyboardButton("%d/%d" % (ind + 1, len(channels)),
                                           callback_data = "none"),
                      InlineKeyboardButton("Next",
                                           callback_data = "next")],
                      [InlineKeyboardButton("Remove", callback_data = "remove"),
                      InlineKeyboardButton("Info", callback_data = "iter_info")],
                        [InlineKeyboardButton("Close", callback_data = "close")]]

        keys_markup = InlineKeyboardMarkup(iter_keys)

        query.edit_message_text(
                         text = text)
        query.edit_message_reply_markup(
                         reply_markup = keys_markup)
        return

    if query.data == "remove":
        #aquire chat data
        channels = sorted(chat_data["channels"])
        ind = chat_data["ch_ind"]

        remove(bot, query, [channels[ind]], chat_data)
        #remove channel from channel list
        #chat_data["channels"].remove(channels[ind])

        #update channels after remove
        channels = sorted(chat_data["channels"])

        if channels == []:
          bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
          return

        #update index
        chat_data["ch_ind"] = (chat_data["ch_ind"] + 1) % len(channels)
        ind = chat_data["ch_ind"]

        text = TWITCH_LINK % channels[ind]

        iter_keys = [[InlineKeyboardButton("Prev",
                                           callback_data = "prev"),
                      InlineKeyboardButton("%d/%d" % (ind + 1, len(channels)),
                                           callback_data = "none"),
                      InlineKeyboardButton("Next",
                                           callback_data = "next")],
                       [InlineKeyboardButton("Remove", callback_data = "remove"),
                        InlineKeyboardButton("Info", callback_data = "iter_info")],
                        [InlineKeyboardButton("Close", callback_data = "close")]]

        keys_markup = InlineKeyboardMarkup(iter_keys)

        query.edit_message_text(
                         text = text)
        query.edit_message_reply_markup(
                         reply_markup = keys_markup)

        chat_data["rem_id"] = query.message.message_id
        return

    if query.data == "iter_info":
        #aquire chat data
        channels = chat_data["channels"]

        if channels == []:
          bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
          return

        ind = chat_data["ch_ind"]
        bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)
        ch_info(bot, query, [channels[ind]], chat_data)
        return

    # - # ITER LIVE CALLBACK # - #
    if query.data == "next_live":
        #aquire chat data
        channels = sorted(chat_data["live_channels"])

        chat_data["live_id"] = (chat_data["live_id"] + 1) % len(channels)
        ind = chat_data["live_id"]

        text = TWITCH_LINK % channels[ind]

        iter_keys = [[InlineKeyboardButton("Prev",
                                       callback_data = "prev_live"),
                  InlineKeyboardButton("Next",
                                       callback_data = "next_live")],
                  [InlineKeyboardButton("Close", callback_data = "close")]]

        keys_markup = InlineKeyboardMarkup(iter_keys)

        query.edit_message_text(
                         text = text)

        query.edit_message_reply_markup(
                                        reply_markup = keys_markup)
        return

    if query.data == "prev_live":
        #aquire chat data
        channels = sorted(chat_data["live_channels"])

        chat_data["live_id"] -= 1
        if chat_data["live_id"] == -1:
            chat_data["live_id"] = len(channels) - 1
        ind = chat_data["live_id"]

        text = TWITCH_LINK % channels[ind]

        iter_keys = [[InlineKeyboardButton("Prev",
                                       callback_data = "prev_live"),
                  InlineKeyboardButton("Next",
                                       callback_data = "next_live")],
                  [InlineKeyboardButton("Close", callback_data = "close")]]

        keys_markup = InlineKeyboardMarkup(iter_keys)

        query.edit_message_text(
                         text = text)

        query.edit_message_reply_markup(
                                        reply_markup = keys_markup)
        return

    #handle undo button
    if query.data == "undo":
      bot.delete_message(chat_id = query.message.chat_id,
                     message_id = query.message.message_id)
      set_update(bot, query, [chat_data["undo"]], chat_data)
      if ("rem_id" in chat_data.keys() and chat_data["rem_id"] != None):
        message_id = chat_data["rem_id"]
        #update channels after remove
        channels = sorted(chat_data["channels"])

        #update index
        chat_data["ch_ind"] -= 1
        if chat_data["ch_ind"] == -1:
            chat_data["ch_ind"] = len(channels) - 1
        ind = chat_data["ch_ind"]

        text = TWITCH_LINK % channels[ind]

        iter_keys = [[InlineKeyboardButton("Prev",
                                           callback_data = "prev"),
                      InlineKeyboardButton("%d/%d" % (ind + 1, len(channels)),
                                           callback_data = "none"),
                      InlineKeyboardButton("Next",
                                           callback_data = "next")],
                       [InlineKeyboardButton("Remove", callback_data = "remove"),
                        InlineKeyboardButton("Info", callback_data = "iter_info")],
                        [InlineKeyboardButton("Close", callback_data = "close")]]

        keys_markup = InlineKeyboardMarkup(iter_keys)

        bot.edit_message_text(chat_id = query.message.chat_id,
                              message_id = message_id,
                         text = text)
        bot.edit_message_reply_markup(chat_id = query.message.chat_id,
                              message_id = message_id,
                         reply_markup = keys_markup)

        chat_data["rem_id"] = None
        return
      return

    global tw
    #handle undo all button
    if query.data == "undo_all":
      channels = chat_data["rem_channels"]
      for channel in channels:
        cur_user = ClUs.user.get_by_id(query.message.chat_id)

        #add channel to user's pool
        cur_user.add_channel(channel)

        #add channel to overall pool
        tw.add_channel(channel)

        global db
        db.sadd("chat_id:" + str(cur_user.chat_id),
                channel)
      chat_data["channels"] = channels
      #remove message about deletion
      bot.delete_message(chat_id = query.message.chat_id,
                       message_id = query.message.message_id)

      close_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Close",
                                                callback_data = "close")]])

      bot.send_message(chat_id = query.message.chat_id,
                       text = MESSAGE_SUCCESS_UNDO,
                       reply_markup = close_markup)
      return

    channel = chat_data["channel"]
    ch_data = tw.get_data(channel)

    #ununicode everything
    import unicodedata
    for key in ch_data.keys():
        if type(ch_data[key]) == unicode:
            ch_data[key] = unicodedata.normalize("NFKD",
            ch_data[key]).encode('utf-8', 'ignore')

    if query.data == "bio":
        if ch_data["description"] != "":
            text = MESSAGE_BIO % (ch_data["display_name"],
                         ch_data["description"])
        else:
            text = MESSAGE_NO_BIO % ch_data["display_name"]

        image = ch_data["logo"]

        bio_keys = [[InlineKeyboardButton("Back",
                                       callback_data = "info"),
                  InlineKeyboardButton("Close",
                                       callback_data = "close")]]
        keys_markup = InlineKeyboardMarkup(bio_keys)

        query.edit_message_text(
                         text = text)

        query.edit_message_reply_markup(
                         reply_markup = keys_markup)
        return

    if query.data == "stats":
        text = MESSAGE_STATS % (ch_data["display_name"],
                                ch_data["game"],
                                ch_data["language"].title(),
                                ch_data["followers"],
                                ch_data["views"],
                                "+" if ch_data["partner"] else "-")

        image = ch_data["logo"]

        bio_keys = [[InlineKeyboardButton("Back",
                                       callback_data = "info"),
                  InlineKeyboardButton("Close",
                                       callback_data = "close")]]
        keys_markup = InlineKeyboardMarkup(bio_keys)

        query.edit_message_text(
                         text = text)

        query.edit_message_reply_markup(
                         reply_markup = keys_markup)
        return

    if query.data == "live":
        stream_data = tw.get_stream_data(channel)
        #ununicode everything in stream data
        import unicodedata
        for key in stream_data.keys():
            if type(stream_data[key]) == unicode:
                stream_data[key] = unicodedata.normalize("NFKD",
                stream_data[key]).encode('utf-8', 'ignore')

        text = MESSAGE_STREAM_STATS % (ch_data["display_name"],
                                stream_data["game"],
                                ch_data["language"].title(),
                                "+" if ch_data["mature"] else "-",
                                stream_data["delay"],
                                stream_data["viewers"],
                                stream_data["video_height"],
                                stream_data["average_fps"])

        image = ch_data["logo"]

        live_keys = [[InlineKeyboardButton("Back",
                                       callback_data = "info"),
                  InlineKeyboardButton("Close",
                                       callback_data = "close")],
                  [InlineKeyboardButton("Preview", callback_data = "preview")]]
        keys_markup = InlineKeyboardMarkup(live_keys)

        query.edit_message_text(
                         text = text)

        query.edit_message_reply_markup(
                         reply_markup = keys_markup)
        return

    if query.data == "preview":
        stream_data = tw.get_stream_data(channel)
        image = stream_data["preview"]["large"]

        im_keys = [[InlineKeyboardButton("Close",
                                       callback_data = "close")]]
        keys_markup = InlineKeyboardMarkup(im_keys)

        bot.send_photo(chat_id=query.message.chat_id,
                       photo = image,
                       reply_markup = keys_markup)
        return

    if query.data == "info":
        info_keys = [[InlineKeyboardButton("Bio",
                                       callback_data = "bio"),
                  InlineKeyboardButton("Stats",
                                       callback_data = "stats")]]

        if (tw.is_online(channel)):
            info_keys.append([InlineKeyboardButton("Live",
                                                   callback_data = "live")])
        else:
            info_keys.append([InlineKeyboardButton("Offline",
                                                   callback_data = "none")])

        info_keys.append([InlineKeyboardButton("Close", callback_data = "close")])


        keys_markup = InlineKeyboardMarkup(info_keys)

        query.edit_message_text(
                         text = TWITCH_LINK % channel)

        query.edit_message_reply_markup(
                         reply_markup = keys_markup)
        return

def exit_handler():
    '''
    Exit handler to collect data
    '''
    logging.info(LOGGING_BLOCK)
    global tw
    twdata = tw._data
    twdata["AVG Tick Time"] = twdata["AVG Tick Time"] / twdata["Ticks"]
    for key, value in twdata.iteritems():
      logging.info(key + ": " + str(value))

    usdata = ClUs.user._data
    usdata["AVG Sort Time"] = usdata["AVG Sort Time"] / usdata["Sorts #"]
    for key, value in usdata.iteritems():
      logging.info(key + ": " + str(value))

    tw.stop()



if (__name__ == "__main__"):
    global tw
    tw, bt, db = init()
    #setup updater and dispatcher
    updater = Updater(token = TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    fm_handler = MessageHandler(Filters.text, message)
    dispatcher.add_handler(fm_handler)

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    upd_handler = CommandHandler('update',  set_update,
                                  pass_args = True,
                                  pass_chat_data = True)
    dispatcher.add_handler(upd_handler)

    rem_handler = CommandHandler('remove',  remove,
                                  pass_args = True,
                                  pass_chat_data = True)
    dispatcher.add_handler(rem_handler)

    help_handler = CommandHandler('help',  help_com)
    dispatcher.add_handler(help_handler)

    list_handler = CommandHandler('list',  list_ch)
    dispatcher.add_handler(list_handler)

    imp_handler = CommandHandler('import', import_st,
                                 pass_args=True)
    dispatcher.add_handler(imp_handler)

    info_handler = CommandHandler('info', ch_info,
                                  pass_args=True,
                                  pass_chat_data=True)
    dispatcher.add_handler(info_handler)

    iter_handler = CommandHandler('iter', iterate,
                                  pass_chat_data=True)
    dispatcher.add_handler(iter_handler)

    ra_handler = CommandHandler('clear', remove_all,
                                pass_chat_data = True)
    dispatcher.add_handler(ra_handler)

    live_handler = CommandHandler('live', live,
                                  pass_chat_data = True)
    dispatcher.add_handler(live_handler)

    uk_handler = MessageHandler(Filters.command,
                                unknown)
    dispatcher.add_handler(uk_handler)

    dispatcher.add_handler(CallbackQueryHandler(keyboard_callback,
                                                pass_chat_data=True))


    t = Thread(target = tw.start, args = (TW_UPDATE_DELAY,))
    t.daemon = True
    t.start()

    updater.start_polling()
    updater.idle()
