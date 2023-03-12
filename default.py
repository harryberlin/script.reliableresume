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

DATAFILE = os.path.join(ADDON_USER_PATH, 'ResumeSaverA.m3u')
DATAFILE2 = os.path.join(ADDON_USER_PATH, 'ResumeSaverB.m3u')

if PY2:
    XBMC_LOG_LEVEL = xbmc.LOGNOTICE
else:
    XBMC_LOG_LEVEL = xbmc.LOGINFO


def get_addon_setting(id):
    setting = xbmcaddon.Addon(ADDON_ID).getSetting(id)
    if setting.lower() == 'true': return True
    if setting.lower() == 'false': return False
    return str(setting)


class ResumePlayer:
    rewind_before_play = {'0': 0.0, '1': 5.0, '2': 15.0, '3': 60.0, '4': 180.0, '5': 300.0}

    rewind_s = rewind_before_play[get_addon_setting('rewind_before_play')]
    selected_m3u_file = ''
    def main(self):
        if os.path.exists(DATAFILE) or os.path.exists(DATAFILE2):
            if not self.opendata():
                return note("""Can't resume corrupt file""")
        else:
            return note('''Can't resume''', 'No File exist')


        if get_addon_setting('volume') and self.volume is not False:
            volume_set(self.volume)

        if self.media in ['audio', 'pvr/radio']:
            self.plist = xbmc.PlayList(0)
        elif self.media in ['video', 'pvr/tv']:
            self.plist = xbmc.PlayList(1)
        else:
            self.plist = xbmc.PlayList(0)

        if self.playing:
            debug('MEDIA IS: %s' % self.media)
            if self.media == 'pvr/tv':
                for counter in range(10, 0, -1):
                    debug('wait for PVR TV Channels %s' % counter)
                    xbmc.sleep(2000)
                    if get_condition('Pvr.HasTVChannels'):
                        break
                    if counter == 1:
                        return note('''Can't resume''', 'PVR Channels not available', icon=ADDON_ICON_STOP)

            if self.media == 'pvr/radio':
                for counter in range(10, 0, -1):
                    debug('wait for PVR Radio Channels %s' % counter)
                    xbmc.sleep(2000)
                    if get_condition('PVR.HasRadioChannels'):
                        break
                    if counter == 1:
                        return note('''Can't resume''', 'PVR Channels not available', icon=ADDON_ICON_STOP)

            # load file or playlist
            if self.plsize == False:
                xbmc.Player().play(item=self.playing, windowed=False)
            else:
                #self.plist.clear()
                xbmc.PlayList(0).clear()
                xbmc.PlayList(1).clear()
                #self.plist.load(self.datafile)
                xbmc.PlayList(0).load(self.datafile)
                xbmc.PlayList(1).load(self.datafile)
                #xbmc.Player().play(item=self.plist, windowed=False, startpos=self.plpos)
                xbmc.Player().play(item=xbmc.PlayList(1), windowed=False, startpos=self.plpos)

                #xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 0, "method": "Playlist.Clear", "params": {"playlistid": 0}}')
                #xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 0, "method": "Playlist.Clear", "params": {"playlistid": 1}}')
                #xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 0, "method": "Playlist.Add", "params": {"playlistid": 0, "item": {"recursive": true, "directory": "%s"}}}' % self.selected_m3u_file.replace('\\', '//'))
                #xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 0, "method": "Playlist.Add", "params": {"playlistid": 1, "item": {"recursive": true, "directory": "%s"}}}' % self.selected_m3u_file.replace('\\', '//'))
                #xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":0,"method":"Player.Open","params":{"item":{"playlistid": 1, "position":%s}}}' % self.plpos)



        self.can_play = False
        from threading import Thread
        self.can_play_thread = Thread(target=self.player_has_started)
        self.can_play_thread.daemon = True
        self.can_play_thread.start()

        self.can_play_thread.join()

        if not self.can_play:
            xbmc.Player().stop()
            return note('''Can't resume''', 'File from Playlist is not available')

        if self.playing.find('pvr://') > -1:
            debug('Skip Seeking, because Video is PVR (Live TV)')
        else:
            self.seekTime(self.time)

        if get_addon_setting('pause_on_startup') and xbmc.Player().isPlaying():
            xbmc.Player().pause()

    def seekTime(self, seekTo):
        xbmc.sleep(1000)  # wait 'a bit'. if doing seek directly it does not work when we just started playing
        if xbmc.Player().isPlaying(): 
            xbmc.Player().seekTime(seekTo)

    def player_has_started(self):
        for counter in range(5000, 0, -1):
            if xbmc.Player().isPlaying():
                if xbmc.Player().getTime() > 0.0:
                    self.can_play = True
                    return
            xbmc.sleep(1)
        self.can_play = False

    def opendata(self):
        firstFile = DATAFILE
        secondFile = DATAFILE2

        if (os.access(firstFile, os.F_OK) and os.access(secondFile, os.F_OK)):
            log('Both files existing. checking which is newer')
            if (os.path.getctime(secondFile) > os.path.getctime(firstFile)):
                firstFile = DATAFILE2
                secondFile = DATAFILE
                log('swapping files')

        try:
            self.selected_m3u_file = firstFile
            return self.opendataex(firstFile)
        except:
            self.selected_m3u_file = secondFile
            return self.opendataex(secondFile)

    def opendataex(self, datafile):
        self.playlist = []
        self.datafile = datafile
        log(self.datafile)
        
        with open(datafile, mode='rb') as fh:
            fh_str = fh.read()
            if not PY2:
                fh_str = fh_str.decode('utf-8')
                
            if fh_str.find('#STORE::DONE') < 0:
                return False

            self.volume = False
            for line in fh_str.splitlines():
                debug('line: [%s]' % line)
                theLine = line.strip()
                if theLine.startswith('#WINDOW::'):
                    self.window = theLine[9:]
                if theLine.startswith('#VOLUME::'):
                    self.volume = theLine[9:]
                if theLine.startswith('#TIME::'):
                    self.time = theLine[7:]
                    if self.time == '-':
                        self.time = False
                    else:
                        self.time = float(self.time)
                    self.time = max(0.0, self.time - self.rewind_s)
                if theLine.startswith('#PLPOS::'):
                    self.plpos = theLine[8:]
                    if self.plpos == "-":
                        self.plpos = False
                    else:
                        self.plpos = int(self.plpos)
                if theLine.startswith('#PLSIZE::'):
                    self.plsize = theLine[9:]
                    if self.plsize == '-':
                        self.plsize = False
                    else:
                        self.plsize = int(self.plsize)
                if theLine.startswith('#PLAYING::'):
                    self.playing = theLine[10:]
                    if self.playing == '-':
                        self.playing = False
                if theLine.startswith('#MEDIA::'):
                    self.media = theLine[8:]
                    if self.media == '-':
                        self.media = False
        
        return True

    def checkme(self):
        self.plist = xbmc.PlayList(0)
        self.plsize = self.plist.size()
        if self.plsize != 0:
            self.media = 'audio'
            for i in range(0, self.plsize):
                temp = self.plist[i]
                self.playlist.append(xbmc.PlayListItem.getfilename(temp))
            return
        else:
            pass
        self.plist = xbmc.PlayList(1)
        self.plsize = self.plist.size()
        if self.plsize != 0:
            self.media = 'video'
            for i in range(0, self.plsize):
                temp = self.plist[i]
                self.playlist.append(xbmc.PlayListItem.getfilename(temp))
            return
        else:
            self.media = '-'
            self.plsize = '-'
            self.playlist = '-'
            return


