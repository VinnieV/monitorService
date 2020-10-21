#!/usr/bin/python3
import boto3
import configparser
import time
import sys
import os
import subprocess
import logging
import datetime
import json
global config


def parseConfig():
    global config 
    config = configparser.ConfigParser()
    config.read('/etc/monitor/config.ini')

def sendNotification(importance,message,description):
    global config
    print("Notification send:\n\tPrio: {}\n\tMessage: {} \n\tDescription: {}".format(importance,message,description))
    # Importance:
    # Critical: 0 (notification + SMS)
    # Error: 1 (notification)
    # Warning: 2 (logged)
    # Info: 3 (logged)
    accessKey = config["AWS"]["snsAccessKey"]
    secretKey = config["AWS"]["snsSecretKey"]
    topicArn = config["AWS"]["snsTopicArn"]

    sns = boto3.client('sns',
        aws_access_key_id=accessKey, 
        aws_secret_access_key=secretKey, 
        region_name="eu-west-1"
    )

    now = datetime.datetime.now()

    jsonMessage = {"client":config["Application"]["client"],
        "scope":"vpnserver",
        "importance":importance,
        "message":message,
        "description":description,
        "datetime":now.strftime("%Y-%m-%d %H:%M:%S")
    }

    response = sns.publish(TopicArn=topicArn, # Right now its hardcoded but it should come from the config file
        MessageStructure="json",
        Message=json.dumps({'default': json.dumps(jsonMessage)})
    )

    print(response)


def checkVPNServer(oldStatus):
    # Check if service running
    service = os.system("service openvpn status > /dev/null")
    # If return code is not 0 then the OpenVPN service is not running
    if service is not 0:
        logging.error("OpenVPN service is not running anymore")
        if oldStatus == "OK":
            sendNotification(0,"OpenVPN service is not running","When performing 'service openvpn status' it looked like the service was not running.")
        return "NOK"

    # Check if port is listening
    portListen = os.system("ss -lnu | grep 0.0.0.0:1194 > /dev/null")
    if portListen == 256:
        logging.error("OpenVPN service is not listening on port 1194")
        if oldStatus == "OK":
            sendNotification(0,"OpenVPN service is not listening","When performing 'ss -lnu | grep 0.0.0.0:1194' no entries are found.")
        return "NOK"

    # Service is running perfect so return "OK"
    if oldStatus == "NOK":
        logging.error("OpenVPN service is working properly again")
        sendNotification(0,"OpenVPN service is working properly again","OpenVPN service is working properly again.")

    return "OK"
        

def checkDiskSpace(oldStatus):
    threshold = 90
    result = subprocess.run(['df','-h','--output=source,pcent','/'], stdout=subprocess.PIPE)
    # Get the diskspace usage percentage
    percentage = int(result.stdout.split()[-1][:-1])
    if percentage > threshold:
        logging.error("Diskspace is low! >{}% used".format(threshold))
        if oldStatus == "OK":
            sendNotification(1,"Diskspace is getting full","Diskspace is getting low is now {} % full.".format(percentage))
            return "NOK"
    
    if oldStatus == "NOK":
        logging.error("Diskspace is OK again")
        sendNotification(1,"Diskspace is OK again","Diskspace was low bit its OK again")

    return "OK"
    

def checkMemoryUsage(oldStatus):
    threshold = 10
    result = subprocess.run(['free','-m'], stdout=subprocess.PIPE)
    result = result.stdout.split(b"\n")[1].split()
    # Get the memory usage percentage
    total = int(result[1])
    free = int(result[3])
    percentage = (free/total)*100
    if percentage < threshold:
        logging.error("Available memory is low! <{}% free".format(percentage))
        if oldStatus == "OK":
            sendNotification(1,"Available memory is low! <{}% free".format(percentage),"Available memory is low now {} % available.".format(percentage))
            return "NOK"
    
    if oldStatus == "NOK":
        logging.error("Memory usage is OK again")
        sendNotification(1,"Memory usuage is OK again","Available memory is now on {}".format(percentage))

    return "OK"
    

def checkInternalIPChange(oldStatus):
    current = os.popen('ip addr show eth0 | grep "\<inet\>" | awk \'{ print $2 }\' | awk -F "/" \'{ print $1 }\'').read().strip()
    if oldStatus != current:
        logging.error("Internal IP changed")
        sendNotification(0,"Internal IP changed","Internal IP address changed from {} to {}".format(oldStatus,current))

    return current



def performCheck(func,oldStatus):
    try:
        result = func(oldStatus)
        return result
    except Exception as ex:
        sendNotification(1,"Monitor service encountered an issue when checking the {} component".format(str(func)),str(ex))
        logging.error("Monitor service encountered an issue when checking the {} component\n{}".format(str(func),str(ex)))

if __name__ == "__main__":
    # Parse /etc/monitor/monitor.ini
    parseConfig()

    # Setup Logger
    logfile = config["Application"]["logfile"]
    logging.basicConfig(filename=logfile, level=logging.INFO)
    
    interval = int(config["Application"]["interval"])*60

    memoryUsage = "OK"
    vpnServer = "OK"
    diskSpace = "OK"
    ipAddress = os.popen('ip addr show eth0 | grep "\<inet\>" | awk \'{ print $2 }\' | awk -F "/" \'{ print $1 }\'').read().strip()
    
    while True:
        logging.info("Starting new monitor round at {}".format(datetime.datetime.now()))
        
        # Checks
        vpnServer = performCheck(checkVPNServer,vpnServer)
        diskSpace = performCheck(checkDiskSpace,diskSpace)
        ipAddress = performCheck(checkInternalIPChange,ipAddress)
        memoryUsage = performCheck(checkMemoryUsage,memoryUsage)
            
        # Wait until next interval 
        time.sleep(interval)

    now = datetime.datetime.now()

    sendNotification(1,"Monitor service is not running","Monitor script reached the end which is not normal")
    logging.info("Monitor service is stopped at {}".format(now.strftime("%Y-%m-%d %H:%M:%S")))
