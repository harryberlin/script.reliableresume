#!/usr/bin/env python
# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

__author__ = 'devkid/stanley87/harryberlin'

import os
import sys
import json
import time
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import datetime

PY2 = sys.version_info[0] == 2

if PY2:
    #del unicode_literals
    from xbmc import translatePath as xbmc_translate_path
else:
    from xbmcvfs import translatePath as xbmc_translate_path

ENCODING = sys.getdefaultencoding()

ADDON = xbmcaddon.Addon('script.reliableresume')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_USER_PATH = os.path.join(xbmc_translate_path('special://userdata'), 'addon_data', ADDON_ID)
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')
ADDON_ICON_STOP = os.path.join(ADDON_PATH, 'resources', 'media', 'icon_stop.png')
MONITOR = xbmc.Monitor()

DATAFILE = os.path.join(ADDON_USER_PATH, 'ResumeSaverA.m3u')
DATAFILE2 = os.path.join(ADDON_USER_PATH, 'ResumeSaverB.m3u')

if PY2:
    XBMC_LOG_LEVEL = xbmc.LOGNOTICE
else:
    XBMC_LOG_LEVEL = xbmc.LOGINFO


class ResumeSaver(object):
    currentFile = 0

    if PY2:
        lastExecutionTime = time.clock()
    else:
        lastExecutionTime = datetime.datetime.now().timestamp()
    lastConfigReadTime = 0

    timer_amounts = {'0': 5, '1': 30, '2': 120, '3': 300, '4': 600}

    videoEnable = False
    audioEnable = False
    executeInterval = 60

    def shouldExecute(self):
        if PY2:
            now = time.clock()
        else:
            now = datetime.datetime.now().timestamp()
        if (now - self.lastExecutionTime) >= self.executeInterval:
            self.lastExecutionTime = now
            return True
        return False

    def shouldReadConfig(self):
        if PY2:
            now = time.clock()
        else:
            now = datetime.datetime.now().timestamp()
        if (now - self.lastConfigReadTime) >= 5:
            self.lastConfigReadTime = now
            return True
        return False

    def reloadConfigIfNeeded(self):
        if self.shouldReadConfig():
            self.videoEnable = get_addon_setting('observe_video')
            self.videoExcludeLiveTV = get_addon_setting('ExcludeLiveTV')
            self.audioExcludeLiveRadio = get_addon_setting('ExcludeLiveRadio')
            self.videoExcludeHTTP = get_addon_setting('ExcludeHTTP')
            self.audioEnable = get_addon_setting('observe_audio')
            self.all_to_music = get_addon_setting('all_to_music')
            self.executeInterval = self.timer_amounts[get_addon_setting('timer_amount')]

    def loader(self):
        while not MONITOR.abortRequested():
            xbmc.sleep(1000)

            self.reloadConfigIfNeeded()

            if not self.shouldExecute():
                continue

            if not xbmc.Player().isPlaying():
                continue

            self.playing = xbmc.Player().getPlayingFile()
            self.playlist = []

            if self.playing.find('pvr://') > -1:
                if xbmc.Player().isPlayingAudio() and self.audioEnable:
                    if self.audioExcludeLiveRadio:
                        debug('Audio is PVR (Live Radio), which is currently set as an excluded source.')
                        continue
                    self.media = 'pvr/radio'
                    self.plist = xbmc.PlayList(0)

                elif xbmc.Player().isPlayingVideo() and self.videoEnable:
                    if self.videoExcludeLiveTV:
                        debug('Video is PVR (Live TV), which is currently set as an excluded source.')
                        continue
                    self.media = 'pvr/tv'
                    self.plist = xbmc.PlayList(1)

                self.time = 0.0 #xbmc.Player().getTime()
                self.plsize = '-'
                self.plpos = 0
                self.writedata()

            elif xbmc.Player().isPlayingAudio() and self.audioEnable:
                self.media = 'audio'
                self.time = xbmc.Player().getTime()
                self.plist = xbmc.PlayList(0)
                self.plsize = self.plist.size()
                self.plpos = self.plist.getposition()
                if xbmc.Player().getTime() > 0:
                    self.writedata()            
            elif xbmc.Player().isPlayingVideo() and self.all_to_music:
                self.media = 'audio'
                self.time = xbmc.Player().getTime()
                self.plist = xbmc.PlayList(0)
                self.plsize = self.plist.size()
                self.plpos = self.plist.getposition()
                if xbmc.Player().getTime() > 0:
                    self.writedata()
            elif xbmc.Player().isPlayingVideo() and self.videoEnable:
                self.media = 'video'
                self.time = xbmc.Player().getTime()
                self.plist = xbmc.PlayList(1)
                self.plsize = self.plist.size()
                self.plpos = self.plist.getposition()
                if xbmc.Player().getTime() > 0:
                    self.writedata()
            else:
                continue

            if (self.playing.find("http://") > -1 or self.playing.find("https://") > -1) and self.videoExcludeHTTP:
                debug("Media is from an HTTP/S source, which is currently set as an excluded source.")
                continue

    def writedata(self):
        if self.currentFile == 0:
            self.writedataex(DATAFILE)
            self.currentFile = 1
        else:
            self.writedataex(DATAFILE2)
            self.currentFile = 0

    def writedataex(self, datafile):
        if PY2:
            f = open(datafile, 'wb')
        else:
            f = open(datafile, 'w', encoding=ENCODING)
        try:
            f.write('#EXTCPlayListM3U::M3U\n')
            debug('writing m3u tracks started')
            if self.plsize != '-':
                for i in range(0, self.plsize):
                    if PY2:
                        debug('#EXTINF:0,{}\n'.format(os.path.split(self.plist[i].getfilename())[1]))
                        f.write('#EXTINF:0,%s\n' % (os.path.split(self.plist[i].getfilename())[1]))
                        debug('%s\n' % self.plist[i].getfilename())
                        f.write('%s\n' % self.plist[i].getfilename())
                    else:
                        temp = os.path.split(self.plist[i].getPath())[1]

                        debug('#EXTINF:0,%s\n' % temp)
                        f.write('#EXTINF:0,%s\n' % temp)

                        temp = self.plist[i].getPath()
                        debug('%s\n' % temp)
                        f.write('%s\n' % temp)

            debug('writing m3u tracks finished')

            debug('writing extra tags started')

            debug('#MEDIA::%s\n' % self.media)
            f.write('#MEDIA::%s\n' % self.media)

            debug('#TIME::%s\n' % self.time)
            f.write('#TIME::%s\n' % self.time)

            debug('#PLPOS::%s\n' % self.plpos)
            f.write('#PLPOS::%s\n' % self.plpos)

            debug('#PLSIZE::%s\n' % self.plsize)
            f.write('#PLSIZE::%s\n' % self.plsize)

            debug('#PLAYING::%s\n' % self.playing)
            f.write('#PLAYING::%s\n' % self.playing)

            debug('#WINDOW::%s\n' % xbmcgui.getCurrentWindowId())
            f.write('#WINDOW::%s\n' % xbmcgui.getCurrentWindowId())

            debug('#VOLUME::%s\n' % volume_get())
            f.write('#VOLUME::%s\n' % volume_get())

            debug('#STORE::DONE\n')
            f.write('#STORE::DONE\n')

            debug('writing extra tags finished')
        finally:
            f.close()


