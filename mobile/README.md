# NomadIQ mobile (React Native + Expo)

Expo SDK 57, Expo Router, TypeScript. Talks to the same `/api/v1` backend as the website.

## Run it

```bash
cd mobile
npm install
npx expo start            # press a (Android), i (iOS) or scan the QR code with Expo Go
```

The app needs the backend running (`cd backend && python main.py`).

| Where the app runs | API address |
|---|---|
| Android emulator | `http://10.0.2.2:8000` (default) |
| iOS simulator / web preview | `http://localhost:8000` (default) |
| Real phone | set `EXPO_PUBLIC_API_URL=http://<your-computer's-LAN-IP>:8000` before `npx expo start` and run the API with `--host 0.0.0.0` |

## Screens

| Route | Screen |
|---|---|
| `welcome`, `login`, `signup` | Signed-out stack (`Stack.Protected`) |
| `(tabs)/index` | Plan: fill-in-the-blanks trip sentence, popular places with live photos |
| `(tabs)/trips` | Saved trips (pull to refresh) |
| `(tabs)/assistant` | Ask: chat + **hold-to-talk voice** (expo-audio → `/voice/assistant`, reply spoken with expo-speech) |
| `(tabs)/tickets` | Trains, flights, buses, hotels search; Select holds the fare |
| `(tabs)/profile` | Defaults, saved travelers, bookings, sign out |
| `trip/new`, `trip/[id]` | Trip builder; live departure board while planning, then the route, stays, food, budget, chat edits |
| `booking/[id]`, `bookings` | Review and pay (explicit confirm, price-hold countdown), booking reference, cancel |
| `explore/[place]` | Photos, summary, week's weather, videos |

## Notes

- Tokens are stored in the device keychain (expo-secure-store); the web preview falls back to localStorage.
- Generation progress is polled from `/trips/{id}/status` (streaming fetch isn't reliable on React Native).
- Payments run in test mode until a native Razorpay/Stripe SDK is added; nothing is booked without the user tapping **Pay and book**.
- `src/api/types.ts` and `src/lib/format.ts` are shared copies of the website's files. Keep them in sync with `docs/API.md`.
- Checks: `npx tsc --noEmit`, `npx expo lint`, `npx expo-doctor`.
