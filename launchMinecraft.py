#!/usr/bin/env python
#coding:utf-8

__author__ = 'CoderZh and Tymur'

import sys
from time import sleep
# Important for multithreading
sys.coinit_flags = 0 # pythoncom.COINIT_MULTITHREADED

import win32com
import win32com.client
import win32gui
import win32con
import pythoncom
#import keyboard

from pathlib import Path
import os
import re
import subprocess
import psutil

def dump(obj):
	for attr in dir(obj):
		print("obj.%s = %r" % (attr, getattr(obj, attr)))

def getIEServer(hwnd, ieServer):
	if win32gui.GetClassName(hwnd) == 'Internet Explorer_Server':
		ieServer.append(hwnd)

#def connectToIEServer():


def changeLanguage(lang):
	#lang should be uk_UA or en_US
	userprofile_folder = os.environ['userprofile']
	data_folder = Path(f"{userprofile_folder}/AppData/Local/Packages/Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe/LocalState/games/com.mojang/minecraftpe/")
	file_to_open = data_folder / "options.txt"
	s = open(file_to_open).read()
	repl_result = re.subn(r'game_language:.*', f'game_language:{lang}', s)
	f = open(file_to_open, 'w')
	f.write(repl_result[0])
	f.close()
	print("language changed")

def launchMinecraft():
	subprocess.call('explorer.exe shell:appsFolder\Microsoft.MinecraftEducationEdition_8wekyb3d8bbwe!Microsoft.MinecraftEducationEdition')

def getCredentials():
	cred_path = os.path.join(os.path.dirname(sys.executable), 'credentials.txt')
	with open(cred_path) as f:
		lines = f.readlines()
		login = lines[0]
		password = lines[1]
	print("credentials received")
	return login, password

def wait_password_page_to_load(login_element):
	#Wait until password input page is loaded
	while(login_element.className != "moveOffScreen"):
		for el in doc.all:
			try:
				if el.name == "loginfmt" and el.className == "moveOffScreen":
					login_element = el
					#print(el.className)
					#sleep(0.1)
			except:
				print("passwd screen isn't loaded yet")
				#sleep(0.1)
				continue
		sleep(0.1)

def loginIE(login, password):
	pythoncom.CoInitializeEx(0) # not use this for multithreading

	#Connect to internet explorer server instance
	mainHwnd = win32gui.FindWindow('ADALWebBrowserHost', '')
	if mainHwnd:
		ieServers = []
		win32gui.EnumChildWindows(mainHwnd, getIEServer, ieServers)
		if len(ieServers) > 0:
			ieServer = ieServers[0]
			msg = win32gui.RegisterWindowMessage('WM_HTML_GETOBJECT')
			ret, result = win32gui.SendMessageTimeout(ieServer, msg, 0, 0, win32con.SMTO_ABORTIFHUNG, 20000)
			ob = pythoncom.ObjectFromLresult(result, pythoncom.IID_IDispatch, 0)
			doc = win32com.client.dynamic.Dispatch(ob)
			print("connected to IE server")
			try:
				win32gui.SetForegroundWindow(mainHwnd)
			except:
				print("couldn't SetForegroundWindow 1")
				return False

			#for i in range(2):
			#Make sure that we've got all elements loaded
			page_type = ""
			login_not_ready = True
			submit_not_ready = True
			password_not_ready = True
			while(login_not_ready or submit_not_ready or password_not_ready):
			#Get elements from document
				try:
					for el in doc.all:
						#Try is needed because not all elements have both name and type fields
						try:
							if el.name == "loginfmt":
								login_element = el
								login_not_ready = False
								print("received login element")
							if el.type == "submit":
								submit_element = el
								submit_not_ready = False
								print("received btn element")
							if el.name == "passwd":
								password_element = el
								password_not_ready = False
						except:
							print("element has no name attribute")
							#sleep(0.1)
							continue
				except:
					print("doc isn't loaded yet")
					return False
				sleep(0.1)
			#Figure out what page is loaded	
			if password_element.className == "moveOffScreen":
				page_type = "login_page"
			elif login_element.className == "moveOffScreen":
				page_type = "password_page"

				
			if page_type == "login_page":
				#Paste login
				login_element.focus()
				login_element.value = login
				submit_element.style.backgroundColor = "#000000"
				submit_element.focus()
				submit_element.blur()
				submit_element.click()
				wait_password_page_to_load(login_element)
			elif page_type == "password_page":
				#Paste password
				password_element.focus()
				password_element.value = password
				submit_element.style.backgroundColor = "#000000"
				submit_element.focus()
				submit_element.blur()
				submit_element.click()
				print("ok")
				return True
			else:
				print("page_type unspecified")
	else:
		print("No IE server found")
		return False

def launchMine(lessonType):

	if lessonType == "PS":
		changeLanguage("uk_UA")
	elif lessonType == "PR":
		changeLanguage("en_US")
	else:
		print("Unavailable lesson type specified. Should be PS or PR")

	login, password = getCredentials()

	launchMinecraft()

	login_successfull = False

	times_launched = 0
	while not(login_successfull):
		try:
			login_successfull = loginIE(login, password)
			sleep(0.5)
			times_launched += 1
			if times_launched > 1200:
				return False
		except:
			print("something went completely wrong...")
	return True

def closeMine():
	os.system("TASKKILL /F /IM Minecraft.Windows.exe")
