xcopy minecraft %userprofile%\documents\MinecraftAutoLogin\
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%userprofile%\Desktop\MinePS.lnk');$s.TargetPath='%userprofile%\documents\MinecraftAutoLogin\MinePS.exe';$s.Save()"
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%userprofile%\Desktop\MinePR.lnk');$s.TargetPath='%userprofile%\documents\MinecraftAutoLogin\MinePR.exe';$s.Save()"
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%appdata%\Microsoft\Windows\Start Menu\Programs\Startup\tchrHlprSt.lnk');$s.TargetPath='%userprofile%\documents\MinecraftAutoLogin\tchrHlprSt.exe';$s.Save()"
explorer.exe %userprofile%\documents\MinecraftAutoLogin\credentials.txt
explorer.exe %userprofile%\documents\MinecraftAutoLogin\