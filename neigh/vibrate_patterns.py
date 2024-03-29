import random

async def pattern_basic(vibrator, vibrate_factor):
    amount = round(random.uniform(0.4, 1.0), 2)
    await vibrator.enqueue(vibrate_factor * amount, 1.3)

async def pattern_burst(vibrator, vibrate_factor):
    await vibrator.enqueue(vibrate_factor * 0.8, 1.2, 0.2)
    await vibrator.enqueue(vibrate_factor * 0.8, 1.2, 0.2)
    await vibrator.enqueue(vibrate_factor * 0.8, 1.2, 0.2)

async def pattern_burst_pulse(vibrator, vibrate_factor):
    await vibrator.enqueue(vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(vibrate_factor * 0.8, 0.1, 0.1)
    await vibrator.enqueue(vibrate_factor * 0.8, 0.1, 0.1)

async def pattern_burst_linger(vibrator, vibrate_factor):
    await vibrator.enqueue(vibrate_factor * 1.0, 0.7, 0.2)
    await vibrator.enqueue(vibrate_factor * 1.0, 0.7, 0.2)
    await vibrator.enqueue(vibrate_factor * 1.0, 0.7, 0.2)
    await vibrator.enqueue(vibrate_factor * 1.0, 1.7, 0.2)

async def pattern_rising(vibrator, vibrate_factor):
    for _ in range(3):
        await vibrator.enqueue(vibrate_factor * 0.3, 0.1)
        await vibrator.enqueue(vibrate_factor * 0.4, 0.1)
        await vibrator.enqueue(vibrate_factor * 0.5, 0.1)
        await vibrator.enqueue(vibrate_factor * 0.6, 0.1)
        await vibrator.enqueue(vibrate_factor * 0.7, 0.1)
        await vibrator.enqueue(vibrate_factor * 0.8, 0.1)
        await vibrator.enqueue(vibrate_factor * 0.9, 0.1)
        await vibrator.enqueue(vibrate_factor * 1.0, 0.3, 0.2)

async def vibrate_random(vibrator, vibrate_factor):
    weights = {
        pattern_basic: 9,
        pattern_burst: 1,
        pattern_burst_pulse: 1,
        pattern_burst_linger: 1,
        pattern_rising: 1
    }

    raffle = []

    for pattern, weight in weights.items():
        for i in range(weight):
            raffle.append(pattern)

    pattern = random.choice(raffle)

    await pattern(vibrator, vibrate_factor)
