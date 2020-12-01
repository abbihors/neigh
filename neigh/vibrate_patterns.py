import random

import settings

async def pattern_basic(vibrator):
    amount = round(random.uniform(0.4, 1.0), 2)
    await vibrator.enqueue(settings.vibrate_factor * amount, 1.3)

async def pattern_burst(vibrator):
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 1.2, 0.2)
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 1.2, 0.2)
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 1.2, 0.2)

async def pattern_burst_pulse(vibrator):
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(settings.vibrate_factor * 0.8, 0.1, 0.1)

async def pattern_burst_linger(vibrator):
    await vibrator.enqueue(settings.vibrate_factor * 1.0, 0.7, 0.2)
    await vibrator.enqueue(settings.vibrate_factor * 1.0, 0.7, 0.2)
    await vibrator.enqueue(settings.vibrate_factor * 1.0, 0.7, 0.2)
    await vibrator.enqueue(settings.vibrate_factor * 1.0, 1.7, 0.2)

async def pattern_rising(vibrator):
    for _ in range(3):
        await vibrator.enqueue(settings.vibrate_factor * 0.3, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 0.4, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 0.5, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 0.6, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 0.7, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 0.8, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 0.9, 0.1)
        await vibrator.enqueue(settings.vibrate_factor * 1.0, 0.3, 0.2)