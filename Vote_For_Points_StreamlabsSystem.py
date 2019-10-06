#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Voting game with lot of variation and customization to fit most streamers"""
#---------------------------------------
# Libraries and references
#---------------------------------------
import codecs
import json
import os
import winsound
import ctypes
import random
import time
#---------------------------------------
# [Required] Script information
#---------------------------------------
ScriptName = "Vote for Points"
Website = "https://www.twitch.tv/generalrommel"
Creator = "GeneralRommel"
Version = "1.0"
Description = "Voting minigame"
#---------------------------------------
# Variables
#---------------------------------------
settingsfile = os.path.join(os.path.dirname(__file__), "settings.json")
MessageBox = ctypes.windll.user32.MessageBoxW
MB_YES = 6
#---------------------------------------
# Classes
#---------------------------------------
class Settings:
    """" Loads settings from file if file is found if not uses default values"""

    # The 'default' variable names need to match UI_Config
    def __init__(self, settingsfile=None):
        if settingsfile and os.path.isfile(settingsfile):
            with codecs.open(settingsfile, encoding='utf-8-sig', mode='r') as f:
                self.__dict__ = json.load(f, encoding='utf-8-sig')

        else: #set variables if no custom settings file is found
            self.OnlyLive = True
            self.StartCommand = "!startvote"
            self.EndCommand = "!endvote"
            self.VoteCommand = "!vote"
            self.WinCommand = "!win"
            self.Permission = "Caster"
            self.PermissionInfo = ""
            self.Usage = "Stream Chat"
            self.EndResponse = "Voting is now closed!  Wait for the announcement to see who wins, good luck!"
            self.WinResponse = "Team {0} has won! Everyone who voted for them gets 1 {1}"
            self.StartResponse = "A round of voting for which team will win has started! Type !vote 1-5 to vote for teams 1-5."
            self.VoteMessage = "$user your vote has been registered."
            self.PermissionResp = "$user -> only $permission ($permissioninfo) and higher can use this command"
            self.VoteTime = -1.0

    # Reload settings on save through UI
    def Reload(self, data):
        """Reload settings on save through UI"""
        self.__dict__ = json.loads(data, encoding='utf-8-sig')

    def Save(self, settingsfile):
        """ Save settings contained within to .json and .js settings files. """
        try:
            with codecs.open(settingsfile, encoding="utf-8-sig", mode="w+") as f:
                json.dump(self.__dict__, f, encoding="utf-8", ensure_ascii=False)
            with codecs.open(settingsfile.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
                f.write("var settings = {0};".format(json.dumps(self.__dict__, encoding='utf-8', ensure_ascii=False)))
        except ValueError:
            Parent.Log(ScriptName, "Failed to save settings to file.")

#---------------------------------------
# Settings functions
#---------------------------------------
def SetDefaults():
    """Set default settings function"""
    winsound.MessageBeep()
    returnValue = MessageBox(0, u"You are about to reset the settings, "
                                "are you sure you want to contine?"
                             , u"Reset settings file?", 4)
    if returnValue == MB_YES:
        returnValue = MessageBox(0, u"Settings successfully restored to default values"
                                 , u"Reset complete!", 0)
        global MySet
        Settings.Save(MySet, settingsfile)

def ReloadSettings(jsonData):
    """Reload settings on pressing the save button"""
    global MySet
    MySet.Reload(jsonData)

def SaveSettings():
    """Save settings on pressing the save button"""
    Settings.Save(MySet, settingsfile)

#---------------------------------------
# Optional functions
#---------------------------------------
def OpenReadMe():
    """Open the readme.txt in the scripts folder"""
    location = os.path.join(os.path.dirname(__file__), "README.txt")
    os.startfile(location)

def SendResp(data, Usage, Message):
    """Sends message to Stream or discord chat depending on settings"""
    Message = Message.replace("$user", data.UserName)
    Message = Message.replace("$currencyname", Parent.GetCurrencyName())
    Message = Message.replace("$target", data.GetParam(1))
    Message = Message.replace("$permissioninfo", MySet.PermissionInfo)
    Message = Message.replace("$permission", MySet.Permission)

    l = ["Stream Chat", "Chat Both", "All", "Stream Both"]
    if not data.IsFromDiscord() and (Usage in l) and not data.IsWhisper():
        Parent.SendStreamMessage(Message)

    l = ["Stream Whisper", "Whisper Both", "All", "Stream Both"]
    if not data.IsFromDiscord() and data.IsWhisper() and (Usage in l):
        Parent.SendStreamWhisper(data.User, Message)

    l = ["Discord Chat", "Chat Both", "All", "Discord Both"]
    if data.IsFromDiscord() and not data.IsWhisper() and (Usage in l):
        Parent.SendDiscordMessage(Message)

    l = ["Discord Whisper", "Whisper Both", "All", "Discord Both"]
    if data.IsFromDiscord() and data.IsWhisper() and (Usage in l):
        Parent.SendDiscordDM(data.User, Message)

#---------------------------------------
# [Required] functions
#---------------------------------------
def Init():
    """data on Load, required function"""
    global MySet
    MySet = Settings(settingsfile)

    if MySet.Usage == "Twitch Chat":
        MySet.Usage = "Stream Chat"
        Settings.Save(MySet, settingsfile)

    elif MySet.Usage == "Twitch Whisper":
        MySet.Usage = "Stream Whisper"
        Settings.Save(MySet, settingsfile)

    elif MySet.Usage == "Twitch Both":
        MySet.Usage = "Stream Both"
        Settings.Save(MySet, settingsfile)

    global State
    State = 0

    global JoinedPlayers
    JoinedPlayers = []

    global StartTime
    StartTime = None
    global StartData
    StartData = None

def Execute(data):
    """Required Execute data function"""
    global State
    global JoinedPlayers
    global StartTime
    global StartData

    if State == 0 and data.IsChatMessage() and data.GetParam(0).lower() == MySet.StartCommand.lower():

        if not HasPermission(data):
            return

        if not MySet.OnlyLive or Parent.IsLive():
            State = 1
            message = MySet.StartResponse
            SendResp(data, MySet.Usage, message)
            StartTime = time.time()
            StartData = data
            return

    if State == 1 and data.IsChatMessage() and data.GetParam(0).lower() == MySet.VoteCommand.lower():
        JoinedPlayers.append(data)
        SendResp(data, MySet.Usage, MySet.VoteMessage)
        return

    if State == 1 and data.IsChatMessage() and data.GetParam(0).lower() == MySet.EndCommand.lower():
        State = 2
        SendResp(data, MySet.Usage, MySet.EndResponse)
        return

    if (State == 1 or State == 2) and data.IsChatMessage() and data.GetParam(0).lower() == MySet.WinCommand.lower():
        HandleWinner(data)
        return

    return

def HandleWinner(data):
    global State
    global JoinedPlayers
    global StartTime

    State = 0
    StartTime = None
    if not JoinedPlayers:
        SendResp(data, MySet.Usage, MySet.NoJoinResponse)
        return

    winningTeam = data.GetParam(1).lower();

    for player in JoinedPlayers:
        if player.GetParam(1).lower() == winningTeam:
            Parent.AddPoints(player.User, player.UserName, 1)

    currency = Parent.GetCurrencyName()
    winMessage = MySet.EndResponse.format(winningTeam, currency)
    SendResp(data, MySet.Usage, winMessage)
    JoinedPlayers = []
    return

def Tick():
    """Required tick function"""
    global StartTime
    global StartData

    if StartTime is not None:
        elapsedTime = time.time() - StartTime
        if elapsedTime > MySet.VoteTime != -1.0:
            HandleWinner(StartData)

    return

def HasPermission(data):
    """Returns true if user has permission and false if user doesn't"""
    if not Parent.HasPermission(data.User, MySet.Permission, MySet.PermissionInfo):
        message = MySet.PermissionResp.format(data.UserName, MySet.Permission, MySet.PermissionInfo)
        SendResp(data, MySet.Usage, message)
        return False
    return True
