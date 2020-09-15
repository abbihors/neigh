import asyncio

from buttplug.client import ButtplugClient
from buttplug.client import ButtplugClientWebsocketConnector

class Vibrator():

    # We need to use a factory method here because async constructors don't work
    @classmethod
    async def create(cls):
        self = Vibrator()
        
        await start_buttplug_server()

        self._bp_client = await init_buttplug_client()
        self._bp_device = self._bp_client.devices[0] # Just get the first device

        self._vibrate_queue = asyncio.Queue()
        self._vibration_level = 0.0

        asyncio.create_task(self.update_vibrator())
        
        return self

    # This runs in the background and waits for things to be put in the queue
    async def update_vibrator(self):
        while True:
            amount, on_time, off_time = await self._vibrate_queue.get()

            await self._bp_device.send_vibrate_cmd(amount)
            self._vibrate_queue.task_done()
            await asyncio.sleep(on_time)

            if self._vibrate_queue.empty() or off_time > 0:
                await self._bp_device.send_vibrate_cmd(self._vibration_level)

            await asyncio.sleep(off_time)

    async def vibrate(self, amount, on_time, off_time=0.0):
        await self._vibrate_queue.put([amount, on_time, off_time])

    async def set_vibration_level(self, amount):
        self._vibration_level = amount
        await self._bp_device.send_vibrate_cmd(self._vibration_level)

    async def stop(self):
        await self._bp_device.send_stop_device_cmd()


async def start_buttplug_server():
    await asyncio.create_subprocess_exec('intiface-cli', "--wsinsecureport", "12345")
    await asyncio.sleep(1) # Wait for the server to start up

async def init_buttplug_client():
    client = ButtplugClient("Neigh")
    connector = ButtplugClientWebsocketConnector("ws://127.0.0.1:12345")

    await client.connect(connector)
    await client.start_scanning()

    # Wait until we get a device
    while client.devices == {}:
        await asyncio.sleep(1)

    await client.stop_scanning()
    return client
