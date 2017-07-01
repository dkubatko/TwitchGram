import requests
import multiprocessing as mp
import time
import logging
from threading import Thread
from Queue import Queue

import classUser as ClUs
from constants import *

class Twitch:
    channels = []
    ch_table = {}
    userlist = []

    _data = {}
    _stop = False
    _weights = {}

    def __init__(self, client_id, users = []):
        self.headers = {'Accept': TWAPI_HEADER,
                        'Client-ID': client_id }
        #call setup if users nonempty
        if len(users):
            self._weights = {}
            self.userlist = users
            self._setup()

    #sets up weighted list of channels from users
    def _setup(self):
        logging.info(LOGGING_SETUP_START)
        logging.info(LOGGING_SETUP_CHLIST)
        #set up weighted list of channels
        for usr in self.userlist:
            #if user is signed for updates
            if usr.track:
                channels = usr.get_channels()
                for channel in channels:
                    if channel in self._weights.keys():
                        self._weights[channel] += 1
                    else:
                        self._weights[channel] = 1
        logging.info(LOGGING_DONE)

        #sort channels by their weight
        self.channels = self._weights.keys()
        self.channels = sorted(self.channels,
            key = lambda x: -self._weights[x])

        logging.info(LOGGING_SETUP_UPDATE)
        self._setch(self.channels)
        logging.info(LOGGING_DONE)


    #get user_id for one channel
    def _update(self, channels, out):
        #get id
        query = ','.join(channels)
        r_get = requests.get(TWAPI_ID_BY_NAME + query,
                         headers = self.headers)
        data = r_get.json()

        #get data
        result = []
        #get all ids
        for ch in data["users"]:
            result.append(ch['_id'])
        out.put(result)

    #process result of all updates
    def _setch(self, channels):
        #initial setup for all channels
        for channel in channels:
            self.ch_table[channel] = False

        chan_chunk = list(self.chunks(channels,
                                     TW_CHUNK_SIZE))

        #multiprocessed channel id obtaining
        out = mp.Queue()
        updates = []
        for chunk in chan_chunk:
            p = mp.Process(target = self._update,
                        args = (chunk, out,))
            p.daemon = True
            updates.append(p)

        for update in updates:
            update.start()

        results = []
        for update in updates:
            update.join()
            result = out.get(update)
            #add result to results
            results.extend(result)

        #split in chunks of 100 elements
        chan_chunk = list(self.chunks(results,
                                 TW_CHUNK_SIZE))

        #multiprocessed update for streams
        out = mp.Queue()
        updates = []
        data = []
        for chunk in chan_chunk:
            p = mp.Process(target = self._process,
                        args = (chunk, out))
            p.daemon = True
            updates.append(p)

        for update in updates:
            update.start()

        for update in updates:
            update.join()
            chunk_data = out.get(update)
            data.extend(chunk_data)

        #set True if stream is live
        for stream in data:
            channel = str(stream["channel"]["name"]).lower()
            logging.info(LOGGING_LIVE % channel)
            self.ch_table[channel] = True

    #process ids to obtain stream data
    def _process(self, res, out):
        query = ','.join(res)
        query = TWAPI_STREAMS + query
        #get data
        r_get = requests.get(TWAPI_STREAMS + query,
                             headers = self.headers)
        data = r_get.json()
        if "streams" in data.keys():
            data = data["streams"]
        else:
            data = []
        out.put(data)

    # EXPLICIT PUBLIC METHODS #
    def stop(self):
        self._stop = True

    def chunks(self, l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    #start the loop of updates
    def start(self, delay = 5):
        self._data["Ticks"] = 0
        self._data["AVG Tick Time"] = 0
        self._data["Time up"] = 0

        #waitlist of just-went-off channels
        waitlist = set()
        while not self._stop:
            try:
                out = mp.Queue()
                updates = []
                timer = time.time()

                #split in chunks of CHUNK_SIZE elements
                chan_chunk = list(self.chunks(self.channels,
                                         TW_CHUNK_SIZE))

                for chunk in chan_chunk:
                    p = mp.Process(target = self._update,
                                args = (chunk, out,))
                    p.daemon = True
                    updates.append(p)

                for update in updates:
                    update.start()

                results = []
                for update in updates:
                    update.join()
                    result = out.get(update)
                    #add result to results
                    results.extend(result)

                #split in chunks of CHUNK_SIZE elements
                chan_chunk = list(self.chunks(results,
                                         TW_CHUNK_SIZE))
                out = mp.Queue()
                updates = []
                data = []
                for chunk in chan_chunk:
                    p = mp.Process(target = self._process,
                                args = (chunk, out))
                    p.daemon = True
                    updates.append(p)

                for update in updates:
                    update.start()

                for update in updates:
                    update.join()
                    chunk_data = out.get(update)
                    data.extend(chunk_data)

                #set list of currently online channels
                #waitlisted channels do not count since they
                #are already tracked
                online_list = []
                for channel in self.ch_table.keys():
                    if (self.ch_table[channel] == True and
                                channel not in waitlist):
                        online_list.append(channel)

                #processing data obtained
                for stream in data:
                    channel = str(stream["channel"]["name"]).lower()
                    #remove stream from online list
                    if channel in online_list:
                        online_list.remove(channel)

                    #if it was in waitlist, but then became online,
                    #remove it from the waitlist
                    if channel in waitlist:
                        waitlist.remove(channel)

                    #if it used to be false, then we need
                    #to notify all users subscribed for this
                    #channel
                    if self.ch_table[channel] == False:
                        logging.info(LOGGING_LIVE % channel)
                        ClUs.user.notify(channel)

                    self.ch_table[channel] = True

                for channel in waitlist:
                    logging.info(LOGGING_OFFLINE % channel)
                    self.ch_table[channel] = False

                waitlist = set()

                for channel in online_list:
                    waitlist.add(channel)

                #data collection
                self._data["Ticks"] += 1
                timer = time.time() - timer
                self._data["AVG Tick Time"] += timer
                self._data["Time up"] += timer
                self._data["Time up"] += delay

                time.sleep(delay)
            #handle Telegram request errors
            except Exception as e:
                logging.info(str(e))
                time.sleep(delay)

    #add channel to list
    def add_channel(self, channel):
        if channel in self._weights.keys():
            self._weights[channel] += 1
        else:
            self._weights[channel] = 1

        if channel in self.channels:
            return

        self.channels.append(channel)
        self.channels = sorted(self.channels,
            key = lambda x: -self._weights[x])

        self.ch_table[channel] = self.is_online(channel)

    #removes channel from the list
    def remove_channel(self, channel):
        self._weights[channel] -= 1
        #check if it still exists
        if self._weights[channel] == 0:
            self.channels.remove(channel)
        self.channels = sorted(self.channels,
            key = lambda x: -self._weights[x])

    #checks whether a channel exists
    def exists(self, channel):
        #get id
        r_get = requests.get(TWAPI_ID_BY_NAME + channel,
                             headers = self.headers)
        data = r_get.json()
        if (data["_total"] == 0):
            return False
        else:
            return True

    #checks whether the channel is online
    def is_online(self, channel):
        #get id
        r_get = requests.get(TWAPI_ID_BY_NAME + channel,
                             headers = self.headers)
        data = r_get.json()
        u_id = data["users"][0]["_id"]

        #get stream
        r_get = requests.get(TWAPI_STREAM + u_id,
                             headers = self.headers)
        data = r_get.json()
        if (data["stream"] == None):
            return False
        else:
            return True

    def get_data(self, channel):
        #get id
        r_get = requests.get(TWAPI_ID_BY_NAME + channel,
                             headers = self.headers)
        data = r_get.json()
        u_id = data["users"][0]["_id"]

        #get stream
        r_get = requests.get(TWAPI_CHANNEL + u_id,
                             headers = self.headers)
        data = r_get.json()
        return data

    def get_stream_data(self, channel):
        #get id
        r_get = requests.get(TWAPI_ID_BY_NAME + channel,
                             headers = self.headers)
        data = r_get.json()
        u_id = data["users"][0]["_id"]

        #get stream
        r_get = requests.get(TWAPI_STREAM + u_id,
                             headers = self.headers)
        data = r_get.json()["stream"]
        return data


    #imports data by user id
    def import_data(self, user_id):
        r_get = requests.get(TWAPI_ID_BY_NAME + user_id,
                             headers = self.headers)
        data = r_get.json()
        if (data["_total"] == 0):
            return None
        u_id = data["users"][0]["_id"]
        #getting follow by id
        r_get = requests.get(TWAPI_FOLLOWS_BY_ID % u_id,
                             headers = self.headers)
        data = r_get.json()
        channels = []
        for chan_data in data["follows"]:
            channels.append(chan_data["channel"]["name"])
        return channels







