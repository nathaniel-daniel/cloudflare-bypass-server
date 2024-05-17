# chrome-bypass-server
A simplistic way to bypass cloudflare protetions.
This repo holds a server that can bypass cloudflare protections with a selenium webdriver.
It is able to run on headless servers.
Intended usage is for applications behind the same IP to ask this server for a bypass.
The server will respond with the cf_clearance cookie and the useragent, which can then be used to bypass cloudflare.

## API
This server currently only implements one endpoint.

### `POST /api/bypass`
This endpoint allows applications to request information to bypass a url.

#### Request
```
POST /api/bypass?url=<url>

Query Params
`url`: The url that the server needs to bypass.
```

#### Response
The response is encoded as JSON.
```json
{
    "user_agent": "<The user agent to use for requests>",
    "cf_clearance": "<The cookie to use for requests. This is a full cookie string, not just a cookie value.>",
}
```