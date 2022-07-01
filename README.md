# auto-twitter-space
### Overview
A script that tracks twitter spaces and can send it to a discord webhook. 
It uses the twitter api to find twitter spaces and then the m3u8 url for the space is found using selenium and will have it printed on console and posted using a discord webhook. 
Optionally, it can also download the twitter space after it ends.

### Installation and Requirements
This script requires a few non-standard modules all of which can be installed using the requirements text file. A requirements text file has been included and the command `pip3 install -r requirements.txt` (or pip) can be used to install the required dependencies(except [FFMPEG](https://ffmpeg.org/))

So far this has only been tested on Windows 10 and with the chrome driver. 

### How To Use
Since this script runs and obtains the Twitter Spaces through the twitter API, users must go to the twitter developer portal and sign up or login. Afterwards, create a project app and obtain the `API Key and Secret`, `Bearer Token`, and the `Access Token`. 
Put these information inside the `const.py`(if you haven't already renamed `const.py.example` to `const.py`, do so now)

With the Twitter authorization/authentication out of the way you can optionally obtain a discord webhook url and put it in `const.py` if you want Twitter Space notification to also be posted onto your discord channel.

The API limit for twitter spaces are 300 requests per a 15 minute window. This script makes 1 request per interval so adjust the `SLEEP_TIME` in the `const.py` file accordingly. If for some reason the m3u8 url can't seemingly be found increase the `SLEEP_TIME`.

Optionally you can also specify whether to download the Twitter Space and/or the download location. After the download the files will optionally be posted and sent through a discord webhook.

With all the setting up out of the way this script can run by calling the main/index file `twitter_space_bot.py`




