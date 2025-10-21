import subprocess
import random

# --- CONFIG ---
heroes = [
    "Roy Benavidez",
    "Audie Murphy",
    "John Basilone",
    "Chesty Puller"
]

products = [
    "bagged_coffee",
    "large_bag",
    "k_cup_pods",
    "gift_card"
]

slogans = [
    "Happy 250th Birthday Marines!",
    "Happy Veterans Day!",
    "Happy 4th of July!",
    "Saluting the Few, the Proud.",
    "Brewed for the Brave.",
    "To Those Who Served, We Raise a Cup.",
    "Honor. Courage. Coffee.",
    "Strong Coffee for Strong Heroes."
]

# --- MAIN LOOP ---
for hero in heroes:
    for product in products:
        slogan = random.choice(slogans)
        print(f"\n☕ Running campaign for {hero} / {product}")
        print(f"   🏷️  Slogan: {slogan}\n")
        subprocess.run([
            "python3", "main.py",
            "--hero", hero,
            "--product", product,
            "--slogan", slogan
        ])
