# auto-twitter-space
### Overview
A program that tracks twitter spaces and sends it to a discord webhook. 
It uses the twitter api to find twitter spaces and then the m3u8 url for the space is found using selenium and will have it printed on console and posted using a discord webhook. 
Optionally It can also download the twitter space after it ends.

### Installation and Requirements
This program requires a few non-standard modules all of which can be installed using the requirements text file. A requirements text file has been included and the command `pip3 install -r requirements.txt` (or pip) can be used to install the required dependencies(except FFMPEG and ChromeDriver).
[ChromeDriver](https://chromedriver.chromium.org/) is also required to get the m3u8 url so make sure the chrome driver version matches your browser version. Also ensure chromedriver is in the same directory as this program.

### How To Use
Since this program runs and obtains the Twitter Spaces through the twitter API, users must go to the twitter developer portal and sign up or login. Afterwards, create a project app and obtain the `API Key and Secret`, `Bearer Token`, and the `Access Token`. 
Put these information inside the `const.py`(if you haven't already renamed `const.py.example` to `const.py`, do so now)

With the Twitter authorization/authentication out of the way you can optionally obtain the discord webhook url and put it in `const.py` if you want Twitter Space notification to also be posted onto your discord channel.

Optionally you can also specify whether to download the Twitter Space and/or the download location. There are two download options one using the default `twspace.py` file provided(only supports prod-fastly rather than canary).
To also use this downloader you must have [kid3-cli](https://kid3.kde.org/) downloaded and on path to properly write the metadata.
The second download method is by using [Ryu's downloader](https://github.com/Ryu1845/twspace-dl). After the download the files will optionally be posted and sent through a discord webhook.
Download is optional as it has not been thoroughly tested so use at your own risk(just double check if the file was downloaded and whether it is the full file)

With all the setting up out of the way the program can run by calling the main/index file `twitter_space_bot.py`

Note: Do not share these key and tokens!

Note 2: I was not the original creator of `twspace.py`, credits go to whoever made it on our group discord server! I had to make a lot of changes to suit my own needs though.

Note 3: The API limit for twitter spaces are 300 requests per a 15 minute window. The program makes 1 request per interval so adjust the `SLEEP_TIME` accordingly. If for some reason the m3u8 url can't seemingly be found increase the `SLEEP_TIME`. 

Note 4: So far this has only been tested on Windows 10 and with the chrome driver. 



