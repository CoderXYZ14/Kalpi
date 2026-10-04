# Kalpi Portfolio Trade Execution Engine

This is my submission for Problem 1 of the Kalpi Builder assignment.

You give the engine a target portfolio (a list of stocks and quantities). It logs into your broker, places all the trades in one click and then sends back a report of what worked and what failed.

It supports Zerodha, Groww, Upstox, Fyers and AngelOne, plus a Mock broker so the whole flow can be tested without real money or real API keys.

## Run it

You only need Docker.

```bash
git clone https://github.com/CoderXYZ14/Kalpi.git
cd Kalpi
docker compose up --build
```

Then open http://localhost:8000 and log in with

```
username  demo
password  demo1234
```

No `.env` file is needed for the demo. Every setting has a default, and the Mock broker needs no keys. If you want to try a real broker, copy `.env.example` to `.env` and add that broker's API key and secret.

To stop it run `docker compose down`. Add `-v` to also delete the database.

### Without Docker

Needs Python 3.12 and pnpm. Without `DATABASE_URL` it uses SQLite.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install --no-deps -r requirements-nodeps.txt
cd frontend && pnpm install && pnpm build && cd ..
python manage.py migrate
python manage.py createsuperuser
BYPASS_MARKET_HOURS=true python manage.py runserver
```

## Try the flow

1. Log in on the UI
2. The Mock broker is in the Brokers list. Click Connect if it is not already Live
3. Click "Demo portfolio", or paste your own JSON, or click "Upload CSV" (columns `section,symbol,quantity`)
4. Click Execute
5. Watch the results table update with each order's status

The demo portfolio uses special test symbols so every success and failure case shows up in one run. It takes about 35 seconds because `TESTCIRCUIT` is held open for the full 30 second status check before the buys start. Any portfolio without it finishes in a couple of seconds.

## How it works

```
UI or API call
     |
     v
DRF API  ->  validate payload  ->  save Execution + Orders in Postgres
     |
     v
Engine (runs in a background thread)
     |
     v
Broker Adapter (Zerodha / Groww / Upstox / Fyers / AngelOne / Mock)
     |
     v
Broker
     |
     v
Notifier (console log + optional webhook)
```

The API returns right away with an execution id. The engine runs in the background and the UI keeps checking the execution until it is done.

How the code is organised

- `brokers` (Django app) has the adapters, broker login and the common error names
- `executions` (Django app) has the models, the engine and the APIs
- `notifications` sends the final summary
- `common` has the shared response format and error handler
- `frontend` is the React dashboard

## The adapter pattern

Every broker has a different API. Different login, different symbol format, different error messages. So every broker gets its own small adapter class, and all of them follow the same interface

```python
get_login_url(state)
complete_login(params)
get_holdings()
place_order(symbol, side, quantity, tag)
get_order_status(broker_order_id)
find_order_by_tag(tag)
```

The engine only talks to this interface. It never knows which broker is underneath.

Each adapter also translates its broker's errors into our own simple error names like `NOT_ALLOWED` or `INSUFFICIENT_FUNDS`. So the engine handles errors the same way for every broker.

### Adding a new broker

It takes one new file and one line. Nothing else changes, not the engine, the models, the views or the serializers.

Create `brokers/adapters/newbroker.py`

```python
from brokers.adapters.base import BrokerAdapter, LoginResult, OrderStatus, next_ist
from brokers.errors import BrokerError, ErrorCode


class NewBrokerAdapter(BrokerAdapter):
    required_settings = ("NEWBROKER_API_KEY",)

    def get_login_url(self, state):
        return f"https://newbroker.example/login?state={state}"

    def complete_login(self, params):
        return LoginResult(access_token=params["code"], expires_at=next_ist(6))

    def get_holdings(self):
        return {"INFY": 10}

    def place_order(self, symbol, side, quantity, tag):
        if symbol == "BANNED":
            raise BrokerError(ErrorCode.NOT_ALLOWED, "Broker says not allowed")
        return "NB-1"

    def get_order_status(self, broker_order_id):
        return OrderStatus(OrderStatus.COMPLETE, filled_quantity=10)

    def find_order_by_tag(self, tag):
        return None
