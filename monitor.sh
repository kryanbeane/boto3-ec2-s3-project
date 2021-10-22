#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2
#
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)
REGION="`wget -qO- http://instance-data/latest/meta-data/placement/availability-zone | sed -e 's:\([0-9][0-9]*\)[a-z]*\$:\\1:'`"
PUBLIC_IPV4=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
LOCAL_IPV4=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORYUSAGE"
echo "No of processes: $PROCESSES"
echo "Instance region: $REGION"
echo "Public IP address: $PUBLIC_IPV4"
echo "Private IP address: $LOCAL_IPV4"

if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi