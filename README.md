# Polisim — Policy Simulation Engine

> Every policy is a bet on how 5.6 million people will react.
> Polisim lets you run that bet 1,000 times before anyone votes.

## What it does
Upload a policy document → Polisim spawns thousands of autonomous agents representing Singapore's demographic makeup → Watch sentiment and vote predictions emerge across constituencies in real-time.

## Architecture
- **TinyFish** scrapes real Singapore demographic data + public sentiment
- **OpenAI GPT-4o** powers agent reasoning (40 representative personas × population weights)
- **Social contagion model** propagates sentiment through demographic networks
- **Interactive levers** let you adjust policy parameters and see outcomes shift live

## Quick Start
```bash
cp .env.example .env  # Add your API keys
chmod +x demo.sh
./demo.sh
```

## Built at TinyFish × OpenAI Hackathon 2026
