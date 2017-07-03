# -*- coding: utf-8 -*-
import tttbot
import time
import logging

class user:
    Users = []
    bot = None

    _data = {"Users added": 0,
             "Sorts #": 0,
             "AVG Sort Time": 0}

    def __init__(self, chat_id, track = True, channels = None):
        self.chat_id = str(chat_id)
        self.track = track
        self.channels = []
        if (channels != None):
            self.channels.extend(channels)


    def add_channel(self, channel):
        self.channels.append(channel)

    def get_channels(self):
        return sorted(self.channels)

    def remove(self, channel):
        return self.channels.remove(channel)

    #STATIC#
    @classmethod
    def sort(cls, sort_by):
        timer = time.time()
        cls.Users = sorted(cls.Users,
                           key=lambda x:
                           getattr(x, str(sort_by)))
        timer = time.time() - timer
        cls._data["AVG Sort Time"] += timer
        cls._data["Sorts #"] += 1

    @classmethod
    def get_by_id(cls, chat_id):
        chat_id = str(chat_id)
        #inner function for filtering
        def f(x): return x.chat_id == chat_id
        #filters users and finds the given id
        result  = filter(f, cls.Users)
        #return first match or none if no matches
        return  result[0] if result != [] else None

    @classmethod
    def add(cls, usr):
        cls.Users.append(usr)
        #sort after appending
        cls.sort("chat_id")
        cls._data["Users added"] += 1

    @classmethod
    def set_bot(cls, bot):
        cls.bot = bot

    @classmethod
    def get_all(cls):
        for us in cls.Users:
            print us.chat_id
            print us.channels

    @classmethod
    def remove_user(cls, user):
        cls.Users.remove(user)

    @classmethod
    def notify(cls, channel):
        for usr in cls.Users:
            if channel in usr.channels and usr.track:
                try:
                    tttbot.notify_live(usr.chat_id, channel,
                                   cls.bot)
                except Exception as e:
                    logging.info(str(e))
                    us = cls.get_by_id(update.message.chat_id)
                    if us != None:
                        cls.remove_user(us)

