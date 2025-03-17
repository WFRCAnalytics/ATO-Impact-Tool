Set objShell = CreateObject("WScript.Shell")
strCurDir = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName(".") ' Get script's directory
objShell.Run """C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe"" """ & strCurDir & "\main.py""", 0, False