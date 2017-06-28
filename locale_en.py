# - # MESSAGES # - #
#error messages
MESSAGE_ERR_NOT_IN_BASE = ("I don't see you in my database, sorry :("
                           " Try /start")
MESSAGE_ERR_IN_BASE = ("You have already checked"
                       " in! Use /import to import your follows")
MESSAGE_ERR_CH_NOT_EXISTS = ("This channel does"
                             " not exist :(")
MESSAGE_ERR_CH_DUP = ("You have already signed"
                      " for updates for this"
                      " channel")
MESSAGE_ERR_NO_CH = ("You are not signed for"
                     " this channel's updates")
MESSAGE_ERR_NO_CMD = ("I don't have such command in use :(\n"
                      "Press <Help> to get the list of available commands")

#help messages
MESSAGE_HELP_UPDATE = ("Syntax to use update is"
                       " /update <channel>")

MESSAGE_HELP_REMOVE = ("Syntax to use remove is"
                       " /remove <channel>")

MESSAGE_HELP_IMPORT = ("Syntax to use import is"
                       " /import <username>")

MESSAGE_HELP_INFO = ("Syntax to use info is"
                     " /info <channel>")

MESSAGE_HELP_LONG = ("Available commands are:\n"
                     "/help -- prints help message\n"
                     "/info <channel> -- shows interactive "
                     "channel info\n"
                     "/list -- lists all subscribed channels\n"
                     "/iter -- lets you iterate through all"
                     " subscribed channels\n"
                     "/live -- shows iterative panel"
                     " of live channels\n"
                     "/clean -- deletes all subscribed channels\n"
                     "/mute (/unmute) -- disables (enables) live "
                     "notifications\n"
                     "/update <channel> -- subscribes"
                     " you for channel's updates\n"
                     "/remove <channel> -- unsubscribes"
                     " you from channel's updates\n"
                     "/import <username> -- imports your"
                     " follows from your account\n"
                     "Remember, for non-prime users "
                     "there is a limit of 10 imported"
                     " channels\n")

#success messages
MESSAGE_NEW_USER = ("Welcome to TwitchGram bot!\n"
                   "I am here to help you keep "
                   "updated for all your favorite"
                   " channels. To start with, you can"
                   " /import your follows list from"
                   " your Twitch account. Otherwise,"
                   " use /update to manually add favorites"
                   " you want to be notified about.")

MESSAGE_LOADING = ("Give me a second...")

MESSAGE_SUCCESS_IMPORT = ("Done! Channels are imported to your list."
                          " Use /list to check updated one!")

MESSAGE_SUCCESS_UPD = ("You are now signed for"
                       " %s's updates!")
MESSAGE_SUCCESS_REM = ("You have unsigned from "
                       "%s's updates")
MESSAGE_SUCCESS_REM_ALL = ("You have unsigned from "
                           "all channels")
MESSAGE_SUCCESS_UNDO = ("You have returned all your"
                        " channels back!")
MESSAGE_SUCCESS_MUTE = ("You will not recieve notifications anymore.")
MESSAGE_SUCCESS_UNMUTE = ("You will recieve notifications now!")

MESSAGE_NO_CHANNELS = ("You have not signed for "
                       "any channels yet. Try "
                       "/update")
MESSAGE_LIST_CHANNELS = ("Your subscribed channels "
                         "are:\n%s")

MESSAGE_START = ("Hello, %s! Press <Start> below in order to"
                 " begin the setup.")

MESSAGE_LIVE = ("Live streams are:\n")

MESSAGE_NO_BIO = ("%s\nNo bio provided")

MESSAGE_BIO = ("%s\n%s")

MESSAGE_STATS = ("Channel name: %s\n"
                "Game: %s\n"
                "Language: %s\n"
                "Followers: %d\n"
                "Views: %d\n"
                "Twitch Partner: %s" )

MESSAGE_STREAM_STATS = ("Channel name: %s\n"
                "Game: %s\n"
                "Language: %s\n"
                "Mature: %s\n"
                "Delay: %d s\n"
                "Viewers: %d\n"
                "Quality: %dp\n"
                "FPS: %d\n")
#notification messages
MESSAGE_STREAM_LIVE = ("%s is live! Join on "
                       "twitch.tv/%s")
