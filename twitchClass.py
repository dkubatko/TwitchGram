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

    _skip = False
    _errors = []

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
    def _ids(self, channels, out):
        #get id
        query = ','.join(channels)
        data = {"users":[]}
        try:
            r_get = requests.get(TWAPI_ID_BY_NAME + query,
                         headers = self.headers)
            #fetch users
            data = r_get.json()["users"]
        #catch connection exception and skip the cycle
        except Exception as e:
            self._errors.append(e)
            self._skip = True
            out.put([])
            return

        #get data
        result = []
        #get all ids
        try:
            for ch in data:
                result.append(ch["_id"])
        #if invalid response
        except Exception as e:
            self._errors.append(e)
            self._skip = True
            out.put([])
            return

        out.put(result)
        return

    #process ids to obtain stream data
    def _process(self, res, out):
        query = ','.join(res)
        query = TWAPI_STREAMS + query
        data = {}
        #get data
        try:
            r_get = requests.get(TWAPI_STREAMS + query,
                                 headers = self.headers)
            data = r_get.json()
        #catch connection exception and skip the cycle
        except Exception as e:
            self._errors.append(e)
            self._skip = True
            out.put([])
            return

        if "streams" in data.keys():
            data = data["streams"]
        else:
            data = []

        out.put(data)
        return

    #multiprocessing splitted queue
    #for target func and given results
    def _multip(self, target, results):
        #split in chunks of 100 elements
        chan_chunk = list(self.chunks(results,
                                 TW_CHUNK_SIZE))

        #multiprocessed update for streams
        out = mp.Queue()
        updates = []
        data = []
        for chunk in chan_chunk:
            p = mp.Process(target = target,
                        args = (chunk, out))
            p.daemon = True
            updates.append(p)

        for update in updates:
            update.start()

        for update in updates:
            update.join()
            chunk_data = out.get(update)
            data.extend(chunk_data)

        return data

    #process result of all updates
    def _setch(self, channels):
        #initial setup for all channels
        for channel in channels:
            self.ch_table[channel] = False

        results = self._multip(self._ids,
                                channels)
        if self._skip:
            self._skip = False
            return


        data = self._multip(self._process,
                                results)
        if self._skip:
            self._skip = False
            return

        #set True if stream is live
        for stream in data:
            channel = str(stream["channel"]["name"]).lower()
            logging.info(LOGGING_LIVE % channel)
            self.ch_table[channel] = True

        return

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
        waitlist = {}
        while not self._stop:
            timer = time.time()

            results = self._multip(self._ids,
                                  self.channels)
            if self._skip:
                logging.warning(LOGGING_CYCLE_FAILURE,
                                str(self._errors.reverse[0]),
                                len(self._errors))
                self._errors = []
                self._skip = False
                time.sleep(delay)
                continue

            data = self._multip(self._process,
                                    results)

            #if error occurs in processes we need to skip
            #one cycle
            if self._skip:
                self._skip = False
                time.sleep(delay)
                continue

            #set list of currently online channels
            #waitlisted channels do not count since they
            #are already tracked
            online_list = []
            for channel in self.ch_table.keys():
                if (self.ch_table[channel] == True and
                            channel not in waitlist.keys()):
                    online_list.append(channel)

            #processing data obtained
            for stream in data:
                channel = str(stream["channel"]["name"]).lower()
                #remove stream from online list
                if channel in online_list:
                    online_list.remove(channel)

                #if it was in waitlist, but then became online,
                #remove it from the waitlist
                if channel in waitlist.keys():
                    waitlist.pop(channel, None)

                #if it used to be false, then we need
                #to notify all users subscribed for this
                #channel
                if self.ch_table[channel] == False:
                    logging.info(LOGGING_LIVE % channel)
                    ClUs.user.notify(channel)

                self.ch_table[channel] = True

            timer = time.time() - timer

            #remove from TW_CD waiting if offline
            for channel in waitlist.keys():
                waitlist[channel] -= (timer + delay)
                if waitlist[channel] <= 0:
                    logging.info(LOGGING_OFFLINE % channel)
                    self.ch_table[channel] = False
                    waitlist.pop(channel, None)

            for channel in online_list:
                waitlist[channel] = TW_CD




            #data collection
            self._data["Ticks"] += 1
            self._data["AVG Tick Time"] += timer
            self._data["Time up"] += timer
            self._data["Time up"] += delay

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
        #I could do it fancier but dont want to mess it up lol
        for chan_data in data["follows"]:
            channels.append(str(chan_data["channel"]["name"]))
        return channels







