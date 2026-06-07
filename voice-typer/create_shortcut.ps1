$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\語音輸入.lnk")
$sc.TargetPath = "$PSScriptRoot\launcher.bat"
$sc.WorkingDirectory = "$PSScriptRoot"
$sc.IconLocation = "$PSScriptRoot\src\ui\icon.ico"
$sc.Save()
Write-Host "桌面捷徑已建立！"
