Set objShell = CreateObject("WScript.Shell")
strCurDir = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName(".") ' Get script's directory
objShell.Run """C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"" """ & strCurDir & "\src\main.py""", 0, False