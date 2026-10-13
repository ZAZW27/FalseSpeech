import asyncio
import json
import sys
import websockets

async def test(audio_path: str):
    uri = "ws://localhost:7860/ws/audio"
    with open(audio_path, "rb") as f:
        data = f.read()
    print(f"Sending {len(data):,} bytes from {audio_path}")

    async with websockets.connect(uri, max_size=None) as ws:
        await ws.send(data)
        print("Waiting for model response...")
        resp = await asyncio.wait_for(ws.recv(), timeout=120)

        print(f"\n=== RAW RESPONSE ===\n{resp}")

        result = json.loads(resp)
        if "error" in result:
            print(f"\n[ERROR] Server said: {result['error']}")
            return

        print("\n=== RESULT ===")
        print(f"  Fake probability : {result['fake_prob']:.4f}")
        print(f"  Real probability : {result['real_prob']:.4f}")
        print(f"  Verdict          : {'FAKE 🔴' if result['is_fake'] else 'REAL 🟢'}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ws.py <audio_file.wav>")
        sys.exit(1)
    asyncio.run(test(sys.argv[1]))