```

Then add it to `brokers/adapters/registry.py`

```python
"newbroker": NewBrokerAdapter,
```

The new broker now works in login and in executions, and it shows up in the UI. `required_settings` lists the env vars it needs. Until they are set, the UI shows the broker as "Needs API keys" and its Connect button is disabled.

## Execution logic

There are two modes.

**First time.** The user has no holdings, so every line is a BUY.

**Rebalance.** The engine does not calculate any delta. The payload tells it exactly what to do

- `sell` exits existing stocks
- `buy` adds new stocks
- `rebalance` adjusts stocks the user already has. A negative change becomes a SELL and a positive change becomes a BUY

What the engine does, step by step

1. Turns the payload into one simple list of orders
2. Checks the broker login is still valid and the market is open (9:15 to 3:30 IST, Monday to Friday)
3. Fetches holdings once and fails any sell that is more than the user owns, before sending anything
4. Places all SELLs first and waits for them to finish, because selling frees up money for the buys
5. Then places all BUYs
6. Sends at most 8 orders per second to stay under the broker limit of 10 per second
7. Checks each order's status every 2 seconds for up to 30 seconds
8. Marks the execution as done and sends the notification

If one order fails, the engine keeps going with the rest. It only stops early when continuing makes no sense, like when the broker login expires or the market is closed.

## Edge cases handled

| Case                                                           | What happens                                                                                                                                                                |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Selling more shares than owned                                 | Order fails with `NOT_ENOUGH_SHARES` before anything is sent                                                                                                                |
| Quantity is zero or negative                                   | Request rejected with a clear error                                                                                                                                         |
| Same symbol twice in one request                               | Request rejected                                                                                                                                                            |
| Buying not allowed (surveillance, trade to trade, suspended)   | Order fails with `NOT_ALLOWED` and the broker's reason                                                                                                                      |
| Selling not allowed (no DDPI or TPIN approval, pledged shares) | Order fails with `SELL_NOT_AUTHORIZED`                                                                                                                                      |
| Not enough money                                               | Order fails with `INSUFFICIENT_FUNDS`                                                                                                                                       |
| Price outside the circuit band                                 | Order fails with `PRICE_OUT_OF_RANGE`                                                                                                                                       |
| Stock stuck at upper or lower circuit                          | Order is accepted but never fills, so after 30 seconds it is marked `PENDING` and left open                                                                                 |
| Partial fill                                                   | Marked `PARTIAL` with the filled quantity                                                                                                                                   |
| Broker says too many requests                                  | Waits and retries, up to 4 attempts with growing gaps                                                                                                                       |
| Broker server down                                             | Retries, then fails with `BROKER_UNAVAILABLE`                                                                                                                               |
| Timeout while placing an order                                 | Never retried blindly. The engine first searches the broker's order list using the order's unique tag. If the order went through it uses it, so there is never a double buy |
| Login expires midway                                           | Execution stops and the remaining orders are marked `SKIPPED`                                                                                                               |
| User clicks Execute twice                                      | Same idempotency key returns the same execution, so no orders are placed twice                                                                                              |
| Two executions on the same account at once                     | Second one is rejected until the first finishes                                                                                                                             |
| Server restarts in the middle                                  | On startup, stuck executions are marked stopped so nothing is left hanging                                                                                                  |
| Broker keys not set                                            | Clear error saying the broker is not configured, the app does not crash                                                                                                     |

Final order statuses are `SUCCESS`, `PARTIAL`, `PENDING`, `FAILED` and `SKIPPED`.

## Mock broker test symbols

The Mock broker behaves like a real one but uses fake money. These symbols trigger each case on purpose

| Symbol           | Behaviour                                                                    |
| ---------------- | ---------------------------------------------------------------------------- |
| `TESTNOTALLOWED` | Rejected as not allowed                                                      |
| `TESTNOSELL`     | Sell rejected as not authorised                                              |
| `TESTCIRCUIT`    | Stays open, ends as PENDING                                                  |
| `TESTPARTIAL`    | Fills only half                                                              |
| `TESTRATELIMIT`  | Rate limited on the first try, then works                                    |
| `TESTTIMEOUT`    | Times out but the order was actually placed, to prove there is no double buy |
| `TESTAUTHEXPIRE` | Login expires in the middle of the execution                                 |

Any other symbol fills fully at a fixed price of ₹100 a share. The mock account starts with ₹10 lakh cash, so huge quantities fail with not enough money. It also starts with INFY 50, TCS 20, HDFCBANK 30, TESTNOSELL 10, TESTCIRCUIT 10 and TESTPARTIAL 10 so sells and rebalances can be tested. Buys and sells update these holdings, and they reset when the server restarts.

## API

All responses look like `{"success": true, "data": ...}` or `{"success": false, "error": "..."}`.

| Method | Endpoint                          | What it does                                                                 |
| ------ | --------------------------------- | ---------------------------------------------------------------------------- |
| POST   | `/api/auth/token/`                | Log in and get a token                                                       |
| GET    | `/api/brokers/`                   | List brokers, whether each has API keys set (`configured`) and whether you are connected |
| GET    | `/api/brokers/<broker>/login/`    | Start broker login. Mock connects instantly, real brokers return a login URL |
| GET    | `/api/brokers/<broker>/callback/` | The broker sends the user back here after login, then it redirects to the UI |
| POST   | `/api/executions/`                | Send a portfolio and start executing. Returns the execution id               |
| GET    | `/api/executions/<id>/`           | Get the execution with every order and its status                            |

Every API except the broker callback needs the header `Authorization: Token <your-token>`. Users can only see their own broker accounts and executions.

### Example

Get a token

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo1234"}'
```

Connect the Mock broker

```bash
curl http://localhost:8000/api/brokers/mock/login/ -H "Authorization: Token <token>"
```

First time portfolio

```json
{
  "mode": "FIRST_TIME",
  "broker": "mock",
  "idempotency_key": "first-run-1",
  "buy": [
    { "symbol": "INFY", "quantity": 10 },
    { "symbol": "TCS", "quantity": 5 }
  ]
}
```