def volume_get():
    request = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')
    volume = json.loads('%s' % request)['result']['volume']
    debug('VOLUME: Get %s' % volume)
    return volume


def log(msg):
    if not PY2:
        msg = msg.encode('utf-8', 'surrogateescape').decode('ISO-8859-1')
    xbmc.log('%s: SRV: %s' % (ADDON_ID, msg), XBMC_LOG_LEVEL)


def note(heading, message=None, time=-1, icon=None):
    if time == -1:
        xbmcgui.Dialog().notification(heading='%s' % heading, message='%s' % message if message else ' ', icon='%s' % (icon if icon else ADDON_ICON))
    else:
        xbmcgui.Dialog().notification(heading='%s' % heading, message='%s' % message if message else ' ', icon='%s' % (icon if icon else ADDON_ICON), time=time)
    log('NOTIFICATION: "%s%s"' % (heading, ' - %s' % message if message else ''))


def get_addon_setting(id):
    setting = xbmcaddon.Addon(ADDON_ID).getSetting(id)
    if setting.lower() == 'true': return True
    if setting.lower() == 'false': return False
    return str(setting)


def get_condition(condition):
    # example: get_condition('String.IsEmpty(System.Time(xx))')
    return bool(xbmc.getCondVisibility(condition))


def debug(string):
    if not get_addon_setting('debug'):
        return
    log('DEBUG: %s' % string)


def main():
    if os.access(ADDON_USER_PATH, os.F_OK) == 0:
        os.mkdir(ADDON_USER_PATH)
    if get_addon_setting('autorun'):
        xbmc.executescript('special://home/addons/script.reliableresume/default.py')
    m = ResumeSaver()
    try:
        m.loader()
    except RuntimeError as e:
        #xbmc.log('%s: RuntimeError: %s' % (ADDON_ID, str(e)), XBMC_LOG_LEVEL) # only for debug
        if not 'Unknown addon id' in str(e):
            raise str(e)
    del m


if __name__ == '__main__':
    main()