def volume_set(volume):
    # xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": {"volume": %s}, "id": 1}' % volume)
    xbmc.executebuiltin('SetVolume(%s, False)' % volume)
    debug('VOLUME: Set = %s' % volume)


def open_settings():
    # log('Window: %s' % xbmcgui.getCurrentWindowId())
    # log('Dialog: %s' % xbmcgui.getCurrentWindowDialogId())
    if xbmcgui.getCurrentWindowDialogId() == 10140:
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Input.Back", "id": 1 }')
    else:
        xbmcaddon.Addon().openSettings()


def log(msg):
    if not PY2:
        msg = msg.encode('utf-8', 'surrogateescape').decode('ISO-8859-1')
    xbmc.log('%s: LDR: %s' % (ADDON_ID, msg), XBMC_LOG_LEVEL)


def note(heading, message=None, time=-1, icon=None):
    if time == -1:
        xbmcgui.Dialog().notification(heading='%s' % heading, message='%s' % message if message else ' ', icon='%s' % (icon if icon else ADDON_ICON))
    else:
        xbmcgui.Dialog().notification(heading='%s' % heading, message='%s' % message if message else ' ', icon='%s' % (icon if icon else ADDON_ICON), time=time)
    log('NOTIFICATION: "%s%s"' % (heading, ' - %s' % message if message else ''))


def dialog_yesno(label1, label2=None, label3=None, nolabel='', yeslabel='', autoclose=0):
    if PY2:
        return xbmcgui.Dialog().yesno(ADDON_NAME, line1=label1, line2=label2, line3=label3, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)
    else:
        return xbmcgui.Dialog().yesno(ADDON_NAME, message='%s%s%s' % (label1, ' - %s' % label2 if label2 else '', ' - %s' % label3 if label3 else ''), nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


def debug(string):
    if not get_addon_setting('debug'):
        return
    log('DEBUG: %s' % string)


def get_condition(condition):
    # example: get_condition('String.IsEmpty(System.Time(xx))')
    return bool(xbmc.getCondVisibility(condition))


def delete_m3u():
    if not dialog_yesno('Sure to delete M3U Files?', nolabel='Cancel', yeslabel='Delete'):
        return
    file_a_deleted = False
    file_b_deleted = False
    try:
        os.remove(DATAFILE)
        file_a_deleted = True
    except:
        pass
    try:
        os.remove(DATAFILE2)
        file_b_deleted = True
    except:
        pass
    note('M3U Files deleted!', '%s | %s' % ('ResumeSaverA.m3u' if file_a_deleted else '', 'ResumeSaverB.m3u' if file_b_deleted else ''))


def main():
    count = len(sys.argv) - 1
    if count > 0:
        log(sys.argv[1])
        given_args = sys.argv[1].split(';')
        if str(given_args[0]) == "delete_m3u":
            delete_m3u()
        #elif str(given_args[0]) == "settings":
        #    open_settings()
        #elif str(given_args[0]) == 'update':
        #    update()
        else:
            note('Unknown Arguments given!', '%s' % given_args)
    else:
        m = ResumePlayer()
        m.main()
        del m


if __name__ == '__main__':
    main()
