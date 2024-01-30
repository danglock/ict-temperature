# Sensor imports
import glob
import time
import platform
from datetime import datetime
# Notifier imports
import asyncio
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage


"""
Raspberry temperature sensor monitor

Synopsis:
    Every 5 minutes:
    - Get data from DS18B20 temperature sensor
    - Send temperature data to azure service bus queue
"""



class Thermometer:
    """
    Thermometer object used to parse temperature provided by DS18B20 sensor.
    
    Usage example:
        t = Thermometer()
        actual_temperature = t.get_temperature()
    """


    def __init__(self, device_root:str="/sys/bus/w1/devices/28*/w1_slave"):
        self.ds18b20_roots = glob.glob(device_root)


    def read_file(self, filePath) -> str:
        with open(filePath, encoding='utf8') as f:
            return f.read()
        
    
    def check_thermometer_connection(self) -> bool:
        """
        Exit the script if problem with ds18b20_roots
        """
        if len(self.ds18b20_roots) > 0:
            return True
        else:
            return False


    def get_temperature(self):
        if self.check_thermometer_connection():
            # Get content of thermometer
            content = self.read_file(self.ds18b20_roots[0])
            # Isolate temperature
            second_line = content.split("\n")[1]
            temperature_data = second_line.split(" ")[9]
            # return formated temperature
            return float(temperature_data[2:]) / 1000
        else:
            raise Exception('unable to get temperature. Please check device connection, or configured ds18b20_roots!')   



class Notifier:
    """
    Notifier object used to push data on azure Service Bus Queue

    Usage examlpe:
        n = Notifier(connection_str = "https://azure.com/storageaccount/S3CRET_CONNECTION_STR")
        n.pushData(queue_name="my_queue", data='{"json": "data"}')


    Source: https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-python-how-to-use-queues
    """


    def __init__(self, connection_str:str):
        self.connection_str = connection_str


    async def pushData(self, queue_name:str, data) -> bool:

        # Init a Service Bus client
        async with ServiceBusClient.from_connection_string(conn_str=self.connection_str, logging_enable=True) as servicebus_client:
            # Init sender object
            sender = servicebus_client.get_queue_sender(queue_name=queue_name)

        # Send the message
        async with sender:
            message = ServiceBusMessage(str(data))
            await sender.send_messages(message)
            print("Message sent to Service Bus Queue !")


def is_linux_os() -> bool:
    if platform == "linux" or platform == "linux2":
        return True
    else:
        return False



def motd():
    print('INFO: please run thoses commands before running this script:')
    print("'sudo modprobe w1-gpio' to enable GPIO communication for 1-Wire devices with w1-gpio kernel module.")
    print("'sudo modprobe w1-therm' to load w1-therm kernel module for reading 1-Wire temperature sensors.")
    print("\n\rStarting...\n\r")
    time.sleep(3)



if __name__ == '__main__':

    # Check OS
    if not is_linux_os():
        print("Error: this scrip cannot be runned on a non linux host")
        exit(1)

    motd() # Print Message of the Day

    # Init thermometer
    t = Thermometer(device_root="/sys/bus/w1/devices/28*/w1_slave")
    # Init notifier
    n = Notifier(connection_str="S3CR3T")


    # Check if working
    try:
        actual_temp = t.get_temperature()
        print(actual_temp)
    except Exception as E:
        print(f"Error: {E}")
        exit(1)


    while True:
        """
        Monitor Temperature
        """

        actual_time = datetime.now().strftime("%H:%M:%S")
        actual_temp = t.get_temperature()
        print(f"[{actual_time}]\t{actual_temp}")

        # Send temperature to Azure
        try:
            n.pushData(queue_name="my_queue", data=f'{{"time": "{actual_time}", "temperature": "{actual_temp}"}}')
        except Exception as E:
            print(f"Error: {E}\n\rUnable to send data to Azure Service Bus Queue!")


        time.sleep(60*5) # Wait 5 minutes
        
