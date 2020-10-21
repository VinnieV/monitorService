# Monitor service
Custom made monitor service for a VPN server that will send a JSON message 

# Install
1.) Create a folder in /etc.

    sudo mkdir /etc/monitor

2.) Copy the config file

    sudo cp monitor.conf /etc/monitor/monitor.conf

3.) Set the parameters with your favorite editor.

    sudo vim /etc/monitor/monitor.conf

4.) Copy monitor.py to /usr/sbin

    sudo cp monitor.py /usr/sbin/monitor.py

5.) Make the script executable

    sudo chmod +x /usr/sbin/monitor.py

6.) Copy monitor-service to init.d

    sudo cp monitor-service /etc/init.d/monitor-service

7.) Make monitor-service executable

    sudo chmod +x /etc/init.d/monitor-service

8.) Start the service

    sudo service monitor-service start

9.) Add the service to start at boot.

    update-rc.d monitor-service defaults
