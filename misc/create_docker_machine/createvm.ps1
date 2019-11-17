# vide: https://www.youtube.com/watch?v=wUQ1CNptnTI
# vide: https://github.com/HealisticEngineer/Powershell/blob/master/New-Virtualbox.ps1
# vide: https://websiteforstudents.com/samba-setup-on-ubuntu-16-04-17-10-18-04-with-windows-systems/
#
# Prerequsities:
# * Internet needs to be one, otherwise the script won't work...  

Function New-virtualbox
{
    Param 
    (
        [Parameter(Mandatory=$True)][String]$name,
        [Parameter(Mandatory=$false)][int]$RAMGB=4,
        [Parameter(Mandatory=$false)][int]$vcpu=2,
        [Parameter(Mandatory=$false)][int]$diskGB=20,
        [Parameter(Mandatory=$false)][String]$user="sdrzymala",
        [Parameter(Mandatory=$false)][String]$pass="Pass@word2@",
        [Parameter(Mandatory=$false)][String]$timezone="UTC",
        [Parameter(Mandatory=$false)][String]$diskPath="E:\VM\",
        [Parameter(Mandatory=$false)][String]$sharedFolderPath="C:\narnia\projects\docker-data-amateur\misc\create_docker_machine\",
        [Parameter(Mandatory=$false)][String]$sharedFolderName="create_docker_machine",
        [Parameter(Mandatory=$false)][String]$configScriptName="configurevm.sh",
        [Parameter(Mandatory=$false)][String]$isoPath="E:\Tools\ubuntu-18.04-desktop-amd64.iso",
        [Parameter(Mandatory=$false)][String]$vBoxManagePath="C:\Program Files\Oracle\VirtualBox\"
    )

    # Convert GB to MB
    $disksize = $diskGB * 1024
    $memory = $RAMGB * 1024

    # Set up other parameters 
    $mediumPath = $diskPath + $name + ".vdi"

    Write-Host (get-date).ToString('y/M/d HH:mm:ss:ms') "Begin virtual machine configuration"
    $startTime = $(get-date)

    # Step one create VM
    Set-Location $vBoxManagePath
    .\VBoxManage createvm --name "$name" --register

    # modify the vm ram and network
    .\VBoxManage modifyvm "$name" --memory $memory --acpi on --boot1 dvd --cpus $vcpu
    .\VBoxManage modifyvm "$name" --nic1 natnetwork --nat-network1 NatNetwork
    ./VBoxManage modifyvm "$name" --nic2 hostonly --hostonlyadapter2 'VirtualBox Host-Only Ethernet Adapter #3'
    .\VBoxManage modifyvm "$name" --ostype Ubuntu_64
    .\VBoxManage sharedfolder add "$name" --name $sharedFolderName --hostpath $sharedFolderPath --automount
    $sharedFolderPathOnGuest = "/media/sf_" + $sharedFolderName + "/" + $configScriptName

    # create storage
    .\VBoxManage createhd --filename $mediumPath --size $disksize --format VDI
    .\VBoxManage storagectl "$name" --name "IDE Controller" --add ide

    # attach storage
    .\VBoxManage storagectl "$name" --add sata --controller IntelAHCI --name "SATA Controller"
    .\VBoxManage storageattach "$name" --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium $mediumPath

    # unattending install aka user name and computer name
    .\VBoxManage unattended install "$name" --iso="$isoPath" --user="$user" --password="$pass" --full-user-name="$user" --time-zone="$timezone" --hostname=$name.lab.local --install-additions

    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Finish virtual machine configuration"

    # start VM
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Start machine"
    #.\VBoxManage startvm "$name" --type headless
    .\VBoxManage startvm "$name"

    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Check installation status"
    # check if install is complete
    $currentstatus = ""
    while($currentstatus -notlike "*Value: *")
    {
        Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Still installing"
        Start-Sleep 30
        $currentstatus = .\VBoxManage guestproperty get $name "/VirtualBox/GuestInfo/OS/LoggedInUsers"
    }

    # wait additional minute so boot is complete
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Wait additional 60 seconds to finish reboot"
    Start-Sleep 60

    # reset / reboot
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Reboot"
    .\VBoxManage controlvm $name reset

    # wait till machine will boot again
    $currentstatus = ""
    while($currentstatus -notlike "*Value: *")
    {
        Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Still rebooting"
        Start-Sleep 30
        $currentstatus = .\VBoxManage guestproperty get $name "/VirtualBox/GuestInfo/OS/LoggedInUsers"
    }

    # wait additional minute so boot is complete
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Wait additional 60 seconds to finish reboot"
    Start-Sleep 60

    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Install complete"

    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Run post installation script"
    .\VBoxManage guestcontrol $name run --verbose --username root --password $pass --wait-stdout --wait-stderr --quiet --exe "/bin/bash" -- ls/arg0 $sharedFolderPathOnGuest | Tee-Object -Variable ConfigScriptOutput
    if ([string]($ConfigScriptOutput) -match 'Finish config script$')
    {
        Write-Host "Config script fully completed"
    }
    else 
    {
        throw "System installed correctly, but there was an error while executing the config script. 
              Check the logs carefully
              Terminating"
    }
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Run post installation script completed"

    # wait additional minute so boot is complete
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Wait additional 60 seconds to finish reboot"
    Start-Sleep 60

    # reset / reboot
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Reboot"
    .\VBoxManage controlvm $name reset

    # wait till machine will boot again
    $currentstatus = ""
    while($currentstatus -notlike "*Value: *")
    {
        Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Still rebooting"
        Start-Sleep 30
        $currentstatus = .\VBoxManage guestproperty get $name "/VirtualBox/GuestInfo/OS/LoggedInUsers"
    }

    # wait additional minute so boot is complete
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Wait additional 60 seconds to finish reboot"
    Start-Sleep 60


    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Installation and configuration done"

    # Report finish and execution time 
    $elapsedTime = $(get-date) - $StartTime
    Write-Host (get-date).ToString('y/M/d HH:mm:ss') "Execution time: " $elapsedTime

}

New-virtualbox -name "mydockermachine"















# $currentstatus = .\VBoxManage guestproperty enumerate "mydockermachine"
# Write-Host ($currentstatus.Split("\n")).Count()