Rebalance

```json
{
  "mode": "REBALANCE",
  "broker": "mock",
  "idempotency_key": "rebalance-1",
  "sell": [{ "symbol": "TCS", "quantity": 5 }],
  "buy": [{ "symbol": "WIPRO", "quantity": 8 }],
  "rebalance": [
    { "symbol": "INFY", "quantity_change": 2 },
    { "symbol": "HDFCBANK", "quantity_change": -3 }
  ]
}
```

Send either one with

```bash
curl -X POST http://localhost:8000/api/executions/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

Then check the result

```bash
curl http://localhost:8000/api/executions/<execution_id>/ -H "Authorization: Token <token>"
```

## UI

There is a simple dashboard at http://localhost:8000 built with React and Vite. Docker builds it automatically and Django serves it, so no extra setup is needed. It covers the full flow from the assignment. Log in, connect a broker, upload a CSV or paste a portfolio, click Execute and watch each order update live in the results table.

Only the Mock broker can execute in the demo. Real brokers like Zerodha need their own API key and secret in `.env`. Their adapters are fully written and use the same engine and UI.

To work on the UI with hot reload, run the backend on port 8000, then

```bash
cd frontend
pnpm install
pnpm dev
```

and open http://localhost:5173. It forwards `/api` calls to the backend.

## Notifications

When an execution finishes, a summary is built with the counts per status and every order with its error if any. It is always printed to the console logs. If `WEBHOOK_URL` is set, the same summary is also POSTed there. A failed webhook is only logged and never breaks the execution. New channels like email or WebSocket can be added as another notifier class.

## Real broker login

Zerodha, Upstox, Fyers and AngelOne use a redirect login. The user is sent to the broker's own page, logs in there and is sent back to our callback with a code. We swap the code for an access token and save it. We never see the user's broker password.

Groww works a bit differently. The user approves their API key on Groww Cloud for the day and then the login endpoint fetches the token directly.

Broker tokens expire daily, so the user has to connect again each trading day.

## Why I chose these tools

**Django REST Framework instead of FastAPI.** The assignment mentions FastAPI. I went with DRF because the built in ORM, migrations, admin panel, token auth and serializers let me build a reliable system faster and with less custom code. The admin panel is also handy to inspect executions and orders.

**Official broker SDKs instead of OpenAlgo.** OpenAlgo is a good open source project that already connects 30+ Indian brokers. But it is a separate Flask platform that would have to run next to this app, and the adapter layer, which is the main point of this assignment, would be hidden inside someone else's code. So I wrote thin adapters on top of each broker's official SDK (`kiteconnect`, `growwapi`, `upstox-python-sdk`, `fyers-apiv3`, `smartapi-python`). Each adapter is small and I can explain every line. OpenAlgo could still be added later as just another adapter.

**tenacity** handles the retries with growing wait times. **pyrate-limiter** keeps orders under the per second limit, with one limiter per broker shared by every execution. **cachetools** caches the Upstox and AngelOne symbol lookups. **django-environ** reads settings from env vars or `.env`. **whitenoise** serves the UI and admin files. All are small focused libraries so I did not have to write that logic myself.

**Broker SDK problems I worked around.** I read each SDK's source, not just its docs, and found real issues:

- `fyers-apiv3` pins `requests==2.31.0` while `growwapi` needs `>=2.32.3`, so they cannot be installed together normally. Fyers is installed with `--no-deps` from `requirements-nodeps.txt`, and its real dependencies are pinned at current versions in `requirements.txt`.
- The Fyers SDK hides network errors, so an unclear error while placing an order is treated as a timeout. The engine then checks the order tag before it ever retries.
- The Groww and Upstox SDKs have no timeout by default, so every call passes one.
- `smartapi-python` (AngelOne) calls a public IP service when it is imported, sends a hardcoded IP header and logs users' tokens on errors. The adapter switches all three off.
- AngelOne rejects order tags of 20 characters, so its tag is cut to 19.

**React, Vite and Tailwind** for the UI. It is one dashboard, so it is built into static files and served by Django. That keeps everything to one container and one URL.

**Postgres** stores every execution and order so there is a full record of what was sent and what happened, which a trading system always needs.

## What I would add for production

- A proper job queue like Celery instead of background threads
- Encrypting broker access tokens in the database
- A whitelisted static IP for the server, since SEBI rules from April 2026 require API orders to come from a registered IP, along with a daily broker login
- Limit orders with a small price buffer as an option, since some brokers convert or block plain market orders
- Testing each real adapter against a live account. Right now the full flow is tested end to end on the Mock broker, and the real adapters are written from each broker's official docs and SDK
- NSE holidays are not checked by the market hours rule. On a holiday the broker rejects the order and it fails with `MARKET_CLOSED`
- Reusing an idempotency key with a different payload returns the first execution and does not warn
- The 8 orders per second limit is shared inside one server process. Several servers on the same broker API key would need a shared limiter, for example in Redis
