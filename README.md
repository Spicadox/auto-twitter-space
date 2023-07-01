# auto-twitter-space
### Overview
A script that tracks twitter spaces and can send it to a discord webhook. 
With twitter api v2 being paywalled, this script now uses Twitter's private API using guest tokens to find twitter spaces of the host and then the m3u8 url for the space is found and will have it printed on console and posted using a discord webhook. 
Optionally, it can also download the twitter space after it ends.

### Installation and Requirements
This script requires a few non-standard modules all of which can be installed using the requirements text file. A requirements text file has been included and the command `pip3 install -r requirements.txt` (or pip) can be used to install the required dependencies(except [FFMPEG](https://ffmpeg.org/))

So far this has only been tested on Windows 11. 

### How To Use
Fill out applicable informations inside the `const.py`(if you haven't already renamed `const.py.example` to `const.py`, do so now)
Optionally, obtain a discord webhook url and put it in `const.py` if you want Twitter Space notification to also be posted onto your discord channel.
Optionally you can also specify whether to download the Twitter Space and/or the download location. After the download the files will optionally be posted and sent through a discord webhook. `twspace.py` can also be ran as a standalone script to manually download twitter spaces.

Cookies such as `AUTH_TOKEN` and `CT0`(CSRF token) must be obtained and can be found via 

`browser's developer tool` > `Application` > `Storage` > `Cookies` 

and provide obtained values in `const.py`. Also, due to rate-limiting, adjust sleep to optimal value. 

With all the setting up out of the way this script can run by calling the main/index file `index.py`




